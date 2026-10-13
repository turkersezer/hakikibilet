import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.cities import find_city, TURKEY_CITIES

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
        base_flight_price: float = 1397.0, base_train_price: float = 430.0, base_bus_price: float = 480.0,
        has_flight: bool = True, has_train: bool = True, has_bus: bool = True,
        days_count: int = 7
    ):
        """
        Gezgin Modu (Tasarım A): Seçilen aralıktaki her gün için 3 seyahat aracının fiyatı
        ve dönem içindeki 'Kategori Şampiyonları' (En Ucuz Otobüs, En Ucuz Uçak, En Ucuz Tren)
        """
        try:
            base_dt = datetime.strptime(base_date_str, "%Y-%m-%d")
        except Exception:
            base_dt = datetime.now() + timedelta(days=7)

        turkish_day_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        turkish_month_names = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        
        # Haftalık dinamik dalgalanma faktörleri (Salı-Çarşamba en ucuz, Cuma-Pazar pahalı)
        flight_factors = [1.02, 0.85, 0.89, 0.95, 1.38, 1.30, 1.18]
        bus_factors = [1.00, 0.73, 0.79, 0.90, 1.25, 1.20, 1.15]
        train_factors = [1.00, 0.82, 0.82, 1.00, 1.05, 1.05, 1.00] # TCDD promosyonlu günler

        # Gün aralığı belirleme (-1 günden başlayarak days_count kadar)
        start_offset = 0 if days_count > 7 else -1
        calendar = []
        
        min_flight_val = float("inf")
        min_train_val = float("inf")
        min_bus_val = float("inf")
        min_overall_val = float("inf")

        for offset in range(start_offset, start_offset + days_count):
            day_dt = base_dt + timedelta(days=offset)
            if day_dt < datetime.now() - timedelta(days=1):
                continue
            
            day_idx = day_dt.weekday()
            
            # Fiyat hesaplamaları
            f_price = round((base_flight_price * flight_factors[day_idx]) / 10) * 10 if has_flight else None
            t_price = round((base_train_price * train_factors[day_idx]) / 10) * 10 if has_train else None
            b_price = round((base_bus_price * bus_factors[day_idx]) / 10) * 10 if has_bus else None

            # Minimum takibi
            if f_price and f_price < min_flight_val:
                min_flight_val = f_price
            if t_price and t_price < min_train_val:
                min_train_val = t_price
            if b_price and b_price < min_bus_val:
                min_bus_val = b_price

            day_avail_prices = [p for p in (f_price, t_price, b_price) if p is not None]
            day_min_price = min(day_avail_prices) if day_avail_prices else 0
            if day_min_price and day_min_price < min_overall_val:
                min_overall_val = day_min_price

            day_min_mode = "bus"
            if b_price == day_min_price:
                day_min_mode = "bus"
            elif t_price == day_min_price:
                day_min_mode = "train"
            elif f_price == day_min_price:
                day_min_mode = "flight"

            calendar.append({
                "date": day_dt.strftime("%Y-%m-%d"),
                "day_name": turkish_day_names[day_idx],
                "day_num": day_dt.strftime("%d"),
                "month_name": turkish_month_names[day_dt.month - 1],
                "is_selected": (day_dt.strftime("%Y-%m-%d") == base_date_str),
                "is_weekend": day_idx in (4, 5, 6),
                "prices": {
                    "flight": f_price,
                    "train": t_price,
                    "bus": b_price
                },
                "has_flight": has_flight,
                "has_train": has_train,
                "has_bus": has_bus,
                "day_min_price": day_min_price,
                "day_min_mode": day_min_mode,
                "is_cheapest_flight": False,
                "is_cheapest_train": False,
                "is_cheapest_bus": False,
                "is_overall_cheapest": False
            })

        # Kategori Şampiyonlarını İşaretle
        best_flight_day = None
        best_bus_day = None
        best_train_day = None

        for item in calendar:
            if item["prices"]["flight"] == min_flight_val and not best_flight_day:
                item["is_cheapest_flight"] = True
                best_flight_day = item
            if item["prices"]["train"] == min_train_val and not best_train_day:
                item["is_cheapest_train"] = True
                best_train_day = item
            if item["prices"]["bus"] == min_bus_val and not best_bus_day:
                item["is_cheapest_bus"] = True
                best_bus_day = item
            if item["day_min_price"] == min_overall_val:
                item["is_overall_cheapest"] = True

        tip_parts = []
        if best_flight_day:
            tip_parts.append(f"✈️ Uçuş için en uygun gün: {best_flight_day['day_num']} {best_flight_day['month_name']} {best_flight_day['day_name']} ({best_flight_day['prices']['flight']} ₺)")
        if best_bus_day:
            tip_parts.append(f"🚌 Otobüs için en uygun gün: {best_bus_day['day_num']} {best_bus_day['month_name']} {best_bus_day['day_name']} ({best_bus_day['prices']['bus']} ₺)")
        if best_train_day:
            tip_parts.append(f"🚆 Tren için en uygun gün: {best_train_day['day_num']} {best_train_day['month_name']} {best_train_day['day_name']} ({best_train_day['prices']['train']} ₺)")

        tip_text = " • ".join(tip_parts) if tip_parts else "💡 Seçtiğiniz dönem seyahat için en avantajlı tarihlerden biridir."

        return {
            "days": calendar,
            "days_count": len(calendar),
            "range_type": days_count,
            "min_flight_val": min_flight_val if min_flight_val != float("inf") else None,
            "min_train_val": min_train_val if min_train_val != float("inf") else None,
            "min_bus_val": min_bus_val if min_bus_val != float("inf") else None,
            "min_overall_val": min_overall_val if min_overall_val != float("inf") else None,
            "tip": f"💡 Gezgin Analizi: {tip_text}"
        }

    @classmethod
    def generate_deep_links(
        cls, origin_city_name: str, dest_city_name: str, departure_date: str, 
        return_date: Optional[str] = None, passengers: int = 1, trip_type: str = "one_way",
        cabin_class: str = "economy"
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

        is_round = (trip_type == "round_trip" and return_date)
        is_biz = (cabin_class == "business")
        sky_cabin = "business" if is_biz else "economy"
        biz_extra_google = "+business" if is_biz else ""
        biz_extra_enuygun = "&sinif=business" if is_biz else ""

        # 1. Uçak Deep Linkleri
        flight_links = {
            "available": origin_has_airport and dest_has_airport,
            "reason": None if (origin_has_airport and dest_has_airport) else f"{origin_city_name if not origin_has_airport else dest_city_name} şehrinde aktif havalimanı bulunmamaktadır."
        }
        if flight_links["available"]:
            enuygun_route = f"{origin_slug}-{dest_slug}-{origin_iata.lower()}a-{dest_iata.lower()}a"
            if is_round:
                sky_ret = cls.format_date_for_skyscanner(return_date)
                enuygun_ret = cls.format_date_for_enuygun(return_date)
                flight_links["skyscanner"] = f"https://www.skyscanner.com.tr/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{sky_dep}/{sky_ret}/?adultsv2={passengers}&cabinclass={sky_cabin}&rtn=1"
                flight_links["google_flights"] = f"https://www.google.com/travel/flights?q=flights+from+{origin_iata}+to+{dest_iata}+on+{departure_date}+through+{return_date}{biz_extra_google}"
                flight_links["enuygun"] = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep}&donus={enuygun_ret}&yetiskin={passengers}{biz_extra_enuygun}"
            else:
                flight_links["skyscanner"] = f"https://www.skyscanner.com.tr/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{sky_dep}/?adultsv2={passengers}&cabinclass={sky_cabin}&rtn=0"
                flight_links["google_flights"] = f"https://www.google.com/travel/flights?q=flights+from+{origin_iata}+to+{dest_iata}+on+{departure_date}{biz_extra_google}"
                flight_links["enuygun"] = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep}&yetiskin={passengers}{biz_extra_enuygun}"
        else:
            flight_links["skyscanner"] = None
            flight_links["google_flights"] = None
            flight_links["enuygun"] = None

        # 2. Tren Deep Linkleri (TCDD)
        train_links = {
            "available": origin_has_train and dest_has_train,
            "reason": None if (origin_has_train and dest_has_train) else f"{origin_city_name if not origin_has_train else dest_city_name} bölgesinde TCDD tren istasyonu veya demiryolu hattı bulunmamaktadır.",
            "tcdd": "https://ebilet.tcddtasimacilik.gov.tr/" if (origin_has_train and dest_has_train) else None,
            "tcdd_search_hint": f"Kalkış: {origin.get('train_station')} -> Varış: {dest.get('train_station')}" if (origin_has_train and dest_has_train) else "Demiryolu hattı yok"
        }

        # 3. Otobüs Deep Linkleri
        bus_ret_query = f"?donus-tarihi={return_date}" if is_round else ""
        bus_links = {
            "available": True,
            "reason": None,
            "obilet": f"https://www.obilet.com/otobus-bileti/{origin_slug}-{dest_slug}/{departure_date}{bus_ret_query}",
            "kamilkoc": "https://www.kamilkoc.com.tr/",
            "pamukkale": "https://www.pamukkale.com.tr/"
        }

        return {
            "flight": flight_links,
            "train": train_links,
            "bus": bus_links
        }

    @classmethod
    def search_anywhere(cls, origin_city: str, departure_date: str, transport_type: str = "all", passengers: int = 1):
        """
        Gezgin Modu: Varış noktası 'Her Yere' seçildiğinde en ucuz yurt içi rotaları listeler
        """
        origin = find_city(origin_city)
        origin_name = origin["name"] if origin else origin_city

        destinations = [
            {"dest": "Eskişehir", "type": "train", "carrier": "TCDD YHT", "logo": "🚆", "price": 280.0, "duration": "3 sa", "badge": "Gezgin Favorisi"},
            {"dest": "Bursa", "type": "bus", "carrier": "Kamil Koç", "logo": "🚌", "price": 220.0, "duration": "2 sa 15 dk", "badge": "Hafta Sonu Kaçamağı"},
            {"dest": "İzmir", "type": "flight", "carrier": "Pegasus", "logo": "✈️", "price": 499.0, "duration": "1 sa 10 dk", "badge": "Flaş Uçuş İndirimi"},
            {"dest": "Konya", "type": "train", "carrier": "TCDD YHT", "logo": "🚆", "price": 310.0, "duration": "4 sa 45 dk", "badge": "Kültür Rotası"},
            {"dest": "Antalya", "type": "flight", "carrier": "AJet", "logo": "✈️", "price": 649.0, "duration": "1 sa 20 dk", "badge": "Güneş Kaçamağı"},
            {"dest": "Kars", "type": "train", "carrier": "Doğu Ekspresi", "logo": "🚆", "price": 400.0, "duration": "24 sa", "badge": "Efsane Macera"},
            {"dest": "Trabzon", "type": "flight", "carrier": "THY", "logo": "✈️", "price": 890.0, "duration": "1 sa 40 dk", "badge": "Karadeniz Turu"}
        ]

        if transport_type != "all":
            destinations = [d for d in destinations if d["type"] == transport_type]

        tickets = []
        for i, d in enumerate(destinations):
            links = cls.generate_deep_links(origin_name, d["dest"], departure_date, passengers=passengers)
            
            if d["type"] == "flight":
                if "pegasus" in d["carrier"].lower():
                    orig_city_obj = find_city(origin_name)
                    dest_city_obj = find_city(d["dest"])
                    orig_iata = orig_city_obj.get("iata", "SAW") if orig_city_obj else "SAW"
                    dest_iata = dest_city_obj.get("iata", "ADB") if dest_city_obj else "ADB"
                    official_link = f"https://web.flypgs.com/booking?departurePort={orig_iata}&arrivalPort={dest_iata}&departureDate={departure_date}&adultCount={passengers}"
                    official_name = "Pegasus Resmi"
                elif "ajet" in d["carrier"].lower():
                    official_link = "https://ajet.com/tr"
                    official_name = "AJet Resmi"
                else:
                    official_link = "https://www.turkishairlines.com/tr-int/"
                    official_name = "THY Resmi"
                agent_name = "Enuygun"
                agent_link = links["flight"]["enuygun"]
            elif d["type"] == "train":
                official_link = links["train"]["tcdd"]
                official_name = "TCDD Taşımacılık"
                agent_name = "TCDD E-Bilet"
                agent_link = links["train"]["tcdd"]
            else:
                official_name = f"{d['carrier']} Resmi"
                official_link = "https://www.kamilkoc.com.tr/" if "kamil" in d["carrier"].lower() else "https://www.pamukkale.com.tr/"
                agent_name = "Obilet"
                agent_link = links["bus"]["obilet"]

            tickets.append({
                "id": f"anywhere-{i}",
                "transport_type": d["type"],
                "carrier": d["carrier"],
                "carrier_logo": d["logo"],
                "flight_number": "Keşif Seferi",
                "origin": origin_name,
                "destination": d["dest"],
                "departure_time": "09:00",
                "arrival_time": "12:00",
                "duration": d["duration"],
                "is_direct": True,
                "price": d["price"] * passengers,
                "regular_price": (d["price"] * 1.8) * passengers,
                "currency": "₺",
                "badge": d["badge"],
                "official_name": official_name,
                "official_link": official_link,
                "agent_name": agent_name,
                "agent_link": agent_link,
                "direct_link": official_link,
                "is_night_trip": False
            })

        tickets.sort(key=lambda x: x["price"])
        return {
            "origin": origin_name,
            "destination": "Her Yere (En Ucuz Rotalar)",
            "date": departure_date,
            "passengers": passengers,
            "transport_type": transport_type,
            "is_anywhere": True,
            "summary": {
                "flight": {"count": len([t for t in tickets if t["transport_type"] == "flight"]), "min_price": 499.0, "min_duration": "1 sa 10 dk", "available": True},
                "train": {"count": len([t for t in tickets if t["transport_type"] == "train"]), "min_price": 280.0, "min_duration": "3 sa", "available": True},
                "bus": {"count": len([t for t in tickets if t["transport_type"] == "bus"]), "min_price": 220.0, "min_duration": "2 sa 15 dk", "available": True}
            },
            "deep_links": {"flight": {"available": True}, "train": {"available": True}, "bus": {"available": True}},
            "notices": ["🌍 Gezgin Keşif Modu: Seçtiğiniz kalkış noktasından Türkiye geneli en ucuz bilet fırsatları listelendi."],
            "results_count": len(tickets),
            "tickets": tickets
        }

    @classmethod
    def search_all_tickets(
        cls, origin_city: str, dest_city: str, departure_date: str, 
        return_date: Optional[str] = None, passengers: int = 1, transport_type: str = "all",
        trip_type: str = "one_way", night_only: bool = False,
        cabin_class: str = "economy", calendar_range: int = 7
    ):
        # 1. "Her Yere" arama modu kontrolü
        if dest_city.lower() in ("her yere", "farketmez", "her-yere", "anywhere"):
            return cls.search_anywhere(origin_city, departure_date, transport_type, passengers)

        origin = find_city(origin_city)
        dest = find_city(dest_city)
        
        origin_name = origin["name"] if origin else origin_city
        dest_name = dest["name"] if dest else dest_city
        
        links = cls.generate_deep_links(origin_name, dest_name, departure_date, return_date, passengers, trip_type, cabin_class=cabin_class)
        
        results = []
        notices = []

        origin_has_airport = bool(origin and origin.get("has_airport"))
        dest_has_airport = bool(dest and dest.get("has_airport"))
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))

        is_round = (trip_type == "round_trip" and return_date)
        round_multiplier = 1.85 if is_round else 1.0 # Gidiş-dönüş kombine indirim oranı

        # Tarih formatlamaları
        try:
            dep_date_dt = datetime.strptime(departure_date, "%Y-%m-%d")
        except Exception:
            dep_date_dt = datetime.now()

        months_tr = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        days_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

        dep_date_formatted = f"{dep_date_dt.day} {months_tr[dep_date_dt.month - 1]} {days_tr[dep_date_dt.weekday()]}"
        next_day_dt = dep_date_dt + timedelta(days=1)
        next_day_formatted = f"{next_day_dt.day} {months_tr[next_day_dt.month - 1]} {days_tr[next_day_dt.weekday()]}"

        # 1. UÇAK SEÇENEKLERİ (CANLI GOOGLE FLIGHTS & HAVAYOLU REZERVASYON MOTORU)
        if transport_type in ("all", "flight"):
            if origin_has_airport and dest_has_airport:
                live_flights = []
                try:
                    from app.services.live_flights import fetch_live_flights_from_google
                    live_flights = fetch_live_flights_from_google(
                        origin_city_name=origin_name,
                        dest_city_name=dest_name,
                        departure_date=departure_date,
                        return_date=return_date,
                        passengers=passengers,
                        trip_type=trip_type,
                        cabin_class=cabin_class
                    )
                except Exception as ex:
                    print(f"Live flights fetch error: {ex}")

                if live_flights:
                    results.extend(live_flights)
                else:
                    # Canlı servis yanıt vermezse güncel piyasa tabanlı akıllı yedek
                    orig_iata = origin.get('iata', 'SAW')
                    dst_iata = dest.get('iata', 'ESB')
                    pgs_url = f"https://web.flypgs.com/booking?departurePort={orig_iata}&arrivalPort={dst_iata}&departureDate={departure_date}&adultCount={passengers}"
                    if is_round and return_date:
                        pgs_url += f"&returnDate={return_date}"

                    base_seat_price = 3500.0 if cabin_class == "business" else 1397.0
                    est_flight_price = base_seat_price * (2.0 if is_round else 1.0) * passengers
                    results.append({
                        "id": "fl-pgs-fallback",
                        "transport_type": "flight",
                        "carrier": "Pegasus Airlines",
                        "carrier_logo": "✈️",
                        "flight_number": "PC 2182",
                        "origin": f"{origin_name} ({orig_iata})",
                        "destination": f"{dest_name} ({dst_iata})",
                        "departure_time": "08:20",
                        "arrival_time": "09:30",
                        "departure_date_formatted": dep_date_formatted,
                        "arrival_date_formatted": dep_date_formatted,
                        "is_next_day": False,
                        "duration": "1 sa 10 dk",
                        "is_direct": True,
                        "is_night_trip": False,
                        "price": est_flight_price,
                        "regular_price": est_flight_price * 1.3,
                        "currency": "₺",
                        "badge": "Comfort Flex ⭐" if cabin_class == "business" else "Pegasus Seferi",
                        "cabin_class": cabin_class,
                        "official_name": "Pegasus Resmi",
                        "official_link": pgs_url,
                        "agent_name": "Enuygun",
                        "agent_link": links["flight"]["enuygun"],
                        "direct_link": pgs_url
                    })
            else:
                missing = origin_name if not origin_has_airport else dest_name
                msg = f"ℹ️ {missing} şehrinde havalimanı bulunmadığı için doğrudan uçak seferi yoktur."
                if transport_type == "flight":
                    notices.append(f"⚠️ {msg} Lütfen otobüs veya tren seçeneklerini deneyiniz.")
                elif transport_type == "all":
                    notices.append(msg)

        # 2. TREN SEÇENEKLERİ (TCDD YHT / Anahat Resmi Tarifeleri)
        if transport_type in ("all", "train"):
            if origin_has_train and dest_has_train:
                # Sabah YHT
                results.append({
                    "id": "tr-tcdd-1",
                    "transport_type": "train",
                    "carrier": "TCDD Taşımacılık (YHT)",
                    "carrier_logo": "🚆",
                    "flight_number": "YHT 91001",
                    "origin": origin.get("train_station", f"{origin_name} Gar"),
                    "destination": dest.get("train_station", f"{dest_name} Gar"),
                    "departure_time": "09:10",
                    "arrival_time": "13:45",
                    "departure_date_formatted": dep_date_formatted,
                    "arrival_date_formatted": dep_date_formatted,
                    "is_next_day": False,
                    "duration": "4 sa 35 dk",
                    "is_direct": True,
                    "is_night_trip": False,
                    "price": (430.00 * (1.9 if is_round else 1.0)) * passengers,
                    "regular_price": (580.00 * (1.9 if is_round else 1.0)) * passengers,
                    "currency": "₺",
                    "badge": "En Ekonomik & Konforlu",
                    "official_name": "TCDD Taşımacılık",
                    "official_link": links["train"]["tcdd"],
                    "agent_name": "TCDD E-Bilet",
                    "agent_link": links["train"]["tcdd"],
                    "direct_link": links["train"]["tcdd"],
                    "note": links["train"]["tcdd_search_hint"]
                })

                # Gece Yataklı / Bölgesel Tren
                results.append({
                    "id": "tr-tcdd-night",
                    "transport_type": "train",
                    "carrier": "TCDD Taşımacılık (Gece YHT)",
                    "carrier_logo": "🚆",
                    "flight_number": "YHT Ekspres",
                    "origin": origin.get("train_station", f"{origin_name} Gar"),
                    "destination": dest.get("train_station", f"{dest_name} Gar"),
                    "departure_time": "22:15",
                    "arrival_time": "02:40",
                    "departure_date_formatted": dep_date_formatted,
                    "arrival_date_formatted": next_day_formatted,
                    "is_next_day": True,
                    "duration": "4 sa 25 dk",
                    "is_direct": True,
                    "is_night_trip": True,
                    "price": (460.00 * (1.9 if is_round else 1.0)) * passengers,
                    "regular_price": (610.00 * (1.9 if is_round else 1.0)) * passengers,
                    "currency": "₺",
                    "badge": "🌙 Gece Seferi",
                    "official_name": "TCDD Taşımacılık",
                    "official_link": links["train"]["tcdd"],
                    "agent_name": "TCDD E-Bilet",
                    "agent_link": links["train"]["tcdd"],
                    "direct_link": links["train"]["tcdd"]
                })
            else:
                missing = origin_name if not origin_has_train else dest_name
                msg = f"ℹ️ {missing} bölgesinde TCDD tren istasyonu veya demiryolu hattı bulunmamaktadır."
                if transport_type == "train":
                    notices.append(f"⚠️ {msg} Tren seferleri yalnızca demiryolu ağı olan iller arasında düzenlenmektedir. Lütfen Otobüs alternatifini inceleyiniz.")
                elif transport_type == "all":
                    notices.append(msg)

        # 3. OTOBÜS SEÇENEKLERİ (Obilet, Kamil Koç, Pamukkale)
        if transport_type in ("all", "bus"):
            # Gündüz Otobüsü
            results.append({
                "id": "bus-kk-1",
                "transport_type": "bus",
                "carrier": "Kamil Koç",
                "carrier_logo": "🚌",
                "flight_number": "2+1 Rahat Hat",
                "origin": f"{origin_name} Otogarı",
                "destination": f"{dest_name} Otogarı",
                "departure_time": "11:30",
                "arrival_time": "18:00",
                "departure_date_formatted": dep_date_formatted,
                "arrival_date_formatted": dep_date_formatted,
                "is_next_day": False,
                "duration": "6 sa 30 dk",
                "is_direct": True,
                "is_night_trip": False,
                "price": (480.00 * (1.9 if is_round else 1.0)) * passengers,
                "regular_price": (620.00 * (1.9 if is_round else 1.0)) * passengers,
                "currency": "₺",
                "badge": "2+1 Konfor",
                "official_name": "Kamil Koç Resmi",
                "official_link": "https://www.kamilkoc.com.tr/",
                "agent_name": "Obilet",
                "agent_link": links["bus"]["obilet"],
                "direct_link": "https://www.kamilkoc.com.tr/"
            })

            # Gece Otobüsü (Gezgin Favorisi)
            results.append({
                "id": "bus-pamuk-night",
                "transport_type": "bus",
                "carrier": "Pamukkale Turizm",
                "carrier_logo": "🚌",
                "flight_number": "Jumbo 2+1 (Gece)",
                "origin": f"{origin_name} Otogarı",
                "destination": f"{dest_name} Otogarı",
                "departure_time": "23:45",
                "arrival_time": "06:15",
                "departure_date_formatted": dep_date_formatted,
                "arrival_date_formatted": next_day_formatted,
                "is_next_day": True,
                "duration": "6 sa 30 dk",
                "is_direct": True,
                "is_night_trip": True,
                "price": (510.00 * (1.9 if is_round else 1.0)) * passengers,
                "regular_price": (650.00 * (1.9 if is_round else 1.0)) * passengers,
                "currency": "₺",
                "badge": "🌙 Otel Tasarruflu Gece Seferi",
                "official_name": "Pamukkale Resmi",
                "official_link": "https://www.pamukkale.com.tr/",
                "agent_name": "Obilet",
                "agent_link": links["bus"]["obilet"],
                "direct_link": "https://www.pamukkale.com.tr/"
            })

        # Gece seferi filtresi
        if night_only:
            results = [r for r in results if r.get("is_night_trip")]

        # Fiyata göre sırala
        results.sort(key=lambda x: x["price"])

        # Model A: Ulaşım Türüne Göre Özet Metrikleri
        flight_tickets = [t for t in results if t["transport_type"] == "flight"]
        train_tickets = [t for t in results if t["transport_type"] == "train"]
        bus_tickets = [t for t in results if t["transport_type"] == "bus"]

        summary = {
            "flight": {
                "count": len(flight_tickets),
                "min_price": min([t["price"] for t in flight_tickets]) if flight_tickets else None,
                "min_duration": "1 sa 10 dk" if flight_tickets else None,
                "available": origin_has_airport and dest_has_airport,
                "reason": links["flight"]["reason"]
            },
            "train": {
                "count": len(train_tickets),
                "min_price": min([t["price"] for t in train_tickets]) if train_tickets else None,
                "min_duration": "4 sa 25 dk" if train_tickets else None,
                "available": origin_has_train and dest_has_train,
                "reason": links["train"]["reason"]
            },
            "bus": {
                "count": len(bus_tickets),
                "min_price": min([t["price"] for t in bus_tickets]) if bus_tickets else None,
                "min_duration": "6 sa 30 dk" if bus_tickets else None,
                "available": True,
                "reason": None
            }
        }

        # Esnek Tarih / Fiyat Takvimi (Tasarım A: Kategori Şampiyonları & Çoklu Gün)
        min_fl_p = summary["flight"]["min_price"] or (3500.0 if cabin_class == "business" else 1397.0)
        min_tr_p = summary["train"]["min_price"] or 430.0
        min_bu_p = summary["bus"]["min_price"] or 480.0

        price_calendar = cls.generate_price_calendar(
            origin_name=origin_name,
            dest_name=dest_name,
            base_date_str=departure_date,
            base_flight_price=min_fl_p,
            base_train_price=min_tr_p,
            base_bus_price=min_bu_p,
            has_flight=origin_has_airport and dest_has_airport,
            has_train=origin_has_train and dest_has_train,
            has_bus=True,
            days_count=calendar_range
        )

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
            "summary": summary,
            "price_calendar": price_calendar,
            "deep_links": links,
            "notices": notices,
            "results_count": len(results),
            "tickets": results
        }
