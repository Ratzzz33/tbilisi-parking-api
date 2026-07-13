"""Parking Tbilisi — HTTP client for municipal.gov.ge API"""
import os, json, logging
from typing import Optional

import httpx

from .models import Vehicle, ActiveParking, PersonInfo, ParkingPlace, CardType

logger = logging.getLogger(__name__)

API_BASE = "https://api.municipal.gov.ge"
TTC_BASE = "https://ttc-api.municipal.gov.ge"


class ParkingClient:
    """Low-level client for the Parking Tbilisi municipal API."""

    def __init__(self, token: str, timeout: int = 10):
        self.token = token
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "LifeOS-Parking/1.0",
        }

    def _request(self, method: str, path: str, data: dict = None,
                 base: str = API_BASE, params: Optional[dict] = None) -> dict:
        url = f"{base}{path}"
        body = json.dumps({"data": data}).encode() if data else None

        with httpx.Client() as client:
            resp = client.request(method, url, content=body, params=params,
                                  headers=self._headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()

    # ---- Vehicles ----

    def get_vehicles(self) -> list[Vehicle]:
        raw = self._request("GET", "/parking/person/vehicles")
        return [Vehicle(**v) for v in raw["result"]["data"]]

    def add_vehicle(self, gov_number: str, name: str = None,
                    plate_no: str = None) -> Vehicle:
        data = {"govNumber": gov_number}
        if name:
            data["name"] = name
        if plate_no:
            data["plateNo"] = plate_no
        elif gov_number:
            data["plateNo"] = gov_number
        raw = self._request("POST", "/parking/person/vehicle", data)
        return Vehicle(**raw["result"]["data"])

    def delete_vehicle(self, vehicle_id: int) -> bool:
        self._request("DELETE", f"/parking/person/vehicle/{vehicle_id}")
        return True

    # ---- Parking sessions ----

    def get_active_parkings(self) -> list[dict]:
        raw = self._request("GET", "/parking/")
        data = raw.get("result", {}).get("data", [])
        if not data:
            return []
        if isinstance(data, dict):
            data = [data]
        return [p for p in data if p]

    def start_parking(self, vehicle_id: int, place_no: str,
                      parking_type: str = "ONLY_PRICED_PARKING") -> ActiveParking:
        raw = self._request("POST", "/parking", {
            "vehicleId": vehicle_id,
            "type": parking_type,
            "placeNo": place_no,
        })
        return ActiveParking(**raw["result"]["data"])

    def stop_parking(self, parking_id: int) -> bool:
        self._request("DELETE", f"/parking/{parking_id}")
        return True

    def get_history(self, page: int = 0, size: int = 20) -> list[dict]:
        raw = self._request("GET", "/parking/history",
                            params={"page": page, "size": size})
        return raw.get("result", {}).get("data", [])

    def get_parking_info(self, parking_id: int) -> dict:
        return self._request("GET", f"/parking/history/{parking_id}")

    # ---- Person / Wallet ----

    def get_person_info(self) -> PersonInfo:
        raw = self._request("GET", "/parking/person/check")
        return PersonInfo(**raw["result"]["data"])

    def get_payment_history(self, page: int = 0, size: int = 20) -> list[dict]:
        raw = self._request("GET", "/parking/person/payment-history",
                            params={"page": page, "size": size})
        return raw.get("result", {}).get("data", [])

    # ---- Parking places ----

    def get_all_places(self) -> list[ParkingPlace]:
        raw = self._request("GET", "/parking/places")
        return [ParkingPlace(**p) for p in raw["result"]["data"]]

    def search_places(self, query: str) -> list[ParkingPlace]:
        """Search parking places by address or number."""
        all_places = self.get_all_places()
        q = query.lower()
        return [p for p in all_places
                if q in p.uniqueNumber.lower()
                or (p.address and q in p.address.lower())]

    # ---- Tariffs ----

    def get_tariffs(self) -> list[CardType]:
        raw = self._request("GET", "/api/dictionaries/41", base=TTC_BASE)
        return [CardType(**ct) for ct in raw["data"]["cardTypes"]]

    # ---- Token validation ----

    def validate_token(self) -> bool:
        try:
            self.get_person_info()
            return True
        except Exception:
            return False
