"""
Hibrit Çoklu Acente (Multi-OTA) Canlı Fiyat ve Doğrudan Biletleme (Deep-Link) Toplayıcı (Faz 1B)

Bu servis, aynı uçuş seferi (ör. PC 2182, VF 3078, TK 2310) için birden fazla veri kaynağını
PARALEL olarak sorgular ve her seferin altına gerçek canlı acente fiyatlarını + doğrudan ödeme/yolcu
ekranına giden (deep-link) bağlantıları yerleştirir:

1. Motor 1 — Kiwi.com / Skypicker GraphQL Canlı Motoru (Anında Aktif & Ücretsiz):
   - Tek yön ve Gidiş-Dönüş tüm seferler için Kiwi.com'un gerçek anlık TL fiyatlarını ve
     doğrudan yolcu bilgisi ekranına giden 'token' bazlı biletleme linkini çeker.
2. Motor 2 — RapidAPI Multi-OTA Motoru (Skyscanner / Google Flights Multi-Agent):
   - RapidAPI aboneliği aktif olduğunda Trip.com, Enuygun, Booking.com vb. acentelerin
     sefer bazlı canlı fiyatlarını ve indirimlerini tek pakette çeker.
3. Motor 3 — Travelpayouts / Aviasales Resmi Veri API Motoru:
   - TRAVELPAYOUTS_API_TOKEN tanımlandığında ek acente fiyatlarını ve affiliate linklerini birleştirir.
"""

from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
import logging
import requests
from app.config import settings
from app.cities import find_city

logger = logging.getLogger(__name__)

KIWI_GRAPHQL_URL = "https://api.skypicker.com/umbrella/v2/graphql"

# Akıllı Önbellek (Kota Koruyucu - 15 Dakika TTL)
_OTA_CACHE: Dict[str, Tuple[float, Any]] = {}
_OTA_CACHE_TTL = 900  # 15 dakika (900 saniye)


def _get_from_cache(cache_key: str):
    now = time.time()
    if cache_key in _OTA_CACHE:
        ts, data = _OTA_CACHE[cache_key]
        if now - ts < _OTA_CACHE_TTL:
            return data
    return None


def _save_to_cache(cache_key: str, data: Any):
    if len(_OTA_CACHE) >= 500:
        oldest_key = min(_OTA_CACHE.keys(), key=lambda k: _OTA_CACHE[k][0])
        _OTA_CACHE.pop(oldest_key, None)
    _OTA_CACHE[cache_key] = (time.time(), data)



def normalize_flight_key(flight_no: str) -> str:
    """
    'PC 2182', 'PC-2182', 'VF 3078' gibi sefer numaralarını 'PC2182', 'VF3078' anahtarına dönüştürür.
    """
    if not flight_no:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(flight_no).upper())


def _merge_offer(
    target_map: Dict[str, Dict[str, Dict[str, Any]]],
    flight_key: str,
    channel: str,
    offer: Dict[str, Any],
) -> None:
    """
    Aynı sefer ve aynı kanal için birden fazla kombinasyon gelirse en düşük canlı fiyatı korur.
    """
    if not flight_key or not offer or not offer.get("price") or float(offer["price"]) <= 0:
        return
    price_val = round(float(offer["price"]), 2)
    flight_bucket = target_map.setdefault(flight_key, {})
    existing = flight_bucket.get(channel)
    if existing is None or price_val < float(existing.get("price", 999999999)):
        merged = dict(offer)
        merged.update({
            "name": offer.get("name", channel.capitalize()),
            "price": price_val,
            "url": offer.get("url", ""),
            "channel": channel,
            "dep_time": offer.get("dep_time"),
        })
        flight_bucket[channel] = merged


def fetch_kiwi_live_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
    seat_mode: str = "economy",
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Kiwi.com GraphQL API üzerinden sefer bazlı canlı TL fiyatlarını ve
    doğrudan yolcu ekranına giden (direct=true&token=...) linklerini çeker.
    """
    offers_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not orig_codes or not dest_codes or not departure_date:
        return offers_map

    source_ids = [f"Station:airport:{code.upper()}" for code in orig_codes if code]
    dest_ids = [f"Station:airport:{code.upper()}" for code in dest_codes if code]
    cabin_str = "BUSINESS" if seat_mode == "business" else "ECONOMY"
    is_round = bool(return_date)
    affil_id = getattr(settings, "KIWI_AFFILIATE_ID", "travelpayouts")
    tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")

    try:
        if is_round and return_date:
            query_payload = {
                "query": """
                query SearchReturn($search: SearchReturnInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {
                  returnItineraries(search: $search, filter: $filter, options: $options) {
                    ... on Itineraries {
                      itineraries {
                        ... on ItineraryReturn {
                          price { amount }
                          bookingOptions {
                            edges {
                              node {
                                bookingUrl
                                price { amount }
                              }
                            }
                          }
                          outbound {
                            sectorSegments {
                              segment {
                                source { station { code } localTime }
                                destination { station { code } localTime }
                                code
                                carrier { code name }
                                operatingCarrier { code name }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
                """,
                "variables": {
                    "search": {
                        "itinerary": {
                            "source": {"ids": source_ids},
                            "destination": {"ids": dest_ids},
                            "outboundDepartureDate": {
                                "start": f"{departure_date}T00:00:00",
                                "end": f"{departure_date}T23:59:59",
                            },
                            "inboundDepartureDate": {
                                "start": f"{return_date}T00:00:00",
                                "end": f"{return_date}T23:59:59",
                            },
                        },
                        "passengers": {"adults": int(adults), "children": int(children), "infants": int(infants)},
                        "cabinClass": {"cabinClass": cabin_str, "applyMixedClasses": False},
                    },
                    "filter": {"limit": 70},
                    "options": {"currency": "TRY", "locale": "tr", "partner": "skypicker"},
                },
            }
        else:
            query_payload = {
                "query": """
                query SearchOneWay($search: SearchOnewayInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {
                  onewayItineraries(search: $search, filter: $filter, options: $options) {
                    ... on Itineraries {
                      itineraries {
                        ... on ItineraryOneWay {
                          price { amount }
                          bookingOptions {
                            edges {
                              node {
                                bookingUrl
                                price { amount }
                              }
                            }
                          }
                          sector {
                            sectorSegments {
                              segment {
                                source { station { code } localTime }
                                destination { station { code } localTime }
                                code
                                carrier { code name }
                                operatingCarrier { code name }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
                """,
                "variables": {
                    "search": {
                        "itinerary": {
                            "source": {"ids": source_ids},
                            "destination": {"ids": dest_ids},
                            "outboundDepartureDate": {
                                "start": f"{departure_date}T00:00:00",
                                "end": f"{departure_date}T23:59:59",
                            },
                        },
                        "passengers": {"adults": int(adults), "children": int(children), "infants": int(infants)},
                        "cabinClass": {"cabinClass": cabin_str, "applyMixedClasses": False},
                    },
                    "filter": {"limit": 70},
                    "options": {"currency": "TRY", "locale": "tr", "partner": "skypicker"},
                },
            }

        resp = requests.post(KIWI_GRAPHQL_URL, json=query_payload, timeout=3.5)
        if resp.status_code != 200:
            return offers_map

        data = resp.json().get("data") or {}
        root_key = "returnItineraries" if (is_round and return_date) else "onewayItineraries"
        itineraries = (data.get(root_key) or {}).get("itineraries") or []

        for it in itineraries:
            if not isinstance(it, dict):
                continue
            sector = it.get("outbound") if (is_round and return_date) else it.get("sector")
            if not sector:
                continue
            segs = sector.get("sectorSegments") or []
            if not segs:
                continue

            first_seg = (segs[0] or {}).get("segment") or {}
            last_seg = (segs[-1] or {}).get("segment") or first_seg
            flight_code_num = str(first_seg.get("code") or "").strip()
            carrier = first_seg.get("carrier") or {}
            op_carrier = first_seg.get("operatingCarrier") or {}
            carrier_code = str(carrier.get("code") or "").strip().upper()
            op_carrier_code = str(op_carrier.get("code") or "").strip().upper()
            carrier_name = str(carrier.get("name") or op_carrier.get("name") or carrier_code or "Havayolu").strip()

            if not flight_code_num or not carrier_code:
                continue

            # Fiyat ve doğrudan yolcu ekranı linkini (bookingUrl) çıkar
            raw_amount = (it.get("price") or {}).get("amount")
            edges = (it.get("bookingOptions") or {}).get("edges") or []
            booking_path = ""
            if edges and isinstance(edges[0], dict):
                node = edges[0].get("node") or {}
                booking_path = node.get("bookingUrl") or ""
                node_amt = (node.get("price") or {}).get("amount")
                if node_amt and not raw_amount:
                    raw_amount = node_amt

            if not raw_amount or float(raw_amount) <= 0:
                continue

            price_val = round(float(raw_amount), 2)
            kiwi_affil_params = f"affilid={affil_id}&marker={tp_marker}"
            if booking_path.startswith("/"):
                sep = "&" if "?" in booking_path else "?"
                direct_url = f"https://www.kiwi.com{booking_path}{sep}{kiwi_affil_params}"
            elif booking_path.startswith("http"):
                sep = "&" if "?" in booking_path else "?"
                direct_url = f"{booking_path}{sep}{kiwi_affil_params}"
            else:
                direct_url = f"https://www.kiwi.com/tr/search/results/{orig_codes[0]}/{dest_codes[0]}/{departure_date}?{kiwi_affil_params}"

            local_time = str(((first_seg.get("source") or {}).get("localTime")) or "")
            arr_local_time = str(((last_seg.get("destination") or {}).get("localTime")) or "")
            dep_hhmm = local_time[11:16] if len(local_time) >= 16 else None
            arr_hhmm = arr_local_time[11:16] if len(arr_local_time) >= 16 else None
            src_code = str(((first_seg.get("source") or {}).get("station") or {}).get("code") or "").upper()
            dst_code = str(((last_seg.get("destination") or {}).get("station") or {}).get("code") or "").upper()
            via_code = str(((first_seg.get("destination") or {}).get("station") or {}).get("code") or "").upper()

            offer_item = {
                "name": "Kiwi.com",
                "price": price_val,
                "url": direct_url,
                "channel": "kiwi",
                "dep_time": dep_hhmm,
                "arr_time": arr_hhmm,
                "dep_local": local_time,
                "arr_local": arr_local_time,
                "from_code": src_code,
                "to_code": dst_code,
                "via_code": via_code,
                "carrier_code": carrier_code,
                "carrier_name": carrier_name,
                "fn_code": flight_code_num,
                "flight_no": f"{carrier_code} {flight_code_num}".strip(),
                "is_direct": (len(segs) == 1),
            }

            primary_key = normalize_flight_key(f"{carrier_code}{flight_code_num}")
            _merge_offer(offers_map, primary_key, "kiwi", offer_item)

            # Codeshare (Örn: TK / VF AnadoluJet ortak uçuşları) için ikinci anahtarı da kaydet
            if op_carrier_code and op_carrier_code != carrier_code:
                alt_key = normalize_flight_key(f"{op_carrier_code}{flight_code_num}")
                _merge_offer(offers_map, alt_key, "kiwi", offer_item)

            # Ayrıca saat bazlı yedek eşleştirme anahtarı (TIME:SAW:ADB:06:00:PC)
            if dep_hhmm and src_code and dst_code:
                time_key = f"TIME:{src_code}:{dst_code}:{dep_hhmm}:{carrier_code}"
                _merge_offer(offers_map, time_key, "kiwi", offer_item)

    except Exception as exc:
        logger.debug(f"Kiwi GraphQL live offer fetch warning: {exc}")

    return offers_map


SKY_ENTITY_MAP = {
    "SAW": ("ISTA", "27542903"),
    "IST": ("ISTA", "27542903"),
    "ADB": ("ADB", "95673399"),
    "AYT": ("AYT", "95673612"),
    "ESB": ("ESB", "128668440"),
    "TZX": ("TZX", "128667446"),
    "COV": ("COV", "220266826"),
    "ADA": ("COV", "220266826"),
    "BJV": ("BJV", "95673401"),
    "DLM": ("DLM", "95673892"),
    "GZT": ("GZT", "128668321"),
    "DIY": ("DIY", "128668443"),
    "VAN": ("VAN", "128667442"),
    "ERZ": ("ERZ", "128667834"),
    "KYA": ("KYA", "128668546"),
    "SZF": ("SZF", "128669037"),
    "ASR": ("ASR", "128668257"),
    "MLX": ("MLX", "128667482"),
    "EDO": ("EDO", "128667067"),
    "DNZ": ("DNZ", "128668104"),
    "GZP": ("GZP", "128667560"),
    "HTY": ("HTY", "128668268"),
    "KSY": ("KSY", "128667576"),
    "RZV": ("RZV", "205363195"),
    "ZRH": ("ZRH", "95673344"),
    "LHR": ("LHR", "95565050"),
    "CDG": ("CDG", "95601358"),
    "AMS": ("AMS", "95601362"),
    "FRA": ("FRA", "95601389"),
    "BER": ("BER", "95601373"),
    "MUC": ("MUC", "95601379"),
    "DUS": ("DUS", "95601384"),
    "VIE": ("VIE", "95673366"),
    "FCO": ("FCO", "95601440"),
    "MXP": ("MXP", "95601432"),
    "BCN": ("BCN", "95565085"),
    "MAD": ("MAD", "95565077"),
    "ATH": ("ATH", "95673624"),
    "GYD": ("GYD", "95673517"),
    "DXB": ("DXB", "95673418"),
}

CARRIER_NAME_MAP = {
    "pegasus": "PC",
    "ajet": "VF",
    "anadolujet": "VF",
    "turkish": "TK",
    "thy": "TK",
    "sunexpress": "XQ",
}


def _resolve_sky_entity(orig_code: str, api_key: str, api_host: str) -> Tuple[str, str]:
    c_up = orig_code.upper()
    if c_up in SKY_ENTITY_MAP:
        return SKY_ENTITY_MAP[c_up]
    try:
        r = requests.get(
            f"https://{api_host}/api/v1/flights/searchAirport?query={c_up}",
            headers={"x-rapidapi-key": api_key, "x-rapidapi-host": api_host},
            timeout=4.5,
        )
        if r.status_code == 200:
            arr = (r.json() or {}).get("data") or []
            chosen = None
            for item in arr:
                if not isinstance(item, dict):
                    continue
                nav = item.get("navigation") or {}
                rel = nav.get("relevantFlightParams") or {}
                if str(rel.get("skyId") or "").upper() == c_up:
                    chosen = item
                    break
            if not chosen and arr and isinstance(arr[0], dict):
                chosen = arr[0]
            if chosen:
                nav = chosen.get("navigation") or {}
                rel = nav.get("relevantFlightParams") or {}
                s_id = rel.get("skyId") or c_up
                e_id = str(rel.get("entityId") or nav.get("entityId") or "")
                if s_id and e_id:
                    SKY_ENTITY_MAP[c_up] = (s_id, e_id)
                    return s_id, e_id
    except Exception:
        pass
    return c_up, ""


def fetch_rapidapi_skyscanner_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
    seat_mode: str = "economy",
    adults: int = 1,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    RapidAPI Sky-Scrapper (Skyscanner Live Gateway) üzerinden doğrulanmış canlı uçuş fiyatlarını çeker.
    15 dakikalık akıllı önbellek ile API kotasını korur.
    """
    if not orig_codes or not dest_codes or not departure_date:
        return {}

    o_code = orig_codes[0].upper()
    d_code = dest_codes[0].upper()
    cache_key = f"SKY:{o_code}:{d_code}:{departure_date}:{return_date or ''}:{seat_mode}:{adults}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    offers_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    api_key = getattr(settings, "RAPIDAPI_FLIGHTS_KEY", "")
    api_host = getattr(settings, "RAPIDAPI_FLIGHTS_HOST", "sky-scrapper.p.rapidapi.com")
    if not api_key:
        return offers_map

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host,
    }

    try:
        # İstanbul için ISTA şehir kodunu tercih et
        if o_code in ("SAW", "IST"):
            o_sky, o_entity = "ISTA", "27542903"
        else:
            o_sky, o_entity = _resolve_sky_entity(o_code, api_key, api_host)

        if d_code in ("SAW", "IST"):
            d_sky, d_entity = "ISTA", "27542903"
        else:
            d_sky, d_entity = _resolve_sky_entity(d_code, api_key, api_host)

        if not o_entity or not d_entity:
            return offers_map

        params = {
            "originSkyId": o_sky,
            "destinationSkyId": d_sky,
            "originEntityId": o_entity,
            "destinationEntityId": d_entity,
            "date": departure_date,
            "currency": "TRY",
            "market": "tr-TR",
            "countryCode": "TR",
            "adults": str(adults),
            "cabinClass": "business" if seat_mode == "business" else "economy",
        }
        if return_date:
            params["returnDate"] = return_date

        resp = requests.get(
            f"https://{api_host}/api/v2/flights/searchFlights",
            headers=headers,
            params=params,
            timeout=5.0,
        )
        if resp.status_code != 200:
            return offers_map

        data_obj = resp.json().get("data") or {}
        itins = list(data_obj.get("itineraries") or [])
        sess_id = (data_obj.get("context") or {}).get("sessionId")
        if sess_id and (data_obj.get("context") or {}).get("status") == "incomplete":
            try:
                r2 = requests.get(
                    f"https://{api_host}/api/v2/flights/searchIncomplete",
                    headers=headers,
                    params={"sessionId": sess_id, "currency": "TRY", "market": "tr-TR", "countryCode": "TR"},
                    timeout=4.5,
                )
                if r2.status_code == 200:
                    itins.extend((r2.json().get("data") or {}).get("itineraries") or [])
            except Exception:
                pass
        sky_dep = departure_date.replace("-", "")[2:]
        if return_date:
            sky_ret = return_date.replace("-", "")[2:]
            skyscanner_base_url = (
                f"https://www.skyscanner.com.tr/transport/flights/{o_code.lower()}/{d_code.lower()}/{sky_dep}/{sky_ret}/?"
                f"adultsv2={adults}&cabinclass={'business' if seat_mode == 'business' else 'economy'}&currency=TRY&locale=tr-TR&rtn=1"
            )
        else:
            skyscanner_base_url = (
                f"https://www.skyscanner.com.tr/transport/flights/{o_code.lower()}/{d_code.lower()}/{sky_dep}/?"
                f"adultsv2={adults}&cabinclass={'business' if seat_mode == 'business' else 'economy'}&currency=TRY&locale=tr-TR&rtn=0"
            )

        for it in itins:
            legs = it.get("legs") or []
            if not legs:
                continue
            first_leg = legs[0]
            segs = first_leg.get("segments") or []
            if not segs:
                continue
            first_seg = segs[0]
            flight_num = str(first_seg.get("flightNumber") or "").strip()

            marketing_carrier = first_seg.get("marketingCarrier") or {}
            carrier_code = str(marketing_carrier.get("displayCode") or "").upper().strip()
            if not carrier_code:
                carrier_obj = (first_leg.get("carriers", {}).get("marketing") or [{}])[0]
                carrier_name = str(carrier_obj.get("name") or "").lower()
                for k, v in CARRIER_NAME_MAP.items():
                    if k in carrier_name:
                        carrier_code = v
                        break
                if not carrier_code:
                    carrier_code = str(carrier_obj.get("alternateId") or "PC").strip().upper()

            raw_price = (it.get("price") or {}).get("raw")
            if not raw_price or float(raw_price) <= 0:
                continue

            clean_price = round(float(raw_price), 2)
            f_key = normalize_flight_key(f"{carrier_code}{flight_num}")

            dep_dt_str = str(first_leg.get("departure") or "")
            arr_dt_str = str(first_leg.get("arrival") or "")
            dep_time = dep_dt_str[11:16] if len(dep_dt_str) >= 16 else None
            arr_time = arr_dt_str[11:16] if len(arr_dt_str) >= 16 else dep_time

            orig_disp = str((first_leg.get("origin") or {}).get("displayCode") or o_code).upper()
            dest_disp = str((first_leg.get("destination") or {}).get("displayCode") or d_code).upper()
            seg_orig = str((first_seg.get("origin") or {}).get("displayCode") or orig_disp).upper()
            seg_dest = str((first_seg.get("destination") or {}).get("displayCode") or dest_disp).upper()
            carrier_disp_name = str(marketing_carrier.get("name") or carrier_code).strip()

            if return_date:
                sky_item_url = (
                    f"https://www.skyscanner.com.tr/transport/flights/{orig_disp.lower()}/{dest_disp.lower()}/{sky_dep}/{sky_ret}/?"
                    f"adultsv2={adults}&cabinclass={'business' if seat_mode == 'business' else 'economy'}&currency=TRY&locale=tr-TR&rtn=1"
                )
            else:
                sky_item_url = (
                    f"https://www.skyscanner.com.tr/transport/flights/{orig_disp.lower()}/{dest_disp.lower()}/{sky_dep}/?"
                    f"adultsv2={adults}&cabinclass={'business' if seat_mode == 'business' else 'economy'}&currency=TRY&locale=tr-TR&rtn=0"
                )

            offer_item = {
                "name": "Skyscanner",
                "price": clean_price,
                "url": sky_item_url,
                "channel": "skyscanner",
                "dep_time": dep_time,
                "arr_time": arr_time,
                "dep_local": dep_dt_str,
                "arr_local": arr_dt_str,
                "from_code": orig_disp,
                "to_code": dest_disp,
                "carrier_code": carrier_code,
                "fn_code": flight_num,
                "carrier_name": carrier_disp_name,
                "flight_no": f"{carrier_code} {flight_num}".strip(),
                "is_direct": (len(segs) == 1),
            }

            _merge_offer(offers_map, f_key, "skyscanner", offer_item)

            if dep_time:
                _merge_offer(offers_map, f"TIME:{orig_disp}:{dest_disp}:{dep_time}:{carrier_code}", "skyscanner", offer_item)
                _merge_offer(offers_map, f"TIME:{seg_orig}:{seg_dest}:{dep_time}:{carrier_code}", "skyscanner", offer_item)
                _merge_offer(offers_map, f"SHORT:{dep_time}:{carrier_code}", "skyscanner", offer_item)

        _save_to_cache(cache_key, offers_map)
    except Exception as exc:
        logger.debug(f"Skyscanner API live offer fetch error: {exc}")

    return offers_map


def fetch_rapidapi_booking_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
    seat_mode: str = "economy",
    adults: int = 1,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    RapidAPI booking-com15 (Booking.com Flights API) üzerinden doğrulanmış canlı uçuş fiyatlarını çeker.
    15 dakikalık akıllı önbellek ile API kotasını korur.
    """
    if not orig_codes or not dest_codes or not departure_date:
        return {}

    o_code = orig_codes[0].upper()
    d_code = dest_codes[0].upper()
    cache_key = f"BOOKING:{o_code}:{d_code}:{departure_date}:{return_date or ''}:{seat_mode}:{adults}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    offers_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    api_key = getattr(settings, "RAPIDAPI_BOOKING_KEY", "")
    api_host = getattr(settings, "RAPIDAPI_BOOKING_HOST", "booking-com15.p.rapidapi.com")
    if not api_key:
        return offers_map

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host,
    }

    try:
        from_id = "IST.CITY" if o_code in ("IST", "SAW", "ISTA") else f"{o_code}.AIRPORT"
        to_id = "IST.CITY" if d_code in ("IST", "SAW", "ISTA") else f"{d_code}.AIRPORT"
        booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")

        params = {
            "fromId": from_id,
            "toId": to_id,
            "departDate": departure_date,
            "pageNo": "1",
            "adults": str(adults),
            "currency_code": "TRY",
            "cabinClass": "BUSINESS" if seat_mode == "business" else "ECONOMY",
        }
        if return_date:
            params["returnDate"] = return_date

        resp = requests.get(
            f"https://{api_host}/api/v1/flights/searchFlights",
            headers=headers,
            params=params,
            timeout=5.0,
        )
        if resp.status_code != 200:
            from app.services.trip_fare_service import fetch_kayak_live_offers
            fallback_kayak = fetch_kayak_live_offers(orig_codes, dest_codes, departure_date, return_date)
            if fallback_kayak:
                _save_to_cache(cache_key, fallback_kayak)
                return fallback_kayak
            return offers_map

        payload = resp.json() or {}
        flight_offers = (payload.get("data") or {}).get("flightOffers") or []

        booking_trip_type = "round_trip" if return_date else "one_way"
        booking_ret_param = f"&return={return_date}" if return_date else ""
        booking_cabin = "BUSINESS" if seat_mode == "business" else "ECONOMY"

        for offer in flight_offers:
            price_breakdown = offer.get("priceBreakdown") or {}
            total_rounded = price_breakdown.get("totalRounded") or {}
            total_obj = price_breakdown.get("total") or {}
            raw_units = total_rounded.get("units") or total_obj.get("units")
            if not raw_units or float(raw_units) <= 0:
                continue

            price_val = round(float(raw_units), 2)
            segments = offer.get("segments") or []
            if not segments:
                continue
            first_seg = segments[0]
            legs = first_seg.get("legs") or []
            if not legs:
                continue

            flight_info = legs[0].get("flightInfo") or {}
            carrier_info = flight_info.get("carrierInfo") or {}
            carrier_code = str(carrier_info.get("operatingCarrier") or carrier_info.get("marketingCarrier") or "").upper().strip()
            flight_num = str(flight_info.get("flightNumber") or "").strip()
            if not carrier_code or not flight_num:
                continue

            f_key = normalize_flight_key(f"{carrier_code}{flight_num}")
            dep_time_raw = str(first_seg.get("departureTime") or "")
            arr_time_raw = str(first_seg.get("arrivalTime") or "")
            dep_time = dep_time_raw[11:16] if len(dep_time_raw) >= 16 else None
            arr_time = arr_time_raw[11:16] if len(arr_time_raw) >= 16 else dep_time

            orig_actual = str((first_seg.get("departureAirport") or {}).get("code") or o_code).upper()
            dest_actual = str((first_seg.get("arrivalAirport") or {}).get("code") or d_code).upper()

            if return_date:
                booking_offer_url = f"https://www.kayak.com.tr/flights/{orig_actual}-{dest_actual}/{departure_date}/{return_date}?sort=bestflight_a"
            else:
                booking_offer_url = f"https://www.kayak.com.tr/flights/{orig_actual}-{dest_actual}/{departure_date}?sort=bestflight_a"


            offer_item = {
                "name": "Booking.com Flights",
                "price": price_val,
                "url": booking_offer_url,
                "channel": "booking",
                "dep_time": dep_time,
                "arr_time": arr_time,
                "dep_local": dep_time_raw,
                "arr_local": arr_time_raw,
                "from_code": orig_actual,
                "to_code": dest_actual,
                "carrier_code": carrier_code,
                "fn_code": flight_num,
                "carrier_name": carrier_code,
                "flight_no": f"{carrier_code} {flight_num}".strip(),
                "is_direct": (len(legs) == 1),
            }

            _merge_offer(offers_map, f_key, "booking", offer_item)

            if dep_time:
                time_key = f"TIME:{orig_actual}:{dest_actual}:{dep_time}:{carrier_code}"
                _merge_offer(offers_map, time_key, "booking", offer_item)
                _merge_offer(offers_map, f"SHORT:{dep_time}:{carrier_code}", "booking", offer_item)

        _save_to_cache(cache_key, offers_map)
    except Exception as exc:
        logger.debug(f"Booking.com Flights live offer fetch error: {exc}")

    return offers_map


def fetch_rapidapi_multi_ota_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
    seat_mode: str = "economy",
    adults: int = 1,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Geriye dönük uyumluluk için Skyscanner servisini çağırır."""
    return fetch_rapidapi_skyscanner_offers(
        orig_codes=orig_codes,
        dest_codes=dest_codes,
        departure_date=departure_date,
        return_date=return_date,
        seat_mode=seat_mode,
        adults=adults,
    )


def fetch_travelpayouts_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Travelpayouts API Token (TRAVELPAYOUTS_API_TOKEN) tanımlıysa sefer bazlı fiyat önbelleğini sorgular.
    """
    offers_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    token = getattr(settings, "TRAVELPAYOUTS_API_TOKEN", "")
    if not token or not orig_codes or not dest_codes:
        return offers_map

    try:
        params = {
            "origin": orig_codes[0],
            "destination": dest_codes[0],
            "departure_at": departure_date,
            "currency": "try",
            "limit": 50,
            "one_way": "false" if return_date else "true",
            "token": token,
        }
        if return_date:
            params["return_at"] = return_date

        resp = requests.get(
            "https://api.travelpayouts.com/aviasales/v3/prices_for_dates",
            params=params,
            timeout=2.5,
        )
        if resp.status_code != 200:
            return offers_map

        items = (resp.json() or {}).get("data") or []
        for row in items:
            airline = str(row.get("airline") or "").upper()
            f_num = str(row.get("flight_number") or "").strip()
            price_val = row.get("price")
            link_path = row.get("link") or ""
            if not airline or not f_num or not price_val:
                continue
            f_key = normalize_flight_key(f"{airline}{f_num}")
            full_link = f"https://www.aviasales.com{link_path}" if link_path.startswith("/") else link_path
            _merge_offer(
                offers_map,
                f_key,
                "aviasales",
                {
                    "name": "Aviasales",
                    "price": float(price_val),
                    "url": full_link,
                    "channel": "aviasales",
                },
            )
    except Exception as exc:
        logger.debug(f"Travelpayouts offer fetch warning: {exc}")

    return offers_map


def fetch_multi_ota_flight_map(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
    seat_mode: str = "economy",
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Tüm aktif Çoklu Acente (Multi-OTA) motorlarını paralel çalıştırır ve
    sefer kodu ('PC2182', 'VF3078' vb.) bazında birleştirilmiş canlı fiyat haritası döndürür.
    KESİN KURAL: Aviasales gibi yabancı/USD diline yönlendiren motorlar devre dışıdır;
    Kiwi.com yalnızca kendi resmi Türkçe doğrudan ödeme motorundan (GraphQL) çekilir.
    """
    combined_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        from app.services.trip_fare_service import fetch_trip_live_offers
        futures = [
            executor.submit(
                fetch_trip_live_offers,
                orig_codes,
                dest_codes,
                departure_date,
            ),
            executor.submit(
                fetch_rapidapi_skyscanner_offers,
                orig_codes,
                dest_codes,
                departure_date,
                return_date,
                seat_mode,
                adults,
            ),
            executor.submit(
                fetch_rapidapi_booking_offers,
                orig_codes,
                dest_codes,
                departure_date,
                return_date,
                seat_mode,
                adults,
            ),
            executor.submit(
                fetch_kiwi_live_offers,
                orig_codes,
                dest_codes,
                departure_date,
                return_date,
                seat_mode,
                adults,
                children,
                infants,
            ),
        ]

        for fut in as_completed(futures):
            try:
                part_map = fut.result() or {}
                for f_key, channels_dict in part_map.items():
                    for ch_name, offer_data in channels_dict.items():
                        _merge_offer(combined_map, f_key, ch_name, offer_data)
            except Exception as exc:
                logger.debug(f"Multi-OTA sub-task warning: {exc}")

    return combined_map
