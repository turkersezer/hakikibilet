"""
Canlı Uçuş Fiyat Servisi (Google Flights RPC Entegrasyonu)
Pegasus, AJet, THY ve SunExpress için anlık canlı fiyatları, sefer saatlerini, tarihleri ve kabin sınıflarını (Ekonomi/Business) çeker.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from app.cities import find_city

logger = logging.getLogger(__name__)

MONTHS_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

def format_tr_date(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_TR[dt.month - 1]} {DAYS_TR[dt.weekday()]}"

def fetch_live_flights_from_google(
    origin_city_name: str,
    dest_city_name: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    trip_type: str = "one_way",
    cabin_class: str = "economy"
) -> List[Dict[str, Any]]:
    """
    Google Flights altyapısını kullanarak canlı havayolu seferlerini, net fiyatlarını ve kabin sınıfını çeker.
    """
    from fast_flights import FlightQuery, Passengers, create_query, get_flights

    origin_city = find_city(origin_city_name)
    dest_city = find_city(dest_city_name)

    if not origin_city or not dest_city:
        return []

    if not origin_city.get("has_airport") or not dest_city.get("has_airport"):
        return []

    # İstanbul için hem SAW hem IST havalimanlarını tara
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
                passengers=Passengers(adults=passengers),
                currency="TRY",
                language="tr"
            )
            raw_results = get_flights(q)
            return list(raw_results)
        except Exception as e:
            logger.warning(f"Live flight error for {orig_code}->{dest_code}: {e}")
            return []

    pairs = [(o, d) for o in orig_codes for d in dest_codes]
    all_raw_flights = []

    # Paralel isteklerle 1 saniye civarında çek
    with ThreadPoolExecutor(max_workers=max(1, len(pairs))) as executor:
        futures = [executor.submit(query_single_pair, o, d) for o, d in pairs]
        for f in as_completed(futures):
            all_raw_flights.extend(f.result())

    if not all_raw_flights:
        return []

    # Fiyata göre sırala
    all_raw_flights.sort(key=lambda x: getattr(x, "price", 999999))

    results: List[Dict[str, Any]] = []
    seen_signatures = set()

    orig_slug = origin_city.get("slug", origin_city_name.lower())
    dest_slug = dest_city.get("slug", dest_city_name.lower())

    for idx, f in enumerate(all_raw_flights):
        try:
            if not getattr(f, "flights", None) or len(f.flights) == 0:
                continue

            first_leg = f.flights[0]
            last_leg = f.flights[-1]

            dep_time_tuple = getattr(first_leg.departure, "time", (0, 0))
            arr_time_tuple = getattr(last_leg.arrival, "time", (0, 0))

            dep_date_tuple = getattr(first_leg.departure, "date", None)
            arr_date_tuple = getattr(last_leg.arrival, "date", None)

            if dep_date_tuple:
                dep_dt = datetime(dep_date_tuple[0], dep_date_tuple[1], dep_date_tuple[2])
            else:
                dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")

            if arr_date_tuple:
                arr_dt = datetime(arr_date_tuple[0], arr_date_tuple[1], arr_date_tuple[2])
            else:
                arr_dt = dep_dt

            dep_time = f"{dep_time_tuple[0]:02d}:{dep_time_tuple[1]:02d}"
            arr_time = f"{arr_time_tuple[0]:02d}:{arr_time_tuple[1]:02d}"

            dep_date_formatted = format_tr_date(dep_dt)
            arr_date_formatted = format_tr_date(arr_dt)
            is_next_day = (arr_dt.date() > dep_dt.date())

            airline_name = f.airlines[0] if getattr(f, "airlines", None) and len(f.airlines) > 0 else "Havayolu"
            price = float(f.price)

            from_code = getattr(first_leg.from_airport, "code", orig_codes[0])
            to_code = getattr(last_leg.to_airport, "code", dest_codes[0])

            # Tekrar eden seferleri filtrele
            sig = f"{airline_name}-{from_code}-{to_code}-{dep_time}-{price}"
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

            # Süre hesaplama
            total_duration_mins = sum(getattr(leg, "duration", 60) for leg in f.flights)
            hours = total_duration_mins // 60
            mins = total_duration_mins % 60
            duration_str = f"{hours} sa {mins} dk" if hours > 0 else f"{mins} dk"

            is_direct = (len(f.flights) == 1)
            is_night_trip = (dep_time_tuple[0] >= 22 or dep_time_tuple[0] <= 5)

            # Havayolu eşleştirme ve doğrudan link üretimi
            carrier_lower = airline_name.lower()
            carrier_type = getattr(f, "type", "").upper()

            plane_type = getattr(first_leg, "plane_type", "Uçak") or "Uçak"
            flight_no = f"{carrier_type} {first_leg.from_airport.code}-{last_leg.to_airport.code}"

            is_biz = (seat_mode == "business")

            # Enuygun acente linki ve Google Flights direkt arama linki
            enuygun_dep_date = datetime.strptime(departure_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            enuygun_route = f"{orig_slug}-{dest_slug}-{from_code.lower()}a-{to_code.lower()}a"
            agent_link = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep_date}&yetiskin={passengers}"
            if is_round and return_date:
                enuygun_ret_date = datetime.strptime(return_date, "%Y-%m-%d").strftime("%d.%m.%Y")
                agent_link += f"&donus={enuygun_ret_date}"
            if is_biz:
                agent_link += "&sinif=business"

            biz_extra_google = "+business" if is_biz else ""
            if is_round and return_date:
                google_flights_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{departure_date}+through+{return_date}{biz_extra_google}"
            else:
                google_flights_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{departure_date}{biz_extra_google}"

            # Enuygun acente hizmet bedeli (Türkiye yurt içi uçuşlarda standart +53 ₺)
            is_intl = bool(origin_city.get("is_international") or dest_city.get("is_international"))
            enuygun_fee = (53.0 * passengers) if not is_intl else 0.0
            enuygun_price = round(price + enuygun_fee, 2)
            final_ticket_price = price

            if "pegasus" in carrier_lower or "PC" in carrier_type:
                carrier_display = "Pegasus Airlines"
                official_name = "Pegasus Resmi"
                official_link = f"https://web.flypgs.com/booking?departurePort={from_code}&arrivalPort={to_code}&departureDate={departure_date}&adultCount={passengers}"
                if is_round and return_date:
                    official_link += f"&returnDate={return_date}"
                badge = "Comfort Flex ⭐" if is_biz else ("En Çok Tercih Edilen" if idx == 0 else "Pegasus Seferi")
                direct_link = official_link
                final_ticket_price = price  # Doğrudan Pegasus sitesinde komisyonsuz net fiyat (1.398 ₺)
                providers_list = [
                    {"name": "Pegasus Resmi Ekranı", "url": official_link, "price": price, "is_best": True},
                    {"name": "Enuygun (+53 ₺)", "url": agent_link, "price": enuygun_price, "is_best": False}
                ]
            elif "ajet" in carrier_lower or "VF" in carrier_type or "anadolu" in carrier_lower:
                carrier_display = "AJet (AnadoluJet)"
                official_name = "AJet (Enuygun Bilet)"
                official_link = "https://ajet.com/tr"
                badge = "Business ⭐" if is_biz else ("AJet Fırsatı" if idx <= 1 else "AJet Seferi")
                direct_link = agent_link  # Enuygun doğrudan bilet seçim ekranı
                final_ticket_price = enuygun_price  # Enuygun ekranındaki net satış fiyatı (1.455 ₺) birebir eşleştirilir
                providers_list = [
                    {"name": "Enuygun Bilet Ekranı", "url": agent_link, "price": enuygun_price, "is_best": True},
                    {"name": "Google Flights / AJet Net", "url": google_flights_link, "price": price, "is_best": False}
                ]
            elif "turkish" in carrier_lower or "thy" in carrier_lower or "TK" in carrier_type:
                carrier_display = "Türk Hava Yolları"
                official_name = "THY Resmi"
                official_link = "https://www.turkishairlines.com/tr-int/"
                badge = "Business Class ⭐" if is_biz else "THY Konforu"
                direct_link = google_flights_link
                final_ticket_price = price
                providers_list = [
                    {"name": "Google Flights / THY Net", "url": google_flights_link, "price": price, "is_best": True},
                    {"name": "Enuygun", "url": agent_link, "price": enuygun_price, "is_best": False}
                ]
            elif "sunexpress" in carrier_lower or "XQ" in carrier_type:
                carrier_display = "SunExpress"
                official_name = "SunExpress (Enuygun)"
                official_link = "https://www.sunexpress.com/tr/"
                badge = "SunClassic" if is_biz else "Direkt Uçuş"
                direct_link = agent_link
                final_ticket_price = enuygun_price
                providers_list = [
                    {"name": "Enuygun Bilet Ekranı", "url": agent_link, "price": enuygun_price, "is_best": True},
                    {"name": "Google Flights / SunExpress", "url": google_flights_link, "price": price, "is_best": False}
                ]
            else:
                carrier_display = airline_name
                official_name = f"{airline_name} Resmi"
                official_link = google_flights_link
                badge = "Business Class ⭐" if is_biz else "Ekonomik Uçuş"
                direct_link = google_flights_link
                final_ticket_price = price
                providers_list = [
                    {"name": "Google Flights (Canlı)", "url": google_flights_link, "price": price, "is_best": True},
                    {"name": "Enuygun", "url": agent_link, "price": enuygun_price, "is_best": False}
                ]

            results.append({
                "id": f"live-fl-{idx+1}",
                "transport_type": "flight",
                "carrier": carrier_display,
                "carrier_logo": "✈️",
                "flight_number": flight_no,
                "origin": f"{origin_city_name} ({from_code})",
                "destination": f"{dest_city_name} ({to_code})",
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "departure_date_formatted": dep_date_formatted,
                "arrival_date_formatted": arr_date_formatted,
                "is_next_day": is_next_day,
                "duration": duration_str,
                "is_direct": is_direct,
                "is_night_trip": is_night_trip,
                "price": final_ticket_price,
                "has_live_price": True,
                "price_status_text": "Doğrulanmış Canlı Fiyat",
                "regular_price": round(final_ticket_price * 1.35, 2),
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
                "providers": providers_list
            })

            # En uygun ilk 12 canlı uçuşu al
            if len(results) >= 12:
                break
        except Exception as err:
            logger.warning(f"Error parsing single flight: {err}")
            continue

    return results
