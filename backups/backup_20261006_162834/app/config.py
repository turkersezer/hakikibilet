import os
from pydantic_settings import BaseSettings

class Settings:
    APP_NAME: str = "Ucuz Bilet Bul"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    
    # Database
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "ucuz_bilet.db")
    
    # Notification API Keys (Opsiyonel / Çevre Değişkenleri)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    
    # Scheduler Interval (Saat cinsinden varsayılan kontrol periyodu)
    PRICE_CHECK_INTERVAL_HOURS: int = 2

settings = Settings()
