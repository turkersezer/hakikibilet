import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings
from app.services.currency_service import CurrencyService

class HotelService:
    """
    MODÜL: Akıllı Otel ve Konaklama Metasearch Servisi (Seçenek A - Hafif & Risksiz Model)
    Kullanıcının seyahat tarihlerini, varış şehrini ve kişi sayısını otomatik alarak
    Booking.com, Enuygun Otel ve Agoda'ya parametrik deep linkler ve şehir bazlı bütçe özetleri üretir.
    İleride canlı Otel API'sine (Seçenek B) geçildiğinde arayüzü bozmadan doğrudan bağlanabilecek modüler mimariye sahiptir.
    """

    # Şehir bazlı ortalama gecelik taban ve tavan piyasa göstergeleri (TRY bazında referans)
    CITY_HOTEL_PROFILES = {
        "paris": {"min_try": 2200, "max_try": 5500, "label": "Fransa / Paris Metropolü"},
        "roma": {"min_try": 1800, "max_try": 4200, "label": "İtalya / Roma Tarihi Merkez"},
        "milano": {"min_try": 1900, "max_try": 4500, "label": "İtalya / Milano Merkez"},
        "londra": {"min_try": 2500, "max_try": 6200, "label": "İngiltere / Londra Merkez"},
        "new-york": {"min_try": 3500, "max_try": 8500, "label": "ABD / New York (Manhattan/Brooklyn)"},
        "berlin": {"min_try": 1600, "max_try": 3800, "label": "Almanya / Berlin Mitte"},
        "amsterdam": {"min_try": 2400, "max_try": 5600, "label": "Hollanda / Amsterdam Merkez"},
        "viyana": {"min_try": 1700, "max_try": 3900, "label": "Avusturya / Viyana Merkez"},
        "prag": {"min_try": 1200, "max_try": 2900, "label": "Çekya / Prag Eski Şehir"},
        "budapeste": {"min_try": 1100, "max_try": 2700, "label": "Macaristan / Budapeşte Tuna Kıyısı"},
        "barselona": {"min_try": 1800, "max_try": 4300, "label": "İspanya / Barselona Sahil & Merkez"},
        "madrid": {"min_try": 1700, "max_try": 3900, "label": "İspanya / Madrid Merkez"},
        "sakiz-adasi": {"min_try": 1300, "max_try": 2800, "label": "Yunanistan / Sakız Adası Liman"},
        "kos-adasi": {"min_try": 1400, "max_try": 3100, "label": "Yunanistan / Kos Adası"},
        "midilli-adasi": {"min_try": 1300, "max_try": 2900, "label": "Yunanistan / Midilli Liman"},
        "rodos-adasi": {"min_try": 1500, "max_try": 3400, "label": "Yunanistan / Rodos Eski Şehir"},
        "selanik": {"min_try": 1200, "max_try": 2700, "label": "Yunanistan / Selanik Kordon"},
        "atina": {"min_try": 1300, "max_try": 3100, "label": "Yunanistan / Atina Akropolis Çevresi"},
        "sofya": {"min_try": 1100, "max_try": 2500, "label": "Bulgaristan / Sofya Merkez"},
        "batum": {"min_try": 1000, "max_try": 2400, "label": "Gürcistan / Batum Sahil"},
        "antalya": {"min_try": 1100, "max_try": 3500, "label": "Türkiye / Antalya & Kaleiçi"},
        "istanbul": {"min_try": 1100, "max_try": 3200, "label": "Türkiye / İstanbul Tarihi Yarımada & Boğaz"},
        "izmir": {"min_try": 1200, "max_try": 3000, "label": "Türkiye / İzmir Kordon & Alsancak"},
        "bodrum": {"min_try": 1800, "max_try": 4800, "label": "Türkiye / Bodrum Yarımadası"},
        "nevsehir": {"min_try": 1400, "max_try": 3900, "label": "Türkiye / Kapadokya Mağara Otelleri"},
        "trabzon": {"min_try": 1000, "max_try": 2500, "label": "Türkiye / Trabzon & Yaylalar"},
        "kars": {"min_try": 900, "max_try": 2200, "label": "Türkiye / Kars Merkez (Tarihi Taş Oteller)"}
    }

    @staticmethod
    def calculate_dates(checkin_str: str, checkout_str: Optional[str] = None, default_nights: int = 3):
        try:
            cin_dt = datetime.strptime(checkin_str, "%Y-%m-%d")
        except Exception:
            cin_dt = datetime.now() + timedelta(days=7)

        if checkout_str:
            try:
                cout_dt = datetime.strptime(checkout_str, "%Y-%m-%d")
                if cout_dt <= cin_dt:
                    cout_dt = cin_dt + timedelta(days=default_nights)
            except Exception:
                cout_dt = cin_dt + timedelta(days=default_nights)
        else:
            cout_dt = cin_dt + timedelta(days=default_nights)

        nights = max(1, (cout_dt - cin_dt).days)
        return cin_dt.strftime("%Y-%m-%d"), cout_dt.strftime("%Y-%m-%d"), nights

    @classmethod
    def get_hotel_recommendation(
        cls,
        dest_city: str,
        checkin_date: str,
        checkout_date: Optional[str] = None,
        guests: int = 1,
        currency: str = "TRY"
    ) -> Dict[str, Any]:
        """
        Varış şehri ve tarihler için hazır parametreli Booking.com, Enuygun ve Agoda bağlantıları üretir.
        """
        cin, cout, nights = cls.calculate_dates(checkin_date, checkout_date)
        city_clean = dest_city.split("(")[0].strip()
        city_slug = city_clean.lower().replace(" ", "-").replace("ı", "i").replace("ç", "c").replace("ş", "s").replace("ö", "o").replace("ü", "u").replace("ğ", "g")
        
        # Enuygun tarih formatı (DD.MM.YYYY)
        try:
            cin_dt = datetime.strptime(cin, "%Y-%m-%d")
            cout_dt = datetime.strptime(cout, "%Y-%m-%d")
            enuygun_cin = cin_dt.strftime("%d.%m.%Y")
            enuygun_cout = cout_dt.strftime("%d.%m.%Y")
        except Exception:
            enuygun_cin = cin
            enuygun_cout = cout

        # Booking.com Derin Bağlantısı (Tarihler, Şehir, Kişi Sayısı & Affiliate ID hazır)
        booking_url = (
            f"https://www.booking.com/searchresults.tr.html?"
            f"ss={urllib.parse.quote(city_clean)}"
            f"&checkin={cin}&checkout={cout}"
            f"&group_adults={guests}&no_rooms=1&group_children=0"
            f"&aid={settings.AFFILIATE_BOOKING_AID}"
        )

        # Enuygun Otel Derin Bağlantısı
        enuygun_url = (
            f"https://www.enuygun.com/otel/arama/{city_slug}/?"
            f"giris={enuygun_cin}&cikis={enuygun_cout}&yetiskin={guests}"
        )

        # Agoda Derin Bağlantısı
        agoda_url = (
            f"https://www.agoda.com/tr-tr/search?"
            f"city={urllib.parse.quote(city_clean)}"
            f"&checkIn={cin}&checkOut={cout}&rooms=1&adults={guests}"
            f"&cid={settings.AFFILIATE_AGODA_CID}"
        )

        # Fiyat profili (TRY bazlı başlangıç, para birimi dönüşümü uygulanır)
        profile = cls.CITY_HOTEL_PROFILES.get(city_slug, {"min_try": 1200, "max_try": 3000, "label": f"{city_clean} Merkez"})
        
        currency = (currency or "TRY").upper()
        curr_sym = CurrencyService.get_symbol(currency)
        
        min_rate = CurrencyService.convert(profile["min_try"], "TRY", currency)
        max_rate = CurrencyService.convert(profile["max_try"], "TRY", currency)

        total_min = min_rate * nights
        total_max = max_rate * nights

        return {
            "destination": city_clean,
            "region_label": profile["label"],
            "checkin_date": cin,
            "checkout_date": cout,
            "nights": nights,
            "guests": guests,
            "currency": curr_sym,
            "currency_code": currency,
            "avg_nightly_min": round(min_rate, 2),
            "avg_nightly_max": round(max_rate, 2),
            "total_stay_min": round(total_min, 2),
            "total_stay_max": round(total_max, 2),
            "deep_links": {
                "booking": booking_url,
                "enuygun": enuygun_url,
                "agoda": agoda_url
            },
            "categories": [
                {
                    "title": "🌟 Bütçe Dostu & Hostel / 3 Yıldız",
                    "badge": "Ekonomik Seçim",
                    "badge_color": "emerald",
                    "desc": "Merkezi konumda, temiz ve gezginler için ideal ekonomik oteller.",
                    "est_nightly": round(min_rate, 2),
                    "est_total": round(total_min, 2),
                    "action_text": "Booking'de Ekonomik Odaları Gör ↗",
                    "link": booking_url
                },
                {
                    "title": "🏨 Şehir Merkezi & 4 Yıldız Konfor",
                    "badge": "En Çok Tercih Edilen",
                    "badge_color": "blue",
                    "desc": "Turistik noktalara ve metroya yürüme mesafesinde, zengin kahvaltılı oteller.",
                    "est_nightly": round((min_rate + max_rate) / 2, 2),
                    "est_total": round(((min_rate + max_rate) / 2) * nights, 2),
                    "action_text": "Booking'de 4 Yıldızlı Otelleri Gör ↗",
                    "link": booking_url
                },
                {
                    "title": "💎 Butik & 5 Yıldız Premium Seçenek",
                    "badge": "Üst Düzey Konfor",
                    "badge_color": "purple",
                    "desc": "Tarihi binalarda butik konsept, spa ve premium hizmet sunan oteller.",
                    "est_nightly": round(max_rate * 1.3, 2),
                    "est_total": round(max_rate * 1.3 * nights, 2),
                    "action_text": "Enuygun & Booking'de İncele ↗",
                    "link": enuygun_url
                }
            ],
            "disclaimer": "Oda ve kesin fiyatlar anlık doluluk ve oda tipine göre doğrudan sağlayıcı sisteminde teyit edilir."
        }
