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
    transport_type: str = "all"  # 'flight', 'train', 'bus', 'all'
    cabin_class: str = "economy"  # 'economy' or 'business'
    calendar_range: int = 7  # 7, 15, or 30 days
    is_flexible: bool = False
    night_only: bool = False

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
