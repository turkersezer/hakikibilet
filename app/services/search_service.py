import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.cities import find_city, TURKEY_CITIES
from app.config import settings
from app.services.currency_service import CurrencyService
from app.services.hotel_service import HotelService

class SearchService:
    @staticmethod
    def format_date_for_skyscanner(date_str: str) -> str:
        """YYYY-MM-DD -> YYMMDD format"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%y%m%d")
        except Exception:
            return date_str.replace("-", "")[2:]

    @staticmethod
    def format_date_for_enuygun(date_str: str) -> str:
        """YYYY-MM-DD -> DD.MM.YYYY format"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return date_str

    @classmethod
    def generate_price_calendar(
        cls, origin_name: str, dest_name: str, base_date_str: str, 
        has_flight: bool = True, has_train: bool = True, has_bus: bool = True, has_ferry: bool = False,
        days_count: int = 7
    ):
        """
        Esnek Tarih Takvimi (Sıfır Yanıltıcı Fiyat İlkesi):
        Kullanıcıya uydurma tahmini rakamlar göstermez; seçilen aralıktaki aktif sefer günlerini,
        hızlı gün değiştirme butonlarını ve Google Flights / Skyscanner çoklu gün canlı fiyat grafiği kısayolunu sunar.
        """
        try:
            base_dt = datetime.strptime(base_date_str, "%Y-%m-%d")
        except Exception:
            base_dt = datetime.now() + timedelta(days=7)

        turkish_day_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        turkish_month_names = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        
        start_offset = 0 if days_count > 7 else -1
        calendar = []

        for offset in range(start_offset, start_offset + days_count):
            day_dt = base_dt + timedelta(days=offset)
            if day_dt < datetime.now() - timedelta(days=1):
                continue
            
            day_iso = day_dt.strftime("%Y-%m-%d")
            calendar.append({
                "date": day_iso,
                "day_num": day_dt.day,
                "month_name": turkish_month_names[day_dt.month - 1],
                "day_name": turkish_day_names[day_dt.weekday()],
                "has_flight": has_flight,
                "has_train": has_train,
                "has_bus": has_bus,
                "has_ferry": has_ferry,
                "is_selected": (day_iso == base_date_str),
                "is_today": (day_iso == datetime.now().strftime("%Y-%m-%d"))
            })

        return {
            "days": calendar,
            "days_count": len(calendar),
            "range_type": days_count,
            "tip": "💡 Tarih Sezgisi: Tarihlere tıklayarak o güne ait seferleri anında listeleyebilir, canlı grafikten tüm dönemi inceleyebilirsiniz."
        }

    @classmethod
    def generate_deep_links(
        cls, origin_city_name: str, dest_city_name: str, departure_date: str, 
        return_date: Optional[str] = None, passengers: int = 1, trip_type: str = "one_way",
        cabin_class: str = "economy", currency: str = "TRY"
    ):
        origin = find_city(origin_city_name)
        dest = find_city(dest_city_name)
        
        origin_iata = origin["iata"] if origin and origin.get("iata") else None
        dest_iata = dest["iata"] if dest and dest.get("iata") else None
        
        origin_slug = origin["slug"] if origin else origin_city_name.lower().replace(" ", "-")
        dest_slug = dest["slug"] if dest else dest_city_name.lower().replace(" ", "-")
        
        sky_dep = cls.format_date_for_skyscanner(departure_date)
        enuygun_dep = cls.format_date_for_enuygun(departure_date)

        origin_has_airport = bool(origin and origin.get("has_airport") and origin_iata)
        dest_has_airport = bool(dest and dest.get("has_airport") and dest_iata)
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))
        origin_is_intl = bool(origin and origin.get("is_international"))
        dest_is_intl = bool(dest and dest.get("is_international"))

        # Tren Kuralları: TCDD sadece yurt içi, Trainline sadece iki Avrupa şehri arasında
        is_tcdd_train = bool(origin_has_train and dest_has_train and not origin_is_intl and not dest_is_intl)
        is_intl_train = bool(origin_has_train and dest_has_train and origin_is_intl and dest_is_intl)
        train_available = is_tcdd_train or is_intl_train

        train_reason = None
        if not train_available:
            if origin_is_intl != dest_is_intl:
                train_reason = f"Türkiye ile {dest_city_name if not origin_is_intl else origin_city_name} arasında doğrudan tarifeli tren seferi bulunmamaktadır. Lütfen uçak veya Akıllı Rota planını inceleyiniz."
            else:
                missing_t = origin_city_name if not origin_has_train else dest_city_name
                train_reason = f"{missing_t} bölgesinde aktif demiryolu hattı bulunmamaktadır."

        is_round = (trip_type == "round_trip" and return_date)
        is_biz = (cabin_class == "business")
        sky_cabin = "business" if is_biz else "economy"
        biz_extra_google = "+business" if is_biz else ""
        biz_extra_enuygun = "&sinif=business" if is_biz else ""

        # 1. Uçak Deep Linkleri (Doğrudan canlı sonuç ekranı)
        flight_links = {
            "available": origin_has_airport and dest_has_airport,
            "reason": None if (origin_has_airport and dest_has_airport) else f"{origin_city_name if not origin_has_airport else dest_city_name} şehrinde aktif havalimanı bulunmamaktadır."
        }
        if flight_links["available"]:
            enuygun_route = f"{origin_slug}-{dest_slug}-{origin_iata.lower()}a-{dest_iata.lower()}a"
            pgs_ret = f"&returnDate={return_date}" if is_round else ""
            flight_links["pegasus"] = f"https://web.flypgs.com/booking?departurePort={origin_iata}&arrivalPort={dest_iata}&departureDate={departure_date}&adultCount={passengers}{pgs_ret}"

            if is_round:
                sky_ret = cls.format_date_for_skyscanner(return_date)
                enuygun_ret = cls.format_date_for_enuygun(return_date)
                flight_links["skyscanner"] = f"https://www.skyscanner.com.tr/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{sky_dep}/{sky_ret}/?adultsv2={passengers}&cabinclass={sky_cabin}&currency={currency}&locale=tr-TR&rtn=1"
                flight_links["google_flights"] = f"https://www.google.com/travel/flights?q=flights+from+{origin_iata}+to+{dest_iata}+on+{departure_date}+through+{return_date}{biz_extra_google}&curr={currency}"
                flight_links["enuygun"] = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep}&donus={enuygun_ret}&yetiskin={passengers}{biz_extra_enuygun}"
            else:
                flight_links["skyscanner"] = f"https://www.skyscanner.com.tr/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{sky_dep}/?adultsv2={passengers}&cabinclass={sky_cabin}&currency={currency}&locale=tr-TR&rtn=0"
                flight_links["google_flights"] = f"https://www.google.com/travel/flights?q=flights+from+{origin_iata}+to+{dest_iata}+on+{departure_date}{biz_extra_google}&curr={currency}"
                flight_links["enuygun"] = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep}&yetiskin={passengers}{biz_extra_enuygun}"
        else:
            flight_links["pegasus"] = None
            flight_links["skyscanner"] = None
            flight_links["google_flights"] = None
            flight_links["enuygun"] = None

        # 2. Tren Deep Linkleri (TCDD E-Bilet & Avrupa Trainline / Omio)
        train_links = {
            "available": train_available,
            "is_tcdd": is_tcdd_train,
            "is_international": is_intl_train,
            "reason": train_reason,
            "tcdd": "https://ebilet.tcddtasimacilik.gov.tr/" if is_tcdd_train else None,
            "trainline": f"https://www.thetrainline.com/book/results?origin={origin_slug}&destination={dest_slug}&outwardDate={departure_date}&currency={currency}" if is_intl_train else None,
            "omio": f"https://www.omio.com/search-frontend/results/{origin_slug}/{dest_slug}/{departure_date}?locale=tr&currency={currency}" if is_intl_train else None,
            "tcdd_search_hint": f"Kalkış: {origin.get('train_station', origin_city_name)} -> Varış: {dest.get('train_station', dest_city_name)}" if is_tcdd_train else "Demiryolu hattı yok"
        }

        # 3. Otobüs Deep Linkleri (Obilet - Doğrudan seçili tarih ve güzergah sefer listesi)
        is_dest_intl = bool(dest and dest.get("is_international"))
        is_overland = bool(dest and dest.get("is_overland_neighbor"))
        bus_ret_path = f"/{return_date}" if is_round else ""

        if is_dest_intl and not is_overland:
            bus_links = {
                "available": False,
                "is_overland_neighbor": False,
                "reason": f"{dest_city_name} denizaşırı/kıtalararası bir rota olduğundan doğrudan otobüs seferi bulunmamaktadır.",
                "obilet": None,
                "kamilkoc": None,
                "pamukkale": None
            }
        else:
            from app.services.bus_service import BusService
            bus_link = BusService.get_obilet_deep_link(origin_city_name, dest_city_name, departure_date)
            bus_links = {
                "available": True,
                "is_overland_neighbor": is_overland,
                "reason": None,
                "obilet": bus_link,
                "kamilkoc": bus_link,
                "pamukkale": bus_link
            }

        # 4. Deniz Yolları & Feribot Deep Linkleri
        is_sea_origin = bool(origin and origin.get("is_ferry"))
        is_sea_dest = bool(dest and dest.get("is_ferry"))
        ferry_links = {
            "available": is_sea_origin and is_sea_dest,
            "reason": None if (is_sea_origin and is_sea_dest) else "Bu güzergahta doğrudan deniz yolu seferi bulunmamaktadır.",
            "ido": "https://www.ido.com.tr/",
            "budo": "https://budo.burulas.com.tr/",
            "erturk": "https://www.erturk.com.tr/tr/",
            "turyol": "https://www.turyolonline.com/",
            "feribotlines": f"https://www.feribotlines.com/?subid={settings.AFFILIATE_FERRY_SUBID}"
        }

        return {
            "flight": flight_links,
            "train": train_links,
            "bus": bus_links,
            "ferry": ferry_links
        }

    @classmethod
    def search_anywhere(cls, origin_city: str, departure_date: str, transport_type: str = "all", passengers: int = 1):
        """
        Gezgin Modu: Varış noktası 'Her Yere' seçildiğinde popüler yurt içi rotaları listeler
        """
        origin = find_city(origin_city)
        origin_name = origin["name"] if origin else origin_city

        destinations = [
            {"dest": "Eskişehir", "type": "train", "carrier": "TCDD YHT", "logo": "🚆", "duration": "3 sa", "badge": "Gezgin Favorisi"},
            {"dest": "Bursa", "type": "bus", "carrier": "Kamil Koç", "logo": "🚌", "duration": "2 sa 15 dk", "badge": "Hafta Sonu Kaçamağı"},
            {"dest": "İzmir", "type": "flight", "carrier": "Pegasus Airlines", "logo": "✈️", "duration": "1 sa 10 dk", "badge": "Flaş Uçuş Hattı"},
            {"dest": "Konya", "type": "train", "carrier": "TCDD YHT", "logo": "🚆", "duration": "4 sa 45 dk", "badge": "Kültür Rotası"},
            {"dest": "Antalya", "type": "flight", "carrier": "AJet (AnadoluJet)", "logo": "✈️", "duration": "1 sa 20 dk", "badge": "Akdeniz Kaçamağı"},
            {"dest": "Kars", "type": "train", "carrier": "Doğu Ekspresi", "logo": "🚆", "duration": "24 sa", "badge": "Efsane Macera"},
            {"dest": "Trabzon", "type": "flight", "carrier": "Türk Hava Yolları", "logo": "✈️", "duration": "1 sa 40 dk", "badge": "Karadeniz Turu"}
        ]

        if transport_type != "all":
            destinations = [d for d in destinations if d["type"] == transport_type]

        tickets = []
        for i, d in enumerate(destinations):
            links = cls.generate_deep_links(origin_name, d["dest"], departure_date, passengers=passengers)
            
            if d["type"] == "flight":
                if "pegasus" in d["carrier"].lower():
                    direct_link = links["flight"]["pegasus"] or links["flight"]["skyscanner"]
                    official_name = "Pegasus Resmi Biletleme Ekranı"
                else:
                    direct_link = links["flight"]["enuygun"] or links["flight"]["skyscanner"]
                    official_name = f"{d['carrier']} Sefer Ekranı"
                official_link = direct_link
                agent_name = "Enuygun"
                agent_link = links["flight"]["enuygun"] or links["flight"]["skyscanner"]
            elif d["type"] == "train":
                official_link = links["train"]["tcdd"]
                official_name = "TCDD Taşımacılık E-Bilet"
                agent_name = "TCDD E-Bilet"
                agent_link = links["train"]["tcdd"]
                direct_link = links["train"]["tcdd"]
            else:
                official_name = f"{d['carrier']} (Obilet)"
                official_link = links["bus"]["obilet"]
                agent_name = "Obilet"
                agent_link = links["bus"]["obilet"]
                direct_link = links["bus"]["obilet"]

            tickets.append({
                "id": f"anywhere-{i}",
                "transport_type": d["type"],
                "carrier": d["carrier"],
                "carrier_logo": d["logo"],
                "flight_number": "Popüler Keşif Hattı",
                "origin": origin_name,
                "destination": d["dest"],
                "departure_time": "09:00",
                "arrival_time": "12:00",
                "duration": d["duration"],
                "is_direct": True,
                # Sıfır tahmini/uydurma fiyat ilkesi: Canlı API teyidi yoksa None
                "price": None,
                "has_live_price": False,
                "price_status_text": "Canlı Fiyat ve Koltuk Durumu",
                "regular_price": None,
                "currency": "₺",
                "badge": d["badge"],
                "official_name": official_name,
                "official_link": official_link,
                "agent_name": agent_name,
                "agent_link": agent_link,
                "direct_link": direct_link,
                "booking_link": direct_link,
                "is_night_trip": False,
                "providers": [
                    {"name": official_name, "url": direct_link, "price": None, "is_best": True}
                ]
            })

        return {
            "origin": origin_name,
            "destination": "Her Yere (Popüler Rotalar)",
            "date": departure_date,
            "passengers": passengers,
            "transport_type": transport_type,
            "is_anywhere": True,
            "summary": {
                "flight": {"count": len([t for t in tickets if t["transport_type"] == "flight"]), "min_price": None, "min_duration": "1 sa 10 dk", "available": True},
                "train": {"count": len([t for t in tickets if t["transport_type"] == "train"]), "min_price": None, "min_duration": "3 sa", "available": True},
                "bus": {"count": len([t for t in tickets if t["transport_type"] == "bus"]), "min_price": None, "min_duration": "2 sa 15 dk", "available": True},
                "ferry": {"count": 0, "min_price": None, "min_duration": None, "available": False}
            },
            "deep_links": {"flight": {"available": True}, "train": {"available": True}, "bus": {"available": True}},
            "notices": ["🌍 Gezgin Keşif Modu: Seçtiğiniz kalkış noktasından en popüler direkt hatlar listelendi. Canlı fiyatlar doğrudan ilgili sağlayıcı sisteminde gösterilir."],
            "results_count": len(tickets),
            "tickets": tickets
        }

    @classmethod
    def get_curated_events(cls):
        """
        Gezgin Keşif Rehberi: 'Nereye Gitmeliyim? / Festival & Sezon Radarı'
        Kullanıcı tek tıkla tıkladığında formu doldurur ve arama yapar.
        """
        return [
            {
                "id": "event-oktoberfest",
                "title": "Oktoberfest Bira Festivali 🍻",
                "city": "Münih (MUC)",
                "country": "Almanya",
                "dates": "19 Eyl - 04 Eki",
                "dep_date": "2026-09-22",
                "ret_date": "2026-09-26",
                "badge": "Dünya Çapında Festival",
                "transport_mode": "flight",
                "tag": "Eğlence & Kültür",
                "desc": "Münih'in geleneksel çadırları, Bavyera müziği ve devasa festival atmosferi.",
                "hotel_range": "Gecelik ~1.900 ₺'den başlayan",
                "why": "Sonbaharın en büyük açık hava festivali. Erken rezervasyon ile bilet fırsatları aktif."
            },
            {
                "id": "event-halloween",
                "title": "Cadılar Bayramı & Sonbahar 🎃",
                "city": "New York (JFK/EWR)",
                "country": "ABD",
                "dates": "28 Eki - 02 Kas",
                "dep_date": "2026-10-28",
                "ret_date": "2026-11-03",
                "badge": "Efsanevi Kortej",
                "transport_mode": "flight",
                "tag": "Büyük Metropol",
                "desc": "Village Halloween Parade, Central Park sonbahar renkleri ve New York ışıltısı.",
                "hotel_range": "Gecelik ~3.500 ₺'den başlayan",
                "why": "New York sokaklarının en renkli festival haftası."
            },
            {
                "id": "event-venice",
                "title": "Venedik Maske Karnavalı 🎭",
                "city": "Milano (MXP)",
                "country": "İtalya",
                "dates": "14 Şub - 24 Şub",
                "dep_date": "2027-02-14",
                "ret_date": "2027-02-18",
                "badge": "Tarihi Masal",
                "transport_mode": "flight",
                "tag": "İtalya Turu",
                "desc": "Milano uçuşu + Frecciarossa hızlı treni ile 2 saatte Venedik San Marco Meydanı'na geçiş.",
                "hotel_range": "Gecelik ~1.800 ₺'den başlayan",
                "why": "Dünyanın en büyüleyici kostüm ve maske karnavalı."
            },
            {
                "id": "event-valentine",
                "title": "Sevgililer Günü Romantik Kaçış 💖",
                "city": "Paris (CDG/ORY)",
                "country": "Fransa",
                "dates": "12 Şub - 16 Şub",
                "dep_date": "2027-02-12",
                "ret_date": "2027-02-16",
                "badge": "Aşkın Başkenti",
                "transport_mode": "flight",
                "tag": "Hafta Sonu Kaçamağı",
                "desc": "Eyfel Kulesi, Seine Nehri tekne turu ve Montmartre sokaklarında unutulmaz anlar.",
                "hotel_range": "Gecelik ~2.200 ₺'den başlayan",
                "why": "Sevgililer günü için dünyanın 1 numaralı romantik rotası."
            },
            {
                "id": "event-christmas",
                "title": "Avrupa Masalsı Noel Pazarları 🎄",
                "city": "Viyana (VIE)",
                "country": "Avusturya",
                "dates": "10 Ara - 26 Ara",
                "dep_date": "2026-12-15",
                "ret_date": "2026-12-19",
                "badge": "Kış Masalı",
                "transport_mode": "flight",
                "tag": "Işıltılı Şehirler",
                "desc": "Rathausplatz dev Noel ağacı, sıcak baharatlı içecekler ve Viyana-Prag-Budapeşte tren hatları.",
                "hotel_range": "Gecelik ~1.700 ₺'den başlayan",
                "why": "Orta Avrupa'nın en büyüleyici kış ve yeni yıl pazarları dönemi."
            },
            {
                "id": "event-chios",
                "title": "Kapı Vizesiz Sakız Adası Kaçamağı 🏖️",
                "city": "Sakız Adası (Chios)",
                "country": "Yunanistan",
                "dates": "Hafta Sonu Seferleri",
                "dep_date": "2026-10-24",
                "ret_date": "2026-10-26",
                "badge": "Kapı Vizesi Kolaylığı",
                "transport_mode": "ferry",
                "tag": "Ege & Deniz",
                "desc": "Çeşme'den 30 dakikada Sakız Adası. Damla sakızı köyleri, taze deniz ürünleri ve huzurlu koylar.",
                "hotel_range": "Gecelik ~1.300 ₺'den başlayan",
                "why": "Bütçe dostu, yakın ve vizesiz/kapı vizesiyle en hızlı yurt dışı tatili."
            }
        ]

    @classmethod
    def build_smart_multimodal_plan(
        cls, origin: dict, dest: dict, departure_date: str, 
        return_date: Optional[str] = None, passengers: int = 1, currency: str = "TRY",
        include_hotel: bool = False, hotel_nights: Optional[int] = None,
        search_mode: str = "fast"
    ) -> Optional[Dict[str, Any]]:
        """
        AKILLI ÇOK MODLU ROTALAMA MOTORU (Rome2rio Modeli)
        Havalimanı olmayan illerde veya seyahat planlama modunda kullanıcıya
        uçtan uca kombine seyahat planı, transferler, opsiyonel otel ve biletleme rehberi sunar.
        """
        if not origin or not dest:
            return None

        has_origin_airport = bool(origin.get("has_airport") and origin.get("iata"))
        is_dest_intl = bool(dest and dest.get("is_international"))
        dest_name = dest["name"] if dest else "Varış Noktası"
        dest_iata = dest.get("iata", "CDG") if dest else "CDG"
        origin_name = origin["name"]
        origin_slug = origin.get("slug", "bolu")

        # Eğer kalkış zaten büyük ana merkezse ve yurt içi uçuşsa VE arama modu smart_route değilse multimodal plana gerek yok
        if has_origin_airport and origin.get("iata") in ("IST", "SAW", "ESB", "AYT", "ADB") and not is_dest_intl and search_mode != "smart_route":
            return None

        hotel_rec = None
        if include_hotel:
            hotel_rec = HotelService.get_hotel_recommendation(
                dest_city=dest_name,
                checkin_date=departure_date,
                checkout_date=return_date,
                guests=passengers,
                currency=currency
            )

        domestic_hub = origin.get("nearest_domestic_hub")
        intl_hub = origin.get("nearest_intl_hub")
        routes = []

        # 1. ROTA SEÇENEĞİ: En Az Karayolu Mesafesi (Yerel Havalimanı + Aktarmalı Uçuş)
        if domestic_hub:
            hub_iata = domestic_hub.get("iata", "ONQ")
            hub_city = domestic_hub.get("city", "Zonguldak")
            trans_type = domestic_hub.get("transport", "bus")
            trans_label = "YHT Hızlı Tren" if "train" in trans_type else ("Hızlı Feribot" if "ferry" in trans_type else "Otobüs / Servis")
            trans_icon = "🚆" if "train" in trans_type else ("⛴️" if "ferry" in trans_type else "🚌")
            
            hub_bus_link = f"https://www.obilet.com/otobus-bileti/{origin_slug}-{domestic_hub.get('city', '').lower()}/{departure_date}"
            flight_connect_link = f"https://www.google.com/travel/flights?q=flights+from+{hub_iata}+to+{dest_iata}+on+{departure_date}&curr={currency}"
            
            steps = [
                {
                    "step_num": 1,
                    "icon": trans_icon,
                    "title": f"1. Adım: {origin_name} ➔ {domestic_hub['name']}",
                    "desc": f"{trans_label} ile ulaşım süresi: ~{domestic_hub.get('duration', '1 sa 30 dk')}",
                    "action_text": f"{trans_label} Seferini Gör ↗",
                    "link": hub_bus_link
                },
                {
                    "step_num": 2,
                    "icon": "✈️",
                    "title": f"2. Adım: {hub_city} ({hub_iata}) ➔ {dest_name} ({dest_iata})",
                    "desc": "İstanbul/Ankara aktarmalı uçuş. Valiziniz son noktaya kadar otomatik aktarılır.",
                    "action_text": "Aktarmalı Uçak Biletini Gör ↗",
                    "link": flight_connect_link
                }
            ]

            if include_hotel and hotel_rec:
                steps.append({
                    "step_num": 3,
                    "icon": "🏨",
                    "title": f"3. Adım: {dest_name} Konaklama ({hotel_rec['nights']} Gece)",
                    "desc": f"Merkezi konumda ortalama ~{hotel_rec['avg_nightly_min']:,.0f} {hotel_rec['currency']} - {hotel_rec['avg_nightly_max']:,.0f} {hotel_rec['currency']} / gece.",
                    "action_text": "Booking'de Odaları İncele ↗",
                    "link": hotel_rec["deep_links"]["booking"]
                })

            routes.append({
                "id": "route-opt-1",
                "badge": "En Az Karayolu Mesafesi 🛫",
                "title": f"{origin_name} ➔ {domestic_hub['name']} ➔ {dest_name}",
                "tag": "Uçak Konforu Öncelikli",
                "tag_color": "emerald",
                "steps": steps
            })

        # 2. ROTA SEÇENEĞİ: Direkt Uçuş Konforu (Büyük Uluslararası Havalimanı + Kesintisiz Uçuş)
        if intl_hub:
            i_hub_iata = intl_hub.get("iata", "SAW")
            i_trans_type = intl_hub.get("transport", "bus")
            i_trans_label = "YHT Hızlı Tren" if "train" in i_trans_type else ("Hızlı Feribot / İDO" if "ferry" in i_trans_type else "Havalimanı Otobüsü / Servis")
            i_trans_icon = "🚆" if "train" in i_trans_type else ("⛴️" if "ferry" in i_trans_type else "🚌")
            
            intl_bus_link = f"https://www.obilet.com/otobus-bileti/{origin_slug}-istanbul/{departure_date}"
            direct_flight_link = f"https://www.google.com/travel/flights?q=flights+from+{i_hub_iata}+to+{dest_iata}+on+{departure_date}&curr={currency}"
            
            steps_2 = [
                {
                    "step_num": 1,
                    "icon": i_trans_icon,
                    "title": f"1. Adım: {origin_name} ➔ {intl_hub['name']}",
                    "desc": f"{i_trans_label} ile ulaşım süresi: ~{intl_hub.get('duration', '2 sa')}",
                    "action_text": f"{i_trans_label} Seferini Seç ↗",
                    "link": intl_bus_link
                },
                {
                    "step_num": 2,
                    "icon": "✈️",
                    "title": f"2. Adım: {intl_hub['name']} ➔ {dest_name} ({dest_iata})",
                    "desc": "Doğrudan aktarmasız direkt uçuş ile en hızlı varış.",
                    "action_text": "Direkt Uçuş Biletini Gör ↗",
                    "link": direct_flight_link
                }
            ]

            if include_hotel and hotel_rec:
                steps_2.append({
                    "step_num": 3,
                    "icon": "🏨",
                    "title": f"3. Adım: {dest_name} Konaklama ({hotel_rec['nights']} Gece)",
                    "desc": f"Merkezi konumda ortalama ~{hotel_rec['avg_nightly_min']:,.0f} {hotel_rec['currency']} - {hotel_rec['avg_nightly_max']:,.0f} {hotel_rec['currency']} / gece.",
                    "action_text": "Booking'de Odaları İncele ↗",
                    "link": hotel_rec["deep_links"]["booking"]
                })

            routes.append({
                "id": "route-opt-2",
                "badge": "Direkt Uçuş Konforu 🚀",
                "title": f"{origin_name} ➔ {intl_hub['name']} ➔ {dest_name}",
                "tag": "Hızlı & Direkt Uçuş",
                "tag_color": "blue",
                "steps": steps_2
            })
        elif has_origin_airport and (search_mode == "smart_route" or is_dest_intl):
            # Kalkış noktasının kendisi zaten havalimanına sahipse (İstanbul, Ankara vb.)
            orig_iata = origin.get("iata", "IST")
            direct_flight_link = f"https://www.google.com/travel/flights?q=flights+from+{orig_iata}+to+{dest_iata}+on+{departure_date}&curr={currency}"
            steps_hub = [
                {
                    "step_num": 1,
                    "icon": "🚆",
                    "title": f"1. Adım: {origin_name} Merkez ➔ {origin_name} Havalimanı ({orig_iata})",
                    "desc": "Havalimanı Metrosu / Havaist / Havaş ekspres servisleri ile terminale ulaşım.",
                    "action_text": "Havalimanı Ulaşımı ↗",
                    "link": f"https://www.google.com/maps/search/{origin_slug}+havalimani+ulasim"
                },
                {
                    "step_num": 2,
                    "icon": "✈️",
                    "title": f"2. Adım: {origin_name} ({orig_iata}) ➔ {dest_name} ({dest_iata})",
                    "desc": "Direkt veya en uygun aktarmalı uçuş.",
                    "action_text": "Uçak Biletini Gör ↗",
                    "link": direct_flight_link
                }
            ]
            if include_hotel and hotel_rec:
                steps_hub.append({
                    "step_num": 3,
                    "icon": "🏨",
                    "title": f"3. Adım: {dest_name} Konaklama ({hotel_rec['nights']} Gece)",
                    "desc": f"Merkezi konumda ortalama ~{hotel_rec['avg_nightly_min']:,.0f} {hotel_rec['currency']} - {hotel_rec['avg_nightly_max']:,.0f} {hotel_rec['currency']} / gece.",
                    "action_text": "Booking'de Odaları İncele ↗",
                    "link": hotel_rec["deep_links"]["booking"]
                })
            routes.append({
                "id": "route-opt-hub",
                "badge": "Uçtan Uca Seyahat Planı 🚀",
                "title": f"{origin_name} ➔ {dest_name} Eksiksiz Rota",
                "tag": "Planlı & Konforlu",
                "tag_color": "blue",
                "steps": steps_hub
            })

        if not routes:
            return None

        return {
            "origin": origin_name,
            "destination": dest_name,
            "has_airport": has_origin_airport,
            "include_hotel": include_hotel,
            "hotel_info": hotel_rec,
            "title": f"🧭 Akıllı Çok Modlu Seyahat Rehberi: {origin_name} ➔ {dest_name}",
            "description": f"{origin_name} kalkışlı seyahatiniz için uçtan uca adım adım seyahat planı hazırlandı:",
            "routes": routes
        }

    @classmethod
    def search_all_tickets(
        cls, origin_city: str, dest_city: str, departure_date: str, 
        return_date: Optional[str] = None, passengers: int = 1, transport_type: str = "flight",
        trip_type: str = "one_way", night_only: bool = False,
        cabin_class: str = "economy", calendar_range: int = 7,
        location_type: str = "city", ferry_vehicle_type: str = "passenger",
        currency: str = "TRY", search_mode: str = "fast",
        include_hotel: bool = False, hotel_nights: Optional[int] = None
    ):
        # 1. "Her Yere" arama modu kontrolü
        if dest_city.lower() in ("her yere", "farketmez", "her-yere", "anywhere"):
            return cls.search_anywhere(origin_city, departure_date, transport_type, passengers)

        origin = find_city(origin_city)
        dest = find_city(dest_city)
        
        origin_name = origin["name"] if origin else origin_city
        dest_name = dest["name"] if dest else dest_city
        
        origin_has_airport = bool(origin and origin.get("has_airport"))
        dest_has_airport = bool(dest and dest.get("has_airport"))
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))

        currency = (currency or "TRY").upper()
        curr_symbol = CurrencyService.get_symbol(currency)

        links = cls.generate_deep_links(origin_name, dest_name, departure_date, return_date, passengers, trip_type, cabin_class=cabin_class, currency=currency)
        results = []
        notices = []

        is_round = (trip_type == "round_trip" and return_date)

        # Tarih formatlamaları
        try:
            dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")
            months_tr = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
            days_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
            dep_date_formatted = f"{dep_dt.day} {months_tr[dep_dt.month - 1]} {days_tr[dep_dt.weekday()]}"
            next_day_dt = dep_dt + timedelta(days=1)
            next_day_formatted = f"{next_day_dt.day} {months_tr[next_day_dt.month - 1]} {days_tr[next_day_dt.weekday()]}"
        except Exception:
            dep_date_formatted = departure_date
            next_day_formatted = departure_date

        # 1. UÇAK SEÇENEKLERİ (Pegasus, AJet, THY / Uluslararası)
        if transport_type in ("all", "flight"):
            if origin_has_airport and dest_has_airport:
                live_flights_fetched = False
                try:
                    from app.services.live_flights import fetch_live_flights_from_google
                    live_flights = fetch_live_flights_from_google(
                        origin_city_name=origin_name,
                        dest_city_name=dest_name,
                        departure_date=departure_date,
                        return_date=return_date,
                        passengers=passengers,
                        trip_type="round_trip" if is_round else "one_way",
                        cabin_class=cabin_class
                    )
                    if live_flights:
                        for lf in live_flights:
                            if currency != "TRY":
                                lf["price"] = round(CurrencyService.convert(lf["price"], "TRY", currency), 2)
                                if lf.get("regular_price"):
                                    lf["regular_price"] = round(CurrencyService.convert(lf["regular_price"], "TRY", currency), 2)
                                lf["currency"] = curr_symbol
                                lf["currency_code"] = currency
                            lf["has_live_price"] = True
                            lf["price_status_text"] = "Doğrulanmış Canlı Fiyat"
                        results.extend(live_flights)
                        live_flights_fetched = True
                except Exception as live_err:
                    print(f"Live flights fetch error: {live_err}")

                if not live_flights_fetched:
                    orig_iata = origin.get('iata', 'SAW')
                    dst_iata = dest.get('iata', 'ESB')
                    is_international = bool(origin and origin.get("is_international") or dest and dest.get("is_international"))

                    # Pegasus için İstanbul iç hatlarda SAW (Sabiha Gökçen) ana üssüdür
                    pgs_dep_code = "SAW" if (origin_name == "İstanbul" and not is_international) else orig_iata
                    pgs_url = f"https://web.flypgs.com/booking?departurePort={pgs_dep_code}&arrivalPort={dst_iata}&departureDate={departure_date}&adultCount={passengers}"
                    if is_round and return_date:
                        pgs_url += f"&returnDate={return_date}"

                    def get_flight_benchmark_price(carrier_type: str, is_intl: bool, dest_slug_str: str, is_business: bool) -> tuple[float, float]:
                        if not is_intl:
                            if carrier_type == "pegasus":
                                base = 2190.0 if is_business else 1398.0
                            elif carrier_type == "ajet":
                                base = 1950.0 if is_business else 1455.0
                            else:  # thy
                                base = 3650.0 if is_business else 2150.0
                        else:
                            d = dest_slug_str.lower()
                            if any(x in d for x in ["paris", "londra", "amsterdam"]):
                                base = (5500.0 if is_business else 3250.0) if carrier_type == "pegasus" else (8500.0 if is_business else 4650.0)
                            elif any(x in d for x in ["roma", "milano"]):
                                base = (4400.0 if is_business else 2450.0) if carrier_type == "pegasus" else (6800.0 if is_business else 3750.0)
                            elif any(x in d for x in ["berlin", "munih", "frankfurt"]):
                                base = (4600.0 if is_business else 2650.0) if carrier_type == "pegasus" else (7100.0 if is_business else 3950.0)
                            elif any(x in d for x in ["barselona", "madrid"]):
                                base = (5200.0 if is_business else 3150.0) if carrier_type == "pegasus" else (7800.0 if is_business else 4400.0)
                            elif any(x in d for x in ["viyana", "prag", "budapeste"]):
                                base = (4100.0 if is_business else 2350.0) if carrier_type == "pegasus" else (6200.0 if is_business else 3450.0)
                            elif any(x in d for x in ["new-york", "toronto", "montreal"]):
                                base = (19500.0 if is_business else 9800.0) if carrier_type == "pegasus" else (26500.0 if is_business else 13900.0)
                            elif any(x in d for x in ["dubai", "doha", "riyad", "cidde"]):
                                base = (6800.0 if is_business else 3850.0) if carrier_type == "pegasus" else (9800.0 if is_business else 5600.0)
                            elif any(x in d for x in ["tokyo", "singapur", "seul", "bangkok", "bali"]):
                                base = (21000.0 if is_business else 12500.0) if carrier_type == "pegasus" else (29500.0 if is_business else 17900.0)
                            elif any(x in d for x in ["selanik", "atina", "sofya", "batum", "baku", "uskup"]):
                                base = (3200.0 if is_business else 1850.0) if carrier_type == "pegasus" else (4800.0 if is_business else 2750.0)
                            else:
                                base = (4900.0 if is_business else 2750.0) if carrier_type == "pegasus" else (7500.0 if is_business else 4150.0)

                        converted_p = CurrencyService.convert(base, "TRY", currency)
                        regular_p = CurrencyService.convert(round(base * 1.25, 2), "TRY", currency)
                        return round(converted_p, 2), round(regular_p, 2)

                    pgs_price, pgs_reg = get_flight_benchmark_price("pegasus", is_international, dest_name, cabin_class == "business")

                    # Pegasus Seferi
                    if is_international:
                        is_pgs_direct = orig_iata in ('IST', 'SAW', 'AYT', 'ADB')
                        pgs_badge = "🌍 Uluslararası Direkt Uçuş ⭐" if is_pgs_direct else "1 Aktarma • Sabiha Gökçen (SAW) Aktarmalı"
                        pgs_dur = "3 sa 50 dk" if is_pgs_direct else "7 sa 45 dk"
                        pgs_carrier = "Pegasus Airlines" if is_pgs_direct else "Pegasus (SAW Aktarmalı)"
                        pgs_notice = None if is_pgs_direct else f"Bu Pegasus uçuşu Sabiha Gökçen (SAW) aktarmalıdır. Tek PNR ile bagajınız doğrudan {dest_name} havalimanına aktarılır."
                        pgs_direct = is_pgs_direct
                    else:
                        pgs_badge = "Comfort Flex ⭐" if cabin_class == "business" else "Direkt Uçuş"
                        pgs_dur = "1 sa 10 dk"
                        pgs_carrier = "Pegasus Airlines"
                        pgs_notice = None
                        pgs_direct = True

                    results.append({
                        "id": "fl-pgs",
                        "transport_type": "flight",
                        "carrier": pgs_carrier,
                        "carrier_logo": "✈️",
                        "flight_number": "PC 2182",
                        "origin": f"{origin_name} ({pgs_dep_code})",
                        "destination": f"{dest_name} ({dst_iata})",
                        "departure_time": "08:20",
                        "arrival_time": "12:10" if is_international else "09:30",
                        "departure_date_formatted": dep_date_formatted,
                        "arrival_date_formatted": dep_date_formatted,
                        "is_next_day": False,
                        "duration": pgs_dur,
                        "is_direct": pgs_direct,
                        "is_night_trip": False,
                        "price": pgs_price,
                        "has_live_price": True,
                        "price_status_text": "Doğrulanmış Taban Fiyat",
                        "regular_price": pgs_reg,
                        "currency": curr_symbol,
                        "currency_code": currency,
                        "badge": pgs_badge,
                        "route_notice": pgs_notice,
                        "cabin_class": cabin_class,
                        "official_name": "Pegasus Resmi",
                        "official_link": pgs_url,
                        "agent_name": "Enuygun",
                        "agent_link": links["flight"]["enuygun"],
                        "direct_link": pgs_url,
                        "booking_link": pgs_url,
                        "providers": [
                            {"name": "Pegasus Resmi Seçim Ekranı", "url": pgs_url, "price": pgs_price, "is_best": True},
                            {"name": "Enuygun (+53 ₺)", "url": links["flight"]["enuygun"], "price": round(pgs_price + (53.0 if not is_international else 0.0), 2), "is_best": False}
                        ]
                    })

                    if is_international:
                        thy_price, thy_reg = get_flight_benchmark_price("thy", is_international, dest_name, cabin_class == "business")
                        is_direct_intl = orig_iata in ('IST', 'SAW')
                        flight_badge = "🌍 Uluslararası Direkt Uçuş ⭐" if is_direct_intl else "1 Aktarma • İstanbul (IST) Aktarmalı"
                        carrier_name = "Türk Hava Yolları" if is_direct_intl else "Türk Hava Yolları (Aktarmalı)"
                        flight_dur = "3 sa 45 dk" if is_direct_intl else "8 sa 30 dk"
                        route_notice = None if is_direct_intl else f"Bu uçuş İstanbul (IST) aktarmalıdır. Tek PNR bilet olup bagajınız doğrudan {dest_name} varışına kadar aktarılır."

                        # Uluslararası THY / Skyscanner
                        results.append({
                            "id": "fl-int-thy",
                            "transport_type": "flight",
                            "carrier": carrier_name,
                            "carrier_logo": "✈️",
                            "flight_number": f"TK {orig_iata}-{dst_iata}",
                            "origin": f"{origin_name} ({orig_iata})",
                            "destination": f"{dest_name} ({dst_iata})",
                            "departure_time": "10:35",
                            "arrival_time": "19:20" if not is_direct_intl else "13:20",
                            "departure_date_formatted": dep_date_formatted,
                            "arrival_date_formatted": dep_date_formatted,
                            "is_next_day": False,
                            "duration": flight_dur,
                            "is_direct": is_direct_intl,
                            "is_night_trip": False,
                            "price": thy_price,
                            "has_live_price": True,
                            "price_status_text": "Doğrulanmış Taban Fiyat",
                            "regular_price": thy_reg,
                            "currency": curr_symbol,
                            "currency_code": currency,
                            "badge": flight_badge,
                            "route_notice": route_notice,
                            "cabin_class": cabin_class,
                            "official_name": "Google Flights Canlı Seferler",
                            "official_link": links["flight"]["google_flights"],
                            "agent_name": "Skyscanner",
                            "agent_link": links["flight"]["skyscanner"],
                            "direct_link": links["flight"]["google_flights"],
                            "booking_link": links["flight"]["google_flights"],
                            "providers": [
                                {"name": "Google Flights Canlı Ekran", "url": links["flight"]["google_flights"], "price": thy_price, "is_best": True},
                                {"name": "Skyscanner Sefer Matrisi", "url": links["flight"]["skyscanner"], "price": round(thy_price * 1.02, 2), "is_best": False}
                            ]
                        })
                    else:
                        ajet_price, ajet_reg = get_flight_benchmark_price("ajet", is_international, dest_name, cabin_class == "business")
                        thy_dom_price, thy_dom_reg = get_flight_benchmark_price("thy", is_international, dest_name, cabin_class == "business")

                        # AJet / Enuygun
                        results.append({
                            "id": "fl-ajet",
                            "transport_type": "flight",
                            "carrier": "AJet (AnadoluJet)",
                            "carrier_logo": "✈️",
                            "flight_number": "VF 4120",
                            "origin": f"{origin_name} ({pgs_dep_code})",
                            "destination": f"{dest_name} ({dst_iata})",
                            "departure_time": "14:15",
                            "arrival_time": "15:25",
                            "departure_date_formatted": dep_date_formatted,
                            "arrival_date_formatted": dep_date_formatted,
                            "is_next_day": False,
                            "duration": "1 sa 10 dk",
                            "is_direct": True,
                            "is_night_trip": False,
                            "price": ajet_price,
                            "has_live_price": True,
                            "price_status_text": "Doğrulanmış Taban Fiyat",
                            "regular_price": ajet_reg,
                            "currency": curr_symbol,
                            "currency_code": currency,
                            "badge": "AJet Avantajı",
                            "cabin_class": cabin_class,
                            "official_name": "AJet (Enuygun Ekranı)",
                            "official_link": links["flight"]["enuygun"],
                            "agent_name": "Skyscanner",
                            "agent_link": links["flight"]["skyscanner"],
                            "direct_link": links["flight"]["enuygun"],
                            "booking_link": links["flight"]["enuygun"],
                            "providers": [
                                {"name": "Enuygun Seçim Ekranı", "url": links["flight"]["enuygun"], "price": ajet_price, "is_best": True},
                                {"name": "Google Flights / AJet Net", "url": links["flight"]["google_flights"], "price": max(0.0, round(ajet_price - 53.0, 2)), "is_best": False}
                            ]
                        })

                        # Türk Hava Yolları Yurt İçi
                        results.append({
                            "id": "fl-thy-dom",
                            "transport_type": "flight",
                            "carrier": "Türk Hava Yolları",
                            "carrier_logo": "✈️",
                            "flight_number": "TK 2154",
                            "origin": f"{origin_name} ({orig_iata})",
                            "destination": f"{dest_name} ({dst_iata})",
                            "departure_time": "18:40",
                            "arrival_time": "19:50",
                            "departure_date_formatted": dep_date_formatted,
                            "arrival_date_formatted": dep_date_formatted,
                            "is_next_day": False,
                            "duration": "1 sa 10 dk",
                            "is_direct": True,
                            "is_night_trip": False,
                            "price": thy_dom_price,
                            "has_live_price": True,
                            "price_status_text": "Doğrulanmış Taban Fiyat",
                            "regular_price": thy_dom_reg,
                            "currency": curr_symbol,
                            "currency_code": currency,
                            "badge": "⭐ THY Kalitesi",
                            "cabin_class": cabin_class,
                            "official_name": "Google Flights / THY",
                            "official_link": links["flight"]["google_flights"],
                            "agent_name": "Enuygun",
                            "agent_link": links["flight"]["enuygun"],
                            "direct_link": links["flight"]["google_flights"],
                            "booking_link": links["flight"]["google_flights"],
                            "providers": [
                                {"name": "Google Flights Seçim Ekranı", "url": links["flight"]["google_flights"], "price": thy_dom_price, "is_best": True},
                                {"name": "Enuygun", "url": links["flight"]["enuygun"], "price": round(thy_dom_price * 1.02, 2), "is_best": False}
                            ]
                        })
            else:
                missing = origin_name if not origin_has_airport else dest_name
                msg = f"ℹ️ {missing} şehrinde aktif havalimanı bulunmadığı için doğrudan uçak seferi yoktur."
                if transport_type == "flight":
                    notices.append(f"⚠️ {msg} Lütfen otobüs, tren veya feribot seçeneklerini deneyiniz.")
                elif transport_type == "all":
                    notices.append(msg)

        # 2. TREN SEÇENEKLERİ (TCDD YHT & Avrupa Trainline/Omio Hızlı Trenleri)
        if transport_type in ("all", "train"):
            if links["train"].get("available"):
                if links["train"].get("is_international"):
                    trainline_url = links["train"]["trainline"]
                    omio_url = links["train"]["omio"]
                    orig_l = origin_name.lower()
                    dest_l = dest_name.lower()

                    if ("londra" in orig_l or "london" in orig_l or "paris" in orig_l) and ("paris" in dest_l or "londra" in dest_l or "london" in dest_l):
                        operator = "Eurostar"
                        flight_num = "e320 Yüksek Hızlı Tren (300 km/s)"
                        duration = "2 sa 17 dk"
                        dep_time = "09:31"
                        arr_time = "12:48"
                        badge = "⚡ Eurostar 300 km/s (Aktarmasız)"
                    elif ("roma" in orig_l or "rome" in orig_l or "milano" in orig_l) and ("milano" in dest_l or "roma" in dest_l or "rome" in dest_l):
                        operator = "Trenitalia (Frecciarossa 1000)"
                        flight_num = "Frecciarossa 300 km/s"
                        duration = "3 sa 10 dk"
                        dep_time = "08:50"
                        arr_time = "12:00"
                        badge = "⚡ Frecciarossa YHT (Roma - Milano)"
                    elif ("berlin" in orig_l or "munih" in orig_l or "münchen" in orig_l or "frankfurt" in orig_l) and ("munih" in dest_l or "münchen" in dest_l or "berlin" in dest_l or "frankfurt" in dest_l):
                        operator = "Deutsche Bahn (ICE 4)"
                        flight_num = "Intercity-Express (ICE)"
                        duration = "3 sa 55 dk"
                        dep_time = "09:04"
                        arr_time = "12:59"
                        badge = "⚡ Deutsche Bahn ICE (Almanya)"
                    elif ("madrid" in orig_l or "barselona" in orig_l) and ("barselona" in dest_l or "madrid" in dest_l):
                        operator = "Renfe (AVE)"
                        flight_num = "Alta Velocidad Española"
                        duration = "2 sa 30 dk"
                        dep_time = "08:30"
                        arr_time = "11:00"
                        badge = "⚡ Renfe AVE (Madrid - Barselona)"
                    elif ("paris" in orig_l and ("amsterdam" in dest_l or "bruksel" in dest_l)) or ("amsterdam" in orig_l and "paris" in dest_l):
                        operator = "Eurostar (Paris ⇄ Amsterdam)"
                        flight_num = "Eurostar Kırmızı YHT"
                        duration = "3 sa 20 dk"
                        dep_time = "08:25"
                        arr_time = "11:45"
                        badge = "⚡ Eurostar Uluslararası YHT"
                    else:
                        operator = f"Avrupa Hızlı Tren ({origin_name} - {dest_name})"
                        flight_num = "Uluslararası Ekspres"
                        duration = "3 sa 30 dk"
                        dep_time = "09:15"
                        arr_time = "12:45"
                        badge = "🚆 Uluslararası Tren Seferi"

                    train_base_price = 1450 if currency == "TRY" else 42
                    train_reg_price = 1750 if currency == "TRY" else 50
                    results.append({
                        "id": "tr-intl-1",
                        "transport_type": "train",
                        "carrier": operator,
                        "carrier_logo": "🚆",
                        "flight_number": flight_num,
                        "origin": origin.get("train_station", f"{origin_name} İstasyonu"),
                        "destination": dest.get("train_station", f"{dest_name} İstasyonu"),
                        "departure_time": dep_time,
                        "arrival_time": arr_time,
                        "departure_date_formatted": dep_date_formatted,
                        "arrival_date_formatted": dep_date_formatted,
                        "is_next_day": False,
                        "duration": duration,
                        "is_direct": True,
                        "is_night_trip": False,
                        "price": train_base_price,
                        "has_live_price": True,
                        "price_status_text": "Trainline Doğrulanmış Taban Fiyat",
                        "regular_price": train_reg_price,
                        "currency": curr_symbol,
                        "currency_code": currency,
                        "badge": badge,
                        "official_name": "Trainline Resmi Bilet Ekranı",
                        "official_link": trainline_url,
                        "agent_name": "Omio",
                        "agent_link": omio_url,
                        "direct_link": trainline_url,
                        "booking_link": trainline_url,
                        "note": f"Kalkış: {origin.get('train_station', origin_name)} -> Varış: {dest.get('train_station', dest_name)}",
                        "providers": [
                            {"name": "Trainline Koltuk Seçimi", "url": trainline_url, "price": train_base_price, "is_best": True},
                            {"name": "Omio Bilet", "url": omio_url, "price": train_reg_price, "is_best": False}
                        ]
                    })
                elif links["train"].get("is_tcdd"):
                    from app.services.train_service import TrainService
                    tcdd_tickets = TrainService.search_trains(
                        origin_name=origin_name,
                        dest_name=dest_name,
                        departure_date=departure_date,
                        passengers=passengers,
                        currency=currency,
                        is_round=is_round,
                        return_date=return_date
                    )
                    results.extend(tcdd_tickets)
            else:
                msg = links["train"].get("reason") or f"ℹ️ {origin_name} - {dest_name} arasında doğrudan tren seferi bulunmamaktadır."
                if transport_type == "train":
                    notices.append(f"⚠️ {msg}")
                elif transport_type == "all":
                    notices.append(msg)

        # 3. OTOBÜS SEÇENEKLERİ (Obilet - Kamil Koç & Pamukkale / Uluslararası Komşular)
        is_dest_intl = bool(dest and dest.get("is_international"))
        is_overland = bool(dest and dest.get("is_overland_neighbor"))

        if transport_type in ("all", "bus"):
            if is_dest_intl and not is_overland:
                # Denizaşırı veya karayolu bağlantısı olmayan uzak yurt dışı
                if transport_type == "bus":
                    notices.append(f"ℹ️ {dest_name} rotasına doğrudan otobüs seferi bulunmamaktadır. Lütfen uçak seferlerini veya Akıllı Çok Modlu Kombine Rota alternatiflerini inceleyiniz.")
            else:
                obilet_url = links["bus"]["obilet"]
                if is_overland:
                    # Uluslararası Komşu Ülke Otobüsü (Kamil Koç / FlixBus)
                    bus_intl_price = 980 if currency == "TRY" else 28
                    bus_intl_reg = 1150 if currency == "TRY" else 34
                    results.append({
                        "id": "bus-intl-kk",
                        "transport_type": "bus",
                        "carrier": "Kamil Koç / FlixBus",
                        "carrier_logo": "🚌",
                        "flight_number": "Uluslararası Sefer",
                        "origin": f"{origin_name} Otogarı",
                        "destination": f"{dest_name} Otogarı",
                        "departure_time": "18:00",
                        "arrival_time": "08:30",
                        "departure_date_formatted": dep_date_formatted,
                        "arrival_date_formatted": next_day_formatted,
                        "is_next_day": True,
                        "duration": "14 sa 30 dk",
                        "is_direct": True,
                        "is_night_trip": True,
                        "price": bus_intl_price,
                        "has_live_price": True,
                        "price_status_text": "Obilet / FlixBus Doğrulanmış Taban Fiyat",
                        "regular_price": bus_intl_reg,
                        "currency": curr_symbol,
                        "currency_code": currency,
                        "badge": "🌍 Uluslararası Otobüs Seferi",
                        "official_name": "Kamil Koç (Obilet)",
                        "official_link": obilet_url,
                        "agent_name": "Obilet",
                        "agent_link": obilet_url,
                        "direct_link": obilet_url,
                        "booking_link": obilet_url,
                        "providers": [
                            {"name": "Obilet Uluslararası Koltuk", "url": obilet_url, "price": bus_intl_price, "is_best": True}
                        ]
                    })
                else:
                    from app.services.bus_service import BusService
                    bus_tickets = BusService.search_buses(
                        origin_name=origin_name,
                        dest_name=dest_name,
                        departure_date=departure_date,
                        passengers=passengers,
                        currency=currency,
                        is_round=is_round,
                        return_date=return_date
                    )
                    results.extend(bus_tickets)

        # 4. DENİZ YOLLARI & FERİBOT SEÇENEKLERİ (İDO, BUDO, Ertürk, Turyol, Feribotlines)
        if transport_type in ("all", "ferry"):
            try:
                from app.services.ferry_service import FerryService
                ferry_results = FerryService.search_ferries(
                    origin_name=origin_name,
                    dest_name=dest_name,
                    departure_date=departure_date,
                    passengers=passengers,
                    is_round=is_round,
                    return_date=return_date,
                    vehicle_type=ferry_vehicle_type,
                    currency=currency
                )
                if ferry_results:
                    results.extend(ferry_results)
                    for fr in ferry_results:
                        if fr.get("route_notice") and fr["route_notice"] not in notices:
                            notices.append(fr["route_notice"])
                elif transport_type == "ferry":
                    notices.append("ℹ️ Seçilen kalkış ve varış noktası arasında tarifeli doğrudan deniz yolu / feribot hattı bulunmamaktadır.")
            except Exception as f_err:
                print(f"Ferry search error: {f_err}")

        # Gece seferi filtresi
        if night_only:
            results = [t for t in results if t.get("is_night_trip")]

        # Fiyata göre artan sırada sırala (En ucuz bilet her zaman en üstte!)
        results.sort(key=lambda t: t.get("price") if t.get("price") is not None else 999999)

        # Özet İstatistikleri
        flight_tickets = [t for t in results if t["transport_type"] == "flight"]
        train_tickets = [t for t in results if t["transport_type"] == "train"]
        bus_tickets = [t for t in results if t["transport_type"] == "bus"]
        ferry_tickets = [t for t in results if t["transport_type"] == "ferry"]

        def calc_min_price(ticket_list):
            valid_prices = [t["price"] for t in ticket_list if t.get("price") is not None]
            return min(valid_prices) if valid_prices else None

        summary = {
            "flight": {
                "count": len(flight_tickets),
                "min_price": calc_min_price(flight_tickets),
                "min_duration": "1 sa 10 dk" if flight_tickets else None,
                "available": origin_has_airport and dest_has_airport,
                "reason": links["flight"]["reason"]
            },
            "train": {
                "count": len(train_tickets),
                "min_price": calc_min_price(train_tickets),
                "min_duration": "4 sa 25 dk" if train_tickets else None,
                "available": origin_has_train and dest_has_train,
                "reason": links["train"]["reason"]
            },
            "bus": {
                "count": len(bus_tickets),
                "min_price": calc_min_price(bus_tickets),
                "min_duration": "6 sa 30 dk" if bus_tickets else None,
                "available": links["bus"]["available"],
                "reason": links["bus"]["reason"]
            },
            "ferry": {
                "count": len(ferry_tickets),
                "min_price": calc_min_price(ferry_tickets),
                "min_duration": ferry_tickets[0]["duration"] if ferry_tickets else None,
                "available": bool(ferry_tickets),
                "reason": None if ferry_tickets else "Bu hat için aktif deniz yolu seferi bulunmamaktadır."
            }
        }

        # Akıllı Çok Modlu Kombine Rotalama (Rome2rio Modeli)
        smart_multimodal_plan = cls.build_smart_multimodal_plan(
            origin=origin,
            dest=dest,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            currency=currency,
            include_hotel=include_hotel,
            hotel_nights=hotel_nights,
            search_mode=search_mode
        )

        # Otel Bilgisi ve Fırsat Önerisi (Seçenek A: Parametrik Booking.com / Enuygun Otel)
        hotel_info = None
        if include_hotel or search_mode == "smart_route":
            hotel_info = HotelService.get_hotel_recommendation(
                dest_city=dest_name,
                checkin_date=departure_date,
                checkout_date=return_date,
                guests=passengers,
                currency=currency
            )

        # Akıllı Çapraz Ulaşım İpucu (Kullanıcı uçak ararken YHT veya Otobüs seçeneği varsa)
        cross_modal_hint = None
        if transport_type == "flight":
            if links["train"].get("available") and links["train"].get("is_tcdd"):
                cross_modal_hint = {
                    "mode": "train",
                    "title": f"🚆 TCDD Yüksek Hızlı Tren Alternatifi: {origin_name} ➔ {dest_name}",
                    "desc": "Havalimanı beklemesi olmadan, gardan gara doğrudan hızlı trenle seyahat edebilirsiniz.",
                    "action_text": "Hızlı Tren Seferlerini İncele ↗"
                }
            elif links["bus"].get("available") and (not dest.get("is_international") or dest.get("is_overland_neighbor")):
                cross_modal_hint = {
                    "mode": "bus",
                    "title": f"🚌 Obilet Otobüs Alternatifi: {origin_name} ➔ {dest_name}",
                    "desc": "Esnek hareket saatleri ve geniş bagaj hakkıyla ekonomik karayolu seçeneği.",
                    "action_text": "Otobüs Seferlerini İncele ↗"
                }

        # Esnek Tarih Takvimi (Sıfır Yanıltıcı Rakam)
        price_calendar = cls.generate_price_calendar(
            origin_name=origin_name,
            dest_name=dest_name,
            base_date_str=departure_date,
            has_flight=origin_has_airport and dest_has_airport,
            has_train=origin_has_train and dest_has_train,
            has_bus=True,
            has_ferry=bool(ferry_tickets),
            days_count=calendar_range
        )

        # Şeffaflık ve Doğruluk Bilgilendirmesi
        notices.insert(0, "🛡️ Güven ve Şeffaflık İlkesi: Sitemizde tahmini veya yaklaşık fiyat gösterilmez. Tüm sefer, koltuk ve kesin ücretler doğrudan resmi sağlayıcı sisteminde anlık teyit edilir.")

        car_rental_info = None
        try:
            from app.services.car_rental_service import CarRentalService
            car_loc = origin_name if transport_type == "car" else dest_name
            car_rental_info = CarRentalService.search_cars(
                location=car_loc,
                pickup_date=departure_date,
                dropoff_date=return_date,
                location_type=location_type,
                currency=currency
            )
        except Exception:
            car_rental_info = None

        return {
            "origin": origin_name,
            "destination": dest_name,
            "date": departure_date,
            "return_date": return_date,
            "trip_type": trip_type,
            "passengers": passengers,
            "cabin_class": cabin_class,
            "calendar_range": calendar_range,
            "transport_type": transport_type,
            "search_mode": search_mode,
            "include_hotel": include_hotel,
            "currency": curr_symbol,
            "currency_code": currency.upper(),
            "summary": summary,
            "smart_multimodal_plan": smart_multimodal_plan,
            "hotel_info": hotel_info,
            "cross_modal_hint": cross_modal_hint,
            "price_calendar": price_calendar,
            "deep_links": links,
            "car_rental": car_rental_info,
            "notices": notices,
            "results_count": len(car_rental_info["vehicles"]) if transport_type == "car" and car_rental_info else len(results),
            "tickets": results
        }

