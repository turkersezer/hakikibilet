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
    RESEND_AUDIENCE_ID: str = os.getenv("RESEND_AUDIENCE_ID", "71f5c278-1caf-4326-a47c-112796f8dbbf")
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

    # Merkezi Gelir Modeli ve Komisyon Oranları Tablosu
    # İleride yeni ortaklıklar onaylandığında veya komisyon oranları değiştiğinde
    # tek bir noktadan (veya Render ortam değişkenlerinden) tüm site genelinde güncellenir.
    PARTNER_COMMISSION_RULES: dict = {
        "trip": {
            "name": "Trip.com",
            "active_affiliate": os.getenv("COMM_TRIP_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_TRIP_MODEL", "percentage"),  # 'percentage' | 'fixed_try'
            "domestic_rate": float(os.getenv("COMM_TRIP_DOMESTIC_RATE", "1.5")),      # %1.5
            "international_rate": float(os.getenv("COMM_TRIP_INTL_RATE", "2.0")),     # %2.0
            "hotel_rate": float(os.getenv("COMM_TRIP_HOTEL_RATE", "5.5")),            # %5.5
            "fixed_try": float(os.getenv("COMM_TRIP_FIXED_TRY", "0.0")),
            "tie_breaker_rank": int(os.getenv("COMM_TRIP_RANK", "100")),
        },
        "kiwi": {
            "name": "Kiwi.com (Travelpayouts)",
            "active_affiliate": os.getenv("COMM_KIWI_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_KIWI_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_KIWI_DOMESTIC_RATE", "1.2")),
            "international_rate": float(os.getenv("COMM_KIWI_INTL_RATE", "1.5")),
            "fixed_try": float(os.getenv("COMM_KIWI_FIXED_TRY", "0.0")),
            "tie_breaker_rank": int(os.getenv("COMM_KIWI_RANK", "85")),
        },
        "agency": {
            "name": "Enuygun",
            "active_affiliate": os.getenv("COMM_ENUYGUN_ACTIVE", "false").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_ENUYGUN_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_ENUYGUN_DOMESTIC_RATE", "1.8")),
            "international_rate": float(os.getenv("COMM_ENUYGUN_INTL_RATE", "2.2")),
            "fixed_try": float(os.getenv("COMM_ENUYGUN_FIXED_TRY", "0.0")),
            "tie_breaker_rank": int(os.getenv("COMM_ENUYGUN_RANK", "70")),
        },
        "obilet": {
            "name": "Obilet",
            "active_affiliate": os.getenv("COMM_OBILET_ACTIVE", "false").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_OBILET_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_OBILET_DOMESTIC_RATE", "2.0")),
            "international_rate": float(os.getenv("COMM_OBILET_INTL_RATE", "2.5")),
            "fixed_try": float(os.getenv("COMM_OBILET_FIXED_TRY", "0.0")),
            "tie_breaker_rank": int(os.getenv("COMM_OBILET_RANK", "75")),
        },
        "booking": {
            "name": "Booking.com",
            "active_affiliate": os.getenv("COMM_BOOKING_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_BOOKING_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_BOOKING_DOMESTIC_RATE", "4.0")),
            "international_rate": float(os.getenv("COMM_BOOKING_INTL_RATE", "4.0")),
            "hotel_rate": float(os.getenv("COMM_BOOKING_HOTEL_RATE", "4.0")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_BOOKING_RANK", "80")),
        },
        "bubilet": {
            "name": "Bubilet",
            "active_affiliate": os.getenv("COMM_BUBILET_ACTIVE", "false").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_BUBILET_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_BUBILET_RATE", "3.5")),
            "international_rate": float(os.getenv("COMM_BUBILET_RATE", "3.5")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_BUBILET_RANK", "65")),
        },
        "official": {
            "name": "Resmi Taşıyıcı / Havayolu",
            "active_affiliate": False,
            "model": "percentage",
            "domestic_rate": 0.0,
            "international_rate": 0.0,
            "fixed_try": 0.0,
            "tie_breaker_rank": 10,
        },
        "meta": {
            "name": "Karşılaştırma / Meta",
            "active_affiliate": False,
            "model": "percentage",
            "domestic_rate": 0.0,
            "international_rate": 0.0,
            "fixed_try": 0.0,
            "tie_breaker_rank": 5,
        },
    }

    # RapidAPI Booking.com Canlı Otel Entegrasyonu
    RAPIDAPI_BOOKING_KEY: str = os.getenv("RAPIDAPI_BOOKING_KEY", "148a35e0b3msh6fee0694743036ap1fba10jsn5361646b970c")
    RAPIDAPI_BOOKING_HOST: str = os.getenv("RAPIDAPI_BOOKING_HOST", "apidojo-booking-v1.p.rapidapi.com")

    # Hibrit Çoklu Acente (Multi-OTA) Canlı Uçuş Fiyat Entegrasyonları (Faz 1B)
    RAPIDAPI_FLIGHTS_KEY: str = os.getenv("RAPIDAPI_FLIGHTS_KEY", os.getenv("RAPIDAPI_BOOKING_KEY", "148a35e0b3msh6fee0694743036ap1fba10jsn5361646b970c"))
    RAPIDAPI_FLIGHTS_HOST: str = os.getenv("RAPIDAPI_FLIGHTS_HOST", "google-flights2.p.rapidapi.com")
    TRAVELPAYOUTS_API_TOKEN: str = os.getenv("TRAVELPAYOUTS_API_TOKEN", "")
    KIWI_AFFILIATE_ID: str = os.getenv("KIWI_AFFILIATE_ID", "hakikibilet")
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
