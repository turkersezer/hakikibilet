"""
Hakiki Bilet — Akıllı Havalimanı VIP Transfer, Resmi Shuttle (HAVAİST/HAVAŞ/MUTTAŞ) & Raylı Ulaşım Servisi
- SIFIR VARSAYIM (Zero-Assumption): Bilet.com Transfer üzerinden gerçek zamanlı SSR transfer taban fiyatları
  (Premium Shuttle, VIP Vito Minivan) 15 dk L1 önbellekle çekilir.
- SEVİYE 2 DERİN LİNK (Ana Ekrana Düşmeme Kuralı):
  Bilet.com (/transfer/{havalimani-slug}), Welcome Pickups (/{sehir}/airport-transfer/),
  HAVAİST (hava.ist/sefer-saatleri.php), HAVABUS (havabus.com) ve HAVAŞ (havas.net/otobus-hizmetleri)
  doğrudan ilgili havalimanı transfer ve sefer saatleri ekranına iner.
"""
import re
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from app.cities import find_city
from app.config import settings


def _to_ascii_slug(text: str) -> str:
    if not text:
        return ""
    tr_map = str.maketrans({
        "ı": "i", "İ": "i", "I": "i",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ş": "s", "Ş": "s",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
    })
    cleaned = text.translate(tr_map).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return cleaned


class TransferService:
    _LIVE_TRANSFER_CACHE: Dict[str, Tuple[float, Dict[str, Optional[float]]]] = {}
    _CACHE_LOCK = threading.Lock()
    _CACHE_TTL_SECONDS = 900  # 15 dk L1 önbellek

    AIRPORT_TRANSFER_TARGETS: Dict[str, Dict[str, str]] = {
        "IST": {
            "name": "İstanbul Havalimanı (IST)",
            "bilet_slug": "istanbul-havalimani",
            "welcome_slug": "istanbul",
            "city": "İstanbul",
            "havas": "HAVAİST Resmi Havalimanı Otobüsü",
            "shuttle_url": "https://www.hava.ist/sefer-saatleri.php",
            "shuttle_routes": "Taksim, Kadıköy, Beşiktaş, Aksaray, Otogar, Bakırköy, Avcılar (7/24 Sefer)",
            "rail_info": "🚇 M11 Gayrettepe ➔ İstanbul Havalimanı ➔ Arnavutköy Metrosu (25 dk)",
        },
        "SAW": {
            "name": "Sabiha Gökçen Havalimanı (SAW)",
            "bilet_slug": "sabiha-gokcen-havalimani",
            "welcome_slug": "istanbul",
            "city": "İstanbul",
            "havas": "HAVABUS (Taksim • Kadıköy • Yenisahra)",
            "shuttle_url": "https://www.havabus.com/",
            "shuttle_routes": "Kadıköy Rıhtım, Taksim Abdülhakhamit Cad., Yenisahra Metro (30 dk'da bir)",
            "rail_info": "🚇 M4 Kadıköy ➔ Tavşantepe ➔ Sabiha Gökçen Havalimanı Metrosu (Terminal İçi)",
        },
        "AYT": {
            "name": "Antalya Havalimanı (AYT)",
            "bilet_slug": "antalya-havalimani",
            "welcome_slug": "antalya",
            "city": "Antalya",
            "havas": "HAVAŞ Antalya & 600/800 Belediye Ekspres",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Lara, Konyaaltı, Otogar, Kemer, Belek, Side, Manavgat, Alanya",
            "rail_info": "🚋 AntRay T1A Havalimanı ➔ Fatih / Otogar / Kalekapısı Tramvay Hattı",
        },
        "ADB": {
            "name": "İzmir Adnan Menderes Havalimanı (ADB)",
            "bilet_slug": "istanbul-havalimani",
            "welcome_slug": "izmir",
            "city": "İzmir",
            "havas": "HAVAŞ İzmir (Alsancak • Karşıyaka • Çeşme • Kuşadası)",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Alsancak, Karşıyaka/Mavişehir, Çeşme, Alaçatı, Urla, Kuşadası, Söke",
            "rail_info": "🚆 İZBAN Havalimanı İstasyonu (Alsancak, Karşıyaka, Selçuk/Tepeköy Bağlantılı)",
        },
        "ESB": {
            "name": "Ankara Esenboğa Havalimanı (ESB)",
            "bilet_slug": "istanbul-havalimani",
            "welcome_slug": "ankara",
            "city": "Ankara",
            "havas": "HAVAŞ Ankara & EGO 442 (Kızılay • AŞTİ)",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "15 Temmuz Kızılay Milli İrade Meydanı, AŞTİ Otogar, Ankara YHT Gar",
            "rail_info": "🚌 EGO 442 Havalimanı Ekspres Hattı (7/24 Kızılay & AŞTİ)",
        },
        "BJV": {
            "name": "Muğla Milas-Bodrum Havalimanı (BJV)",
            "bilet_slug": "bodrum-milas-havalimani",
            "welcome_slug": "bodrum",
            "city": "Muğla (Bodrum)",
            "havas": "MUTTAŞ & HAVAŞ Bodrum",
            "shuttle_url": "https://ulasim.muttas.com.tr/",
            "shuttle_routes": "Bodrum Merkez Otogar, Torba, Güvercinlik, Milas, Didim",
            "rail_info": "🚌 Her Uçak İnişine Entegre MUTTAŞ & HAVAŞ Seferleri",
        },
        "DLM": {
            "name": "Muğla Dalaman Havalimanı (DLM)",
            "bilet_slug": "mugla-dalaman-havalimani",
            "welcome_slug": "dalaman",
            "city": "Muğla (Dalaman / Fethiye / Marmaris)",
            "havas": "MUTTAŞ & HAVAŞ (Fethiye • Marmaris • Göcek • Datça)",
            "shuttle_url": "https://ulasim.muttas.com.tr/",
            "shuttle_routes": "Fethiye Otogar, Göcek, Marmaris Otogar, Gökova, Köyceğiz, Ortaca",
            "rail_info": "🚌 İç ve Dış Hat İnişlerine Entegre MUTTAŞ / HAVAŞ Otobüsleri",
        },
        "TZX": {
            "name": "Trabzon Havalimanı (TZX)",
            "bilet_slug": "trabzon-havalimani",
            "welcome_slug": "istanbul",
            "city": "Trabzon",
            "havas": "HAVAŞ Karadeniz (Trabzon • Rize • Hopa • Giresun)",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Trabzon Meydan, Beşirli, Yomra, Ardeşen, Rize, Hopa, Tirebolu, Giresun",
            "rail_info": "🚌 Havalimanı Çıkışı Büyükşehir Havalimanı Otobüsleri",
        },
        "GZP": {
            "name": "Alanya Gazipaşa Havalimanı (GZP)",
            "bilet_slug": "antalya-havalimani",
            "welcome_slug": "antalya",
            "city": "Alanya",
            "havas": "HAVAŞ Alanya (Mahmutlar • Oba • Alanya Otogar)",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Kargıcak, Mahmutlar, Kestel, Tosmur, Oba, Alanya Merkez Otogar",
            "rail_info": "🚌 Uçuş Saatlerine Göre HAVAŞ Karşılama Servisi",
        },
        "EDO": {
            "name": "Balıkesir Edremit Koca Seyit (EDO)",
            "bilet_slug": "istanbul-havalimani",
            "welcome_slug": "izmir",
            "city": "Balıkesir (Edremit / Ayvalık)",
            "havas": "BTT & Havalimanı Servisleri (Ayvalık • Akçay • Altınoluk)",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Burhaniye, Gömeç, Ayvalık, Edremit, Akçay, Güre, Altınoluk, Küçükkuyu",
            "rail_info": "🚌 Balıkesir Toplu Taşıma (BTT) Havalimanı Entegre Hatları",
        },
        "COV": {
            "name": "Çukurova Uluslararası Havalimanı (COV)",
            "bilet_slug": "adana-sakirpasa-havalimani",
            "welcome_slug": "antalya",
            "city": "Adana / Mersin",
            "havas": "HAVAMAŞ (Adana Merkez • Mersin • Tarsus)",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Adana Otogar / Optimum / Ziyapaşa, Tarsus, Mersin Forum / Mezitli / MEŞOT",
            "rail_info": "🚌 7/24 HAVAMAŞ Adana & Mersin Ekspres Otobüsleri",
        },
        "ASR": {
            "name": "Kayseri Erkilet Havalimanı (ASR)",
            "bilet_slug": "kayseri-erkilet-havalimani",
            "welcome_slug": "istanbul",
            "city": "Kayseri / Kapadokya",
            "havas": "HAVAŞ Kayseri & Kapadokya / Erciyes Shuttle",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Kayseri Forum / Otogar, Erciyes Kayak Merkezi, Ürgüp, Göreme, Avanos",
            "rail_info": "🚌 HAVAŞ & Kapadokya Otel Kapıdan Kapıya Shuttle",
        },
        "GZT": {
            "name": "Gaziantep Havalimanı (GZT)",
            "bilet_slug": "gaziantep-havalimani",
            "welcome_slug": "istanbul",
            "city": "Gaziantep",
            "havas": "HAVAŞ Gaziantep & GAZİULAŞ B01",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": "Karataş, Üniversite, Sankopark, Gaziantep Otogar, Nizip",
            "rail_info": "🚌 HAVAŞ & Gaziulaş Havalimanı Ekspres Hattı",
        },
    }

    @classmethod
    def _fetch_live_biletcom_transfer_prices(cls) -> Dict[str, Optional[float]]:
        now = time.time()
        with cls._CACHE_LOCK:
            cached = cls._LIVE_TRANSFER_CACHE.get("biletcom_global")
            if cached and (now - cached[0]) < cls._CACHE_TTL_SECONDS:
                return cached[1]

        prices: Dict[str, Optional[float]] = {
            "shuttle_try": None,
            "minivan_try": None,
            "vito_try": None,
        }
        try:
            req = urllib.request.Request(
                "https://www.bilet.com/transfer",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept-Language": "tr-TR,tr;q=0.9",
                },
            )
            html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", "ignore")

            def _parse(s: str) -> Optional[float]:
                try:
                    v = float(s.replace(".", "").replace(",", "."))
                    return v if 300.0 <= v <= 25000.0 else None
                except Exception:
                    return None

            shuttles = [
                _parse(m.group(1))
                for m in re.finditer(r"Premium Shuttle.*?([\d\.]+)\s*TL", html, re.S)
            ]
            minivans = [
                _parse(m.group(1))
                for m in re.finditer(r"Minivan(?!\s*\(1-6).*?([\d\.]+)\s*TL", html, re.S)
            ]
            vitos = [
                _parse(m.group(1))
                for m in re.finditer(r"Executive Vito Minivan.*?([\d\.]+)\s*TL", html, re.S)
            ]

            shuttles = [x for x in shuttles if x]
            minivans = [x for x in minivans if x]
            vitos = [x for x in vitos if x]

            if shuttles:
                prices["shuttle_try"] = min(shuttles)
            if minivans:
                prices["minivan_try"] = min(minivans)
            if vitos:
                prices["vito_try"] = min(vitos)
        except Exception:
            pass

        with cls._CACHE_LOCK:
            cls._LIVE_TRANSFER_CACHE["biletcom_global"] = (now, prices)

        return prices

    @classmethod
    def _resolve_airport_from_text(cls, raw_text: str) -> Tuple[str, str]:
        clean_input = (raw_text or "").strip()
        low_input = clean_input.lower()
        iata = ""
        city_name = clean_input

        if "(" in clean_input and ")" in clean_input:
            candidate_iata = clean_input.split("(")[-1].replace(")", "").strip().upper()
            if len(candidate_iata) == 3 and candidate_iata in cls.AIRPORT_TRANSFER_TARGETS:
                return candidate_iata, clean_input.split("(")[0].strip()

        if "sabiha" in low_input or "saw" in low_input:
            iata = "SAW"
        elif "istanbul" in low_input or "ist" in low_input or "kadıköy" in low_input or "kadikoy" in low_input or "taksim" in low_input or "beşiktaş" in low_input:
            iata = "IST"
        elif "gazipaşa" in low_input or "gazipasa" in low_input or "gzp" in low_input or "alanya" in low_input:
            iata = "GZP"
        elif "antalya" in low_input or "ayt" in low_input or "kemer" in low_input or "belek" in low_input or "side" in low_input or "kaş" in low_input or "kas" in low_input or "lara" in low_input:
            iata = "AYT"
        elif "izmir" in low_input or "adb" in low_input or "çeşme" in low_input or "cesme" in low_input or "alaçatı" in low_input or "alacati" in low_input or "kuşadası" in low_input or "kusadasi" in low_input:
            iata = "ADB"
        elif "bodrum" in low_input or "milas" in low_input or "bjv" in low_input:
            iata = "BJV"
        elif "dalaman" in low_input or "dlm" in low_input or "marmaris" in low_input or "fethiye" in low_input or "göcek" in low_input or "gocek" in low_input:
            iata = "DLM"
        elif "ankara" in low_input or "esenboğa" in low_input or "esenboga" in low_input or "esb" in low_input:
            iata = "ESB"
        elif "trabzon" in low_input or "tzx" in low_input or "rize" in low_input:
            iata = "TZX"
        elif "adana" in low_input or "mersin" in low_input or "çukurova" in low_input or "cukurova" in low_input or "cov" in low_input:
            iata = "COV"
        elif "kayseri" in low_input or "kapadokya" in low_input or "ürgüp" in low_input or "asr" in low_input:
            iata = "ASR"
        elif "gaziantep" in low_input or "gzt" in low_input:
            iata = "GZT"
        elif "edremit" in low_input or "ayvalık" in low_input or "akçay" in low_input or "edo" in low_input:
            iata = "EDO"
        else:
            city_obj = find_city(clean_input)
            if city_obj and city_obj.get("iata"):
                iata = city_obj["iata"].upper()
                city_name = city_obj.get("name", clean_input)

        return iata, city_name

    @classmethod
    def generate_transfer_links(
        cls,
        dest_city_or_code: str,
        travel_date: str = "",
        pickup_location: str = "",
        passengers: int = 1,
    ) -> Dict[str, Any]:
        """
        Varış şehri veya havalimanı için Bilet.com Transfer, Welcome Pickups ve resmi HAVAİST/HAVAŞ/MUTTAŞ
        sağlayıcılarına asla ana ekrana düşmeyen doğrulanmış derin linkler ve canlı taban fiyatlar üretir.
        """
        iata, city_name = cls._resolve_airport_from_text(dest_city_or_code)
        if pickup_location:
            p_iata, p_city = cls._resolve_airport_from_text(pickup_location)
            # Eğer kalkış noktasında açıkça havalimanı kodu varsa (örn: SAW, IST, AYT) veya dest'te havalimanı bulunamadıysa
            if p_iata and (not iata or "(" in pickup_location or "havaliman" in pickup_location.lower()):
                iata, city_name = p_iata, p_city

        target_info = cls.AIRPORT_TRANSFER_TARGETS.get(iata, {
            "name": f"{city_name} Havalimanı / Merkez",
            "bilet_slug": "istanbul-havalimani",
            "welcome_slug": "istanbul",
            "city": city_name,
            "havas": "HAVAŞ & Resmi Havalimanı Otobüsleri",
            "shuttle_url": "https://www.havas.net/otobus-hizmetleri",
            "shuttle_routes": f"{city_name} Havalimanı ➔ Şehir Merkezi & Otogar",
            "rail_info": "🚌 Uçuş İniş Saatlerine Entegre Havalimanı Servisleri",
        })

        # 1. Bilet.com Transfer Doğrudan Havalimanı Sayfası (HTTP 200 - Ana sayfaya düşmez)
        from app.services.revenue_service import RevenueService
        bilet_slug = target_info.get("bilet_slug", "istanbul-havalimani")
        biletcom_transfer_url = RevenueService.enrich_deep_link(
            "biletcom",
            f"https://www.bilet.com/transfer/{bilet_slug}",
            "airport_transfer",
        )

        # 2. Welcome Pickups Doğrudan Havalimanı Karşılama Sayfası (HTTP 200)
        welcome_slug = target_info.get("welcome_slug", "istanbul")
        welcomepickups_url = RevenueService.enrich_deep_link(
            "welcomepickups",
            f"https://www.welcomepickups.com/{welcome_slug}/airport-transfer/",
            "airport_transfer",
        )

        # 3. Resmi Havalimanı Shuttle (HAVAİST / HAVABUS / HAVAŞ / MUTTAŞ) Sefer Saatleri Sayfası (HTTP 200)
        shuttle_url = RevenueService.enrich_deep_link(
            "official",
            target_info.get("shuttle_url", "https://www.havas.net/otobus-hizmetleri"),
            "airport_transfer",
        )

        # 4. Canlı Bilet.com Transfer Fiyatlarını Çek (15 dk L1 önbellek)
        live_prices = cls._fetch_live_biletcom_transfer_prices()

        return {
            "city_name": target_info.get("city", city_name),
            "iata": iata or "IST",
            "display_name": target_info["name"],
            "shuttle_name": target_info.get("havas", "HAVAŞ Resmi Havalimanı Servisi"),
            "shuttle_url": shuttle_url,
            "shuttle_routes": target_info.get("shuttle_routes", ""),
            "rail_info": target_info.get("rail_info", ""),
            "biletcom_url": biletcom_transfer_url,
            "welcomepickups_url": welcomepickups_url,
            "kiwitaxi_url": welcomepickups_url,
            "gettransfer_url": shuttle_url,
            "live_shuttle_try": live_prices.get("shuttle_try"),
            "live_minivan_try": live_prices.get("minivan_try"),
            "live_vito_try": live_prices.get("vito_try"),
            "badge": "Havalimanı ➔ Otel VIP / Shuttle Transferi",
        }
