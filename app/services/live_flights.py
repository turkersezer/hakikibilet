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
import os
import re
import time
import copy
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from selectolax.lexbor import LexborHTMLParser
from fast_flights.fetcher import fetch_flights_html
from fast_flights.querying import create_query
from fast_flights import FlightQuery, Passengers
from app.cities import find_city, resolve_nearest_airport_city
from app.config import settings
from app.services.commission_service import select_winning_offer, calculate_expected_commission
from app.services.multi_ota_service import fetch_multi_ota_flight_map, normalize_flight_key
from app.services.provider_registry import resolve_carrier_meta, decide_winning_flight_offer

logger = logging.getLogger(__name__)

MONTHS_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# 10 Dakikalık Akıllı Uçuş Önbelleği (Canlı fiyat güncelliği ve hız dengesi)
_FLIGHT_CACHE: Dict[str, Dict[str, Any]] = {}
_FLIGHT_CACHE_LOCK = threading.Lock()
FLIGHT_CACHE_TTL_SECONDS = 600  # 10 dakika
FLIGHT_DISK_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "flight_results_cache")
os.makedirs(FLIGHT_DISK_CACHE_DIR, exist_ok=True)


def _get_flight_disk_cache_path(cache_key: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", cache_key)
    return os.path.join(FLIGHT_DISK_CACHE_DIR, f"{safe_name}.json")



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

            from app.services.multi_ota_service import TR_AIRPORT_CODES
            is_dom_leg_search = (str(from_code).upper() in TR_AIRPORT_CODES and str(to_code).upper() in TR_AIRPORT_CODES)
            if is_dom_leg_search:
                if len(legs) > 2:
                    continue
                invalid_via = False
                for lg in legs:
                    lg_orig = str(lg[3] or "").upper() if len(lg) > 3 else ""
                    lg_dest = str(lg[6] or "").upper() if len(lg) > 6 else ""
                    if (lg_orig and lg_orig not in TR_AIRPORT_CODES) or (lg_dest and lg_dest not in TR_AIRPORT_CODES):
                        invalid_via = True
                        break
                if invalid_via:
                    continue

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
            if len(legs) > 1:
                leg_codes = []
                for lg in legs:
                    if len(lg) > 22 and isinstance(lg[22], list) and len(lg[22]) >= 2:
                        lc = str(lg[22][0] or "").strip()
                        ln = str(lg[22][1] or "").strip()
                        if lc and ln:
                            leg_codes.append(f"{lc} {ln}")
                if len(leg_codes) > 1:
                    flight_no = " + ".join(leg_codes)

            sum_leg_mins = sum(
                (leg[11] if len(leg) > 11 and isinstance(leg[11], int) else 75)
                for leg in legs
            )
            total_duration_mins = sum_leg_mins
            if len(legs) > 1:
                try:
                    if (
                        len(first_leg) > 20 and isinstance(first_leg[20], list) and len(first_leg[20]) == 3
                        and len(last_leg) > 21 and isinstance(last_leg[21], list) and len(last_leg[21]) == 3
                    ):
                        d1 = datetime(first_leg[20][0], first_leg[20][1], first_leg[20][2], dep_t[0], dep_t[1])
                        d2 = datetime(last_leg[21][0], last_leg[21][1], last_leg[21][2], arr_t[0], arr_t[1])
                        elapsed_m = int((d2 - d1).total_seconds() // 60)
                        if elapsed_m >= sum_leg_mins:
                            total_duration_mins = elapsed_m
                except Exception:
                    pass
            if is_dom_leg_search and total_duration_mins > 990:
                continue
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

    # Kur / Önbellek Gecikmesi (1-5 TL FX Lag) Senkronizasyonu:
    # Aynı havayolu ve parkurda (örn. SAW->ESB Pegasus) 5 sefer 1.401 TL iken tek bir seferde
    # Google önbellek kur farkından dolayı 1.399 TL (1-5 TL fark) görünmesi durumunda,
    # listedeki gerçek taban fiyatla (1.401 TL) %100 birebir uyum için taban dilimi senkronize et.
    from collections import Counter
    by_carrier_route: Dict[tuple, List[Dict[str, Any]]] = {}
    for fl in unique_flights.values():
        cr_key = (fl.get("carrier_code") or fl.get("airline_name"), fl.get("from_code"), fl.get("to_code"))
        by_carrier_route.setdefault(cr_key, []).append(fl)

    for cr_key, fl_list in by_carrier_route.items():
        if len(fl_list) < 2:
            continue
        prices_int = [int(round(f["price"])) for f in fl_list if f.get("price")]
        if not prices_int:
            continue
        min_p = min(prices_int)
        counts = Counter(prices_int)
        # min_p'den 1 ile 5 TL arasında daha yüksek ve birden fazla seferde tekrar eden ana tarife dilimi varsa:
        higher_buckets = [p for p, cnt in counts.items() if 0 < (p - min_p) <= 5 and cnt >= counts[min_p]]
        if higher_buckets:
            target_bucket = float(min(higher_buckets))
            for f in fl_list:
                if int(round(f["price"])) == min_p:
                    f["price"] = target_bucket

    return sorted(unique_flights.values(), key=lambda x: (x["price"], x["dep_t"][0] * 60 + x["dep_t"][1]))


def _build_fallback_sorted_raw_from_ota(
    multi_ota_map: Dict[str, Dict[str, Dict[str, Any]]],
    departure_date: str,
) -> List[Dict[str, Any]]:
    """
    Bulut veri merkezi (Render vb.) IP'lerinde Google Flights'ın yanıt vermediği veya
    kısıtlama uyguladığı anlarda, paralel çalışan Multi-OTA (Kiwi GraphQL) motorundan
    gelen gerçek canlı seferleri aynı yapısal şemaya dönüştürür.
    """
    if not multi_ota_map:
        return []

    unique_fallback: Dict[tuple, Dict[str, Any]] = {}
    try:
        base_dt = datetime.strptime(departure_date, "%Y-%m-%d")
    except Exception:
        base_dt = datetime.now()

    for key, channels in multi_ota_map.items():
        if not key or key.startswith("TIME:") or key.startswith("SHORT:") or key.startswith("CONN:") or not isinstance(channels, dict):
            continue
        # Tüm aktif kanallardan (Skyscanner, Booking, Trip, Kiwi) en zengin meta veriyi ve en düşük doğrulanmış fiyatı seç
        cand_offs = [
            channels.get(ch)
            for ch in ("skyscanner", "booking", "trip", "kiwi")
            if isinstance(channels.get(ch), dict) and float(channels[ch].get("price") or 0) > 0
        ]
        if not cand_offs:
            continue
        meta_off = next((o for o in cand_offs if o.get("from_code") and o.get("dep_time")), cand_offs[0])
        min_ota_price = min(float(o["price"]) for o in cand_offs)
        non_kiwi_prices = [float(o["price"]) for o in cand_offs if o.get("channel") != "kiwi"]
        official_base_price = min(non_kiwi_prices) if non_kiwi_prices else None

        price = min_ota_price
        from_code = str(meta_off.get("from_code") or "").strip().upper()
        to_code = str(meta_off.get("to_code") or "").strip().upper()
        dep_time = str(meta_off.get("dep_time") or "").strip()
        arr_time = str(meta_off.get("arr_time") or dep_time).strip()
        carrier_code = str(meta_off.get("carrier_code") or "").strip().upper()
        fn_code = str(meta_off.get("fn_code") or "").strip()
        airline_name = str(meta_off.get("carrier_name") or carrier_code or "Havayolu").strip()
        flight_no = str(meta_off.get("flight_no") or f"{carrier_code} {fn_code}").strip()
        is_direct = bool(meta_off.get("is_direct", True))
        via_code = str(meta_off.get("via_code") or to_code).strip().upper()

        if price <= 0 or not from_code or not to_code or not dep_time or ":" not in dep_time:
            continue

        try:
            dep_h, dep_m = map(int, dep_time.split(":")[:2])
        except Exception:
            dep_h, dep_m = 0, 0
        try:
            arr_h, arr_m = map(int, arr_time.split(":")[:2])
        except Exception:
            arr_h, arr_m = dep_h, dep_m

        dep_dt = base_dt
        arr_dt = base_dt
        total_duration_mins = 75
        dep_local = str(meta_off.get("dep_local") or "")
        arr_local = str(meta_off.get("arr_local") or "")
        try:
            if len(dep_local) >= 19 and len(arr_local) >= 19:
                dt1 = datetime.fromisoformat(dep_local[:19])
                dt2 = datetime.fromisoformat(arr_local[:19])
                dep_dt = dt1
                arr_dt = dt2
                diff_m = int((dt2 - dt1).total_seconds() // 60)
                if diff_m > 0:
                    total_duration_mins = diff_m
        except Exception:
            pass

        hours = total_duration_mins // 60
        mins = total_duration_mins % 60
        duration_str = f"{hours} sa {mins} dk" if hours > 0 else f"{mins} dk"

        leg_first: List[Any] = [None] * 23
        leg_first[3] = from_code
        leg_first[6] = via_code if not is_direct else to_code
        leg_first[11] = total_duration_mins
        leg_first[17] = "Uçak"
        leg_first[20] = [dep_dt.year, dep_dt.month, dep_dt.day]
        leg_first[21] = [arr_dt.year, arr_dt.month, arr_dt.day]
        legs = [leg_first]
        if not is_direct:
            leg_last = list(leg_first)
            leg_last[6] = to_code
            legs.append(leg_last)

        sig = (carrier_code or airline_name, from_code, to_code, dep_time, arr_time)
        if sig not in unique_fallback or price < unique_fallback[sig]["price"]:
            unique_fallback[sig] = {
                "f0": [],
                "legs": legs,
                "price": price,
                "official_base_price": official_base_price,
                "from_ota_fallback": True,
                "booking_token": None,
                "from_code": from_code,
                "to_code": to_code,
                "dep_t": (dep_h, dep_m),
                "arr_t": (arr_h, arr_m),
                "dep_time": dep_time,
                "arr_time": arr_time,
                "carrier_code": carrier_code,
                "fn_code": fn_code,
                "airline_name": airline_name,
                "flight_no": flight_no,
                "total_duration_mins": total_duration_mins,
                "duration_str": duration_str,
                "is_direct": is_direct,
            }

    return sorted(unique_fallback.values(), key=lambda x: (x["price"], x["dep_t"][0] * 60 + x["dep_t"][1]))


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
    infants: int = 0,
    include_multi_ota: bool = True,
    _allow_hub_fallback: bool = True,
) -> List[Dict[str, Any]]:
    """
    Google Flights altyapısını kullanarak canlı havayolu seferlerini, net fiyatlarını ve kabin sınıfını çeker.
    Tüm kategorileri ve havalimanı çiftlerini tarayarak eksiksiz sefer listesi döndürür.
    Havalimanı olmayan ilçe/şehir aramalarında (ör. Manavgat, Alanya, Fethiye, Çeşme) en yakın aktif havalimanını çözümler.
    """
    from app.cities import FALLBACK_MAJOR_HUB_BY_IATA, find_city

    origin_city, orig_is_nearby = resolve_nearest_airport_city(origin_city_name)
    dest_city, dest_is_nearby = resolve_nearest_airport_city(dest_city_name)

    if not origin_city or not dest_city:
        return []

    if not origin_city.get("has_airport") or not dest_city.get("has_airport"):
        return []

    orig_nearby_note = (
        f"ℹ️ {origin_city_name} için en yakın aktif ana havalimanı olan {origin_city.get('name')} seferleri listelenmiştir."
        if orig_is_nearby
        else None
    )
    dest_nearby_note = (
        f"ℹ️ {dest_city_name} için en yakın aktif ana havalimanı olan {dest_city.get('name')} seferleri listelenmiştir."
        if dest_is_nearby
        else None
    )

    hub_fallback_notes: List[str] = []
    is_dom_route = not bool(origin_city.get("is_international") or dest_city.get("is_international"))
    if is_dom_route and _allow_hub_fallback:
        orig_iata_raw = str(origin_city.get("iata") or "").upper()
        dest_iata_raw = str(dest_city.get("iata") or "").upper()
        if orig_iata_raw in FALLBACK_MAJOR_HUB_BY_IATA and FALLBACK_MAJOR_HUB_BY_IATA[orig_iata_raw].get("domestic_inactive"):
            fb_info = FALLBACK_MAJOR_HUB_BY_IATA[orig_iata_raw]
            fb_city = find_city(fb_info["hub_slug"])
            if fb_city:
                hub_fallback_notes.append(
                    f"ℹ️ {origin_city.get('name')} ({orig_iata_raw}) Havalimanı'nda tarifeli iç hat seferi bulunmadığından en yakın ana merkez olan {fb_info['hub_name']} ({fb_info['transfer_note']}) seferleri listelenmiştir."
                )
                origin_city = fb_city
        if dest_iata_raw in FALLBACK_MAJOR_HUB_BY_IATA and FALLBACK_MAJOR_HUB_BY_IATA[dest_iata_raw].get("domestic_inactive"):
            fb_info = FALLBACK_MAJOR_HUB_BY_IATA[dest_iata_raw]
            fb_city = find_city(fb_info["hub_slug"])
            if fb_city:
                hub_fallback_notes.append(
                    f"ℹ️ {dest_city.get('name')} ({dest_iata_raw}) Havalimanı'nda tarifeli iç hat seferi bulunmadığından en yakın ana merkez olan {fb_info['hub_name']} ({fb_info['transfer_note']}) seferleri listelenmiştir."
                )
                dest_city = fb_city

    if origin_city.get("iata") and origin_city.get("iata") == dest_city.get("iata"):
        return []

    # Yolcu sayılarını normalize et
    adults = max(1, adults or passengers or 1)
    children = max(0, children or 0)
    infants = max(0, infants or 0)

    orig_slug = origin_city.get("slug", origin_city_name.lower())
    dest_slug = dest_city.get("slug", dest_city_name.lower())
    is_round = (trip_type == "round_trip" and bool(return_date))
    seat_mode = "business" if cabin_class == "business" else "economy"

    def _apply_caller_notes(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        caller_notes = [n for n in [orig_nearby_note, dest_nearby_note, *hub_fallback_notes] if n]
        if not caller_notes:
            return items
        for it in items:
            existing_parts = [p.strip() for p in str(it.get("route_notice") or "").split("•") if p.strip()]
            for cn in caller_notes:
                if cn not in existing_parts:
                    existing_parts.append(cn)
            it["route_notice"] = " • ".join(existing_parts) if existing_parts else None
        return items

    # 1. Önbellek (Cache) Kontrolü (10 Dakika TTL • RAM + Disk Korumalı)
    # ÖNEMLİ: include_multi_ota=False (esnek takvim şeridi) asla ana arama (include_multi_ota=True) önbelleğini ezemez!
    base_cache_key = f"{orig_slug}:{dest_slug}:{departure_date}:{return_date or ''}:{'rt' if is_round else 'ow'}:{seat_mode}:{adults}:{children}:{infants}"
    cache_key = base_cache_key if include_multi_ota else f"{base_cache_key}:fast"
    now_ts = time.time()
    with _FLIGHT_CACHE_LOCK:
        # Eğer hızlı sorgu (fast) isteniyorsa ama tam sorgu (base_cache_key) zaten önbellekte varsa onu kullan
        if not include_multi_ota and base_cache_key in _FLIGHT_CACHE:
            full_entry = _FLIGHT_CACHE[base_cache_key]
            if now_ts - full_entry["ts"] < FLIGHT_CACHE_TTL_SECONDS:
                return _apply_caller_notes(copy.deepcopy(full_entry["data"]))
        cached_entry = _FLIGHT_CACHE.get(cache_key)
        if cached_entry and (now_ts - cached_entry["ts"] < FLIGHT_CACHE_TTL_SECONDS):
            return _apply_caller_notes(copy.deepcopy(cached_entry["data"]))

    disk_path = _get_flight_disk_cache_path(cache_key)
    full_disk_path = _get_flight_disk_cache_path(base_cache_key)
    check_paths = [full_disk_path, disk_path] if not include_multi_ota else [disk_path]
    for d_path in check_paths:
        if os.path.exists(d_path):
            try:
                with open(d_path, "r", encoding="utf-8") as df:
                    disk_payload = json.load(df)
                if disk_payload and (now_ts - float(disk_payload.get("ts", 0)) < FLIGHT_CACHE_TTL_SECONDS):
                    disk_data = disk_payload.get("data") or []
                    if disk_data:
                        from app.cities import build_obilet_flight_url
                        for _it in disk_data:
                            if "/ucak-bileti/" in str(_it.get("obilet_link") or ""):
                                _it["obilet_link"] = build_obilet_flight_url(
                                    from_code=_it.get("from_code") or "",
                                    to_code=_it.get("to_code") or "",
                                    departure_date=departure_date,
                                    return_date=return_date,
                                    is_round=is_round,
                                    adults=adults,
                                    children=children,
                                    infants=infants,
                                    cabin_class=seat_mode,
                                    orig_slug=orig_slug,
                                    dest_slug=dest_slug,
                                )
                            if str(_it.get("airline_direct_url") or "") in (
                                "https://ajet.com/tr",
                                "https://www.turkishairlines.com/tr-tr/ucak-bileti/",
                                "https://www.sunexpress.com/tr-tr/",
                                "https://www.flypgs.com/",
                            ):
                                _it["airline_direct_url"] = _it.get("official_link") or _it.get("airline_direct_url")
                        with _FLIGHT_CACHE_LOCK:
                            _FLIGHT_CACHE[cache_key] = {"ts": float(disk_payload["ts"]), "data": copy.deepcopy(disk_data)}
                        return _apply_caller_notes(copy.deepcopy(disk_data))
            except Exception:
                pass

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
            html = ""
            req_params = {**q.params(), "gl": "TR", "hl": "tr", "curr": "TRY"}
            req_cookies = {
                "SOCS": "CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmVuIAEaBgiAo_CmBg",
                "CONSENT": "YES+cb.20230531-04-p0.tr+FX+999",
            }
            try:
                from primp import Client as PrimpClient
                p_client = None
                for imp_ver in ("chrome_145", "chrome_133", "chrome_131", "chrome_130", "chrome_128", "chrome_126", "chrome_124", "chrome_120", None):
                    try:
                        if imp_ver:
                            p_client = PrimpClient(
                                impersonate=imp_ver,
                                referer=True,
                                cookie_store=True,
                            )
                        else:
                            p_client = PrimpClient(referer=True, cookie_store=True)
                        break
                    except Exception:
                        continue
                if p_client is not None:
                    p_res = p_client.get(
                        "https://www.google.com/travel/flights",
                        params=req_params,
                        cookies=req_cookies,
                    )
                    html = p_res.text or ""
            except Exception:
                html = ""
            if not html or "ds:1" not in html:
                try:
                    import requests as _requests
                    r_res = _requests.get(
                        "https://www.google.com/travel/flights",
                        params=req_params,
                        cookies=req_cookies,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                        },
                        timeout=8.0,
                    )
                    if r_res.status_code == 200 and "ds:1" in (r_res.text or ""):
                        html = r_res.text
                except Exception:
                    pass
            if not html or "ds:1" not in html:
                html = fetch_flights_html(q)
            parser = LexborHTMLParser(html)
            script = parser.css_first('script.ds\\:1')
            if not script:
                return []
            data_str = script.text().split('data:', 1)[1].rsplit(',', 1)[0].strip()
            try:
                payload = json.loads(data_str)
            except json.JSONDecodeError:
                payload, _ = json.JSONDecoder().raw_decode(data_str)
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
    max_workers = max(2, len(pairs) * (2 if is_round else 1) + (1 if include_multi_ota else 0))
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
        multi_ota_future = (
            executor.submit(
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
            if include_multi_ota
            else None
        )

        for f in as_completed(outbound_futures):
            all_raw_flights.extend(f.result())
        for f in as_completed(return_futures):
            all_raw_return_flights.extend(f.result())
        if multi_ota_future is not None:
            try:
                multi_ota_map = multi_ota_future.result() or {}
            except Exception as ota_err:
                logger.debug(f"Multi-OTA map error: {ota_err}")
                multi_ota_map = {}

    sorted_raw = _parse_unique_flights(all_raw_flights) if all_raw_flights else []
    if not sorted_raw and multi_ota_map:
        sorted_raw = _build_fallback_sorted_raw_from_ota(multi_ota_map, departure_date)
    if not sorted_raw:
        # 2. Kademe Dinamik Yedek Hub (Dynamic Hub Fallback):
        # Kısıtlı/sezonluk havalimanlarında (Örn: YEI, ISE, KZR, ONQ, TEQ, CKZ, KFS, NOP, TJK, SXZ)
        # seçilen rotada 0 geçerli uçuş döndüyse otomatik olarak en yakın 7/24 aktif ana hub'a geç.
        if _allow_hub_fallback:
            orig_i = str(origin_city.get("iata") or "").upper()
            dest_i = str(dest_city.get("iata") or "").upper()
            new_orig_name = origin_city_name
            new_dest_name = dest_city_name
            dyn_notes: List[str] = []
            if orig_i in FALLBACK_MAJOR_HUB_BY_IATA:
                fbo = FALLBACK_MAJOR_HUB_BY_IATA[orig_i]
                new_orig_name = fbo["hub_slug"]
                dyn_notes.append(
                    f"ℹ️ {origin_city.get('name')} ({orig_i}) Havalimanı'nda bu rotada doğrudan sefer bulunmadığından en yakın ana merkez olan {fbo['hub_name']} ({fbo['transfer_note']}) seferleri listelenmiştir."
                )
            if dest_i in FALLBACK_MAJOR_HUB_BY_IATA:
                fbd = FALLBACK_MAJOR_HUB_BY_IATA[dest_i]
                new_dest_name = fbd["hub_slug"]
                dyn_notes.append(
                    f"ℹ️ {dest_city.get('name')} ({dest_i}) Havalimanı'nda bu rotada doğrudan sefer bulunmadığından en yakın ana merkez olan {fbd['hub_name']} ({fbd['transfer_note']}) seferleri listelenmiştir."
                )
            if dyn_notes and (new_orig_name != origin_city_name or new_dest_name != dest_city_name):
                fb_results = fetch_live_flights_from_google(
                    origin_city_name=new_orig_name,
                    dest_city_name=new_dest_name,
                    departure_date=departure_date,
                    return_date=return_date,
                    passengers=passengers,
                    trip_type=trip_type,
                    cabin_class=cabin_class,
                    adults=adults,
                    children=children,
                    infants=infants,
                    include_multi_ota=include_multi_ota,
                    _allow_hub_fallback=False,
                )
                if fb_results:
                    combined_note = " ".join(dyn_notes)
                    for item_r in fb_results:
                        existing_rn = item_r.get("route_notice")
                        item_r["route_notice"] = f"{combined_note} • {existing_rn}" if existing_rn else combined_note
                    return fb_results

        with _FLIGHT_CACHE_LOCK:
            _FLIGHT_CACHE[cache_key] = {"ts": now_ts, "data": []}
        return []
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
            if hub_fallback_notes:
                fb_prefix = " ".join(hub_fallback_notes)
                route_notice = f"{fb_prefix} • {route_notice}" if route_notice else fb_prefix

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
            _kayak_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
            if is_round and return_date:
                booking_flight_link = f"https://www.kayak.com.tr/flights/{from_code.upper()}-{to_code.upper()}/{departure_date}/{return_date}?sort=bestflight_a&aid={_kayak_aid}"
            else:
                booking_flight_link = f"https://www.kayak.com.tr/flights/{from_code.upper()}-{to_code.upper()}/{departure_date}?sort=bestflight_a&aid={_kayak_aid}"


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

            # Enuygun Canlı Arama ve Biletleme Linki (Kalkış, Varış, Tarih, Yolcu ve Havayolu Filtreli)
            enuygun_dep_date = dep_dt.strftime("%d.%m.%Y") if dep_dt else datetime.strptime(departure_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            enuygun_route = f"{orig_slug}-{dest_slug}-{from_code.lower()}a-{to_code.lower()}a"
            enuygun_pax = f"yetiskin={adults}"
            if children > 0:
                enuygun_pax += f"&cocuk={children}"
            if infants > 0:
                enuygun_pax += f"&bebek={infants}"
            enuygun_subid = getattr(settings, "AFFILIATE_ENUYGUN_SUBID", "hakikibilet")
            enuygun_flight_link = f"https://www.enuygun.com/ucak-bileti/arama/{enuygun_route}/?gidis={enuygun_dep_date}&{enuygun_pax}"
            if is_round and return_date:
                try:
                    enuygun_ret_date = datetime.strptime(return_date, "%Y-%m-%d").strftime("%d.%m.%Y")
                except Exception:
                    enuygun_ret_date = return_date
                enuygun_flight_link += f"&donus={enuygun_ret_date}"
            if is_biz:
                enuygun_flight_link += "&sinif=business"
            if carrier_code in ("PC", "TK", "VF", "XQ"):
                enuygun_flight_link += f"&havayolu={carrier_code}"
            if enuygun_subid:
                enuygun_flight_link += f"&subid={enuygun_subid}"

            # Obilet Gerçek Tarihli Canlı Uçak Sefer Sonuçları Linki (/ucuslar/{orig_id}-{dest_id}/{YYYYMMDD}/{pax}/{cabin}/all)
            from app.cities import build_obilet_flight_url
            obilet_flight_link = build_obilet_flight_url(
                from_code=from_code,
                to_code=to_code,
                departure_date=departure_date,
                return_date=return_date,
                is_round=is_round,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=seat_mode,
                orig_slug=orig_slug,
                dest_slug=dest_slug,
            )


            # Havayolu kimliği ve resmi bilet seçim linkleri (Provider Registry üzerinden kural bazlı)
            carrier_meta = resolve_carrier_meta(
                carrier_name=airline_name,
                carrier_code=carrier_code,
                from_code=from_code,
                to_code=to_code,
                dep_date=departure_date,
                ret_date=return_date,
                is_round=is_round,
                adults=adults,
                cabin_class=seat_mode,
            )
            carrier_display = carrier_meta["display_name"]
            official_name = carrier_meta["official_name"]
            official_link = carrier_meta["official_link"]
            badge = "💰 En Uygun Fiyat" if (idx == 0 and not is_biz) else carrier_meta["badge"]

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
            conn_time_key = f"CONN:{from_code}:{to_code}:{dep_time}:{arr_time}:{carrier_code}"

            ota_for_flight: Dict[str, Dict[str, Any]] = {}
            if is_direct:
                if short_time_key in multi_ota_map:
                    ota_for_flight.update(multi_ota_map[short_time_key])
                if city_time_key in multi_ota_map:
                    ota_for_flight.update(multi_ota_map[city_time_key])
                if city_dest_time_key in multi_ota_map:
                    ota_for_flight.update(multi_ota_map[city_dest_time_key])
                if time_key in multi_ota_map:
                    ota_for_flight.update(multi_ota_map[time_key])
            else:
                if conn_time_key in multi_ota_map:
                    ota_for_flight.update(multi_ota_map[conn_time_key])
            if f_key and f_key in multi_ota_map:
                ota_for_flight.update(multi_ota_map[f_key])

            # Toleranslı saat kontrolü (+/- 10 dakika içindeki aynı havayolu direkt seferi)
            if is_direct and dep_time and carrier_code:
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

            # ANAYASA KURALI (EN UCUZ FİYAT KAZANIR, EŞİTLİKTE GELİR GETİREN ORTAK KAZANIR):
            # 1. Trip.com (active_affiliate=True, AllianceID: 11051531) resmi IATA biletleme acentesidir.
            #    Eğer Trip.com canlı taramasında havayolu taban fiyatından daha ucuz özel bir indirim
            #    yakalandıysa o indirimli fiyat kullanılır; aksi halde standart IATA taban fiyatı (price)
            #    üzerinden eşitlik (tie-breaker) yarışına girer ve gelir getiren aktif ortak olarak kazanır.
            # 2. Kiwi.com, Booking.com veya Enuygun daha ucuz bir canlı fiyat sunduğunda ise en ucuz olan kazanır.
            base_clean_price = float(round(price)) if (price and float(price) > 0) else None
            if trip_live and trip_live.get("price") and float(trip_live["price"]) > 0:
                base_trip_price = float(trip_live["price"])
                if is_round and not trip_live.get("is_round"):
                    cand_trip_price = float(round(base_trip_price * 2))
                else:
                    cand_trip_price = float(round(base_trip_price))
                # SIFIR VARSAYIM: Trip.com yalnızca kendi canlı fiyatını taşır; havayolu fiyatı kopyalanmaz.
                trip_price = cand_trip_price
            else:
                # Trip.com canlı fiyatı yoksa fiyat boş kalır (asla başka kaynaktan kopyalanmaz).
                trip_price = None

            candidate_trip_url = str(trip_live.get("url") or "") if trip_live else ""
            if candidate_trip_url and "/flights/search" not in candidate_trip_url:
                trip_url = candidate_trip_url
            else:
                trip_url = trip_flight_link

            # Eğer bulut IP kısıtlaması nedeniyle Google Flights yerine OTA yedek motorundan geldiyse,
            # Kiwi'nin yüksek API fiyatını asla Google Flights (official) üstüne kopyalama!
            official_verified_price = item.get("official_base_price") if item.get("from_ota_fallback") else price
            raw_providers = [
                {
                    "name": official_name,
                    "url": official_link,
                    "price": official_verified_price,
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

            # Booking.com Flights (Booking Holdings resmi Türkiye platformu: Kayak.com.tr)
            if booking_live and booking_live.get("price") and float(booking_live["price"]) > 0:
                base_b_price = float(booking_live["price"])
                booking_price = round(base_b_price * 2, 2) if (is_round and not booking_live.get("is_round")) else round(base_b_price, 2)
                cand_b_url = str(booking_live.get("url") or "")
                b_url = cand_b_url if (cand_b_url and "booking.com/flights" not in cand_b_url and "flights.booking.com" not in cand_b_url) else booking_flight_link
            else:
                booking_price = None
                b_url = booking_flight_link

            raw_providers.append(
                {
                    "name": "Booking / Kayak",
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
                skyscanner_price = None
                s_url = skyscanner_flight_link

            raw_providers.append(
                {
                    "name": "Skyscanner",
                    "url": s_url,
                    "price": skyscanner_price,
                    "channel": "skyscanner",
                }
            )

            # TEK VE KESİN KAZANAN SAĞLAYICI SEÇİMİ (Universal Single Source of Truth)
            decision = decide_winning_flight_offer(
                raw_providers=raw_providers,
                carrier_meta=carrier_meta,
                is_international=is_intl_route,
            )
            providers_list = decision["providers"]
            final_ticket_price = decision["winner_price"] if (decision["winner_price"] is not None) else price
            direct_link = decision["winner_url"]
            winner_name = decision["winner_name"]
            winner_channel = decision["winner_channel"]
            winner_button_tr = decision["winner_button_tr"]
            winner_button_en = decision["winner_button_en"]

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

                clean_ret_orig = re.sub(r"\s*\([A-Z0-9/ -]+\)", "", dest_city_name).strip()
                clean_ret_dest = re.sub(r"\s*\([A-Z0-9/ -]+\)", "", origin_city_name).strip()
                ret_orig_lbl = "Adana - Mersin / Çukurova (COV)" if chosen_ret["from_code"] == "COV" else f"{clean_ret_orig} ({chosen_ret['from_code']})"
                ret_dest_lbl = "Adana - Mersin / Çukurova (COV)" if chosen_ret["to_code"] == "COV" else f"{clean_ret_dest} ({chosen_ret['to_code']})"
                return_leg_dict = {
                    "origin": ret_orig_lbl,
                    "destination": ret_dest_lbl,
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

            clean_orig_title = re.sub(r"\s*\([A-Z0-9/ -]+\)", "", origin_city_name).strip()
            clean_dest_title = re.sub(r"\s*\([A-Z0-9/ -]+\)", "", dest_city_name).strip()
            orig_display_lbl = "Adana - Mersin / Çukurova (COV)" if from_code == "COV" else f"{clean_orig_title} ({from_code})"
            dest_display_lbl = "Adana - Mersin / Çukurova (COV)" if to_code == "COV" else f"{clean_dest_title} ({to_code})"

            results.append({
                "id": f"live-fl-{idx+1}",
                "transport_type": "flight",
                "carrier": carrier_display,
                "carrier_code": carrier_code,
                "carrier_logo": "✈️",
                "flight_number": flight_no,
                "origin": orig_display_lbl,
                "destination": dest_display_lbl,
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
                "airline_direct_url": carrier_meta.get("airline_direct_url", official_link),
                "airline_label_tr": carrier_meta.get("airline_label_tr", f"✈️ {carrier_display}'da Gör ↗"),
                "airline_label_en": carrier_meta.get("airline_label_en", f"✈️ View on {carrier_display} ↗"),
                "agent_name": "Enuygun",
                "agent_link": enuygun_flight_link,
                "enuygun_link": enuygun_flight_link,
                "kayak_link": booking_flight_link,
                "obilet_link": obilet_flight_link,
                "google_link": google_flights_link,
                "direct_link": direct_link,
                "booking_link": direct_link,
                "winner_url": direct_link,
                "winner_name": winner_name,
                "winner_channel": winner_channel,
                "winner_button_text": winner_button_tr,
                "winner_button_text_en": winner_button_en,
                "trip_link": trip_url,
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
        save_ts = time.time()
        with _FLIGHT_CACHE_LOCK:
            if len(_FLIGHT_CACHE) >= 50:
                oldest_key = min(_FLIGHT_CACHE.keys(), key=lambda k: _FLIGHT_CACHE[k].get("ts", 0))
                _FLIGHT_CACHE.pop(oldest_key, None)
            _FLIGHT_CACHE[cache_key] = {
                "ts": save_ts,
                "data": copy.deepcopy(results),
            }
        try:
            with open(disk_path, "w", encoding="utf-8") as df:
                json.dump({"ts": save_ts, "data": results}, df, ensure_ascii=False)
        except Exception:
            pass

    return _apply_caller_notes(results)

