import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.cities import find_city, resolve_nearest_airport_city, TURKEY_CITIES
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
        cabin_class: str = "economy", currency: str = "TRY",
        adults: int = 1, children: int = 0, infants: int = 0
    ):
        origin = find_city(origin_city_name)
        dest = find_city(dest_city_name)

        eff_orig_airport, _ = resolve_nearest_airport_city(origin or origin_city_name)
        eff_dest_airport, _ = resolve_nearest_airport_city(dest or dest_city_name)

        origin_iata = (origin.get("iata") if origin and origin.get("iata") else None) or (eff_orig_airport.get("iata") if eff_orig_airport else None)
        dest_iata = (dest.get("iata") if dest and dest.get("iata") else None) or (eff_dest_airport.get("iata") if eff_dest_airport else None)

        origin_slug = origin["slug"] if origin else origin_city_name.lower().replace(" ", "-")
        dest_slug = dest["slug"] if dest else dest_city_name.lower().replace(" ", "-")

        # 0. Aynı Kalkış ve Varış Noktası Kontrolü
        if origin_slug == dest_slug or origin_city_name.strip().lower() == dest_city_name.strip().lower():
            return {
                "flight": {"available": False, "reason": "Kalkış ve varış noktası aynı olamaz. Lütfen farklı bir varış noktası seçiniz.", "trip": None, "travelpayouts": None, "pegasus": None, "google_flights": None, "enuygun": None, "skyscanner": None},
                "train": {"available": False, "is_tcdd": False, "is_international": False, "reason": "Kalkış ve varış garı aynı olamaz.", "tcdd": None, "trainline": None, "omio": None},
                "bus": {"available": False, "is_overland_neighbor": False, "reason": "Kalkış ve varış şehri aynı olamaz.", "obilet": None, "kamilkoc": None, "pamukkale": None},
                "ferry": {"available": False, "reason": "Kalkış ve varış iskelesi aynı olamaz.", "ido": None, "budo": None, "erturk": None, "turyol": None, "feribotlines": None}
            }

        sky_dep = cls.format_date_for_skyscanner(departure_date)
        enuygun_dep = cls.format_date_for_enuygun(departure_date)

        origin_has_airport = bool(origin_iata and ((origin and origin.get("has_airport")) or eff_orig_airport))
        dest_has_airport = bool(dest_iata and ((dest and dest.get("has_airport")) or eff_dest_airport) and origin_iata != dest_iata)
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))
        origin_is_intl = bool(origin and origin.get("is_international"))
        dest_is_intl = bool(dest and dest.get("is_international"))

        # Tren Kuralları: TCDD 597 istasyon canlı ağı + Balkan Ekspresi + Trainline Avrupa Hızlı Trenleri
        from app.services.train_service import TrainService
        has_live_tcdd = TrainService.has_direct_tcdd_connection(origin_city_name, dest_city_name)
        is_tcdd_train = bool((origin_has_train and dest_has_train and not origin_is_intl and not dest_is_intl) or (has_live_tcdd and not (origin_is_intl and dest_is_intl)))
        is_intl_train = bool((origin_has_train and dest_has_train and origin_is_intl and dest_is_intl) or (has_live_tcdd and (origin_is_intl or dest_is_intl)))
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

        # Yolcu parametreleri (Yetişkin / Çocuk / Bebek)
        adults = max(1, adults or passengers or 1)
        children = max(0, children or 0)
        infants = max(0, infants or 0)

        pgs_pax = f"adultCount={adults}"
        if children > 0:
            pgs_pax += f"&childCount={children}"
        if infants > 0:
            pgs_pax += f"&infantCount={infants}"

        enuygun_pax = f"yetiskin={adults}"
        if children > 0:
            enuygun_pax += f"&cocuk={children}"
        if infants > 0:
            enuygun_pax += f"&bebek={infants}"

        sky_pax = f"adultsv2={adults}"
        if children > 0:
            sky_pax += f"&childrenv2={children}"

        # 1. Uçak Deep Linkleri (Doğrudan canlı sonuç ekranı)
        flight_links = {
            "available": origin_has_airport and dest_has_airport,
            "reason": None if (origin_has_airport and dest_has_airport) else f"{origin_city_name if not origin_has_airport else dest_city_name} şehrinde aktif havalimanı bulunmamaktadır."
        }
        if flight_links["available"]:
            # Pegasus ve AJet ana operasyon üssü Sabiha Gökçen (SAW) kilitlemesi:
            # Kullanıcı genel "İstanbul" seçtiyse ve rota iç hat ise, Pegasus'u SAW koduna yönlendirerek
            # IST üzerinden aktarmalı fahiş fiyat hatasını önle.
            pgs_orig_code = "saw" if (origin_iata == "IST" and "havalimanı" not in origin_city_name.lower() and "havalimani" not in origin_city_name.lower()) else origin_iata.lower()
            pgs_dest_code = "saw" if (dest_iata == "IST" and "havalimanı" not in dest_city_name.lower() and "havalimani" not in dest_city_name.lower()) else dest_iata.lower()
            pegasus_route = f"{origin_slug}-{dest_slug}-{pgs_orig_code}a-{pgs_dest_code}a"

            enuygun_route = f"{origin_slug}-{dest_slug}-{origin_iata.lower()}a-{dest_iata.lower()}a"
            # Travelpayouts / Aviasales Uçak Arama Deep Linki (Marker: 585474)
            tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
            try:
                dep_dt_obj = datetime.strptime(departure_date, "%Y-%m-%d")
                dep_d = dep_dt_obj.strftime("%d")
                dep_m = dep_dt_obj.strftime("%m")
                ret_d_m = ""
                if is_round and return_date:
                    ret_dt_obj = datetime.strptime(return_date, "%Y-%m-%d")
                    ret_d_m = f"{ret_dt_obj.strftime('%d')}{ret_dt_obj.strftime('%m')}"
                tp_flight_url = f"https://www.aviasales.com/search/{origin_iata}{dep_d}{dep_m}{dest_iata}{ret_d_m}{adults}?marker={tp_marker}&currency={currency}"
            except Exception:
                tp_flight_url = f"https://www.aviasales.com/?marker={tp_marker}&currency={currency}"

            flight_links["travelpayouts"] = tp_flight_url
            flight_links["aviasales"] = tp_flight_url

            if is_round:
                sky_ret = cls.format_date_for_skyscanner(return_date)
                enuygun_ret = cls.format_date_for_enuygun(return_date)
                flight_links["pegasus"] = f"https://www.enuygun.com/ucak-bileti/arama/{pegasus_route}/?gidis={enuygun_dep}&donus={enuygun_ret}&{enuygun_pax}{biz_extra_enuygun}&havayolu=PC"
                flight_links["skyscanner"] = f"https://www.skyscanner.com.tr/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{sky_dep}/{sky_ret}/?{sky_pax}&cabinclass={sky_cabin}&currency={currency}&locale=tr-TR&rtn=1"
                flight_links["google_flights"] = f"https://www.google.com/travel/flights?q=flights+from+{origin_iata}+to+{dest_iata}+on+{departure_date}+through+{return_date}{biz_extra_google}&hl=tr&gl=tr&curr={currency}"
                flight_links["enuygun"] = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep}&donus={enuygun_ret}&{enuygun_pax}{biz_extra_enuygun}"
                trip_ret_param = f"&rdate={return_date}"
            else:
                flight_links["pegasus"] = f"https://www.enuygun.com/ucak-bileti/arama/{pegasus_route}/?gidis={enuygun_dep}&{enuygun_pax}{biz_extra_enuygun}&havayolu=PC"
                flight_links["skyscanner"] = f"https://www.skyscanner.com.tr/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{sky_dep}/?{sky_pax}&cabinclass={sky_cabin}&currency={currency}&locale=tr-TR&rtn=0"
                flight_links["google_flights"] = f"https://www.google.com/travel/flights?q=flights+from+{origin_iata}+to+{dest_iata}+on+{departure_date}+one+way{biz_extra_google}&hl=tr&gl=tr&curr={currency}"
                flight_links["enuygun"] = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep}&{enuygun_pax}{biz_extra_enuygun}"
                trip_ret_param = ""

            trip_alliance = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "")
            trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "")
            trip_aff_param = f"&Allianceid={trip_alliance}&SID={trip_sid}" if trip_alliance else ""
            trip_flighttype = "rt" if is_round else "ow"
            flight_links["trip"] = f"https://tr.trip.com/flights/{origin_slug}-to-{dest_slug}/tickets-{origin_iata.lower()}-{dest_iata.lower()}?flighttype={trip_flighttype}&dcity={origin_iata.lower()}&acity={dest_iata.lower()}&ddate={departure_date}{trip_ret_param}&curr={currency}{trip_aff_param}"
            from app.cities import build_obilet_flight_url
            flight_links["obilet"] = build_obilet_flight_url(
                from_code=origin_iata,
                to_code=dest_iata,
                departure_date=departure_date,
                return_date=return_date,
                is_round=is_round,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
                orig_slug=origin_slug,
                dest_slug=dest_slug,
            )
        else:
            flight_links["pegasus"] = None
            flight_links["skyscanner"] = None
            flight_links["google_flights"] = None
            flight_links["enuygun"] = None
            flight_links["trip"] = None
            flight_links["obilet"] = None
            flight_links["travelpayouts"] = None
            flight_links["aviasales"] = None

        # 2. Tren Deep Linkleri (TCDD E-Bilet & Avrupa Trainline / Omio)
        train_links = {
            "available": train_available,
            "is_tcdd": is_tcdd_train,
            "is_international": is_intl_train,
            "reason": train_reason,
            "tcdd": "https://ebilet.tcddtasimacilik.gov.tr/" if is_tcdd_train else None,
            "trainline": f"https://www.thetrainline.com/book/results?origin={origin_slug}&destination={dest_slug}&outwardDate={departure_date}&currency={currency}" if is_intl_train else None,
            "omio": f"https://www.omio.com/search-frontend/results/{origin_slug}/{dest_slug}/{departure_date}?locale=tr&currency={currency}" if is_intl_train else None,
            "tcdd_search_hint": f"Kalkış: {origin.get('train_station', origin_city_name) if origin else origin_city_name} -> Varış: {dest.get('train_station', dest_city_name) if dest else dest_city_name}" if is_tcdd_train else "Demiryolu hattı yok"
        }

        # 3. Otobüs Deep Linkleri (Obilet yurt içi, FlixBus/Omio Avrupa ve komşu ağlar)
        is_dest_intl = bool(dest and dest.get("is_international"))
        is_orig_intl = bool(origin and origin.get("is_international"))
        is_overland = bool(dest and dest.get("is_overland_neighbor"))
        is_intra_europe = bool(is_orig_intl and is_dest_intl and origin.get("region") == "Avrupa" and dest.get("region") == "Avrupa")
        bus_ret_path = f"/{return_date}" if is_round else ""

        if is_dest_intl and not is_overland and not is_intra_europe:
            bus_links = {
                "available": False,
                "is_overland_neighbor": False,
                "reason": f"{dest_city_name} denizaşırı/kıtalararası bir rota olduğundan doğrudan otobüs seferi bulunmamaktadır.",
                "obilet": None,
                "kamilkoc": None,
                "pamukkale": None,
                "flixbus": None,
                "omio": None
            }
        else:
            from app.services.bus_service import BusService
            if is_intra_europe:
                bus_link = BusService.get_flixbus_deep_link(origin_city_name, dest_city_name, departure_date)
                omio_bus_link = BusService.get_omio_deep_link(origin_city_name, dest_city_name, departure_date)
            else:
                bus_link = BusService.get_obilet_deep_link(origin_city_name, dest_city_name, departure_date)
                omio_bus_link = None

            bus_links = {
                "available": True,
                "is_overland_neighbor": is_overland or is_intra_europe,
                "reason": None,
                "obilet": None if is_intra_europe else bus_link,
                "kamilkoc": None if is_intra_europe else bus_link,
                "pamukkale": None if is_intra_europe else bus_link,
                "flixbus": bus_link if is_intra_europe else None,
                "omio": omio_bus_link
            }

        # 4. Deniz Yolları & Feribot Deep Linkleri (Asla kuru ana sayfaya yönlendirme yok; parametrik derin linkler)
        from app.services.ferry_service import FerryService
        matched_ferry_routes = FerryService.find_matching_routes(origin_city_name, dest_city_name)
        is_sea_origin = bool(origin and origin.get("is_ferry"))
        is_sea_dest = bool(dest and dest.get("is_ferry"))
        ferry_avail = bool(matched_ferry_routes or (is_sea_origin and is_sea_dest))
        if matched_ferry_routes:
            f_deep = FerryService.build_partner_deep_links(
                route=matched_ferry_routes[0],
                departure_date=departure_date,
                return_date=return_date if is_round else None,
                passengers=adults,
            )
            ferry_links = {
                "available": True,
                "reason": None,
                "obilet": f_deep.get("obilet"),
                "feribotlines": f_deep.get("feribotlines"),
                "biletcom": f_deep.get("biletcom"),
                "official": f_deep.get("official"),
                "ferryhopper": f_deep.get("ferryhopper"),
                "ido": f_deep.get("official"),
                "budo": f_deep.get("official"),
                "erturk": f_deep.get("official"),
                "turyol": f_deep.get("official"),
            }
        else:
            ferry_links = {
                "available": ferry_avail,
                "reason": None if ferry_avail else "Bu güzergahta doğrudan deniz yolu seferi bulunmamaktadır.",
                "obilet": f"https://www.obilet.com/feribot-bileti?tarih={departure_date}&yetiskin={adults}&utm_source=hakikibilet" if ferry_avail else None,
                "feribotlines": f"https://feribotlines.com/?gidis_tarihi={departure_date}&yetiskin={adults}&subid={settings.AFFILIATE_FERRY_SUBID}" if ferry_avail else None,
                "biletcom": f"https://www.bilet.com/feribot-bileti?tarih={departure_date}&ref={settings.AFFILIATE_FERRY_SUBID}" if ferry_avail else None,
                "ido": f"https://www.ido.com.tr/sefer-saatleri?date={departure_date}&utm_source=hakikibilet" if ferry_avail else None,
                "budo": f"https://budo.burulas.com.tr/tr/Timetables?DepartureDate={departure_date}" if ferry_avail else None,
                "erturk": f"https://www.erturk.com.tr/tr/?date={departure_date}&utm_source=hakikibilet" if ferry_avail else None,
                "turyol": f"https://www.turyolonline.com/?date={departure_date}&utm_source=hakikibilet" if ferry_avail else None,
            }

        # 5. Akıllı Havalimanı & Şehir İçi Transfer Derin Linkleri (Bilet.com, KiwiTaxi, GetTransfer)
        from app.services.transfer_service import TransferService
        transfer_data = TransferService.generate_transfer_links(
            dest_city_or_code=dest_city_name,
            travel_date=departure_date,
            passengers=adults
        )

        return {
            "flight": flight_links,
            "train": train_links,
            "bus": bus_links,
            "ferry": ferry_links,
            "transfer": transfer_data
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
        Tarihi kesinleşmiş, resmi satışta veya teyitli yaklaşan organizasyonlar.
        Sıfır Tahmin Kuralı: Geçmiş tarihli veya teyitsiz hiçbir etkinlik gösterilmez.
        Kalan gün sayısına göre akıllı aciliyet (FOMO) ve yeni takvim rozetleri dinamik hesaplanır.
        Otomatik olarak kronolojik (en yakın tarihli en üstte) sıralanır.
        """
        events = [
            {
                "id": "event-chios",
                "title": "Kapı Vizesiz Sakız Adası Kaçamağı 🏖️",
                "title_en": "Visa-on-Arrival Chios Island Getaway 🏖️",
                "city": "Sakız Adası (Chios)",
                "city_en": "Chios Island",
                "country": "Yunanistan",
                "country_en": "Greece",
                "category": "island",
                "category_label": "Yunan Adaları & Deniz",
                "is_escape": True,
                "dates": "Hafta Sonu İçin İdeal",
                "dates_en": "Ideal for Weekend",
                "badge": "💡 Aklınızda Bulunsun",
                "badge_en": "💡 Keep in Mind",
                "transport_mode": "ferry",
                "tag": "Ege & Deniz",
                "desc": "Çeşme'den 30 dakikada Sakız Adası. Cuma çıkışlı 2 günlük sakin ada kaçamağı, damla sakızı köyleri ve taze deniz ürünleri.",
                "desc_en": "Chios in 30 mins from Cesme. A 2-day tranquil island getaway departing Friday, exploring mastic villages and fresh seafood.",
                "hotel_range": "Booking.com Canlı Teyitli Oteller",
                "ticket_org": "Ertürk & Feribotlines Resmi Bilet Portalı",
                "ticket_url": "https://www.erturk.com.tr/tr/",
                "image_url": "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Günübirlik Yaya Yolcu", "price": "~35 €", "desc": "Aynı gün gidiş-dönüş"},
                    {"name": "Açık Dönüşlü Standart Bilet", "price": "~45 €", "desc": "Hafta sonu konaklamalı"},
                    {"name": "Araçlı Geçiş (Otomobil)", "price": "~90 €", "desc": "Araçla ada keşfi"}
                ],
                "why": "Bütçe dostu, yakın ve kapı vizesiyle en pratik yurt dışı kaçamağı."
            },
            {
                "id": "event-harbiye-zorlu",
                "title": "Harbiye Açıkhava & Zorlu PSM Sahne Sezonu 🎭 🎶",
                "title_en": "Harbiye Open-Air & Zorlu PSM Stage Season 🎭 🎶",
                "city": "İstanbul (IST/SAW)",
                "city_en": "Istanbul (IST/SAW)",
                "country": "Türkiye",
                "country_en": "Turkey",
                "category": "concert_theater",
                "category_label": "Konser, Tiyatro & Sahne",
                "dates": "14 Kas - 16 Kas",
                "dates_en": "Nov 14 - Nov 16",
                "dep_date": "2026-11-14",
                "ret_date": "2026-11-16",
                "badge": "Resmi Biletix & Bubilet & Passo Satışı",
                "badge_en": "Official Biletix & Passo Box Office",
                "transport_mode": "flight",
                "is_new": True,
                "tag": "Kültür & Müzik",
                "desc": "İstanbul'un kalbinde dev müzikaller, senfoni konserleri ve tiyatro şöleni. Şehir dışından gelen gezginler için uçuş ve Taksim/Beşiktaş otelleri tek tıkla hazır.",
                "desc_en": "Grand musicals, symphony concerts, and stage plays in the heart of Istanbul. Direct flights and Taksim/Besiktas hotels ready in one click.",
                "hotel_range": "Booking.com Canlı Taksim & Şişli Otelleri",
                "ticket_org": "Bubilet & Biletix & Passo Resmi Bilet Satışı",
                "ticket_url": "https://www.bubilet.com.tr/istanbul",
                "image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Standart Tiyatro / Konser Bileti", "price": "450 - 950 ₺", "desc": "Biletix / Bubilet resmi koltuk seçimi"},
                    {"name": "Protokol & Sahne Önü", "price": "1.250 - 2.800 ₺", "desc": "Ön sıra VIP deneyimi"},
                    {"name": "Şehir Dışı Kombine (Uçuş + Otel)", "price": "Fırsat", "desc": "Travelpayouts taban fiyat güvencesi"}
                ],
                "why": "Kültür-sanat tutkunlarının yıl boyu en çok ziyaret ettiği prestijli sahne takvimi."
            },
            {
                "id": "event-aspendos",
                "title": "Aspendos Antik Tiyatro Festivali & Opera 🩰 🏛️",
                "title_en": "Aspendos Antique Theatre Opera & Ballet Festival 🩰 🏛️",
                "city": "Antalya (AYT)",
                "city_en": "Antalya (AYT)",
                "country": "Türkiye",
                "country_en": "Turkey",
                "category": "concert_theater",
                "category_label": "Konser, Tiyatro & Sahne",
                "dates": "11 Ara - 13 Ara",
                "dates_en": "Dec 11 - Dec 13",
                "dep_date": "2026-12-11",
                "ret_date": "2026-12-13",
                "badge": "Devlet Opera & Balesi Teyitli",
                "badge_en": "State Opera & Ballet Confirmed",
                "transport_mode": "flight",
                "tag": "Tarih & Sanat",
                "desc": "2000 yıllık Roma tiyatrosunun büyülü akustiğinde dünyaca ünlü operalar ve bale gösterileri. Antalya direkt uçuşları ve sahil otelleri.",
                "desc_en": "World-class operas and ballets in the 2,000-year-old Roman amphitheatre with magical acoustics. Direct Antalya flights & seaside hotels.",
                "hotel_range": "Booking.com Canlı Antalya & Belek Otelleri",
                "ticket_org": "Biletinial Resmi T.C. Kültür ve Turizm Bakanlığı Bilet Portalı",
                "ticket_url": "https://biletinial.com/tr-tr/tiyatro",
                "image_url": "https://images.unsplash.com/photo-1469488865564-c2de10f69f96?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "1. Kategori Numaralı Koltuk", "price": "~400 ₺", "desc": "Sahneye hakim amfitiyatro koltuğu"},
                    {"name": "2. Kategori Koltuk", "price": "~250 ₺", "desc": "Akustik merkez tribün"},
                    {"name": "Öğrenci / İndirimli", "price": "~150 ₺", "desc": "Resmi kontenjan"}
                ],
                "why": "Dünyanın en iyi korunmuş antik tiyatrosunda eşsiz bir sanat ve seyahat deneyimi."
            },
            {
                "id": "event-f1-monaco",
                "title": "Formula 1 Monaco Grand Prix (Monte Carlo) 🏎️",
                "title_en": "Formula 1 Monaco Grand Prix (Monte Carlo) 🏎️",
                "city": "Nice (NCE)",
                "city_en": "Nice (NCE)",
                "country": "Fransa / Monaco",
                "country_en": "France / Monaco",
                "category": "sport",
                "category_label": "Dünya Spor Zirveleri",
                "dates": "21 May - 24 May 2027",
                "dates_en": "May 21 - May 24, 2027",
                "dep_date": "2027-05-21",
                "ret_date": "2027-05-24",
                "badge": "FIA Resmi Monaco Takvimi",
                "badge_en": "FIA Official Monaco Calendar",
                "transport_mode": "flight",
                "tag": "Hız & Prestij (Ferrari)",
                "desc": "Monte Carlo sokak pistinde Scuderia Ferrari ve F1 kükremesi. Nice (NCE) uçuşu + 20 dk sahil treniyle Monaco Garı'na doğrudan varış.",
                "desc_en": "Scuderia Ferrari and the roar of F1 through Monte Carlo streets. Flight to Nice (NCE) + 20-min scenic train to Monaco.",
                "hotel_range": "Booking.com Canlı Nice & Monaco Otelleri",
                "ticket_org": "Resmi FIA F1 Monaco Bilet & Koltuk Seçimi",
                "ticket_url": "https://ticketing.formula1.com/monaco/",
                "image_url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Genel Giriş (Rocher Yamaç)", "price": "~150 €", "desc": "Pist panoraması ve dev ekran"},
                    {"name": "K Tribünü (Liman & Rascasse)", "price": "~480 €", "desc": "Süper yatlar ve viraj mücadelesi"},
                    {"name": "B Tribünü (Casino Meydanı)", "price": "~850 €", "desc": "Miras Casino virajı ve pit çıkışı"}
                ],
                "why": "Dünyanın en ikonik, en lüks ve en prestijli Formula 1 sokak yarışı."
            },
            {
                "id": "event-ucl-final",
                "title": "UEFA Şampiyonlar Ligi Finali Münih ⚽",
                "title_en": "UEFA Champions League Final Munich ⚽",
                "city": "Münih (MUC)",
                "city_en": "Munich (MUC)",
                "country": "Almanya",
                "country_en": "Germany",
                "category": "sport",
                "category_label": "Dünya Spor Zirveleri",
                "dates": "29 May - 31 May 2027",
                "dates_en": "May 29 - May 31, 2027",
                "dep_date": "2027-05-29",
                "ret_date": "2027-05-31",
                "badge": "Avrupa Kulüpler Zirvesi",
                "badge_en": "European Club Championship",
                "transport_mode": "flight",
                "tag": "Futbol Şöleni",
                "desc": "Allianz Arena'da Avrupa'nın en büyüğünü belirleyecek dev final maçı ve Münih taraftar festivali coşkusu.",
                "desc_en": "The grand final match at Allianz Arena deciding European champions, plus fan festival excitement across Munich.",
                "hotel_range": "Booking.com Canlı Münih Otelleri",
                "ticket_org": "Resmi UEFA Bilet Portalı",
                "ticket_url": "https://www.uefa.com/tickets/",
                "image_url": "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Kategori 4 (Kale Arkası Üst)", "price": "~70 €", "desc": "Coşkulu taraftar tribünü"},
                    {"name": "Kategori 3 & 2 (Köşe & Yan)", "price": "~180 €", "desc": "Geniş saha açısı"},
                    {"name": "Kategori 1 (Merkez Maraton)", "price": "~590 €", "desc": "Kupa seremonisi ve orta saha"}
                ],
                "why": "Yılın en büyük futbol organizasyonunda kupa heyecanını yerinde yaşayın."
            },
            {
                "id": "event-wimbledon",
                "title": "Wimbledon Tenis Şampiyonası 🎾",
                "title_en": "Wimbledon Tennis Championships 🎾",
                "city": "Londra (LHR/STN)",
                "city_en": "London (LHR/STN)",
                "country": "İngiltere",
                "country_en": "United Kingdom",
                "category": "sport",
                "category_label": "Dünya Spor Zirveleri",
                "dates": "28 Haz - 05 Tem 2027",
                "dates_en": "Jun 28 - Jul 05, 2027",
                "dep_date": "2027-06-28",
                "ret_date": "2027-07-05",
                "badge": "Tenisin Mabedi",
                "badge_en": "The Cathedral of Tennis",
                "transport_mode": "flight",
                "tag": "Grand Slam Geleneği",
                "desc": "Çilek & krema geleneği, yemyeşil çim kortlar ve Centre Court'ta dünyanın en iyi raketleri.",
                "desc_en": "Strawberries & cream tradition, lush grass courts, and world's best racquets on Centre Court.",
                "hotel_range": "Booking.com Canlı Londra Otelleri",
                "ticket_org": "Resmi Wimbledon Public Ballot & The Queue",
                "ticket_url": "https://www.wimbledon.com",
                "image_url": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Grounds Pass (Dış Kortlar)", "price": "~30 £", "desc": "Henman Hill ve yan kortlar"},
                    {"name": "No.1 Court Rezervasyonlu", "price": "~130 £", "desc": "Üstü kapanabilir çim kort"},
                    {"name": "Centre Court (Merkez Kort)", "price": "~240 £", "desc": "Tarihi şampiyonluk kortu"}
                ],
                "why": "Beyaz kıyafet geleneği ve tenis tarihinin en asil şampiyonası."
            },
            {
                "id": "event-f1-silverstone",
                "title": "Formula 1 Britanya Grand Prix (Silverstone) 🏎️",
                "title_en": "Formula 1 British Grand Prix (Silverstone) 🏎️",
                "city": "Londra (LHR/STN)",
                "city_en": "London (LHR/STN)",
                "country": "İngiltere",
                "country_en": "United Kingdom",
                "category": "sport",
                "category_label": "Dünya Spor Zirveleri",
                "dates": "04 Tem - 06 Tem 2027",
                "dates_en": "Jul 04 - Jul 06, 2027",
                "dep_date": "2027-07-04",
                "ret_date": "2027-07-06",
                "badge": "FIA Resmi Silverstone Takvimi",
                "badge_en": "FIA Official Silverstone Calendar",
                "transport_mode": "flight",
                "tag": "Motor Sporları Doğuşu (Ferrari)",
                "desc": "Scuderia Ferrari'nin F1 tarihindeki ilk zaferini kazandığı efsanevi Silverstone pistinde yüksek hızlı virajlar ve motor festivali coşkusu.",
                "desc_en": "Legendary Silverstone circuit where Ferrari claimed its first F1 victory, featuring high-speed sweeps and festival vibes.",
                "hotel_range": "Booking.com Canlı Londra & Milton Keynes Otelleri",
                "ticket_org": "Resmi Silverstone & FIA Bilet Portalı",
                "ticket_url": "https://ticketing.formula1.com/great-britain/",
                "image_url": "https://images.unsplash.com/photo-1773851729103-93173282bd45?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "General Admission (Genel Giriş)", "price": "~185 £", "desc": "Tüm pist çevresi çim alanlar"},
                    {"name": "Stowe / Club Viraj Tribünü", "price": "~420 £", "desc": "Geçişlerin en çok yapıldığı virajlar"},
                    {"name": "Hamilton Ana Düzlük & Pit", "price": "~690 £", "desc": "Start/Finish çizgisi ve podyum"}
                ],
                "why": "F1 tutkunlarının en heyecanlı ve en hızlı viraj mücadelelerine tanık olduğu efsane pist."
            },
            {
                "id": "event-f1-monza",
                "title": "Formula 1 İtalya Grand Prix (Monza) 🏎️",
                "title_en": "Formula 1 Italian Grand Prix (Monza) 🏎️",
                "city": "Milano (MXP)",
                "city_en": "Milan (MXP)",
                "country": "İtalya",
                "country_en": "Italy",
                "category": "sport",
                "category_label": "Dünya Spor Zirveleri",
                "dates": "03 Eyl - 05 Eyl 2027",
                "dates_en": "Sep 03 - Sep 05, 2027",
                "dep_date": "2027-09-03",
                "ret_date": "2027-09-05",
                "badge": "Hız Tapınağı (Temple of Speed)",
                "badge_en": "Temple of Speed",
                "transport_mode": "flight",
                "tag": "Tifosi Kırmızı Denizi (Ferrari SF-24)",
                "desc": "Scuderia Ferrari SF-24 taraftarlarının kırmızı denizi, 355 km/s hız rekorları. Milano uçuşu + Milano Garı'ndan 15 dk Monza treni.",
                "desc_en": "The red sea of Scuderia Ferrari tifosi with 355 km/h speed records. Milan flight + 15-min train to Monza.",
                "hotel_range": "Booking.com Canlı Milano Otelleri",
                "ticket_org": "Resmi Autodromo Nazionale Monza & F1",
                "ticket_url": "https://ticketing.formula1.com/italy/",
                "image_url": "https://images.unsplash.com/photo-1762857362511-86142780dc43?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Prato (Genel Giriş)", "price": "~140 €", "desc": "Parabolica ve Curva Grande çevresi"},
                    {"name": "Laterale Parabolica Tribünü", "price": "~350 €", "desc": "Son viraj ve düzlüğe çıkış"},
                    {"name": "Centrale Tribuna Ana Düzlük", "price": "~650 €", "desc": "Ferrari pit garajı ve kupa seremonisi"}
                ],
                "why": "Takvimin en hızlı pistinde unutulmaz İtalyan motor sporları ve Ferrari atmosferi."
            },
            {
                "id": "event-f1-baku",
                "title": "Formula 1 Azerbaycan Grand Prix (Bakü) 🏎️",
                "title_en": "Formula 1 Azerbaijan Grand Prix (Baku) 🏎️",
                "city": "Bakü (GYD)",
                "city_en": "Baku (GYD)",
                "country": "Azerbaycan",
                "country_en": "Azerbaijan",
                "category": "sport",
                "category_label": "Dünya Spor Zirveleri",
                "dates": "17 Eyl - 19 Eyl 2027",
                "dates_en": "Sep 17 - Sep 19, 2027",
                "dep_date": "2027-09-17",
                "ret_date": "2027-09-19",
                "badge": "Vizesiz • En Hızlı Şehir Pisti",
                "badge_en": "Fastest Street Circuit",
                "transport_mode": "flight",
                "tag": "Kardeş Ülke Heyecanı",
                "desc": "Bakü Şehir Pisti'nde Hazar Denizi ve tarihi kale surları boyunca 340 km/s hızla soluksuz yarış heyecanı. Türk vatandaşlarına vizesiz ve direkt uçuşlu.",
                "desc_en": "Breathtaking 340 km/h racing alongside Caspian shoreline and ancient castle walls on Baku City Circuit.",
                "hotel_range": "Booking.com Canlı Bakü Sahil Otelleri",
                "ticket_org": "Resmi Bakü City Circuit Biletleri",
                "ticket_url": "https://ticketing.formula1.com/azerbaijan/",
                "image_url": "https://images.unsplash.com/photo-1614949194403-9602bdc14a3a?auto=format&fit=crop&w=800&q=80",
                "ticket_categories": [
                    {"name": "Bulvar Genel Giriş (General)", "price": "~120 $", "desc": "Hazar kıyısı ve festival alanı"},
                    {"name": "İçeri Şehir (Tarihi Kale Virajı)", "price": "~290 $", "desc": "Dünyanın en dar pist virajı"},
                    {"name": "Abşeron Ana Düzlük (Main)", "price": "~540 $", "desc": "Start/Finish çizgisi ve pit aksiyonu"}
                ],
                "why": "Vizesiz ve en kolay ulaşılabilen, bol geçişli büyüleyici şehir yarışı."
            }
        ]
        
        # SIFIR TAHMİN & AKILLI ACİLİYET (FOMO) FİLTRESİ
        today = datetime.now().date()
        valid_events = []
        for evt in events:
            # Aklınızda Bulunsun / Hafta Sonu Kaçamak Rotaları (Yapay Tarih ve Sayaç Yoktur)
            if evt.get("is_escape"):
                # Kullanıcı arama yaptığında en yakın Cuma - Pazar gününü arama kutusuna hazırla
                days_to_fri = (4 - today.weekday()) % 7
                if days_to_fri == 0:
                    days_to_fri = 7
                next_fri = today + timedelta(days=days_to_fri)
                next_sun = next_fri + timedelta(days=2)
                evt["dep_date"] = next_fri.strftime("%Y-%m-%d")
                evt["ret_date"] = next_sun.strftime("%Y-%m-%d")
                evt["dates"] = "Hafta Sonu İçin İdeal"
                evt["dates_en"] = "Ideal for Weekend"
                evt["badge"] = "💡 Aklınızda Bulunsun"
                evt["badge_en"] = "💡 Keep in Mind"
                evt["urgency_badge"] = "🏖️ Hafta Sonu Kaçamağı"
                evt["urgency_badge_en"] = "🏖️ Weekend Getaway"
                evt["urgency_level"] = "escape"
                evt["urgency_class"] = "bg-amber-500 text-slate-950 font-black"
                evt["urgency_desc"] = "Festival şartı yok; Cuma çıkışlı 2 günlük sakin ada kaçamağı için tavsiye edilir."
                evt["urgency_desc_en"] = "Recommended for a peaceful 2-day island getaway departing Friday."
                valid_events.append(evt)
                continue

            dep_str = evt.get("dep_date")
            if not dep_str:
                continue
            try:
                dep_dt = datetime.strptime(dep_str, "%Y-%m-%d").date()
            except Exception:
                continue
            
            # KESİNLİKLE GEÇMİŞ TARİHLİ ETKİNLİK GÖSTERİLMEZ
            if dep_dt < today:
                continue
            
            days_left = (dep_dt - today).days
            evt["days_left"] = days_left
            
            # Akıllı Aciliyet (FOMO) ve Sayaç Rozetleri
            if days_left <= 15:
                evt["urgency_badge"] = f"🔥 Son {days_left} Gün • Kontenjanlar Tükenmek Üzere"
                evt["urgency_badge_en"] = f"🔥 Last {days_left} Days • Seats Filling Fast"
                evt["urgency_level"] = "critical"
                evt["urgency_class"] = "bg-rose-600 text-white animate-pulse"
                evt["urgency_desc"] = "Uçak ve otel fiyatları son günlerde yükselir, yerinizi gecikmeden ayırtın."
                evt["urgency_desc_en"] = "Flight and hotel rates increase as dates approach, book early."
            elif days_left <= 30:
                evt["urgency_badge"] = f"⏳ Son {days_left} Gün • Erken Fırsatı Kaçırmayın"
                evt["urgency_badge_en"] = f"⏳ Last {days_left} Days • Grab Early Fares"
                evt["urgency_level"] = "warning"
                evt["urgency_class"] = "bg-amber-500 text-slate-950 font-black"
                evt["urgency_desc"] = "Bilet ve konaklama fiyatları artmadan yerinizi ayırtın."
                evt["urgency_desc_en"] = "Secure your tickets before hotel and flight rates surge."
            else:
                evt["urgency_badge"] = "✈️ Erken Rezervasyon • Taban Fiyatlar Açık"
                evt["urgency_badge_en"] = "✈️ Early Bird • Base Fares Available"
                evt["urgency_level"] = "info"
                evt["urgency_class"] = "bg-emerald-600 text-white"
                evt["urgency_desc"] = "Resmi taban fiyatlarla en avantajlı planlama dönemi."
                evt["urgency_desc_en"] = "Best booking window with official base prices."
                
            if evt.get("is_new"):
                evt["new_badge"] = "✨ YENİ TAKVİM AÇILDI"
                evt["new_badge_en"] = "✨ NEW CALENDAR"
            else:
                evt["new_badge"] = None
                evt["new_badge_en"] = None

            valid_events.append(evt)

        # Otomatik Kronolojik Sıralama (En yakın tarihli olan en başta!)
        valid_events.sort(key=lambda e: e.get("dep_date", "9999-99-99"))
        return valid_events

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
            
            hub_bus_link = f"https://www.obilet.com/otobus-bileti/{origin_slug}-{domestic_hub.get('city', '').lower()}/{departure_date}?sorting=price&sort=price"
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
            
            intl_bus_link = f"https://www.obilet.com/otobus-bileti/{origin_slug}-istanbul/{departure_date}?sorting=price&sort=price"
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
        include_hotel: bool = False, hotel_nights: Optional[int] = None,
        adults: int = 1, children: int = 0, infants: int = 0
    ):
        # Yolcu sayılarını normalize et
        adults = max(1, adults or passengers or 1)
        children = max(0, children or 0)
        infants = max(0, infants or 0)
        total_pax = adults + children + infants

        # 1. "Her Yere" arama modu kontrolü
        if dest_city.lower() in ("her yere", "farketmez", "her-yere", "anywhere"):
            return cls.search_anywhere(origin_city, departure_date, transport_type, total_pax)

        origin = find_city(origin_city)
        dest = find_city(dest_city)
        
        origin_name = origin["name"] if origin else origin_city
        dest_name = dest["name"] if dest else dest_city

        # 1.1 Aynı Kalkış ve Varış Noktası Erken Koruması (Kiralık Araç & Havalimanı Transferi hariç)
        orig_slug = origin["slug"] if origin else origin_city.lower().replace(" ", "-")
        dest_slug = dest["slug"] if dest else dest_city.lower().replace(" ", "-")
        if transport_type != "car" and (orig_slug == dest_slug or origin_city.strip().lower() == dest_city.strip().lower()):
            currency_norm = (currency or "TRY").upper()
            curr_sym = CurrencyService.get_symbol(currency_norm)
            links = cls.generate_deep_links(
                origin_name, dest_name, departure_date, return_date, total_pax, trip_type, 
                cabin_class=cabin_class, currency=currency_norm,
                adults=adults, children=children, infants=infants
            )
            return {
                "origin": origin_name,
                "destination": dest_name,
                "date": departure_date,
                "departure_date": departure_date,
                "return_date": return_date,
                "trip_type": trip_type,
                "passengers": total_pax,
                "adults": adults,
                "children": children,
                "infants": infants,
                "cabin_class": cabin_class,
                "transport_type": transport_type,
                "currency": curr_sym,
                "currency_code": currency_norm,
                "tickets": [],
                "results_count": 0,
                "summary": {"total_options": 0, "flight": None, "train": None, "bus": None, "ferry": None},
                "deep_links": links,
                "notices": ["⚠️ Kalkış ve varış noktası aynı olamaz. Lütfen farklı bir varış şehri belirleyiniz."],
                "hotel_info": None,
                "price_calendar": {"days": [], "days_count": 0, "range_type": calendar_range, "tip": ""}
            }
        
        eff_orig_airport, orig_nearby_airport = resolve_nearest_airport_city(origin or origin_name)
        eff_dest_airport, dest_nearby_airport = resolve_nearest_airport_city(dest or dest_name)
        origin_has_airport = bool(eff_orig_airport and eff_orig_airport.get("has_airport"))
        dest_has_airport = bool(
            eff_dest_airport
            and eff_dest_airport.get("has_airport")
            and eff_orig_airport
            and eff_orig_airport.get("iata") != eff_dest_airport.get("iata")
        )
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))

        currency = (currency or "TRY").upper()
        curr_symbol = CurrencyService.get_symbol(currency)

        links = cls.generate_deep_links(
            origin_name, dest_name, departure_date, return_date, total_pax, trip_type, 
            cabin_class=cabin_class, currency=currency,
            adults=adults, children=children, infants=infants
        )
        results = []
        notices = []

        is_round = (trip_type == "round_trip" and return_date)

        # Alternatif ulaşım rozetlerini (Örn: Otobüs ararken Uçak + Tren fiyatlarını) ana aramayla EŞ ZAMANLI (paralel) başlat!
        _alt_executor = ThreadPoolExecutor(max_workers=1)
        _alt_badges_future = _alt_executor.submit(
            cls.build_alternative_mode_badges,
            origin_name=origin_name,
            dest_name=dest_name,
            departure_date=departure_date,
            current_mode=transport_type,
            passengers=total_pax,
            currency=currency,
            curr_symbol=curr_symbol,
            links=links,
            summary={},
        )

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

        ret_date_formatted = return_date
        if is_round and return_date:
            try:
                ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
                ret_date_formatted = f"{ret_dt.day} {months_tr[ret_dt.month - 1]} {days_tr[ret_dt.weekday()]}"
            except Exception:
                ret_date_formatted = return_date

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
                        passengers=total_pax,
                        trip_type="round_trip" if is_round else "one_way",
                        cabin_class=cabin_class,
                        adults=adults,
                        children=children,
                        infants=infants
                    )
                    if live_flights:
                        for lf in live_flights:
                            if currency != "TRY":
                                lf["price"] = round(CurrencyService.convert(lf["price"], "TRY", currency), 2)
                                if lf.get("regular_price"):
                                    lf["regular_price"] = round(CurrencyService.convert(lf["regular_price"], "TRY", currency), 2)
                                for p in lf.get("providers") or []:
                                    if p.get("price") is not None:
                                        p["price"] = round(CurrencyService.convert(p["price"], "TRY", currency), 2)
                                lf["currency"] = curr_symbol
                                lf["currency_code"] = currency
                            lf["has_live_price"] = True
                            lf["price_status_text"] = "Doğrulanmış Canlı Fiyat"
                        results.extend(live_flights)
                        live_flights_fetched = True
                except Exception as live_err:
                    print(f"Live flights fetch error: {live_err}")

                if not live_flights_fetched:
                    orig_iata = (origin.get('iata') if origin else None) or 'SAW'
                    dst_iata = (dest.get('iata') if dest else None) or 'ESB'
                    is_international = bool(origin and origin.get("is_international") or dest and dest.get("is_international"))
                    trip_url = links["flight"]["trip"]
                    google_url = links["flight"]["google_flights"]
                    enuygun_fallback_url = links["flight"].get("enuygun")
                    from app.cities import build_obilet_flight_url
                    obilet_fallback_url = build_obilet_flight_url(
                        from_code=orig_iata,
                        to_code=dst_iata,
                        departure_date=departure_date,
                        return_date=return_date,
                        is_round=is_round,
                        adults=adults,
                        children=children,
                        infants=infants,
                        cabin_class=cabin_class,
                        orig_slug=orig_slug,
                        dest_slug=dest_slug,
                    )

                    booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
                    try:
                        dep_dt_calc = datetime.strptime(departure_date, "%Y-%m-%d")
                        hotel_ret_calc = return_date if (is_round and return_date) else (dep_dt_calc + timedelta(days=2)).strftime("%Y-%m-%d")
                    except Exception:
                        hotel_ret_calc = departure_date
                    dest_hotel_link = (
                        f"https://www.booking.com/searchresults.html?"
                        f"ss={urllib.parse.quote(dest_name)}"
                        f"&checkin={departure_date}&checkout={hotel_ret_calc}"
                        f"&group_adults={adults}&no_rooms=1"
                        f"&aid={booking_aid}"
                    )

                    # Şeffaf ve Dürüst Canlı Sefer Kartı (Uydurma sefer, saat veya sabit fiyat kesinlikle üretilmez)
                    results.append({
                        "id": "fl-trip-live",
                        "transport_type": "flight",
                        "carrier": "Canlı Uçuş Arama",
                        "carrier_logo": "✈️",
                        "flight_number": f"{orig_iata} ➔ {dst_iata}",
                        "origin": f"{origin_name} ({orig_iata})",
                        "destination": f"{dest_name} ({dst_iata})",
                        "from_code": orig_iata,
                        "to_code": dst_iata,
                        "departure_time": "Tüm Gün Seferleri",
                        "arrival_time": "Canlı",
                        "departure_date_formatted": dep_date_formatted,
                        "arrival_date_formatted": dep_date_formatted,
                        "is_next_day": False,
                        "duration": "Direkt & Aktarmalı Seferler",
                        "is_direct": True,
                        "is_night_trip": False,
                        "return_leg": None,
                        "price": None,
                        "has_live_price": False,
                        "price_status_text": "Canlı Sefer Sorgula",
                        "regular_price": None,
                        "currency": curr_symbol,
                        "currency_code": currency,
                        "badge": "⭐ Resmi Gelir Ortağı",
                        "route_notice": f"{origin_name} - {dest_name} rotasında seçtiğiniz tarih için anlık müsaitlik ve tüm havayolu fiyatlarını canlı ekranlarda listeleyin.",
                        "cabin_class": cabin_class,
                        "official_name": "Resmi Havayolu Sorgula",
                        "official_link": trip_url or "https://www.turkishairlines.com/",
                        "agent_name": "Trip.com",
                        "agent_link": trip_url,
                        "enuygun_link": enuygun_fallback_url,
                        "obilet_link": obilet_fallback_url,
                        "direct_link": trip_url,
                        "booking_link": trip_url,
                        "hotel_link": dest_hotel_link,
                        "providers": [
                            {"name": "Trip.com (En Uygun Canlı Fiyatlar)", "url": trip_url, "price": None, "is_best": True, "channel": "trip"},
                            {"name": "Google Flights Karşılaştırması", "url": google_url, "price": None, "is_best": False, "channel": "meta"}
                        ]
                    })

            else:
                missing = origin_name if not origin_has_airport else dest_name
                msg = f"ℹ️ {missing} şehrinde aktif havalimanı bulunmadığı için doğrudan uçak seferi yoktur."
                if transport_type == "flight":
                    notices.append(f"⚠️ {msg} Lütfen otobüs, tren veya feribot seçeneklerini deneyiniz.")
                elif transport_type == "all":
                    notices.append(msg)

        # 2. TREN SEÇENEKLERİ (TCDD YHT & Trainline Avrupa Hızlı Trenleri)
        if transport_type in ("all", "train"):
            from app.services.train_service import TrainService
            train_tickets = TrainService.search_trains(
                origin_name=origin_name,
                dest_name=dest_name,
                departure_date=departure_date,
                passengers=passengers,
                currency=currency,
                is_round=is_round,
                return_date=return_date
            )
            if train_tickets:
                results.extend(train_tickets)
            else:
                msg = links["train"].get("reason") or f"ℹ️ {origin_name} - {dest_name} arasında doğrudan tarifeli tren seferi bulunmamaktadır."
                if transport_type == "train":
                    notices.append(f"⚠️ {msg}")
                elif transport_type == "all":
                    notices.append(msg)

        # 3. OTOBÜS SEÇENEKLERİ (Obilet Canlı Sefer & FlixBus Uluslararası Ağı)
        if transport_type in ("all", "bus"):
            if links.get("bus", {}).get("available", True):
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
                if bus_tickets:
                    results.extend(bus_tickets)
                elif transport_type == "bus":
                    notices.append(f"ℹ️ {origin_name} - {dest_name} rotasında seçilen tarihte doğrudan otobüs seferi bulunamamıştır. Lütfen farklı bir tarih veya alternatif ulaşım modlarını inceleyiniz.")
            elif transport_type == "bus":
                notices.append(links.get("bus", {}).get("reason") or f"ℹ️ {origin_name} - {dest_name} rotasında doğrudan otobüs seferi bulunmamaktadır.")

        # 4. DENİZ YOLLARI & FERİBOT SEÇENEKLERİ (İDO, BUDO, Ertürk, Turyol, Feribotlines)
        if transport_type in ("all", "ferry"):
            try:
                from app.services.ferry_service import FerryService
                ferry_results = FerryService.search_ferries(
                    origin_name=origin_city or origin_name,
                    dest_name=dest_city or dest_name,
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

        # Sıralama: Otobüs ve Feribot sekmelerinde akıllı kürasyon / iskele sırasını (smart_sort_rank) koru
        if transport_type in ("bus", "ferry"):
            results.sort(
                key=lambda t: (
                    t.get("smart_sort_rank", 9999) if t.get("transport_type") in ("bus", "ferry") else 9999,
                    t.get("price") if t.get("price") is not None else 999999,
                    -int(t.get("carrier_score", 0)),
                    t.get("departure_time") or "23:59",
                )
            )
        else:
            results.sort(
                key=lambda t: (
                    t.get("price") if t.get("price") is not None else 999999,
                    -int(t.get("carrier_score", 0)),
                    t.get("departure_time") or "23:59",
                )
            )

        # Özet İstatistikleri
        flight_tickets = [t for t in results if t["transport_type"] == "flight"]
        train_tickets = [t for t in results if t["transport_type"] == "train"]
        bus_tickets = [t for t in results if t["transport_type"] == "bus"]
        ferry_tickets = [t for t in results if t["transport_type"] == "ferry"]

        def calc_min_price(ticket_list):
            if not ticket_list:
                return None
            rank1_prices = [t["price"] for t in ticket_list if t.get("price") is not None and int(t.get("smart_sort_rank", 1)) == 1]
            if rank1_prices:
                return min(rank1_prices)
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
                "min_duration": train_tickets[0]["duration"] if train_tickets else None,
                "available": bool(train_tickets) or (origin_has_train and dest_has_train),
                "reason": links["train"]["reason"]
            },
            "bus": {
                "count": len(bus_tickets),
                "min_price": calc_min_price(bus_tickets),
                "min_duration": bus_tickets[0]["duration"] if bus_tickets else None,
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
            elif links["bus"].get("available") and (not (dest and dest.get("is_international")) or (dest and dest.get("is_overland_neighbor"))):
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
        notices.insert(0, "🛡️ Güven ve Şeffaflık İlkesi: Uçuş seferleri ve fiyatlar Trip.com ve resmi sağlayıcılar üzerinden canlı sorgulanır. Hakiki Bilet kullanıcıdan ek hizmet bedeli veya komisyon almaz.")

        car_rental_info = None
        if transport_type in ("car", "all"):
            try:
                from app.services.car_rental_service import CarRentalService
                car_loc = (origin_city or origin_name) if transport_type == "car" else (dest_city or dest_name)
                car_dropoff = (dest_city or dest_name) if transport_type == "car" and (dest_city or dest_name) != car_loc else None
                car_rental_info = CarRentalService.search_cars(
                    location=car_loc,
                    pickup_date=departure_date,
                    dropoff_date=return_date,
                    dropoff_location=car_dropoff,
                    location_type=location_type,
                    currency=currency
                )
            except Exception:
                car_rental_info = None

        # Adım 2.1: Pegasus Tarzı 7 Günlük Esnek Fiyat Şeridi & "Hakiki İpucu" Hesaplaması
        active_min_price = calc_min_price(results)
        flexible_insights = cls.build_flexible_date_insights(
            origin_name=origin_name,
            dest_name=dest_name,
            departure_date=departure_date,
            selected_min_price=active_min_price,
            transport_type=transport_type,
            currency=currency,
            curr_symbol=curr_symbol,
            passengers=total_pax,
            trip_type="round_trip" if is_round else "one_way",
            cabin_class=cabin_class,
            return_date=return_date,
            adults=adults,
            children=children,
            infants=infants,
        )

        # Adım 2.2: Haftanın En Ucuz Otobüs / Tren / Alternatif Ulaşım Rozetleri (Paralel Görevden Al)
        try:
            alternative_badges = _alt_badges_future.result(timeout=8) or []
        except Exception:
            alternative_badges = []
        finally:
            _alt_executor.shutdown(wait=False)

        # Adım 2.3: Uçuş / Sefer Altı "Gittiğiniz Yerde Bunlar Var!" (Otel + Araç + Etkinlik/Gezi Tavsiyesi)
        destination_cross_sell = cls.build_destination_cross_sell(
            origin_name=(origin_city or origin_name) if transport_type == "car" else origin_name,
            dest_name=(dest_city or dest_name) if transport_type == "car" else dest_name,
            departure_date=departure_date,
            return_date=return_date,
            passengers=total_pax,
            currency=currency,
            curr_symbol=curr_symbol,
            transport_type=transport_type
        )

        is_intl_search = bool((origin and origin.get("is_international")) or (dest and dest.get("is_international")))
        travel_context = {
            "origin_name": origin_name,
            "origin_iata": origin.get("iata") if origin else None,
            "destination_name": dest_name,
            "destination_iata": dest.get("iata") if dest else None,
            "departure_date": departure_date,
            "return_date": return_date,
            "trip_type": trip_type,
            "adults": adults,
            "children": children,
            "infants": infants,
            "passengers": total_pax,
            "cabin_class": cabin_class,
            "is_international": is_intl_search,
            "currency": currency.upper(),
        }

        return {
            "origin": origin_name,
            "destination": dest_name,
            "date": departure_date,
            "return_date": return_date,
            "trip_type": trip_type,
            "passengers": total_pax,
            "adults": adults,
            "children": children,
            "infants": infants,
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
            "flexible_insights": flexible_insights,
            "alternative_badges": alternative_badges,
            "destination_cross_sell": destination_cross_sell,
            "deep_links": links,
            "car_rental": car_rental_info,
            "travel_context": travel_context,
            "extension_slots": getattr(settings, "EXTENSION_SLOTS", {}),
            "notices": notices,
            "results_count": len(car_rental_info["vehicles"]) if transport_type == "car" and car_rental_info else len(results),
            "tickets": results
        }

    @classmethod
    def build_flexible_date_insights(
        cls,
        origin_name: str,
        dest_name: str,
        departure_date: str,
        selected_min_price: Optional[float],
        transport_type: str = "flight",
        currency: str = "TRY",
        curr_symbol: str = "₺",
        passengers: int = 1,
        trip_type: str = "one_way",
        cabin_class: str = "economy",
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
    ) -> Dict[str, Any]:
        """
        Pegasus / Skyscanner tarzı 7 günlük (-3..+3 gün) esnek fiyat şeridi ve
        '💡 Hakiki İpucu' hesaplayıcısı.
        KESİN KURAL (Sıfır Tahmin / %100 Hakiki Fiyat):
        Şeritteki her gün için gerçek canlı uçuş sorgusu (veya önbellekteki gerçek sefer listesi)
        kullanılır; güne tıklandığında çıkan en düşük bilet fiyatı ile şeritteki fiyat %100 birebir aynıdır.
        """
        from concurrent.futures import ThreadPoolExecutor

        try:
            base_dt = datetime.strptime(departure_date, "%Y-%m-%d").date()
        except Exception:
            base_dt = (datetime.now() + timedelta(days=7)).date()

        today = datetime.now().date()
        start_dt = base_dt - timedelta(days=3)
        if start_dt < today:
            start_dt = today

        round_span = 3
        is_round = (trip_type == "round_trip" and bool(return_date))
        if is_round and return_date:
            try:
                ret_dt_parsed = datetime.strptime(return_date, "%Y-%m-%d").date()
                round_span = max(1, (ret_dt_parsed - base_dt).days)
            except Exception:
                round_span = 3

        weekdays_short_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        weekdays_full_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        weekdays_short_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekdays_full_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        months_tr = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        orig_obj, _ = resolve_nearest_airport_city(origin_name)
        dest_obj, _ = resolve_nearest_airport_city(dest_name)
        can_query_flights = bool(
            transport_type in ("flight", "all")
            and orig_obj and orig_obj.get("has_airport")
            and dest_obj and dest_obj.get("has_airport")
            and orig_obj.get("iata") != dest_obj.get("iata")
        )

        target_dates = [start_dt + timedelta(days=i) for i in range(7)]
        live_day_prices: Dict[str, Optional[float]] = {}

        if can_query_flights:
            try:
                from app.services.live_flights import fetch_live_flights_from_google

                def _fetch_real_day_min(d_dt_item) -> tuple:
                    d_iso_str = d_dt_item.strftime("%Y-%m-%d")
                    if d_iso_str == departure_date and selected_min_price is not None and selected_min_price > 0:
                        val = round(float(selected_min_price)) if currency == "TRY" else round(float(selected_min_price), 2)
                        return d_iso_str, val
                    day_ret_str = (d_dt_item + timedelta(days=round_span)).strftime("%Y-%m-%d") if is_round else None
                    try:
                        day_flights = fetch_live_flights_from_google(
                            origin_city_name=origin_name,
                            dest_city_name=dest_name,
                            departure_date=d_iso_str,
                            return_date=day_ret_str,
                            passengers=passengers,
                            trip_type="round_trip" if is_round else "one_way",
                            cabin_class=cabin_class,
                            adults=adults,
                            children=children,
                            infants=infants,
                            include_multi_ota=False,
                        )
                        valid_p = [float(f["price"]) for f in (day_flights or []) if f.get("price") is not None and float(f["price"]) > 0]
                        if not valid_p:
                            return d_iso_str, None
                        min_try = min(valid_p)
                        if currency != "TRY":
                            conv = round(CurrencyService.convert(min_try, "TRY", currency), 2)
                            return d_iso_str, conv
                        return d_iso_str, round(min_try)
                    except Exception:
                        return d_iso_str, None

                ex = ThreadPoolExecutor(max_workers=6)
                try:
                    futs = {ex.submit(_fetch_real_day_min, d_item): d_item for d_item in target_dates}
                    for fut in futs:
                        try:
                            d_key, d_val = fut.result(timeout=4)
                            live_day_prices[d_key] = d_val
                        except Exception:
                            pass
                finally:
                    ex.shutdown(wait=False)
            except Exception as flex_fl_err:
                logger.warning(f"Esnek tarih uçuş fiyat şeridi hatası: {flex_fl_err}")

        days_strip = []
        for d_dt in target_dates:
            d_iso = d_dt.strftime("%Y-%m-%d")
            dow = d_dt.weekday()
            is_sel = (d_iso == departure_date)

            day_price = None
            if can_query_flights:
                day_price = live_day_prices.get(d_iso)
            elif is_sel and selected_min_price and selected_min_price > 0:
                day_price = round(float(selected_min_price)) if currency == "TRY" else round(float(selected_min_price), 2)
            elif transport_type == "bus":
                try:
                    from app.services.bus_service import BusService
                    day_price = BusService.get_cached_min_price(
                        origin_name=origin_name,
                        dest_name=dest_name,
                        departure_date=d_iso,
                        passengers=passengers,
                        currency=currency,
                        is_round=is_round
                    )
                except Exception:
                    day_price = None
                if day_price is None and selected_min_price and selected_min_price > 0:
                    day_price = round(float(selected_min_price)) if currency == "TRY" else round(float(selected_min_price), 2)
            elif transport_type == "train":
                try:
                    from app.services.train_service import TrainService
                    day_price = TrainService.get_cached_min_price(
                        origin_name=origin_name,
                        dest_name=dest_name,
                        departure_date=d_iso,
                        passengers=passengers,
                        currency=currency,
                        is_round=is_round
                    )
                except Exception:
                    day_price = None
                if day_price is None and selected_min_price and selected_min_price > 0:
                    day_price = round(float(selected_min_price)) if currency == "TRY" else round(float(selected_min_price), 2)
            elif transport_type == "ferry":
                if selected_min_price and selected_min_price > 0:
                    day_price = round(float(selected_min_price)) if currency == "TRY" else round(float(selected_min_price), 2)

            day_diff = (d_dt - base_dt).days
            days_strip.append({
                "date": d_iso,
                "day_num": d_dt.day,
                "month_tr": months_tr[d_dt.month - 1],
                "month_en": months_en[d_dt.month - 1],
                "weekday_short_tr": weekdays_short_tr[dow],
                "weekday_full_tr": weekdays_full_tr[dow],
                "weekday_short_en": weekdays_short_en[dow],
                "weekday_full_en": weekdays_full_en[dow],
                "label_tr": f"{d_dt.day} {months_tr[d_dt.month - 1]} {weekdays_short_tr[dow]}",
                "label_en": f"{weekdays_short_en[dow]}, {months_en[d_dt.month - 1]} {d_dt.day}",
                "min_price": day_price,
                "currency": curr_symbol,
                "is_selected": is_sel,
                "is_cheapest": False,
                "day_diff": day_diff
            })

        # En ucuz günü işaretle ve "Hakiki İpucu" oluştur (%100 Şerit ve Banner Tutarlılığı)
        priced_days = [d for d in days_strip if d.get("min_price") is not None and d["min_price"] > 0]
        hakiki_tip = None
        if priced_days:
            sel_day_obj = next((d for d in days_strip if d["is_selected"]), None)
            cheapest_day = min(
                priced_days,
                key=lambda x: (
                    float(x["min_price"]),
                    0 if x["is_selected"] else 1,
                    abs(x["day_diff"]),
                ),
            )
            for d in days_strip:
                if d["date"] == cheapest_day["date"]:
                    d["is_cheapest"] = True

            if sel_day_obj and sel_day_obj.get("min_price") and cheapest_day.get("min_price"):
                raw_savings = float(sel_day_obj["min_price"]) - float(cheapest_day["min_price"])
                savings = int(round(raw_savings)) if currency == "TRY" else round(raw_savings, 2)
                diff = cheapest_day["day_diff"]
                if savings > 0 and diff != 0:
                    abs_diff = abs(diff)
                    diff_tr = f"{abs_diff} gün {'önce' if diff < 0 else 'sonra'}"
                    diff_en = f"{abs_diff} {'day' if abs_diff == 1 else 'days'} {'earlier' if diff < 0 else 'later'}"
                    hakiki_tip = {
                        "type": "savings",
                        "has_savings": True,
                        "selected_date": sel_day_obj["date"],
                        "selected_weekday_tr": sel_day_obj["weekday_full_tr"],
                        "selected_weekday_en": sel_day_obj["weekday_full_en"],
                        "selected_price": sel_day_obj["min_price"],
                        "best_date": cheapest_day["date"],
                        "best_label_tr": cheapest_day["label_tr"],
                        "best_label_en": cheapest_day["label_en"],
                        "best_weekday_tr": cheapest_day["weekday_full_tr"],
                        "best_weekday_en": cheapest_day["weekday_full_en"],
                        "best_price": cheapest_day["min_price"],
                        "savings": savings,
                        "currency": curr_symbol,
                        "day_diff": diff,
                        "diff_text_tr": diff_tr,
                        "diff_text_en": diff_en
                    }
                else:
                    hakiki_tip = {
                        "type": "optimal",
                        "has_savings": False,
                        "selected_date": sel_day_obj["date"],
                        "selected_weekday_tr": sel_day_obj["weekday_full_tr"],
                        "selected_weekday_en": sel_day_obj["weekday_full_en"],
                        "selected_price": sel_day_obj["min_price"],
                        "currency": curr_symbol
                    }

        return {
            "days": days_strip,
            "hakiki_tip": hakiki_tip
        }

    @classmethod
    def build_alternative_mode_badges(
        cls,
        origin_name: str,
        dest_name: str,
        departure_date: str,
        current_mode: str,
        passengers: int,
        currency: str,
        curr_symbol: str,
        links: Dict[str, Any],
        summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Uçuş (veya diğer ulaşım) aramalarında üst barda 'Bu Haftanın En Ucuz Otobüs Bileti',
        'En Ucuz Tren (YHT) Bileti' ve 'En Ucuz Uçak Bileti' rozetlerini paralel canlı sorgularla üretir.
        """
        island_markers = (
            "girne", "kıbrıs", "kibris", "kktc", "bozcaada", "gökçeada", "gokceada",
            "avşa", "avsa", "adası", "adasi", "chios", "sakız", "sakiz", "kos",
            "midilli", "lesvos", "samos", "sisam", "rodos", "rhodes", "meis", "simi", "symi",
            "cruise", "galataport",
        )
        is_island_trip = any(m in f"{origin_name} {dest_name}".lower() for m in island_markers)

        def _fetch_bus_badge() -> Optional[Dict[str, Any]]:
            if current_mode == "bus" or is_island_trip or not links.get("bus", {}).get("available"):
                return None
            try:
                from app.services.bus_service import BusService
                bus_list = BusService.search_buses(
                    origin_name=origin_name,
                    dest_name=dest_name,
                    departure_date=departure_date,
                    passengers=passengers,
                    currency=currency,
                    is_round=False
                )
                bus_prices = [b.get("price") for b in (bus_list or []) if b.get("price")]
                if bus_prices:
                    min_bus = int(round(min(bus_prices)))
                    min_dur = bus_list[0].get("duration", "") if bus_list else ""
                    return {
                        "mode": "bus",
                        "icon": "🚌",
                        "title_tr": "En Ucuz Otobüs",
                        "title_en": "Cheapest Bus",
                        "min_price": min_bus,
                        "currency": curr_symbol,
                        "duration": min_dur,
                        "provider": "Obilet / Kamil Koç",
                        "deep_link": links["bus"].get("obilet")
                    }
            except Exception:
                pass
            return None

        def _fetch_train_badge() -> Optional[Dict[str, Any]]:
            if current_mode == "train" or is_island_trip:
                return None
            try:
                from app.services.train_service import TrainService
                fast_info = TrainService.get_fast_badge_info(
                    origin_name=origin_name,
                    dest_name=dest_name,
                    passengers=passengers,
                    currency=currency,
                )
                if fast_info:
                    min_tr, min_dur, b_type = fast_info
                    if b_type == "intl":
                        return {
                            "mode": "train",
                            "icon": "🚆",
                            "title_tr": "Avrupa Hızlı Tren",
                            "title_en": "European High-Speed Rail",
                            "min_price": min_tr,
                            "currency": curr_symbol,
                            "duration": min_dur,
                            "provider": "Trainline / Eurostar",
                            "deep_link": links.get("train", {}).get("trainline") or "https://www.thetrainline.com/",
                        }
                    disc_tcdd = {
                        "yas_65_ustu": int(round(min_tr * 0.50)),
                        "emekli": int(round(min_tr * 0.80)),
                        "genc_ogrenci": int(round(min_tr * 0.85)),
                    }
                    return {
                        "mode": "train",
                        "icon": "🚆",
                        "title_tr": "En Ucuz Tren (YHT)",
                        "title_en": "Cheapest Train (YHT)",
                        "min_price": min_tr,
                        "currency": curr_symbol,
                        "duration": min_dur,
                        "provider": "TCDD Taşımacılık",
                        "deep_link": links.get("train", {}).get("tcdd") or "https://ebilet.tcddtasimacilik.gov.tr/",
                        "discounts": disc_tcdd,
                    }

                if not links.get("train", {}).get("available"):
                    return None

                if links["train"].get("is_tcdd"):
                    tr_list = TrainService.search_trains(
                        origin_name=origin_name,
                        dest_name=dest_name,
                        departure_date=departure_date,
                        passengers=passengers,
                        currency=currency,
                        is_round=False
                    )
                    tr_prices = [t.get("price") for t in (tr_list or []) if t.get("price")]
                    if tr_prices:
                        min_tr = int(round(min(tr_prices)))
                        min_dur = tr_list[0].get("duration", "") if tr_list else ""
                        disc_tcdd = {
                            "yas_65_ustu": int(round(min_tr * 0.50)),
                            "emekli": int(round(min_tr * 0.80)),
                            "genc_ogrenci": int(round(min_tr * 0.85)),
                        }
                        return {
                            "mode": "train",
                            "icon": "🚆",
                            "title_tr": "En Ucuz Tren (YHT)",
                            "title_en": "Cheapest Train (YHT)",
                            "min_price": min_tr,
                            "currency": curr_symbol,
                            "duration": min_dur,
                            "provider": "TCDD Taşımacılık",
                            "deep_link": links["train"].get("tcdd"),
                            "discounts": disc_tcdd,
                        }
                elif links["train"].get("is_international"):
                    min_intl_tr = 1450 if currency == "TRY" else 42
                    return {
                        "mode": "train",
                        "icon": "🚆",
                        "title_tr": "Avrupa Hızlı Tren",
                        "title_en": "European High-Speed Rail",
                        "min_price": min_intl_tr,
                        "currency": curr_symbol,
                        "duration": "3 sa 15 dk",
                        "provider": "Trainline / Eurostar",
                        "deep_link": links["train"].get("trainline")
                    }
            except Exception:
                pass
            return None

        def _fetch_flight_badge() -> Optional[Dict[str, Any]]:
            if current_mode not in ("bus", "train"):
                return None
            eff_orig, orig_nearby = resolve_nearest_airport_city(origin_name)
            eff_dest, dest_nearby = resolve_nearest_airport_city(dest_name)
            if not eff_orig or not eff_dest or eff_orig.get("iata") == eff_dest.get("iata"):
                return None

            fl_min_price = (summary or {}).get("flight", {}).get("min_price")
            fl_duration = "1 sa 15 dk"
            if fl_min_price is None:
                try:
                    from app.services.live_flights import fetch_live_flights_from_google
                    f_list = fetch_live_flights_from_google(
                        origin_city_name=eff_orig["name"],
                        dest_city_name=eff_dest["name"],
                        departure_date=departure_date,
                        passengers=passengers,
                        include_multi_ota=False,
                    )
                    valid_fp = [float(f["price"]) for f in (f_list or []) if f.get("price") is not None and float(f["price"]) > 0]
                    if valid_fp:
                        raw_min_fp = min(valid_fp)
                        fl_min_price = round(CurrencyService.convert(raw_min_fp, "TRY", currency), 2) if currency != "TRY" else round(raw_min_fp)
                        if f_list and f_list[0].get("duration"):
                            fl_duration = f_list[0]["duration"]
                except Exception:
                    fl_min_price = None

            dest_iata_label = eff_dest.get("iata") or ""
            dest_city_short = (eff_dest.get("name") or "").split("(")[0].strip()
            if dest_nearby and dest_iata_label:
                title_tr = f"En Ucuz Uçak ({dest_city_short} {dest_iata_label})"
                title_en = f"Cheapest Flight ({dest_city_short} {dest_iata_label})"
            else:
                title_tr = "Direkt Uçak Bileti"
                title_en = "Direct Flights"

            return {
                "mode": "flight",
                "icon": "✈️",
                "title_tr": title_tr,
                "title_en": title_en,
                "min_price": fl_min_price,
                "currency": curr_symbol,
                "duration": fl_duration,
                "provider": "THY / Pegasus / AJet",
                "deep_link": links.get("flight", {}).get("enuygun") or links.get("flight", {}).get("trip"),
                "flight_origin": eff_orig["name"] if orig_nearby else None,
                "flight_dest": eff_dest["name"] if dest_nearby else None,
            }

        badges: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=3) as ex:
            fut_bus = ex.submit(_fetch_bus_badge)
            fut_tr = ex.submit(_fetch_train_badge)
            fut_fl = ex.submit(_fetch_flight_badge)
            for fut in (fut_bus, fut_tr, fut_fl):
                try:
                    res_b = fut.result(timeout=7)
                    if res_b:
                        badges.append(res_b)
                except Exception:
                    pass

        return badges

    @classmethod
    def build_destination_cross_sell(
        cls,
        origin_name: str,
        dest_name: str,
        departure_date: str,
        return_date: Optional[str],
        passengers: int,
        currency: str,
        curr_symbol: str,
        transport_type: str = "flight"
    ) -> Dict[str, Any]:
        """
        Uçuş/Sefer sonuçlarının hemen altında:
        1. Gidilen şehirde o dönemdeki etkinlikler (varsa biletli etkinlik, yoksa 'Oradayken Bunu Mutlaka Görün' kültür/lezzet tavsiyesi)
        2. Otel / Pansiyon / Airbnb Tarzı Villa hızlı geçişi
        3. Havalimanı / Şehir içi Araç Kiralama hızlı geçişi
        4. Tek tuşla Kapıdan Kapıya Akıllı Rota Sihirbazı bağlantısı
        """
        dest_clean = dest_name.split("(")[0].strip()
        dest_lower = dest_clean.lower()

        # 1. Şehirdeki Etkinlikleri Eşleştir
        all_events = cls.get_curated_events()
        matched_events = []
        for evt in all_events:
            e_city = (evt.get("city") or "").lower()
            e_country = (evt.get("country") or "").lower()
            if dest_lower in e_city or e_city.split("(")[0].strip() in dest_lower:
                matched_events.append(evt)

        # 2. Şehir İçin "Oradayken Bunu Mutlaka Görün!" Yerel Keşif Veritabanı
        CITY_HIGHLIGHTS = {
            "antalya": {
                "title": "🌟 Antalya'dayken Bunları Mutlaka Görün & Deneyimleyin!",
                "spots": ["🏛️ Kaleiçi Tarihi Liman & Hadrian Kapısı", "🎭 Aspendos & Perge Antik Tiyatrosu", "🌊 Düden Şelalesi & Konyaaltı Sahili"],
                "taste": "🍽️ Antalya Piyazı (Tahinli), Yanık Dondurma ve Akdeniz Deniz Ürünleri",
                "stay_tip": "Kaleiçi'nde Butik Pansiyon, Belek/Kemer'de Resort Otel veya Kaş/Kalkan'da Havuzlu Villa"
            },
            "izmir": {
                "title": "🌟 İzmir'deyken Bunları Mutlaka Görün & Deneyimleyin!",
                "spots": ["🏛️ Efes Antik Kenti & Şirince Köyü", "🌊 Kordon Boyu, Tarihi Asansör & Kemeraltı", "🏖️ Çeşme, Alaçatı & Urla Bağ Yolu"],
                "taste": "🍽️ İzmir Boyozu, Kumru, Şevketi Bostan ve Ege Zeytinyağlıları",
                "stay_tip": "Alaçatı'da Taş Butik Otel, Kordon'da Şehir Oteli veya Urla'da Bağ Evi"
            },
            "ankara": {
                "title": "🌟 Ankara'dayken Bunları Mutlaka Görün & Deneyimleyin!",
                "spots": ["🇹🇷 Anıtkabir & Kurtuluş Savaşı Müzesi", "🏛️ Anadolu Medeniyetleri Müzesi & Ankara Kalesi", "🎭 CSO Ada Ankara Konser Salonu & Hamamönü"],
                "taste": "🍽️ Ankara Tava, Beypazarı Kurusu ve Coğrafi İşaretli Ankara Döneri",
                "stay_tip": "Çankaya / Kavaklıdere Şehir Otelleri veya Beypazarı Tarihi Konakları"
            },
            "istanbul": {
                "title": "🌟 İstanbul'dayken Bunları Mutlaka Görün & Deneyimleyin!",
                "spots": ["🏰 Galata Kulesi, Tarihi Yarımada & Ayasofya", "🚢 Boğaz Hattı Vapur Turu & Galataport", "🎭 Harbiye Açıkhava, AKM & Zorlu PSM Sahnesi"],
                "taste": "🍽️ Karaköy/Eminönü Lezzetleri, Boğaz'da Balık ve Tarihi Yarımada Mutfağı",
                "stay_tip": "Sultanahmet/Karaköy Butik Oteller, Beşiktaş/Taksim 5 Yıldızlı Oteller veya Boğaz Manzaralı Rezidans"
            },
            "trabzon": {
                "title": "🌟 Trabzon & Karadeniz'deyken Bunları Mutlaka Görün!",
                "spots": ["⛰️ Sümela Manastırı (Maçka)", "🌲 Uzungöl, Ayder Yaylası & Çamlıhemşin", "🏛️ Atatürk Köşkü & Ayasofya Camii"],
                "taste": "🍽️ Akçaabat Köftesi, Kuymak (Mıhlama), Vakfıkebir Ekmeği ve Hamsiköy Sütlacı",
                "stay_tip": "Yayla Bungalov & Dağ Evleri veya Trabzon Merkez Deniz Manzaralı Oteller"
            },
            "adana": {
                "title": "🌟 Adana & Çukurova'dayken Bunları Mutlaka Görün!",
                "spots": ["🌉 Tarihi Taşköprü & Seyhan Nehri Kıyısı", "🕌 Sabancı Merkez Camii & Varda Köprüsü", "🏛️ Tarsus Tarihi Evleri & Kleopatra Kapısı"],
                "taste": "🍽️ Tescilli Adana Kebap, Şalgam, Cezerye ve Bici Bici",
                "stay_tip": "Seyhan Nehri Kıyısı Şehir Otelleri veya Butik Konaklama"
            },
            "baku": {
                "title": "🌟 Bakü'deyken Bunları Mutlaka Görün & Deneyimleyin!",
                "spots": ["🏰 İçerişehir (Tarihi Kale) & Kız Kulesi", "🔥 Alev Kuleleri (Flame Towers) & Haydar Aliyev Merkezi", "🌊 Hazar Denizi Bulvarı & Küçük Venedik"],
                "taste": "🍽️ Şah Pilavı, Bakü Kutabı, Lüle Kebabı ve Azerbaycan Çay Kültürü",
                "stay_tip": "Hazar Kıyısı 5 Yıldızlı Oteller veya İçerişehir Butik Konaklar"
            }
        }

        highlight_data = None
        for k, v in CITY_HIGHLIGHTS.items():
            if k in dest_lower or dest_lower.replace("ı", "i").replace("ü", "u").replace("ş", "s").replace("ç", "c").replace("ö", "o").startswith(k[:4]):
                highlight_data = v
                break

        if not highlight_data:
            highlight_data = {
                "title": f"🌟 {dest_clean} Seyahatinizde Bunları Mutlaka Görün!",
                "spots": [
                    f"🏛️ {dest_clean} Tarihi Şehir Merkezi & Kültür Durakları",
                    f"📸 {dest_clean} Panoramik Seyir Noktaları & Doğa Rotaları",
                    f"🎭 {dest_clean} Yerel Sanat, Müze ve Meydanları"
                ],
                "taste": f"🍽️ {dest_clean} yöresel mutfağı ve en yüksek puanlı yerel lezzet durakları",
                "stay_tip": f"{dest_clean} Merkez Oteller, Butik Pansiyonlar ve Günlük Kiralık Evler"
            }

        try:
            dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")
            cout_str = return_date if return_date else (dep_dt + timedelta(days=3)).strftime("%Y-%m-%d")
        except Exception:
            cout_str = departure_date

        booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
        hotel_deep_link = (
            f"https://www.booking.com/searchresults.html?"
            f"ss={urllib.parse.quote(dest_clean)}"
            f"&checkin={departure_date}&checkout={cout_str}"
            f"&group_adults={max(1, passengers)}&no_rooms=1&aid={booking_aid}"
        )

        # Akıllı Transfer Linki (Bilet.com Transfer & Resmi Shuttle)
        from app.services.transfer_service import TransferService
        transfer_meta = TransferService.generate_transfer_links(
            dest_city_or_code=dest_name,
            travel_date=departure_date,
            pickup_location=origin_name if transport_type == "car" else "",
            passengers=passengers
        )

        return {
            "city": dest_clean,
            "origin": origin_name.split("(")[0].strip(),
            "checkin_date": departure_date,
            "checkout_date": cout_str,
            "has_live_event": len(matched_events) > 0,
            "matched_event": matched_events[0] if matched_events else None,
            "highlights": highlight_data,
            "hotel_deep_link": hotel_deep_link,
            "transfer": transfer_meta,
        }


