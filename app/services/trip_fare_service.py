"""
Trip.com Canlı Fiyat Keşif ve Entegrasyon Servisi (Trip.com Live Fare Probe & Parser)

Bu servis, Trip.com'un web/mobil arama motorundan gerçek zamanlı acente fiyatlarını
ve özel indirimli biletlerini (ör. AJet 1.371 TL sübvansiyonlu biletleri) çeker.
- Her sefer bağımsız değerlendirilir; asla toptancı varsayım yapılmaz.
- Çekilen doğrulanmış canlı fiyatlar 'multi_ota_service' üzerinden bilet karşılaştırma motoruna iletilir.
- 15 dakikalık akıllı dosya ve bellek önbelleği (Cache) ile sunucu yükünü minimize eder.
"""

import os
import json
import time
import logging
import re
from typing import Dict, Any, List, Optional
from app.config import settings
from app.cities import find_city

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "trip_fare_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

import threading

_TRIP_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 7200  # 2 Saat (Trip.com Anti-Bot / WhaleGuard koruması ve güncel fiyat dengesi)
_PROBE_LOCK = threading.Lock()
_ACTIVE_PROBES: set = set()


def _get_cache_filepath(orig_code: str, dest_code: str, dep_date: str, ret_date: Optional[str] = None) -> str:
    ret_part = f"_{ret_date}" if ret_date else ""
    filename = f"{orig_code.upper()}_{dest_code.upper()}_{dep_date}{ret_part}.json"
    return os.path.join(CACHE_DIR, filename)


def parse_trip_flightlist_json(
    raw_data: Dict[str, Any],
    from_code: str,
    to_code: str,
    dep_date: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Trip.com FlightListSearch JSON yanıtını ayrıştırır ve sefer anahtarlarına göre
    (ör. 'VF3072', 'PC2184' ve 'TIME:SAW:ADB:00:05:VF') doğrulanmış canlı teklifleri döndürür.
    """
    offers: Dict[str, Dict[str, Any]] = {}
    itins = raw_data.get("itineraryList") or []
    trip_alliance = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
    trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")
    aff_param = f"&Allianceid={trip_alliance}&SID={trip_sid}" if trip_alliance else ""

    for it in itins:
        journeys = it.get("journeyList") or []
        if not journeys:
            continue
        sections = journeys[0].get("transSectionList") or []
        if not sections:
            continue
        first_sec = sections[0]
        fl_info = first_sec.get("flightInfo") or {}
        fn = str(fl_info.get("flightNo") or "").strip().upper()
        airline_code = str(fl_info.get("airlineCode") or "").strip().upper()
        dep_dt_str = str(first_sec.get("departDateTime") or "")
        dep_hm = dep_dt_str[11:16] if len(dep_dt_str) >= 16 else None

        policies = it.get("policies") or []
        if not policies:
            continue

        candidate_prices = []
        for pol in policies:
            p_obj = pol.get("price") or {}
            # 1. discountAverage (Özel İndirimli / Kampanyalı Fiyat)
            more_p = p_obj.get("morePrice") or {}
            if more_p.get("discountAverage") and float(more_p["discountAverage"]) > 0:
                candidate_prices.append(float(more_p["discountAverage"]))
            # 2. totalPrice / averagePrice
            tp = p_obj.get("totalPrice") or p_obj.get("averagePrice")
            if tp and float(tp) > 0:
                candidate_prices.append(float(tp))
            # 3. adult salePrice + tax
            adult_p = p_obj.get("adult") or {}
            if adult_p.get("totalPrice") and float(adult_p["totalPrice"]) > 0:
                candidate_prices.append(float(adult_p["totalPrice"]))

        if not candidate_prices:
            continue

        clean_price = round(min(candidate_prices), 2)
        airline_filter = f"&airline={airline_code}&airlineCode={airline_code}" if airline_code else ""
        
        orig_c = find_city(from_code)
        dest_c = find_city(to_code)
        orig_slug = orig_c.get("slug") if orig_c else from_code.lower()
        dest_slug = dest_c.get("slug") if dest_c else to_code.lower()
        
        trip_url = (
            f"https://tr.trip.com/flights/{orig_slug}-to-{dest_slug}/tickets-{from_code.lower()}-{to_code.lower()}?"
            f"flighttype=ow&dcity={from_code.lower()}&acity={to_code.lower()}&ddate={dep_date}"
            f"&curr=TRY{airline_filter}{aff_param}"
        )

        item = {
            "name": "Trip.com",
            "price": clean_price,
            "url": trip_url,
            "channel": "trip",
            "dep_time": dep_hm,
        }

        # Birincil anahtar: Sefer Kodu (Örn: 'VF3072', 'PC4104')
        if fn:
            fn_norm = fn.replace(" ", "").upper()
            if fn_norm not in offers or clean_price < offers[fn_norm]["trip"]["price"]:
                offers[fn_norm] = {"trip": item}

        # İkincil anahtar: Kalkış Saati ve Havayolu (Örn: 'TIME:SAW:ADB:00:05:VF')
        if dep_hm and airline_code:
            t_key = f"TIME:{from_code.upper()}:{to_code.upper()}:{dep_hm}:{airline_code}"
            short_key = f"SHORT:{dep_hm}:{airline_code}"
            if t_key not in offers or clean_price < offers[t_key]["trip"]["price"]:
                offers[t_key] = {"trip": item}
            if short_key not in offers or clean_price < offers[short_key]["trip"]["price"]:
                offers[short_key] = {"trip": item}
            # IST/SAW capraz eslesme destegi
            if from_code.upper() in ("SAW", "IST"):
                alt_o = "IST" if from_code.upper() == "SAW" else "SAW"
                offers[f"TIME:{alt_o}:{to_code.upper()}:{dep_hm}:{airline_code}"] = {"trip": item}
            if to_code.upper() in ("SAW", "IST"):
                alt_d = "IST" if to_code.upper() == "SAW" else "SAW"
                offers[f"TIME:{from_code.upper()}:{alt_d}:{dep_hm}:{airline_code}"] = {"trip": item}

    return offers


def parse_trip_dom_text(body_text: str, orig_code: str, dest_code: str, dep_date: str) -> Dict[str, Dict[str, Any]]:
    """
    Trip.com'un dinamik yüklenen sayfasından havayolu, kalkış saati ve indirimli net TL fiyatlarını
    ayrıştırır ve biletleme motorunun eşleşebileceği formatta sunar.
    """
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]
    offers: Dict[str, Dict[str, Any]] = {}

    orig_c = find_city(orig_code)
    dest_c = find_city(dest_code)
    orig_slug = orig_c.get("slug") if orig_c else orig_code.lower()
    dest_slug = dest_c.get("slug") if dest_c else dest_code.lower()

    trip_alliance = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
    trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")
    aff_param = f"&Allianceid={trip_alliance}&SID={trip_sid}" if trip_alliance else ""

    for i in range(len(lines)):
        carrier = None
        line_cur = lines[i]
        if line_cur == "AJet" or "AJet " in line_cur:
            carrier = "VF"
        elif "Pegasus" in line_cur:
            carrier = "PC"
        elif "Türk Hava Yolları" in line_cur or "Turkish" in line_cur:
            carrier = "TK"
        elif "SunExpress" in line_cur:
            carrier = "XQ"

        if carrier and i + 1 < len(lines):
            dep_m = re.match(r"^([0-2][0-9]:[0-5][0-9])$", lines[i + 1])
            if dep_m:
                dep_time = dep_m.group(1)
                price = None
                for j in range(i + 2, min(len(lines), i + 20)):
                    if j > i + 3 and any(a in lines[j] for a in ["AJet", "Pegasus", "Türk Hava Yolları", "SunExpress"]):
                        break
                    p_match = re.search(r"([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+)\s*TL", lines[j])
                    if p_match:
                        val_str = p_match.group(1).replace(".", "").replace(",", ".")
                        try:
                            val = float(val_str)
                            if val > 200:
                                price = val
                                break
                        except ValueError:
                            pass
                if price:
                    trip_flight_url = (
                        f"https://tr.trip.com/flights/{orig_slug}-to-{dest_slug}/tickets-{orig_code.lower()}-{dest_code.lower()}?"
                        f"flighttype=ow&dcity={orig_code.lower()}&acity={dest_code.lower()}&ddate={dep_date}&curr=TRY&airline={carrier}&airlineCode={carrier}{aff_param}"
                    )
                    item = {
                        "name": "Trip.com",
                        "price": price,
                        "url": trip_flight_url,
                        "channel": "trip",
                        "dep_time": dep_time,
                    }
                    t_key = f"TIME:{orig_code.upper()}:{dest_code.upper()}:{dep_time}:{carrier}"
                    short_key = f"SHORT:{dep_time}:{carrier}"
                    if t_key not in offers or price < offers[t_key]["trip"]["price"]:
                        offers[t_key] = {"trip": item}
                    if short_key not in offers or price < offers[short_key]["trip"]["price"]:
                        offers[short_key] = {"trip": item}
                    # IST/SAW capraz eslesme destegi
                    if orig_code.upper() in ("SAW", "IST"):
                        alt_o = "IST" if orig_code.upper() == "SAW" else "SAW"
                        offers[f"TIME:{alt_o}:{dest_code.upper()}:{dep_time}:{carrier}"] = {"trip": item}
                    if dest_code.upper() in ("SAW", "IST"):
                        alt_d = "IST" if dest_code.upper() == "SAW" else "SAW"
                        offers[f"TIME:{orig_code.upper()}:{alt_d}:{dep_time}:{carrier}"] = {"trip": item}

    return offers


def probe_trip_fares_via_browser(orig_code: str, dest_code: str, dep_date: str) -> Dict[str, Dict[str, Any]]:
    """
    Playwright (Edge) kullanarak Trip.com'dan canlı fırsatları (Pegasus, AJet, THY vb.)
    FlightListSearchSSE JSON veri akışından ve sayfa DOM'undan çeker.
    """
    try:
        from playwright.sync_api import sync_playwright

        orig_c = find_city(orig_code)
        dest_c = find_city(dest_code)
        orig_slug = orig_c.get("slug") if orig_c else orig_code.lower()
        dest_slug = dest_c.get("slug") if dest_c else dest_code.lower()

        trip_alliance = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
        trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")
        aff_param = f"&Allianceid={trip_alliance}&SID={trip_sid}" if trip_alliance else ""

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]
        url = (
            f"https://tr.trip.com/flights/{orig_slug}-to-{dest_slug}/tickets-{orig_code.lower()}-{dest_code.lower()}?"
            f"flighttype=ow&dcity={orig_code.lower()}&acity={dest_code.lower()}&ddate={dep_date}&curr=TRY{aff_param}"
        )

        captured_payload = None
        captured_headers = None

        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True, args=args)
            ctx = b.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
                viewport={"width": 1366, "height": 768},
                locale="tr-TR",
            )
            page = ctx.new_page()

            def on_req(req):
                nonlocal captured_payload, captured_headers
                if "FlightListSearch" in req.url and not captured_payload:
                    captured_payload = req.post_data
                    captured_headers = req.headers

            page.on("request", on_req)
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3500)

            # 1. Öncelik: JSON API (FlightListSearchSSE) yanıtını parse et
            if captured_payload:
                try:
                    api_res = ctx.request.post(
                        "https://tr.trip.com/restapi/soa2/27015/FlightListSearchSSE",
                        data=captured_payload,
                        headers=captured_headers,
                        timeout=12000,
                    )
                    if api_res.status == 200:
                        lines = api_res.text().splitlines()
                        all_offers: Dict[str, Dict[str, Any]] = {}
                        for line in lines:
                            if line.startswith("data:"):
                                try:
                                    data_chunk = json.loads(line[5:])
                                    parsed = parse_trip_flightlist_json(data_chunk, orig_code, dest_code, dep_date)
                                    all_offers.update(parsed)
                                except Exception:
                                    pass
                        if all_offers:
                            b.close()
                            return all_offers
                except Exception as api_err:
                    logger.debug(f"Trip API request warning: {api_err}")

            # 2. Öncelik: DOM Text akışından parse et
            body_text = page.inner_text("body")
            b.close()

            if body_text:
                return parse_trip_dom_text(body_text, orig_code, dest_code, dep_date)

    except Exception as exc:
        logger.warning(f"Trip.com browser probe warning: {exc}")

    return {}


def _bg_refresh_trip(orig: str, dest: str, date: str, cache_key: str, cache_file: str):
    """Arka planda Trip.com canlı tekliflerini yeniler ve önbelleğe yazar (Çift tarayıcı kilidi korumalı)."""
    with _PROBE_LOCK:
        if cache_key in _ACTIVE_PROBES:
            return
        _ACTIVE_PROBES.add(cache_key)

    try:
        fresh_offers = probe_trip_fares_via_browser(orig, dest, date)
        if fresh_offers:
            _TRIP_MEMORY_CACHE[cache_key] = {"ts": time.time(), "data": fresh_offers}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), "offers": fresh_offers}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug(f"Background Trip refresh error: {e}")
    finally:
        with _PROBE_LOCK:
            _ACTIVE_PROBES.discard(cache_key)


def fetch_trip_live_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Belirli bir hat ve tarih için Trip.com canlı fiyatlarını çeker.
    Stale-While-Revalidate yaklaşımıyla var olan veriyi anında döndürür, arka planda günceller.
    """
    if not orig_codes or not dest_codes or not departure_date:
        return {}

    all_offers: Dict[str, Dict[str, Any]] = {}
    now_ts = time.time()

    for orig_raw in orig_codes:
        o_code = orig_raw.strip().upper()
        for dest_raw in dest_codes:
            d_code = dest_raw.strip().upper()
            cache_key = f"{o_code}_{d_code}_{departure_date}_{return_date or 'ow'}"

            # 1. Bellek Önbelleği (RAM Cache)
            if cache_key in _TRIP_MEMORY_CACHE:
                entry = _TRIP_MEMORY_CACHE[cache_key]
                if now_ts - entry["ts"] < CACHE_TTL_SECONDS:
                    all_offers.update(entry["data"])
                    continue

            # 2. Disk Önbelleği (File Cache)
            cache_file = _get_cache_filepath(o_code, d_code, departure_date)
            cached_disk = None
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        disk_entry = json.load(f)
                    cached_disk = disk_entry.get("offers", {})
                    age = now_ts - disk_entry.get("ts", 0)
                    if age < CACHE_TTL_SECONDS and cached_disk:
                        _TRIP_MEMORY_CACHE[cache_key] = {"ts": disk_entry.get("ts", now_ts), "data": cached_disk}
                        all_offers.update(cached_disk)
                        # 30 dakikadan eskiyse arka planda sessizce taze guncelleme baslat
                        if age > 1800:
                            threading.Thread(
                                target=_bg_refresh_trip,
                                args=(o_code, d_code, departure_date, cache_key, cache_file),
                                daemon=True,
                            ).start()
                        continue
                except Exception as err:
                    logger.debug(f"Disk cache read error for Trip: {err}")

            # 3. Canlı Sorgu (Disk cache yoksa doğrudan çek)
            try:
                parsed_offers = probe_trip_fares_via_browser(o_code, d_code, departure_date)
                if parsed_offers:
                    _TRIP_MEMORY_CACHE[cache_key] = {"ts": time.time(), "data": parsed_offers}
                    all_offers.update(parsed_offers)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump({"ts": time.time(), "offers": parsed_offers}, f, ensure_ascii=False, indent=2)
                elif cached_disk:
                    all_offers.update(cached_disk)
            except Exception as e:
                logger.debug(f"Direct Trip probe error: {e}")
                if cached_disk:
                    all_offers.update(cached_disk)

    return all_offers

