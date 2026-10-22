from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import date, datetime, timedelta
import re

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

    @model_validator(mode="after")
    def validate_and_sanitize_search(self):
        # 1. Tarih formatı ve geçmiş tarih kontrolü (Bozuk format veya geçmiş tarih gelirse güvenli geleceğe normalize et)
        try:
            dep_dt = datetime.strptime(str(self.departure_date).strip(), "%Y-%m-%d")
            today = datetime.now().date()
            if dep_dt.date() < today:
                dep_dt = datetime.now() + timedelta(days=7)
                self.departure_date = dep_dt.strftime("%Y-%m-%d")
        except Exception:
            dep_dt = datetime.now() + timedelta(days=7)
            self.departure_date = dep_dt.strftime("%Y-%m-%d")

        if self.return_date:
            try:
                ret_dt = datetime.strptime(str(self.return_date).strip(), "%Y-%m-%d")
                if ret_dt < dep_dt:
                    ret_dt = dep_dt + timedelta(days=3)
                    self.return_date = ret_dt.strftime("%Y-%m-%d")
            except Exception:
                ret_dt = dep_dt + timedelta(days=3)
                self.return_date = ret_dt.strftime("%Y-%m-%d")

        # 2. Yolcu sayılarını güvenli sınırlar içinde tut (1-9 arası)
        self.adults = max(1, min(9, int(self.adults if self.adults is not None else (self.passengers or 1))))
        self.children = max(0, min(9, int(self.children or 0)))
        self.infants = max(0, min(self.adults, int(self.infants or 0)))
        self.passengers = self.adults + self.children + self.infants
        return self


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

