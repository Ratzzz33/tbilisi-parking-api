"""Parking Tbilisi API — domain models"""
from pydantic import BaseModel, Field
from typing import Optional, Any


class ParkingPlace(BaseModel):
    id: Optional[int] = None
    uniqueNumber: Optional[str] = None
    address: Optional[str] = None
    polygon: Optional[str] = None


class Vehicle(BaseModel):
    id: int
    govNumber: str
    name: Optional[str] = None
    ownerCode: Optional[str] = None
    isTransit: int = 0
    cards: list[dict] = []
    fineServiceIsSubscribed: int = 0
    notPayedFinesCnt: int = 0
    onlyForFine: int = 0
    orderNumber: int = 0


class ActiveParking(BaseModel):
    id: Optional[int] = None
    carId: Optional[int] = None
    govNumber: Optional[str] = None
    parkingType: Optional[str] = None
    fixedTime: bool = False
    includeFreeParking: bool = False
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    status: Optional[str] = None
    parkingPlace: Optional[ParkingPlace] = None
    fixedAmount: float = 0
    difference: float = 0
    zoneCardExists: bool = False

    @property
    def display_id(self) -> int:
        return self.id or self.carId or 0


class PersonInfo(BaseModel):
    id: int
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    walletNumber: Optional[str] = None
    balanceAmount: float = 0
    dailyFreeParkingLeft: int = 4


class CardType(BaseModel):
    id: int
    name: Optional[str] = None
    nameKeyword: Optional[str] = None
    price: int = 0
    length: int = 0
    unit: str = "DAY"
    forZoneParking: int = 0
    shortNameEng: Optional[str] = None
    shortNameKa: Optional[str] = None

    @property
    def price_gel(self) -> float:
        return self.price / 100


# --- Request models ---

class StartParkingRequest(BaseModel):
    vehicleId: int
    type: str = "ONLY_PRICED_PARKING"
    placeNo: str

    model_config = {"json_schema_extra": {
        "example": {
            "vehicleId": 1446810,
            "type": "ONLY_PRICED_PARKING",
            "placeNo": "A1023"
        }
    }}


class AddVehicleRequest(BaseModel):
    govNumber: str
    plateNo: Optional[str] = None
    name: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {"govNumber": "NN371KN", "name": "Mazda 3"}
    }}


# --- API response wrapper ---

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
