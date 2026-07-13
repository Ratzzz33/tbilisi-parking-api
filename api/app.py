"""
Parking Tbilisi API Service
============================
FastAPI-based REST service for Tbilisi municipal parking.

Run:
    uvicorn app:app --host 0.0.0.0 --port 8127

Or with systemd (recommended):
    systemctl start tbilisi-parking-api
"""
import os, logging, secrets
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .client import ParkingClient
from .models import (
    StartParkingRequest, AddVehicleRequest, ApiResponse,
    Vehicle, ActiveParking, PersonInfo,
)

load_dotenv()

logger = logging.getLogger("parking-api")

# --- Global client ---
_client: Optional[ParkingClient] = None
_api_key: Optional[str] = None


def get_client() -> ParkingClient:
    if _client is None:
        raise HTTPException(503, "Service not initialized")
    return _client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client, _api_key
    token = os.environ.get("PARKING_TOKEN", "")
    _api_key = os.environ.get("PARKING_API_KEY") or None
    if not token:
        logger.warning("PARKING_TOKEN not set — service will return 503 on all requests")
    if not _api_key:
        logger.error("PARKING_API_KEY not set — authenticated routes are disabled")
    _client = ParkingClient(token) if token else None
    yield
    _client = None
    _api_key = None


app = FastAPI(
    title="Parking Tbilisi API",
    description="REST API для управления парковкой в Тбилиси через municipal.gov.ge",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    if not _api_key:
        return JSONResponse(status_code=503, content={"detail": "API key not configured"})
    if not secrets.compare_digest(request.headers.get("X-API-Key", ""), _api_key):
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


# ---- Health ---

@app.get("/health")
def health():
    if _client is None:
        return {"status": "error", "message": "PARKING_TOKEN not configured"}
    ok = _client.validate_token()
    return {"status": "ok" if ok else "token_expired", "token_valid": ok}


@app.get("/status", response_model=ApiResponse)
def status(client: ParkingClient = Depends(get_client)):
    person = client.get_person_info()
    return ApiResponse(success=True, data={
        "balanceAmount": person.balanceAmount,
        "dailyFreeParkingLeft": person.dailyFreeParkingLeft,
        "activeParkingCount": len(client.get_active_parkings()),
    })


# ---- Token ---

@app.post("/token")
def set_token(body: dict):
    """Set or update the Bearer token at runtime."""
    token = body.get("token", "")
    if not token:
        raise HTTPException(400, "token required")
    global _client
    _client = ParkingClient(token)
    ok = _client.validate_token()
    if not ok:
        _client = None
        raise HTTPException(401, "Invalid token")
    return {"status": "ok", "message": "Token accepted"}


# ---- Person / Wallet ---

@app.get("/person", response_model=ApiResponse)
def get_person(client: ParkingClient = Depends(get_client)):
    info = client.get_person_info()
    return ApiResponse(success=True, data=info.model_dump())


# ---- Vehicles ---

@app.get("/vehicles", response_model=ApiResponse)
def list_vehicles(client: ParkingClient = Depends(get_client)):
    vehicles = client.get_vehicles()
    return ApiResponse(success=True, data=[v.model_dump() for v in vehicles])


@app.post("/vehicles", response_model=ApiResponse)
def add_vehicle(req: AddVehicleRequest,
                client: ParkingClient = Depends(get_client)):
    try:
        v = client.add_vehicle(req.govNumber, req.name, req.plateNo)
        return ApiResponse(success=True, data=v.model_dump())
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/vehicles/{vehicle_id}", response_model=ApiResponse)
def remove_vehicle(vehicle_id: int,
                   client: ParkingClient = Depends(get_client)):
    client.delete_vehicle(vehicle_id)
    return ApiResponse(success=True)


# ---- Parking ---

@app.get("/parking/active", response_model=ApiResponse)
def get_active_parking(client: ParkingClient = Depends(get_client)):
    parkings = client.get_active_parkings()
    return ApiResponse(success=True, data=parkings)


@app.post("/parking/start", response_model=ApiResponse)
def start_parking(req: StartParkingRequest,
                  client: ParkingClient = Depends(get_client)):
    try:
        p = client.start_parking(req.vehicleId, req.placeNo, req.type)
        return ApiResponse(success=True, data=p.model_dump())
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/parking/stop/{parking_id}", response_model=ApiResponse)
def stop_parking(parking_id: int,
                 client: ParkingClient = Depends(get_client)):
    client.stop_parking(parking_id)
    return ApiResponse(success=True, message="Parking stopped")


@app.get("/parking/history", response_model=ApiResponse)
def parking_history(page: int = Query(0, ge=0),
                    size: int = Query(20, ge=1, le=100),
                    client: ParkingClient = Depends(get_client)):
    data = client.get_history(page, size)
    return ApiResponse(success=True, data=data)


# ---- Places ---

@app.get("/places", response_model=ApiResponse)
def list_places(search: str = Query(None, description="Filter by address or number"),
                client: ParkingClient = Depends(get_client)):
    if search:
        places = client.search_places(search)
    else:
        places = client.get_all_places()
    return ApiResponse(success=True, data=[p.model_dump() for p in places])


# ---- Tariffs ---

@app.get("/tariffs", response_model=ApiResponse)
def get_tariffs(client: ParkingClient = Depends(get_client)):
    tariffs = client.get_tariffs()
    return ApiResponse(success=True, data=[t.model_dump() for t in tariffs])


# ---- CLI convenience (same as before) ---

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8127"))
    uvicorn.run("app:app", host=host, port=port, reload=True)
