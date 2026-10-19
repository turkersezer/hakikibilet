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
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "trip_fare_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

_TRIP_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1 Saat güncellik


def _get_cache_filepath(orig_code: str, dest_code: str, dep_date: str) -> str:
    filename = f"{orig_code.upper()}_{dest_code.upper()}_{dep_date}.json"
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
        price_obj = policies[0].get("price") or {}
        total_price = price_obj.get("totalPrice") or price_obj.get("averagePrice")
        if not total_price or float(total_price) <= 0:
            continue

        clean_price = round(float(total_price), 2)
        airline_filter = f"&airline={airline_code}&airlineCode={airline_code}" if airline_code else ""
        trip_url = (
            f"https://tr.trip.com/flights/search?"
            f"dcity={from_code.lower()}&acity={to_code.lower()}&ddate={dep_date}"
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
            if t_key not in offers or clean_price < offers[t_key]["trip"]["price"]:
                offers[t_key] = {"trip": item}

    return offers


def probe_trip_fares_via_browser(orig_code: str, dest_code: str, dep_date: str) -> Optional[Dict[str, Any]]:
    """
    Playwright Stealth (Edge) kullanarak Trip.com'dan canlı arama yapar ve JSON sonucunu döner.
    """
    try:
        from playwright.sync_api import sync_playwright

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]
        url = (
            f"https://tr.trip.com/flights/search?"
            f"flighttype=ow&dcity={orig_code.lower()}&acity={dest_code.lower()}&ddate={dep_date}&curr=TRY"
        )
        captured_data = []

        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True, args=args)
            ctx = b.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
                viewport={"width": 1366, "height": 768},
                locale="tr-TR",
            )
            ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = ctx.new_page()

            def on_resp(r):
                if "FlightListSearch" in r.url:
                    try:
                        txt = r.text()
                        if txt and "itineraryList" in txt:
                            captured_data.append(json.loads(txt))
                    except Exception:
                        pass

            page.on("response", on_resp)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)

            # Arama butonu tıkla
            try:
                btn = page.locator('button:has-text("Ara"), div:has-text("Ara")').first
                if btn:
                    btn.click()
            except Exception:
                pass

            # Yanıtın gelmesi için kısa bekleme
            for _ in range(8):
                if captured_data:
                    break
                page.wait_for_timeout(1000)

            b.close()

        if captured_data:
            return captured_data[0]
    except Exception as exc:
        logger.warning(f"Trip.com browser probe warning: {exc}")

    return None


def fetch_trip_live_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Belirli bir hat ve tarih için Trip.com canlı fiyatlarını çeker.
    Önce bellek ve disk önbelleğine bakar; yoksa anlık canlı yakalama yapar.
    """
    if not orig_codes or not dest_codes or not departure_date:
        return {}

    all_offers: Dict[str, Dict[str, Any]] = {}
    now_ts = time.time()

    for orig_raw in orig_codes:
        o_code = orig_raw.strip().upper()
        for dest_raw in dest_codes:
            d_code = dest_raw.strip().upper()
            cache_key = f"{o_code}_{d_code}_{departure_date}"

            # 1. Bellek Önbelleği (RAM Cache)
            if cache_key in _TRIP_MEMORY_CACHE:
                entry = _TRIP_MEMORY_CACHE[cache_key]
                if now_ts - entry["ts"] < CACHE_TTL_SECONDS:
                    all_offers.update(entry["data"])
                    continue

            # 2. Disk Önbelleği (File Cache)
            cache_file = _get_cache_filepath(o_code, d_code, departure_date)
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        disk_entry = json.load(f)
                    if now_ts - disk_entry.get("ts", 0) < CACHE_TTL_SECONDS:
                        parsed_offers = disk_entry.get("offers", {})
                        _TRIP_MEMORY_CACHE[cache_key] = {"ts": disk_entry.get("ts", now_ts), "data": parsed_offers}
                        all_offers.update(parsed_offers)
                        continue
                except Exception as err:
                    logger.debug(f"Disk cache read error for Trip: {err}")

            # 3. Canlı Sorgu (Arka planda asenkron çalıştır, kullanıcı aramasını bloke etme)
            def _bg_probe(orig=o_code, dest=d_code, date=departure_date, c_key=cache_key, c_file=cache_file):
                try:
                    raw_json = probe_trip_fares_via_browser(orig, dest, date)
                    if raw_json:
                        parsed_offers = parse_trip_flightlist_json(raw_json, orig, dest, date)
                        if parsed_offers:
                            _TRIP_MEMORY_CACHE[c_key] = {"ts": time.time(), "data": parsed_offers}
                            with open(c_file, "w", encoding="utf-8") as f:
                                json.dump({"ts": time.time(), "offers": parsed_offers}, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.debug(f"Background Trip probe error: {e}")

            import threading
            threading.Thread(target=_bg_probe, daemon=True).start()

    return all_offers
