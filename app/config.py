import os
from dotenv import load_dotenv

load_dotenv()
from pydantic_settings import BaseSettings

class Settings:
    APP_NAME: str = "Hakiki Bilet"
    APP_SLOGAN: str = "Hakiki Fiyat, Hakiki Bilet"
    APP_DOMAIN: str = "hakikibilet.com"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8143
    HOST: str = "127.0.0.1"
    
    # Database
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "ucuz_bilet.db")
    
    # Notification API Keys & Kurumsal E-posta Ayarları
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "Hakiki Bilet <info@hakikibilet.com>")
    RESEND_REPLY_TO: str = os.getenv("RESEND_REPLY_TO", "hakikibilet@gmail.com")
    ADMIN_NOTIFICATION_EMAIL: str = os.getenv("ADMIN_NOTIFICATION_EMAIL", "hakikibilet@gmail.com")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    
    # Scheduler Interval (Saat cinsinden varsayılan kontrol periyodu)
    PRICE_CHECK_INTERVAL_HOURS: int = 2

    # Affiliate / Gelir Ortaklığı Kodları (GelirOrtakları & Travelpayouts & Obilet)
    AFFILIATE_ENUYGUN_SUBID: str = os.getenv("AFFILIATE_ENUYGUN_SUBID", "hakikibilet")
    AFFILIATE_OBILET_SUBID: str = os.getenv("AFFILIATE_OBILET_SUBID", "hakikibilet")
    AFFILIATE_YOLCU360_SUBID: str = os.getenv("AFFILIATE_YOLCU360_SUBID", "hakikibilet")
    AFFILIATE_TRAVELPAYOUTS_MARKER: str = os.getenv("AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
    AFFILIATE_FERRY_SUBID: str = os.getenv("AFFILIATE_FERRY_SUBID", "hakikibilet")
    AFFILIATE_BOOKING_AID: str = os.getenv("AFFILIATE_BOOKING_AID", "585474")
    AFFILIATE_AGODA_CID: str = os.getenv("AFFILIATE_AGODA_CID", "hakikibilet")
    AFFILIATE_TRIP_ALLIANCE_ID: str = os.getenv("AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
    AFFILIATE_TRIP_SID: str = os.getenv("AFFILIATE_TRIP_SID", "333747492")

    # RapidAPI Booking.com Canlı Otel Entegrasyonu
    RAPIDAPI_BOOKING_KEY: str = os.getenv("RAPIDAPI_BOOKING_KEY", "148a35e0b3msh6fee0694743036ap1fba10jsn5361646b970c")
    RAPIDAPI_BOOKING_HOST: str = os.getenv("RAPIDAPI_BOOKING_HOST", "apidojo-booking-v1.p.rapidapi.com")
    # Hukuki Yasal Metinler & TÜRSAB Muafiyeti (Metasearch / Karşılaştırma Beyanı)
    LEGAL_DISCLAIMER: str = (
        "Hakiki Bilet (hakikibilet.com) bağımsız bir seyahat ve etkinlik bilet fiyat karşılaştırma ve yönlendirme platformudur. "
        "Hakiki Bilet doğrudan bilet satışı yapmaz, ödeme tahsil etmez. Satın alma, rezervasyon ve biletleme "
        "işlemleri kullanıcının yönlendirildiği yetkili acente veya resmi taşıyıcı firmanın güvenli altyapısında tamamlanır."
    )

    # Bakım / Lansman Öncesi Modu (Canlı açık beta; istendiğinde Render ortam değişkeninden 'true' yapılabilir)
    MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "true").lower() in ("true", "1", "yes")
    MAINTENANCE_BYPASS_KEY: str = os.getenv("MAINTENANCE_BYPASS_KEY", "hakiki2026")

settings = Settings()
