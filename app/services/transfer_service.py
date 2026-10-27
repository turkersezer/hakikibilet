"""
Hakiki Bilet — Akıllı Havalimanı & Şehirlerarası Transfer Servisi
(Bilet.com, KiwiTaxi, GetTransfer, Bitaksi / Havabüs parametrik derin link ve akıllı çapraz satış motoru)
"""

import re
import urllib.parse
from typing import Dict, Any, Optional
from app.cities import find_city
from app.config import settings


def _to_ascii_slug(text: str) -> str:
    """Türkçe karakterleri temizleyip SEO/URL uyumlu ASCII slug üretir."""
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
    """
    MODÜL: Akıllı Transfer Çözümleyici & Deep Link Üretici
    - Bilet.com Transfer Entegrasyonu
    - KiwiTaxi & GetTransfer (Global & Turistik)
    - Havalimanı Shuttle (Havabüs / Havaş) Kılavuzları
    - Uçuş, Tren, Otobüs sonuç kartlarına otomatik cross-sell bağlama
    """

    AIRPORT_TRANSFER_TARGETS = {
        "IST": {"name": "İstanbul Havalimanı (IST)", "slug": "istanbul-havalimani", "city": "İstanbul", "havaş": "Havaist"},
        "SAW": {"name": "Sabiha Gökçen Havalimanı (SAW)", "slug": "sabiha-gokcen-havalimani", "city": "İstanbul", "havaş": "Havabüs"},
        "AYT": {"name": "Antalya Havalimanı (AYT)", "slug": "antalya-havalimani", "city": "Antalya", "havaş": "Havaş"},
        "ADB": {"name": "İzmir Adnan Menderes (ADB)", "slug": "izmir-adnan-menderes-havalimani", "city": "İzmir", "havaş": "Havaş"},
        "ESB": {"name": "Ankara Esenboğa (ESB)", "slug": "ankara-esenboga-havalimani", "city": "Ankara", "havaş": "BelkoAir"},
        "BJV": {"name": "Bodrum Milas (BJV)", "slug": "bodrum-milas-havalimani", "city": "Muğla", "havaş": "MUTTAŞ"},
        "DLM": {"name": "Dalaman Havalimanı (DLM)", "slug": "dalaman-havalimani", "city": "Muğla", "havaş": "MUTTAŞ"},
        "TZX": {"name": "Trabzon Havalimanı (TZX)", "slug": "trabzon-havalimani", "city": "Trabzon", "havaş": "Havaş"},
        "GZP": {"name": "Alanya Gazipaşa (GZP)", "slug": "alanya-gazipasa-havalimani", "city": "Antalya", "havaş": "Havaş"},
        "EDO": {"name": "Balıkesir Edremit Koca Seyit (EDO)", "slug": "balikesir-edremit-havalimani", "city": "Balıkesir", "havaş": "Havaş"},
        "COV": {"name": "Çukurova Uluslararası (COV)", "slug": "cukurova-havalimani", "city": "Adana", "havaş": "Havaş"},
        "KSY": {"name": "Kars Harakani Havalimanı (KSY)", "slug": "kars-harakani-havalimani", "city": "Kars", "havaş": "Belediye Otobüsü & Taksi"},
        "NAV": {"name": "Nevşehir Kapadokya (NAV)", "slug": "nevsehir-kapadokya-havalimani", "city": "Nevşehir", "havaş": "Kapadokya Shuttle"},
        "ASR": {"name": "Kayseri Havalimanı (ASR)", "slug": "kayseri-havalimani", "city": "Kayseri", "havaş": "Havaş"},
        "GNY": {"name": "Şanlıurfa GAP (GNY)", "slug": "sanliurfa-gap-havalimani", "city": "Şanlıurfa", "havaş": "Havaş"},
        "DIY": {"name": "Diyarbakır Havalimanı (DIY)", "slug": "diyarbakir-havalimani", "city": "Diyarbakır", "havaş": "Havaş"},
        "VAN": {"name": "Van Ferit Melen (VAN)", "slug": "van-ferit-melen-havalimani", "city": "Van", "havaş": "Belediye & Havaş"},
        "MLX": {"name": "Malatya Erhaç (MLX)", "slug": "malatya-erhac-havalimani", "city": "Malatya", "havaş": "Havaş"},
        "DNZ": {"name": "Denizli Çardak (DNZ)", "slug": "denizli-cardak-havalimani", "city": "Denizli", "havaş": "Bay-Tur Shuttle"},
        "GZT": {"name": "Gaziantep Havalimanı (GZT)", "slug": "gaziantep-havalimani", "city": "Gaziantep", "havaş": "Havaş"},
    }

    @classmethod
    def generate_transfer_links(
        cls,
        dest_city_or_code: str,
        travel_date: str = "",
        pickup_location: str = "",
        passengers: int = 1,
    ) -> Dict[str, Any]:
        """
        Varış şehri veya havalimanı için Bilet.com ve global transfer sağlayıcılarına derin link üretir.
        """
        clean_input = (dest_city_or_code or "").strip()
        iata = ""
        city_name = clean_input

        # IATA parantezi kontrolü: "Kars (KSY)" -> KSY
        if "(" in clean_input and ")" in clean_input:
            candidate_iata = clean_input.split("(")[-1].replace(")", "").strip().upper()
            if len(candidate_iata) == 3:
                iata = candidate_iata
                city_name = clean_input.split("(")[0].strip()

        if not iata:
            city_obj = find_city(clean_input)
            if city_obj and city_obj.get("iata"):
                iata = city_obj["iata"].upper()
                city_name = city_obj.get("name", clean_input)

        target_info = cls.AIRPORT_TRANSFER_TARGETS.get(iata, {
            "name": f"{city_name} Havalimanı / Merkez",
            "slug": _to_ascii_slug(city_name),
            "city": city_name,
            "havaş": "Havaş & Havalimanı Taksileri"
        })

        encoded_city = urllib.parse.quote(city_name)
        safe_date = travel_date or ""

        # 1. Bilet.com Transfer Derin Linki
        biletcom_transfer_url = (
            f"https://www.bilet.com/transfer?kalkis={target_info['slug']}&tarih={safe_date}&yolcu={passengers}&utm_source=hakikibilet&ref=hakikibilet"
            if safe_date
            else f"https://www.bilet.com/transfer?kalkis={target_info['slug']}&utm_source=hakikibilet&ref=hakikibilet"
        )

        # 2. GetTransfer & KiwiTaxi (Global / Turistik Karşılaştırma)
        tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
        kiwitaxi_url = f"https://kiwitaxi.com/?pap={tp_marker}&from={encoded_city}"
        gettransfer_url = f"https://gettransfer.com/tr?utm_source=hakikibilet&to={encoded_city}"

        return {
            "city_name": city_name,
            "iata": iata,
            "display_name": target_info["name"],
            "shuttle_name": target_info.get("havaş", "Havalimanı Servisi"),
            "biletcom_url": biletcom_transfer_url,
            "kiwitaxi_url": kiwitaxi_url,
            "gettransfer_url": gettransfer_url,
            "badge": "Havalimanı ➔ Otel VIP / Shuttle Transferi",
        }
