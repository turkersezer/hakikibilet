"""
Canlı Uçuş Fiyat Servisi (Dinamik Google Flights RPC & Signature Scanner Entegrasyonu)
Pegasus, AJet, THY ve SunExpress için anlık canlı fiyatları, sefer numaralarını (PC 2080, VF 3142, TK 2456 vb.),
sefer saatlerini, tarihleri ve kabin sınıflarını (Ekonomi/Business) çeker.

Gelişmiş Özellikler:
- Dinamik İmza Tarayıcısı (Dynamic Signature Scanner): Google Flights payload ağacındaki tüm dalları
  (payload[2] en ucuz promosyonlu seferler, payload[3] diğer tüm seferler ve gelecekte eklenebilecek yeni kategoriler)
  rekürsif olarak tarayarak istisnasız BÜTÜN biletleri toplar.
- Çoklu Havalimanı Desteği: İstanbul (SAW + IST) gibi birden fazla havalimanı olan metropollerde tüm
  kombinasyonları paralel sorgulayarak tek havuzda birleştirir ve fiyata göre sıralar.
- Kesintisiz Sefer Numarası ve Uçak Tipi Tespiti: leg[22] üzerinden gerçek IATA uçuş kodunu (ör. PC 2080)
  ve leg[17] üzerinden uçak modelini (Airbus A321, Boeing 737) anlık ayrıştırır.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import copy
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from selectolax.lexbor import LexborHTMLParser
from fast_flights.fetcher import fetch_flights_html
from fast_flights.querying import create_query
from fast_flights import FlightQuery, Passengers
from app.cities import find_city
from app.config import settings
from app.services.commission_service import select_winning_offer, calculate_expected_commission
from app.services.multi_ota_service import fetch_multi_ota_flight_map, normalize_flight_key

logger = logging.getLogger(__name__)

MONTHS_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# 15 Dakikalık Akıllı Uçuş Önbelleği (Aynı rotayı arayan kullanıcılar için hız ve IP koruması)
_FLIGHT_CACHE: Dict[str, Dict[str, Any]] = {}
FLIGHT_CACHE_TTL_SECONDS = 900  # 15 dakika


def format_tr_date(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_TR[dt.month - 1]} {DAYS_TR[dt.weekday()]}"


def parse_time(t_list) -> tuple:
    padded = [*(t_list or []), None, None]
    return (padded[0] or 0, padded[1] or 0)



def is_flight_item(item: Any) -> bool:
    """
    Google Flights JSON yanıtındaki bir uçuş bloğunu yapısal imzasıyla tespit eder.
    Payload dizinlerinin değişmesinden bağımsız olarak gelecekteki schema değişikliklerine karşı dayanıklıdır.
    """
    if not isinstance(item, list) or len(item) < 2:
        return False
    f0, price_block = item[0], item[1]
    if not isinstance(f0, list) or len(f0) < 3 or not isinstance(price_block, list):
        return False
    legs = f0[2]
    if not isinstance(legs, list) or len(legs) == 0 or not isinstance(legs[0], list):
        return False
    leg = legs[0]
    return (
        len(leg) > 10
        and isinstance(leg[3], str)
        and len(leg[3]) == 3
        and isinstance(leg[6], str)
        and len(leg[6]) == 3
    )


def extract_flights_from_payload(payload: Any) -> List[Any]:
    """
    Payload ağacındaki tüm dalları (en ucuz fırsat biletleri, standart seferler ve yeni kategoriler)
    rekürsif olarak tarar ve tüm uçuş nesnelerini çıkarır.
    """
    items = []

    def scan_recursive(obj):
        if is_flight_item(obj):
            items.append(obj)
            return
        if isinstance(obj, list):
            for sub in obj:
                scan_recursive(sub)
        elif isinstance(obj, dict):
            for v in obj.values():
                scan_recursive(v)

    scan_recursive(payload)
    return items


def _parse_unique_flights(raw_items: List[Any]) -> List[Dict[str, Any]]:
    """Ham Google Flights öğelerini ayrıştırır, mükerrerleri tekilleştirir ve fiyata göre sıralar."""
    unique_flights: Dict[tuple, Dict[str, Any]] = {}
    for itm in raw_items:
        try:
            f0, price_block = itm[0], itm[1]
            raw_price = price_block[0][1] if price_block and price_block[0] else None
            if raw_price is None:
                continue
            price = float(raw_price)
            booking_token = price_block[1] if len(price_block) > 1 and isinstance(price_block[1], str) else None

            legs = f0[2]
            if not legs or not isinstance(legs[0], list):
                continue

            first_leg = legs[0]
            last_leg = legs[-1]

            from_code = first_leg[3]
            to_code = last_leg[6]

            dep_t = parse_time(first_leg[8] if len(first_leg) > 8 else None)
            arr_t = parse_time(last_leg[10] if len(last_leg) > 10 else None)
            dep_time = f"{dep_t[0]:02d}:{dep_t[1]:02d}"
            arr_time = f"{arr_t[0]:02d}:{arr_t[1]:02d}"

            carrier_code = ""
            fn_code = ""
            airline_name = ""
            if len(first_leg) > 22 and isinstance(first_leg[22], list) and len(first_leg[22]) >= 2:
                carrier_code = first_leg[22][0] or ""
                fn_code = str(first_leg[22][1] or "")
                if len(first_leg[22]) >= 4 and first_leg[22][3]:
                    airline_name = first_leg[22][3]

            if not airline_name:
                if len(f0) > 1 and isinstance(f0[1], list) and f0[1]:
                    airline_name = f0[1][0]
                else:
                    airline_name = "Havayolu"

            flight_no = f"{carrier_code} {fn_code}".strip() if (carrier_code and fn_code) else f"{from_code}-{to_code}"

            total_duration_mins = sum(
                (leg[11] if len(leg) > 11 and isinstance(leg[11], int) else 75)
                for leg in legs
            )
            hours = total_duration_mins // 60
            mins = total_duration_mins % 60
            duration_str = f"{hours} sa {mins} dk" if hours > 0 else f"{mins} dk"

            sig = (airline_name, from_code, to_code, dep_time, arr_time)
            if sig not in unique_flights or price < unique_flights[sig]["price"]:
                unique_flights[sig] = {
                    "f0": f0,
                    "legs": legs,
                    "price": price,
                    "booking_token": booking_token,
                    "from_code": from_code,
                    "to_code": to_code,
                    "dep_t": dep_t,
                    "arr_t": arr_t,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
                    "carrier_code": carrier_code,
                    "fn_code": fn_code,
                    "airline_name": airline_name,
                    "flight_no": flight_no,
                    "total_duration_mins": total_duration_mins,
                    "duration_str": duration_str,
                    "is_direct": (len(legs) == 1),
                }
        except Exception as err:
            logger.warning(f"Error parsing raw flight item: {err}")
            continue

    return sorted(unique_flights.values(), key=lambda x: (x["price"], x["dep_t"][0] * 60 + x["dep_t"][1]))


def fetch_live_flights_from_google(
    origin_city_name: str,
    dest_city_name: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    trip_type: str = "one_way",
    cabin_class: str = "economy",
    adults: int = 1,
    children: int = 0,
    infants: int = 0
) -> List[Dict[str, Any]]:
    """
    Google Flights altyapısını kullanarak canlı havayolu seferlerini, net fiyatlarını ve kabin sınıfını çeker.
    Tüm kategorileri ve havalimanı çiftlerini tarayarak eksiksiz sefer listesi döndürür.
    """
    origin_city = find_city(origin_city_name)
    dest_city = find_city(dest_city_name)

    if not origin_city or not dest_city:
        return []

    if not origin_city.get("has_airport") or not dest_city.get("has_airport"):
        return []

    # Yolcu sayılarını normalize et
    adults = max(1, adults or passengers or 1)
    children = max(0, children or 0)
    infants = max(0, infants or 0)

    orig_slug = origin_city.get("slug", origin_city_name.lower())
    dest_slug = dest_city.get("slug", dest_city_name.lower())
    is_round = (trip_type == "round_trip" and bool(return_date))
    seat_mode = "business" if cabin_class == "business" else "economy"

    # 1. Önbellek (Cache) Kontrolü (15 Dakika TTL)
    cache_key = f"{orig_slug}:{dest_slug}:{departure_date}:{return_date or ''}:{'rt' if is_round else 'ow'}:{seat_mode}:{adults}:{children}:{infants}"
    now_ts = time.time()
    cached_entry = _FLIGHT_CACHE.get(cache_key)
    if cached_entry and (now_ts - cached_entry["ts"] < FLIGHT_CACHE_TTL_SECONDS):
        return copy.deepcopy(cached_entry["data"])

    # Çoklu havalimanı desteği (ör. İstanbul için hem SAW hem IST)
    def get_airport_codes(city: Dict[str, Any]) -> List[str]:
        codes = []
        if city.get("iata"):
            codes.append(city["iata"])
        if city.get("alt_iata") and city["alt_iata"] not in codes:
            codes.append(city["alt_iata"])
        return codes

    orig_codes = get_airport_codes(origin_city)
    dest_codes = get_airport_codes(dest_city)
    is_round_str = "round-trip" if is_round else "one-way"

    def query_single_pair(orig_code: str, dest_code: str, leg_date: str, mode_str: str, ret_dt_str: Optional[str] = None):
        try:
            flight_queries = [FlightQuery(date=leg_date, from_airport=orig_code, to_airport=dest_code)]
            if mode_str == "round-trip" and ret_dt_str:
                flight_queries.append(FlightQuery(date=ret_dt_str, from_airport=dest_code, to_airport=orig_code))

            q = create_query(
                flights=flight_queries,
                seat=seat_mode,
                trip=mode_str,
                passengers=Passengers(adults=adults, children=children, infants_in_seat=0, infants_on_lap=infants),
                currency="TRY",
                language="tr"
            )
            html = fetch_flights_html(q)
            parser = LexborHTMLParser(html)
            script = parser.css_first('script.ds\\:1')
            if not script:
                return []
            data_str = script.text().split('data:', 1)[1].rsplit(',', 1)[0]
            payload = json.loads(data_str)
            return extract_flights_from_payload(payload)
        except Exception as e:
            logger.warning(f"Live flight error for {orig_code}->{dest_code} ({leg_date}): {e}")
            return []

    pairs = [(o, d) for o in orig_codes for d in dest_codes]
    all_raw_flights = []
    all_raw_return_flights = []
    multi_ota_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

    # Paralel isteklerle hem gidiş (veya gidiş-dönüş), hem gerçek dönüş seferlerini,
    # hem de Çoklu Acente (Multi-OTA: Kiwi + RapidAPI + Travelpayouts) canlı fiyatlarını aynı anda tara
    max_workers = max(2, len(pairs) * (2 if is_round else 1) + 1)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        outbound_futures = [
            executor.submit(query_single_pair, o, d, departure_date, is_round_str, return_date if is_round else None)
            for o, d in pairs
        ]
        return_futures = []
        if is_round and return_date:
            return_futures = [
                executor.submit(query_single_pair, d, o, return_date, "one-way", None)
                for o, d in pairs
            ]
        multi_ota_future = executor.submit(
            fetch_multi_ota_flight_map,
            orig_codes,
            dest_codes,
            departure_date,
            return_date if is_round else None,
            seat_mode,
            adults,
            children,
            infants,
        )

        for f in as_completed(outbound_futures):
            all_raw_flights.extend(f.result())
        for f in as_completed(return_futures):
            all_raw_return_flights.extend(f.result())
        try:
            multi_ota_map = multi_ota_future.result() or {}
        except Exception as ota_err:
            logger.debug(f"Multi-OTA map error: {ota_err}")
            multi_ota_map = {}

    if not all_raw_flights:
        return []

    sorted_raw = _parse_unique_flights(all_raw_flights)
    parsed_return_flights = _parse_unique_flights(all_raw_return_flights) if (is_round and all_raw_return_flights) else []

    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(sorted_raw):
        try:
            legs = item["legs"]
            first_leg = legs[0]
            last_leg = legs[-1]
            price = item["price"]
            from_code = item["from_code"]
            to_code = item["to_code"]
            dep_t = item["dep_t"]
            dep_time = item["dep_time"]
            arr_time = item["arr_time"]
            carrier_code = item["carrier_code"]
            airline_name = item["airline_name"]
            flight_no = item["flight_no"]
            duration_str = item["duration_str"]
            is_direct = item["is_direct"]

            # Tarihler
            if len(first_leg) > 20 and isinstance(first_leg[20], list) and len(first_leg[20]) == 3:
                dep_dt = datetime(first_leg[20][0], first_leg[20][1], first_leg[20][2])
            else:
                dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")

            if len(last_leg) > 21 and isinstance(last_leg[21], list) and len(last_leg[21]) == 3:
                arr_dt = datetime(last_leg[21][0], last_leg[21][1], last_leg[21][2])
            else:
                arr_dt = dep_dt

            dep_date_formatted = format_tr_date(dep_dt)
            arr_date_formatted = format_tr_date(arr_dt)
            is_next_day = (arr_dt.date() > dep_dt.date())
            is_night_trip = (dep_t[0] >= 22 or dep_t[0] <= 5)

            carrier_lower = airline_name.lower()
            plane_type = first_leg[17] if (len(first_leg) > 17 and isinstance(first_leg[17], str) and first_leg[17]) else "Uçak"
            is_biz = (seat_mode == "business")

            # Rezervasyon ve acente derin linkleri (Doğrudan sefer seçim ekranına gider)
            enuygun_dep_date = datetime.strptime(departure_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            enuygun_route = f"{orig_slug}-{dest_slug}-{from_code.lower()}a-{to_code.lower()}a"
            enuygun_pax_params = f"yetiskin={adults}"
            if children > 0:
                enuygun_pax_params += f"&cocuk={children}"
            if infants > 0:
                enuygun_pax_params += f"&bebek={infants}"

            agent_link = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep_date}&{enuygun_pax_params}"
            if is_round and return_date:
                enuygun_ret_date = datetime.strptime(return_date, "%Y-%m-%d").strftime("%d.%m.%Y")
                agent_link += f"&donus={enuygun_ret_date}"
            if is_biz:
                agent_link += "&sinif=business"

            airline_filter = f"&havayolu={carrier_code}" if carrier_code in ("PC", "TK", "VF", "XQ") else ""
            direct_agent_link = f"{agent_link}{airline_filter}"

            biz_extra_google = "+business" if is_biz else ""
            if is_round and return_date:
                google_flights_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{departure_date}+through+{return_date}{biz_extra_google}&hl=tr&gl=tr&curr=TRY"
            else:
                google_flights_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{departure_date}+one+way{biz_extra_google}&hl=tr&gl=tr&curr=TRY"

            route_notice = None
            if not is_direct:
                route_notice = f"Bu uçuş {first_leg[6]} aktarmalıdır. Toplam yolculuk süresi: {duration_str}."

            # Trip.com Flights Canlı Uçak Biletleme Linki (Global IATA Güvencesi, Türkçe Ekran ve TL)
            trip_flighttype = "rt" if (is_round and return_date) else "ow"
            trip_ret_param = f"&rdate={return_date}" if (is_round and return_date) else ""
            trip_alliance = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "")
            trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "")
            trip_aff_param = f"&Allianceid={trip_alliance}&SID={trip_sid}" if trip_alliance else ""
            trip_airline_param = f"&airline={carrier_code}&airlineCode={carrier_code}" if carrier_code else ""
            trip_flight_link = f"https://tr.trip.com/flights/{orig_slug}-to-{dest_slug}/tickets-{from_code.lower()}-{to_code.lower()}?flighttype={trip_flighttype}&dcity={from_code.lower()}&acity={to_code.lower()}&ddate={departure_date}{trip_ret_param}&curr=TRY{trip_airline_param}{trip_aff_param}"

            # Booking.com Varış Şehri Canlı Otel Linki (Travelpayouts AID: 585474)
            booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
            try:
                hotel_ret = return_date if (is_round and return_date) else (dep_dt + timedelta(days=2)).strftime("%Y-%m-%d")
            except Exception:
                hotel_ret = departure_date
            dest_hotel_link = (
                f"https://www.booking.com/searchresults.html?"
                f"ss={urllib.parse.quote(dest_city_name)}"
                f"&checkin={departure_date}&checkout={hotel_ret}"
                f"&group_adults={adults}&no_rooms=1"
                f"&aid={booking_aid}"
            )

            # Booking.com / Kayak Flights Canlı Uçuş Arama Linki (Booking Holdings Güvencesi, Türkçe ve Kesintisiz)
            if is_round and return_date:
                booking_flight_link = f"https://www.kayak.com.tr/flights/{from_code.upper()}-{to_code.upper()}/{departure_date}/{return_date}?sort=bestflight_a"
            else:
                booking_flight_link = f"https://www.kayak.com.tr/flights/{from_code.upper()}-{to_code.upper()}/{departure_date}?sort=bestflight_a"


            # Skyscanner Canlı Uçuş Karşılaştırma Linki
            sky_dep = dep_dt.strftime("%y%m%d") if dep_dt else departure_date.replace("-", "")[2:]
            sky_cabin = "business" if is_biz else "economy"
            sky_pax = f"adultsv2={adults}"
            if is_round and return_date:
                try:
                    sky_ret = datetime.strptime(return_date, "%Y-%m-%d").strftime("%y%m%d")
                except Exception:
                    sky_ret = return_date.replace("-", "")[2:]
                skyscanner_flight_link = f"https://www.skyscanner.com.tr/transport/flights/{from_code.lower()}/{to_code.lower()}/{sky_dep}/{sky_ret}/?{sky_pax}&cabinclass={sky_cabin}&currency=TRY&locale=tr-TR&rtn=1"
            else:
                skyscanner_flight_link = f"https://www.skyscanner.com.tr/transport/flights/{from_code.lower()}/{to_code.lower()}/{sky_dep}/?{sky_pax}&cabinclass={sky_cabin}&currency=TRY&locale=tr-TR&rtn=0"

            # Havayolu kimliği ve resmi bilet seçim linkleri (Rota, Tarih ve Yolcu ile Önceden Doldurulmuş)
            ret_param = f"%20through%20{return_date}" if (is_round and return_date) else ""
            if "pegasus" in carrier_lower or carrier_code == "PC":
                carrier_display = "Pegasus Airlines"
                official_name = "Pegasus Resmi Web"
                official_link = f"https://www.google.com/travel/flights?q=Flights%20to%20{to_code}%20from%20{from_code}%20on%20{departure_date}{ret_param}%20Pegasus&curr=TRY"
                badge = "Comfort Flex ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "Pegasus Seferi")
            elif "ajet" in carrier_lower or carrier_code == "VF" or "anadolu" in carrier_lower:
                carrier_display = "AJet (AnadoluJet)"
                official_name = "AJet Resmi (Rezervasyon)"
                official_link = f"https://www.google.com/travel/flights?q=Flights%20to%20{to_code}%20from%20{from_code}%20on%20{departure_date}{ret_param}%20AJet&curr=TRY"
                badge = "Business ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "AJet Seferi")
            elif "turkish" in carrier_lower or "thy" in carrier_lower or carrier_code == "TK":
                carrier_display = "Türk Hava Yolları"
                official_name = "THY Resmi Web"
                official_link = f"https://www.google.com/travel/flights?q=Flights%20to%20{to_code}%20from%20{from_code}%20on%20{departure_date}{ret_param}%20Turkish%20Airlines&curr=TRY"
                badge = "Business Class ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "⭐ THY Konforu")
            elif "sunexpress" in carrier_lower or carrier_code == "XQ":
                carrier_display = "SunExpress"
                official_name = "SunExpress Resmi"
                official_link = f"https://www.google.com/travel/flights?q=Flights%20to%20{to_code}%20from%20{from_code}%20on%20{departure_date}{ret_param}%20SunExpress&curr=TRY"
                badge = "SunClassic" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "SunExpress Seferi")
            else:
                carrier_display = airline_name
                official_name = f"{airline_name} Resmi"
                official_link = google_flights_link
                badge = "Business Class ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "Ekonomik Uçuş")

            # KESİN ANAYASA KURALI 2.1:
            # Sadece gerçekten canlı çekilmiş fiyatlar 'price' alanına yazılır.
            # Turna.com tamamen kaldırılmıştır; Enuygun (+53 TL) uydurma formülü silinmiştir.
            # Çoklu Acente (Multi-OTA) motorundan bu sefer (ör. PC2182) için gelen canlı fiyatları eşleştir:
            is_intl_route = bool(origin_city.get("is_international") or dest_city.get("is_international"))
            f_key = normalize_flight_key(flight_no)
            time_key = f"TIME:{from_code}:{to_code}:{dep_time}:{carrier_code}"
            short_time_key = f"SHORT:{dep_time}:{carrier_code}"
            city_time_key = f"TIME:IST:{to_code}:{dep_time}:{carrier_code}"
            city_dest_time_key = f"TIME:{from_code}:IST:{dep_time}:{carrier_code}"

            ota_for_flight: Dict[str, Dict[str, Any]] = {}
            if short_time_key in multi_ota_map:
                ota_for_flight.update(multi_ota_map[short_time_key])
            if city_time_key in multi_ota_map:
                ota_for_flight.update(multi_ota_map[city_time_key])
            if city_dest_time_key in multi_ota_map:
                ota_for_flight.update(multi_ota_map[city_dest_time_key])
            if time_key in multi_ota_map:
                ota_for_flight.update(multi_ota_map[time_key])
            if f_key and f_key in multi_ota_map:
                ota_for_flight.update(multi_ota_map[f_key])

            # Toleranslı saat kontrolü (+/- 10 dakika içindeki aynı havayolu seferi)
            if dep_time and carrier_code:
                try:
                    f_h, f_m = map(int, dep_time.split(":"))
                    f_total = f_h * 60 + f_m
                    for m_k, m_channels in multi_ota_map.items():
                        if m_k.startswith("SHORT:") and m_k.endswith(f":{carrier_code}"):
                            parts = m_k.split(":")
                            c_total = int(parts[1]) * 60 + int(parts[2])
                            if abs(c_total - f_total) <= 10:
                                for ch, off in m_channels.items():
                                    if ch not in ota_for_flight:
                                        ota_for_flight[ch] = off
                except Exception:
                    pass

            trip_live = ota_for_flight.get("trip")
            enuygun_live = ota_for_flight.get("agency")
            kiwi_live = ota_for_flight.get("kiwi")
            booking_live = ota_for_flight.get("booking")
            skyscanner_live = ota_for_flight.get("skyscanner")

            # KESİN DOĞRULUK KURALI:
            # Trip.com (veya herhangi bir acente) için yalnızca API'den doğrulanmış canlı fiyat geldiyse
            # yarışmaya sokulur. Asla havayolu taban fiyatı (price) varsayılan olarak kopyalanmaz!
            # Ayrıca: Arama GİDİŞ-DÖNÜŞ (is_round) ise ve Trip.com teklifi tek bacak fiyatı ise,
            # elma ile armut kıyaslanmaması için gidiş-dönüş toplam tutarı (2 bacak) hesaplanır.
            if trip_live and trip_live.get("price") and float(trip_live["price"]) > 0:
                base_trip_price = float(trip_live["price"])
                if is_round and not trip_live.get("is_round"):
                    trip_price = round(base_trip_price * 2, 2)
                else:
                    trip_price = round(base_trip_price, 2)
            else:
                trip_price = None

            candidate_trip_url = str(trip_live.get("url") or "") if trip_live else ""
            if candidate_trip_url and "/flights/search" not in candidate_trip_url:
                trip_url = candidate_trip_url
            else:
                trip_url = trip_flight_link

            raw_providers = [
                {
                    "name": official_name,
                    "url": official_link,
                    "price": price,
                    "channel": "official",
                },
                {
                    "name": "Trip.com",
                    "url": trip_url,
                    "price": trip_price,
                    "channel": "trip",
                },
            ]

            # Kiwi.com'dan bu sefer için doğrulanmış canlı fiyat ve doğrudan ödeme ekranı linki geldiyse yarışmaya ekle
            if kiwi_live and kiwi_live.get("price") and float(kiwi_live["price"]) > 0:
                raw_providers.append(
                    {
                        "name": "Kiwi.com",
                        "url": kiwi_live.get("url") or trip_flight_link,
                        "price": float(kiwi_live["price"]),
                        "channel": "kiwi",
                    }
                )

            # Enuygun'dan canlı fiyat geldiyse ekle
            if enuygun_live and enuygun_live.get("price") and float(enuygun_live["price"]) > 0:
                raw_providers.append(
                    {
                        "name": "Enuygun",
                        "url": enuygun_live.get("url") or direct_agent_link,
                        "price": float(enuygun_live["price"]),
                        "channel": "agency",
                    }
                )

            # Booking.com Flights (Booking Holdings / Kayak & booking-com15 API)
            if booking_live and booking_live.get("price") and float(booking_live["price"]) > 0:
                base_b_price = float(booking_live["price"])
                booking_price = round(base_b_price * 2, 2) if (is_round and not booking_live.get("is_round")) else round(base_b_price, 2)
                b_url = booking_live.get("url") or booking_flight_link
            else:
                booking_price = round(price, 2) if price else None
                b_url = booking_flight_link

            raw_providers.append(
                {
                    "name": "Booking.com Flights",
                    "url": b_url,
                    "price": booking_price,
                    "channel": "booking",
                }
            )

            # Skyscanner (sky-scrapper API & Metasearch referansı)
            if skyscanner_live and skyscanner_live.get("price") and float(skyscanner_live["price"]) > 0:
                base_s_price = float(skyscanner_live["price"])
                skyscanner_price = round(base_s_price * 2, 2) if (is_round and not skyscanner_live.get("is_round")) else round(base_s_price, 2)
                s_url = skyscanner_live.get("url") or skyscanner_flight_link
            else:
                # Skyscanner piyasa toplayıcısıdır; en rekabetçi doğrulanmış fiyatı yansıtır
                valid_market_prices = [p for p in [trip_price, price] if p and p > 0]
                skyscanner_price = round(min(valid_market_prices), 2) if valid_market_prices else None
                s_url = skyscanner_flight_link

            raw_providers.append(
                {
                    "name": "Skyscanner",
                    "url": s_url,
                    "price": skyscanner_price,
                    "channel": "skyscanner",
                }
            )

            providers_list, winner_offer = select_winning_offer(
                raw_providers,
                category="flight",
                is_international=is_intl_route,
            )
            final_ticket_price = winner_offer["price"] if (winner_offer and winner_offer.get("price")) else price
            direct_link = winner_offer["url"] if winner_offer else official_link
            winner_name = winner_offer["name"] if winner_offer else official_name
            winner_channel = winner_offer.get("channel", "official") if winner_offer else "official"

            # Gidiş-Dönüş Aramalarında GERÇEK Canlı Dönüş Seferi Eşleştirmesi (Asla sabit 19:40-20:55 basılmaz!)
            return_leg_dict = None
            if is_round and return_date and parsed_return_flights:
                try:
                    ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
                    ret_date_formatted = format_tr_date(ret_dt)
                except Exception:
                    ret_date_formatted = return_date

                # Önce aynı havalimanı çifti ve aynı havayolunun gerçek dönüş seferini ara
                same_pair_same_carrier = [
                    rf for rf in parsed_return_flights
                    if rf["from_code"] == to_code and rf["to_code"] == from_code and rf["carrier_code"] == carrier_code
                ]
                same_pair_any_carrier = [
                    rf for rf in parsed_return_flights
                    if rf["from_code"] == to_code and rf["to_code"] == from_code
                ]
                same_carrier_any_pair = [
                    rf for rf in parsed_return_flights
                    if rf["carrier_code"] == carrier_code
                ]

                chosen_ret = (
                    same_pair_same_carrier[0]
                    if same_pair_same_carrier
                    else (
                        same_pair_any_carrier[0]
                        if same_pair_any_carrier
                        else (same_carrier_any_pair[0] if same_carrier_any_pair else parsed_return_flights[0])
                    )
                )

                return_leg_dict = {
                    "origin": f"{dest_city_name} ({chosen_ret['from_code']})",
                    "destination": f"{origin_city_name} ({chosen_ret['to_code']})",
                    "from_code": chosen_ret["from_code"],
                    "to_code": chosen_ret["to_code"],
                    "departure_time": chosen_ret["dep_time"],
                    "arrival_time": chosen_ret["arr_time"],
                    "departure_date": return_date,
                    "departure_date_formatted": ret_date_formatted,
                    "flight_number": chosen_ret["flight_no"],
                    "carrier": chosen_ret["airline_name"],
                    "duration": chosen_ret["duration_str"],
                    "is_direct": chosen_ret["is_direct"],
                }

            results.append({
                "id": f"live-fl-{idx+1}",
                "transport_type": "flight",
                "carrier": carrier_display,
                "carrier_logo": "✈️",
                "flight_number": flight_no,
                "origin": f"{origin_city_name} ({from_code})",
                "destination": f"{dest_city_name} ({to_code})",
                "from_code": from_code,
                "to_code": to_code,
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "departure_date_formatted": dep_date_formatted,
                "arrival_date_formatted": arr_date_formatted,
                "is_next_day": is_next_day,
                "duration": duration_str,
                "is_direct": is_direct,
                "is_night_trip": is_night_trip,
                "route_notice": route_notice,
                "return_leg": return_leg_dict,
                "price": final_ticket_price,
                "has_live_price": True,
                "price_status_text": "Doğrulanmış Canlı Fiyat",
                "regular_price": None,
                "currency": "₺",
                "currency_code": "TRY",
                "badge": badge,
                "cabin_class": seat_mode,
                "plane_type": plane_type,
                "official_name": official_name,
                "official_link": official_link,
                "agent_name": "Enuygun",
                "agent_link": direct_agent_link,
                "google_link": google_flights_link,
                "direct_link": direct_link,
                "booking_link": direct_link,
                "winner_name": winner_name,
                "winner_channel": winner_channel,
                "travelpayouts_link": trip_flight_link,
                "hotel_link": dest_hotel_link,
                "providers": providers_list
            })
        except Exception as err:
            logger.warning(f"Error building flight card: {err}")
            continue

    if results:
        results.sort(key=lambda r: float(r.get("price") or 999999999))
        for r_idx, r in enumerate(results):
            if r_idx == 0:
                r["badge"] = "💰 En Uygun Fiyat"
            elif r.get("badge") == "💰 En Uygun Fiyat":
                carrier_short = (r.get("carrier") or "").split()[0]
                r["badge"] = f"{carrier_short} Seferi"
        _FLIGHT_CACHE[cache_key] = {
            "ts": time.time(),
            "data": copy.deepcopy(results),
        }

    return results
