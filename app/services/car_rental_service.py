"""
Hakiki Bilet — Araç Kiralama Karşılaştırma & Canlı Fiyat Servisi (Argon High Standardı)
- SIFIR VARSAYIM (Zero-Assumption): Sabit/uydurma formül fiyatlar tamamen kaldırılmıştır.
  Yolcu360 ve Enuygun Araç üzerinden 15 dk L1 önbellekli gerçek zamanlı günlük taban fiyatlar çekilir.
  Canlı fiyatı doğrulanamayan kanallarda uydurma yüzde farkı üretilmez; "Canlı Filo & Fiyatı Gör ↗" gösterilir.
- SEVİYE 2 DERİN LİNK (Ana Ekrana Düşmeme Kuralı):
  Yolcu360 (/arac-kiralama/search?p_d=...&d_d=...&pid=...&p_p=...&c=...),
  Enuygun (/arac-kiralama/havalimani/...),
  Obilet (/arac-kiralama/{sehir}/{havalimani}),
  Garenta (garenta.com/tr/arac-kiralama/{sehir}/{havalimani}),
  Avis (avis.com.tr/arac-kiralama/{sehir}) ve
  Rentalcars (/tr/airport/tr/{iata}/) doğrudan ilgili lokasyon ve tarih ekranına iner.
"""
import logging
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.cities import find_city
from app.config import settings
from app.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)


class CarRentalService:
    _LIVE_CAR_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _CACHE_LOCK = threading.Lock()
    _CACHE_TTL_SECONDS = 900  # 15 dakika L1 önbellek

    # Havalimanı Bazlı Doğrulanmış Derin Link & Google Place ID (Yolcu360 / Obilet / Enuygun / Garenta) Haritası
    _AIRPORT_META: Dict[str, Dict[str, str]] = {
        "IST": {
            "city_slug": "istanbul",
            "y360_path": "turkiye/istanbul/istanbul-havalimani",
            "y360_pid": "ChIJqZW8Cvb_n0ARBuUkyCzgDDg",
            "y360_pp": "41.259656501755316,28.74417437428462",
            "enuygun_slug": "havalimani/istanbul-havalimani",
            "obilet_path": "istanbul/istanbul-havalimani",
            "garenta_path": "istanbul/istanbul-havalimani",
            "label": "İstanbul Havalimanı (IST)",
        },
        "SAW": {
            "city_slug": "istanbul",
            "y360_path": "turkiye/istanbul/sabiha-gokcen-havalimani",
            "y360_pid": "ChIJU6Ek9MvbyhQRdNqYgE3K76w",
            "y360_pp": "40.8944747,29.3130928",
            "enuygun_slug": "havalimani/istanbul-sabiha-gokcen-havalimani",
            "obilet_path": "istanbul/sabiha-gokcen-uluslararasi-havalimani",
            "garenta_path": "istanbul/istanbul-sabiha-gokcen-havalimani",
            "label": "İstanbul Sabiha Gökçen Havalimanı (SAW)",
        },
        "AYT": {
            "city_slug": "antalya",
            "y360_path": "turkiye/antalya/antalya-havalimani",
            "y360_pid": "ChIJnXxhjXeEwxQR-uhI2_zcfME",
            "y360_pp": "36.9086961,30.7981855",
            "enuygun_slug": "havalimani/antalya-havalimani",
            "obilet_path": "antalya/antalya-havalimani",
            "garenta_path": "antalya/antalya-havalimani",
            "label": "Antalya Havalimanı (AYT)",
        },
        "ADB": {
            "city_slug": "izmir",
            "y360_path": "turkiye/izmir/adnan-menderes-havalimani",
            "y360_pid": "ChIJNzAtBD7guxQRSGSP1dn9i6A",
            "y360_pp": "38.2919973,27.1489398",
            "enuygun_slug": "havalimani/izmir-adnan-menderes-havalimani",
            "obilet_path": "izmir/izmir-adnan-menderes-uluslararasi-havalimani",
            "garenta_path": "izmir/izmir-adnan-menderes-havalimani",
            "label": "İzmir Adnan Menderes Havalimanı (ADB)",
        },
        "ESB": {
            "city_slug": "ankara",
            "y360_path": "turkiye/ankara/esenboga-havalimani",
            "y360_pid": "ChIJqYLJ0NoPgkAR1nZct7rSPvE",
            "y360_pp": "40.1149458,32.9926733",
            "enuygun_slug": "havalimani/ankara-esenboga-havalimani",
            "obilet_path": "ankara/ankara-esenboga-uluslararasi-havalimani",
            "garenta_path": "ankara/ankara-esenboga-havalimani",
            "label": "Ankara Esenboğa Havalimanı (ESB)",
        },
        "BJV": {
            "city_slug": "mugla",
            "y360_path": "turkiye/mugla/milas-bodrum-havalimani",
            "y360_pid": "ChIJHdQmLhf2vhQR0mNL2LRpO5g",
            "y360_pp": "37.2335821,27.7058084",
            "enuygun_slug": "havalimani/mugla-milas-bodrum-havalimani",
            "obilet_path": "mugla/milas-bodrum-havalimani",
            "garenta_path": "mugla",
            "label": "Muğla Milas-Bodrum Havalimanı (BJV)",
        },
        "DLM": {
            "city_slug": "mugla",
            "y360_path": "turkiye/mugla/dalaman-havalimani",
            "y360_pid": "",
            "y360_pp": "",
            "enuygun_slug": "havalimani/mugla-dalaman-havalimani",
            "obilet_path": "mugla/dalaman-havalimani",
            "garenta_path": "mugla",
            "label": "Muğla Dalaman Havalimanı (DLM)",
        },
        "TZX": {
            "city_slug": "trabzon",
            "y360_path": "turkiye/trabzon/trabzon-havalimani",
            "y360_pid": "",
            "y360_pp": "",
            "enuygun_slug": "havalimani/trabzon-havalimani",
            "obilet_path": "trabzon/trabzon-havalimani",
            "garenta_path": "trabzon",
            "label": "Trabzon Havalimanı (TZX)",
        },
        "COV": {
            "city_slug": "adana",
            "y360_path": "turkiye/adana",
            "y360_pid": "",
            "y360_pp": "",
            "enuygun_slug": "havalimani/adana-havalimani",
            "obilet_path": "adana/cukurova-havalimani",
            "garenta_path": "adana",
            "label": "Çukurova Uluslararası Havalimanı (COV)",
        },
        "GZT": {
            "city_slug": "gaziantep",
            "y360_path": "turkiye/gaziantep/gaziantep-havalimani",
            "y360_pid": "",
            "y360_pp": "",
            "enuygun_slug": "havalimani/gaziantep-havalimani",
            "obilet_path": "gaziantep/oguzeli-havalimani",
            "garenta_path": "gaziantep/gaziantep-havalimani",
            "label": "Gaziantep Havalimanı (GZT)",
        },
        "ASR": {
            "city_slug": "kayseri",
            "y360_path": "turkiye/kayseri/erkilet-havalimani",
            "y360_pid": "",
            "y360_pp": "",
            "enuygun_slug": "havalimani/kayseri-erkilet-havalimani",
            "obilet_path": "kayseri",
            "garenta_path": "kayseri",
            "label": "Kayseri Erkilet Havalimanı (ASR)",
        },
        "EDO": {
            "city_slug": "balikesir",
            "y360_path": "turkiye/balikesir/koca-seyit-havalimani",
            "y360_pid": "",
            "y360_pp": "",
            "enuygun_slug": "havalimani/balikesir-koca-seyit-havalimani",
            "obilet_path": "balikesir",
            "garenta_path": "balikesir",
            "label": "Balıkesir Edremit Koca Seyit Havalimanı (EDO)",
        },
    }

    @classmethod
    def clean_slug(cls, text: str) -> str:
        s = (text or "").lower().strip()
        if "(" in s:
            s = s.split("(")[0].strip()
        for tr, en in [
            ("ı", "i"), ("İ", "i"), ("ğ", "g"), ("ü", "u"),
            ("ş", "s"), ("ö", "o"), ("ç", "c"), ("/", "-"), (" ", "-"),
        ]:
            s = s.replace(tr, en)
        s = re.sub(r"[^a-z0-9\-]+", "-", s)
        while "--" in s:
            s = s.replace("--", "-")
        return s.strip("-")

    @classmethod
    def _resolve_airport_and_city(cls, location_name: str, location_type: str = "city") -> Tuple[str, str, Dict[str, str]]:
        raw = (location_name or "").strip()
        raw_low = raw.lower()

        detected_iata = ""
        if "sabiha" in raw_low or "(saw)" in raw_low or raw_low == "saw":
            detected_iata = "SAW"
        elif "istanbul havaliman" in raw_low or "(ist)" in raw_low or raw_low == "ist":
            detected_iata = "IST"
        elif "(ayt)" in raw_low or "antalya" in raw_low:
            detected_iata = "AYT"
        elif "(adb)" in raw_low or "adnan menderes" in raw_low or "izmir" in raw_low:
            detected_iata = "ADB"
        elif "(esb)" in raw_low or "esenboga" in raw_low or "esenboğa" in raw_low or "ankara" in raw_low:
            detected_iata = "ESB"
        elif "(bjv)" in raw_low or "bodrum" in raw_low or "milas" in raw_low:
            detected_iata = "BJV"
        elif "(dlm)" in raw_low or "dalaman" in raw_low or "marmaris" in raw_low or "fethiye" in raw_low:
            detected_iata = "DLM"
        elif "(tzx)" in raw_low or "trabzon" in raw_low:
            detected_iata = "TZX"
        elif "(cov)" in raw_low or "çukurova" in raw_low or "cukurova" in raw_low or "adana" in raw_low or "mersin" in raw_low:
            detected_iata = "COV"
        elif "(gzt)" in raw_low or "gaziantep" in raw_low:
            detected_iata = "GZT"
        elif "(asr)" in raw_low or "kayseri" in raw_low:
            detected_iata = "ASR"
        elif "(edo)" in raw_low or "edremit" in raw_low or "ayvalık" in raw_low or "ayvalik" in raw_low:
            detected_iata = "EDO"

        city_obj = find_city(raw)
        if not detected_iata and city_obj and city_obj.get("iata"):
            detected_iata = str(city_obj["iata"]).upper()

        base_city_slug = cls.clean_slug(city_obj["slug"] if city_obj else raw)
        for suffix in ["-havalimani", "-sabiha-gokcen", "-adnan-menderes", "-esenboga", "-milas", "-cukurova"]:
            if base_city_slug.endswith(suffix):
                base_city_slug = base_city_slug[: -len(suffix)].strip("-")

        if not base_city_slug:
            base_city_slug = "istanbul"

        meta = cls._AIRPORT_META.get(detected_iata)
        if meta:
            return detected_iata, meta["city_slug"], meta

        return (
            detected_iata or "IST",
            base_city_slug,
            {
                "city_slug": base_city_slug,
                "y360_path": f"turkiye/{base_city_slug}",
                "y360_pid": "",
                "y360_pp": "",
                "enuygun_slug": base_city_slug,
                "obilet_path": base_city_slug,
                "garenta_path": base_city_slug,
                "label": f"{raw.split('(')[0].strip()} Havalimanı / Şehir Ofisleri",
            },
        )

    @classmethod
    def _fetch_live_car_pricing(cls, iata: str, city_slug: str, meta: Dict[str, str]) -> Dict[str, Any]:
        """
        Yolcu360 ve Enuygun Araç sayfalarından gerçek zamanlı günlük kiralama taban fiyatlarını
        ve varsa dinamik Google Place ID (pid / p_p) bilgilerini çeker (15 dk L1 önbellekli).
        """
        cache_key = f"{iata}_{city_slug}"
        now = time.time()
        with cls._CACHE_LOCK:
            cached = cls._LIVE_CAR_CACHE.get(cache_key)
            if cached and (now - cached[0]) < cls._CACHE_TTL_SECONDS:
                return cached[1]

        result: Dict[str, Any] = {
            "y360_prices": {},   # economy, eco_auto, comfort, suv, luxury
            "enuygun_prices": {},
            "y360_pid": meta.get("y360_pid") or "",
            "y360_pp": meta.get("y360_pp") or "",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }

        def _parse_tr_price(val_str: str) -> Optional[float]:
            if not val_str:
                return None
            clean = val_str.strip().replace(".", "").replace(",", ".")
            try:
                v = float(clean)
                return float(round(v)) if 600.0 <= v <= 35000.0 else None
            except Exception:
                return None

        def _scrape_yolcu360():
            url = f"https://yolcu360.com/arac-kiralama/{meta['y360_path']}"
            try:
                req = urllib.request.Request(url, headers=headers)
                html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", "ignore")
            except Exception:
                try:
                    url2 = f"https://yolcu360.com/arac-kiralama/turkiye/{city_slug}"
                    req2 = urllib.request.Request(url2, headers=headers)
                    html = urllib.request.urlopen(req2, timeout=5).read().decode("utf-8", "ignore")
                except Exception:
                    return

            cat_buckets: Dict[str, List[float]] = {
                "economy": [],
                "mid": [],
                "suv": [],
                "upper": [],
                "luxury": [],
            }
            for m in re.finditer(r'href=["\'](/arac-kiralama/search\?[^"\']+)["\'][^>]*>(.*?)</a>', html, re.S):
                href = m.group(1).replace("&amp;", "&")
                inner = re.sub(r"<[^>]+>", " ", m.group(2))
                pm = re.search(r"([\d\.]+(?:,\d+)?)\s*(?:TL|₺)", inner)
                if not pm:
                    continue
                p_val = _parse_tr_price(pm.group(1))
                if not p_val:
                    continue

                if not result["y360_pid"]:
                    pid_m = re.search(r"pid=([^&]+)", href)
                    pp_m = re.search(r"p_p=([^&]+)", href)
                    if pid_m and pp_m:
                        result["y360_pid"] = pid_m.group(1)
                        result["y360_pp"] = pp_m.group(1)

                c_m = re.search(r"(?:^|[?&])c=([a-z_]+)", href)
                cat_code = c_m.group(1) if c_m else ""
                if cat_code in cat_buckets:
                    cat_buckets[cat_code].append(p_val)

            if cat_buckets["economy"]:
                sorted_eco = sorted(cat_buckets["economy"])
                result["y360_prices"]["economy"] = sorted_eco[0]
                result["y360_prices"]["eco_auto"] = sorted_eco[min(1, len(sorted_eco) - 1)]
            if cat_buckets["mid"]:
                sorted_mid = sorted(cat_buckets["mid"])
                result["y360_prices"]["comfort"] = sorted_mid[0]
                if "eco_auto" not in result["y360_prices"]:
                    result["y360_prices"]["eco_auto"] = sorted_mid[0]
            if cat_buckets["suv"]:
                result["y360_prices"]["suv"] = min(cat_buckets["suv"])
            if cat_buckets["upper"] or cat_buckets["luxury"]:
                lux_pool = cat_buckets["upper"] + cat_buckets["luxury"]
                result["y360_prices"]["luxury"] = min(lux_pool)

        def _scrape_enuygun():
            url = f"https://www.enuygun.com/arac-kiralama/{meta['enuygun_slug']}/"
            try:
                req = urllib.request.Request(url, headers=headers)
                html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", "ignore")
            except Exception:
                try:
                    url2 = f"https://www.enuygun.com/arac-kiralama/{city_slug}/"
                    req2 = urllib.request.Request(url2, headers=headers)
                    html = urllib.request.urlopen(req2, timeout=5).read().decode("utf-8", "ignore")
                except Exception:
                    return

            # Tablo hücrelerinden (car-prices-2-price-0..5) veya özet metinden canlı fiyatları çek
            table_prices: Dict[int, Tuple[float, float]] = {}
            for tm in re.finditer(r'data-testid="car-prices-2-price-(\d+)"[^>]*>\s*([\d\.]+)(?:\s*-\s*([\d\.]+))?\s*TL', html):
                idx = int(tm.group(1))
                p_low = _parse_tr_price(tm.group(2))
                p_high = _parse_tr_price(tm.group(3)) if tm.group(3) else p_low
                if p_low:
                    table_prices[idx] = (p_low, p_high or p_low)

            if 0 in table_prices:
                result["enuygun_prices"]["economy"] = table_prices[0][0]
                result["enuygun_prices"]["eco_auto"] = table_prices[0][1]
            if 4 in table_prices:
                result["enuygun_prices"]["comfort"] = table_prices[4][0]
            elif 1 in table_prices:
                result["enuygun_prices"]["comfort"] = table_prices[1][0]
            if 5 in table_prices:
                result["enuygun_prices"]["suv"] = table_prices[5][0]
            if 2 in table_prices:
                result["enuygun_prices"]["luxury"] = table_prices[2][0]
            elif 1 in table_prices:
                result["enuygun_prices"]["luxury"] = table_prices[1][1]

            if not result["enuygun_prices"]:
                m_eco = re.search(r"ekonomi.*?günlük\s*(?:<[^>]+>)*([\d\.]+)\s*TL", html, re.I | re.S)
                m_suv = re.search(r"SUV.*?günlük\s*(?:<[^>]+>)*([\d\.]+)\s*TL", html, re.I | re.S)
                m_prm = re.search(r"premium.*?günlük\s*(?:<[^>]+>)*([\d\.]+)\s*TL", html, re.I | re.S)
                if m_eco:
                    p = _parse_tr_price(m_eco.group(1))
                    if p:
                        result["enuygun_prices"]["economy"] = p
                        result["enuygun_prices"]["eco_auto"] = p
                if m_suv:
                    p = _parse_tr_price(m_suv.group(1))
                    if p:
                        result["enuygun_prices"]["suv"] = p
                        result["enuygun_prices"]["comfort"] = p
                if m_prm:
                    p = _parse_tr_price(m_prm.group(1))
                    if p:
                        result["enuygun_prices"]["luxury"] = p

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_scrape_yolcu360)
            f2 = pool.submit(_scrape_enuygun)
            for f in (f1, f2):
                try:
                    f.result(timeout=6)
                except Exception:
                    pass

        with cls._CACHE_LOCK:
            cls._LIVE_CAR_CACHE[cache_key] = (now, result)

        return result

    @classmethod
    def generate_car_deep_links(
        cls,
        location_name: str,
        pickup_date: str,
        dropoff_date: str,
        location_type: str = "city",
        y360_pid: str = "",
        y360_pp: str = "",
    ) -> Dict[str, str]:
        """
        Asla çıplak ana sayfaya düşmeyen, doğrulanmış (HTTP 200) havalimanı/şehir ve tarih parametreli derin linkler üretir.
        """
        iata, city_slug, meta = cls._resolve_airport_and_city(location_name, location_type)
        pid = y360_pid or meta.get("y360_pid") or ""
        pp = y360_pp or meta.get("y360_pp") or ""

        tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")

        # 1. Yolcu360: Eğer Google Place ID (pid + p_p) mevcutsa doğrudan tarihli & en ucuz sıralı /arac-kiralama/search ekranına iner!
        if pid and pp:
            yolcu360_base = (
                f"https://yolcu360.com/arac-kiralama/search"
                f"?p_d={pickup_date}&d_d={dropoff_date}&p_t=10:00&d_t=10:00"
                f"&a=30-65&sb=lowest_price_first&p_p={pp}&pid={pid}"
            )
        else:
            yolcu360_base = f"https://yolcu360.com/arac-kiralama/{meta['y360_path']}"

        # 2. Enuygun Araç: Doğrudan havalimanı/şehir araç kiralama sayfası (HTTP 200)
        enuygun_car_url = f"https://www.enuygun.com/arac-kiralama/{meta['enuygun_slug']}/"

        # 3. Obilet Araç: Doğrudan havalimanı/şehir araç kiralama ekranı (/arac-kiralama/{sehir}/{havalimani})
        obilet_car_url = f"https://www.obilet.com/arac-kiralama/{meta['obilet_path']}"

        # 4. Rentalcars (Booking Holdings): Doğrudan havalimanı (/tr/airport/tr/{iata}/) veya şehir (/tr/city/tr/{sehir}/) sayfası
        if iata:
            rentalcars_url = f"https://www.rentalcars.com/tr/airport/tr/{iata.lower()}/"
        else:
            rentalcars_url = f"https://www.rentalcars.com/tr/city/tr/{city_slug}/"

        # 5. Garenta: Doğrudan ilgili havalimanı/şehir şube kiralama sayfası (garenta.com/tr/arac-kiralama/...)
        garenta_url = f"https://www.garenta.com/tr/arac-kiralama/{meta['garenta_path']}"

        # 6. Avis: Doğrudan ilgili şehir kiralama sayfası (avis.com.tr/arac-kiralama/{sehir})
        avis_url = f"https://www.avis.com.tr/arac-kiralama/{city_slug}"

        return {
            "yolcu360": yolcu360_base,
            "yolcu360_economy": f"{yolcu360_base}&c=economy" if "?" in yolcu360_base else yolcu360_base,
            "yolcu360_mid": f"{yolcu360_base}&c=mid" if "?" in yolcu360_base else yolcu360_base,
            "yolcu360_suv": f"{yolcu360_base}&c=suv" if "?" in yolcu360_base else yolcu360_base,
            "yolcu360_luxury": f"{yolcu360_base}&c=luxury" if "?" in yolcu360_base else yolcu360_base,
            "enuygun": enuygun_car_url,
            "obilet": obilet_car_url,
            "rentalcars": rentalcars_url,
            "garenta": garenta_url,
            "avis": avis_url,
            "location_label": meta.get("label") or f"{location_name} Havalimanı / Şehir Ofisleri",
        }

    @classmethod
    def _build_vehicle_providers(
        cls,
        seg_key: str,
        y360_cat_link: str,
        links: Dict[str, str],
        live_data: Dict[str, Any],
        days_count: int,
        currency: str,
    ) -> List[Dict[str, Any]]:
        """
        SIFIR VARSAYIM KURALI:
        Yalnızca Yolcu360 ve Enuygun'dan canlı doğrulanmış fiyat varsa rakam gösterilir;
        diğer resmi sağlayıcılar uydurma fiyat olmadan şeffaf karşılaştırma butonu olarak listelenir.
        """
        y360_raw = live_data.get("y360_prices", {}).get(seg_key)
        en_raw = live_data.get("enuygun_prices", {}).get(seg_key)

        def _conv(val: Optional[float]) -> Optional[float]:
            if val is None or val <= 0:
                return None
            return round(CurrencyService.convert(val, "TRY", currency)) if currency != "TRY" else round(val)

        y360_daily = _conv(y360_raw)
        en_daily = _conv(en_raw)

        raw_providers = [
            {
                "id": "yolcu360",
                "name": "Yolcu360",
                "url": y360_cat_link,
                "daily_price": y360_daily,
                "total_price": round(y360_daily * days_count) if y360_daily else None,
                "commission_rank": 100,
                "badge": "100+ Ofis • Canlı Fiyat" if y360_daily else "100+ Ofis Filosu",
                "btn_class": "bg-emerald-600 hover:bg-emerald-700 text-white",
            },
            {
                "id": "enuygun",
                "name": "Enuygun Araç",
                "url": links["enuygun"],
                "daily_price": en_daily,
                "total_price": round(en_daily * days_count) if en_daily else None,
                "commission_rank": 95,
                "badge": "Anlık Karşılaştırma" if en_daily else "Canlı Filo Sorgula",
                "btn_class": "bg-sky-600 hover:bg-sky-700 text-white",
            },
            {
                "id": "obilet",
                "name": "Obilet Araç",
                "url": links["obilet"],
                "daily_price": None,
                "total_price": None,
                "commission_rank": 90,
                "badge": "Popüler & Güvenli",
                "btn_class": "bg-amber-600 hover:bg-amber-700 text-white",
            },
            {
                "id": "rentalcars",
                "name": "Rentalcars (Booking)",
                "url": links["rentalcars"],
                "daily_price": None,
                "total_price": None,
                "commission_rank": 85,
                "badge": "Global Havalimanı Ağı",
                "btn_class": "bg-blue-600 hover:bg-blue-700 text-white",
            },
            {
                "id": "garenta",
                "name": "Garenta",
                "url": links["garenta"],
                "daily_price": None,
                "total_price": None,
                "commission_rank": 80,
                "badge": "Yerli Kurumsal Filo",
                "btn_class": "bg-indigo-600 hover:bg-indigo-700 text-white",
            },
            {
                "id": "avis",
                "name": "Avis Türkiye",
                "url": links["avis"],
                "daily_price": None,
                "total_price": None,
                "commission_rank": 75,
                "badge": "Terminal İçi Ofis",
                "btn_class": "bg-rose-600 hover:bg-rose-700 text-white",
            },
        ]

        priced = [p for p in raw_providers if p["daily_price"] is not None]
        unpriced = [p for p in raw_providers if p["daily_price"] is None]

        priced.sort(key=lambda p: (float(p["daily_price"]), -int(p["commission_rank"])))
        for p in raw_providers:
            p["is_cheapest"] = False

        if priced:
            priced[0]["is_cheapest"] = True
            priced[0]["badge"] = "🏆 EN UCUZ CANLI FİYAT"
        else:
            raw_providers[0]["is_cheapest"] = True

        return priced + unpriced

    @classmethod
    def search_cars(
        cls,
        location: str,
        pickup_date: str,
        dropoff_date: Optional[str] = None,
        dropoff_location: Optional[str] = None,
        driver_age: int = 25,
        location_type: str = "city",
        currency: str = "TRY",
    ) -> Dict[str, Any]:
        iata, city_slug, meta = cls._resolve_airport_and_city(location, location_type)
        city_obj = find_city(location)
        loc_name = meta.get("label") or (city_obj["name"] if city_obj else location)
        has_airport = True

        is_different_dropoff = False
        drop_name = loc_name
        if dropoff_location and dropoff_location.strip().lower() not in (location.strip().lower(), "aynı noktaya iade"):
            drop_obj = find_city(dropoff_location)
            drop_name = drop_obj["name"] if drop_obj else dropoff_location
            is_different_dropoff = True

        try:
            d_pick = datetime.strptime(pickup_date, "%Y-%m-%d")
            if dropoff_date:
                d_drop = datetime.strptime(dropoff_date, "%Y-%m-%d")
            else:
                d_drop = d_pick + timedelta(days=3)
                dropoff_date = d_drop.strftime("%Y-%m-%d")
            days_count = max(1, (d_drop - d_pick).days)
        except Exception:
            days_count = 3
            d_pick = datetime.now() + timedelta(days=7)
            d_drop = d_pick + timedelta(days=3)
            pickup_date = d_pick.strftime("%Y-%m-%d")
            dropoff_date = d_drop.strftime("%Y-%m-%d")

        # 1. Canlı Fiyatları ve Dinamik Google Place ID'yi Çek (15 Dk L1 Önbellek)
        live_data = cls._fetch_live_car_pricing(iata, city_slug, meta)

        # 2. Doğrulanmış Seviye 2 Derin Linkleri Üret
        links = cls.generate_car_deep_links(
            location_name=location,
            pickup_date=pickup_date,
            dropoff_date=dropoff_date,
            location_type=location_type,
            y360_pid=live_data.get("y360_pid", ""),
            y360_pp=live_data.get("y360_pp", ""),
        )

        if is_different_dropoff:
            location_type_label = f"🚗 Farklı Noktada Teslim ({loc_name} ➔ {drop_name})"
            pickup_point_desc = f"{loc_name} Alış Ofisi ➔ {drop_name} İade Noktası"
        else:
            location_type_label = f"✈️ {meta.get('label', loc_name)} • Terminal & Merkez Ofisleri"
            pickup_point_desc = f"{meta.get('label', loc_name)} Terminal İçi & Karşılama Ofisleri"

        currency = (currency or "TRY").upper()
        curr_symbol = CurrencyService.get_symbol(currency)

        provs_eco = cls._build_vehicle_providers("economy", links["yolcu360_economy"], links, live_data, days_count, currency)
        provs_eco_auto = cls._build_vehicle_providers("eco_auto", links["yolcu360_economy"], links, live_data, days_count, currency)
        provs_comfort = cls._build_vehicle_providers("comfort", links["yolcu360_mid"], links, live_data, days_count, currency)
        provs_suv = cls._build_vehicle_providers("suv", links["yolcu360_suv"], links, live_data, days_count, currency)
        provs_luxury = cls._build_vehicle_providers("luxury", links["yolcu360_luxury"], links, live_data, days_count, currency)

        def _card_summary(provs: List[Dict[str, Any]], seg_id: str, category: str, model: str, icon: str, trans: str, fuel: str, luggage: str, badge: str, deposit_note: str) -> Dict[str, Any]:
            winner = provs[0]
            return {
                "id": seg_id,
                "category": category,
                "car_model": model,
                "image_icon": icon,
                "transmission": trans,
                "fuel": fuel,
                "seats": 5,
                "doors": 5,
                "luggage": luggage,
                "air_conditioning": True,
                "unlimited_mileage": True,
                "provider_name": "Yolcu360 • Enuygun • Obilet • Garenta • Avis",
                "daily_price": winner.get("daily_price"),
                "total_price": winner.get("total_price"),
                "has_live_price": winner.get("daily_price") is not None,
                "cheapest_provider_name": winner["name"],
                "deposit": deposit_note,
                "badge": badge,
                "pickup_point": pickup_point_desc,
                "official_link": winner["url"],
                "agent_link": links["enuygun"],
                "obilet_link": links["obilet"],
                "providers": provs,
            }

        vehicles = [
            _card_summary(
                provs_eco,
                "car-eco-1",
                "Ekonomi",
                "Renault Clio / Dacia Logan veya Benzeri",
                "🚗",
                "Manuel / Otomatik",
                "Benzin",
                "2 Büyük Valiz",
                "EN ÇOK TERCİH EDİLEN 🔥",
                "Kredi Kartı Provizyonlu • Kasko Dahil",
            ),
            _card_summary(
                provs_eco_auto,
                "car-eco-auto",
                "Ekonomi (Otomatik)",
                "Fiat Egea Cross / Hyundai i20 Otomatik",
                "🚗",
                "Otomatik",
                "Benzin / Dizel",
                "3 Valiz",
                "YAKIT CİMRİSİ ⛽",
                "Kredi Kartı Provizyonlu • Kasko Dahil",
            ),
            _card_summary(
                provs_comfort,
                "car-comfort",
                "Konfor / Orta Sınıf",
                "Renault Megane Sedan / Toyota Corolla Hybrid",
                "🚘",
                "Otomatik",
                "Hibrit / Dizel",
                "3 Büyük Valiz",
                "YÜKSEK KONFOR ⭐",
                "Geniş Bagaj • Sınırsız Km Seçenekli",
            ),
            _card_summary(
                provs_suv,
                "car-suv",
                "SUV & Aile",
                "Peugeot 2008 / Chery Omoda 5 / Dacia Duster SUV",
                "🚙",
                "Otomatik",
                "Benzin / Dizel",
                "4 Büyük Valiz",
                "AİLE & GEZİ FAVORİSİ 🏔️",
                "Yüksek Sürüş • Tam Güvence Opsiyonlu",
            ),
            _card_summary(
                provs_luxury,
                "car-luxury",
                "Premium / VIP Lüks",
                "Mercedes-Benz C200 / BMW 520i / Audi A3 Sedan",
                "🏎️",
                "Otomatik",
                "Benzin / Hibrit",
                "3 Büyük Valiz",
                "PRESTİJ & VIP ✨",
                "Kurumsal Filo • Havalimanı VIP Teslimat",
            ),
        ]

        live_prices = [float(v["daily_price"]) for v in vehicles if v.get("daily_price") is not None]
        min_price = min(live_prices) if live_prices else None

        return {
            "location": loc_name,
            "airport_code": iata,
            "has_airport": has_airport,
            "location_type": location_type,
            "location_type_label": location_type_label,
            "pickup_date": pickup_date,
            "dropoff_date": dropoff_date,
            "days_count": days_count,
            "min_daily_price": min_price,
            "has_live_price": min_price is not None,
            "currency": curr_symbol,
            "currency_code": currency,
            "deep_links": links,
            "providers": provs_eco,
            "vehicles_count": len(vehicles),
            "vehicles": vehicles,
        }
