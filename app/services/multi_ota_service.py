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

from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import logging
import requests
from app.config import settings

logger = logging.getLogger(__name__)

KIWI_GRAPHQL_URL = "https://api.skypicker.com/umbrella/v2/graphql"


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
        flight_bucket[channel] = {
            "name": offer.get("name", channel.capitalize()),
            "price": price_val,
            "url": offer.get("url", ""),
            "channel": channel,
            "dep_time": offer.get("dep_time"),
        }


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
    affil_id = getattr(settings, "KIWI_AFFILIATE_ID", "hakikibilet")

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
            flight_code_num = str(first_seg.get("code") or "").strip()
            carrier = first_seg.get("carrier") or {}
            op_carrier = first_seg.get("operatingCarrier") or {}
            carrier_code = str(carrier.get("code") or "").strip().upper()
            op_carrier_code = str(op_carrier.get("code") or "").strip().upper()

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
            if booking_path.startswith("/"):
                sep = "&" if "?" in booking_path else "?"
                direct_url = f"https://www.kiwi.com{booking_path}{sep}affilid={affil_id}"
            elif booking_path.startswith("http"):
                direct_url = booking_path
            else:
                direct_url = f"https://www.kiwi.com/tr/search/results/{orig_codes[0]}/{dest_codes[0]}/{departure_date}"

            local_time = str(((first_seg.get("source") or {}).get("localTime")) or "")
            dep_hhmm = local_time[11:16] if len(local_time) >= 16 else None

            offer_item = {
                "name": "Kiwi.com",
                "price": price_val,
                "url": direct_url,
                "channel": "kiwi",
                "dep_time": dep_hhmm,
            }

            primary_key = normalize_flight_key(f"{carrier_code}{flight_code_num}")
            _merge_offer(offers_map, primary_key, "kiwi", offer_item)

            # Codeshare (Örn: TK / VF AnadoluJet ortak uçuşları) için ikinci anahtarı da kaydet
            if op_carrier_code and op_carrier_code != carrier_code:
                alt_key = normalize_flight_key(f"{op_carrier_code}{flight_code_num}")
                _merge_offer(offers_map, alt_key, "kiwi", offer_item)

            # Ayrıca saat bazlı yedek eşleştirme anahtarı (TIME:SAW:ADB:06:00:PC)
            src_code = str(((first_seg.get("source") or {}).get("station") or {}).get("code") or "").upper()
            dst_code = str(((first_seg.get("destination") or {}).get("station") or {}).get("code") or "").upper()
            if dep_hhmm and src_code and dst_code:
                time_key = f"TIME:{src_code}:{dst_code}:{dep_hhmm}:{carrier_code}"
                _merge_offer(offers_map, time_key, "kiwi", offer_item)

    except Exception as exc:
        logger.debug(f"Kiwi GraphQL live offer fetch warning: {exc}")

    return offers_map


def fetch_rapidapi_multi_ota_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
    seat_mode: str = "economy",
    adults: int = 1,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    RapidAPI (google-flights2.p.rapidapi.com veya sky-scrapper.p.rapidapi.com) aboneliği aktif olduğunda
    Trip.com, Enuygun, Booking.com vb. acentelerin sefer bazlı canlı fiyatlarını çeker.
    """
    offers_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    api_key = getattr(settings, "RAPIDAPI_FLIGHTS_KEY", "")
    api_host = getattr(settings, "RAPIDAPI_FLIGHTS_HOST", "google-flights2.p.rapidapi.com")
    if not api_key or not orig_codes or not dest_codes:
        return offers_map

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host,
    }

    try:
        params = {
            "departure_id": orig_codes[0],
            "arrival_id": dest_codes[0],
            "outbound_date": departure_date,
            "currency": "TRY",
            "language_code": "tr",
            "country_code": "TR",
            "adults": str(adults),
            "travel_class": "BUSINESS" if seat_mode == "business" else "ECONOMY",
        }
        if return_date:
            params["return_date"] = return_date

        resp = requests.get(
            f"https://{api_host}/api/v1/searchFlights",
            headers=headers,
            params=params,
            timeout=3.0,
        )
        if resp.status_code != 200:
            return offers_map

        payload = resp.json()
        data_block = payload.get("data") or {}
        itineraries = (data_block.get("itineraries") or {}).get("topFlights", []) + (
            (data_block.get("itineraries") or {}).get("otherFlights", [])
        )

        for it in itineraries:
            if not isinstance(it, dict):
                continue
            flights_list = it.get("flights") or []
            if not flights_list:
                continue
            first_leg = flights_list[0] or {}
            f_num = first_leg.get("flight_number") or ""
            f_key = normalize_flight_key(f_num)
            if not f_key:
                continue

            booking_options = it.get("booking_options") or it.get("pricing_options") or []
            for opt in booking_options:
                if not isinstance(opt, dict):
                    continue
                agent_name = str(opt.get("agent_name") or opt.get("provider") or "").strip()
                agent_lower = agent_name.lower()
                opt_price = opt.get("price")
                opt_url = opt.get("booking_url") or opt.get("url") or ""
                if not opt_price or float(opt_price) <= 0:
                    continue

                if "trip.com" in agent_lower or agent_lower == "trip":
                    channel = "trip"
                    display_name = "Trip.com"
                elif "enuygun" in agent_lower or "wingie" in agent_lower:
                    channel = "agency"
                    display_name = "Enuygun"
                elif "kiwi" in agent_lower:
                    channel = "kiwi"
                    display_name = "Kiwi.com"
                elif "booking" in agent_lower:
                    channel = "booking"
                    display_name = "Booking.com"
                else:
                    continue

                _merge_offer(
                    offers_map,
                    f_key,
                    channel,
                    {
                        "name": display_name,
                        "price": float(opt_price),
                        "url": opt_url,
                        "channel": channel,
                    },
                )
    except Exception as exc:
        logger.debug(f"RapidAPI Multi-OTA warning: {exc}")

    return offers_map


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
                "kiwi",
                {
                    "name": "Kiwi / Aviasales",
                    "price": float(price_val),
                    "url": full_link,
                    "channel": "kiwi",
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
    """
    combined_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
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
            executor.submit(
                fetch_rapidapi_multi_ota_offers,
                orig_codes,
                dest_codes,
                departure_date,
                return_date,
                seat_mode,
                adults,
            ),
            executor.submit(
                fetch_travelpayouts_offers,
                orig_codes,
                dest_codes,
                departure_date,
                return_date,
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
