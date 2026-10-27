import os
from dotenv import load_dotenv

load_dotenv()
from pydantic_settings import BaseSettings

class Settings:
    APP_NAME: str = "Hakiki Bilet"
    APP_SLOGAN: str = "Hakiki Fiyat, Hakiki Bilet"
    APP_DOMAIN: str = "hakikibilet.com"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    PORT: int = int(os.getenv("PORT", "8143"))
    HOST: str = os.getenv("HOST", "127.0.0.1")
    
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

    # Affiliate / Gelir Ortaklığı Kodları (GelirOrtakları & Travelpayouts & Obilet & Bilet.com & Yolcu360)
    AFFILIATE_ENUYGUN_SUBID: str = os.getenv("AFFILIATE_ENUYGUN_SUBID", "hakikibilet")
    AFFILIATE_OBILET_SUBID: str = os.getenv("AFFILIATE_OBILET_SUBID", "hakikibilet")
    AFFILIATE_YOLCU360_SUBID: str = os.getenv("AFFILIATE_YOLCU360_SUBID", "hakikibilet")
    AFFILIATE_BILETCOM_SUBID: str = os.getenv("AFFILIATE_BILETCOM_SUBID", "hakikibilet")
    AFFILIATE_GARENTA_SUBID: str = os.getenv("AFFILIATE_GARENTA_SUBID", "hakikibilet")
    AFFILIATE_AVIS_SUBID: str = os.getenv("AFFILIATE_AVIS_SUBID", "hakikibilet")
    AFFILIATE_TRAVELPAYOUTS_MARKER: str = os.getenv("AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
    AFFILIATE_FERRY_SUBID: str = os.getenv("AFFILIATE_FERRY_SUBID", "hakikibilet")
    AFFILIATE_BOOKING_AID: str = os.getenv("AFFILIATE_BOOKING_AID", "585474")
    AFFILIATE_AGODA_CID: str = os.getenv("AFFILIATE_AGODA_CID", "hakikibilet")
    AFFILIATE_TRIP_ALLIANCE_ID: str = os.getenv("AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
    AFFILIATE_TRIP_SID: str = os.getenv("AFFILIATE_TRIP_SID", "333747492")
    AFFILIATE_AWIN_PUBLISHER_ID: str = os.getenv("AFFILIATE_AWIN_PUBLISHER_ID", "3132253")
    AFFILIATE_FLIXBUS_AWIN_MID: str = os.getenv("AFFILIATE_FLIXBUS_AWIN_MID", "")

    # Çift Kademeli (Dual-Mode) Şemsiye Ağ Sarmalayıcıları (GelirOrtakları / Admitad / Travelpayouts)
    # İleride şemsiye ağ yönlendirme linki kullanılmak istendiğinde sadece bu ortam değişkenleri doldurulur.
    AFFILIATE_WRAPPER_YOLCU360: str = os.getenv("AFFILIATE_WRAPPER_YOLCU360", "")
    AFFILIATE_WRAPPER_ENUYGUN: str = os.getenv("AFFILIATE_WRAPPER_ENUYGUN", "")
    AFFILIATE_WRAPPER_OBILET: str = os.getenv("AFFILIATE_WRAPPER_OBILET", "")
    AFFILIATE_WRAPPER_BILETCOM: str = os.getenv("AFFILIATE_WRAPPER_BILETCOM", "")

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
            "domestic_rate": float(os.getenv("COMM_KIWI_DOMESTIC_RATE", "3.0")),
            "international_rate": float(os.getenv("COMM_KIWI_INTL_RATE", "3.0")),
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
            "active_affiliate": os.getenv("COMM_OBILET_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_OBILET_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_OBILET_DOMESTIC_RATE", "4.5")),
            "international_rate": float(os.getenv("COMM_OBILET_INTL_RATE", "5.5")),
            "ferry_rate": float(os.getenv("COMM_OBILET_FERRY_RATE", "5.5")),
            "fixed_try": float(os.getenv("COMM_OBILET_FIXED_TRY", "0.0")),
            "tie_breaker_rank": int(os.getenv("COMM_OBILET_RANK", "95")),
        },
        "feribotlines": {
            "name": "Feribotlines",
            "active_affiliate": os.getenv("COMM_FERIBOTLINES_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_FERIBOTLINES_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_FERIBOTLINES_DOMESTIC_RATE", "5.0")),
            "international_rate": float(os.getenv("COMM_FERIBOTLINES_INTL_RATE", "6.5")),
            "ferry_rate": float(os.getenv("COMM_FERIBOTLINES_FERRY_RATE", "6.5")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_FERIBOTLINES_RANK", "90")),
        },
        "biletcom": {
            "name": "Bilet.com",
            "active_affiliate": os.getenv("COMM_BILETCOM_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": os.getenv("COMM_BILETCOM_MODEL", "percentage"),
            "domestic_rate": float(os.getenv("COMM_BILETCOM_DOMESTIC_RATE", "3.5")),
            "international_rate": float(os.getenv("COMM_BILETCOM_INTL_RATE", "4.5")),
            "ferry_rate": float(os.getenv("COMM_BILETCOM_FERRY_RATE", "4.5")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_BILETCOM_RANK", "85")),
        },
        "ferryhopper": {
            "name": "Ferryhopper",
            "active_affiliate": os.getenv("COMM_FERRYHOPPER_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": 3.5,
            "international_rate": 4.0,
            "ferry_rate": 4.0,
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_FERRYHOPPER_RANK", "80")),
        },
        "setur_cruise": {
            "name": "Setur Cruise",
            "active_affiliate": os.getenv("COMM_SETUR_CRUISE_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": 4.5,
            "international_rate": 4.5,
            "cruise_rate": 4.5,
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_SETUR_CRUISE_RANK", "92")),
        },
        "jolly_cruise": {
            "name": "Jolly Tur Gemi",
            "active_affiliate": os.getenv("COMM_JOLLY_CRUISE_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": 4.0,
            "international_rate": 4.0,
            "cruise_rate": 4.0,
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_JOLLY_CRUISE_RANK", "88")),
        },
        "cruisedirect": {
            "name": "CruiseDirect",
            "active_affiliate": os.getenv("COMM_CRUISEDIRECT_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": 3.0,
            "international_rate": 3.0,
            "cruise_rate": 3.0,
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_CRUISEDIRECT_RANK", "82")),
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
        "yolcu360": {
            "name": "Yolcu360",
            "active_affiliate": os.getenv("COMM_YOLCU360_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": float(os.getenv("COMM_YOLCU360_RATE", "6.0")),
            "international_rate": float(os.getenv("COMM_YOLCU360_RATE", "6.0")),
            "car_rate": float(os.getenv("COMM_YOLCU360_RATE", "6.0")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_YOLCU360_RANK", "96")),
        },
        "rentalcars": {
            "name": "Rentalcars (Booking.com)",
            "active_affiliate": os.getenv("COMM_RENTALCARS_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": float(os.getenv("COMM_RENTALCARS_RATE", "5.5")),
            "international_rate": float(os.getenv("COMM_RENTALCARS_RATE", "5.5")),
            "car_rate": float(os.getenv("COMM_RENTALCARS_RATE", "5.5")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_RENTALCARS_RANK", "86")),
        },
        "welcomepickups": {
            "name": "Welcome Pickups",
            "active_affiliate": os.getenv("COMM_WELCOMEPICKUPS_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": float(os.getenv("COMM_WELCOMEPICKUPS_RATE", "8.0")),
            "international_rate": float(os.getenv("COMM_WELCOMEPICKUPS_RATE", "8.0")),
            "transfer_rate": float(os.getenv("COMM_WELCOMEPICKUPS_RATE", "8.0")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_WELCOMEPICKUPS_RANK", "89")),
        },
        "garenta": {
            "name": "Garenta",
            "active_affiliate": os.getenv("COMM_GARENTA_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": float(os.getenv("COMM_GARENTA_RATE", "4.0")),
            "international_rate": float(os.getenv("COMM_GARENTA_RATE", "4.0")),
            "car_rate": float(os.getenv("COMM_GARENTA_RATE", "4.0")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_GARENTA_RANK", "78")),
        },
        "avis": {
            "name": "Avis Türkiye",
            "active_affiliate": os.getenv("COMM_AVIS_ACTIVE", "true").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": float(os.getenv("COMM_AVIS_RATE", "4.0")),
            "international_rate": float(os.getenv("COMM_AVIS_RATE", "4.0")),
            "car_rate": float(os.getenv("COMM_AVIS_RATE", "4.0")),
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_AVIS_RANK", "76")),
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
        "skyscanner": {
            "name": "Skyscanner",
            "active_affiliate": os.getenv("COMM_SKYSCANNER_ACTIVE", "false").lower() in ("true", "1", "yes"),
            "model": "percentage",
            "domestic_rate": 0.0,
            "international_rate": 0.0,
            "fixed_try": 0.0,
            "tie_breaker_rank": int(os.getenv("COMM_SKYSCANNER_RANK", "60")),
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

    # RapidAPI Booking.com Canlı Otel & Uçuş Entegrasyonu
    RAPIDAPI_BOOKING_KEY: str = os.getenv("RAPIDAPI_BOOKING_KEY", "")
    RAPIDAPI_BOOKING_HOST: str = os.getenv("RAPIDAPI_BOOKING_HOST", "booking-com15.p.rapidapi.com")

    # Hibrit Çoklu Acente (Multi-OTA) Canlı Uçuş Fiyat Entegrasyonları (Faz 1B)
    RAPIDAPI_FLIGHTS_KEY: str = os.getenv("RAPIDAPI_FLIGHTS_KEY", "")
    RAPIDAPI_FLIGHTS_HOST: str = os.getenv("RAPIDAPI_FLIGHTS_HOST", "sky-scrapper.p.rapidapi.com")
    TRAVELPAYOUTS_API_TOKEN: str = os.getenv("TRAVELPAYOUTS_API_TOKEN", "")
    KIWI_AFFILIATE_ID: str = os.getenv("KIWI_AFFILIATE_ID", "travelpayouts")
    # Hukuki Yasal Metinler & TÜRSAB Muafiyeti (Metasearch / Karşılaştırma Beyanı)
    LEGAL_DISCLAIMER: str = (
        "Hakiki Bilet (hakikibilet.com) bağımsız bir seyahat ve etkinlik bilet fiyat karşılaştırma ve yönlendirme platformudur. "
        "Hakiki Bilet doğrudan bilet satışı yapmaz, ödeme tahsil etmez. Satın alma, rezervasyon ve biletleme "
        "işlemleri kullanıcının yönlendirildiği yetkili acente veya resmi taşıyıcı firmanın güvenli altyapısında tamamlanır."
    )

    # Bakım / Lansman Öncesi Modu (Canlı açık; istendiğinde Render ortam değişkeninden 'true' yapılabilir)
    MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "false").lower() in ("true", "1", "yes")
    MAINTENANCE_BYPASS_KEY: str = os.getenv("MAINTENANCE_BYPASS_KEY", "hakiki2026")

    # 🔌 ŞALTER PANELİ: Gelecek Modüller ve Yedek Priz Boşlukları (Plug-and-Play Extension Slots)
    # Mevcut çalışan sistemi hiç bozmadan ileride tek şalterle ('enabled': True) devreye alınabilecek hazır yuvalar.
    EXTENSION_SLOTS: dict = {
        "ancillary_slots": {
            "enabled": os.getenv("SLOT_ANCILLARY_ENABLED", "false").lower() in ("true", "1", "yes"),
            "esim_partner_url": os.getenv("PARTNER_ESIM_URL", ""),
            "insurance_partner_url": os.getenv("PARTNER_INSURANCE_URL", ""),
            "flight_compensation_url": os.getenv("PARTNER_COMPENSATION_URL", ""),
            "lounge_parking_url": os.getenv("PARTNER_LOUNGE_URL", ""),
        },
        "experience_slots": {
            "enabled": os.getenv("SLOT_EXPERIENCE_ENABLED", "false").lower() in ("true", "1", "yes"),
            "tours_partner_url": os.getenv("PARTNER_TOURS_URL", ""),
        },
        "sponsored_slots": {
            "enabled": os.getenv("SLOT_SPONSORED_ENABLED", "false").lower() in ("true", "1", "yes"),
            "items": [],
        },
        "user_hub_slot": {
            "enabled": os.getenv("SLOT_USER_HUB_ENABLED", "false").lower() in ("true", "1", "yes"),
        },
        "smart_route_wizard": {
            "enabled": os.getenv("SLOT_SMART_ROUTE_ENABLED", "true").lower() in ("true", "1", "yes"),
        },
        "price_ribbon_7d": {
            "enabled": os.getenv("SLOT_PRICE_RIBBON_ENABLED", "true").lower() in ("true", "1", "yes"),
        },
        "city_guide_gems": {
            "enabled": os.getenv("SLOT_CITY_GUIDE_ENABLED", "true").lower() in ("true", "1", "yes"),
        },
        "mobile_whatsapp_gateway": {
            "enabled": True,
            "api_version": "1.0",
        },
        "custom_extension_blocks": [],
    }

settings = Settings()

