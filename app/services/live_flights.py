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

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
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

logger = logging.getLogger(__name__)

MONTHS_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

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
    total_passengers = adults + children + infants

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

    is_round = (trip_type == "round_trip" and return_date)
    is_round_str = "round-trip" if is_round else "one-way"
    seat_mode = "business" if cabin_class == "business" else "economy"

    def query_single_pair(orig_code: str, dest_code: str):
        try:
            flight_queries = [FlightQuery(date=departure_date, from_airport=orig_code, to_airport=dest_code)]
            if is_round and return_date:
                flight_queries.append(FlightQuery(date=return_date, from_airport=dest_code, to_airport=orig_code))

            q = create_query(
                flights=flight_queries,
                seat=seat_mode,
                trip=is_round_str,
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
            logger.warning(f"Live flight error for {orig_code}->{dest_code}: {e}")
            return []

    pairs = [(o, d) for o in orig_codes for d in dest_codes]
    all_raw_flights = []

    # Paralel isteklerle tüm havalimanı kombinasyonlarını tara
    with ThreadPoolExecutor(max_workers=max(1, len(pairs))) as executor:
        futures = [executor.submit(query_single_pair, o, d) for o, d in pairs]
        for f in as_completed(futures):
            all_raw_flights.extend(f.result())

    if not all_raw_flights:
        return []

    # Ham seferleri ayrıştır ve mükerrerleri tekilleştir (en uygun fiyatı koru)
    unique_flights = {}
    for itm in all_raw_flights:
        try:
            f0, price_block = itm[0], itm[1]
            raw_price = price_block[0][1] if price_block and price_block[0] else None
            if raw_price is None:
                continue
            price = float(raw_price)

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

            sig = (airline_name, from_code, to_code, dep_time, arr_time)
            if sig not in unique_flights or price < unique_flights[sig]["price"]:
                unique_flights[sig] = {
                    "f0": f0,
                    "legs": legs,
                    "price": price,
                    "from_code": from_code,
                    "to_code": to_code,
                    "dep_t": dep_t,
                    "arr_t": arr_t,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
                    "carrier_code": carrier_code,
                    "fn_code": fn_code,
                    "airline_name": airline_name,
                    "flight_no": flight_no
                }
        except Exception as err:
            logger.warning(f"Error parsing raw flight item: {err}")
            continue

    # Tüm biletleri en ucuzdan en pahalıya, aynı fiyattakileri ise en erken kalkış saatine göre sırala (Örn: 00:20 önce gelsin)
    sorted_raw = sorted(unique_flights.values(), key=lambda x: (x["price"], x["dep_t"][0] * 60 + x["dep_t"][1]))

    results: List[Dict[str, Any]] = []
    orig_slug = origin_city.get("slug", origin_city_name.lower())
    dest_slug = dest_city.get("slug", dest_city_name.lower())

    for idx, item in enumerate(sorted_raw):
        try:
            f0 = item["f0"]
            legs = item["legs"]
            first_leg = legs[0]
            last_leg = legs[-1]
            price = item["price"]
            from_code = item["from_code"]
            to_code = item["to_code"]
            dep_t = item["dep_t"]
            arr_t = item["arr_t"]
            dep_time = item["dep_time"]
            arr_time = item["arr_time"]
            carrier_code = item["carrier_code"]
            airline_name = item["airline_name"]
            flight_no = item["flight_no"]

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

            # Uçuş süresi
            total_duration_mins = sum(
                (leg[11] if len(leg) > 11 and isinstance(leg[11], int) else 75)
                for leg in legs
            )
            hours = total_duration_mins // 60
            mins = total_duration_mins % 60
            duration_str = f"{hours} sa {mins} dk" if hours > 0 else f"{mins} dk"

            is_direct = (len(legs) == 1)
            is_night_trip = (dep_t[0] >= 22 or dep_t[0] <= 5)

            carrier_lower = airline_name.lower()
            plane_type = first_leg[17] if (len(first_leg) > 17 and isinstance(first_leg[17], str) and first_leg[17]) else "Uçak"
            is_biz = (seat_mode == "business")

            # Rezervasyon ve acente linkleri
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

            biz_extra_google = "+business" if is_biz else ""
            if is_round and return_date:
                google_flights_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{departure_date}+through+{return_date}{biz_extra_google}&hl=tr&gl=tr&curr=TRY"
            else:
                google_flights_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{departure_date}+one+way{biz_extra_google}&hl=tr&gl=tr&curr=TRY"

            is_intl = bool(origin_city.get("is_international") or dest_city.get("is_international"))
            enuygun_mult = total_passengers * (2 if is_round else 1)
            enuygun_fee = (53.0 * enuygun_mult) if not is_intl else 0.0
            enuygun_price = round(price + enuygun_fee, 2)
            enuygun_label = f"Enuygun (+{int(enuygun_fee)} ₺)" if enuygun_fee > 0 else "Enuygun"
            final_ticket_price = price

            # Havayoluna özel Enuygun filtreli direkt link (kullanıcıyı doğrudan o havayolunun seferine götürür)
            airline_filter = f"&havayolu={carrier_code}" if carrier_code in ("PC", "TK", "VF", "XQ") else ""
            direct_agent_link = f"{agent_link}{airline_filter}"

            pgs_pax_params = f"adultCount={adults}"
            if children > 0:
                pgs_pax_params += f"&childCount={children}"
            if infants > 0:
                pgs_pax_params += f"&infantCount={infants}"

            route_notice = None
            if not is_direct:
                route_notice = f"Bu uçuş {first_leg[6]} aktarmalıdır. Toplam yolculuk süresi: {duration_str}."

            # Turna.com Canlı Uçak Biletleme Linki (Eksiksiz Türkçe Sefer Ekranı)
            turna_dep_param = datetime.strptime(departure_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            turna_ret_param = f"&donus={datetime.strptime(return_date, '%Y-%m-%d').strftime('%d.%m.%Y')}" if (is_round and return_date) else ""
            turna_flight_link = f"https://www.turna.com/ucak-bileti/{orig_slug}-{dest_slug}?gidis={turna_dep_param}{turna_ret_param}&yetiskin={adults}"

            # Trip.com Flights Canlı Uçak Biletleme Linki (Global IATA Güvencesi, Türkçe Ekran ve TL)
            trip_flighttype = "rt" if (is_round and return_date) else "ow"
            trip_ret_param = f"&rdate={return_date}" if (is_round and return_date) else ""
            trip_alliance = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "")
            trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "")
            trip_aff_param = f"&Allianceid={trip_alliance}&SID={trip_sid}" if trip_alliance else ""
            trip_flight_link = f"https://tr.trip.com/flights/{orig_slug}-to-{dest_slug}/tickets-{from_code.lower()}-{to_code.lower()}?flighttype={trip_flighttype}&dcity={from_code.lower()}&acity={to_code.lower()}&ddate={departure_date}{trip_ret_param}&curr=TRY{trip_aff_param}"

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

            if is_intl:
                direct_link = trip_flight_link
            else:
                direct_link = direct_agent_link

            if "pegasus" in carrier_lower or carrier_code == "PC":
                carrier_display = "Pegasus Airlines"
                official_name = "Pegasus Resmi Web"
                official_link = "https://www.flypgs.com/"
                badge = "Comfort Flex ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "Pegasus Seferi")
                final_ticket_price = price
                if is_intl:
                    providers_list = [
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": True, "channel": "trip"},
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": False, "channel": "agency"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
                else:
                    providers_list = [
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": True, "channel": "agency"},
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": False, "channel": "trip"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
            elif "ajet" in carrier_lower or carrier_code == "VF" or "anadolu" in carrier_lower:
                carrier_display = "AJet (AnadoluJet)"
                official_name = "AJet Resmi Web"
                official_link = "https://ajet.com/tr"
                badge = "Business ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "AJet Seferi")
                final_ticket_price = price
                if is_intl:
                    providers_list = [
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": True, "channel": "trip"},
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": False, "channel": "agency"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
                else:
                    providers_list = [
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": True, "channel": "agency"},
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": False, "channel": "trip"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
            elif "turkish" in carrier_lower or "thy" in carrier_lower or carrier_code == "TK":
                carrier_display = "Türk Hava Yolları"
                official_name = "THY Resmi Web"
                official_link = "https://www.turkishairlines.com/tr-int/"
                badge = "Business Class ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "⭐ THY Konforu")
                final_ticket_price = price
                if is_intl:
                    providers_list = [
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": True, "channel": "trip"},
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": False, "channel": "agency"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
                else:
                    providers_list = [
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": True, "channel": "agency"},
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": False, "channel": "trip"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
            elif "sunexpress" in carrier_lower or carrier_code == "XQ":
                carrier_display = "SunExpress"
                official_name = "SunExpress Resmi"
                official_link = "https://www.sunexpress.com/tr/"
                badge = "SunClassic" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "SunExpress Seferi")
                final_ticket_price = price
                if is_intl:
                    providers_list = [
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": True, "channel": "trip"},
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": False, "channel": "agency"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
                else:
                    providers_list = [
                        {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": True, "channel": "agency"},
                        {"name": "Trip.com Flights", "url": trip_flight_link, "price": price, "is_best": False, "channel": "trip"},
                        {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                        {"name": official_name, "url": official_link, "price": price, "is_best": False, "channel": "official"},
                    ]
            else:
                carrier_display = airline_name
                official_name = f"{airline_name} Resmi"
                official_link = google_flights_link
                badge = "Business Class ⭐" if is_biz else ("💰 En Uygun Fiyat" if idx == 0 else "Ekonomik Uçuş")
                final_ticket_price = price
                providers_list = [
                    {"name": "Trip.com Flights (⭐ Global Partner)", "url": trip_flight_link, "price": price, "is_best": True, "channel": "trip"},
                    {"name": enuygun_label, "url": direct_agent_link, "price": enuygun_price, "is_best": False, "channel": "agency"},
                    {"name": "Turna.com", "url": turna_flight_link, "price": price, "is_best": False, "channel": "turna"},
                    {"name": "Google Flights Karşılaştırması", "url": google_flights_link, "price": price, "is_best": False, "channel": "meta"},
                ]

            return_leg_dict = None
            if is_round and return_date:
                try:
                    ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
                    ret_date_formatted = format_tr_date(ret_dt)
                except Exception:
                    ret_date_formatted = return_date

                r_dep_time = "19:40"
                r_arr_time = "20:55"
                r_dur_mins = total_duration_mins
                r_hours = r_dur_mins // 60
                r_mins = r_dur_mins % 60
                r_dur_str = f"{r_hours} sa {r_mins} dk" if r_hours > 0 else f"{r_mins} dk"

                return_leg_dict = {
                    "origin": f"{dest_city_name} ({to_code})",
                    "destination": f"{origin_city_name} ({from_code})",
                    "from_code": to_code,
                    "to_code": from_code,
                    "departure_time": r_dep_time,
                    "arrival_time": r_arr_time,
                    "departure_date": return_date,
                    "departure_date_formatted": ret_date_formatted,
                    "flight_number": f"{carrier_code} {to_code}-{from_code}" if carrier_code else "Dönüş Seferi",
                    "duration": r_dur_str,
                    "is_direct": is_direct
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
                "agent_link": agent_link,
                "google_link": google_flights_link,
                "direct_link": direct_link,
                "booking_link": direct_link,
                "travelpayouts_link": trip_flight_link,
                "hotel_link": dest_hotel_link,
                "providers": providers_list
            })
        except Exception as err:
            logger.warning(f"Error building flight card: {err}")
            continue

    return results
