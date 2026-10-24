import urllib.parse
import urllib.request
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from app.config import settings
from app.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

class HotelService:
    """
    MODÜL: Akıllı Canlı Otel ve Konaklama Metasearch Servisi
    - RapidAPI Booking.com Canlı Veri Motoru (Gerçek otel adları, puanlar, HD fotoğraflar ve canlı fiyatlar)
    - 2 Saatlik Akıllı Önbellek (Kota tasarrufu ve ultra hızlı yanıt)
    - Yurt dışı / Ada güvenliği (Enuygun 404 hatasını önlemek için adalarda ve yurt dışında sadece Booking & Agoda)
    - Hatasız Yedekleme (API erişilemezse kesintisiz parametrik Booking.com yönlendirmesi)
    """

    # Canlı sorgu önbelleği: {cache_key: (timestamp, data)}
    _HOTEL_CACHE: Dict[str, tuple] = {}
    _CACHE_TTL = 7200  # 2 saat

    # Popüler destinasyonların önceden haritalandırılmış Booking.com bölge ve şehir ID'leri
    DEST_ID_MAP = {
        "sakiz-adasi": {"dest_id": "2810", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Sakız Adası (Chios)"},
        "chios": {"dest_id": "2810", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Sakız Adası (Chios)"},
        "rodos-adasi": {"dest_id": "2668", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Rodos Eski Şehir"},
        "rodos": {"dest_id": "2668", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Rodos"},
        "midilli-adasi": {"dest_id": "2811", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Midilli (Lesbos)"},
        "midilli": {"dest_id": "2811", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Midilli"},
        "kos-adasi": {"dest_id": "2665", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Kos Adası"},
        "kos": {"dest_id": "2665", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Kos"},
        "paris": {"dest_id": "-1456928", "dest_type": "city", "is_intl": True, "label": "Fransa / Paris"},
        "roma": {"dest_id": "-126693", "dest_type": "city", "is_intl": True, "label": "İtalya / Roma"},
        "munih": {"dest_id": "-1829149", "dest_type": "city", "is_intl": True, "label": "Almanya / Münih"},
        "viyana": {"dest_id": "-1995499", "dest_type": "city", "is_intl": True, "label": "Avusturya / Viyana"},
        "londra": {"dest_id": "-2601889", "dest_type": "city", "is_intl": True, "label": "İngiltere / Londra"},
        "venedik": {"dest_id": "-132007", "dest_type": "city", "is_intl": True, "label": "İtalya / Venedik"},
        "tokyo": {"dest_id": "-246227", "dest_type": "city", "is_intl": True, "label": "Japonya / Tokyo"},
        "kyoto": {"dest_id": "-235553", "dest_type": "city", "is_intl": True, "label": "Japonya / Kyoto"},
        "new-york": {"dest_id": "20088325", "dest_type": "city", "is_intl": True, "label": "ABD / New York"},
        "nice": {"dest_id": "-1454984", "dest_type": "city", "is_intl": True, "label": "Fransa / Nice & Côte d'Azur"},
        "monaco": {"dest_id": "-1454984", "dest_type": "city", "is_intl": True, "label": "Monaco / Monte Carlo & Nice Sahili"},
        "baku": {"dest_id": "-2417770", "dest_type": "city", "is_intl": True, "label": "Azerbaycan / Bakü Sahil & İçeri Şehir"},
        "ankara": {"dest_id": "-735340", "dest_type": "city", "is_intl": False, "label": "Türkiye / Ankara & Kızılay"},
        "antalya": {"dest_id": "-735346", "dest_type": "city", "is_intl": False, "label": "Türkiye / Antalya & Kaleiçi"},
        "istanbul": {"dest_id": "-755070", "dest_type": "city", "is_intl": False, "label": "Türkiye / İstanbul"},
        "izmir": {"dest_id": "-754964", "dest_type": "city", "is_intl": False, "label": "Türkiye / İzmir"},
        "bodrum": {"dest_id": "-739775", "dest_type": "city", "is_intl": False, "label": "Türkiye / Bodrum"},
        "adana": {"dest_id": "-733575", "dest_type": "city", "is_intl": False, "label": "Türkiye / Adana"},
        "nevsehir": {"dest_id": "-766579", "dest_type": "city", "is_intl": False, "label": "Türkiye / Kapadokya"},
        "balikesir": {"dest_id": "-737225", "dest_type": "city", "is_intl": False, "label": "Türkiye / Balıkesir & Körfez"}
    }

    # Yedek referans piyasa fiyat profilleri (TRY bazında)
    CITY_HOTEL_PROFILES = {
        "paris": {"min_try": 2200, "max_try": 5500, "label": "Fransa / Paris Metropolü"},
        "nice": {"min_try": 2400, "max_try": 6200, "label": "Fransa / Nice & Côte d'Azur"},
        "monaco": {"min_try": 3500, "max_try": 9000, "label": "Monaco / Monte Carlo & Nice Sahili"},
        "baku": {"min_try": 1400, "max_try": 3800, "label": "Azerbaycan / Bakü Sahil"},
        "ankara": {"min_try": 1200, "max_try": 3100, "label": "Türkiye / Ankara & Çankaya"},
        "roma": {"min_try": 1800, "max_try": 4200, "label": "İtalya / Roma Tarihi Merkez"},
        "milano": {"min_try": 1900, "max_try": 4500, "label": "İtalya / Milano Merkez"},
        "venedik": {"min_try": 1800, "max_try": 4400, "label": "İtalya / Venedik & San Marco"},
        "munih": {"min_try": 1900, "max_try": 4500, "label": "Almanya / Münih & Bavyera"},
        "londra": {"min_try": 2500, "max_try": 6200, "label": "İngiltere / Londra Merkez"},
        "new-york": {"min_try": 3500, "max_try": 8500, "label": "ABD / New York"},
        "viyana": {"min_try": 1700, "max_try": 3900, "label": "Avusturya / Viyana Merkez"},
        "sakiz-adasi": {"min_try": 1300, "max_try": 2800, "label": "Yunanistan / Sakız Adası Liman"},
        "kos-adasi": {"min_try": 1400, "max_try": 3100, "label": "Yunanistan / Kos Adası"},
        "midilli-adasi": {"min_try": 1300, "max_try": 2900, "label": "Yunanistan / Midilli Liman"},
        "rodos-adasi": {"min_try": 1500, "max_try": 3400, "label": "Yunanistan / Rodos Eski Şehir"},
        "antalya": {"min_try": 1100, "max_try": 3500, "label": "Türkiye / Antalya & Kaleiçi"},
        "istanbul": {"min_try": 1100, "max_try": 3200, "label": "Türkiye / İstanbul"},
        "izmir": {"min_try": 1200, "max_try": 3000, "label": "Türkiye / İzmir"},
        "bodrum": {"min_try": 1800, "max_try": 4800, "label": "Türkiye / Bodrum"},
        "adana": {"min_try": 1000, "max_try": 2600, "label": "Türkiye / Adana"},
        "nevsehir": {"min_try": 1400, "max_try": 3900, "label": "Türkiye / Kapadokya"},
        "balikesir": {"min_try": 1100, "max_try": 2800, "label": "Türkiye / Balıkesir & Edremit"}
    }

    @staticmethod
    def slugify_hotel_name(name: str) -> str:
        import re
        s = (name or "").lower()
        for tr_c, en_c in [
            ('ı', 'i'), ('ş', 's'), ('ç', 'c'), ('ğ', 'g'), ('ü', 'u'), ('ö', 'o'),
            ('’', ''), ("'", ""), ('"', ''), ('&', 'and'), ('.', '')
        ]:
            s = s.replace(tr_c, en_c)
        s = re.sub(r'[^a-z0-9]+', '-', s)
        return s.strip('-')

    @staticmethod
    def calculate_dates(checkin_str: str, checkout_str: Optional[str] = None, default_nights: int = 2):
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
    def fetch_live_booking_hotels(
        cls, dest_id: str, dest_type: str, cin: str, cout: str, guests: int = 1, currency: str = "TRY"
    ) -> List[Dict[str, Any]]:
        """
        RapidAPI Booking.com üzerinden gerçek otel adı, HD fotoğraf, puan ve net canlı fiyat çeker.
        Doğrudan otele ait oda seçim ekranı linki oluşturur.
        """
        api_key = getattr(settings, "RAPIDAPI_BOOKING_KEY", "")
        api_host = getattr(settings, "RAPIDAPI_BOOKING_HOST", "apidojo-booking-v1.p.rapidapi.com")
        
        if not api_key:
            return []

        cache_key = f"{dest_id}_{dest_type}_{cin}_{cout}_{guests}_{currency}"
        now_ts = time.time()
        if cache_key in cls._HOTEL_CACHE:
            ts, cached_result = cls._HOTEL_CACHE[cache_key]
            if now_ts - ts < cls._CACHE_TTL:
                return cached_result

        now_dt = datetime.now()
        try:
            req_cin_dt = datetime.strptime(cin, "%Y-%m-%d")
            if req_cin_dt.date() < now_dt.date():
                api_cin = (now_dt + timedelta(days=14)).strftime("%Y-%m-%d")
                api_cout = (now_dt + timedelta(days=17)).strftime("%Y-%m-%d")
            else:
                api_cin = cin
                api_cout = cout
        except Exception:
            api_cin = (now_dt + timedelta(days=14)).strftime("%Y-%m-%d")
            api_cout = (now_dt + timedelta(days=17)).strftime("%Y-%m-%d")

        try:
            params = {
                "dest_ids": str(dest_id),
                "search_type": dest_type,
                "arrival_date": api_cin,
                "departure_date": api_cout,
                "adults": str(guests),
                "room_qty": "1",
                "currency_code": currency,
                "units": "metric",
                "languagecode": "tr"
            }
            url = f"https://{api_host}/properties/v2/list?" + urllib.parse.urlencode(params)
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": api_host,
                "User-Agent": "HakikiBilet/1.0"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                raw_hotels = [h for h in payload.get("result", []) if "hotel_name" in h]

                live_list = []
                for h in raw_hotels[:6]:
                    name = h.get("hotel_name")
                    score = h.get("review_score")
                    score_word = h.get("review_score_word", "İyi")
                    photo_raw = h.get("main_photo_url", "")
                    photo_hd = photo_raw.replace("square60", "max500") if photo_raw else ""
                    
                    cpb = h.get("composite_price_breakdown", {})
                    per_night_val = cpb.get("gross_amount_per_night", {}).get("value")
                    total_val = cpb.get("gross_amount", {}).get("value")
                    curr_returned = cpb.get("gross_amount", {}).get("currency", "USD")

                    # Fiyatı hedef para birimine (TRY vb.) çevir
                    if per_night_val:
                        nightly_target = CurrencyService.convert(per_night_val, curr_returned, currency)
                        total_target = CurrencyService.convert(total_val, curr_returned, currency)
                    else:
                        min_tot = h.get("min_total_price", 0)
                        nightly_target = CurrencyService.convert(min_tot / 2, "EUR", currency) if min_tot else 0
                        total_target = CurrencyService.convert(min_tot, "EUR", currency) if min_tot else 0

                    aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
                    agoda_cid = getattr(settings, "AFFILIATE_AGODA_CID", "1924128")
                    country_code = (h.get("countrycode") or "gr").lower()
                    hotel_name = name or ""
                    hotel_city = h.get("city") or ""
                    hotel_slug = cls.slugify_hotel_name(hotel_name)
                    is_domestic = (country_code == "tr")

                    # 1. Doğrudan Booking.com Tesis Oda Rezervasyon Sayfası (.html ile temiz parametre)
                    direct_booking = (
                        f"https://www.booking.com/hotel/{country_code}/{hotel_slug}.html?"
                        f"checkin={cin}&checkout={cout}"
                        f"&group_adults={guests}&no_rooms=1"
                        f"&aid={aid}"
                    )
                    # 2. Doğrudan Agoda Canlı Oda ve Fiyat Ekranı (Türkiye içi ve dışı yasal, engelsiz)
                    direct_agoda = (
                        f"https://www.agoda.com/tr-tr/search?"
                        f"text={urllib.parse.quote(hotel_name + ' ' + hotel_city)}"
                        f"&checkIn={cin}&checkOut={cout}&rooms=1&adults={guests}"
                        f"&cid={agoda_cid}"
                    )
                    # 3. Doğrudan Google Hotels Karşılaştırma Ekranı
                    direct_google = (
                        f"https://www.google.com/travel/hotels?"
                        f"q={urllib.parse.quote(hotel_name + ' ' + hotel_city)}"
                    )

                    # Türkiye içindeki otellerde Booking.com Türk IP'lerine mahkeme kararıyla kapalı olduğundan,
                    # yerli otellerde birincil link Agoda / Google Hotels atanır. Yurt dışında ise doğrudan Booking.com otel sayfası verilir.
                    if is_domestic:
                        primary_url = direct_agoda
                        primary_provider = "Agoda"
                    else:
                        primary_url = direct_booking
                        primary_provider = "Booking.com"

                    curr_sym = CurrencyService.get_symbol(currency)
                    live_list.append({
                        "name": name,
                        "score": round(score, 1) if score else 9.0,
                        "review_score": round(score, 1) if score else 9.0,
                        "score_word": score_word,
                        "photo": photo_hd,
                        "photo_url": photo_hd,
                        "address": h.get("address", h.get("city", "")),
                        "city": hotel_city,
                        "price": round(nightly_target, 2),
                        "nightly_price": round(nightly_target, 2),
                        "total_price": round(total_target, 2),
                        "price_formatted": f"{int(round(nightly_target)):,} {curr_sym}".replace(",", "."),
                        "total_price_formatted": f"{int(round(total_target)):,} {curr_sym}".replace(",", "."),
                        "currency": curr_sym,
                        "booking_url": primary_url,
                        "url": primary_url,
                        "direct_url": primary_url,
                        "direct_booking_url": direct_booking,
                        "agoda_url": direct_agoda,
                        "google_url": direct_google,
                        "provider": primary_provider,
                        "is_domestic_tr": is_domestic
                    })

                cls._HOTEL_CACHE[cache_key] = (now_ts, live_list)
                return live_list
        except Exception as e:
            logger.warning(f"RapidAPI Booking fetch warning: {e}")
            return []

    @classmethod
    def _get_fallback_hotels(
        cls,
        city_clean: str,
        city_slug: str,
        cin: str,
        cout: str,
        nights: int,
        guests: int,
        currency: str,
        is_international: bool,
        dest_id: Optional[str] = None,
        dest_type: str = "city"
    ) -> List[Dict[str, Any]]:
        # SIFIR VARSAYIM KURALI: Canlı API'den doğrulanmış gerçek otel odası gelmediyse
        # ASLA hayali gecelik fiyat veya uydurma otel üretilmez.
        # Kullanıcı doğrudan Trip.com, Booking.com, Enuygun ve Agoda'nın canlı sonuçlarına yönlendirilir.
        return []

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
        Kullanıcının seyahat tarihlerini ve varış şehrini alarak:
        1. Varsa RapidAPI Booking.com'dan CANLI ve GERÇEK otel odalarını çeker.
        2. Yurt dışı/adalarda Enuygun linkini kaldırıp Booking ve Agoda'ya kusursuz yönlendirir.
        """
        cin, cout, nights = cls.calculate_dates(checkin_date, checkout_date)
        city_clean = dest_city.split("(")[0].strip()
        city_slug = (
            city_clean.replace("İ", "i")
            .replace("I", "i")
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("Ş", "s")
            .replace("ç", "c")
            .replace("Ç", "c")
            .replace("ö", "o")
            .replace("Ö", "o")
            .replace("ü", "u")
            .replace("Ü", "u")
            .replace("ğ", "g")
            .replace("Ğ", "g")
            .lower()
            .replace("\u0307", "")
            .replace(" ", "-")
        )
        
        # Destinasyonun yurt dışı / ada kontrolü (Önce şehir veritabanından, yoksa haritadan teyit)
        from app.cities import find_city
        matched_loc = find_city(dest_city)
        dest_meta = cls.DEST_ID_MAP.get(city_slug)
        if matched_loc and "is_international" in matched_loc:
            is_international = bool(matched_loc.get("is_international", False))
        elif dest_meta:
            is_international = bool(dest_meta.get("is_intl", False))
        else:
            is_international = bool("adasi" in city_slug or "island" in city_slug or "nce" in city_slug or "nice" in city_slug)
            
        dest_id = dest_meta.get("dest_id") if dest_meta else None
        dest_type = dest_meta.get("dest_type", "city") if dest_meta else "city"

        currency = (currency or "TRY").upper()
        curr_sym = CurrencyService.get_symbol(currency)
        aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
        trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
        trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")

        # 1. Trip.com Otel Resmi Derin Arama Linki (%4 - %7 Net Komisyon, TR'de Engellemesiz)
        trip_domain = "www.trip.com" if is_international else "tr.trip.com"
        trip_hotel_url = (
            f"https://{trip_domain}/hotels/list?"
            f"keyword={urllib.parse.quote(city_clean)}"
            f"&checkin={cin}&checkout={cout}"
            f"&crn=1&adult={guests}"
            f"&Allianceid={trip_aid}&SID={trip_sid}"
        )

        # 2. Booking.com Doğrudan Canlı Arama Linki (.html uzantısı ile WAF tr_redirected önlenir)
        dest_q = f"&dest_id={dest_id}&dest_type={dest_type}" if dest_id else ""
        booking_url = (
            f"https://www.booking.com/searchresults.html?"
            f"ss={urllib.parse.quote(city_clean)}"
            f"{dest_q}"
            f"&checkin={cin}&checkout={cout}"
            f"&group_adults={guests}&no_rooms=1"
            f"&sb=1"
            f"&aid={aid}"
        )

        # 3. Agoda Doğrudan Canlı Arama Linki
        agoda_url = (
            f"https://www.agoda.com/tr-tr/search?"
            f"city={urllib.parse.quote(city_clean)}"
            f"&checkIn={cin}&checkOut={cout}&rooms=1&adults={guests}"
            f"&cid={settings.AFFILIATE_AGODA_CID}"
        )

        # 4. Enuygun Otel Linki (SADECE YURT İÇİ TÜRKİYE İÇİN AKTİF, YURT DIŞINDA 404 ÖNLEMEK İÇİN NONE)
        if not is_international:
            try:
                cin_dt = datetime.strptime(cin, "%Y-%m-%d")
                cout_dt = datetime.strptime(cout, "%Y-%m-%d")
                enuygun_cin = cin_dt.strftime("%d.%m.%Y")
                enuygun_cout = cout_dt.strftime("%d.%m.%Y")
            except Exception:
                enuygun_cin, enuygun_cout = cin, cout

            enuygun_url = (
                f"https://www.enuygun.com/otel/arama/{city_slug}/?"
                f"giris={enuygun_cin}&cikis={enuygun_cout}&yetiskin={guests}"
            )
            primary_city_url = trip_hotel_url
            primary_provider = "Trip.com"
        else:
            enuygun_url = None
            primary_city_url = booking_url
            primary_provider = "Booking.com"

        # 1. CANLI BOOKING.COM VERİSİ SORGULA
        live_hotels = []
        if dest_id:
            live_hotels = cls.fetch_live_booking_hotels(
                dest_id=dest_id,
                dest_type=dest_type,
                cin=cin,
                cout=cout,
                guests=guests,
                currency=currency
            )

        if not live_hotels:
            live_hotels = cls._get_fallback_hotels(
                city_clean=city_clean,
                city_slug=city_slug,
                cin=cin,
                cout=cout,
                nights=nights,
                guests=guests,
                currency=currency,
                is_international=is_international,
                dest_id=dest_id,
                dest_type=dest_type
            )

        # Fiyat profili (Yedek piyasa göstergesi)
        profile = cls.CITY_HOTEL_PROFILES.get(city_slug, {"min_try": 1200, "max_try": 3000, "label": f"{city_clean} Merkez"})
        min_rate = CurrencyService.convert(profile["min_try"], "TRY", currency)
        max_rate = CurrencyService.convert(profile["max_try"], "TRY", currency)

        # Kategori kartları (Canlı veya güvenilir metasearch)
        categories = [
            {
                "title": "🌟 Bütçe Dostu & Ada / Şehir Butik Otelleri",
                "badge": "Canlı Müsaitlik",
                "badge_color": "emerald",
                "desc": f"{city_clean} merkezinde gezginlerin en çok tercih ettiği ekonomik butik oteller.",
                "est_nightly": round(min_rate, 2),
                "est_total": round(min_rate * nights, 2),
                "action_text": f"{primary_provider}'da Odaları Gör ↗",
                "link": primary_city_url
            },
            {
                "title": "🏨 Merkez & Sahil / 4 Yıldız Konfor",
                "badge": "Popüler Seçim",
                "badge_color": "blue",
                "desc": "Turistik noktalara, limana ve merkeze yürüme mesafesinde konforlu oteller.",
                "est_nightly": round((min_rate + max_rate) / 2, 2),
                "est_total": round(((min_rate + max_rate) / 2) * nights, 2),
                "action_text": f"{primary_provider}'da İncele ↗",
                "link": primary_city_url
            },
            {
                "title": "💎 Taş Konak & Premium Resort Seçenekleri",
                "badge": "Üst Düzey Puan",
                "badge_color": "purple",
                "desc": "Tarihi taş mimarili oteller, deniz manzaralı süitler ve spa otelleri.",
                "est_nightly": round(max_rate * 1.3, 2),
                "est_total": round(max_rate * 1.3 * nights, 2),
                "action_text": f"{primary_provider}'da İncele ↗",
                "link": primary_city_url
            }
        ]

        return {
            "destination": city_clean,
            "region_label": dest_meta.get("label", profile["label"]) if dest_meta else profile["label"],
            "checkin_date": cin,
            "checkout_date": cout,
            "nights": nights,
            "guests": guests,
            "currency": curr_sym,
            "currency_code": currency,
            "is_international": is_international,
            "avg_nightly_min": round(min_rate, 2),
            "avg_nightly_max": round(max_rate, 2),
            "total_stay_min": round(min_rate * nights, 2),
            "total_stay_max": round(max_rate * nights, 2),
            "is_live": len(live_hotels) > 0,
            "live_hotels": live_hotels,
            "booking_url": booking_url,
            "primary_city_url": primary_city_url,
            "primary_provider": primary_provider,
            "enuygun_url": enuygun_url,
            "agoda_url": agoda_url,
            "trip_hotel_url": trip_hotel_url,
            "deep_links": {
                "trip": trip_hotel_url,
                "booking": booking_url,
                "agoda": agoda_url,
                "enuygun": enuygun_url,
                "primary": primary_city_url
            },
            "categories": categories,
            "disclaimer": "Oda ve kesin fiyatlar anlık doluluk ve oda tipine göre doğrudan sağlayıcı sisteminde teyit edilir."
        }
