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
            tp = p_obj.get("totalPrice") or p_obj.get("averagePrice")
            if tp and float(tp) > 0:
                candidate_prices.append(float(tp))

        if not candidate_prices:
            continue

        clean_price = float(round(min(candidate_prices)))
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

        # Birincil anahtar: Sefer Kodu (Örn: 'VF3072', 'PC4104' veya aktarmalı 'PC2829PC2190')
        if len(sections) > 1:
            sec_fns = [
                str((s.get("flightInfo") or {}).get("flightNo") or "").replace(" ", "").upper()
                for s in sections
                if (s.get("flightInfo") or {}).get("flightNo")
            ]
            if sec_fns:
                combined_fn = "".join(sec_fns)
                if combined_fn not in offers or clean_price < offers[combined_fn]["trip"]["price"]:
                    offers[combined_fn] = {"trip": item}
        if fn:
            fn_norm = fn.replace(" ", "").upper()
            if fn_norm not in offers or clean_price < offers[fn_norm]["trip"]["price"]:
                offers[fn_norm] = {"trip": item}

        # İkincil anahtar: Sadece direkt seferlerde Kalkış Saati ve Havayolu (Örn: 'TIME:SAW:ADB:00:05:VF')
        if len(sections) == 1 and dep_hm and airline_code:
            t_key = f"TIME:{from_code.upper()}:{to_code.upper()}:{dep_hm}:{airline_code}"
            short_key = f"SHORT:{dep_hm}:{airline_code}"
            if t_key not in offers or clean_price < offers[t_key]["trip"]["price"]:
                offers[t_key] = {"trip": item}
            if short_key not in offers or clean_price < offers[short_key]["trip"]["price"]:
                offers[short_key] = {"trip": item}
            # IST/SAW capraz eslesme destegi (En ucuz teklifi koru)
            if from_code.upper() in ("SAW", "IST"):
                alt_o = "IST" if from_code.upper() == "SAW" else "SAW"
                alt_key = f"TIME:{alt_o}:{to_code.upper()}:{dep_hm}:{airline_code}"
                if alt_key not in offers or clean_price < offers[alt_key]["trip"]["price"]:
                    offers[alt_key] = {"trip": item}
            if to_code.upper() in ("SAW", "IST"):
                alt_d = "IST" if to_code.upper() == "SAW" else "SAW"
                alt_d_key = f"TIME:{from_code.upper()}:{alt_d}:{dep_hm}:{airline_code}"
                if alt_d_key not in offers or clean_price < offers[alt_d_key]["trip"]["price"]:
                    offers[alt_d_key] = {"trip": item}

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
        line_low = line_cur.lower()
        if line_low == "ajet" or line_low.startswith("ajet "):
            carrier = "VF"
        elif "pegasus" in line_low:
            carrier = "PC"
        elif "türk hava yolları" in line_low or "turkish" in line_low:
            carrier = "TK"
        elif "sunexpress" in line_low:
            carrier = "XQ"

        if carrier and i + 1 < len(lines):
            dep_m = re.match(r"^([0-2][0-9]:[0-5][0-9])$", lines[i + 1])
            if dep_m:
                dep_time = dep_m.group(1)
                price = None
                card_window = lines[i + 2 : min(len(lines), i + 20)]
                is_direct_dom = any("aktarmasız" in w.lower() for w in card_window[:10])
                for j in range(i + 2, min(len(lines), i + 20)):
                    jl = lines[j].lower()
                    if j > i + 3 and any(a in jl for a in ["ajet", "pegasus", "türk hava yolları", "sunexpress"]):
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
                if price and is_direct_dom:
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
                    # IST/SAW capraz eslesme destegi (En ucuz teklifi koru)
                    if orig_code.upper() in ("SAW", "IST"):
                        alt_o = "IST" if orig_code.upper() == "SAW" else "SAW"
                        alt_key = f"TIME:{alt_o}:{dest_code.upper()}:{dep_time}:{carrier}"
                        if alt_key not in offers or price < offers[alt_key]["trip"]["price"]:
                            offers[alt_key] = {"trip": item}
                    if dest_code.upper() in ("SAW", "IST"):
                        alt_d = "IST" if dest_code.upper() == "SAW" else "SAW"
                        alt_d_key = f"TIME:{orig_code.upper()}:{alt_d}:{dep_time}:{carrier}"
                        if alt_d_key not in offers or price < offers[alt_d_key]["trip"]["price"]:
                            offers[alt_d_key] = {"trip": item}

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
            f"flighttype=ow&dcity={orig_code.lower()}&acity={dest_code.lower()}&ddate={dep_date}&curr=TRY"
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
            ctx.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
            page = ctx.new_page()

            all_offers: Dict[str, Dict[str, Any]] = {}

            def on_req(req):
                nonlocal captured_payload, captured_headers
                if "FlightListSearch" in req.url and not captured_payload:
                    captured_payload = req.post_data
                    captured_headers = req.headers

            def on_res(res):
                if "FlightMiddleSearch" in res.url or "FlightListSearch" in res.url:
                    try:
                        txt = res.text()
                        for line in txt.splitlines():
                            chunk_str = line[5:].strip() if line.startswith("data:") else line.strip()
                            if chunk_str.startswith("{"):
                                data_chunk = json.loads(chunk_str)
                                parsed = parse_trip_flightlist_json(data_chunk, orig_code, dest_code, dep_date)
                                for pk, pv in parsed.items():
                                    if pk not in all_offers or pv["trip"]["price"] < all_offers[pk]["trip"]["price"]:
                                        all_offers[pk] = pv
                    except Exception:
                        pass

            page.on("request", on_req)
            page.on("response", on_res)
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(5200)

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
                        for line in lines:
                            if line.startswith("data:"):
                                try:
                                    data_chunk = json.loads(line[5:])
                                    parsed = parse_trip_flightlist_json(data_chunk, orig_code, dest_code, dep_date)
                                    for pk, pv in parsed.items():
                                        if pk not in all_offers or pv["trip"]["price"] < all_offers[pk]["trip"]["price"]:
                                            all_offers[pk] = pv
                                except Exception:
                                    pass
                except Exception as api_err:
                    logger.debug(f"Trip API request warning: {api_err}")

            # 2. Tamamlayıcı: FlightMiddleSearch ile yüklenen DOM Text akışını (örn. Sunexpress vb.) birleştir
            body_text = page.inner_text("body")
            b.close()

            if body_text:
                dom_offers = parse_trip_dom_text(body_text, orig_code, dest_code, dep_date)
                for dk, dv in dom_offers.items():
                    if dk not in all_offers or dv["trip"]["price"] < all_offers[dk]["trip"]["price"]:
                        all_offers[dk] = dv

            return all_offers

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
            now_val = time.time()
            _TRIP_MEMORY_CACHE[cache_key] = {"ts": now_val, "data": fresh_offers}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"ts": now_val, "offers": fresh_offers}, f, ensure_ascii=False, indent=2)
            # İstanbul (SAW/IST) ortak havuz önbelleğini de senkronize et
            if orig.upper() in ("SAW", "IST"):
                alt_o = "IST" if orig.upper() == "SAW" else "SAW"
                alt_file = _get_cache_filepath(alt_o, dest, date)
                alt_key = f"{alt_o}_{dest.upper()}_{date}_ow"
                _TRIP_MEMORY_CACHE[alt_key] = {"ts": now_val, "data": fresh_offers}
                with open(alt_file, "w", encoding="utf-8") as f:
                    json.dump({"ts": now_val, "offers": fresh_offers}, f, ensure_ascii=False, indent=2)
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
    Stale-While-Revalidate yaklaşımıyla var olan veriyi anında döndürür, yoksa ilk sorguda çeker.
    """
    if not orig_codes or not dest_codes or not departure_date:
        return {}

    all_offers: Dict[str, Dict[str, Any]] = {}
    now_ts = time.time()
    default_probe = "false" if os.getenv("RENDER") else "true"
    allow_probe = os.getenv("ENABLE_TRIP_BROWSER_PROBE", default_probe).lower() in ("true", "1", "yes")
    probed_city_once = False

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
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        disk_entry = json.load(f)
                    cached_disk = disk_entry.get("offers", {})
                    if cached_disk:
                        _TRIP_MEMORY_CACHE[cache_key] = {"ts": disk_entry.get("ts", now_ts), "data": cached_disk}
                        all_offers.update(cached_disk)
                        age = now_ts - float(disk_entry.get("ts", 0))
                        if age > 3600 and allow_probe and not probed_city_once:
                            probed_city_once = True
                            threading.Thread(
                                target=_bg_refresh_trip,
                                args=(o_code, d_code, departure_date, cache_key, cache_file),
                                daemon=True,
                            ).start()
                        continue
                except Exception as err:
                    logger.debug(f"Disk cache read error for Trip: {err}")

            # 3. Önbellekte hiç yoksa ve yerel/aktif ortamdaysa ilk aramada canlı çek
            if allow_probe and not probed_city_once and not all_offers:
                probed_city_once = True
                try:
                    _bg_refresh_trip(o_code, d_code, departure_date, cache_key, cache_file)
                    if cache_key in _TRIP_MEMORY_CACHE:
                        all_offers.update(_TRIP_MEMORY_CACHE[cache_key]["data"])
                except Exception as e:
                    logger.debug(f"Direct Trip probe error: {e}")

    return all_offers


def parse_kayak_dom_text(
    body_text: str,
    orig_code: str,
    dest_code: str,
    dep_date: str,
    ret_date: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Kayak.com.tr (Booking Holdings) canlı uçuş sonuç sayfasından kalkış saati,
    havayolu ve doğrulanmış TL fiyatlarını ayrıştırır.
    """
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]
    offers: Dict[str, Dict[str, Any]] = {}
    booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")

    for i, line in enumerate(lines):
        m_time = re.match(r"^([0-2][0-9]:[0-5][0-9])\s*[–\-]\s*([0-2][0-9]:[0-5][0-9])", line)
        if not m_time:
            continue
        dep_time = m_time.group(1)
        window = lines[i + 1 : min(len(lines), i + 16)]
        win_joined = " | ".join(window).lower()
        if "aktarma" in win_joined and "direkt" not in win_joined:
            continue

        from_ap = orig_code.upper()
        for w in window[:4]:
            if w.startswith("SAW"):
                from_ap = "SAW"
                break
            elif w.startswith("IST"):
                from_ap = "IST"
                break

        carrier = None
        for w in window:
            wl = w.lower()
            if "pegasus" in wl:
                carrier = "PC"
                break
            elif "ajet" in wl or "anadolujet" in wl:
                carrier = "VF"
                break
            elif "türk hava" in wl or "turkish" in wl:
                carrier = "TK"
                break
            elif "sunexpress" in wl:
                carrier = "XQ"
                break

        if not carrier:
            continue

        price_val = None
        for w in window:
            pm = re.search(r"₺\s*([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)", w)
            if not pm:
                pm = re.search(r"([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)\s*₺", w)
            if pm:
                raw_num = pm.group(1).replace(".", "").replace(",", ".")
                try:
                    val = float(raw_num)
                    if val > 250:
                        price_val = val
                        break
                except ValueError:
                    pass

        if not price_val:
            continue

        if ret_date:
            b_url = f"https://www.kayak.com.tr/flights/{from_ap}-{dest_code.upper()}/{dep_date}/{ret_date}?sort=bestflight_a&aid={booking_aid}"
        else:
            b_url = f"https://www.kayak.com.tr/flights/{from_ap}-{dest_code.upper()}/{dep_date}?sort=bestflight_a&aid={booking_aid}"

        item = {
            "name": "Booking / Kayak",
            "price": price_val,
            "url": b_url,
            "channel": "booking",
            "dep_time": dep_time,
        }
        t_key = f"TIME:{from_ap}:{dest_code.upper()}:{dep_time}:{carrier}"
        s_key = f"SHORT:{dep_time}:{carrier}"
        if t_key not in offers or price_val < offers[t_key]["booking"]["price"]:
            offers[t_key] = {"booking": item}
        if s_key not in offers or price_val < offers[s_key]["booking"]["price"]:
            offers[s_key] = {"booking": item}

    return offers


def probe_kayak_fares_via_browser(
    orig_code: str,
    dest_code: str,
    dep_date: str,
    ret_date: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Headless Edge ile Kayak.com.tr üzerinden canlı uçuş fiyatlarını çeker."""
    try:
        from playwright.sync_api import sync_playwright

        booking_aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
        if ret_date:
            url = f"https://www.kayak.com.tr/flights/{orig_code.upper()}-{dest_code.upper()}/{dep_date}/{ret_date}?sort=bestflight_a&aid={booking_aid}"
        else:
            url = f"https://www.kayak.com.tr/flights/{orig_code.upper()}-{dest_code.upper()}/{dep_date}?sort=bestflight_a&aid={booking_aid}"

        with sync_playwright() as p:
            b = p.chromium.launch(
                channel="msedge",
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            ctx = b.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
                locale="tr-TR",
                viewport={"width": 1366, "height": 768},
            )
            ctx.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(5200)
            body_text = page.inner_text("body")
            b.close()

        if body_text:
            return parse_kayak_dom_text(body_text, orig_code, dest_code, dep_date, ret_date)
    except Exception as exc:
        logger.debug(f"Kayak browser probe warning: {exc}")
    return {}


def fetch_kayak_live_offers(
    orig_codes: List[str],
    dest_codes: List[str],
    departure_date: str,
    return_date: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Kayak / Booking canlı uçuş tekliflerini önbellekten veya tarayıcıdan getirir."""
    if not orig_codes or not dest_codes or not departure_date:
        return {}

    all_offers: Dict[str, Dict[str, Any]] = {}
    now_ts = time.time()
    default_probe = "false" if os.getenv("RENDER") else "true"
    allow_probe = os.getenv("ENABLE_TRIP_BROWSER_PROBE", default_probe).lower() in ("true", "1", "yes")
    probed_once = False

    for orig_raw in orig_codes:
        o_code = orig_raw.strip().upper()
        for dest_raw in dest_codes:
            d_code = dest_raw.strip().upper()
            cache_key = f"KAYAK_{o_code}_{d_code}_{departure_date}_{return_date or 'ow'}"
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

            if cache_key in _TRIP_MEMORY_CACHE:
                entry = _TRIP_MEMORY_CACHE[cache_key]
                if now_ts - entry["ts"] < CACHE_TTL_SECONDS:
                    all_offers.update(entry["data"])
                    continue

            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        disk_entry = json.load(f)
                    cached_disk = disk_entry.get("offers", {})
                    if cached_disk:
                        _TRIP_MEMORY_CACHE[cache_key] = {"ts": disk_entry.get("ts", now_ts), "data": cached_disk}
                        all_offers.update(cached_disk)
                        continue
                except Exception:
                    pass

            if allow_probe and not probed_once:
                probed_once = True
                fresh = probe_kayak_fares_via_browser(o_code, d_code, departure_date, return_date)
                if fresh:
                    _TRIP_MEMORY_CACHE[cache_key] = {"ts": now_ts, "data": fresh}
                    all_offers.update(fresh)
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump({"ts": now_ts, "offers": fresh}, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

    return all_offers

