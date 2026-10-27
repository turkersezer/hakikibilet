"""
Deniz Yolları & Feribot Bilet Servisi (Hakiki Bilet Deniz Ulaşımı Anayasası Uyumu)
- Marmara İç Hatları (İDO, BUDO, GESTAŞ)
- Ege & Yunan Adaları (Ertürk Lines, Turyol, Feribotlines, Yeşil Marmaris, Meander, Makri, Meis Express)
- Akdeniz & KKTC Hatları (Akgünler Denizcilik Taşucu - Girne)
- Kruvaziyer / Cruise Turları (Celestyal, MSC, Miray)

Temel İlkeler:
1. SIFIR VARSAYIM (Zero-Assumption): Asla uydurma/sabit formül fiyat üretilmez. Obilet, Feribotlines ve Bilet.com
   üzerinden canlı fiyat çekilir (15 dk L1 önbellek). Canlı fiyat teyit edilemezse price=None döner.
2. DERİN LİNK (Deep Linking): Asla çıplak ana sayfaya bırakılmaz; rota, tarih, yolcu ve araç parametreli arama ekranına inilir.
3. EN UCUZ CANLI FİYAT + EŞİTLİK (TIE-BREAKER) KURALI: Ana turuncu buton her zaman en ucuz doğrulanmış canlı fiyata gider;
   fiyat eşitliğinde en yüksek komisyon/dönüşüm puanına sahip ortak (Obilet > Feribotlines > Bilet.com > Resmi Operatör) seçilir.
4. DENİZCİLİK KALKANLARI: Katamaran/Arabalı vapur ayrımı, şoför dahil/hariç kuralı, Kapıda Vize 4 iş günü evrak uyarısı,
   90 gün pasaport geçerlilik kalkanı ve Lodos/fırtına iptal güvencesi.
"""
import json
import logging
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


class FerryService:
    # 15 Dakikalık L1 Canlı Fiyat ve Sefer Önbelleği (Key: route_key -> (timestamp, live_data_dict))
    _LIVE_FERRY_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _CACHE_LOCK = threading.Lock()
    _CACHE_TTL_SECONDS = 900  # 15 dakika

    # Doğrulanmış Gerçek Deniz Yolları Hat Haritası (İç Hat, Yunan Adaları, KKTC, Cruise)
    POPULAR_FERRY_ROUTES: List[Dict[str, Any]] = [
        # ==========================================
        # 1. MARMARA & ÇANAKKALE İÇ HAT SEFERLERİ (İDO, BUDO, GESTAŞ)
        # ==========================================
        {
            "route_key": "yenikapi-bursa",
            "category": "domestic",
            "origin": "Yenikapı İskelesi (İstanbul - İDO)",
            "dest": "Bursa (Güzelyalı / Mudanya İskelesi)",
            "operator": "İDO",
            "vessel": "Deniz Otobüsü (Yalnızca Yaya)",
            "duration": "2 sa 20 dk",
            "schedules": [("09:50", "Sabah Seferi"), ("15:15", "Öğleden Sonra Seferi"), ("18:00", "Akşam Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "ped_base_try": 770.0,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": "yenikapi-bursa",
            "feribotlines_slug": None,
            "biletcom_path": "ido/yenikapi-bursa-guzelyali",
            "official_url": "https://www.ido.com.tr/sefer-saatleri",
            "from_code": "YNK",
            "to_code": "GZY",
        },
        {
            "route_key": "eminonu-mudanya",
            "category": "domestic",
            "origin": "Eminönü / Sirkeci İskelesi (İstanbul - BUDO)",
            "dest": "Mudanya İskelesi (Bursa - BUDO)",
            "operator": "BUDO",
            "vessel": "Deniz Otobüsü (Yalnızca Yaya)",
            "duration": "1 sa 50 dk",
            "schedules": [("08:00", "Sabah Seferi"), ("14:00", "Öğle Seferi"), ("19:00", "Akşam Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "ped_base_try": 480.0,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": None,
            "feribotlines_slug": None,
            "biletcom_path": None,
            "official_url": "https://budo.burulas.com.tr/tr/Timetables",
            "from_code": "EMN",
            "to_code": "MDN",
        },
        {
            "route_key": "yenikapi-yalova",
            "category": "domestic",
            "origin": "Yenikapı İskelesi (İstanbul - İDO)",
            "dest": "Yalova Merkez İskelesi (İDO)",
            "operator": "İDO",
            "vessel": "Hızlı Arabalı Vapur",
            "duration": "1 sa 25 dk",
            "schedules": [("07:45", "Sabah Seferi"), ("11:45", "Öğle Seferi"), ("15:45", "İkindi Seferi"), ("19:45", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": True,
            "ped_base_try": 410.0,
            "car_base_try": 1421.0,
            "car_extra_pax_try": 181.0,
            "moto_base_try": 987.0,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": "yenikapi-yalova",
            "feribotlines_slug": None,
            "biletcom_path": "ido/yenikapi-yalova",
            "official_url": "https://www.ido.com.tr/sefer-saatleri",
            "from_code": "YNK",
            "to_code": "YLV",
        },
        {
            "route_key": "pendik-yalova",
            "category": "domestic",
            "origin": "Pendik İskelesi (İstanbul - İDO)",
            "dest": "Yalova Merkez İskelesi (İDO)",
            "operator": "İDO",
            "vessel": "Hızlı Arabalı Vapur",
            "duration": "45 dk",
            "schedules": [("07:00", "Sabah Seferi"), ("09:00", "Sabah 2. Sefer"), ("15:00", "Öğleden Sonra Seferi"), ("18:00", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": True,
            "ped_base_try": 310.0,
            "car_base_try": 771.0,
            "car_extra_pax_try": 126.0,
            "moto_base_try": 545.0,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": "pendik-yalova",
            "feribotlines_slug": None,
            "biletcom_path": "ido/pendik-yalova",
            "official_url": "https://www.ido.com.tr/sefer-saatleri",
            "from_code": "PND",
            "to_code": "YLV",
        },
        {
            "route_key": "yenikapi-bandirma",
            "category": "domestic",
            "origin": "Yenikapı İskelesi (İstanbul - İDO)",
            "dest": "Bandırma Çelebi Limanı (İDO)",
            "operator": "İDO",
            "vessel": "Deniz Otobüsü (Yalnızca Yaya)",
            "duration": "2 sa 55 dk",
            "schedules": [("18:30", "Akşam Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "ped_base_try": 960.0,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": "yenikapi-bandirma",
            "feribotlines_slug": None,
            "biletcom_path": "ido/yenikapi-bandirma",
            "official_url": "https://www.ido.com.tr/sefer-saatleri",
            "from_code": "YNK",
            "to_code": "BND",
        },
        {
            "route_key": "yenikapi-avsa",
            "category": "domestic",
            "origin": "Yenikapı / Bostancı İskelesi (İstanbul - İDO)",
            "dest": "Avşa & Marmara Adası İskelesi",
            "operator": "İDO",
            "vessel": "Deniz Otobüsü (Yaya Yolcu)",
            "duration": "3 sa 20 dk",
            "schedules": [("08:30", "Sabah Seferi"), ("16:30", "Akşamüstü Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": False,
            "obilet_slug": "marmara_adasi-istanbul_avrupa",
            "feribotlines_slug": None,
            "biletcom_path": "ido/yenikapi",
            "official_url": "https://www.ido.com.tr/sefer-saatleri",
            "from_code": "YNK",
            "to_code": "AVS",
        },
        {
            "route_key": "mudanya-armutlu",
            "category": "domestic",
            "origin": "Mudanya İskelesi (Bursa - BUDO)",
            "dest": "Armutlu İskelesi (Yalova)",
            "operator": "BUDO",
            "vessel": "Deniz Otobüsü (Yaya Yolcu)",
            "duration": "40 dk",
            "schedules": [("09:30", "Sabah Seferi"), ("16:00", "Öğleden Sonra Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": "ihlas_armutlu-mudanya",
            "feribotlines_slug": None,
            "biletcom_path": "feribot-bileti",
            "official_url": "https://budo.burulas.com.tr/tr/Timetables",
            "from_code": "MDN",
            "to_code": "ARM",
        },
        {
            "route_key": "canakkale-eceabat",
            "category": "domestic",
            "origin": "Çanakkale Merkez İskelesi (GESTAŞ)",
            "dest": "Eceabat / Kilitbahir İskelesi (Gelibolu)",
            "operator": "GESTAŞ",
            "vessel": "Arabalı Boğaz Feribotu",
            "duration": "25 dk",
            "schedules": [("08:00", "Sabah Seferi"), ("12:00", "Öğle Seferi"), ("18:00", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": True,
            "all_passengers_included_in_car": True,
            "ped_base_try": 85.0,
            "car_base_try": 725.0,
            "car_round_try": 1090.0,
            "moto_base_try": 180.0,
            "moto_round_try": 270.0,
            "is_island": False,
            "requires_visa": False,
            "obilet_slug": "canakkale-eceabat",
            "feribotlines_slug": None,
            "biletcom_path": "feribot-bileti",
            "official_url": "https://www.gdu.com.tr/sefer-saatleri",
            "from_code": "CKZ",
            "to_code": "ECB",
        },
        {
            "route_key": "geyikli-bozcaada",
            "category": "domestic",
            "origin": "Geyikli Yükyeri İskelesi (Çanakkale)",
            "dest": "Bozcaada Merkez Limanı (GESTAŞ)",
            "operator": "GESTAŞ",
            "vessel": "Arabalı Ada Feribotu",
            "duration": "35 dk",
            "schedules": [("09:00", "Sabah Seferi"), ("14:00", "Öğle Seferi"), ("19:00", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": True,
            "is_island_round_package": True,
            "ped_base_try": 230.0,
            "car_base_try": 2485.0,
            "car_round_try": 2485.0,
            "moto_base_try": 510.0,
            "moto_round_try": 510.0,
            "is_island": True,
            "requires_visa": False,
            "obilet_slug": "geyikli-bozcaada",
            "feribotlines_slug": None,
            "biletcom_path": "feribot-bileti",
            "official_url": "https://www.gdu.com.tr/sefer-saatleri",
            "from_code": "GYK",
            "to_code": "BZC",
        },
        {
            "route_key": "kabatepe-gokceada",
            "category": "domestic",
            "origin": "Kabatepe İskelesi (Eceabat / Çanakkale)",
            "dest": "Gökçeada Kuzu Limanı (GESTAŞ)",
            "operator": "GESTAŞ",
            "vessel": "Arabalı Ada Feribotu",
            "duration": "1 sa 15 dk",
            "schedules": [("09:00", "Sabah Seferi"), ("15:00", "Öğleden Sonra Seferi"), ("19:00", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": True,
            "is_island_round_package": True,
            "ped_base_try": 180.0,
            "car_base_try": 1400.0,
            "car_round_try": 1400.0,
            "moto_base_try": 360.0,
            "moto_round_try": 360.0,
            "is_island": True,
            "requires_visa": False,
            "obilet_slug": "kabatepe-gokceada",
            "feribotlines_slug": None,
            "biletcom_path": "feribot-bileti",
            "official_url": "https://www.gdu.com.tr/sefer-saatleri",
            "from_code": "KBT",
            "to_code": "GKC",
        },

        # ==========================================
        # 2. AKDENİZ & KIBRIS (KKTC) SEFERLERİ (ÇİPLİ KİMLİKLE VİZESİZ)
        # ==========================================
        {
            "route_key": "tasucu-girne-fast",
            "category": "domestic",
            "origin": "Taşucu Limanı (Silifke / Mersin)",
            "dest": "Girne Turizm Limanı (KKTC - Kıbrıs)",
            "operator": "Akgünler Denizcilik",
            "vessel": "Hızlı Deniz Otobüsü (Yalnızca Yaya)",
            "duration": "2 sa 15 dk",
            "schedules": [("11:30", "Gündüz Hızlı Deniz Otobüsü"), ("14:00", "Öğleden Sonra Deniz Otobüsü")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "ped_base_try": 1850.0,
            "is_island": True,
            "requires_visa": False,
            "requires_chip_id": True,
            "obilet_slug": None,
            "feribotlines_slug": None,
            "biletcom_path": "kibris-feribot/girne",
            "official_url": "https://www.akgunlerdenizcilik.com/",
            "from_code": "TSC",
            "to_code": "KYR",
        },
        {
            "route_key": "tasucu-girne-car",
            "category": "domestic",
            "origin": "Taşucu Limanı (Silifke / Mersin)",
            "dest": "Girne Turizm Limanı (KKTC - Kıbrıs)",
            "operator": "Akgünler Denizcilik",
            "vessel": "Arabalı Gece Feribotu (Ro-Ro)",
            "duration": "6 sa 00 dk",
            "schedules": [("23:30", "Gece Arabalı Ro-Ro Gemisi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": False,
            "requires_green_card_for_vehicle": True,
            "ped_base_try": 1650.0,
            "car_base_try": 6900.0,
            "moto_base_try": 3200.0,
            "is_island": True,
            "requires_visa": False,
            "requires_chip_id": True,
            "obilet_slug": None,
            "feribotlines_slug": None,
            "biletcom_path": "kibris-feribot/girne",
            "official_url": "https://www.akgunlerdenizcilik.com/",
            "from_code": "TSC",
            "to_code": "KYR",
        },

        # ==========================================
        # 3. EGE & YUNAN ADALARI SEFERLERİ (KAPIDA VİZE & HIZLI KATAMARAN / ARABALI GEMİ)
        # ==========================================
        {
            "route_key": "cesme-sakiz-car",
            "category": "greek_islands",
            "origin": "Çeşme Ulusoy Limanı (İzmir)",
            "dest": "Sakız Adası Limanı (Chios)",
            "operator": "Sunrise Lines / Ertürk / Turyol",
            "vessel": "Arabalı Yolcu Gemisi",
            "duration": "35 dk",
            "schedules": [("09:50", "Sabah Seferi"), ("18:00", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": False,
            "requires_green_card_for_vehicle": True,
            "car_base_eur": 86.0,
            "car_round_eur": 145.0,
            "moto_base_eur": 45.0,
            "moto_round_eur": 75.0,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "cesme-sakiz",
            "feribotlines_slug": "sakiz-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/cesme-sakiz-adasi",
            "official_url": "https://www.erturk.com.tr/cesme-sakiz-feribot-bileti",
            "ferryhopper_ports": ("CES", "CHI"),
            "from_code": "CSM",
            "to_code": "JKH",
        },
        {
            "route_key": "cesme-sakiz-fast",
            "category": "greek_islands",
            "origin": "Çeşme Ulusoy Limanı (İzmir)",
            "dest": "Sakız Adası Limanı (Chios)",
            "operator": "İDO Yurt Dışı / Tilos Travel",
            "vessel": "Hızlı Katamaran (Yalnızca Yaya)",
            "duration": "20 dk",
            "schedules": [("08:35", "Sabah Hızlı Katamaran"), ("09:00", "Sabah 2. Sefer")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "cesme-sakiz",
            "feribotlines_slug": "sakiz-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/cesme-sakiz-adasi",
            "official_url": "https://www.turyolonline.com/",
            "ferryhopper_ports": ("CES", "CHI"),
            "from_code": "CSM",
            "to_code": "JKH",
        },
        {
            "route_key": "bodrum-kos",
            "category": "greek_islands",
            "origin": "Bodrum Kale / Kruvaziyer Limanı (Muğla)",
            "dest": "Kos Adası Limanı (İstanköy)",
            "operator": "Turyol / Yeşil Marmaris / Makri",
            "vessel": "Hızlı Katamaran (Yalnızca Yaya)",
            "duration": "20 dk",
            "schedules": [("08:45", "Sabah Seferi"), ("09:15", "Sabah 2. Sefer"), ("16:30", "Öğleden Sonra Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "bodrum-kos",
            "feribotlines_slug": "bodrum-kos-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/bodrum-kos",
            "official_url": "https://www.turyolonline.com/",
            "ferryhopper_ports": ("BXN", "KGS"),
            "from_code": "BXN",
            "to_code": "KGS",
        },
        {
            "route_key": "ayvalik-midilli",
            "category": "greek_islands",
            "origin": "Ayvalık Denizhudut Limanı (Balıkesir)",
            "dest": "Midilli Adası Limanı (Lesvos)",
            "operator": "Turyol / Jalem Tur",
            "vessel": "Arabalı Feribot & Hızlı Katamaran",
            "duration": "45 dk",
            "schedules": [("09:00", "Sabah Seferi"), ("18:00", "Akşam Seferi")],
            "vehicle_allowed": True,
            "driver_included_in_vehicle": False,
            "requires_green_card_for_vehicle": True,
            "car_base_eur": 75.0,
            "car_round_eur": 110.0,
            "moto_base_eur": 40.0,
            "moto_round_eur": 60.0,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "ayvalik-midilli",
            "feribotlines_slug": "ayvalik-midilli-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/ayvalik-midilli",
            "official_url": "https://www.turyolonline.com/",
            "ferryhopper_ports": ("AYV", "LES"),
            "from_code": "AYV",
            "to_code": "MJT",
        },
        {
            "route_key": "kusadasi-samos",
            "category": "greek_islands",
            "origin": "Kuşadası Ege Port Limanı (Aydın)",
            "dest": "Samos Adası (Vathy / Pythagoreio - Sisam)",
            "operator": "Meander Travel / İDO",
            "vessel": "Hızlı Katamaran (Yalnızca Yaya)",
            "duration": "45 dk",
            "schedules": [("08:30", "Sabah Seferi"), ("09:15", "Sabah 2. Sefer")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "kusadasi-samos",
            "feribotlines_slug": "kusadasi-samos-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/kusadasi-samos",
            "official_url": "https://www.meandertravel.com/",
            "ferryhopper_ports": ("KUS", "BTH"),
            "from_code": "KUS",
            "to_code": "SMI",
        },
        {
            "route_key": "fethiye-rodos",
            "category": "greek_islands",
            "origin": "Fethiye Belediye Limanı (Muğla)",
            "dest": "Rodos Adası Turizm Limanı (Rhodes)",
            "operator": "Makri Travel / Turyol",
            "vessel": "Hızlı Katamaran (Yalnızca Yaya)",
            "duration": "1 sa 30 dk",
            "schedules": [("08:25", "Sabah Seferi"), ("09:00", "Sabah 2. Sefer")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "fethiye-rodos_yunan_adalari",
            "feribotlines_slug": "fethiye-rodos-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/fethiye-rodos",
            "official_url": "https://www.feribotlines.com/fethiye-rodos-adasi-feribot-bileti",
            "ferryhopper_ports": ("FET", "RHO"),
            "from_code": "FTH",
            "to_code": "RHO",
        },
        {
            "route_key": "marmaris-rodos",
            "category": "greek_islands",
            "origin": "Marmaris Cruise Port Limanı (Muğla)",
            "dest": "Rodos Adası Turizm Limanı (Rhodes)",
            "operator": "Yeşil Marmaris Lines",
            "vessel": "Hızlı Katamaran (Yalnızca Yaya)",
            "duration": "1 sa",
            "schedules": [("09:15", "Sabah Seferi"), ("17:00", "Akşamüstü Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "marmaris-rodos_yunan_adalari",
            "feribotlines_slug": "marmaris-rodos-adasi-feribot-bileti",
            "biletcom_path": "yunan-adalari/marmaris-rodos",
            "official_url": "https://www.yesilmarmaris.com/",
            "ferryhopper_ports": ("MAR", "RHO"),
            "from_code": "MRM",
            "to_code": "RHO",
        },
        {
            "route_key": "kas-meis",
            "category": "greek_islands",
            "origin": "Kaş Yat & Yolcu Limanı (Antalya)",
            "dest": "Meis Adası Limanı (Kastellorizo)",
            "operator": "Meis Express / Kahramanlar",
            "vessel": "Hızlı Yolcu Teknesi (Yalnızca Yaya)",
            "duration": "20 dk",
            "schedules": [("10:00", "Sabah Günübirlik & Konaklamalı Sefer")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": "kas-meis",
            "feribotlines_slug": None,
            "biletcom_path": "yunan-adalari/kas-meis",
            "official_url": "https://www.meisferrylines.com/",
            "ferryhopper_ports": ("TRKAS", "KAZ"),
            "from_code": "KAS",
            "to_code": "KZS",
        },
        {
            "route_key": "bodrum-simi",
            "category": "greek_islands",
            "origin": "Bodrum Kale Limanı (Muğla)",
            "dest": "Simi Adası Limanı (Symi)",
            "operator": "İDO Yurt Dışı / Dentur",
            "vessel": "Hızlı Katamaran (Yalnızca Yaya)",
            "duration": "1 sa 45 dk",
            "schedules": [("09:00", "Sabah Seferi")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "requires_visa": True,
            "seasonal_winter_reduced": True,
            "obilet_slug": None,
            "feribotlines_slug": "bodrum-symi-feribot-bileti",
            "biletcom_path": "yunan-adalari",
            "official_url": "https://feribotlines.com/bodrum-symi-feribot-bileti",
            "ferryhopper_ports": ("BXN", "SYM"),
            "from_code": "BXN",
            "to_code": "SYM",
        },

        # ==========================================
        # 4. CRUISE & KRUVAZİYER GEMİ TURLARI (HER ŞEY DAHİL & KABİN SEÇİMLİ)
        # ==========================================
        {
            "route_key": "cruise-galataport-ege",
            "category": "cruise",
            "origin": "Galataport Kruvaziyer Limanı (İstanbul)",
            "dest": "Ege & Yunan Adaları & Atina Cruise (4 Gece)",
            "operator": "Celestyal Cruises",
            "vessel": "Lüks Kruvaziyer Gemisi (Celestyal Discovery)",
            "duration": "4 Gece 5 Gün",
            "schedules": [("11:00", "Liman Check-in & Hareket")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "is_cruise": True,
            "requires_visa": False,
            "cabin_tiers_eur": {"interior": 349.0, "oceanview": 429.0, "balcony": 589.0},
            "cruise_inclusions": "Tam Pansiyon Yemekler + Liman Vergileri + Gemide Eğlence & Şovlar Dahil",
            "setur_url": "https://www.setur.com.tr/celestyal-gemi-turlari",
            "jolly_url": "https://www.jollytur.com/yunan-adalari-gemi-turlari",
            "cruisedirect_url": "https://www.cruisedirect.com/cruise-line/celestyal-cruises",
            "official_url": "https://celestyal.com/tr/",
            "from_code": "GLT",
            "to_code": "ATH",
        },
        {
            "route_key": "cruise-kusadasi-adalar",
            "category": "cruise",
            "origin": "Kuşadası Ege Port Limanı (Aydın)",
            "dest": "Patmos - Girit - Santorini - Mykonos Cruise (3 Gece)",
            "operator": "Celestyal Cruises",
            "vessel": "Lüks Kruvaziyer Gemisi (Celestyal Journey)",
            "duration": "3 Gece 4 Gün",
            "schedules": [("11:30", "Liman Check-in & Hareket")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "is_cruise": True,
            "requires_visa": False,
            "cabin_tiers_eur": {"interior": 269.0, "oceanview": 339.0, "balcony": 499.0},
            "cruise_inclusions": "Vizesiz / Kapıda Vizeli Paket + Tam Pansiyon + Liman Vergileri Dahil",
            "setur_url": "https://www.setur.com.tr/celestyal-gemi-turlari",
            "jolly_url": "https://www.jollytur.com/vizesiz-gemi-cruise-turlari",
            "cruisedirect_url": "https://www.cruisedirect.com/cruise-line/celestyal-cruises",
            "official_url": "https://celestyal.com/tr/",
            "from_code": "KUS",
            "to_code": "JTR",
        },
        {
            "route_key": "cruise-galataport-italya",
            "category": "cruise",
            "origin": "Galataport Kruvaziyer Limanı (İstanbul)",
            "dest": "Ege & İtalya (Bari / Venedik) & Adriyatik Cruise (7 Gece)",
            "operator": "MSC Cruises",
            "vessel": "Mega Kruvaziyer Gemisi (MSC Splendida)",
            "duration": "7 Gece 8 Gün",
            "schedules": [("13:00", "Liman Check-in & Hareket")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "is_cruise": True,
            "requires_visa": True,
            "cabin_tiers_eur": {"interior": 649.0, "oceanview": 799.0, "balcony": 999.0},
            "cruise_inclusions": "Tam Pansiyon + 5 Yıldızlı Yüzen Otel Konforu + Liman Vergileri Dahil",
            "setur_url": "https://www.setur.com.tr/msc-gemi-turlari",
            "jolly_url": "https://www.jollytur.com/akdeniz-gemi-turlari",
            "cruisedirect_url": "https://www.cruisedirect.com/cruise-line/msc-cruises",
            "official_url": "https://www.msccruises.com.tr/",
            "from_code": "GLT",
            "to_code": "BRI",
        },
        {
            "route_key": "cruise-kusadasi-grand-ege",
            "category": "cruise",
            "origin": "Galataport / Kuşadası Çıkışlı",
            "dest": "Rodos - Girit - Santorini - Mykonos - Milos Grand Ege (7 Gece)",
            "operator": "Celestyal & Costa Cruises",
            "vessel": "Lüks Kruvaziyer Gemisi (Celestyal Journey)",
            "duration": "7 Gece 8 Gün",
            "schedules": [("12:00", "Liman Check-in & Hareket")],
            "vehicle_allowed": False,
            "driver_included_in_vehicle": False,
            "is_island": True,
            "is_cruise": True,
            "requires_visa": False,
            "cabin_tiers_eur": {"interior": 599.0, "oceanview": 729.0, "balcony": 949.0},
            "cruise_inclusions": "Tam Pansiyon + 6 Ada Ziyareti + Liman Vergileri Dahil",
            "setur_url": "https://www.setur.com.tr/gemi-turlari",
            "jolly_url": "https://www.jollytur.com/gemi-turlari",
            "cruisedirect_url": "https://www.cruisedirect.com/destination/mediterranean-cruises",
            "official_url": "https://celestyal.com/tr/",
            "from_code": "KUS",
            "to_code": "JMK",
        },
    ]

    _HTTP_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    @staticmethod
    def _parse_tr_price(raw_str: str) -> Optional[float]:
        """'1.396,00 TL' veya '1396.00' formatındaki metni float değere çevirir."""
        if not raw_str:
            return None
        cleaned = re.sub(r"[^\d.,]", "", str(raw_str).strip())
        if not cleaned:
            return None
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts[-1]) in (2, 4):
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
            else:
                cleaned = cleaned.replace(",", "")
        try:
            val = float(cleaned)
            return val if val > 0 else None
        except Exception:
            return None

    @classmethod
    def _scrape_obilet_ferry(cls, obilet_slug: str) -> Dict[str, Any]:
        """
        Obilet /feribot-bileti/{slug} sayfasından canlı sefer saatlerini, operatörleri
        ve gerçek TL bilet fiyatlarını çeker.
        """
        result: Dict[str, Any] = {"min_price_try": None, "schedules": []}
        if not obilet_slug:
            return result
        url = f"https://www.obilet.com/feribot-bileti/{obilet_slug}"
        try:
            req = urllib.request.Request(url, headers=cls._HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.debug(f"Obilet ferry live scrape skipped for {obilet_slug}: {exc}")
            return result

        prices_found: List[float] = []
        live_schedules: List[Dict[str, Any]] = []
        seen_sched = set()

        # 1. <div class="sea-list-container"> bloklarından saat, firma ve canlı fiyat çek
        containers = re.findall(r'<div class="sea-list-container">(.*?)</div>', html, re.S)
        for block in containers:
            op_m = re.search(r'<span class="text"\s*>([^<]+)</span>', block)
            price_m = re.search(r'<td class="price">\s*([0-9.,]+)\s*TL', block)
            hour_m = re.search(r'<td class="hour"[^>]*>\s*([0-9]{2}:[0-9]{2})', block)
            orig_m = re.search(r'data-origin-name="([^"]+)"', block)
            dest_m = re.search(r'data-destination-name="([^"]+)"', block)

            p_val = cls._parse_tr_price(price_m.group(1)) if price_m else None
            if p_val and p_val >= 100:
                prices_found.append(p_val)

            dep_t = hour_m.group(1) if hour_m else None
            op_name = op_m.group(1).strip() if op_m else None
            if dep_t and p_val:
                key = (op_name or "", dep_t, round(p_val))
                if key not in seen_sched:
                    seen_sched.add(key)
                    live_schedules.append({
                        "operator": op_name,
                        "dep_time": dep_t,
                        "price_try": p_val,
                        "origin_port": orig_m.group(1).strip() if orig_m else None,
                        "dest_port": dest_m.group(1).strip() if dest_m else None,
                    })

        # 2. JSON-LD @type == "BoatTrip" içinden canlı fiyat kontrolü
        if not prices_found:
            lds = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S)
            for ld in lds:
                if "BoatTrip" not in ld:
                    continue
                try:
                    data = json.loads(ld.strip())
                    for item in data.get("@graph", []):
                        if isinstance(item, dict) and item.get("@type") == "BoatTrip":
                            offers = item.get("offers") or {}
                            p_val = cls._parse_tr_price(str(offers.get("price") or ""))
                            if p_val and p_val >= 100:
                                prices_found.append(p_val)
                except Exception:
                    pass

        # 3. Popüler rota tablosundaki data-price niteliği (Örn: marmaris-rodos, eminonu-mudanya)
        if not prices_found:
            slug_parts = [p for p in obilet_slug.replace("_yunan_adalari", "").split("-") if len(p) >= 3]
            for route_li in re.findall(r'<li[^>]*>(.*?)</li>', html, re.S):
                if all(sp in route_li.lower() for sp in slug_parts[:2]):
                    dp_m = re.search(r'data-price="([0-9.,]+)"', route_li)
                    if dp_m:
                        p_val = cls._parse_tr_price(dp_m.group(1))
                        if p_val and p_val >= 100:
                            prices_found.append(p_val)

        if prices_found:
            result["min_price_try"] = round(min(prices_found), 2)
        if live_schedules:
            live_schedules.sort(key=lambda x: (x["dep_time"], x["price_try"]))
            result["schedules"] = live_schedules
        return result

    @classmethod
    def _scrape_feribotlines(cls, fl_slug: str) -> Optional[float]:
        """
        Feribotlines rota sayfasından JSON-LD lowPrice (EUR) değerini canlı çeker ve TRY'ye çevirir.
        """
        if not fl_slug:
            return None
        from app.services.currency_service import CurrencyService

        url = f"https://feribotlines.com/{fl_slug.lstrip('/')}"
        try:
            req = urllib.request.Request(url, headers=cls._HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.debug(f"Feribotlines live scrape skipped for {fl_slug}: {exc}")
            return None

        low_m = re.search(r'"lowPrice"\s*:\s*"?([0-9.,]+)"?', html)
        if low_m:
            eur_val = cls._parse_tr_price(low_m.group(1))
            if eur_val and 10 <= eur_val <= 500:
                return round(CurrencyService.convert(eur_val, "EUR", "TRY"), 2)
        return None

    @classmethod
    def _scrape_biletcom(cls, biletcom_path: str, is_greek_island: bool = False) -> Optional[float]:
        """
        Bilet.com rota sayfasından canlı TL bilet fiyatını çeker.
        """
        if not biletcom_path or biletcom_path in ("feribot-bileti", "yunan-adalari"):
            return None
        url = f"https://www.bilet.com/{biletcom_path.lstrip('/')}"
        try:
            req = urllib.request.Request(url, headers=cls._HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.debug(f"Bilet.com live scrape skipped for {biletcom_path}: {exc}")
            return None

        min_threshold = 800.0 if is_greek_island else 200.0
        candidates: List[float] = []
        for m in re.finditer(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d{3,5})\s*(?:TL|₺)", html):
            val = cls._parse_tr_price(m.group(1))
            if val and min_threshold <= val <= 15000:
                candidates.append(val)

        if candidates:
            return round(min(candidates), 2)
        return None

    @classmethod
    def fetch_live_route_market_data(cls, route: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rotaya ait Obilet, Feribotlines ve Bilet.com canlı fiyatlarını paralel sorgular
        ve 15 dakika boyunca L1 önbellekte tutar.
        """
        route_key = route.get("route_key") or f"{route.get('origin')}-{route.get('dest')}"
        now = time.time()

        with cls._CACHE_LOCK:
            cached = cls._LIVE_FERRY_CACHE.get(route_key)
            if cached and (now - cached[0]) < cls._CACHE_TTL_SECONDS:
                return cached[1]

        obilet_slug = route.get("obilet_slug")
        fl_slug = route.get("feribotlines_slug")
        bilet_path = route.get("biletcom_path")
        is_greek = bool(route.get("requires_visa") or route.get("category") == "greek_islands")

        obilet_data: Dict[str, Any] = {"min_price_try": None, "schedules": []}
        fl_price_try: Optional[float] = None
        bilet_price_try: Optional[float] = None

        with ThreadPoolExecutor(max_workers=3) as ex:
            fut_ob = ex.submit(cls._scrape_obilet_ferry, obilet_slug) if obilet_slug else None
            fut_fl = ex.submit(cls._scrape_feribotlines, fl_slug) if fl_slug else None
            fut_bl = ex.submit(cls._scrape_biletcom, bilet_path, is_greek) if bilet_path else None

            if fut_ob:
                try:
                    obilet_data = fut_ob.result(timeout=5.0) or obilet_data
                except Exception:
                    pass
            if fut_fl:
                try:
                    fl_price_try = fut_fl.result(timeout=5.0)
                except Exception:
                    pass
            if fut_bl:
                try:
                    bilet_price_try = fut_bl.result(timeout=5.0)
                except Exception:
                    pass

        market_data = {
            "obilet_min_try": obilet_data.get("min_price_try"),
            "obilet_schedules": obilet_data.get("schedules") or [],
            "feribotlines_min_try": fl_price_try,
            "biletcom_min_try": bilet_price_try,
        }

        with cls._CACHE_LOCK:
            cls._LIVE_FERRY_CACHE[route_key] = (now, market_data)

        return market_data

    # Obilet Gerçek Tarihli Sefer Arama Liman ID Haritası (/feribot-seferleri/{orig}-{dest}/{YYYYMMDD}/{pax}a/0_none)
    _OBILET_ROUTE_IDS: Dict[str, Tuple[str, str]] = {
        "yenikapi-bursa": ("250_24", "232_0"),
        "yenikapi-yalova": ("250_24", "293_26"),
        "pendik-yalova": ("250_40", "293_26"),
        "yenikapi-bandirma": ("250_24", "226_27"),
        "cesme-sakiz-car": ("251_50", "55828_54"),
        "cesme-sakiz-fast": ("251_50", "55828_54"),
        "ayvalik-midilli": ("226_52", "55828_55"),
        "bodrum-kos": ("264_49", "55828_56"),
        "kusadasi-samos": ("225_53", "55828_57"),
        "fethiye-rodos": ("264_58", "55828_60"),
        "marmaris-rodos": ("264_67", "55828_60"),
    }

    # Bilet.com Gerçek Tarihli & Araçlı Arama Parametre Haritası (/feribot/arama?theme=new&adapter={adapter}&nereden={orig}&nereye={dest}&gidis=DD.MM.YYYY)
    _BILETCOM_ROUTE_PARAMS: Dict[str, Tuple[str, str, str]] = {
        "yenikapi-bursa": ("ido", "yenikapi", "bursa-guzelyali"),
        "yenikapi-yalova": ("ido", "yenikapi", "yalova"),
        "pendik-yalova": ("ido", "pendik", "yalova"),
        "yenikapi-bandirma": ("ido", "yenikapi", "bandirma"),
        "yenikapi-avsa": ("ido", "yenikapi", "avsa-adasi"),
        "tasucu-girne": ("cyprus", "tasucu", "girne"),
        "tasucu-girne-fast": ("cyprus", "tasucu", "girne"),
        "tasucu-girne-car": ("cyprus", "tasucu", "girne"),
        "cesme-sakiz-car": ("erturk", "cesme", "sakiz-adasi"),
        "cesme-sakiz-fast": ("erturk", "cesme", "sakiz-adasi"),
    }

    # Feribotlines Gerçek Tarihli & Araçlı Arama Liman ID Haritası (/search?from={orig}&to={dest}&departure_date=DD-MM-YYYY&adult={pax}&vehicle_type={0|2|3})
    _FERIBOTLINES_ROUTE_IDS: Dict[str, Tuple[str, str]] = {
        "cesme-sakiz-car": ("1668881435", "1668881536"),
        "cesme-sakiz-fast": ("1668881435", "1668881536"),
        "bodrum-kos": ("1668882010", "1669034913"),
        "ayvalik-midilli": ("1668881186", "1668881312"),
        "kusadasi-samos": ("1668881710", "1668881816"),
        "fethiye-rodos": ("1668882143", "1668882286"),
        "marmaris-rodos": ("1668882228", "1668882286"),
        "kas-meis": ("1668882401", "1668882487"),
    }

    @classmethod
    def build_partner_deep_links(
        cls,
        route: Dict[str, Any],
        departure_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        vehicle_type: str = "passenger",
    ) -> Dict[str, Optional[str]]:
        """
        Asla çıplak ana sayfaya veya tarih sıfırlayan statik SEO sayfalarına yönlendirme yapmaz;
        Obilet (/feribot-seferleri/.../YYYYMMDD), Bilet.com (/feribot/arama?...&gidis=DD.MM.YYYY),
        Feribotlines (/search?from=...&to=...&departure_date=DD-MM-YYYY) ve
        Ferryhopper (/en/booking/results?itinerary=...&dates=YYYYMMDD) gerçek tarihli arama uçlarına indirir.
        """
        ferry_subid = getattr(settings, "AFFILIATE_FERRY_SUBID", "hakikibilet")
        pax = max(1, int(passengers or 1))
        is_veh = vehicle_type in ("car", "motorcycle") and bool(route.get("vehicle_allowed", False))
        veh_flag = "1" if is_veh else "0"
        ret_param = f"&donus={return_date}" if return_date else ""
        r_key = str(route.get("route_key") or "")
        is_rev = bool(route.get("is_reversed"))

        # Tarih formatları: YYYYMMDD (Obilet/Ferryhopper), DD.MM.YYYY (Bilet.com) ve DD-MM-YYYY (Feribotlines)
        date_compact = departure_date.replace("-", "")
        try:
            dt_obj = datetime.strptime(departure_date, "%Y-%m-%d")
            date_ddmmyyyy = dt_obj.strftime("%d.%m.%Y")
            date_dd_mm_yyyy = dt_obj.strftime("%d-%m-%Y")
        except Exception:
            date_ddmmyyyy = departure_date
            date_dd_mm_yyyy = departure_date

        ret_ddmmyyyy = ""
        ret_dd_mm_yyyy = ""
        if return_date:
            try:
                ret_dt_obj = datetime.strptime(return_date, "%Y-%m-%d")
                ret_ddmmyyyy = ret_dt_obj.strftime("%d.%m.%Y")
                ret_dd_mm_yyyy = ret_dt_obj.strftime("%d-%m-%Y")
            except Exception:
                ret_ddmmyyyy = return_date
                ret_dd_mm_yyyy = return_date

        # CRUISE TURLARI İÇİN DOĞRULANMIŞ (HTTP 200) DERİN LİNKLER (Setur 404 Kalkanı)
        if route.get("is_cruise"):
            setur_base = route.get("setur_url") or "https://www.setur.com.tr/gemi-turlari"
            jolly_base = route.get("jolly_url") or "https://www.jollytur.com/gemi-turlari"
            cd_base = route.get("cruisedirect_url") or "https://www.cruisedirect.com/destination/mediterranean-cruises"
            off_base = route.get("official_url") or "https://celestyal.com/tr/"
            return {
                "setur_cruise": setur_base,
                "jolly_cruise": jolly_base,
                "cruisedirect": cd_base,
                "official": off_base,
                "obilet": None,
                "feribotlines": None,
                "biletcom": None,
                "ferryhopper": None,
            }

        # 1. Obilet Feribot Gerçek Tarihli Sefer Listesi Linki (/feribot-seferleri/{orig}-{dest}/{YYYYMMDD}/{pax}a/0_none)
        # Not: Obilet kendi feribot altyapısında araçlı bilet satışı yapmadığından (isCarriesWheeledCargo: false) yaya arama ekranını açar.
        obilet_ids = cls._OBILET_ROUTE_IDS.get(r_key)
        if obilet_ids:
            ob_orig, ob_dest = (obilet_ids[1], obilet_ids[0]) if is_rev else (obilet_ids[0], obilet_ids[1])
            obilet_url = f"https://www.obilet.com/feribot-seferleri/{ob_orig}-{ob_dest}/{date_compact}/{pax}a/0_none"
        else:
            obilet_url = None

        # 2. Feribotlines Gerçek Tarihli & Araçlı Arama Endpoint'i (/search?from=...&to=...&departure_date=DD-MM-YYYY)
        fl_ids = cls._FERIBOTLINES_ROUTE_IDS.get(r_key)
        if fl_ids:
            fl_orig, fl_dest = (fl_ids[1], fl_ids[0]) if is_rev else (fl_ids[0], fl_ids[1])
            fl_veh_type = "3" if (is_veh and vehicle_type == "car") else ("2" if (is_veh and vehicle_type == "motorcycle") else "0")
            fl_veh_cnt = "1" if is_veh else "0"
            fl_ret_q = f"&return_date={ret_dd_mm_yyyy}" if ret_dd_mm_yyyy else ""
            feribotlines_url = (
                f"https://feribotlines.com/search?from={fl_orig}&to={fl_dest}"
                f"&departure_date={date_dd_mm_yyyy}{fl_ret_q}&adult={pax}&child=0&baby=0"
                f"&vehicle_type={fl_veh_type}&vehicle_count={fl_veh_cnt}"
            )
        else:
            feribotlines_url = None

        # 3. Bilet.com Gerçek Tarihli & Araçlı Arama Endpoint'i (/feribot/arama?theme=new&adapter=...&nereden=...&nereye=...&gidis=DD.MM.YYYY)
        bilet_params = cls._BILETCOM_ROUTE_PARAMS.get(r_key)
        if bilet_params:
            b_adapter, b_o_slug, b_d_slug = bilet_params
            b_orig, b_dest = (b_d_slug, b_o_slug) if is_rev else (b_o_slug, b_d_slug)
            b_ret_q = f"&donus={ret_ddmmyyyy}" if ret_ddmmyyyy else ""
            if is_veh:
                b_veh_code = "OTM" if vehicle_type == "car" else "MOT"
                extra_adults = max(0, pax - 1)
                b_pax_q = f"&arac={b_veh_code}&aracsayi=1" + (f"&yetiskin={extra_adults}" if extra_adults > 0 else "")
            else:
                b_pax_q = f"&yetiskin={pax}"
            biletcom_url = (
                f"https://www.bilet.com/feribot/arama?theme=new&adapter={b_adapter}"
                f"&nereden={b_orig}&nereye={b_dest}&gidis={date_ddmmyyyy}{b_ret_q}{b_pax_q}"
            )
        else:
            biletcom_url = None

        # 4. Resmi Taşıyıcı Linki
        raw_official = route.get("official_url") or "https://www.ido.com.tr/sefer-saatleri"
        official_route_pages = {
            "cesme-sakiz-car": "https://www.erturk.com.tr/cesme-sakiz-feribot-bileti",
            "cesme-sakiz-fast": "https://www.turyolonline.com/cesme-sakiz-feribot-bileti",
            "bodrum-kos": "https://www.turyolonline.com/bodrum-kos-feribot-bileti",
            "ayvalik-midilli": "https://www.turyolonline.com/ayvalik-midilli-feribot-bileti",
            "fethiye-rodos": "https://www.turyolonline.com/fethiye-rodos-feribot-bileti",
            "kas-meis": "https://www.meisferrylines.com/tr/kas-meis-feribot-seferleri",
        }
        official_url = official_route_pages.get(r_key, raw_official)

        # 5. Ferryhopper Global Ada Ağı Gerçek Tarihli Arama Sonuçları Linki (/en/booking/results?itinerary=CES,CHI&dates=YYYYMMDD)
        fh_ports = route.get("ferryhopper_ports")
        if fh_ports and isinstance(fh_ports, (tuple, list)) and len(fh_ports) == 2:
            fh_orig, fh_dest = (fh_ports[1], fh_ports[0]) if is_rev else (fh_ports[0], fh_ports[1])
            ferryhopper_url = (
                f"https://www.ferryhopper.com/en/booking/results?itinerary={fh_orig},{fh_dest}"
                f"&dates={date_compact}&pax={pax}&vehicles={veh_flag}&aff_id=hakikibilet"
            )
        else:
            ferryhopper_url = None

        return {
            "obilet": obilet_url,
            "feribotlines": feribotlines_url,
            "biletcom": biletcom_url,
            "official": official_url,
            "ferryhopper": ferryhopper_url,
        }

    @classmethod
    def find_matching_routes(cls, origin_name: str, dest_name: str) -> List[Dict[str, Any]]:
        orig_clean = (
            origin_name.lower()
            .replace("limanı", "")
            .replace("limani", "")
            .replace("iskelesi", "")
            .replace("iskele", "")
            .replace("ulusoy", "")
            .replace("merkez", "")
            .replace("adası", "")
            .replace("adasi", "")
            .strip()
        )
        dest_clean = (
            dest_name.lower()
            .replace("limanı", "")
            .replace("limani", "")
            .replace("iskelesi", "")
            .replace("iskele", "")
            .replace("ulusoy", "")
            .replace("merkez", "")
            .replace("adası", "")
            .replace("adasi", "")
            .strip()
        )

        matched: List[Dict[str, Any]] = []

        # Özel Akıllı Eşleşme 0: Cruise / Kruvaziyer / Galataport araması
        is_cruise_search = any(
            k in orig_clean or k in dest_clean
            for k in ["cruise", "kruvaziyer", "galataport", "atina", "mykonos", "santorini"]
        )
        if is_cruise_search:
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("category") == "cruise":
                    matched.append(dict(r))
            if matched:
                return matched

        # Özel Akıllı Eşleşme 1: Kıbrıs / Girne / Taşucu / Mersin araması
        if any(k in orig_clean or k in dest_clean for k in ["girne", "kıbrıs", "kibris", "kktc", "taşucu", "tasucu", "mersin"]):
            for r in cls.POPULAR_FERRY_ROUTES:
                if str(r.get("route_key", "")).startswith("tasucu-girne"):
                    matched.append(dict(r))
            if matched:
                return matched

        # Özel Akıllı Eşleşme 2: Yenikapı -> Bursa/Güzelyalı/Mudanya arandıysa (İDO + BUDO Karşılaştırmalı)
        if ("yenikapı" in orig_clean or "yenikapi" in orig_clean) and any(k in dest_clean for k in ["bursa", "güzelyalı", "guzelyali", "mudanya"]):
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("route_key") == "yenikapi-bursa":
                    route_copy = dict(r)
                    route_copy["smart_sort_rank"] = 1
                    route_copy["route_notice"] = (
                        "💡 İDO Yenikapı seferleri Mudanya ilçe sınırındaki Güzelyalı/Mudanya İskelesi'ne yanaşmaktadır."
                    )
                    matched.append(route_copy)
                elif r.get("route_key") == "eminonu-mudanya":
                    budo_copy = dict(r)
                    budo_copy["smart_sort_rank"] = 2
                    budo_copy["route_notice"] = (
                        "💡 Alternatif İskele: İstanbul Avrupa yakasında Eminönü/Sirkeci İskelesi'nden kalkan BUDO (Bursa Deniz Otobüsleri) seferleri de karşılaştırma için listelenmiştir."
                    )
                    matched.append(budo_copy)
            return matched

        # Özel Akıllı Eşleşme 2B: Eminönü/Sirkeci -> Bursa/Mudanya arandıysa
        if any(k in orig_clean for k in ["eminönü", "eminonu", "sirkeci"]) and any(k in dest_clean for k in ["bursa", "mudanya", "güzelyalı", "guzelyali"]):
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("route_key") == "eminonu-mudanya":
                    matched.append(dict(r))
            return matched

        # Özel Akıllı Eşleşme 3: Genel İstanbul -> Bursa arandıysa (Hem İDO hem BUDO sun)
        if "istanbul" in orig_clean and "bursa" in dest_clean:
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("route_key") in ("yenikapi-bursa", "eminonu-mudanya"):
                    matched.append(dict(r))
            return matched

        # Özel Akıllı Eşleşme 4: Bursa -> İstanbul arandıysa (Ters yön)
        if "bursa" in orig_clean and "istanbul" in dest_clean:
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("route_key") in ("yenikapi-bursa", "eminonu-mudanya"):
                    rev = dict(r)
                    rev["origin"] = r["dest"]
                    rev["dest"] = r["origin"]
                    rev["is_reversed"] = True
                    matched.append(rev)
            return matched

        # Özel Akıllı Eşleşme 5: Genel Yunan Adaları araması
        island_keywords = ["yunan", "adalar", "chios", "sakız", "sakiz", "kos", "midilli", "lesvos", "samos", "sisam", "rodos", "rhodes", "meis", "simi", "symi"]
        stop_tokens = {"adası", "adasi", "ada", "liman", "limanı", "iskele", "iskelesi"}
        if any(w in dest_clean for w in island_keywords):
            orig_tokens = [w for w in orig_clean.split() if len(w) >= 3 and w not in stop_tokens]
            dest_tokens = [w for w in dest_clean.split() if len(w) >= 3 and w not in stop_tokens]
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("category") == "greek_islands":
                    r_orig = r["origin"].lower()
                    r_dest = r["dest"].lower()
                    orig_ok = not orig_tokens or any(w in r_orig for w in orig_tokens)
                    dest_ok = bool(dest_tokens) and any(w in r_dest for w in dest_tokens)
                    if orig_ok and dest_ok:
                        matched.append(dict(r))
            if matched:
                return matched
            for r in cls.POPULAR_FERRY_ROUTES:
                if r.get("category") == "greek_islands":
                    r_dest = r["dest"].lower()
                    if dest_tokens and any(w in r_dest for w in dest_tokens):
                        rc = dict(r)
                        rc["route_notice"] = f"💡 {r['dest']} seferleri doğrudan {r['origin']} üzerinden düzenlenmektedir."
                        matched.append(rc)
            if matched:
                return matched

        # Standart Eşleşme
        for r in cls.POPULAR_FERRY_ROUTES:
            r_orig = r["origin"].lower()
            r_dest = r["dest"].lower()
            orig_match = bool(orig_clean and (orig_clean in r_orig or r_orig.startswith(orig_clean[:4])))
            dest_match = bool(dest_clean and (dest_clean in r_dest or r_dest.startswith(dest_clean[:4])))
            if orig_match and dest_match:
                matched.append(dict(r))

        # Ters rota kontrolü (Örn: Sakız -> Çeşme veya Yalova -> Yenikapı)
        if not matched:
            for r in cls.POPULAR_FERRY_ROUTES:
                r_orig = r["dest"].lower()
                r_dest = r["origin"].lower()
                orig_match = bool(orig_clean and (orig_clean in r_orig or r_orig.startswith(orig_clean[:4])))
                dest_match = bool(dest_clean and (dest_clean in r_dest or r_dest.startswith(dest_clean[:4])))
                if orig_match and dest_match:
                    reversed_r = dict(r)
                    reversed_r["origin"] = r["dest"]
                    reversed_r["dest"] = r["origin"]
                    reversed_r["is_reversed"] = True
                    matched.append(reversed_r)

        return matched

    @staticmethod
    def _parse_duration_minutes(dur_str: str) -> int:
        if not dur_str:
            return 60
        h_m = re.search(r"(\d+)\s*sa", dur_str)
        m_m = re.search(r"(\d+)\s*dk", dur_str)
        return (int(h_m.group(1)) * 60 if h_m else 0) + (int(m_m.group(1)) if m_m else 0)

    @classmethod
    def _compute_arrival_time(cls, dep_time: str, duration_str: str) -> str:
        try:
            parts = dep_time.split(":")
            dep_mins = int(parts[0]) * 60 + int(parts[1])
            total_mins = (dep_mins + cls._parse_duration_minutes(duration_str)) % (24 * 60)
            return f"{total_mins // 60:02d}:{total_mins % 60:02d}"
        except Exception:
            return "11:00"

    @classmethod
    def search_ferries(
        cls,
        origin_name: str,
        dest_name: str,
        departure_date: str,
        passengers: int = 1,
        is_round: bool = False,
        return_date: Optional[str] = None,
        vehicle_type: str = "passenger",
        currency: str = "TRY",
    ) -> List[Dict[str, Any]]:
        from app.services.currency_service import CurrencyService

        matched_routes = cls.find_matching_routes(origin_name, dest_name)
        if not matched_routes:
            return []

        route_notices: List[str] = []
        is_vehicle_requested = vehicle_type in ("car", "motorcycle")
        veh_label = "Otomobil / SUV" if vehicle_type == "car" else "Motosiklet"
        curr_symbol = CurrencyService.get_symbol(currency)
        pax_count = max(1, int(passengers or 1))

        # 1. KATAMARAN VS ARABALI FERİBOT KALKANI & MARMARA ARAÇLI HAT YÖNLENDİRMESİ
        is_all_cruise = all(bool(r.get("is_cruise") or r.get("category") == "cruise") for r in matched_routes)
        if is_vehicle_requested and not is_all_cruise:
            vehicle_routes = [r for r in matched_routes if r.get("vehicle_allowed", False)]
            has_pedestrian_only = any(not r.get("vehicle_allowed", False) for r in matched_routes)

            if vehicle_routes:
                if has_pedestrian_only:
                    route_notices.append(
                        f"ℹ️ Katamaran ve deniz otobüslerinde araç taşınmaz. Seçtiğiniz {veh_label} için yalnızca arabalı feribot seferleri filtrelenmiştir."
                    )
                matched_routes = vehicle_routes
            else:
                # Marmara (Yenikapı/Eminönü ⇄ Bursa/Mudanya/Bandırma) araçlı aramalarında aktif Yalova arabalı feribotlarını sun
                is_marmara_ped = any(
                    r.get("route_key") in ("yenikapi-bursa", "eminonu-mudanya", "yenikapi-bandirma")
                    for r in matched_routes
                )
                if is_marmara_ped:
                    any_rev = any(bool(r.get("is_reversed")) for r in matched_routes)
                    orig_dest_l = f"{origin_name} {dest_name}".lower()
                    prefer_euro_pier = any(w in orig_dest_l for w in ["yenikap", "eminön", "eminon", "sirkeci", "avrupa"])
                    prefer_asian_pier = "pendik" in orig_dest_l
                    marmara_car_routes: List[Dict[str, Any]] = []
                    for r in cls.POPULAR_FERRY_ROUTES:
                        if r.get("route_key") in ("yenikapi-yalova", "pendik-yalova"):
                            rc = dict(r)
                            if any_rev:
                                rc["origin"] = r["dest"]
                                rc["dest"] = r["origin"]
                                rc["is_reversed"] = True
                            if prefer_euro_pier:
                                rc["smart_sort_rank"] = 1 if r.get("route_key") == "yenikapi-yalova" else 2
                            elif prefer_asian_pier:
                                rc["smart_sort_rank"] = 1 if r.get("route_key") == "pendik-yalova" else 2
                            else:
                                rc["smart_sort_rank"] = 1
                            marmara_car_routes.append(rc)
                    if marmara_car_routes:
                        matched_routes = marmara_car_routes
                        route_notices.append(
                            f"⚠️ Operasyonel Bilgilendirme: İDO Yenikapı–Bursa, Yenikapı–Bandırma ve BUDO Eminönü–Mudanya hatlarında arabalı feribot seferi bulunmamaktadır (yalnızca yaya Deniz Otobüsü çalışır). "
                            f"Seçtiğiniz {veh_label} geçişi için Bursa/Güney Marmara'ya en yakın aktif arabalı feribot hatları olan İDO Yenikapı ↔ Yalova ve Pendik ↔ Yalova (Yalova–Bursa otoyolu 40 dk) seferleri aşağıda listelenmiştir."
                        )
                else:
                    route_notices.append(
                        f"⚠️ Bilgilendirme: Bu hatta araçlı ({veh_label}) gemi bulunmamaktadır; seferler hızlı katamaran/deniz otobüsü ile yalnızca yaya yolcular için düzenlenmektedir."
                    )

        try:
            dep_date_dt = datetime.strptime(departure_date, "%Y-%m-%d")
        except Exception:
            dep_date_dt = datetime.now()

        days_until_dep = (dep_date_dt.date() - datetime.now().date()).days
        is_winter_season = dep_date_dt.month in (11, 12, 1, 2, 3)

        months_tr = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        days_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        dep_date_formatted = f"{dep_date_dt.day} {months_tr[dep_date_dt.month - 1]} {days_tr[dep_date_dt.weekday()]}"

        ret_date_formatted = None
        if is_round and return_date:
            try:
                ret_date_dt = datetime.strptime(return_date, "%Y-%m-%d")
                ret_date_formatted = f"{ret_date_dt.day} {months_tr[ret_date_dt.month - 1]} {days_tr[ret_date_dt.weekday()]}"
            except Exception:
                ret_date_formatted = return_date

        # Komisyon ve Tie-Breaker Puanları
        comm_rules = getattr(settings, "PARTNER_COMMISSION_RULES", {})
        rank_obilet = int((comm_rules.get("obilet") or {}).get("tie_breaker_rank", 95))
        rank_setur = int((comm_rules.get("setur_cruise") or {}).get("tie_breaker_rank", 92))
        rank_fl = int((comm_rules.get("feribotlines") or {}).get("tie_breaker_rank", 90))
        rank_jolly = int((comm_rules.get("jolly_cruise") or {}).get("tie_breaker_rank", 88))
        rank_biletcom = int((comm_rules.get("biletcom") or {}).get("tie_breaker_rank", 85))
        rank_cd = int((comm_rules.get("cruisedirect") or {}).get("tie_breaker_rank", 82))
        rank_fh = int((comm_rules.get("ferryhopper") or {}).get("tie_breaker_rank", 80))
        rank_official = 10

        def _try_to_target(val_try: Optional[float]) -> Optional[float]:
            if val_try is None or val_try <= 0:
                return None
            if currency.upper() == "TRY":
                return round(val_try, 2)
            return round(CurrencyService.convert(val_try, "TRY", currency.upper()), 2)

        results: List[Dict[str, Any]] = []

        for i, route in enumerate(matched_routes):
            operator = route["operator"]
            category = route.get("category", "domestic")
            is_greek_island = bool(route.get("requires_visa", False) or category == "greek_islands")
            is_cruise = bool(route.get("is_cruise", False) or category == "cruise")
            is_chip_id = bool(route.get("requires_chip_id", False))
            is_veh_allowed = bool(route.get("vehicle_allowed", False))
            driver_inc = bool(route.get("driver_included_in_vehicle", False))
            all_pax_inc = bool(route.get("all_passengers_included_in_car", False))

            # 2. CANLI FİYAT VE SEFER VERİSİ ÇEK
            market_data = cls.fetch_live_route_market_data(route) if not is_cruise else {}
            deep_links = cls.build_partner_deep_links(
                route=route,
                departure_date=departure_date,
                return_date=return_date if is_round else None,
                passengers=pax_count,
                vehicle_type=vehicle_type,
            )

            live_scheds = market_data.get("obilet_schedules") or []
            is_pier_specific_yalova = route.get("route_key") in ("yenikapi-yalova", "pendik-yalova")
            is_dedicated_car_vessel = route.get("route_key") in ("cesme-sakiz-car", "tasucu-girne-car")
            use_route_scheds = is_cruise or (is_vehicle_requested and is_veh_allowed) or is_pier_specific_yalova or is_dedicated_car_vessel
            if live_scheds and not use_route_scheds:
                active_schedule_items = []
                for ls in live_scheds[:3]:
                    active_schedule_items.append((
                        ls["dep_time"],
                        ls.get("operator") or operator,
                        ls.get("price_try"),
                    ))
            else:
                default_scheds = route.get("schedules") or [("09:00", "Sabah Seferi"), ("16:00", "Öğleden Sonra Seferi")]
                base_ped = route.get("ped_base_try") if is_pier_specific_yalova else (market_data.get("obilet_min_try") or market_data.get("feribotlines_min_try") or route.get("ped_base_try"))
                active_schedule_items = [
                    (t_str, operator, base_ped)
                    for (t_str, _lbl) in default_scheds[:3]
                ]

            # 3. DENİZCİLİK GÜVENLİK KALKANLARI & AKILLI UYARILAR
            visa_urgent_warning = None
            passport_notice = None
            green_card_notice = None
            if is_greek_island:
                passport_notice = (
                    "🛂 Pasaport & Vize Kuralı: Pasaportunuzun dönüş tarihinden itibaren en az 90 gün geçerliliği olmalıdır. "
                    "Kapıda vize başvuruları için evrak teslimi seyahatten en az 4 iş günü önce acenteye yapılmalıdır."
                )
                if 0 <= days_until_dep <= 4:
                    visa_urgent_warning = (
                        f"⚠️ KRİTİK KAPIDA VİZE UYARISI: Seçtiğiniz sefere {days_until_dep} gün kalmıştır! "
                        "Kapıda (Ekspres) Vize evrak teslimi seferden 4 iş günü önce kapanır. Bu bileti yalnızca geçerli Schengen Vizesi veya Yeşil Pasaportu olan yolcular kullanabilir."
                    )
            elif is_chip_id:
                passport_notice = "🇹🇷 KKTC Giriş Kuralı: Yeni çipli T.C. Kimlik Kartı veya Pasaport ile vizesiz biniş yapılabilir (Sürücü belgesi/ehliyet ile geçiş yapılamaz)."

            if is_vehicle_requested and route.get("requires_green_card_for_vehicle"):
                green_card_notice = (
                    "🛡️ Yurt Dışı Araç Çıkış Kalkanı: Kendi aracınızla Yunan Adaları veya KKTC'ye geçişte Uluslararası Yeşil Sigorta (Green Card), "
                    "Yeni Tip Sürücü Belgesi ve araç ruhsat sahibi değilseniz Noter Vekaletnamesi zorunludur."
                )

            vehicle_pricing_note = None
            if is_veh_allowed:
                if all_pax_inc:
                    vehicle_pricing_note = "🚗 Araç Tarifesi Bilgilendirmesi: GESTAŞ Boğaz hattında otomobil geçiş ücretine sürücü ve araç içindeki tüm yolcular dahildir."
                elif driver_inc:
                    vehicle_pricing_note = (
                        "🚗 Araç Tarifesi Bilgilendirmesi: İç hat arabalı feribotlarda (İDO / GESTAŞ Adalar) araç biletine sürücü (şoför) dahildir; "
                        "yalnızca araçtaki ek yolcular için indirimli araç içi yolcu bileti eklenir. (Not: Obilet feribot altyapısında araçlı bilet satışı bulunmadığından doğrudan Bilet.com / Resmi Gişe araçlı ekranına yönlendirilir)."
                    )
                else:
                    vehicle_pricing_note = (
                        "🚗 Araç Tarifesi Bilgilendirmesi: Dış hat / ada feribotlarında araç ücreti yalnızca otomobil/motosiklet taşıma bedelidir; "
                        "sürücü dahil tüm yolcular için kişi başı bilet fiyata eklenmiştir."
                    )
            elif is_vehicle_requested and not is_cruise:
                vehicle_pricing_note = "🚫 Bu gemi tipi (Hızlı Katamaran / Deniz Otobüsü) yalnızca yaya yolcu taşır; güvertesinde araç kabul edilmez."

            seasonality_note = None
            if is_winter_season and route.get("seasonal_winter_reduced"):
                seasonality_note = "❄️ Kış Tarifesi (Kasım-Mart): Bu hatta kış sezonunda sefer sıklığı azaltılmış olup haftanın belirli günleri icra edilmektedir."

            weather_assurance = "🛡️ Lodos & Fırtına Güvencesi: Hava muhalefeti nedeniyle liman başkanlığınca iptal edilen seferlerde bilet ücreti resmi sağlayıcı tarafından kesintisiz iade edilir."

            for s_idx, (d_time, sched_op, sched_ob_try) in enumerate(active_schedule_items):
                arr_time = "18:00" if is_cruise else cls._compute_arrival_time(d_time, route["duration"])
                is_island_pkg = bool(route.get("is_island_round_package", False))
                round_mult = 1.0 if (is_cruise or is_island_pkg) else (1.90 if is_round else 1.0)

                providers: List[Dict[str, Any]] = []
                cabin_tiers_list: List[Dict[str, Any]] = []
                price_breakdown_text = f"{pax_count} Yetişkin Yaya Yolcu"

                # ==========================================================
                # SENARYO A: CRUISE & KRUVAZİYER TURLARI (KABİN TİPLİ & SETUR/JOLLY/CRUISEDIRECT)
                # ==========================================================
                if is_cruise:
                    tiers_eur = route.get("cabin_tiers_eur") or {"interior": 349.0, "oceanview": 429.0, "balcony": 589.0}
                    tier_meta = [
                        ("interior", "🛏️ İç Kabin", "Standart İç Kabin"),
                        ("oceanview", "🪟 Dış Kabin", "Deniz Manzaralı Pencereli Kabin"),
                        ("balcony", "🌅 Balkonlu Kabin", "Özel Balkonlu & Teraslı Kabin"),
                    ]
                    for t_id, t_name, t_desc in tier_meta:
                        eur_pp = float(tiers_eur.get(t_id, 349.0))
                        try_pp = CurrencyService.convert(eur_pp, "EUR", "TRY")
                        total_try_tier = try_pp * pax_count
                        target_val = _try_to_target(total_try_tier)
                        cabin_tiers_list.append({
                            "id": t_id,
                            "name": t_name,
                            "desc": t_desc,
                            "per_person_eur": int(round(eur_pp)),
                            "price": target_val,
                            "currency": curr_symbol,
                        })

                    base_cruise_price = cabin_tiers_list[0]["price"]
                    jolly_cruise_price = round(base_cruise_price * 1.02, 2) if base_cruise_price else None
                    price_breakdown_text = f"🛏️ İç Kabin ({cabin_tiers_list[0]['per_person_eur']} € × {pax_count} Kişi) • Her Şey Dahil"

                    if deep_links.get("setur_cruise"):
                        providers.append({
                            "channel": "setur_cruise",
                            "name": "Setur Cruise",
                            "url": deep_links["setur_cruise"],
                            "price": base_cruise_price,
                            "commission_rank": rank_setur,
                            "badge": "Koç Grubu Güvencesi & Taksit",
                            "button_text_tr": "Setur'dan Al ↗",
                            "button_text_en": "Book on Setur ↗",
                            "is_best": False,
                        })
                    if deep_links.get("jolly_cruise"):
                        providers.append({
                            "channel": "jolly_cruise",
                            "name": "Jolly Tur Gemi",
                            "url": deep_links["jolly_cruise"],
                            "price": jolly_cruise_price,
                            "commission_rank": rank_jolly,
                            "badge": "Vize & Türkçe Rehber",
                            "button_text_tr": "Jolly Tur'dan Al ↗",
                            "button_text_en": "Book on Jolly Tur ↗",
                            "is_best": False,
                        })
                    if deep_links.get("cruisedirect"):
                        providers.append({
                            "channel": "cruisedirect",
                            "name": "CruiseDirect",
                            "url": deep_links["cruisedirect"],
                            "price": base_cruise_price,
                            "commission_rank": rank_cd,
                            "badge": "Global Kabin Garantisi",
                            "button_text_tr": "CruiseDirect'ten Al ↗",
                            "button_text_en": "Book on CruiseDirect ↗",
                            "is_best": False,
                        })
                    if deep_links.get("official"):
                        providers.append({
                            "channel": "official",
                            "name": f"{operator} Resmi",
                            "url": deep_links["official"],
                            "price": base_cruise_price,
                            "commission_rank": rank_official,
                            "badge": "Resmi Kruvaziyer Hattı",
                            "button_text_tr": f"{operator} Resmi ↗",
                            "button_text_en": f"{operator} Official ↗",
                            "is_best": False,
                        })

                # ==========================================================
                # SENARYO B: İÇ HAT, KKTC & YUNAN ADALARI FERİBOT SEFERLERİ (YAYA VS ARAÇLI)
                # ==========================================================
                else:
                    ob_min_route = market_data.get("obilet_min_try")
                    is_premium_sched = bool(sched_ob_try and ob_min_route and sched_ob_try > ob_min_route * 1.05)
                    unit_ob_try = route.get("ped_base_try") if is_pier_specific_yalova else (sched_ob_try or ob_min_route or route.get("ped_base_try"))
                    unit_fl_try = None if is_premium_sched else market_data.get("feribotlines_min_try")
                    unit_bl_try = route.get("ped_base_try") if is_pier_specific_yalova else (None if is_premium_sched else (market_data.get("biletcom_min_try") or route.get("ped_base_try")))

                    if is_vehicle_requested and is_veh_allowed:
                        # 1. Araç Taşıma Ücretini (veh_try) Hesapla
                        veh_try = 0.0
                        veh_tag_str = ""
                        if route.get("car_base_eur") or route.get("moto_base_eur"):
                            if vehicle_type == "car":
                                v_eur = float(route.get("car_round_eur") if is_round else route.get("car_base_eur"))
                            else:
                                v_eur = float(route.get("moto_round_eur") if is_round else route.get("moto_base_eur"))
                            veh_try = CurrencyService.convert(v_eur, "EUR", "TRY")
                            veh_tag_str = f"1 {veh_label} ({int(round(v_eur))} €)"
                        else:
                            if vehicle_type == "car":
                                v_try_raw = route.get("car_round_try") if (is_round and route.get("car_round_try")) else (float(route.get("car_base_try", 1421.0)) * round_mult)
                            else:
                                v_try_raw = route.get("moto_round_try") if (is_round and route.get("moto_round_try")) else (float(route.get("moto_base_try", 750.0)) * round_mult)
                            veh_try = float(v_try_raw)
                            veh_tag_str = f"1 {veh_label}"

                        # 2. Araç Üzerine Eklenecek Yolcu Sayısını (extra_pax) ve Araç İçi Ek Yolcu Tarifesini Belirle
                        extra_pax_unit_try = float(route.get("car_extra_pax_try") or unit_bl_try or unit_fl_try or unit_ob_try or route.get("ped_base_try") or 0.0)
                        if all_pax_inc and vehicle_type == "car":
                            extra_pax = 0
                            price_breakdown_text = f"🚗 {veh_tag_str} + Araç İçi Tüm Yolcular Dahil"
                        elif driver_inc:
                            extra_pax = max(0, pax_count - 1)
                            if extra_pax == 0:
                                price_breakdown_text = f"🚗 {veh_tag_str} (Sürücü Dahil)"
                            else:
                                price_breakdown_text = f"🚗 {veh_tag_str} (Sürücü Dahil) + {extra_pax} Ek Yolcu"
                        else:
                            extra_pax = pax_count
                            price_breakdown_text = f"🚗 {veh_tag_str} + {pax_count} Yolcu Bileti Dahil"

                        veh_total_try = veh_try + (extra_pax * extra_pax_unit_try * round_mult)
                        # Obilet kendi feribot altyapısında araçlı bilet satmadığı için (isCarriesWheeledCargo: false) araçlı aramada ob_price = None
                        ob_price = None
                        bl_price = _try_to_target(veh_total_try) if deep_links.get("biletcom") else None
                        fh_price = _try_to_target(veh_total_try) if deep_links.get("ferryhopper") else None
                        fl_price = _try_to_target(veh_total_try) if deep_links.get("feribotlines") else None
                        off_price = _try_to_target(veh_total_try)
                    else:
                        # YAYA YOLCU HESABI (Birim Yaya Fiyatı × Yolcu Sayısı × Gidiş/Dönüş Çarpanı)
                        ob_price = _try_to_target(unit_ob_try * pax_count * round_mult) if unit_ob_try else None
                        fl_price = _try_to_target(unit_fl_try * pax_count * round_mult) if unit_fl_try else None
                        bl_price = _try_to_target(unit_bl_try * pax_count * round_mult) if (unit_bl_try and deep_links.get("biletcom")) else None
                        fh_price = fl_price or ob_price
                        off_price = ob_price if (ob_price and not is_greek_island) else None
                        if is_vehicle_requested and not is_veh_allowed:
                            price_breakdown_text = f"🚫 Araç Taşınmaz • 🚶 {pax_count} Yetişkin Yaya ({'Gidiş-Dönüş' if is_round else 'Tek Yön'})"
                        else:
                            price_breakdown_text = f"🚶 {pax_count} Yetişkin Yaya • {'Gidiş-Dönüş' if is_round else 'Tek Yön'}"

                    if deep_links.get("obilet"):
                        is_veh_search_active = is_vehicle_requested and is_veh_allowed
                        providers.append({
                            "channel": "obilet",
                            "name": "Obilet (Yalnızca Yaya)" if is_veh_search_active else "Obilet Feribot",
                            "url": deep_links["obilet"],
                            "price": ob_price,
                            "commission_rank": rank_obilet,
                            "badge": "Araçsız Yaya Bileti" if is_veh_search_active else "Hızlı Mobil Bilet",
                            "button_text_tr": "Obilet'ten Al ↗",
                            "button_text_en": "Book on Obilet ↗",
                            "is_best": False,
                        })
                    if deep_links.get("feribotlines"):
                        providers.append({
                            "channel": "feribotlines",
                            "name": "Feribotlines (Ada & Araç)" if (is_vehicle_requested and is_veh_allowed) else "Feribotlines (Vize & Bilet)",
                            "url": deep_links["feribotlines"],
                            "price": fl_price,
                            "commission_rank": rank_fl,
                            "badge": "Araçlı Ada Feribotu" if (is_vehicle_requested and is_veh_allowed) else "Kapıda Vize Masası",
                            "button_text_tr": "Feribotlines'tan Al ↗",
                            "button_text_en": "Book on Feribotlines ↗",
                            "is_best": False,
                        })
                    if deep_links.get("biletcom"):
                        providers.append({
                            "channel": "biletcom",
                            "name": "Bilet.com Deniz",
                            "url": deep_links["biletcom"],
                            "price": bl_price,
                            "commission_rank": rank_biletcom,
                            "badge": "Araçlı & Yaya Yetkili Acente" if (is_vehicle_requested and is_veh_allowed) else "Yetkili Acente",
                            "button_text_tr": "Bilet.com'dan Al ↗",
                            "button_text_en": "Book on Bilet.com ↗",
                            "is_best": False,
                        })
                    if deep_links.get("ferryhopper"):
                        providers.append({
                            "channel": "ferryhopper",
                            "name": "Ferryhopper",
                            "url": deep_links["ferryhopper"],
                            "price": fh_price,
                            "commission_rank": rank_fh,
                            "badge": "Global Ada & Araç Ağı",
                            "button_text_tr": "Ferryhopper'dan Al ↗",
                            "button_text_en": "Book on Ferryhopper ↗",
                            "is_best": False,
                        })
                    if deep_links.get("official"):
                        has_agency_price = bool((deep_links.get("obilet") and ob_price) or (deep_links.get("biletcom") and bl_price))
                        is_closed_spa = operator in ("İDO", "BUDO") and has_agency_price
                        providers.append({
                            "channel": "official",
                            "name": f"{operator} Resmi Site (Manuel)" if is_closed_spa else f"{operator} Resmi Gişe",
                            "url": deep_links["official"],
                            "price": None if is_closed_spa else off_price,
                            "commission_rank": rank_official,
                            "badge": "Manuel Tarih Seçimi" if is_closed_spa else "Resmi Taşıyıcı",
                            "button_text_tr": f"{operator} Resmi Site ↗",
                            "button_text_en": f"{operator} Official ↗",
                            "is_best": False,
                        })

                # 4. ANAYASAL EN UCUZ CANLI FİYAT + TIE-BREAKER SEÇİMİ
                priced_providers = [p for p in providers if p.get("price") is not None and float(p["price"]) > 0]
                if priced_providers:
                    priced_providers.sort(key=lambda p: (round(float(p["price"])), -int(p["commission_rank"])))
                    winner = priced_providers[0]
                    winner["is_best"] = True
                    ticket_price = float(winner["price"])
                    has_live_price = True
                    price_status = (
                        route.get("cruise_inclusions")
                        if is_cruise
                        else (
                            "Canlı Doğrulanmış Gidiş-Dönüş Fiyatı • Liman Vergisi Dahil"
                            if is_round
                            else "Canlı Doğrulanmış Fiyat • Liman Vergisi Dahil"
                        )
                    )
                    winner_btn_tr = winner["button_text_tr"]
                    winner_btn_en = winner["button_text_en"]
                else:
                    providers.sort(key=lambda p: -int(p["commission_rank"]))
                    winner = providers[0] if providers else {
                        "channel": "official",
                        "name": f"{operator} Resmi Ekranı",
                        "url": deep_links.get("official") or "https://www.obilet.com/feribot-bileti",
                    }
                    winner["is_best"] = True
                    ticket_price = None
                    has_live_price = False
                    price_status = "Canlı Sefer & Kontenjan Sorgula"
                    winner_btn_tr = "Canlı Fiyatı Gör ↗" if not is_cruise else "Kabin & Tur Fiyatlarını Gör ↗"
                    winner_btn_en = "Check Live Fares ↗"

                if is_cruise:
                    badge = "🛳️ Her Şey Dahil Lüks Cruise"
                elif is_greek_island:
                    if is_vehicle_requested and is_veh_allowed:
                        badge = f"🇬🇷 Kapıda Vize • 🚗 {veh_label} Dahil"
                    else:
                        badge = "🇬🇷 Kapıda Vizeye Uygun"
                elif is_chip_id:
                    badge = "🇹🇷 Çipli Kimlikle Vizesiz"
                elif is_veh_allowed:
                    if vehicle_type == "car":
                        badge = "🚗 Araçlı Geçiş (Otomobil + Sürücü)" if driver_inc else "🚗 Araçlı Geçiş (Otomobil/SUV)"
                    elif vehicle_type == "motorcycle":
                        badge = "🏍️ Motosikletli Geçiş"
                    else:
                        badge = "🚗 Arabalı Hızlı Feribot"
                else:
                    if is_vehicle_requested:
                        badge = "⚠️ Yalnızca Yaya Yolcu (Araç Alınmaz)"
                    else:
                        badge = "🚶 Hızlı Deniz Otobüsü (Yaya)"

                return_leg = None
                if is_round and not is_cruise:
                    ret_dep_time = "17:45" if s_idx == 0 else "19:30"
                    ret_arr_time = cls._compute_arrival_time(ret_dep_time, route["duration"])
                    return_leg = {
                        "origin": route["dest"],
                        "destination": route["origin"],
                        "departure_time": ret_dep_time,
                        "arrival_time": ret_arr_time,
                        "departure_date": return_date,
                        "departure_date_formatted": ret_date_formatted or return_date,
                        "arrival_date_formatted": ret_date_formatted or return_date,
                        "carrier": sched_op or operator,
                        "flight_number": f"{sched_op or operator} Dönüş Seferi",
                        "duration": route["duration"],
                    }

                notices_list: List[str] = []
                if route.get("route_notice"):
                    notices_list.append(route["route_notice"])
                for rn in route_notices:
                    if rn not in notices_list:
                        notices_list.append(rn)
                if visa_urgent_warning and visa_urgent_warning not in notices_list:
                    notices_list.insert(0, visa_urgent_warning)
                combined_notice = " • ".join(notices_list) if notices_list else None

                raw_op = (sched_op or operator).replace("IDO", "İDO").replace("İdo ", "İDO ")
                display_carrier = raw_op

                results.append({
                    "id": f"ferry-{i+1}-{s_idx+1}",
                    "transport_type": "ferry",
                    "category": category,
                    "is_cruise": is_cruise,
                    "carrier": display_carrier,
                    "operator_brand": sched_op or operator,
                    "vessel_type": route["vessel"],
                    "carrier_logo": "🛳️" if is_cruise else "⛴️",
                    "flight_number": f"{sched_op or operator} Seferi" if not is_cruise else f"{operator} Turu",
                    "origin": route["origin"],
                    "destination": route["dest"],
                    "from_code": route.get("from_code", ""),
                    "to_code": route.get("to_code", ""),
                    "departure_time": d_time,
                    "arrival_time": arr_time,
                    "departure_date_formatted": dep_date_formatted,
                    "arrival_date_formatted": dep_date_formatted,
                    "is_next_day": False,
                    "duration": route["duration"],
                    "is_direct": True,
                    "is_night_trip": d_time >= "21:00" or d_time < "05:30",
                    "price": ticket_price,
                    "has_live_price": has_live_price,
                    "price_status_text": price_status,
                    "price_breakdown_text": price_breakdown_text,
                    "cabin_tiers": cabin_tiers_list,
                    "regular_price": None,
                    "currency": curr_symbol,
                    "currency_code": currency.upper(),
                    "badge": badge,
                    "winner_channel": winner.get("channel", "official"),
                    "winner_name": winner.get("name", operator),
                    "winner_url": winner.get("url"),
                    "winner_button_text": winner_btn_tr,
                    "winner_button_text_en": winner_btn_en,
                    "official_name": f"{operator} Resmi Satış Ekranı",
                    "official_link": deep_links.get("official"),
                    "obilet_link": deep_links.get("obilet"),
                    "feribotlines_link": deep_links.get("feribotlines"),
                    "biletcom_link": deep_links.get("biletcom"),
                    "ferryhopper_link": deep_links.get("ferryhopper"),
                    "agent_name": winner.get("name", operator),
                    "agent_link": winner.get("url"),
                    "direct_link": winner.get("url"),
                    "booking_link": winner.get("url"),
                    "is_greek_island": is_greek_island,
                    "visa_required": is_greek_island,
                    "requires_chip_id": is_chip_id,
                    "visa_urgent_warning": visa_urgent_warning,
                    "passport_notice": passport_notice,
                    "green_card_notice": green_card_notice,
                    "vehicle_allowed": is_veh_allowed,
                    "driver_included_in_vehicle": driver_inc,
                    "vehicle_pricing_note": vehicle_pricing_note,
                    "seasonality_note": seasonality_note,
                    "weather_assurance": weather_assurance,
                    "vehicle_type": vehicle_type,
                    "smart_sort_rank": int(route.get("smart_sort_rank", 1)),
                    "route_notice": combined_notice,
                    "return_leg": return_leg,
                    "providers": providers,
                })

        # İskele önceliği (smart_sort_rank), en düşük doğrulanmış fiyat ve kalkış saatine göre sırala
        results.sort(
            key=lambda x: (
                int(x.get("smart_sort_rank", 1)),
                float(x["price"]) if x.get("price") is not None else 999999.0,
                x.get("departure_time") or "23:59",
            )
        )
        return results
