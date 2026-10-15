from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class SearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    trip_type: str = "one_way"  # 'one_way' or 'round_trip'
    passengers: int = 1
    adults: Optional[int] = 1
    children: Optional[int] = 0
    infants: Optional[int] = 0
    transport_type: str = "all"  # 'flight', 'train', 'bus', 'car', 'all'
    cabin_class: str = "economy"  # 'economy' or 'business'
    calendar_range: int = 7  # 7, 15, or 30 days
    is_flexible: bool = False
    night_only: bool = False
    location_type: str = "city"  # 'city', 'airport', 'station'
    ferry_vehicle_type: Optional[str] = "passenger"  # 'passenger', 'car', 'motorcycle'
    currency: Optional[str] = "TRY"  # 'TRY', 'EUR', 'USD', 'GBP'
    search_mode: Optional[str] = "fast"  # 'fast' (Hızlı Bilet) or 'smart_route' (Akıllı Rota & Seyahat Planı)
    include_hotel: Optional[bool] = False  # Akıllı Rota Planında Otel Dahil Edilsin mi?
    hotel_nights: Optional[int] = None  # Konaklama gece sayısı

class CarSearchRequest(BaseModel):
    location: str
    pickup_date: str
    dropoff_date: Optional[str] = None
    location_type: str = "city"  # 'city' (Şehir Merkezi), 'airport' (Havalimanı), 'station' (Gar/Otogar)
    driver_age: int = 25
    currency: Optional[str] = "TRY"

class TrackRouteRequest(BaseModel):
    origin_city: str
    destination_city: str
    target_price: float
    travel_date_start: str
    travel_date_end: Optional[str] = None
    transport_type: str = "all"
    channels: List[str] = ["email", "push", "telegram"]
    user_email: Optional[str] = "demo@ucuzbilet.com"
    telegram_chat_id: Optional[str] = None

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    telegram_chat_id: Optional[str] = None
    phone_number: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserSettingsUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None
    phone_number: Optional[str] = None
    quiet_hours_start: Optional[str] = "23:00"
    quiet_hours_end: Optional[str] = "08:00"
    email_enabled: bool = True
    push_enabled: bool = True
    telegram_enabled: bool = True

class TestNotificationRequest(BaseModel):
    channel: str # 'email', 'push', 'telegram', 'whatsapp'
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    route: Optional[str] = "İstanbul → Ankara"
    price: Optional[float] = 399.00
    regular_price: Optional[float] = 850.00
    link: Optional[str] = "https://www.enuygun.com"

class EarlyAccessRequest(BaseModel):
    email: str
    kvkk_consent: bool = True

