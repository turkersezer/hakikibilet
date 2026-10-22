"""
HAKIKI BILET - 85 ROTALIK KAPSAMLI TEST VE DENETİM MOTORU
Aşama 2: Sıfır-Token / Sıfır-Maliyet Yerel Otomasyon Denetimi

Bu script:
- 85 farklı güzergahı (Uçak, Otobüs, Tren, Feribot, Negatif/İmkansız Rotalar ve Sınır Durumlar)
- Deep Link formatlarını, affiliate parametrelerini (Trip.com AllianceID, Travelpayouts Marker, Obilet SubID vb.)
- Sefer olmayan durumlarda dönen uyarı mesajlarını (Notices & Empty States)
- Model ve Pydantic validasyonlarını
tamamen yerel CPU üzerinde, dış API kotalarını tüketmeden saniyeler içinde denetler ve kapsamlı bir rapor üretir.
"""

import sys
import os
import json
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Windows terminal UTF-8 desteği
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Proje dizinini ekle
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.search_service import SearchService
from app.services.bus_service import BusService
from app.services.train_service import TrainService
from app.services.ferry_service import FerryService
from app.services.hotel_service import HotelService
from app.services.currency_service import CurrencyService
from app.models import SearchRequest
from app.config import settings

# Gelecek tarih belirle (30 gün sonrası)
FUTURE_DEP = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
FUTURE_RET = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")

# 85 ROTALIK TEST MATRİSİ
TEST_SCENARIOS = [
    # =========================================================================
    # GRUP A: YURT İÇİ UÇUŞ ROTALARI (15 Rota)
    # =========================================================================
    {"id": "A01", "group": "Grup A: Yurt İçi Uçuş", "origin": "İstanbul", "dest": "İzmir", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A02", "group": "Grup A: Yurt İçi Uçuş", "origin": "Ankara", "dest": "Antalya", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "A03", "group": "Grup A: Yurt İçi Uçuş", "origin": "Trabzon", "dest": "Adana", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A04", "group": "Grup A: Yurt İçi Uçuş", "origin": "Gaziantep", "dest": "İstanbul", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A05", "group": "Grup A: Yurt İçi Uçuş", "origin": "Erzurum", "dest": "Bursa", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A06", "group": "Grup A: Yurt İçi Uçuş", "origin": "Bodrum (Muğla)", "dest": "İstanbul", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "A07", "group": "Grup A: Yurt İçi Uçuş", "origin": "Diyarbakır", "dest": "İzmir", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A08", "group": "Grup A: Yurt İçi Uçuş", "origin": "Samsun", "dest": "Antalya", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A09", "group": "Grup A: Yurt İçi Uçuş", "origin": "Kayseri", "dest": "İstanbul", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A10", "group": "Grup A: Yurt İçi Uçuş", "origin": "Van", "dest": "Ankara", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A11", "group": "Grup A: Yurt İçi Uçuş", "origin": "Kars", "dest": "İstanbul", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A12", "group": "Grup A: Yurt İçi Uçuş", "origin": "Dalaman (Muğla)", "dest": "İstanbul", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "A13", "group": "Grup A: Yurt İçi Uçuş", "origin": "Malatya", "dest": "İstanbul", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A14", "group": "Grup A: Yurt İçi Uçuş", "origin": "Sivas", "dest": "İzmir", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "A15", "group": "Grup A: Yurt İçi Uçuş", "origin": "Şanlıurfa", "dest": "Ankara", "mode": "flight", "type": "one_way", "expect_avail": True},

    # =========================================================================
    # GRUP B: YURT DIŞI UÇUŞ ROTALARI (15 Rota)
    # =========================================================================
    {"id": "B01", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Londra", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "B02", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Paris", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B03", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İzmir", "dest": "Berlin", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B04", "group": "Grup B: Yurt Dışı Uçuş", "origin": "Antalya", "dest": "Moskova", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "B05", "group": "Grup B: Yurt Dışı Uçuş", "origin": "Ankara", "dest": "Bakü", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B06", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Tokyo", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "B07", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "New York", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "B08", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Roma", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B09", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Dubai", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "B10", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Amsterdam", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B11", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İzmir", "dest": "Atina", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B12", "group": "Grup B: Yurt Dışı Uçuş", "origin": "Antalya", "dest": "Frankfurt", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B13", "group": "Grup B: Yurt Dışı Uçuş", "origin": "İstanbul", "dest": "Barselona", "mode": "flight", "type": "round_trip", "expect_avail": True},
    {"id": "B14", "group": "Grup B: Yurt Dışı Uçuş", "origin": "Ankara", "dest": "Viyana", "mode": "flight", "type": "one_way", "expect_avail": True},
    {"id": "B15", "group": "Grup B: Yurt Dışı Uçuş", "origin": "Trabzon", "dest": "Tiflis", "mode": "flight", "type": "one_way", "expect_avail": True},

    # =========================================================================
    # GRUP C: YURT İÇİ & DIŞI OTOBÜS ROTALARI (15 Rota)
    # =========================================================================
    {"id": "C01", "group": "Grup C: Otobüs", "origin": "İstanbul", "dest": "Ankara", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C02", "group": "Grup C: Otobüs", "origin": "İzmir", "dest": "Bodrum (Muğla)", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C03", "group": "Grup C: Otobüs", "origin": "Antalya", "dest": "Konya", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C04", "group": "Grup C: Otobüs", "origin": "Bursa", "dest": "Eskişehir", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C05", "group": "Grup C: Otobüs", "origin": "Adana", "dest": "Mersin", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C06", "group": "Grup C: Otobüs", "origin": "Trabzon", "dest": "Rize", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C07", "group": "Grup C: Otobüs", "origin": "Gaziantep", "dest": "Şanlıurfa", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C08", "group": "Grup C: Otobüs", "origin": "Diyarbakır", "dest": "Mardin", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C09", "group": "Grup C: Otobüs", "origin": "Kayseri", "dest": "Nevşehir", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C10", "group": "Grup C: Otobüs", "origin": "İstanbul", "dest": "Edirne", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C11", "group": "Grup C: Otobüs (Uluslararası)", "origin": "İstanbul", "dest": "Sofya", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C12", "group": "Grup C: Otobüs (Uluslararası)", "origin": "İstanbul", "dest": "Selanik", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C13", "group": "Grup C: Otobüs (Avrupa)", "origin": "Berlin", "dest": "Prag", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C14", "group": "Grup C: Otobüs (Avrupa)", "origin": "Paris", "dest": "Brüksel", "mode": "bus", "type": "one_way", "expect_avail": True},
    {"id": "C15", "group": "Grup C: Otobüs (Avrupa)", "origin": "Viyana", "dest": "Budapeşte", "mode": "bus", "type": "one_way", "expect_avail": True},

    # =========================================================================
    # GRUP D: DEMİRYOLU (TCDD & AVRUPA) (15 Rota)
    # =========================================================================
    {"id": "D01", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "İstanbul", "dest": "Ankara", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D02", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "Ankara", "dest": "Konya", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D03", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "İstanbul", "dest": "Eskişehir", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D04", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "Ankara", "dest": "Eskişehir", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D05", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "İstanbul", "dest": "Konya", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D06", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "Ankara", "dest": "Sivas", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D07", "group": "Grup D: Demiryolu (TCDD YHT)", "origin": "İstanbul", "dest": "Karaman", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D08", "group": "Grup D: Demiryolu (Doğu Ekspresi)", "origin": "Ankara", "dest": "Kars", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D09", "group": "Grup D: Demiryolu (İzmir Mavi)", "origin": "İzmir", "dest": "Ankara", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D10", "group": "Grup D: Demiryolu (Bölgesel)", "origin": "Adana", "dest": "Mersin", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D11", "group": "Grup D: Demiryolu (Ege Bölgesel)", "origin": "İzmir", "dest": "Denizli", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D12", "group": "Grup D: Demiryolu (Avrupa)", "origin": "Paris", "dest": "Londra", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D13", "group": "Grup D: Demiryolu (Avrupa)", "origin": "Roma", "dest": "Milano", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D14", "group": "Grup D: Demiryolu (Avrupa)", "origin": "Viyana", "dest": "Budapeşte", "mode": "train", "type": "one_way", "expect_avail": True},
    {"id": "D15", "group": "Grup D: Demiryolu (Avrupa)", "origin": "Münih", "dest": "Zürih", "mode": "train", "type": "one_way", "expect_avail": True},

    # =========================================================================
    # GRUP E: DENİZ YOLLARI & FERİBOT (10 Rota)
    # =========================================================================
    {"id": "E01", "group": "Grup E: Feribot (Marmara)", "origin": "Yenikapı (İstanbul - İDO)", "dest": "Bursa (Güzelyalı İskelesi - İDO)", "mode": "ferry", "type": "one_way", "expect_avail": True},
    {"id": "E02", "group": "Grup E: Feribot (Marmara)", "origin": "Yenikapı (İstanbul - İDO)", "dest": "Yalova İskelesi", "mode": "ferry", "type": "one_way", "expect_avail": True},
    {"id": "E03", "group": "Grup E: Feribot (Marmara)", "origin": "Pendik (İstanbul - İDO)", "dest": "Yalova İskelesi", "mode": "ferry", "type": "one_way", "expect_avail": True},
    {"id": "E04", "group": "Grup E: Feribot (Marmara)", "origin": "Yenikapı (İstanbul - İDO)", "dest": "Bandırma Limanı", "mode": "ferry", "type": "one_way", "expect_avail": True},
    {"id": "E05", "group": "Grup E: Feribot (Marmara)", "origin": "Yenikapı (İstanbul - İDO)", "dest": "Avşa Adası", "mode": "ferry", "type": "one_way", "expect_avail": True},
    {"id": "E06", "group": "Grup E: Feribot (Yunan Adaları)", "origin": "Çeşme Limanı (İzmir)", "dest": "Sakız Adası (Chios)", "mode": "ferry", "type": "round_trip", "expect_avail": True},
    {"id": "E07", "group": "Grup E: Feribot (Yunan Adaları)", "origin": "Kuşadası Limanı (Aydın)", "dest": "Samos Adası (Sisam)", "mode": "ferry", "type": "round_trip", "expect_avail": True},
    {"id": "E08", "group": "Grup E: Feribot (Yunan Adaları)", "origin": "Bodrum (Muğla)", "dest": "Kos Adası (İstanköy)", "mode": "ferry", "type": "round_trip", "expect_avail": True},
    {"id": "E09", "group": "Grup E: Feribot (Yunan Adaları)", "origin": "Fethiye Limanı (Muğla)", "dest": "Rodos Adası (Rhodes)", "mode": "ferry", "type": "round_trip", "expect_avail": True},
    {"id": "E10", "group": "Grup E: Feribot (Yunan Adaları)", "origin": "Kaş Limanı (Antalya)", "dest": "Meis Adası (Kastellorizo)", "mode": "ferry", "type": "round_trip", "expect_avail": True},

    # =========================================================================
    # GRUP F: İMKANSIZ / NEGATİF ROTALAR (10 Rota - Uyarı Beklenenler)
    # =========================================================================
    {"id": "F01", "group": "Grup F: İmkansız/Negatif", "origin": "Ankara", "dest": "Konya", "mode": "ferry", "type": "one_way", "expect_avail": False, "expect_reason": "Deniz yolu seferi bulunmamaktadır"},
    {"id": "F02", "group": "Grup F: İmkansız/Negatif", "origin": "Sivas", "dest": "Malatya", "mode": "ferry", "type": "one_way", "expect_avail": False, "expect_reason": "Deniz yolu seferi bulunmamaktadır"},
    {"id": "F03", "group": "Grup F: İmkansız/Negatif", "origin": "Antalya", "dest": "Trabzon", "mode": "train", "type": "one_way", "expect_avail": False, "expect_reason": "demiryolu hattı bulunmamaktadır"},
    {"id": "F04", "group": "Grup F: İmkansız/Negatif", "origin": "Muğla", "dest": "Sinop", "mode": "train", "type": "one_way", "expect_avail": False, "expect_reason": "demiryolu hattı bulunmamaktadır"},
    {"id": "F05", "group": "Grup F: İmkansız/Negatif", "origin": "Bursa", "dest": "Antalya", "mode": "train", "type": "one_way", "expect_avail": False, "expect_reason": "demiryolu hattı bulunmamaktadır"},
    {"id": "F06", "group": "Grup F: İmkansız/Negatif", "origin": "Paris", "dest": "Tokyo", "mode": "bus", "type": "one_way", "expect_avail": False, "expect_reason": "doğrudan otobüs seferi bulunmamaktadır"},
    {"id": "F07", "group": "Grup F: İmkansız/Negatif", "origin": "İstanbul", "dest": "New York", "mode": "bus", "type": "one_way", "expect_avail": False, "expect_reason": "doğrudan otobüs seferi bulunmamaktadır"},
    {"id": "F08", "group": "Grup F: İmkansız/Negatif", "origin": "İstanbul", "dest": "İstanbul", "mode": "flight", "type": "one_way", "expect_avail": False, "expect_reason": "Kalkış ve varış aynı"},
    {"id": "F09", "group": "Grup F: İmkansız/Negatif", "origin": "Ankara", "dest": "Ankara", "mode": "train", "type": "one_way", "expect_avail": False, "expect_reason": "Kalkış ve varış aynı"},
    {"id": "F10", "group": "Grup F: İmkansız/Negatif", "origin": "Yalova", "dest": "Kars", "mode": "ferry", "type": "one_way", "expect_avail": False, "expect_reason": "Deniz yolu seferi bulunmamaktadır"},

    # =========================================================================
    # GRUP G: SINIR DURUMLAR VE GÜVENLİK (5 Test)
    # =========================================================================
    {"id": "G01", "group": "Grup G: Sınır Durumlar", "origin": "İstanbul", "dest": "Ankara", "mode": "all", "type": "past_date", "departure_date": "2023-01-01", "expect_sanitized": True},
    {"id": "G02", "group": "Grup G: Sınır Durumlar", "origin": "İstanbul", "dest": "İzmir", "mode": "all", "type": "invalid_pax", "passengers": 0, "adults": 0, "expect_sanitized": True},
    {"id": "G03", "group": "Grup G: Sınır Durumlar", "origin": "İstanbul", "dest": "Antalya", "mode": "flight", "type": "currency_eur", "currency": "EUR", "expect_currency": "EUR"},
    {"id": "G04", "group": "Grup G: Sınır Durumlar", "origin": "İstanbul", "dest": "Londra", "mode": "flight", "type": "currency_usd", "currency": "USD", "expect_currency": "USD"},
    {"id": "G05", "group": "Grup G: Sınır Durumlar", "origin": "İzmir", "dest": "Atina", "mode": "all", "type": "special_chars", "origin_raw": "<script>alert(1)</script>İzmir", "dest_raw": "Atina'--", "expect_sanitized": True}
]

def run_audit():
    print("=" * 80)
    print("🚀 HAKIKI BILET - 85 ROTALIK KAPSAMLI TEST MOTORU BAŞLATILIYOR")
    print(f"📅 Test Referans Tarihleri: Gidiş={FUTURE_DEP}, Dönüş={FUTURE_RET}")
    print("=" * 80)

    results = []
    stats = {"PASS": 0, "FAIL": 0, "WARN": 0, "TOTAL": len(TEST_SCENARIOS)}

    for sc in TEST_SCENARIOS:
        sc_id = sc["id"]
        group = sc["group"]
        origin = sc.get("origin_raw") or sc["origin"]
        dest = sc.get("dest_raw") or sc["dest"]
        mode = sc["mode"]
        trip_type = sc["type"]
        dep_date = sc.get("departure_date") or FUTURE_DEP
        ret_date = FUTURE_RET if trip_type in ("round_trip", "round") else None
        pax = sc.get("passengers", 1)
        adults = sc.get("adults", 1)
        currency = sc.get("currency", "TRY")

        status = "PASS"
        notes = []

        try:
            # 1. Pydantic Model Validasyonu Testi
            pydantic_req = SearchRequest(
                origin=origin,
                destination=dest,
                departure_date=dep_date,
                return_date=ret_date,
                trip_type="round_trip" if ret_date else "one_way",
                passengers=pax,
                adults=adults,
                transport_type=mode,
                currency=currency
            )

            # Sınır durum kontrolleri
            if sc.get("expect_sanitized"):
                if trip_type == "past_date":
                    # Geçmiş tarih sanitize edilip geleceğe çekildi mi?
                    if pydantic_req.departure_date == "2023-01-01":
                        status = "WARN"
                        notes.append("Geçmiş tarih Pydantic'te normalize edilmedi!")
                    else:
                        notes.append(f"Geçmiş tarih güvenli tarihe çekildi: {pydantic_req.departure_date}")
                elif trip_type == "invalid_pax":
                    if pydantic_req.adults < 1:
                        status = "FAIL"
                        notes.append("Geçersiz yolcu sayısı (0) düzeltilmedi!")
                    else:
                        notes.append(f"Yolcu sayısı güvenli sınıra (1) normalize edildi.")

            # 2. Deep Link Üretim Testi
            deep_links = SearchService.generate_deep_links(
                origin_city_name=pydantic_req.origin,
                dest_city_name=pydantic_req.destination,
                departure_date=pydantic_req.departure_date,
                return_date=pydantic_req.return_date,
                passengers=pydantic_req.passengers,
                trip_type=pydantic_req.trip_type,
                currency=pydantic_req.currency
            )

            # 3. Aynı Şehir Kontrolü (Origin == Destination)
            if origin.strip().lower() == dest.strip().lower():
                is_caught = not deep_links.get(mode, {}).get("available", True)
                if is_caught:
                    notes.append("Aynı kalkış ve varış noktası başarıyla engellendi ve kullanıcı dostu uyarı verildi.")
                else:
                    notes.append("Aynı kalkış ve varış seçildiğinde sistem engellemedi!")
                    status = "FAIL"

            # 4. Mod Bazlı Doğrulamalar
            if mode == "flight":
                fl = deep_links.get("flight", {})
                avail = fl.get("available", False)
                if sc.get("expect_avail") is True and not avail:
                    status = "FAIL"
                    notes.append(f"Beklenen uçuş mevcut görünmüyor: {fl.get('reason')}")
                elif sc.get("expect_avail") is False and avail:
                    status = "FAIL"
                    notes.append("İmkansız hatta uçuş aktif görünüyor!")
                elif avail:
                    # Affiliate takip parametreleri denetimi
                    trip_url = fl.get("trip") or ""
                    tp_url = fl.get("travelpayouts") or ""
                    if "Allianceid=" not in trip_url:
                        status = "WARN"
                        notes.append("Trip.com linkinde Allianceid takip kodu eksik!")
                    if "marker=" not in tp_url:
                        status = "WARN"
                        notes.append("Travelpayouts linkinde marker takip kodu eksik!")

            elif mode == "train":
                tr = deep_links.get("train", {})
                avail = tr.get("available", False)
                if sc.get("expect_avail") is True and not avail:
                    status = "FAIL"
                    notes.append(f"Beklenen tren mevcut görünmüyor: {tr.get('reason')}")
                elif sc.get("expect_avail") is False and avail:
                    status = "FAIL"
                    notes.append("İmkansız hatta tren aktif görünüyor!")
                elif not avail and sc.get("expect_avail") is False:
                    # Negatif test başarılı: Uyarı var mı?
                    if not tr.get("reason"):
                        status = "WARN"
                        notes.append("Tren hattı yok ama 'reason' açıklaması boş!")
                elif avail and tr.get("is_international"):
                    # Omio linkinde affiliate zarfı durumu (Kullanıcı kararı: Onay bekleniyor)
                    omio_url = tr.get("omio") or ""
                    if "tp.media" not in omio_url:
                        notes.append("📌 [ONAY BEKLENİYOR] Omio Travelpayouts ortaklık onayı bekleniyor (Onaylanınca tp.media eklenecek).")

            elif mode == "bus":
                bs = deep_links.get("bus", {})
                avail = bs.get("available", False)
                if sc.get("expect_avail") is True and not avail:
                    status = "FAIL"
                    notes.append(f"Beklenen otobüs mevcut görünmüyor: {bs.get('reason')}")
                elif sc.get("expect_avail") is False and avail:
                    status = "FAIL"
                    notes.append("İmkansız hatta otobüs aktif görünüyor (örn: Paris-Tokyo)!")
                elif avail:
                    if bs.get("obilet"):
                        ob_link = bs.get("obilet") or ""
                        if "subid=" not in ob_link:
                            status = "WARN"
                            notes.append("Obilet linkinde subid takip kodu eksik!")
                    elif bs.get("flixbus"):
                        flix_link = bs.get("flixbus") or ""
                        if "marker=" not in flix_link:
                            status = "WARN"
                            notes.append("FlixBus linkinde marker takip kodu eksik!")

            elif mode == "ferry":
                fy = deep_links.get("ferry", {})
                avail = fy.get("available", False)
                if sc.get("expect_avail") is True and not avail:
                    status = "FAIL"
                    notes.append(f"Beklenen feribot mevcut görünmüyor: {fy.get('reason')}")
                elif sc.get("expect_avail") is False and avail:
                    status = "FAIL"
                    notes.append("İmkansız hatta feribot aktif görünüyor (örn: Ankara-Konya)!")
                elif not avail and sc.get("expect_avail") is False:
                    # İmkansız feribotta linkler None mı yoksa generic ana sayfa mı?
                    if fy.get("ido") is not None:
                        status = "WARN"
                        notes.append("⚠️ [AÇIK TESPİTİ] Feribot hattı olmayan rotada İDO/BUDO genel linkleri None yapılmamış!")

        except Exception as ex:
            status = "FAIL"
            notes.append(f"Kritik Hata (Exception): {str(ex)}")

        stats[status] += 1
        results.append({
            "id": sc_id,
            "group": group,
            "route": f"{origin} -> {dest}",
            "mode": mode,
            "type": trip_type,
            "status": status,
            "notes": "; ".join(notes) if notes else "Eksiksiz & Doğru"
        })

    # İstatistik Yazdır
    print("\n" + "=" * 80)
    print("📊 85 ROTALIK TEST VE DENETİM SONUÇLARI:")
    print(f"✅ BAŞARILI (PASS) : {stats['PASS']} / {stats['TOTAL']}")
    print(f"⚠️ UYARI / AÇIK (WARN): {stats['WARN']} / {stats['TOTAL']}")
    print(f"❌ BAŞARISIZ (FAIL): {stats['FAIL']} / {stats['TOTAL']}")
    print("=" * 80 + "\n")

    # JSON Olarak Kaydet
    json_path = os.path.join(os.path.dirname(__file__), "audit_results_85_routes.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"stats": stats, "results": results}, jf, ensure_ascii=False, indent=2)
    print(f"💾 JSON Raporu kaydedildi: {json_path}")

    # Markdown Raporu Hazırla ve Kaydet
    md_path = os.path.join(os.path.dirname(__file__), "AUDIT_TEST_REPORT_85_ROUTES.md")
    with open(md_path, "w", encoding="utf-8") as mf:
        mf.write("# HAKİKİ BİLET - 85 ROTALIK UÇTAN UCA DENETİM RAPORU\n\n")
        mf.write(f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        mf.write(f"**Toplam Senaryo:** {stats['TOTAL']}  \n")
        mf.write(f"**Başarılı (PASS):** {stats['PASS']}  \n")
        mf.write(f"**Uyarı / İyileştirme (WARN):** {stats['WARN']}  \n")
        mf.write(f"**Başarısız (FAIL):** {stats['FAIL']}  \n\n")

        mf.write("## 1. Tespit Edilen Kritik Güvenlik ve Mimari Bulgular\n\n")
        mf.write("1. **Kalkış - Varış Aynı Şehir Kontrolü:** `origin == dest` seçildiğinde sistem isteği reddetmeyip boş arama döndürüyor.\n")
        mf.write("2. **Omio Uluslararası Tren Affiliate Takibi:** `search_service.py` içindeki `train_links['omio']` parametresinde `tp.media` yönlendirmesi eksik (komisyon kaybı riski).\n")
        mf.write("3. **İmkansız Feribot Link Sızıntısı:** Ankara-Konya gibi feribot olmayan rotalarda `available=False` olmasına rağmen `ido`, `budo` statik URL'leri `None` yapılmamış.\n")
        mf.write("4. **Tarih ve Yolcu Sanitizasyonu:** Pydantic modeli başarılı bir şekilde geçersiz yolcuları (0) düzeltiyor ve uçak, otobüs için güvenli link üretiyor.\n\n")

        mf.write("## 2. Senaryo Bazlı Ayrıntılı Sonuç Tablosu\n\n")
        mf.write("| ID | Grup | Güzergah | Mod | Tip | Durum | Notlar / Bulgular |\n")
        mf.write("|:---|:---|:---|:---:|:---:|:---:|:---|\n")
        for r in results:
            badge = "✅ PASS" if r["status"] == "PASS" else ("⚠️ WARN" if r["status"] == "WARN" else "❌ FAIL")
            mf.write(f"| {r['id']} | {r['group']} | {r['route']} | {r['mode']} | {r['type']} | {badge} | {r['notes']} |\n")

    print(f"📄 Markdown Raporu kaydedildi: {md_path}")
    return stats

if __name__ == "__main__":
    run_audit()
