import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.cities import find_city, resolve_nearest_airport_city, TURKEY_CITIES, FALLBACK_MAJOR_HUB_BY_IATA
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

        origin_is_intl = bool(origin and origin.get("is_international"))
        dest_is_intl = bool(dest and dest.get("is_international"))

        # İç hatlarda tarifeli iç hat uçuşu olmayan havalimanlarını (AOE Eskişehir, USQ Uşak) ana hub'a yönlendir
        if not origin_is_intl and not dest_is_intl:
            orig_fb = FALLBACK_MAJOR_HUB_BY_IATA.get(origin_iata or "")
            if orig_fb and orig_fb.get("domestic_inactive"):
                fb_city = find_city(orig_fb["hub_slug"])
                if fb_city:
                    eff_orig_airport = fb_city
                    origin_iata = orig_fb["hub_iata"]
            dest_fb = FALLBACK_MAJOR_HUB_BY_IATA.get(dest_iata or "")
            if dest_fb and dest_fb.get("domestic_inactive"):
                fb_city = find_city(dest_fb["hub_slug"])
                if fb_city:
                    eff_dest_airport = fb_city
                    dest_iata = dest_fb["hub_iata"]

        origin_has_airport = bool(origin_iata and ((origin and origin.get("has_airport")) or eff_orig_airport))
        dest_has_airport = bool(dest_iata and ((dest and dest.get("has_airport")) or eff_dest_airport) and origin_iata != dest_iata)
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))

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
        children = max(0, int(children or 0))
        infants = max(0, int(infants or 0))
        adults = max(int(adults or 1), int(passengers or 1) - children - infants, 1)

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
            flight_orig_slug = (eff_orig_airport.get("slug") if eff_orig_airport and eff_orig_airport.get("slug") else None) or origin_slug
            flight_dest_slug = (eff_dest_airport.get("slug") if eff_dest_airport and eff_dest_airport.get("slug") else None) or dest_slug

            # Pegasus ve AJet ana operasyon üssü Sabiha Gökçen (SAW) kilitlemesi:
            # Kullanıcı genel "İstanbul" seçtiyse ve rota iç hat ise, Pegasus'u SAW koduna yönlendirerek
            # IST üzerinden aktarmalı fahiş fiyat hatasını önle.
            pgs_orig_code = "saw" if (origin_iata == "IST" and "havalimanı" not in origin_city_name.lower() and "havalimani" not in origin_city_name.lower()) else origin_iata.lower()
            pgs_dest_code = "saw" if (dest_iata == "IST" and "havalimanı" not in dest_city_name.lower() and "havalimani" not in dest_city_name.lower()) else dest_iata.lower()
            pegasus_route = f"{flight_orig_slug}-{flight_dest_slug}-{pgs_orig_code}a-{pgs_dest_code}a"

            enuygun_route = f"{flight_orig_slug}-{flight_dest_slug}-{origin_iata.lower()}a-{dest_iata.lower()}a"
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
            trip_pax_param = f"&quantity={adults}" + (f"&childqty={children}" if children > 0 else "") + (f"&babyqty={infants}" if infants > 0 else "")
            flight_links["trip"] = f"https://tr.trip.com/flights/{flight_orig_slug}-to-{flight_dest_slug}/tickets-{origin_iata.lower()}-{dest_iata.lower()}?flighttype={trip_flighttype}&dcity={origin_iata.lower()}&acity={dest_iata.lower()}&ddate={departure_date}{trip_ret_param}{trip_pax_param}&curr={currency}{trip_aff_param}"
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
                orig_slug=flight_orig_slug,
                dest_slug=flight_dest_slug,
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

        # 2. Tren Deep Linkleri (TCDD E-Bilet & Avrupa Trip.com Trains / Trainline / Omio)
        train_links = {
            "available": train_available,
            "is_tcdd": is_tcdd_train,
            "is_international": is_intl_train,
            "reason": train_reason,
            "tcdd": "https://ebilet.tcddtasimacilik.gov.tr/" if is_tcdd_train else None,
            "trip_trains": TrainService.get_trip_train_deep_link(origin_slug, dest_slug, departure_date) if is_intl_train else None,
            "trainline": TrainService.get_trainline_deep_link(origin_slug, dest_slug, departure_date) if is_intl_train else None,
            "omio": TrainService.get_omio_deep_link(origin_slug, dest_slug, departure_date) if is_intl_train else None,
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
                "enuygun": None,
                "biletcom": None,
                "flixbus": None,
                "omio": None
            }
        else:
            from app.services.bus_service import BusService
            kamilkoc_bus_link = BusService.get_kamilkoc_deep_link(
                origin_city_name, dest_city_name, departure_date,
                passengers=adults + children,
                return_date=return_date if is_round else None
            )
            if is_intra_europe:
                bus_link = kamilkoc_bus_link
                omio_bus_link = BusService.get_omio_deep_link(origin_city_name, dest_city_name, departure_date)
                enuygun_bus_link = None
                biletcom_bus_link = None
            else:
                bus_link = BusService.get_obilet_deep_link(origin_city_name, dest_city_name, departure_date)
                omio_bus_link = BusService.get_omio_deep_link(origin_city_name, dest_city_name, departure_date) if is_overland else None
                enuygun_bus_link = BusService.get_enuygun_bus_deep_link(origin_city_name, dest_city_name, departure_date)
                biletcom_bus_link = BusService.get_biletcom_bus_deep_link(origin_city_name, dest_city_name, departure_date)

            bus_links = {
                "available": True,
                "is_overland_neighbor": is_overland or is_intra_europe,
                "reason": None,
                "obilet": None if is_intra_europe else bus_link,
                "kamilkoc": kamilkoc_bus_link,
                "pamukkale": None if is_intra_europe else bus_link,
                "enuygun": enuygun_bus_link,
                "biletcom": biletcom_bus_link,
                "flixbus": kamilkoc_bus_link if (is_intra_europe or is_overland) else None,
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

    @staticmethod
    def _haversine_km(lat1: Optional[float], lng1: Optional[float], lat2: Optional[float], lng2: Optional[float]) -> Optional[float]:
        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            return None
        try:
            import math
            r = 6371.0
            phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
            dphi = math.radians(float(lat2) - float(lat1))
            dlambda = math.radians(float(lng2) - float(lng1))
            a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
            return round(2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 1)
        except Exception:
            return None

    @staticmethod
    def _parse_duration_mins(dur_str: Optional[str]) -> int:
        if not dur_str:
            return 0
        import re
        s = str(dur_str).lower()
        hrs = 0
        mins = 0
        m_hr = re.search(r"(\d+)\s*(?:sa|saat|h|hr)", s)
        if m_hr:
            hrs = int(m_hr.group(1))
        m_mn = re.search(r"(\d+)\s*(?:dk|dakika|m|min)", s)
        if m_mn:
            mins = int(m_mn.group(1))
        if hrs == 0 and mins == 0:
            m_any = re.search(r"(\d+)", s)
            if m_any:
                hrs = int(m_any.group(1))
        return hrs * 60 + mins

    @staticmethod
    def _format_mins_tr(total_mins: int) -> str:
        if total_mins <= 0:
            return "1 sa"
        h = total_mins // 60
        m = total_mins % 60
        if h > 0 and m > 0:
            return f"{h} sa {m} dk"
        elif h > 0:
            return f"{h} sa"
        return f"{m} dk"

    @classmethod
    def build_smart_hub_analysis(
        cls,
        true_orig_obj: Optional[dict],
        true_dest_obj: Optional[dict],
        true_orig_name: str,
        true_dest_name: str,
        eff_orig_airport: Optional[dict],
        eff_dest_airport: Optional[dict],
        orig_redirected: bool,
        dest_redirected: bool,
        same_region_shield: bool,
        dist_orig_dest_km: Optional[float],
        flight_tickets: List[Dict[str, Any]],
        departure_date: str,
        passengers: int,
        currency: str,
        curr_symbol: str,
        links: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        4 KALKANLI AKILLI BAĞLANTI & TERS YÖN HAKEMİ:
        1) Kalkan 1 (Aynı İl / Komşu İlçe / Aynı Hub Kalkanı): <135 km veya aynı havalimanına (ADB->ADB, AYT->AYT)
           bağlanan noktalarda uçak aramasını durdurup doğrudan otobüs/tren/transfer alternatiflerini sunar.
        2) Kalkan 2 (Sıfır Hayali Sefer): Havalimanına ulaşımda (1. Adım / Son Adım) sadece gerçekten seferi olan
           ulaşım modlarını (Otobüs / TCDD Tren / Feribot / Havaş) fiyat ve süresiyle listeler.
        3) Kalkan 3 (Ters Yön & Süre/Maliyet Hakemi): (1. Adım + 90 dk Havalimanı Tamponu + Uçuş) toplam süresini
           ve maliyetini doğrudan otobüs/tren ile karşılaştırır. Uşak -> Antalya veya Edirne -> Sofya gibi ters yön /
           daha uzun süren rotalarda dürüstçe "Doğrudan Otobüs/Tren Daha Hızlı ve Ekonomik" uyarısı verir;
           Uşak -> Trabzon / Zürih gibi uzak rotalarda "2 Adımlı Akıllı Bağlantılı Rota" kartını açar.
        4) Kalkan 4 (Yurt Dışı Uçuş Hub Garantisi): Yurt dışı varışlarda küçük iç hat havalimanı yerine uluslararası
           ana merkez (IST, SAW, ADB, ESB, AYT) üzerinden bağlantı kurar.
        """
        if not same_region_shield and not orig_redirected and not dest_redirected:
            return None

        from app.services.bus_service import BusService
        from app.services.train_service import TrainService
        from app.services.ferry_service import FerryService

        def _clean_place_for_ground(p_name: str) -> str:
            s = (p_name or "").strip()
            if "istanbul" in s.lower() or "sabiha" in s.lower():
                return "İstanbul"
            s = s.split("(")[0].replace("Limanı", "").replace("İskelesi", "").strip()
            return s or p_name

        def _fmt_hub_label(c_name: str, iata_c: str) -> str:
            c_clean = (c_name or "").strip()
            if not iata_c:
                return c_clean
            if f"({iata_c})" in c_clean:
                return c_clean
            return f"{c_clean} ({iata_c})"

        def _query_verified_ground_legs(from_place: str, to_place: str, place_obj: Optional[dict] = None, hub_iata: str = "") -> List[Dict[str, Any]]:
            leg_opts: List[Dict[str, Any]] = []
            fp_clean = _clean_place_for_ground(from_place)
            tp_clean = _clean_place_for_ground(to_place)
            # 1. Otobüs kontrolü
            try:
                b_list = BusService.search_buses(
                    origin_name=fp_clean,
                    dest_name=tp_clean,
                    departure_date=departure_date,
                    passengers=passengers,
                    currency=currency,
                    is_round=False,
                )
                b_prices = [float(b["price"]) for b in (b_list or []) if b.get("price")]
                if b_list and b_prices:
                    min_b = int(round(min(b_prices)))
                    b_dur = b_list[0].get("duration") or "2 sa"
                    b_mins = cls._parse_duration_mins(b_dur) or 120
                    b_url = b_list[0].get("official_link") or BusService.get_obilet_deep_link(fp_clean, tp_clean, departure_date)
                    leg_opts.append({
                        "mode": "bus",
                        "icon": "🚌",
                        "label_tr": "Şehirlerarası Otobüs",
                        "label_en": "Intercity Bus",
                        "duration": b_dur,
                        "duration_mins": b_mins,
                        "min_price": min_b,
                        "currency": curr_symbol,
                        "provider": "Obilet / Kamil Koç",
                        "url": b_url,
                    })
            except Exception:
                pass

            # 2. TCDD Tren kontrolü (Sadece gerçek tarife varsa döner)
            try:
                t_list = TrainService.search_trains(
                    origin_name=fp_clean,
                    dest_name=tp_clean,
                    departure_date=departure_date,
                    passengers=passengers,
                    currency=currency,
                    is_round=False,
                )
                t_prices = [float(t["price"]) for t in (t_list or []) if t.get("price")]
                if t_list and t_prices:
                    min_t = int(round(min(t_prices)))
                    t_dur = t_list[0].get("duration") or "3 sa"
                    t_mins = cls._parse_duration_mins(t_dur) or 180
                    leg_opts.append({
                        "mode": "train",
                        "icon": "🚆",
                        "label_tr": f"TCDD Tren ({t_list[0].get('carrier', 'YHT/Anahat')})",
                        "label_en": "TCDD Rail",
                        "duration": t_dur,
                        "duration_mins": t_mins,
                        "min_price": min_t,
                        "currency": curr_symbol,
                        "provider": "TCDD Taşımacılık",
                        "url": "https://ebilet.tcddtasimacilik.gov.tr/",
                    })
            except Exception:
                pass

            # 3. Feribot kontrolü (Sadece gerçek deniz hattı varsa döner: örn. Bursa/Yalova/Bandırma -> İstanbul)
            try:
                f_routes = FerryService.find_matching_routes(fp_clean, tp_clean)
                if f_routes:
                    f_list = FerryService.search_ferries(
                        origin_name=fp_clean,
                        dest_name=tp_clean,
                        departure_date=departure_date,
                        passengers=passengers,
                        is_round=False,
                        currency=currency,
                    )
                    f_prices = [float(f["price"]) for f in (f_list or []) if f.get("price")]
                    if f_list and f_prices:
                        min_f = int(round(min(f_prices)))
                        f_dur = f_list[0].get("duration") or "1 sa 15 dk"
                        f_mins = cls._parse_duration_mins(f_dur) or 75
                        f_url = f_list[0].get("official_link") or "https://www.ido.com.tr/"
                        leg_opts.append({
                            "mode": "ferry",
                            "icon": "⛴️",
                            "label_tr": "Hızlı Feribot / Deniz Otobüsü",
                            "label_en": "Fast Ferry",
                            "duration": f_dur,
                            "duration_mins": f_mins,
                            "min_price": min_f,
                            "currency": curr_symbol,
                            "provider": f_list[0].get("carrier", "İDO / BUDO"),
                            "url": f_url,
                        })
            except Exception:
                pass

            # Eğer tatil ilçesi / yakın ilçe ise ve Havaş/Muttaş bilgisi varsa yedek olarak ekle
            if not leg_opts:
                hub_meta = (place_obj or {}).get("nearest_domestic_hub") or (place_obj or {}).get("nearest_intl_hub") or {}
                est_dur = hub_meta.get("duration") or "1 sa 15 dk"
                est_mins = cls._parse_duration_mins(est_dur) or 75
                leg_opts.append({
                    "mode": "shuttle",
                    "icon": "🚌",
                    "label_tr": "Havaş / Havalimanı Servisi & Otobüs",
                    "label_en": "Airport Shuttle / Bus",
                    "duration": est_dur,
                    "duration_mins": est_mins,
                    "min_price": None,
                    "currency": curr_symbol,
                    "provider": "Havaş / Obilet",
                    "url": BusService.get_obilet_deep_link(from_place, to_place, departure_date),
                })

            leg_opts.sort(key=lambda x: (x["duration_mins"], x["min_price"] or 999999))
            return leg_opts

        # KALKAN 1: Aynı İl / Komşu İlçe / Aynı Havalimanı (<135 km veya aynı IATA)
        if same_region_shield:
            direct_opts = _query_verified_ground_legs(true_orig_name, true_dest_name, true_orig_obj)
            best_opt = direct_opts[0] if direct_opts else None
            best_dur = best_opt["duration"] if best_opt else "~1 sa 15 dk"
            dist_txt = f" (~{int(round(dist_orig_dest_km))} km)" if dist_orig_dest_km else ""
            shared_iata = (eff_orig_airport.get("iata") if eff_orig_airport else "") or ""
            return {
                "verdict": "same_region_ground_only",
                "shield_badge_tr": "🛑 Kısa Mesafe & Aynı Havalimanı Kalkanı",
                "shield_badge_en": "🛑 Short Distance & Shared Airport Shield",
                "true_origin": true_orig_name,
                "true_destination": true_dest_name,
                "shared_airport_iata": shared_iata,
                "orig_hub_code": shared_iata,
                "dest_hub_code": shared_iata,
                "distance_km": dist_orig_dest_km,
                "title": f"{true_orig_name} ➔ {true_dest_name} Arasında Uçak Seferi Bulunmamaktadır",
                "title_tr": f"{true_orig_name} ➔ {true_dest_name} Arasında Uçak Seferi Bulunmamaktadır",
                "title_en": f"No Flights Between {true_orig_name} and {true_dest_name}",
                "summary_tr": (
                    f"{true_orig_name} ile {true_dest_name} aynı havalimanı ({shared_iata}) bölgesinde / yakın mesafede{dist_txt} yer almaktadır. "
                    f"Bu güzergahta uçak yerine doğrudan karayolu/raylı sistem ile {best_dur} sürede ulaşabilirsiniz."
                ),
                "summary_en": (
                    f"{true_orig_name} and {true_dest_name} share the same regional airport ({shared_iata}){dist_txt}. "
                    f"Direct ground transport takes {best_dur}."
                ),
                "direct_ground_options": direct_opts,
                "ground_modes": direct_opts,
                "origin_leg": None,
                "flight_leg": None,
                "dest_leg": None,
            }

        hub_orig_city = (eff_orig_airport["name"].split("(")[0].strip() if eff_orig_airport else true_orig_name)
        hub_orig_iata = (eff_orig_airport.get("iata") if eff_orig_airport else "") or "ADB"
        hub_dest_city = (eff_dest_airport["name"].split("(")[0].strip() if eff_dest_airport else true_dest_name)
        hub_dest_iata = (eff_dest_airport.get("iata") if eff_dest_airport else "") or "AYT"

        origin_leg = None
        leg1_mins = 0
        leg1_min_price = 0
        if orig_redirected:
            orig_opts = _query_verified_ground_legs(true_orig_name, hub_orig_city, true_orig_obj, hub_orig_iata)
            best_o = orig_opts[0] if orig_opts else None
            leg1_mins = best_o["duration_mins"] if best_o else 120
            leg1_min_price = best_o["min_price"] or 0 if best_o else 0
            lead_hours = round(max(2.5, (leg1_mins + 100) / 60.0) * 2) / 2
            lead_str = f"{int(lead_hours)}" if lead_hours == int(lead_hours) else f"{lead_hours}".replace(".", ",")
            origin_leg = {
                "from": true_orig_name,
                "to": _fmt_hub_label(f"{hub_orig_city} Havalimanı" if "Havalimanı" not in hub_orig_city else hub_orig_city, hub_orig_iata),
                "hub_city": hub_orig_city,
                "hub_iata": hub_orig_iata,
                "best_duration": best_o["duration"] if best_o else "2 sa",
                "best_price": best_o["min_price"] if best_o else None,
                "currency": curr_symbol,
                "safe_lead_hours_text": f"Uçuş saatinizden en az {lead_str} saat önce {true_orig_name} noktasından hareket eden seferi seçiniz.",
                "options": orig_opts,
            }

        dest_leg = None
        leg3_mins = 0
        leg3_min_price = 0
        if dest_redirected:
            dest_opts = _query_verified_ground_legs(hub_dest_city, true_dest_name, true_dest_obj, hub_dest_iata)
            best_d = dest_opts[0] if dest_opts else None
            leg3_mins = best_d["duration_mins"] if best_d else 90
            leg3_min_price = best_d["min_price"] or 0 if best_d else 0
            dest_leg = {
                "from": _fmt_hub_label(f"{hub_dest_city} Havalimanı" if "Havalimanı" not in hub_dest_city else hub_dest_city, hub_dest_iata),
                "to": true_dest_name,
                "hub_city": hub_dest_city,
                "hub_iata": hub_dest_iata,
                "best_duration": best_d["duration"] if best_d else "1 sa 30 dk",
                "best_price": best_d["min_price"] if best_d else None,
                "currency": curr_symbol,
                "options": dest_opts,
            }

        # Uçuş ayağı istatistikleri
        valid_fl_prices = [float(f["price"]) for f in (flight_tickets or []) if f.get("price") is not None and float(f["price"]) > 0]
        min_flight_price = int(round(min(valid_fl_prices))) if valid_fl_prices else None
        fl_durs = [cls._parse_duration_mins(f.get("duration")) for f in (flight_tickets or []) if f.get("duration")]
        fl_durs = [d for d in fl_durs if d > 0]
        flight_mins = min(fl_durs) if fl_durs else 75
        flight_dur_str = cls._format_mins_tr(flight_mins)

        airport_buffer_mins = 90  # Havalimanı güvenlik + bagaj + terminal geçiş tamponu
        combo_total_mins = leg1_mins + airport_buffer_mins + flight_mins + leg3_mins
        combo_total_dur_str = cls._format_mins_tr(combo_total_mins)
        combo_total_price = (leg1_min_price + min_flight_price + leg3_min_price) if min_flight_price else None

        flight_leg = {
            "from": _fmt_hub_label(hub_orig_city, hub_orig_iata),
            "to": _fmt_hub_label(hub_dest_city, hub_dest_iata),
            "from_iata": hub_orig_iata,
            "to_iata": hub_dest_iata,
            "duration": flight_dur_str,
            "duration_mins": flight_mins,
            "min_price": min_flight_price,
            "currency": curr_symbol,
            "flights_count": len(flight_tickets or []),
        }

        # KALKAN 3: Doğrudan Otobüs/Tren ile Ters Yön ve Süre/Maliyet Karşılaştırması
        is_dest_intl = bool(true_dest_obj and true_dest_obj.get("is_international"))
        is_orig_intl = bool(true_orig_obj and true_orig_obj.get("is_international"))
        is_overland = bool((true_dest_obj and true_dest_obj.get("is_overland_neighbor")) or (true_orig_obj and true_orig_obj.get("is_overland_neighbor")))

        direct_ground_options: List[Dict[str, Any]] = []
        if (not is_dest_intl and not is_orig_intl) or is_overland:
            direct_ground_options = _query_verified_ground_legs(true_orig_name, true_dest_name, true_orig_obj)
            # Sadece gerçek otobüs/tren/feribot olanları tut (shuttle tahminini doğrudan şehirlerarası karşılaştırmaya sokma)
            direct_ground_options = [o for o in direct_ground_options if o["mode"] in ("bus", "train", "ferry") and (o.get("min_price") is not None or is_overland)]

        best_direct = direct_ground_options[0] if direct_ground_options else None
        direct_mins = best_direct["duration_mins"] if best_direct else None
        direct_price = best_direct["min_price"] if best_direct else None

        # Coğrafi Ters Yön Tespiti: Havalimanı varış noktasına asıl kalkış noktasından daha uzaksa!
        dist_hub_dest_km = None
        if orig_redirected and eff_orig_airport and true_dest_obj:
            dist_hub_dest_km = cls._haversine_km(
                eff_orig_airport.get("lat"), eff_orig_airport.get("lng"),
                true_dest_obj.get("lat"), true_dest_obj.get("lng")
            )
        is_reverse_direction = bool(
            dist_orig_dest_km is not None
            and dist_hub_dest_km is not None
            and (dist_hub_dest_km > dist_orig_dest_km + 35)
        )
        # Sınır komşusu ters yön (Örn: Edirne -> Sofya/Selanik için doğuya İstanbul'a geri gitmek)
        if is_overland and orig_redirected and true_orig_obj and true_orig_obj.get("slug") in ("edirne", "kirklareli", "artvin", "rize"):
            is_reverse_direction = True
            if not best_direct:
                best_direct = {
                    "mode": "bus",
                    "icon": "🚌",
                    "label_tr": "Uluslararası Doğrudan Otobüs",
                    "label_en": "Direct International Bus",
                    "duration": "3 sa 15 dk",
                    "duration_mins": 195,
                    "min_price": None,
                    "currency": curr_symbol,
                    "provider": "Kamil Koç / FlixBus / Obilet",
                    "url": BusService.get_kamilkoc_deep_link(true_orig_name, true_dest_name, departure_date, passengers=passengers),
                }
                direct_ground_options = [best_direct]
                direct_mins = 195

        # KARAR (VERDICT):
        # 1) Doğrudan otobüs/tren toplam uçuş+aktarma süresinden daha kısaysa (veya en fazla 45 dk fark varsa)
        #    VEYA havalimanı ters yöndeyse ve doğrudan karayolu <= 6 saat (360 dk) ise -> "direct_ground_better"
        if best_direct and direct_mins and (
            direct_mins <= combo_total_mins + 45
            or (is_reverse_direction and direct_mins <= 360)
        ):
            time_diff_mins = max(0, combo_total_mins - direct_mins)
            time_saved_txt = f" ({cls._format_mins_tr(time_diff_mins)} daha hızlı)" if time_diff_mins >= 15 else ""
            rev_txt = f" {hub_orig_city} ({hub_orig_iata}) havalimanı ters yönde kaldığından," if is_reverse_direction else ""
            d_price_txt = f" (~{direct_price:,} {curr_symbol})".replace(",", ".") if direct_price else ""
            c_price_txt = f" (~{combo_total_price:,} {curr_symbol})".replace(",", ".") if combo_total_price else ""

            return {
                "verdict": "direct_ground_better",
                "is_reverse_direction": is_reverse_direction,
                "shield_badge_tr": "⚠️ Ters Yön & Süre Hakemi Uyarısı" if is_reverse_direction else "💡 Hakiki Süre & Maliyet Analizi",
                "shield_badge_en": "⚠️ Reverse Direction & Time Alert" if is_reverse_direction else "💡 Smart Time & Cost Analysis",
                "true_origin": true_orig_name,
                "true_destination": true_dest_name,
                "orig_hub_code": hub_orig_iata,
                "dest_hub_code": hub_dest_iata,
                "title": f"Doğrudan {best_direct['label_tr']} ({best_direct['duration']}), Aktarmalı Uçuştan ({combo_total_dur_str}) Daha Avantajlı!",
                "title_tr": f"Doğrudan {best_direct['label_tr']} ({best_direct['duration']}), Aktarmalı Uçuştan ({combo_total_dur_str}) Daha Avantajlı!",
                "title_en": f"Direct {best_direct['label_en']} ({best_direct['duration']}) Beats Connecting Flight ({combo_total_dur_str})!",
                "summary_tr": (
                    f"{true_orig_name} şehrinde aktif havalimanı bulunmamaktadır.{rev_txt} "
                    f"{hub_orig_city} ({hub_orig_iata}) üzerinden uçmak; karayolu transferi ({origin_leg['best_duration'] if origin_leg else '1 sa 30 dk'}), "
                    f"havalimanı beklemesi (1 sa 30 dk) ve uçuş ({flight_dur_str}) ile toplam {combo_total_dur_str}{c_price_txt} sürmektedir. "
                    f"Oysa doğrudan {true_orig_name} ➔ {true_dest_name} {best_direct['label_tr'].lower()} seferi yalnızca {best_direct['duration']}{d_price_txt} sürer{time_saved_txt}."
                ),
                "summary_en": (
                    f"Flying via {hub_orig_city} ({hub_orig_iata}) takes {combo_total_dur_str} total including ground transfer and airport buffer, "
                    f"whereas direct {best_direct['label_en'].lower()} takes only {best_direct['duration']}{d_price_txt}."
                ),
                "combo_total_duration": combo_total_dur_str,
                "combo_total_mins": combo_total_mins,
                "combo_total_price": combo_total_price,
                "best_direct_option": best_direct,
                "direct_ground_options": direct_ground_options,
                "ground_modes": direct_ground_options,
                "origin_leg": origin_leg,
                "flight_leg": flight_leg,
                "dest_leg": dest_leg,
            }

        # 2) Uçmak gerçekten zaman kazandırıyorsa -> "smart_combo_recommended" (2/3 Adımlı Akıllı Bağlantılı Rota)
        saved_mins = (direct_mins - combo_total_mins) if (direct_mins and direct_mins > combo_total_mins) else None
        saved_badge_tr = f"⚡ Karayoluna Göre ~{cls._format_mins_tr(saved_mins)} Zaman Kazandırır" if (saved_mins and saved_mins >= 90) else "🧭 En Hızlı Havalimanı Bağlantılı Plan"
        route_chain = []
        if orig_redirected:
            route_chain.append(true_orig_name)
        route_chain.append(f"{hub_orig_city} ({hub_orig_iata})")
        route_chain.append(f"{hub_dest_city} ({hub_dest_iata})")
        if dest_redirected:
            route_chain.append(true_dest_name)

        return {
            "verdict": "smart_combo_recommended",
            "is_reverse_direction": False,
            "shield_badge_tr": saved_badge_tr,
            "shield_badge_en": "🧭 Smart Connected Route Plan",
            "true_origin": true_orig_name,
            "true_destination": true_dest_name,
            "orig_hub_code": hub_orig_iata,
            "dest_hub_code": hub_dest_iata,
            "route_chain_text": " ➔ ".join(route_chain),
            "title": f"Akıllı Bağlantılı Rota: {' ➔ '.join(route_chain)}",
            "title_tr": f"Akıllı Bağlantılı Rota: {' ➔ '.join(route_chain)}",
            "title_en": f"Smart Connected Route: {' ➔ '.join(route_chain)}",
            "summary_tr": (
                f"{true_orig_name if orig_redirected else true_dest_name} noktasında doğrudan uçuş bulunmadığından en hızlı ulaşım "
                f"toplam ~{combo_total_dur_str} süren aşağıdaki adım adım bağlantılı plan ile sağlanmaktadır:"
            ),
            "summary_en": (
                f"Step-by-step connected itinerary via {hub_orig_city} ({hub_orig_iata}) with an estimated total travel time of ~{combo_total_dur_str}:"
            ),
            "combo_total_duration": combo_total_dur_str,
            "combo_total_mins": combo_total_mins,
            "combo_total_price": combo_total_price,
            "best_direct_option": best_direct,
            "direct_ground_options": direct_ground_options,
            "ground_modes": direct_ground_options,
            "origin_leg": origin_leg,
            "flight_leg": flight_leg,
            "dest_leg": dest_leg,
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
        adults: int = 1, children: int = 0, infants: int = 0,
        raw_origin: Optional[str] = None, raw_destination: Optional[str] = None,
    ):
        # Yolcu sayılarını normalize et
        children = max(0, int(children or 0))
        infants = max(0, int(infants or 0))
        adults = max(int(adults or 1), int(passengers or 1) - children - infants, 1)
        total_pax = adults + children + infants

        # 1. "Her Yere" arama modu kontrolü
        if dest_city.lower() in ("her yere", "farketmez", "her-yere", "anywhere"):
            return cls.search_anywhere(origin_city, departure_date, transport_type, total_pax)

        origin = find_city(origin_city)
        dest = find_city(dest_city)

        # Tren, Otobüs ve Feribot modlarında SAW / IST gibi alt havalimanı nesnelerini ana İstanbul iline normalize et
        _orig_airport_sub_label = None
        _dest_airport_sub_label = None
        if transport_type in ("train", "bus", "ferry"):
            if origin and origin.get("slug") in ("istanbul-sabiha-gokcen", "istanbul-havalimani"):
                _orig_airport_sub_label = origin.get("name")
                origin = find_city("İstanbul") or origin
            if dest and dest.get("slug") in ("istanbul-sabiha-gokcen", "istanbul-havalimani"):
                _dest_airport_sub_label = dest.get("name")
                dest = find_city("İstanbul") or dest

        origin_name = origin["name"] if origin else origin_city
        dest_name = dest["name"] if dest else dest_city

        # Kullanıcının ilk yazdığı şehir/ilçe bilgisini (örn. Uşak, Çeşme, Edirne, Bursa) tespit et
        _AIRPORT_SHORTHANDS = {
            "saw", "ist", "ahl", "esb", "adb", "ayt", "ksy", "tzx", "bjv", "dlm", "cov", "ada", "gzp",
            "asr", "gzt", "diy", "erz", "erc", "van", "szf", "mqm", "rzv", "nav", "vas", "kya", "aoe",
            "mlx", "ezs", "bal", "dnz", "edo", "usq", "kzr", "afy", "ise", "onq", "kco", "teq", "yei",
            "ckz", "sxz", "mzh", "tjk", "nop", "kfs", "ogu", "hty", "gny", "adf", "aji", "igd", "yko",
            "nkt", "bgg", "msr", "sabiha", "sabiha gokcen", "esenboga", "adnan menderes", "cukurova",
        }
        raw_orig_clean = (raw_origin or "").strip()
        raw_dest_clean = (raw_destination or "").strip()
        true_orig_obj = (
            find_city(raw_orig_clean)
            if (raw_orig_clean and raw_orig_clean.lower() not in _AIRPORT_SHORTHANDS)
            else origin
        ) or origin
        true_dest_obj = (
            find_city(raw_dest_clean)
            if (raw_dest_clean and raw_dest_clean.lower() not in _AIRPORT_SHORTHANDS)
            else dest
        ) or dest
        true_orig_name = (
            raw_orig_clean
            if (raw_orig_clean and true_orig_obj and ("Limanı" in true_orig_obj.get("name", "") or "İskelesi" in true_orig_obj.get("name", "")) and transport_type != "ferry")
            else (true_orig_obj["name"].split("(")[0].strip() if true_orig_obj else (raw_orig_clean or origin_name))
        )
        true_dest_name = (
            raw_dest_clean
            if (raw_dest_clean and true_dest_obj and ("Limanı" in true_dest_obj.get("name", "") or "İskelesi" in true_dest_obj.get("name", "")) and transport_type != "ferry")
            else (true_dest_obj["name"].split("(")[0].strip() if true_dest_obj else (raw_dest_clean or dest_name))
        )
        true_orig_slug = true_orig_obj.get("slug") if true_orig_obj else true_orig_name.lower().replace(" ", "-")
        true_dest_slug = true_dest_obj.get("slug") if true_dest_obj else true_dest_name.lower().replace(" ", "-")

        # 1.1 Aynı Kalkış ve Varış Noktası Erken Koruması (Sadece kullanıcının asıl kalkış ve varış yeri birebir aynıysa)
        orig_slug = origin["slug"] if origin else origin_city.lower().replace(" ", "-")
        dest_slug = dest["slug"] if dest else dest_city.lower().replace(" ", "-")
        if transport_type != "car" and (true_orig_slug == true_dest_slug or true_orig_name.strip().lower() == true_dest_name.strip().lower()):
            currency_norm = (currency or "TRY").upper()
            curr_sym = CurrencyService.get_symbol(currency_norm)
            links = cls.generate_deep_links(
                origin_name, dest_name, departure_date, return_date, total_pax, trip_type, 
                cabin_class=cabin_class, currency=currency_norm,
                adults=adults, children=children, infants=infants
            )
            same_city_hotel_info = None
            if include_hotel or search_mode == "smart_route":
                try:
                    same_city_hotel_info = HotelService.get_hotel_recommendation(
                        dest_city=dest_city or dest_name,
                        checkin_date=departure_date,
                        checkout_date=return_date,
                        guests=total_pax,
                        currency=currency_norm,
                    )
                except Exception as he:
                    logger.warning(f"Same-city hotel recommendation error: {he}")
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
                "notices": [] if include_hotel else ["⚠️ Kalkış ve varış noktası aynı olamaz. Lütfen farklı bir varış şehri belirleyiniz."],
                "hotel_info": same_city_hotel_info,
                "price_calendar": {"days": [], "days_count": 0, "range_type": calendar_range, "tip": ""}
            }

        eff_orig_airport, orig_nearby_airport = resolve_nearest_airport_city(true_orig_obj or origin or origin_name)
        eff_dest_airport, dest_nearby_airport = resolve_nearest_airport_city(true_dest_obj or dest or dest_name)

        is_any_intl = bool(
            (true_orig_obj and true_orig_obj.get("is_international"))
            or (true_dest_obj and true_dest_obj.get("is_international"))
            or (origin and origin.get("is_international"))
            or (dest and dest.get("is_international"))
        )

        # KALKAN 4: Yurt dışı uçuşlarda küçük iç hat havalimanı yerine uluslararası ana merkezi (nearest_intl_hub / FALLBACK_MAJOR_HUB_BY_IATA) baz al
        if is_any_intl and transport_type in ("flight", "all"):
            if true_orig_obj and not true_orig_obj.get("is_international"):
                intl_o = true_orig_obj.get("nearest_intl_hub")
                fb_intl_o = find_city(intl_o.get("iata") or intl_o.get("city", "")) if intl_o else None
                if not fb_intl_o:
                    cur_o_iata = (eff_orig_airport.get("iata") if eff_orig_airport else "") or (true_orig_obj.get("iata") or "")
                    fb_chk_o = FALLBACK_MAJOR_HUB_BY_IATA.get(cur_o_iata.upper())
                    if fb_chk_o:
                        fb_intl_o = find_city(fb_chk_o["hub_slug"])
                if fb_intl_o:
                    eff_orig_airport = fb_intl_o
                    origin = fb_intl_o
                    origin_name = fb_intl_o["name"]
            if true_dest_obj and not true_dest_obj.get("is_international"):
                intl_d = true_dest_obj.get("nearest_intl_hub")
                fb_intl_d = find_city(intl_d.get("iata") or intl_d.get("city", "")) if intl_d else None
                if not fb_intl_d:
                    cur_d_iata = (eff_dest_airport.get("iata") if eff_dest_airport else "") or (true_dest_obj.get("iata") or "")
                    fb_chk_d = FALLBACK_MAJOR_HUB_BY_IATA.get(cur_d_iata.upper())
                    if fb_chk_d:
                        fb_intl_d = find_city(fb_chk_d["hub_slug"])
                if fb_intl_d:
                    eff_dest_airport = fb_intl_d
                    dest = fb_intl_d
                    dest_name = fb_intl_d["name"]
        elif not is_any_intl:
            orig_fb_chk = FALLBACK_MAJOR_HUB_BY_IATA.get((eff_orig_airport.get("iata") if eff_orig_airport else "") or "")
            if orig_fb_chk and orig_fb_chk.get("domestic_inactive"):
                fb_c = find_city(orig_fb_chk["hub_slug"])
                if fb_c:
                    eff_orig_airport = fb_c
            dest_fb_chk = FALLBACK_MAJOR_HUB_BY_IATA.get((eff_dest_airport.get("iata") if eff_dest_airport else "") or "")
            if dest_fb_chk and dest_fb_chk.get("domestic_inactive"):
                fb_c = find_city(dest_fb_chk["hub_slug"])
                if fb_c:
                    eff_dest_airport = fb_c

        # KALKAN 1: Aynı İl / Komşu İlçe / Aynı Havalimanı (<135 km veya aynı IATA) tespiti
        dist_orig_dest_km = cls._haversine_km(
            true_orig_obj.get("lat") if true_orig_obj else None,
            true_orig_obj.get("lng") if true_orig_obj else None,
            true_dest_obj.get("lat") if true_dest_obj else None,
            true_dest_obj.get("lng") if true_dest_obj else None,
        )
        same_airport_iata = bool(
            eff_orig_airport
            and eff_dest_airport
            and eff_orig_airport.get("iata")
            and eff_orig_airport.get("iata") == eff_dest_airport.get("iata")
        )
        same_region_shield = bool(
            transport_type == "flight"
            and (
                same_airport_iata
                or (dist_orig_dest_km is not None and dist_orig_dest_km < 135.0 and not is_any_intl)
            )
        )

        _JOINT_HUB_SLUGS = {
            ("adana", "mersin"), ("mersin", "adana"),
            ("rize", "artvin"), ("artvin", "rize"),
            ("ordu", "giresun"), ("giresun", "ordu"),
            ("istanbul", "istanbul-sabiha-gokcen"), ("istanbul", "istanbul-havalimani"),
        }
        orig_redirected = bool(
            transport_type == "flight"
            and not same_region_shield
            and true_orig_obj
            and eff_orig_airport
            and true_orig_obj.get("slug") != eff_orig_airport.get("slug")
            and (true_orig_obj.get("slug"), eff_orig_airport.get("slug")) not in _JOINT_HUB_SLUGS
            and (
                not true_orig_obj.get("has_airport")
                or true_orig_obj.get("is_district")
                or (true_orig_obj.get("iata") or "") != (eff_orig_airport.get("iata") or "")
            )
        )
        dest_redirected = bool(
            transport_type == "flight"
            and not same_region_shield
            and true_dest_obj
            and eff_dest_airport
            and true_dest_obj.get("slug") != eff_dest_airport.get("slug")
            and (true_dest_obj.get("slug"), eff_dest_airport.get("slug")) not in _JOINT_HUB_SLUGS
            and (
                not true_dest_obj.get("has_airport")
                or true_dest_obj.get("is_district")
                or (true_dest_obj.get("iata") or "") != (eff_dest_airport.get("iata") or "")
            )
        )

        # Eğer uçak modunda havalimanı olmayan bir il/ilçe girilmişse uçuş sorgusunu çözümlenmiş hub üzerinden yap
        if transport_type == "flight":
            if orig_redirected and eff_orig_airport:
                origin_name = eff_orig_airport["name"]
            if dest_redirected and eff_dest_airport:
                dest_name = eff_dest_airport["name"]

        origin_has_airport = bool(eff_orig_airport and eff_orig_airport.get("has_airport") and not same_region_shield)
        dest_has_airport = bool(
            eff_dest_airport
            and eff_dest_airport.get("has_airport")
            and eff_orig_airport
            and eff_orig_airport.get("iata") != eff_dest_airport.get("iata")
            and not same_region_shield
        )
        origin_has_train = bool(origin and origin.get("has_train"))
        dest_has_train = bool(dest and dest.get("has_train"))

        currency = (currency or "TRY").upper()
        curr_symbol = CurrencyService.get_symbol(currency)

        links = cls.generate_deep_links(
            true_orig_name if transport_type != "flight" else origin_name,
            true_dest_name if transport_type != "flight" else dest_name,
            departure_date, return_date, total_pax, trip_type, 
            cabin_class=cabin_class, currency=currency,
            adults=adults, children=children, infants=infants
        )
        results = []
        notices = []

        is_round = (trip_type == "round_trip" and return_date)

        # Alternatif ulaşım rozetlerini kullanıcının asıl kalkış/varış noktası (örn. Uşak -> Antalya) üzerinden paralel başlat!
        _alt_executor = None
        _alt_badges_future = None
        _hotel_executor = None
        _hotel_future = None
        if include_hotel or search_mode == "smart_route":
            _hotel_executor = ThreadPoolExecutor(max_workers=1)
            _hotel_future = _hotel_executor.submit(
                HotelService.get_hotel_recommendation,
                dest_city=true_dest_name or dest_city or dest_name,
                checkin_date=departure_date,
                checkout_date=return_date,
                guests=total_pax,
                currency=currency,
            )
        else:
            _alt_links = cls.generate_deep_links(
                true_orig_name, true_dest_name, departure_date, return_date, total_pax, trip_type,
                cabin_class=cabin_class, currency=currency,
                adults=adults, children=children, infants=infants
            ) if (orig_redirected or dest_redirected or same_region_shield) else links
            _alt_executor = ThreadPoolExecutor(max_workers=1)
            _alt_badges_future = _alt_executor.submit(
                cls.build_alternative_mode_badges,
                origin_name=true_orig_name,
                dest_name=true_dest_name,
                departure_date=departure_date,
                current_mode=transport_type,
                passengers=total_pax,
                currency=currency,
                curr_symbol=curr_symbol,
                links=_alt_links,
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
                        infants=infants,
                        include_multi_ota=(not include_hotel),
                    )
                    if live_flights:
                        for lf in live_flights:
                            if lf.get("route_notice"):
                                for rn_part in str(lf["route_notice"]).split("•"):
                                    rn_clean = rn_part.strip()
                                    if rn_clean and "aktarmalıdır" not in rn_clean and rn_clean not in notices:
                                        notices.append(rn_clean)
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
                    orig_iata = (origin.get('iata') if origin and origin.get('iata') else None) or (eff_orig_airport.get('iata') if eff_orig_airport else None) or 'SAW'
                    dst_iata = (dest.get('iata') if dest and dest.get('iata') else None) or (eff_dest_airport.get('iata') if eff_dest_airport else None) or 'ESB'
                    fl_orig_slug = (eff_orig_airport.get('slug') if eff_orig_airport and eff_orig_airport.get('slug') else None) or orig_slug
                    fl_dest_slug = (eff_dest_airport.get('slug') if eff_dest_airport and eff_dest_airport.get('slug') else None) or dest_slug
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
                        orig_slug=fl_orig_slug,
                        dest_slug=fl_dest_slug,
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
            if transport_type == "train":
                if _orig_airport_sub_label or (len((origin_city or "").strip()) == 3 and (origin_city or "").strip().isalpha()):
                    raw_lbl = _orig_airport_sub_label or (origin_city or "").strip().upper()
                    notices.append(f"ℹ️ Tren sekmesinde '{raw_lbl}' havalimanı kodu yerine {origin_name} (Söğütlüçeşme / Pendik YHT) garı baz alınmıştır.")
                if _dest_airport_sub_label or (len((dest_city or "").strip()) == 3 and (dest_city or "").strip().isalpha()):
                    raw_d_lbl = _dest_airport_sub_label or (dest_city or "").strip().upper()
                    notices.append(f"ℹ️ Tren sekmesinde '{raw_d_lbl}' havalimanı kodu yerine {dest_name} Garı baz alınmıştır.")
            from app.services.train_service import TrainService
            train_tickets = TrainService.search_trains(
                origin_name=origin_city if ("YHT" in (origin_city or "") or "Gar" in (origin_city or "")) else origin_name,
                dest_name=dest_city if ("YHT" in (dest_city or "") or "Gar" in (dest_city or "")) else dest_name,
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
                    notices.append(msg if str(msg).startswith(("⚠️", "ℹ️")) else f"⚠️ {msg}")
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

        # Otel Bilgisi ve Fırsat Önerisi (Paralel başlatılan otel sorgusunun sonucunu al)
        hotel_info = None
        if _hotel_future is not None:
            try:
                hotel_info = _hotel_future.result(timeout=14.0)
            except Exception as he:
                logger.warning(f"Parallel hotel recommendation warning: {he}")
                hotel_info = None
            finally:
                if _hotel_executor:
                    _hotel_executor.shutdown(wait=False)
        elif include_hotel or search_mode == "smart_route":
            hotel_info = HotelService.get_hotel_recommendation(
                dest_city=dest_city or dest_name,
                checkin_date=departure_date,
                checkout_date=return_date,
                guests=total_pax,
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
        if transport_type == "car" or (transport_type == "all" and not include_hotel):
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
        if include_hotel:
            flexible_insights = {"days": [], "tip": None}
        else:
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
        alternative_badges = []
        if _alt_badges_future is not None:
            try:
                alternative_badges = _alt_badges_future.result(timeout=8) or []
            except Exception:
                alternative_badges = []
            finally:
                if _alt_executor is not None:
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

        smart_hub_analysis = None
        if transport_type == "flight" and flight_tickets and not same_region_shield:
            # Eğer canlı uçuş servisi kısıtlı havalimanından (örn. YEI, KZR, TEQ) ana hub'a (SAW, IST, ESB) otomatik geçiş yaptıysa yakala
            first_fl = flight_tickets[0]
            fl_from_code = (first_fl.get("from_code") or "").upper()
            fl_to_code = (first_fl.get("to_code") or "").upper()
            orig_true_iatas = {
                (true_orig_obj.get("iata") or "").upper(),
                (true_orig_obj.get("alt_iata") or "").upper(),
            } - {""}
            dest_true_iatas = {
                (true_dest_obj.get("iata") or "").upper(),
                (true_dest_obj.get("alt_iata") or "").upper(),
            } - {""}
            if fl_from_code and orig_true_iatas and fl_from_code not in orig_true_iatas:
                resolved_fl_orig = find_city(fl_from_code)
                if resolved_fl_orig and (true_orig_obj.get("slug"), resolved_fl_orig.get("slug")) not in _JOINT_HUB_SLUGS:
                    eff_orig_airport = resolved_fl_orig
                    orig_redirected = True
            if fl_to_code and dest_true_iatas and fl_to_code not in dest_true_iatas:
                resolved_fl_dest = find_city(fl_to_code)
                if resolved_fl_dest and (true_dest_obj.get("slug"), resolved_fl_dest.get("slug")) not in _JOINT_HUB_SLUGS:
                    eff_dest_airport = resolved_fl_dest
                    dest_redirected = True

        if transport_type == "flight" and (same_region_shield or orig_redirected or dest_redirected):
            try:
                smart_hub_analysis = cls.build_smart_hub_analysis(
                    true_orig_obj=true_orig_obj,
                    true_dest_obj=true_dest_obj,
                    true_orig_name=true_orig_name,
                    true_dest_name=true_dest_name,
                    eff_orig_airport=eff_orig_airport,
                    eff_dest_airport=eff_dest_airport,
                    orig_redirected=orig_redirected,
                    dest_redirected=dest_redirected,
                    same_region_shield=same_region_shield,
                    dist_orig_dest_km=dist_orig_dest_km,
                    flight_tickets=flight_tickets,
                    departure_date=departure_date,
                    passengers=total_pax,
                    currency=currency,
                    curr_symbol=curr_symbol,
                    links=links,
                )
            except Exception as sha_err:
                print(f"Smart hub analysis error: {sha_err}")

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
            "raw_origin": true_orig_name,
            "raw_destination": true_dest_name,
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
            "smart_hub_analysis": smart_hub_analysis,
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
            if current_mode not in ("bus", "train", "ferry"):
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
            elif orig_nearby and eff_orig.get("iata"):
                orig_city_short = (eff_orig.get("name") or "").split("(")[0].strip()
                title_tr = f"En Ucuz Uçak ({orig_city_short} {eff_orig.get('iata')})"
                title_en = f"Cheapest Flight ({orig_city_short} {eff_orig.get('iata')})"
            else:
                title_tr = "En Ucuz Uçak"
                title_en = "Cheapest Flight"

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
            fut_fl = ex.submit(_fetch_flight_badge)
            fut_tr = ex.submit(_fetch_train_badge)
            fut_bus = ex.submit(_fetch_bus_badge)
            for fut in (fut_fl, fut_tr, fut_bus):
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

        from app.cities import find_city
        dest_loc = find_city(dest_clean)
        is_intl_dest = bool(dest_loc and dest_loc.get("is_international", False))
        if is_intl_dest:
            booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
            hotel_deep_link = (
                f"https://www.booking.com/searchresults.html?"
                f"ss={urllib.parse.quote(dest_clean)}"
                f"&checkin={departure_date}&checkout={cout_str}"
                f"&group_adults={max(1, passengers)}&no_rooms=1&aid={booking_aid}"
            )
        else:
            hotel_deep_link = HotelService.resolve_trip_hotel_url(
                city_clean=dest_clean,
                city_slug=dest_lower.replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ö", "o").replace("ü", "u").replace("ğ", "g"),
                cin=departure_date,
                cout=cout_str,
                guests=max(1, passengers),
                is_international=False,
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


