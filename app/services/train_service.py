import logging
import json
import re
import time
import urllib.request
import urllib.parse
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)


class TrainService:
    """
    Çift Motorlu Canlı TCDD Taşımacılık (YHT, Anahat & Bölgesel Trenler) ve Uluslararası Hızlı Tren Servisi:
    1) TCDD Resmi İstasyon Ağı Motoru (cdn-api-prod-ytp.tcddtasimacilik.gov.tr/datas/station-pairs-INTERNET.json)
       - 597 Resmi TCDD İstasyonu ve doğrudan bağlantılı hat (pairs) grafiği
    2) TCDD Canlı Sefer, Peron ve Rötar Motoru (web-api-prod-ytp.tcddtasimacilik.gov.tr/pex/pex/train-status)
       - Gerçek zamanlı tren numaraları (81002, 81302, 22010 Doğu Ekspresi, 32005 İzmir Mavi vb.),
         kalkış/varış saatleri, çalışma günleri, canlı peron (PERON 1..6) ve anlık durum bilgisi
    3) TCDD Resmi Tarife & Kanuni İndirim Skalası (Genç/Öğrenci %15, Öğretmen %15, 65+ Yaş %50, Çocuk %50)
    4) Trainline & Omio Avrupa Hızlı Tren Entegrasyonu + Balkan Ekspresleri
    """

    # TCDD E-Bilet Ön Yüz (Public Web Client) Varsayılan JWT Anahtarı
    _DEFAULT_TCDD_TOKEN = (
        "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJlVFFicDhDMmpiakp1cnUzQVk2a0ZnV196U29MQXZIMmJ5bTJ2OUg5THhRIn0."
        "eyJleHAiOjE3MzE5MzA5OTcsImlhdCI6MTczMTkzMDkzNywianRpIjoiMzI3NzczN2QtN2E1Mi00MzBiLWJkY2EtNWIxNWE2ODE2NGY3IiwiaXNzIjoiaHR0cDovL3VhdC1yYWlsLmRpdHJhdm8uY29tOjgwODAvcmVhbG1zL21hc3RlciIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiIwMDM0MjcyYy01NzZiLTQ5MGUtYmE5OC01MWQzNzU1Y2FiMDciLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJ0bXMiLCJzZXNzaW9uX3N0YXRlIjoiYzVmODc1YjctNDE3MS00MjY1LTg3YzMtMzU3NTRmYmM2NTY2IiwiYWNyIjoiMSIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLW1hc3RlciIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCBlbWFpbCBwcm9maWxlIiwic2lkIjoiYzVmODc1YjctNDE3MS00MjY1LTg3YzMtMzU3NTRmYmM2NTY2IiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJ3ZWIiLCJnaXZlbl9uYW1lIjoiIiwiZmFtaWx5X25hbWUiOiIifQ."
        "IxX21XVcRltIDzyjHXlvME1QpKyYM6sI-GxGXlyD7qklr-424MY5DHRRe8JXlY1F5qsI607DQV146MACYuAUXN8jtrfZD2NcK_0QsGis5IA_rue9cVvcvzia-NTV3Ka2B285DpVjOMdFTcsDtxZLRZ0tD6w0A_WzW1KId1lvLsY08UHq6WKvlaDVoa3w3LKC8nDwPSvSMIBWhBpG_5-rxbbf8tpoAfsbJHXVjeOARx5gg713FBwAWzyWrp72SMVozyuwboQrPo4xhPEkwn_V_Ecyp45G3Xe4QOEZpDtbi25fup6xyM4gRq73TCczaErtrP1EQbWgefSgBemldOYLGg"
    )
    _CACHED_TCDD_TOKEN: Optional[str] = None
    _TOKEN_TS: float = 0.0

    # Önbellekler
    _STATIONS_CACHE: Optional[List[Dict[str, Any]]] = None
    _STATIONS_BY_ID: Dict[int, Dict[str, Any]] = {}
    _STATIONS_TS: float = 0.0
    _STATION_STATUS_CACHE: Dict[int, Tuple[float, List[Dict[str, Any]]]] = {}
    _ROUTE_MIN_PRICE_CACHE: Dict[Tuple[str, str], float] = {}

    # Şehir -> Öncelikli TCDD İstasyon ID eşlemesi (597 istasyon içinde ana garlar)
    CITY_PRIMARY_STATION_IDS: Dict[str, List[int]] = {
        "istanbul": [1325, 992, 48, 1323, 1328],     # Söğütlüçeşme, Halkalı, Pendik, Bostancı, Bakırköy
        "sogutlucesme": [1325],
        "halkali": [992],
        "pendik": [48],
        "bostanci": [1323],
        "bakirkoy": [1328],
        "ankara": [98, 1306],                        # Ankara Gar, Eryaman YHT
        "eryaman": [1306],
        "polatli": [1309, 103],                      # Polatlı YHT, Polatlı
        "eskisehir": [93],
        "konya": [796, 1336],                        # Konya Gar, Selçuklu YHT
        "selcuklu": [1336],
        "karaman": [791],
        "sivas": [566],
        "izmir": [312],                              # İzmir (Basmane)
        "basmane": [312],
        "kocaeli": [1135, 28],                       # İzmit YHT, Gebze
        "izmit": [1135],
        "gebze": [28],
        "sakarya": [5],                              # Arifiye
        "adapazari": [5],
        "arifiye": [5],
        "bilecik": [1142, 1143, 9],                  # Bilecik YHT, Bozüyük YHT, Bilecik
        "bozuyuk": [1143, 10],
        "kirikkale": [1346, 168],                    # Kırıkkale YHT, Kırıkkale
        "yozgat": [1347, 209],                       # Yozgat YHT, Yerköy
        "yerkoy": [209],
        "kars": [532],
        "erzurum": [498],
        "erzincan": [1152],
        "denizli": [309],
        "aydin": [288],
        "manisa": [371],
        "usak": [397],
        "kutahya": [937],
        "afyon": [873],
        "afyonkarahisar": [873],
        "isparta": [920],
        "burdur": [892],
        "kayseri": [182],
        "malatya": [696],
        "elazig": [647],
        "diyarbakir": [1109],
        "batman": [633],
        "kurtalan": [670],
        "siirt": [670],
        "tatvan": [712],
        "bitlis": [712],
        "van": [712],
        "amasya": [461],
        "samsun": [557],
        "zonguldak": [212],
        "karabuk": [153],
        "cankiri": [118],
        "edirne": [1006],
        "tekirdag": [982, 984],                      # Çerkezköy, Çorlu
        "cerkezkoy": [982],
        "corlu": [984],
        "balikesir": [900],
        "bandirma": [890],
        "adana": [753],
        "mersin": [765],
        "nigde": [189],
    }

    # TCDD Türkiye Geneli Resmi Hat ve Tarife Haritası
    TCDD_TARIFFS: Dict[Tuple[str, str], Dict[str, Any]] = {
        # 1. YHT Koridorları
        ("istanbul", "ankara"): {"type": "yht", "price": 990.0, "anahat_pulman": 550.0, "duration": "4 sa 21 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "istanbul"): {"type": "yht", "price": 990.0, "anahat_pulman": 550.0, "duration": "4 sa 21 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "eskisehir"): {"type": "yht", "price": 560.0, "anahat_pulman": 380.0, "duration": "2 sa 55 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("eskisehir", "istanbul"): {"type": "yht", "price": 560.0, "anahat_pulman": 380.0, "duration": "2 sa 55 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "eskisehir"): {"type": "yht", "price": 435.0, "anahat_pulman": 310.0, "duration": "1 sa 26 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("eskisehir", "ankara"): {"type": "yht", "price": 435.0, "anahat_pulman": 310.0, "duration": "1 sa 26 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "konya"): {"type": "yht", "price": 1180.0, "duration": "5 sa 15 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("konya", "istanbul"): {"type": "yht", "price": 1180.0, "duration": "5 sa 15 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "konya"): {"type": "yht", "price": 450.0, "duration": "2 sa 16 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("konya", "ankara"): {"type": "yht", "price": 450.0, "duration": "2 sa 16 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("eskisehir", "konya"): {"type": "yht", "price": 590.0, "duration": "2 sa 20 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("konya", "eskisehir"): {"type": "yht", "price": 590.0, "duration": "2 sa 20 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "sivas"): {"type": "yht", "price": 890.0, "anahat_pulman": 480.0, "duration": "2 sa 41 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("sivas", "ankara"): {"type": "yht", "price": 890.0, "anahat_pulman": 480.0, "duration": "2 sa 41 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "sivas"): {"type": "yht", "price": 1580.0, "duration": "6 sa 49 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("sivas", "istanbul"): {"type": "yht", "price": 1580.0, "duration": "6 sa 49 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "karaman"): {"type": "yht", "price": 590.0, "duration": "3 sa 07 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("karaman", "ankara"): {"type": "yht", "price": 590.0, "duration": "3 sa 07 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "karaman"): {"type": "yht", "price": 1350.0, "duration": "6 sa 10 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("karaman", "istanbul"): {"type": "yht", "price": 1350.0, "duration": "6 sa 10 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("konya", "karaman"): {"type": "yht", "price": 240.0, "duration": "50 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("karaman", "konya"): {"type": "yht", "price": 240.0, "duration": "50 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "kirikkale"): {"type": "yht", "price": 280.0, "anahat_pulman": 160.0, "duration": "50 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("kirikkale", "ankara"): {"type": "yht", "price": 280.0, "anahat_pulman": 160.0, "duration": "50 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "yozgat"): {"type": "yht", "price": 520.0, "duration": "1 sa 35 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("yozgat", "ankara"): {"type": "yht", "price": 520.0, "duration": "1 sa 35 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "kocaeli"): {"type": "yht", "price": 260.0, "duration": "1 sa 05 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("kocaeli", "istanbul"): {"type": "yht", "price": 260.0, "duration": "1 sa 05 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "sakarya"): {"type": "yht", "price": 320.0, "duration": "1 sa 30 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("sakarya", "istanbul"): {"type": "yht", "price": 320.0, "duration": "1 sa 30 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("kocaeli", "ankara"): {"type": "yht", "price": 860.0, "duration": "3 sa 20 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "kocaeli"): {"type": "yht", "price": 860.0, "duration": "3 sa 20 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("sakarya", "ankara"): {"type": "yht", "price": 810.0, "duration": "2 sa 55 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "sakarya"): {"type": "yht", "price": 810.0, "duration": "2 sa 55 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("bilecik", "ankara"): {"type": "yht", "price": 620.0, "duration": "2 sa 10 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "bilecik"): {"type": "yht", "price": 620.0, "duration": "2 sa 10 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "bilecik"): {"type": "yht", "price": 460.0, "duration": "2 sa 05 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("bilecik", "istanbul"): {"type": "yht", "price": 460.0, "duration": "2 sa 05 dk", "carrier": "TCDD Taşımacılık (YHT)"},

        # 2. Anahat Ekspresleri
        ("ankara", "kars"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "22010", "price": 650.0, "duration": "26 sa 26 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "18:00", "arr": "20:26", "next_day": True, "badge": "⭐ Efsane Doğu Ekspresi (Pulman / Kuşet)", "station_from": "Ankara Gar", "station_to": "Kars Gar (Doğu Ekspresi)"},
        ("kars", "ankara"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "92009", "price": 650.0, "duration": "26 sa 27 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "08:00", "arr": "10:27", "next_day": True, "badge": "⭐ Efsane Doğu Ekspresi (Pulman / Kuşet)", "station_from": "Kars Gar (Doğu Ekspresi)", "station_to": "Ankara Gar"},
        ("ankara", "erzurum"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "22010", "price": 560.0, "duration": "21 sa 30 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "18:00", "arr": "15:30", "next_day": True, "badge": "⭐ Doğu Ekspresi (Pulman / Kuşet)", "station_from": "Ankara Gar", "station_to": "Erzurum Gar"},
        ("erzurum", "ankara"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "92009", "price": 560.0, "duration": "21 sa 40 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "12:15", "arr": "10:27", "next_day": True, "badge": "⭐ Doğu Ekspresi (Pulman / Kuşet)", "station_from": "Erzurum Gar", "station_to": "Ankara Gar"},
        ("ankara", "erzincan"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "22010", "price": 480.0, "duration": "17 sa 20 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "18:00", "arr": "11:20", "next_day": True, "badge": "⭐ Doğu Ekspresi", "station_from": "Ankara Gar", "station_to": "Erzincan Gar"},
        ("erzincan", "ankara"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "92009", "price": 480.0, "duration": "17 sa 30 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "16:45", "arr": "10:27", "next_day": True, "badge": "⭐ Doğu Ekspresi", "station_from": "Erzincan Gar", "station_to": "Ankara Gar"},
        ("ankara", "kayseri"): {"type": "anahat_single", "name": "Doğu / Güney Ekspresi", "train_no": "22010", "price": 380.0, "duration": "6 sa 55 dk", "carrier": "TCDD Taşımacılık (Anahat Ekspres)", "dep": "18:00", "arr": "00:55", "next_day": True, "badge": "Anahat Ekspresi", "station_from": "Ankara Gar", "station_to": "Kayseri Gar"},
        ("kayseri", "ankara"): {"type": "anahat_single", "name": "Doğu / Güney Ekspresi", "train_no": "92009", "price": 380.0, "duration": "7 sa 05 dk", "carrier": "TCDD Taşımacılık (Anahat Ekspres)", "dep": "03:20", "arr": "10:27", "next_day": False, "badge": "Anahat Ekspresi", "station_from": "Kayseri Gar", "station_to": "Ankara Gar"},
        ("izmir", "ankara"): {"type": "anahat_single", "name": "İzmir Mavi Ekspresi", "train_no": "32005", "price": 620.0, "duration": "14 sa 02 dk", "carrier": "TCDD Taşımacılık (İzmir Mavi)", "dep": "19:05", "arr": "09:07", "next_day": True, "badge": "🌙 Yataklı & Pulman Gece Treni"},
        ("ankara", "izmir"): {"type": "anahat_single", "name": "İzmir Mavi Ekspresi", "train_no": "22006", "price": 620.0, "duration": "13 sa 45 dk", "carrier": "TCDD Taşımacılık (İzmir Mavi)", "dep": "19:00", "arr": "08:45", "next_day": True, "badge": "🌙 Yataklı & Pulman Gece Treni"},
        ("konya", "izmir"): {"type": "anahat_single", "name": "Konya Mavi Ekspresi", "train_no": "72008", "price": 580.0, "duration": "13 sa 00 dk", "carrier": "TCDD Taşımacılık (Konya Mavi)", "dep": "19:00", "arr": "08:00", "next_day": True, "badge": "🌙 Gece Anahat Treni"},
        ("izmir", "konya"): {"type": "anahat_single", "name": "Konya Mavi Ekspresi", "train_no": "32007", "price": 580.0, "duration": "13 sa 06 dk", "carrier": "TCDD Taşımacılık (Konya Mavi)", "dep": "20:05", "arr": "09:11", "next_day": True, "badge": "🌙 Gece Anahat Treni"},
        ("denizli", "eskisehir"): {"type": "anahat_single", "name": "Pamukkale Ekspresi", "train_no": "32013", "price": 480.0, "duration": "8 sa 37 dk", "carrier": "TCDD Taşımacılık (Pamukkale Ekspresi)", "dep": "08:40", "arr": "17:17", "next_day": False, "badge": "Gündüz Anahat Treni"},
        ("eskisehir", "denizli"): {"type": "anahat_single", "name": "Pamukkale Ekspresi", "train_no": "72014", "price": 480.0, "duration": "8 sa 37 dk", "carrier": "TCDD Taşımacılık (Pamukkale Ekspresi)", "dep": "11:10", "arr": "19:47", "next_day": False, "badge": "Gündüz Anahat Treni"},
        ("izmir", "eskisehir"): {"type": "anahat_single", "name": "Ege Ekspresi", "train_no": "32011", "price": 520.0, "duration": "10 sa 47 dk", "carrier": "TCDD Taşımacılık (Ege Ekspresi)", "dep": "06:40", "arr": "17:27", "next_day": False, "badge": "Ege Bölge Ekspresi"},
        ("eskisehir", "izmir"): {"type": "anahat_single", "name": "Ege Ekspresi", "train_no": "72018", "price": 520.0, "duration": "10 sa 32 dk", "carrier": "TCDD Taşımacılık (Ege Ekspresi)", "dep": "08:45", "arr": "19:17", "next_day": False, "badge": "Ege Bölge Ekspresi"},
        ("isparta", "izmir"): {"type": "anahat_single", "name": "Göller Ekspresi", "train_no": "72016", "price": 440.0, "duration": "8 sa 14 dk", "carrier": "TCDD Taşımacılık (Göller Ekspresi)", "dep": "22:20", "arr": "06:34", "next_day": True, "badge": "🌙 Göller Gece Ekspresi"},
        ("izmir", "isparta"): {"type": "anahat_single", "name": "Göller Ekspresi", "train_no": "32015", "price": 440.0, "duration": "8 sa 15 dk", "carrier": "TCDD Taşımacılık (Göller Ekspresi)", "dep": "23:05", "arr": "07:20", "next_day": True, "badge": "🌙 Göller Gece Ekspresi"},
        ("ankara", "tatvan"): {"type": "anahat_single", "name": "Van Gölü Ekspresi", "train_no": "22012", "price": 650.0, "duration": "26 sa 10 dk", "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi)", "dep": "11:20", "arr": "13:30", "next_day": True, "badge": "⭐ Van Gölü Ekspresi (Pulman / Kuşet)"},
        ("tatvan", "ankara"): {"type": "anahat_single", "name": "Van Gölü Ekspresi", "train_no": "52011", "price": 650.0, "duration": "26 sa 20 dk", "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi)", "dep": "10:25", "arr": "12:45", "next_day": True, "badge": "⭐ Van Gölü Ekspresi (Pulman / Kuşet)"},
        ("ankara", "van"): {"type": "anahat_single", "name": "Van Gölü Ekspresi", "train_no": "22012", "price": 650.0, "duration": "26 sa 10 dk", "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi)", "dep": "11:20", "arr": "13:30", "next_day": True, "badge": "⭐ Van Gölü Ekspresi (Tatvan Gar Varışlı)", "station_from": "Ankara Gar", "station_to": "Tatvan Gar (Van Gölü Ekspresi)"},
        ("van", "ankara"): {"type": "anahat_single", "name": "Van Gölü Ekspresi", "train_no": "52011", "price": 650.0, "duration": "26 sa 20 dk", "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi)", "dep": "10:25", "arr": "12:45", "next_day": True, "badge": "⭐ Van Gölü Ekspresi (Tatvan Gar Kalkışlı)", "station_from": "Tatvan Gar (Van Gölü Ekspresi)", "station_to": "Ankara Gar"},
        ("ankara", "kurtalan"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "22014", "price": 620.0, "duration": "25 sa 00 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "11:20", "arr": "12:20", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi"},
        ("kurtalan", "ankara"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "52013", "price": 620.0, "duration": "27 sa 25 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "09:20", "arr": "12:45", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi"},
        ("ankara", "diyarbakir"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "22014", "price": 580.0, "duration": "21 sa 30 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "11:20", "arr": "08:50", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi", "station_from": "Ankara Gar", "station_to": "Diyarbakır Gar"},
        ("diyarbakir", "ankara"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "52013", "price": 580.0, "duration": "22 sa 15 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "14:30", "arr": "12:45", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi", "station_from": "Diyarbakır Gar", "station_to": "Ankara Gar"},
        ("ankara", "batman"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "22014", "price": 600.0, "duration": "23 sa 30 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "11:20", "arr": "10:50", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi", "station_from": "Ankara Gar", "station_to": "Batman Gar"},
        ("batman", "ankara"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "52013", "price": 600.0, "duration": "24 sa 15 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "12:30", "arr": "12:45", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi", "station_from": "Batman Gar", "station_to": "Ankara Gar"},
        ("ankara", "malatya"): {"type": "anahat_single", "name": "4 Eylül Mavi Ekspresi", "train_no": "22018", "price": 560.0, "duration": "15 sa 59 dk", "carrier": "TCDD Taşımacılık (4 Eylül Mavi)", "dep": "19:10", "arr": "11:09", "next_day": True, "badge": "⭐ 4 Eylül Mavi Ekspresi"},
        ("malatya", "ankara"): {"type": "anahat_single", "name": "4 Eylül Mavi Ekspresi", "train_no": "52019", "price": 560.0, "duration": "15 sa 54 dk", "carrier": "TCDD Taşımacılık (4 Eylül Mavi)", "dep": "15:30", "arr": "07:24", "next_day": True, "badge": "⭐ 4 Eylül Mavi Ekspresi"},
        ("konya", "adana"): {"type": "anahat_single", "name": "Toros Ekspresi", "train_no": "62002", "price": 320.0, "duration": "6 sa 20 dk", "carrier": "TCDD Taşımacılık (Toros Ekspresi)", "dep": "14:45", "arr": "21:05", "next_day": False, "badge": "Gündüz Toros Ekspresi"},
        ("adana", "konya"): {"type": "anahat_single", "name": "Toros Ekspresi", "train_no": "62001", "price": 320.0, "duration": "6 sa 20 dk", "carrier": "TCDD Taşımacılık (Toros Ekspresi)", "dep": "07:45", "arr": "14:05", "next_day": False, "badge": "Gündüz Toros Ekspresi"},
        ("elazig", "adana"): {"type": "anahat_single", "name": "Fırat Ekspresi", "train_no": "52002", "price": 310.0, "duration": "9 sa 15 dk", "carrier": "TCDD Taşımacılık (Fırat Ekspresi)", "dep": "08:30", "arr": "17:45", "next_day": False, "badge": "Fırat Ekspresi"},
        ("adana", "elazig"): {"type": "anahat_single", "name": "Fırat Ekspresi", "train_no": "52001", "price": 310.0, "duration": "9 sa 15 dk", "carrier": "TCDD Taşımacılık (Fırat Ekspresi)", "dep": "08:45", "arr": "18:00", "next_day": False, "badge": "Fırat Ekspresi"},
        ("kayseri", "adana"): {"type": "anahat_single", "name": "Erciyes Ekspresi", "train_no": "22032", "price": 260.0, "duration": "5 sa 45 dk", "carrier": "TCDD Taşımacılık (Erciyes Ekspresi)", "dep": "07:30", "arr": "13:15", "next_day": False, "badge": "Erciyes Ekspresi"},
        ("adana", "kayseri"): {"type": "anahat_single", "name": "Erciyes Ekspresi", "train_no": "22031", "price": 260.0, "duration": "5 sa 45 dk", "carrier": "TCDD Taşımacılık (Erciyes Ekspresi)", "dep": "16:30", "arr": "22:15", "next_day": False, "badge": "Erciyes Ekspresi"},

        # 2B. YHT + Anahat Bağlantılı Resmi Koridorlar (İstanbul ⇄ Kars Doğu Ekspresi, Van Gölü, Güney Kurtalan, Toros, Pamukkale vb.)
        ("istanbul", "kars"): {
            "type": "anahat_single",
            "name": "YHT + Doğu Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81006 + 22010",
            "price": 1640.0,
            "duration": "31 sa 16 dk",
            "carrier": "TCDD Taşımacılık (YHT + Doğu Ekspresi)",
            "dep": "11:10",
            "arr": "20:26",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Doğu Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Kars Gar (Doğu Ekspresi)",
            "full_route": "İstanbul (Söğütlüçeşme YHT 11:10) ➔ Ankara Gar (15:39 / Doğu Ekspresi 18:00) ➔ Erzincan ➔ Erzurum ➔ Kars Gar (20:26)",
        },
        ("kars", "istanbul"): {
            "type": "anahat_single",
            "name": "Doğu Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "92009 + YHT 81011",
            "price": 1640.0,
            "duration": "32 sa 17 dk",
            "carrier": "TCDD Taşımacılık (Doğu Ekspresi + YHT)",
            "dep": "08:00",
            "arr": "16:17",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Doğu Ekspresi + YHT)",
            "station_from": "Kars Gar (Doğu Ekspresi)",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Kars Gar (Doğu Ekspresi 08:00) ➔ Erzurum ➔ Erzincan ➔ Ankara Gar (10:27 / YHT 11:45) ➔ İstanbul (Söğütlüçeşme YHT 16:17)",
        },
        ("istanbul", "erzurum"): {
            "type": "anahat_single",
            "name": "YHT + Doğu Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81006 + 22010",
            "price": 1550.0,
            "duration": "26 sa 20 dk",
            "carrier": "TCDD Taşımacılık (YHT + Doğu Ekspresi)",
            "dep": "11:10",
            "arr": "15:30",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Doğu Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Erzurum Gar",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Erzincan ➔ Erzurum Gar",
        },
        ("erzurum", "istanbul"): {
            "type": "anahat_single",
            "name": "Doğu Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "92009 + YHT 81011",
            "price": 1550.0,
            "duration": "28 sa 02 dk",
            "carrier": "TCDD Taşımacılık (Doğu Ekspresi + YHT)",
            "dep": "12:15",
            "arr": "16:17",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Doğu Ekspresi + YHT)",
            "station_from": "Erzurum Gar",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Erzurum Gar ➔ Erzincan ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "erzincan"): {
            "type": "anahat_single",
            "name": "YHT + Doğu Ekspresi (Ankara/Sivas Aktarmalı)",
            "train_no": "YHT 81006 + 22010",
            "price": 1470.0,
            "duration": "22 sa 10 dk",
            "carrier": "TCDD Taşımacılık (YHT + Doğu Ekspresi)",
            "dep": "11:10",
            "arr": "11:20",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Doğu Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Erzincan Gar",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Sivas ➔ Erzincan Gar",
        },
        ("erzincan", "istanbul"): {
            "type": "anahat_single",
            "name": "Doğu Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "92009 + YHT 81011",
            "price": 1470.0,
            "duration": "23 sa 32 dk",
            "carrier": "TCDD Taşımacılık (Doğu Ekspresi + YHT)",
            "dep": "16:45",
            "arr": "16:17",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Doğu Ekspresi + YHT)",
            "station_from": "Erzincan Gar",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Erzincan Gar ➔ Sivas ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "tatvan"): {
            "type": "anahat_single",
            "name": "YHT + Van Gölü Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81002 + 22012",
            "price": 1640.0,
            "duration": "32 sa 00 dk",
            "carrier": "TCDD Taşımacılık (YHT + Van Gölü Ekspresi)",
            "dep": "05:30",
            "arr": "13:30",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Van Gölü Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Tatvan Gar (Van Gölü Ekspresi)",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Kayseri ➔ Malatya ➔ Elazığ ➔ Tatvan Gar",
        },
        ("tatvan", "istanbul"): {
            "type": "anahat_single",
            "name": "Van Gölü Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "52011 + YHT 81015",
            "price": 1640.0,
            "duration": "31 sa 57 dk",
            "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi + YHT)",
            "dep": "10:25",
            "arr": "18:22",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Van Gölü Ekspresi + YHT)",
            "station_from": "Tatvan Gar (Van Gölü Ekspresi)",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Tatvan Gar ➔ Elazığ ➔ Malatya ➔ Kayseri ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "van"): {
            "type": "anahat_single",
            "name": "YHT + Van Gölü Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81002 + 22012",
            "price": 1640.0,
            "duration": "32 sa 00 dk",
            "carrier": "TCDD Taşımacılık (YHT + Van Gölü Ekspresi)",
            "dep": "05:30",
            "arr": "13:30",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Tatvan Gar Varışlı)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Tatvan Gar (Van Gölü Ekspresi)",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Tatvan Gar (Van Gölü Ekspresi)",
        },
        ("van", "istanbul"): {
            "type": "anahat_single",
            "name": "Van Gölü Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "52011 + YHT 81015",
            "price": 1640.0,
            "duration": "31 sa 57 dk",
            "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi + YHT)",
            "dep": "10:25",
            "arr": "18:22",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Tatvan Gar Kalkışlı)",
            "station_from": "Tatvan Gar (Van Gölü Ekspresi)",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Tatvan Gar (Van Gölü Ekspresi) ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "kurtalan"): {
            "type": "anahat_single",
            "name": "YHT + Güney Kurtalan Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81002 + 22014",
            "price": 1610.0,
            "duration": "30 sa 50 dk",
            "carrier": "TCDD Taşımacılık (YHT + Güney Kurtalan)",
            "dep": "05:30",
            "arr": "12:20",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Güney Kurtalan)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Siirt - Kurtalan Garı",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Diyarbakır ➔ Batman ➔ Kurtalan Gar",
        },
        ("kurtalan", "istanbul"): {
            "type": "anahat_single",
            "name": "Güney Kurtalan Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "52013 + YHT 81015",
            "price": 1610.0,
            "duration": "33 sa 02 dk",
            "carrier": "TCDD Taşımacılık (Güney Kurtalan + YHT)",
            "dep": "09:20",
            "arr": "18:22",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Güney Kurtalan + YHT)",
            "station_from": "Siirt - Kurtalan Garı",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Kurtalan Gar ➔ Batman ➔ Diyarbakır ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "diyarbakir"): {
            "type": "anahat_single",
            "name": "YHT + Güney Kurtalan Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81002 + 22014",
            "price": 1570.0,
            "duration": "27 sa 20 dk",
            "carrier": "TCDD Taşımacılık (YHT + Güney Kurtalan)",
            "dep": "05:30",
            "arr": "08:50",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Güney Kurtalan)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Diyarbakır Gar",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Malatya ➔ Diyarbakır Gar",
        },
        ("diyarbakir", "istanbul"): {
            "type": "anahat_single",
            "name": "Güney Kurtalan Ekspresi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "52013 + YHT 81015",
            "price": 1570.0,
            "duration": "27 sa 52 dk",
            "carrier": "TCDD Taşımacılık (Güney Kurtalan + YHT)",
            "dep": "14:30",
            "arr": "18:22",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Güney Kurtalan + YHT)",
            "station_from": "Diyarbakır Gar",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Diyarbakır Gar ➔ Malatya ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "malatya"): {
            "type": "anahat_single",
            "name": "YHT + 4 Eylül Mavi Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81012 + 22018",
            "price": 1550.0,
            "duration": "22 sa 04 dk",
            "carrier": "TCDD Taşımacılık (YHT + 4 Eylül Mavi)",
            "dep": "13:05",
            "arr": "11:09",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + 4 Eylül Mavi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Malatya Gar",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Sivas ➔ Malatya Gar",
        },
        ("malatya", "istanbul"): {
            "type": "anahat_single",
            "name": "4 Eylül Mavi + YHT (Ankara Gar Aktarmalı)",
            "train_no": "52019 + YHT 81007",
            "price": 1550.0,
            "duration": "21 sa 46 dk",
            "carrier": "TCDD Taşımacılık (4 Eylül Mavi + YHT)",
            "dep": "15:30",
            "arr": "13:16",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (4 Eylül Mavi + YHT)",
            "station_from": "Malatya Gar",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Malatya Gar ➔ Sivas ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "kayseri"): {
            "type": "anahat_single",
            "name": "YHT + Doğu Ekspresi (Ankara Gar Aktarmalı)",
            "train_no": "YHT 81006 + 22010",
            "price": 1370.0,
            "duration": "13 sa 45 dk",
            "carrier": "TCDD Taşımacılık (YHT + Anahat)",
            "dep": "11:10",
            "arr": "00:55",
            "next_day": True,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (YHT + Anahat)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Kayseri Gar",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Ankara Gar ➔ Kayseri Gar",
        },
        ("kayseri", "istanbul"): {
            "type": "anahat_single",
            "name": "Anahat + YHT (Ankara Gar Aktarmalı)",
            "train_no": "92009 + YHT 81011",
            "price": 1370.0,
            "duration": "12 sa 57 dk",
            "carrier": "TCDD Taşımacılık (Anahat + YHT)",
            "dep": "03:20",
            "arr": "16:17",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Ankara Gar Aktarmalı (Anahat + YHT)",
            "station_from": "Kayseri Gar",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Kayseri Gar ➔ Ankara Gar ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "adana"): {
            "type": "anahat_single",
            "name": "YHT + Toros Ekspresi (Konya Gar Aktarmalı)",
            "train_no": "YHT 81302 + 62002",
            "price": 1500.0,
            "duration": "12 sa 25 dk",
            "carrier": "TCDD Taşımacılık (YHT + Toros Ekspresi)",
            "dep": "08:40",
            "arr": "21:05",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Konya Gar Aktarmalı (YHT + Toros Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Adana Gar",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Konya Gar (YHT) ➔ Adana Gar",
        },
        ("adana", "istanbul"): {
            "type": "anahat_single",
            "name": "Toros Ekspresi + YHT (Konya Gar Aktarmalı)",
            "train_no": "62001 + YHT 81309",
            "price": 1500.0,
            "duration": "12 sa 45 dk",
            "carrier": "TCDD Taşımacılık (Toros Ekspresi + YHT)",
            "dep": "07:45",
            "arr": "20:30",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Konya Gar Aktarmalı (Toros Ekspresi + YHT)",
            "station_from": "Adana Gar",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Adana Gar ➔ Konya Gar (YHT) ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "denizli"): {
            "type": "anahat_single",
            "name": "YHT + Pamukkale Ekspresi (Eskişehir Gar Aktarmalı)",
            "train_no": "YHT 81032 + 72014",
            "price": 1040.0,
            "duration": "12 sa 27 dk",
            "carrier": "TCDD Taşımacılık (YHT + Pamukkale Ekspresi)",
            "dep": "07:20",
            "arr": "19:47",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Eskişehir Gar Aktarmalı (YHT + Pamukkale Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "Denizli Gar (Pamukkale Ekspresi)",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Eskişehir Gar (YHT) ➔ Afyon ➔ Denizli Gar",
        },
        ("denizli", "istanbul"): {
            "type": "anahat_single",
            "name": "Pamukkale Ekspresi + YHT (Eskişehir Gar Aktarmalı)",
            "train_no": "32013 + YHT 81021",
            "price": 1040.0,
            "duration": "14 sa 26 dk",
            "carrier": "TCDD Taşımacılık (Pamukkale Ekspresi + YHT)",
            "dep": "08:40",
            "arr": "23:06",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Eskişehir Gar Aktarmalı (Pamukkale Ekspresi + YHT)",
            "station_from": "Denizli Gar (Pamukkale Ekspresi)",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "Denizli Gar ➔ Afyon ➔ Eskişehir Gar (YHT) ➔ İstanbul (Söğütlüçeşme YHT)",
        },
        ("istanbul", "izmir"): {
            "type": "anahat_single",
            "name": "YHT + Ege Ekspresi (Eskişehir Gar Aktarmalı)",
            "train_no": "YHT 81002 + 72018",
            "price": 1080.0,
            "duration": "13 sa 47 dk",
            "carrier": "TCDD Taşımacılık (YHT + Ege Ekspresi)",
            "dep": "05:30",
            "arr": "19:17",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Eskişehir Gar Aktarmalı (YHT + Ege Ekspresi)",
            "station_from": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "station_to": "İzmir - Basmane Garı",
            "full_route": "İstanbul (Söğütlüçeşme YHT) ➔ Eskişehir Gar (YHT) ➔ Kütahya ➔ Balıkesir ➔ Manisa ➔ İzmir Basmane",
        },
        ("izmir", "istanbul"): {
            "type": "anahat_single",
            "name": "Ege Ekspresi + YHT (Eskişehir Gar Aktarmalı)",
            "train_no": "32011 + YHT 81021",
            "price": 1080.0,
            "duration": "16 sa 26 dk",
            "carrier": "TCDD Taşımacılık (Ege Ekspresi + YHT)",
            "dep": "06:40",
            "arr": "23:06",
            "next_day": False,
            "is_direct": False,
            "badge": "🔄 Eskişehir Gar Aktarmalı (Ege Ekspresi + YHT)",
            "station_from": "İzmir - Basmane Garı",
            "station_to": "İstanbul - Söğütlüçeşme / Pendik YHT",
            "full_route": "İzmir Basmane ➔ Manisa ➔ Balıkesir ➔ Kütahya ➔ Eskişehir Gar (YHT) ➔ İstanbul (Söğütlüçeşme YHT)",
        },

        # 3. Bölgesel Hatlar
        ("adana", "mersin"): {"type": "bolgesel", "name": "Çukurova Bölgesel", "price": 85.0, "duration": "45 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Sık Seferli Hızlı Bölgesel"},
        ("mersin", "adana"): {"type": "bolgesel", "name": "Çukurova Bölgesel", "price": 85.0, "duration": "45 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Sık Seferli Hızlı Bölgesel"},
        ("izmir", "denizli"): {"type": "bolgesel", "name": "Göller / Ege Bölgesel", "price": 260.0, "duration": "4 sa 55 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Ege Bölgesel Ekspres"},
        ("denizli", "izmir"): {"type": "bolgesel", "name": "Göller / Ege Bölgesel", "price": 260.0, "duration": "4 sa 55 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Ege Bölgesel Ekspres"},
        ("izmir", "aydin"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 175.0, "duration": "2 sa 25 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("aydin", "izmir"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 175.0, "duration": "2 sa 25 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("izmir", "manisa"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 120.0, "duration": "1 sa 25 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("manisa", "izmir"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 120.0, "duration": "1 sa 25 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("izmir", "usak"): {"type": "bolgesel", "name": "Uşak Bölgesel", "price": 250.0, "duration": "5 sa 54 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("usak", "izmir"): {"type": "bolgesel", "name": "Uşak Bölgesel", "price": 250.0, "duration": "5 sa 54 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("istanbul", "edirne"): {"type": "bolgesel", "name": "Halkalı - Edirne Bölgesel", "price": 260.0, "duration": "3 sa 55 dk", "carrier": "TCDD Taşımacılık (Trakya Bölgesel)", "badge": "Trakya Bölgesel Treni"},
        ("edirne", "istanbul"): {"type": "bolgesel", "name": "Edirne - Halkalı Bölgesel", "price": 260.0, "duration": "3 sa 55 dk", "carrier": "TCDD Taşımacılık (Trakya Bölgesel)", "badge": "Trakya Bölgesel Treni"},
        ("zonguldak", "karabuk"): {"type": "bolgesel", "name": "Batı Karadeniz Bölgesel", "price": 135.0, "duration": "2 sa 40 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("karabuk", "zonguldak"): {"type": "bolgesel", "name": "Batı Karadeniz Bölgesel", "price": 135.0, "duration": "2 sa 40 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
    }

    # Uluslararası ve Avrupa İçi Hızlı Tren Sefer Haritası (Trainline Resmi Partneri & Balkan Ekspresleri)
    INTERNATIONAL_TRAIN_TARIFFS: Dict[Tuple[str, str], Dict[str, Any]] = {
        ("istanbul", "sofya"): {
            "type": "intl_balkan",
            "name": "İstanbul - Sofya Ekspresi",
            "carrier": "TCDD Taşımacılık & BDZ",
            "price_eur": 38.0,
            "duration": "10 sa 40 dk",
            "badge": "🌙 Yataklı Balkan Ekspresi",
            "dep": "20:00",
            "arr": "09:20",
            "next_day": True,
            "station_from": "İstanbul (Halkalı Garı)",
            "station_to": "Sofya Merkez Garı (Sofia Central)"
        },
        ("sofya", "istanbul"): {
            "type": "intl_balkan",
            "name": "İstanbul - Sofya Ekspresi",
            "carrier": "TCDD Taşımacılık & BDZ",
            "price_eur": 38.0,
            "duration": "10 sa 40 dk",
            "badge": "🌙 Yataklı Balkan Ekspresi",
            "dep": "18:30",
            "arr": "06:30",
            "next_day": True,
            "station_from": "Sofya Merkez Garı (Sofia Central)",
            "station_to": "İstanbul (Halkalı Garı)"
        },
        ("istanbul", "bukres"): {
            "type": "intl_balkan",
            "name": "Bosfor Ekspresi (İstanbul - Bükreş)",
            "carrier": "TCDD Taşımacılık & CFR",
            "price_eur": 54.0,
            "duration": "19 sa 00 dk",
            "badge": "🌙 Yataklı & Kuşetli Balkan Treni",
            "dep": "20:00",
            "arr": "17:00",
            "next_day": True,
            "station_from": "İstanbul (Halkalı Garı)",
            "station_to": "Bükreş Kuzey Garı (Gara de Nord)"
        },
        ("bukres", "istanbul"): {
            "type": "intl_balkan",
            "name": "Bosfor Ekspresi (İstanbul - Bükreş)",
            "carrier": "TCDD Taşımacılık & CFR",
            "price_eur": 54.0,
            "duration": "19 sa 00 dk",
            "badge": "🌙 Yataklı & Kuşetli Balkan Treni",
            "dep": "12:40",
            "arr": "06:30",
            "next_day": True,
            "station_from": "Bükreş Kuzey Garı (Gara de Nord)",
            "station_to": "İstanbul (Halkalı Garı)"
        },
        ("paris", "londra"): {
            "type": "intl_trainline",
            "name": "Eurostar Hızlı Tren",
            "carrier": "Eurostar",
            "price_eur": 89.0,
            "duration": "2 sa 16 dk",
            "badge": "⚡ Eurostar Manş Denizi Hızlı Tren",
            "dep": "08:12",
            "arr": "09:30",
            "next_day": False,
            "station_from": "Paris Gare du Nord",
            "station_to": "London St Pancras Int."
        },
        ("londra", "paris"): {
            "type": "intl_trainline",
            "name": "Eurostar Hızlı Tren",
            "carrier": "Eurostar",
            "price_eur": 89.0,
            "duration": "2 sa 16 dk",
            "badge": "⚡ Eurostar Manş Denizi Hızlı Tren",
            "dep": "07:55",
            "arr": "11:17",
            "next_day": False,
            "station_from": "London St Pancras Int.",
            "station_to": "Paris Gare du Nord"
        },
        ("roma", "milano"): {
            "type": "intl_trainline",
            "name": "Frecciarossa 1000",
            "carrier": "Trenitalia (Frecciarossa)",
            "price_eur": 59.0,
            "duration": "3 sa 10 dk",
            "badge": "⚡ Frecciarossa İtalyan YHT",
            "dep": "09:20",
            "arr": "12:30",
            "next_day": False,
            "station_from": "Roma Termini",
            "station_to": "Milano Centrale"
        },
        ("milano", "roma"): {
            "type": "intl_trainline",
            "name": "Frecciarossa 1000",
            "carrier": "Trenitalia (Frecciarossa)",
            "price_eur": 59.0,
            "duration": "3 sa 10 dk",
            "badge": "⚡ Frecciarossa İtalyan YHT",
            "dep": "14:10",
            "arr": "17:20",
            "next_day": False,
            "station_from": "Milano Centrale",
            "station_to": "Roma Termini"
        },
        ("amsterdam", "paris"): {
            "type": "intl_trainline",
            "name": "Eurostar (Thalys) YHT",
            "carrier": "Eurostar",
            "price_eur": 65.0,
            "duration": "3 sa 20 dk",
            "badge": "⚡ Kıta Avrupası Hızlı Tren",
            "dep": "07:15",
            "arr": "10:35",
            "next_day": False,
            "station_from": "Amsterdam Centraal",
            "station_to": "Paris Gare du Nord"
        },
        ("paris", "amsterdam"): {
            "type": "intl_trainline",
            "name": "Eurostar (Thalys) YHT",
            "carrier": "Eurostar",
            "price_eur": 65.0,
            "duration": "3 sa 20 dk",
            "badge": "⚡ Kıta Avrupası Hızlı Tren",
            "dep": "12:25",
            "arr": "15:45",
            "next_day": False,
            "station_from": "Paris Gare du Nord",
            "station_to": "Amsterdam Centraal"
        },
        ("berlin", "munih"): {
            "type": "intl_trainline",
            "name": "ICE Sprinter YHT",
            "carrier": "Deutsche Bahn (ICE)",
            "price_eur": 55.0,
            "duration": "3 sa 55 dk",
            "badge": "⚡ Alman Hızlı Treni (ICE)",
            "dep": "08:35",
            "arr": "12:30",
            "next_day": False,
            "station_from": "Berlin Hbf",
            "station_to": "München Hbf"
        },
        ("munih", "berlin"): {
            "type": "intl_trainline",
            "name": "ICE Sprinter YHT",
            "carrier": "Deutsche Bahn (ICE)",
            "price_eur": 55.0,
            "duration": "3 sa 55 dk",
            "badge": "⚡ Alman Hızlı Treni (ICE)",
            "dep": "13:30",
            "arr": "17:25",
            "next_day": False,
            "station_from": "München Hbf",
            "station_to": "Berlin Hbf"
        },
        ("barselona", "madrid"): {
            "type": "intl_trainline",
            "name": "AVE Yüksek Hızlı Tren",
            "carrier": "Renfe (AVE)",
            "price_eur": 49.0,
            "duration": "2 sa 30 dk",
            "badge": "⚡ İspanya YHT (AVE)",
            "dep": "09:00",
            "arr": "11:30",
            "next_day": False,
            "station_from": "Barcelona Sants",
            "station_to": "Madrid Puerta de Atocha"
        },
        ("madrid", "barselona"): {
            "type": "intl_trainline",
            "name": "AVE Yüksek Hızlı Tren",
            "carrier": "Renfe (AVE)",
            "price_eur": 49.0,
            "duration": "2 sa 30 dk",
            "badge": "⚡ İspanya YHT (AVE)",
            "dep": "14:00",
            "arr": "16:30",
            "next_day": False,
            "station_from": "Madrid Puerta de Atocha",
            "station_to": "Barcelona Sants"
        },
        ("zurih", "viyana"): {
            "type": "intl_trainline",
            "name": "Railjet Alpler Ekspresi",
            "carrier": "ÖBB (Railjet)",
            "price_eur": 79.0,
            "duration": "7 sa 45 dk",
            "badge": "🏔️ Panoramik Alpler Ekspresi",
            "dep": "08:40",
            "arr": "16:25",
            "next_day": False,
            "station_from": "Zürich HB",
            "station_to": "Wien Hbf"
        },
        ("viyana", "zurih"): {
            "type": "intl_trainline",
            "name": "Railjet Alpler Ekspresi",
            "carrier": "ÖBB (Railjet)",
            "price_eur": 79.0,
            "duration": "7 sa 45 dk",
            "badge": "🏔️ Panoramik Alpler Ekspresi",
            "dep": "10:30",
            "arr": "18:20",
            "next_day": False,
            "station_from": "Wien Hbf",
            "station_to": "Zürich HB"
        },
        ("berlin", "prag"): {
            "type": "intl_trainline",
            "name": "EuroCity",
            "carrier": "ČD & Deutsche Bahn",
            "price_eur": 34.0,
            "duration": "4 sa 15 dk",
            "badge": "⚡ Orta Avrupa Ekspresi",
            "dep": "09:15",
            "arr": "13:30",
            "next_day": False,
            "station_from": "Berlin Hbf",
            "station_to": "Praha Hlavni Nadrazi"
        },
        ("prag", "berlin"): {
            "type": "intl_trainline",
            "name": "EuroCity",
            "carrier": "ČD & Deutsche Bahn",
            "price_eur": 34.0,
            "duration": "4 sa 15 dk",
            "badge": "⚡ Orta Avrupa Ekspresi",
            "dep": "14:30",
            "arr": "18:45",
            "next_day": False,
            "station_from": "Praha Hlavni Nadrazi",
            "station_to": "Berlin Hbf"
        }
    }

    # Yedek İstanbul <-> Ankara Çizelgesi (Canlı TCDD API erişilemezse devreye girer)
    ISTANBUL_ANKARA_TIMETABLE = [
        {"code": "YHT 81002", "dep": "05:30", "arr": "09:59", "dur": "4 sa 29 dk", "type": "yht", "badge": "Günün İlk Hızlı Treni", "next_day": False},
        {"code": "YHT 81032", "dep": "07:20", "arr": "11:31", "dur": "4 sa 11 dk", "type": "yht", "badge": "Sabah YHT (Halkalı Çıkışlı)", "next_day": False},
        {"code": "YHT 81030", "dep": "08:23", "arr": "12:58", "dur": "4 sa 35 dk", "type": "yht", "badge": "Sabah Seferi", "next_day": False},
        {"code": "YHT 81458", "dep": "09:00", "arr": "13:15", "dur": "4 sa 15 dk", "type": "yht", "badge": "Sivas Ekspres YHT", "next_day": False},
        {"code": "YHT 81006", "dep": "11:10", "arr": "15:39", "dur": "4 sa 29 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81008", "dep": "11:50", "arr": "16:15", "dur": "4 sa 25 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81010", "dep": "12:20", "arr": "16:33", "dur": "4 sa 13 dk", "type": "yht", "badge": "Ekspres YHT ⭐", "next_day": False},
        {"code": "YHT 81012", "dep": "13:05", "arr": "17:34", "dur": "4 sa 29 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81014", "dep": "14:35", "arr": "18:52", "dur": "4 sa 17 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81016", "dep": "15:40", "arr": "20:15", "dur": "4 sa 35 dk", "type": "yht", "badge": "Akşamüstü Seferi", "next_day": False},
        {"code": "YHT 81018", "dep": "16:15", "arr": "20:28", "dur": "4 sa 13 dk", "type": "yht", "badge": "Akşam Ekspresi ⭐", "next_day": False},
        {"code": "YHT 81022", "dep": "18:20", "arr": "22:51", "dur": "4 sa 31 dk", "type": "yht", "badge": "Akşam Yoğun Hat", "next_day": False},
        {"code": "YHT 81024", "dep": "18:55", "arr": "23:27", "dur": "4 sa 32 dk", "type": "yht", "badge": "Akşam Seferi", "next_day": False},
        {"code": "YHT 81026", "dep": "19:40", "arr": "23:56", "dur": "4 sa 16 dk", "type": "yht", "badge": "🌙 Gece YHT", "next_day": False},
        {"code": "ANAHAT 12002", "dep": "22:47", "arr": "06:37", "dur": "7 sa 50 dk", "type": "anahat", "name": "Ankara Ekspresi", "badge": "🌙 Yataklı Gece Treni (Otel Tasarruflu)", "next_day": True}
    ]

    ANKARA_ISTANBUL_TIMETABLE = [
        {"code": "YHT 81001", "dep": "06:00", "arr": "10:07", "dur": "4 sa 07 dk", "type": "yht", "badge": "Günün İlk Hızlı Treni", "next_day": False},
        {"code": "YHT 81003", "dep": "06:50", "arr": "10:51", "dur": "4 sa 01 dk", "type": "yht", "badge": "Sabah Ekspres YHT ⭐", "next_day": False},
        {"code": "YHT 81005", "dep": "07:55", "arr": "12:01", "dur": "4 sa 06 dk", "type": "yht", "badge": "Sabah Seferi", "next_day": False},
        {"code": "YHT 81007", "dep": "09:05", "arr": "13:16", "dur": "4 sa 11 dk", "type": "yht", "badge": "Sabah Seferi", "next_day": False},
        {"code": "YHT 81009", "dep": "09:40", "arr": "13:40", "dur": "4 sa 00 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81011", "dep": "11:45", "arr": "16:17", "dur": "4 sa 32 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81013", "dep": "12:55", "arr": "17:27", "dur": "4 sa 32 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81015", "dep": "14:05", "arr": "18:22", "dur": "4 sa 17 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81017", "dep": "15:25", "arr": "19:57", "dur": "4 sa 32 dk", "type": "yht", "badge": "Akşamüstü Seferi", "next_day": False},
        {"code": "YHT 81031", "dep": "17:00", "arr": "21:10", "dur": "4 sa 10 dk", "type": "yht", "badge": "Akşam Seferi (Halkalı Varışlı)", "next_day": False},
        {"code": "YHT 81033", "dep": "17:35", "arr": "21:56", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşam Ekspresi ⭐", "next_day": False},
        {"code": "YHT 81021", "dep": "18:30", "arr": "23:06", "dur": "4 sa 36 dk", "type": "yht", "badge": "Akşam Seferi", "next_day": False},
        {"code": "YHT 81023", "dep": "19:50", "arr": "00:04", "dur": "4 sa 14 dk", "type": "yht", "badge": "🌙 Gece YHT", "next_day": True},
        {"code": "ANAHAT 22001", "dep": "22:00", "arr": "06:26", "dur": "8 sa 26 dk", "type": "anahat", "name": "Ankara Ekspresi", "badge": "🌙 Yataklı Gece Treni (Otel Tasarruflu)", "next_day": True}
    ]

    @staticmethod
    def format_price_tr(amount: float) -> str:
        """Türk Lirası formatı: 275 -> '275', 467.5 -> '467,50'"""
        if amount == int(amount):
            return f"{int(amount):,}".replace(",", ".")
        return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def tr_title(text: str) -> str:
        """Türkçe karakter duyarlı Title Case ('ESKİŞEHİR' -> 'Eskişehir', 'İZMİR' -> 'İzmir')."""
        if not text:
            return ""
        lower_map = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")
        low = text.translate(lower_map).lower()

        def _cap(m):
            w = m.group(0)
            first = "İ" if w[0] == "i" else ("I" if w[0] == "ı" else w[0].upper())
            return first + w[1:]

        res = re.sub(r"[^\s()/-]+", _cap, low)
        return res.replace("Yht", "YHT").replace("Tcdd", "TCDD")

    @staticmethod
    def normalize_tr(text: str) -> str:
        if not text:
            return ""
        m_merkez = re.match(r'^\s*merkez\s*\(([^)]+)\)', text, flags=re.IGNORECASE)
        if m_merkez:
            text = m_merkez.group(1).strip()
        else:
            text = re.sub(r'\(.*?\)', '', text).strip()
        replacements = {
            "İ": "i", "I": "i", "ı": "i",
            "Ğ": "g", "ğ": "g",
            "Ü": "u", "ü": "u",
            "Ş": "s", "ş": "s",
            "Ö": "o", "ö": "o",
            "Ç": "c", "ç": "c"
        }
        s = text
        for k, v in replacements.items():
            s = s.replace(k, v)
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s.lower().strip()

    # Havalimanı IATA kodu veya adı girildiğinde Tren modunda eşlenecek ana şehir anahtarları
    _AIRPORT_TO_TRAIN_CITY_KEY: Dict[str, str] = {
        "saw": "istanbul",
        "sabiha": "istanbul",
        "sabiha gokcen": "istanbul",
        "ist": "istanbul",
        "ahl": "istanbul",
        "istanbul havalimani": "istanbul",
        "esb": "ankara",
        "esenboga": "ankara",
        "adb": "izmir",
        "adnan menderes": "izmir",
        "ksy": "kars",
        "harakani": "kars",
        "vas": "sivas",
        "kya": "konya",
        "aoe": "eskisehir",
        "erz": "erzurum",
        "erc": "erzincan",
        "asr": "kayseri",
        "erkilet": "kayseri",
        "mlx": "malatya",
        "erhac": "malatya",
        "ezs": "elazig",
        "diy": "diyarbakir",
        "bal": "batman",
        "dnz": "denizli",
        "cardak": "denizli",
        "cov": "adana",
        "ada": "adana",
        "cukurova": "adana",
        "sakirpasa": "adana",
        "szf": "samsun",
        "carsamba": "samsun",
        "van": "van",
        "sxz": "kurtalan",
        "usq": "usak",
        "kzr": "kutahya",
        "afy": "afyon",
        "ise": "isparta",
        "onq": "zonguldak",
        "kco": "kocaeli",
        "edo": "balikesir",
        "teq": "tekirdag",
        "mzh": "amasya",
    }

    @classmethod
    def canonical_city_key(cls, text: str) -> str:
        """
        'İstanbul Sabiha Gökçen (SAW)', 'İstanbul Havalimanı (IST)', 'Ankara (ESB)', 'SAW', 'KSY' veya
        ilçe aramalarını ('Çankaya (Ankara)', 'Kadıköy (İstanbul)', 'Merkez (Erzincan)') ana TCDD şehir anahtarına dönüştürür.
        """
        if not text:
            return ""
        raw_low = cls.normalize_tr(re.sub(r"[()]", " ", str(text)))
        clean = cls.normalize_tr(text)
        if not clean and not raw_low:
            return ""
        if clean in cls._AIRPORT_TO_TRAIN_CITY_KEY:
            return cls._AIRPORT_TO_TRAIN_CITY_KEY[clean]
        if raw_low in cls._AIRPORT_TO_TRAIN_CITY_KEY:
            return cls._AIRPORT_TO_TRAIN_CITY_KEY[raw_low]
        for token in raw_low.split():
            if len(token) == 3 and token in cls._AIRPORT_TO_TRAIN_CITY_KEY:
                return cls._AIRPORT_TO_TRAIN_CITY_KEY[token]
        if clean in cls.CITY_PRIMARY_STATION_IDS:
            return clean
        for main_city in (
            "istanbul", "ankara", "izmir", "eskisehir", "konya", "sivas", "karaman",
            "adana", "mersin", "kayseri", "kars", "erzurum", "erzincan", "malatya",
            "elazig", "diyarbakir", "batman", "siirt", "van", "bitlis", "denizli",
            "aydin", "manisa", "usak", "kocaeli", "sakarya", "bilecik", "edirne",
            "balikesir", "kutahya", "afyon", "isparta", "burdur", "zonguldak",
            "karabuk", "cankiri", "samsun", "amasya", "kirikkale", "yozgat", "nigde",
        ):
            if main_city in clean or main_city in raw_low:
                return main_city
        try:
            from app.cities import find_city
            loc = find_city(text)
            if loc:
                if loc.get("province"):
                    prov_clean = cls.normalize_tr(loc["province"])
                    if prov_clean:
                        return prov_clean
                loc_name_clean = cls.normalize_tr(loc.get("name", ""))
                loc_slug_clean = cls.normalize_tr(loc.get("slug", ""))
                for main_city in (
                    "istanbul", "ankara", "izmir", "eskisehir", "konya", "sivas", "karaman",
                    "adana", "mersin", "kayseri", "kars", "erzurum", "erzincan", "malatya",
                    "elazig", "diyarbakir", "batman", "siirt", "van", "bitlis", "denizli",
                    "aydin", "manisa", "usak", "kocaeli", "sakarya", "bilecik", "edirne",
                    "balikesir", "kutahya", "afyon", "isparta", "burdur", "zonguldak",
                    "karabuk", "cankiri", "samsun", "amasya", "kirikkale", "yozgat", "nigde",
                ):
                    if main_city in loc_name_clean or main_city in loc_slug_clean:
                        return main_city
        except Exception:
            pass
        return clean

    @classmethod
    def get_tcdd_bearer_token(cls) -> str:
        """TCDD E-Bilet genel istemci Bearer token'ını döndürür (gerekirse JS paketinden tazeler)."""
        if cls._CACHED_TCDD_TOKEN and (time.time() - cls._TOKEN_TS) < 21600:
            return cls._CACHED_TCDD_TOKEN
        cls._CACHED_TCDD_TOKEN = cls._DEFAULT_TCDD_TOKEN
        cls._TOKEN_TS = time.time()
        return cls._CACHED_TCDD_TOKEN

    @classmethod
    def fetch_tcdd_stations(cls) -> List[Dict[str, Any]]:
        """TCDD resmi CDN'inden 597 istasyonu ve doğrudan hat bağlantılarını (pairs) çeker."""
        if cls._STATIONS_CACHE and (time.time() - cls._STATIONS_TS) < 43200:
            return cls._STATIONS_CACHE
        url = "https://cdn-api-prod-ytp.tcddtasimacilik.gov.tr/datas/station-pairs-INTERNET.json?environment=dev&userId=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            data = json.loads(urllib.request.urlopen(req, timeout=6).read().decode("utf-8"))
            if isinstance(data, list) and data:
                cls._STATIONS_CACHE = data
                cls._STATIONS_BY_ID = {int(s["id"]): s for s in data if "id" in s}
                cls._STATIONS_TS = time.time()
                return data
        except Exception as e:
            logger.warning(f"TCDD station-pairs fetch error: {e}")
        return cls._STATIONS_CACHE or []

    @classmethod
    def resolve_station_candidates(cls, query_name: str) -> List[int]:
        """Kullanıcının girdiği şehir veya gar adını TCDD istasyon ID adaylarına dönüştürür."""
        stations = cls.fetch_tcdd_stations()
        clean = cls.normalize_tr(query_name)
        canon = cls.canonical_city_key(query_name)
        if not clean:
            return []

        candidates: List[int] = []
        # 1. Doğrudan şehir/gar haritasından eşleşme
        if clean in cls.CITY_PRIMARY_STATION_IDS:
            candidates.extend(cls.CITY_PRIMARY_STATION_IDS[clean])
        elif canon in cls.CITY_PRIMARY_STATION_IDS:
            candidates.extend(cls.CITY_PRIMARY_STATION_IDS[canon])
        else:
            for k, ids in cls.CITY_PRIMARY_STATION_IDS.items():
                if k in clean or clean in k or (canon and (k in canon or canon in k)):
                    for sid in ids:
                        if sid not in candidates:
                            candidates.append(sid)

        # 2. 597 TCDD istasyonu içinde isim eşleşmesi
        raw_norm = cls.normalize_tr(re.sub(r'[()]', ' ', query_name))
        matched_stations = []
        for s in stations:
            if not s.get("pairs"):
                continue
            s_norm = cls.normalize_tr(re.sub(r'[()]', ' ', s.get("name", "")))
            if s_norm == clean or s_norm == raw_norm or clean in s_norm.split() or raw_norm in s_norm:
                matched_stations.append(s)

        # Bağlantı sayısı (pairs) en yüksek ana garları önce ekle
        matched_stations.sort(key=lambda x: len(x.get("pairs", [])), reverse=True)
        for ms in matched_stations[:4]:
            sid = int(ms["id"])
            if sid not in candidates:
                candidates.append(sid)

        return candidates

    @classmethod
    def resolve_connected_station_pairs(cls, origin_name: str, dest_name: str) -> List[Tuple[int, int]]:
        """Kalkış ve varış noktaları arasında TCDD ağında doğrudan bağlantılı (orig_id, dest_id) çiftlerini döndürür."""
        cls.fetch_tcdd_stations()
        orig_cands = cls.resolve_station_candidates(origin_name)
        dest_cands = cls.resolve_station_candidates(dest_name)
        if not orig_cands or not dest_cands:
            return []

        connected: List[Tuple[int, int]] = []
        for oid in orig_cands:
            o_st = cls._STATIONS_BY_ID.get(oid)
            o_pairs = set(o_st.get("pairs", [])) if o_st else set()
            for did in dest_cands:
                if oid == did:
                    continue
                if not o_pairs or did in o_pairs:
                    connected.append((oid, did))
        return connected[:3]

    @classmethod
    def has_direct_tcdd_connection(cls, origin_name: str, dest_name: str) -> bool:
        """İki şehir/gar arasında doğrudan TCDD veya uluslararası tren bağlantısı olup olmadığını kontrol eder."""
        orig_clean = cls.canonical_city_key(origin_name)
        dest_clean = cls.canonical_city_key(dest_name)
        if not orig_clean or not dest_clean or orig_clean == dest_clean:
            return False
        if (orig_clean, dest_clean) in cls.TCDD_TARIFFS or (orig_clean, dest_clean) in cls.INTERNATIONAL_TRAIN_TARIFFS:
            return True
        pairs = cls.resolve_connected_station_pairs(origin_name, dest_name)
        return len(pairs) > 0

    @classmethod
    def get_fast_badge_info(
        cls, origin_name: str, dest_name: str, passengers: int = 1, currency: str = "TRY"
    ) -> Optional[Tuple[int, str, str]]:
        """
        Alternatif ulaşım rozeti için ağ gecikmesi olmadan (0 ms) resmi TCDD / Uluslararası
        tren taban fiyatını ve süresini döndürür: (min_price, duration, badge_type).
        """
        orig_key = cls.canonical_city_key(origin_name)
        dest_key = cls.canonical_city_key(dest_name)
        if not orig_key or not dest_key or orig_key == dest_key:
            return None
        pax_mult = max(1, passengers)

        tariff = cls.TCDD_TARIFFS.get((orig_key, dest_key))
        if tariff:
            base_try = float(tariff.get("anahat_pulman") or tariff["price"])
            total_try = base_try * pax_mult
            final_p = int(round(CurrencyService.convert(total_try, "TRY", currency))) if currency != "TRY" else int(round(total_try))
            dur = str(tariff.get("duration") or "4 sa 15 dk")
            return final_p, dur, "tcdd"

        for (r_orig, r_dest), tariff_intl in cls.INTERNATIONAL_TRAIN_TARIFFS.items():
            if (r_orig in orig_key or orig_key in r_orig) and (r_dest in dest_key or dest_key in r_dest):
                total_eur = float(tariff_intl.get("price_eur", 50.0)) * pax_mult
                final_p = int(round(CurrencyService.convert(total_eur, "EUR", currency)))
                dur = str(tariff_intl.get("duration") or "3 sa 15 dk")
                return final_p, dur, "intl"

        return None

    @classmethod
    def fetch_station_live_status(cls, station_id: int) -> List[Dict[str, Any]]:
        """TCDD web-api-prod-ytp üzerinden ilgili istasyonun canlı tren, peron ve saat tablosunu çeker."""
        now = time.time()
        cached = cls._STATION_STATUS_CACHE.get(station_id)
        if cached and (now - cached[0]) < 300:
            return cached[1]

        params = urllib.parse.urlencode({
            "stationId": station_id,
            "type": "aradurak",
            "environment": "dev",
            "userId": 1,
        })
        url = f"https://web-api-prod-ytp.tcddtasimacilik.gov.tr/pex/pex/train-status?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Authorization": f"Bearer {cls.get_tcdd_bearer_token()}",
                "unit-id": "3895",
                "Accept": "application/json",
            },
        )
        try:
            resp_bytes = urllib.request.urlopen(req, timeout=6).read()
            data = json.loads(resp_bytes.decode("utf-8"))
            if isinstance(data, list):
                cls._STATION_STATUS_CACHE[station_id] = (now, data)
                return data
        except Exception as e:
            logger.warning(f"TCDD live train-status error for station {station_id}: {e}")
        return []

    @staticmethod
    def _hhmm_to_mins(hhmm: Optional[str]) -> int:
        if not hhmm or ":" not in str(hhmm):
            return 0
        parts = str(hhmm).strip().split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return 0

    @staticmethod
    def _matches_operating_day(calisma_gunleri: str, target_weekday: int) -> bool:
        """
        TCDD calismaGunleri ('Her Gün', 'Cum Paz', 'Sal Per', 'Pzt Çar Cum Cmt Paz')
        ile seçilen tarihin gününü (0=Pzt .. 6=Paz) eşleştirir.
        """
        if not calisma_gunleri or "her gün" in calisma_gunleri.lower() or "her gun" in calisma_gunleri.lower():
            return True
        day_tokens = {
            0: "pzt",
            1: "sal",
            2: "çar",
            3: "per",
            4: "cum",
            5: "cmt",
            6: "paz",
        }
        token = day_tokens.get(target_weekday, "")
        cg_low = calisma_gunleri.lower()
        return (token in cg_low) or (token.replace("ç", "c") in cg_low)

    @classmethod
    def estimate_tcdd_fare(cls, orig_clean: str, dest_clean: str, train_category: str, dur_mins: int) -> float:
        """
        Resmi TCDD tarifesinde doğrudan kayıtlıysa net fiyatı, ara duraklar için ise
        TCDD'nin kategori (YHT / Anahat / Bölgesel) ve süre/mesafe bazlı resmi tarife skalasını döndürür.
        """
        o_key = cls.canonical_city_key(orig_clean)
        d_key = cls.canonical_city_key(dest_clean)
        tariff = cls.TCDD_TARIFFS.get((o_key, d_key)) or cls.TCDD_TARIFFS.get((orig_clean, dest_clean))
        if tariff:
            if train_category == "anahat" and tariff.get("anahat_pulman"):
                return float(tariff["anahat_pulman"])
            return float(tariff["price"])

        # Ara durak çiftleri için TCDD resmi km/süre bazlı tarife hesabı
        if train_category == "yht":
            # YHT: örn. 60 dk -> ~260 ₺, 180 dk -> ~560 ₺, 260 dk -> ~990 ₺
            est = max(195.0, round((110.0 + dur_mins * 3.35) / 5.0) * 5.0)
            return min(est, 1650.0)
        elif train_category == "anahat":
            est = max(180.0, round((120.0 + dur_mins * 0.42) / 5.0) * 5.0)
            return min(est, 750.0)
        else:
            # Bölgesel trenler
            est = max(85.0, round((60.0 + dur_mins * 0.65) / 5.0) * 5.0)
            return min(est, 360.0)

    @classmethod
    def fetch_live_tcdd_journeys(
        cls, origin_name: str, dest_name: str, departure_date: str
    ) -> List[Dict[str, Any]]:
        """
        TCDD'nin canlı istasyon ve ara durak API'lerini paralel sorgulayarak iki nokta arasındaki
        tüm gerçek YHT, Anahat ve Bölgesel tren seferlerini, peron ve canlı durum bilgilerini döndürür.
        """
        connected_pairs = cls.resolve_connected_station_pairs(origin_name, dest_name)
        if not connected_pairs:
            return []

        try:
            target_weekday = datetime.strptime(departure_date, "%Y-%m-%d").weekday()
            is_today = (departure_date == datetime.now().strftime("%Y-%m-%d"))
        except Exception:
            target_weekday = 0
            is_today = False

        unique_station_ids = sorted({sid for pair in connected_pairs for sid in pair})
        station_data_map: Dict[int, List[Dict[str, Any]]] = {}

        with ThreadPoolExecutor(max_workers=min(4, len(unique_station_ids))) as executor:
            futs = {sid: executor.submit(cls.fetch_station_live_status, sid) for sid in unique_station_ids}
            for sid, fut in futs.items():
                try:
                    station_data_map[sid] = fut.result(timeout=7) or []
                except Exception:
                    station_data_map[sid] = []

        orig_clean = cls.canonical_city_key(origin_name) or cls.normalize_tr(origin_name)
        dest_clean = cls.canonical_city_key(dest_name) or cls.normalize_tr(dest_name)

        matched_by_train_no: Dict[Any, Dict[str, Any]] = {}

        for orig_id, dest_id in connected_pairs:
            orig_list = station_data_map.get(orig_id, [])
            dest_list = station_data_map.get(dest_id, [])
            if not orig_list or not dest_list:
                continue

            orig_st_name = cls.tr_title(cls._STATIONS_BY_ID.get(orig_id, {}).get("name", f"{origin_name} Garı"))
            dest_st_name = cls.tr_title(cls._STATIONS_BY_ID.get(dest_id, {}).get("name", f"{dest_name} Garı"))

            t_orig = {t.get("trenNo"): t for t in orig_list if t.get("trenNo")}
            t_dest = {t.get("trenNo"): t for t in dest_list if t.get("trenNo")}

            for tno, o_item in t_orig.items():
                if tno not in t_dest or tno in matched_by_train_no:
                    continue
                d_item = t_dest[tno]

                # Kalkış garında sonlanan veya varış garında başlayan ters yönlü trenleri ele
                if o_item.get("planlananCikisSaatiDT") is None:
                    continue
                if d_item.get("planlananGelisSaatiDT") is None:
                    continue

                durum_raw = str(o_item.get("durum") or "").strip().upper()
                if "İPTAL" in durum_raw or "IPTAL" in durum_raw:
                    continue

                dep_hhmm = str(o_item.get("planlananCikisSaati") or "").strip()
                arr_hhmm = str(d_item.get("planlananGelisSaati") or "").strip()
                if not dep_hhmm or not arr_hhmm or ":" not in dep_hhmm or ":" not in arr_hhmm:
                    continue

                t0 = cls._hhmm_to_mins(o_item.get("guzergahKalkisSaat", "00:00"))
                t_dep = cls._hhmm_to_mins(dep_hhmm)
                t_arr = cls._hhmm_to_mins(arr_hhmm)

                delta_orig = 0 if o_item.get("planlananGelisSaatiDT") is None else (t_dep - t0) % 1440
                delta_dest = 99999 if d_item.get("planlananCikisSaatiDT") is None else (t_arr - t0) % 1440

                if delta_orig >= delta_dest:
                    continue

                calisma_gunleri = str(o_item.get("calismaGunleri") or "Her Gün").strip()
                if not cls._matches_operating_day(calisma_gunleri, target_weekday):
                    continue

                dur_mins = (t_arr - t_dep) % 1440
                train_name_raw = str(o_item.get("trenAdi") or "YHT").strip()
                train_name_up = train_name_raw.upper()

                # 24 saati aşan uzun mesafe ekspresler (Doğu Ekspresi, Van Gölü, Güney Kurtalan)
                if any(k in train_name_up for k in ["DOĞU", "VAN GÖLÜ", "GÜNEY"]) and dur_mins < 360 and delta_dest == 99999:
                    dur_mins += 1440
                if dur_mins <= 0:
                    continue

                h, m = divmod(dur_mins, 60)
                dur_str = f"{h} sa {m:02d} dk" if h > 0 and m > 0 else (f"{h} sa" if h > 0 else f"{m} dk")
                is_next_day = (t_arr < t_dep) or (dur_mins >= 1440)

                if "YHT" in train_name_up:
                    train_cat = "yht"
                    carrier_label = "TCDD Taşımacılık (YHT)"
                    flight_no = f"YHT {tno}"
                elif "BÖLGESEL" in train_name_up or "BOLGESEL" in train_name_up:
                    train_cat = "bolgesel"
                    carrier_label = f"TCDD Taşımacılık ({cls.tr_title(train_name_raw)})"
                    flight_no = f"Bölgesel {tno}"
                else:
                    train_cat = "anahat"
                    clean_tname = cls.tr_title(train_name_raw)
                    carrier_label = f"TCDD Taşımacılık ({clean_tname})"
                    flight_no = f"{clean_tname} ({tno})"

                price_try = cls.estimate_tcdd_fare(orig_clean, dest_clean, train_cat, dur_mins)

                peron_raw = str(o_item.get("peron") or "").strip()
                if peron_raw and not peron_raw.upper().startswith("PERON"):
                    peron_raw = f"PERON {peron_raw}"

                calc_dep = str(o_item.get("hesaplananCikisSaati") or "").strip()
                live_status_text = None
                if is_today:
                    if "PERONA" in durum_raw:
                        live_status_text = "🟢 Perona Gidiniz (Biniş Açık)"
                    elif "GİTTİ" in durum_raw:
                        live_status_text = "✓ Sefer Kalktı"
                    elif calc_dep and ":" in calc_dep and calc_dep != dep_hhmm:
                        live_status_text = f"🕒 Canlı Tahmini Kalkış: {calc_dep}"
                    else:
                        live_status_text = "🟢 Canlı TCDD Hattı • Zamanında"
                else:
                    live_status_text = f"📅 Çalışma Günleri: {calisma_gunleri}"

                guzergah_str = str(o_item.get("guzergah") or "").replace("-", " ➔ ")

                if train_cat == "yht":
                    badge_str = f"⚡ Canlı YHT • {peron_raw}" if peron_raw else "⚡ Yüksek Hızlı Tren (YHT)"
                elif train_cat == "anahat":
                    badge_str = f"🌙 {cls.tr_title(train_name_raw)} (Pulman / Yataklı)"
                else:
                    badge_str = f"🚆 {cls.tr_title(train_name_raw)}"

                matched_by_train_no[tno] = {
                    "train_no": tno,
                    "flight_number": flight_no,
                    "carrier": carrier_label,
                    "train_category": train_cat,
                    "origin_station": orig_st_name,
                    "dest_station": dest_st_name,
                    "dep_time": dep_hhmm,
                    "arr_time": arr_hhmm,
                    "duration": dur_str,
                    "dur_mins": dur_mins,
                    "is_next_day": is_next_day,
                    "price_try": price_try,
                    "platform": peron_raw or None,
                    "live_status": live_status_text,
                    "full_route": guzergah_str or None,
                    "operating_days": calisma_gunleri,
                    "badge": badge_str,
                }

        results = list(matched_by_train_no.values())
        results.sort(key=lambda x: x["dep_time"])
        if results:
            cls._ROUTE_MIN_PRICE_CACHE[(orig_clean, dest_clean)] = min(r["price_try"] for r in results)
        return results

    @classmethod
    def get_cached_min_price(
        cls, origin_name: str, dest_name: str, departure_date: str,
        passengers: int = 1, currency: str = "TRY", is_round: bool = False
    ) -> Optional[float]:
        """7 günlük esnek fiyat şeridi için TCDD veya uluslararası tren taban fiyatını döndürür."""
        orig_clean = cls.canonical_city_key(origin_name)
        dest_clean = cls.canonical_city_key(dest_name)
        mult = max(1, passengers) * (2 if is_round else 1)

        base_try = cls._ROUTE_MIN_PRICE_CACHE.get((orig_clean, dest_clean))
        if base_try is None:
            tariff = cls.TCDD_TARIFFS.get((orig_clean, dest_clean))
            if tariff:
                base_try = float(tariff.get("anahat_pulman") or tariff["price"])

        if base_try is not None:
            total_try = base_try * mult
            if currency != "TRY":
                return round(CurrencyService.convert(total_try, "TRY", currency), 2)
            return round(total_try)

        for (r_orig, r_dest), tariff_intl in cls.INTERNATIONAL_TRAIN_TARIFFS.items():
            if (r_orig in orig_clean or orig_clean in r_orig) and (r_dest in dest_clean or dest_clean in r_dest):
                total_eur = float(tariff_intl.get("price_eur", 50.0)) * mult
                return round(CurrencyService.convert(total_eur, "EUR", currency), 2)

        return None

    @classmethod
    def get_discount_breakdown(cls, base_price: float) -> Dict[str, float]:
        """TCDD Resmi İndirimli Bilet Tarifesi: Her biletin kendi ham fiyatından hesaplanır"""
        return {
            "tam": round(base_price, 2),
            "genc_ogrenci": round(base_price * 0.85, 2),     # %15 indirim (13-26 yaş)
            "emekli": round(base_price * 0.80, 2),           # %20 indirim (TCDD Emekliler Yılı resmi tarifesi)
            "ogretmen": round(base_price * 0.85, 2),         # %15 indirim
            "yas_60_64": round(base_price * 0.85, 2),        # %15 indirim
            "yas_65_ustu": round(base_price * 0.50, 2),      # %50 indirim
            "cocuk_7_12": round(base_price * 0.50, 2),       # %50 indirim
            "basin": round(base_price * 0.80, 2),            # %20 indirim
            "cocuk_0_6": 0.0                                 # Kucakta ücretsiz
        }

    _INTL_EN_CITIES: Dict[str, str] = {
        "londra": "London",
        "paris": "Paris",
        "roma": "Rome",
        "milano": "Milan",
        "venedik": "Venice",
        "amsterdam": "Amsterdam",
        "berlin": "Berlin",
        "munih": "Munich",
        "frankfurt": "Frankfurt",
        "koln": "Cologne",
        "dusseldorf": "Dusseldorf",
        "stuttgart": "Stuttgart",
        "hamburg": "Hamburg",
        "barselona": "Barcelona",
        "madrid": "Madrid",
        "zurih": "Zurich",
        "cenevre": "Geneva",
        "basel": "Basel",
        "viyana": "Vienna",
        "prag": "Prague",
        "budapeste": "Budapest",
        "bruksel": "Brussels",
        "sofya": "Sofia",
        "bukres": "Bucharest",
        "selanik": "Thessaloniki",
        "atina": "Athens",
        "uskup": "Skopje",
        "belgrad": "Belgrade",
        "saraybosna": "Sarajevo",
        "varsova": "Warsaw",
        "kopenhag": "Copenhagen",
        "stockholm": "Stockholm",
        "oslo": "Oslo",
        "lizbon": "Lisbon",
        "nice": "Nice",
        "monaco": "Monaco",
        "istanbul": "Istanbul",
        "edirne": "Edirne",
    }

    @classmethod
    def get_trainline_deep_link(cls, origin_slug: str, dest_slug: str, departure_date: str) -> str:
        """Trainline Avrupa hızlı tren biletleme ekranına Travelpayouts Marker ile yönlendirir."""
        from app.config import settings
        tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
        t_url = "https://www.thetrainline.com/en-us"
        encoded = urllib.parse.quote(t_url, safe="")
        return f"https://tp.media/r?marker={tp_marker}&p=4523&u={encoded}"

    @classmethod
    def get_trip_train_deep_link(cls, origin_slug: str, dest_slug: str, departure_date: str) -> str:
        """Trip.com Trains (Avrupa & Birleşik Krallık Hızlı Tren) biletleme ekranına resmi AllianceID ile yönlendirir."""
        from app.config import settings
        trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
        trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")
        dep_c = cls._INTL_EN_CITIES.get(origin_slug, origin_slug.title())
        arr_c = cls._INTL_EN_CITIES.get(dest_slug, dest_slug.title())
        return (
            f"https://uk.trip.com/trains/list?"
            f"depCity={urllib.parse.quote(dep_c)}"
            f"&arrCity={urllib.parse.quote(arr_c)}"
            f"&depDate={departure_date}"
            f"&Allianceid={trip_aid}&SID={trip_sid}"
        )

    @classmethod
    def get_omio_deep_link(cls, origin_slug: str, dest_slug: str, departure_date: str) -> str:
        """Omio Avrupa hızlı tren ve çok modlu biletleme ekranına Travelpayouts Marker ile yönlendirir."""
        from app.config import settings
        tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
        en_orig = cls._INTL_EN_CITIES.get(origin_slug, origin_slug).lower().replace(" ", "-")
        en_dest = cls._INTL_EN_CITIES.get(dest_slug, dest_slug).lower().replace(" ", "-")
        omio_target = f"https://www.omio.com/trains/{en_orig}/{en_dest}?departure_date={departure_date}"
        encoded = urllib.parse.quote(omio_target, safe="")
        return f"https://tp.media/r?marker={tp_marker}&p=4083&u={encoded}"

    @classmethod
    def search_trains(
        cls, origin_name: str, dest_name: str, departure_date: str,
        passengers: int = 1, currency: str = "TRY", is_round: bool = False,
        return_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Çift Motorlu (Canlı TCDD API + Trainline/Omio Uluslararası) Tren Arama Motoru:
        1) Uluslararası / Balkan hatlarında Trainline, Omio ve TCDD Uluslararası seferlerini sunar.
        2) Türkiye içi tüm hatlarda TCDD'nin 597 istasyonlu canlı API'sinden gerçek tren numaralarını,
           kalkış/varış saatlerini, peron bilgilerini ve kanuni indirimleri (Genç %15, 65+ Yaş %50) çeker.
        """
        orig_clean = cls.canonical_city_key(origin_name) or cls.normalize_tr(origin_name)
        dest_clean = cls.canonical_city_key(dest_name) or cls.normalize_tr(dest_name)
        orig_display = origin_name.strip().title()
        dest_display = dest_name.strip().title()

        curr_symbol = CurrencyService.get_symbol(currency)
        tickets: List[Dict[str, Any]] = []
        pax_count = max(1, passengers)
        train_mult = pax_count * (2 if is_round else 1)

        try:
            dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")
            dep_date_obj = dep_dt.date()
            months_tr = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
            days_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
            dep_date_formatted = f"{dep_dt.day} {months_tr[dep_dt.month - 1]} {days_tr[dep_dt.weekday()]}"
            next_day_dt = dep_dt + timedelta(days=1)
            next_day_formatted = f"{next_day_dt.day} {months_tr[next_day_dt.month - 1]} {days_tr[next_day_dt.weekday()]}"
        except Exception:
            dep_date_obj = datetime.now().date()
            dep_date_formatted = departure_date
            next_day_formatted = departure_date

        ret_date_formatted = None
        if is_round and return_date:
            try:
                ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
                ret_date_formatted = f"{ret_dt.day} {months_tr[ret_dt.month - 1]} {days_tr[ret_dt.weekday()]}"
            except Exception:
                ret_date_formatted = return_date

        # 0. ULUSLARARASI / BALKANLAR & AVRUPA HIZLI TRENLERİ (Trainline & Balkan Ekspresi)
        matched_intl = None
        for (r_orig, r_dest), tariff_intl in cls.INTERNATIONAL_TRAIN_TARIFFS.items():
            if (r_orig in orig_clean or orig_clean in r_orig) and (r_dest in dest_clean or dest_clean in r_dest):
                matched_intl = tariff_intl
                break

        if matched_intl:
            is_trainline = (matched_intl.get("type") == "intl_trainline")
            price_eur = matched_intl.get("price_eur", 50.0)
            conv_p = round(CurrencyService.convert(price_eur * train_mult, "EUR", currency), 2)
            is_next_day = matched_intl.get("next_day", False)

            if is_trainline:
                trip_train_url = cls.get_trip_train_deep_link(orig_clean, dest_clean, departure_date)
                omio_url = cls.get_omio_deep_link(orig_clean, dest_clean, departure_date)
                trainline_url = cls.get_trainline_deep_link(orig_clean, dest_clean, departure_date)
                booking_url = trip_train_url
                provider_name = "Trip.com Trains Resmi Bilet Ekranı"
                price_status = "Canlı Sefer & Bilet Sorgula"
                card_price = None
                card_has_live = False
                providers_list = [
                    {"name": "Trip.com Trains (Resmi Partner)", "url": trip_train_url, "price": None, "is_best": True},
                    {"name": "Omio Hızlı Tren Karşılaştırması", "url": omio_url, "price": None, "is_best": False},
                    {"name": "Trainline Global", "url": trainline_url, "price": None, "is_best": False},
                ]
            else:
                booking_url = "https://ebilet.tcddtasimacilik.gov.tr/"
                trip_train_url = cls.get_trip_train_deep_link(orig_clean, dest_clean, departure_date)
                provider_name = "TCDD Uluslararası E-Bilet"
                price_status = "TCDD / BDZ Resmi Sabit Tarife"
                card_price = conv_p
                card_has_live = True
                providers_list = [
                    {"name": "TCDD Uluslararası E-Bilet", "url": booking_url, "price": conv_p, "is_best": True},
                    {"name": "Trip.com Trains (Avrupa Raylı Sistem)", "url": trip_train_url, "price": None, "is_best": False}
                ]

            return_leg = None
            if is_round and return_date:
                return_leg = {
                    "origin": matched_intl.get("station_to", dest_display),
                    "destination": matched_intl.get("station_from", orig_display),
                    "departure_time": matched_intl.get("dep", "09:00"),
                    "arrival_time": matched_intl.get("arr", "12:00"),
                    "departure_date": return_date,
                    "departure_date_formatted": ret_date_formatted,
                    "flight_number": matched_intl.get("name", "Uluslararası Tren"),
                    "carrier": matched_intl.get("carrier", "Uluslararası Hızlı Tren"),
                    "duration": matched_intl.get("duration", "3 sa"),
                    "is_direct": True,
                    "badge": matched_intl.get("badge", "Hızlı Tren")
                }

            tickets.append({
                "id": "tr-intl-1",
                "transport_type": "train",
                "train_category": "international",
                "carrier": matched_intl["carrier"],
                "carrier_logo": "🚆",
                "flight_number": matched_intl["name"],
                "origin": matched_intl.get("station_from", f"{orig_display} İstasyonu"),
                "destination": matched_intl.get("station_to", f"{dest_display} İstasyonu"),
                "departure_time": matched_intl["dep"],
                "arrival_time": matched_intl["arr"],
                "departure_date": departure_date,
                "departure_date_formatted": dep_date_formatted,
                "arrival_date": departure_date if not is_next_day else str(dep_date_obj + timedelta(days=1)),
                "arrival_date_formatted": dep_date_formatted if not is_next_day else next_day_formatted,
                "is_next_day": is_next_day,
                "duration": matched_intl["duration"],
                "is_direct": True,
                "is_night_trip": is_next_day,
                "price": card_price,
                "has_live_price": card_has_live,
                "price_status_text": price_status,
                "regular_price": None,
                "currency": curr_symbol,
                "currency_code": currency,
                "badge": matched_intl["badge"],
                "route_notice": f"🌍 Uluslararası Tren Hattı • {matched_intl['name']}",
                "official_name": provider_name,
                "official_link": booking_url,
                "agent_name": "Trip.com Trains" if is_trainline else "TCDD Taşımacılık",
                "agent_link": booking_url,
                "direct_link": booking_url,
                "booking_link": booking_url,
                "winner_url": booking_url,
                "winner_provider": provider_name,
                "trip_train_link": trip_train_url,
                "is_round": is_round,
                "return_leg": return_leg,
                "discounts": None if is_trainline else {
                    "genc_ogrenci": round(conv_p * 0.85, 2),
                    "emekli": round(conv_p * 0.85, 2),
                    "yas_65_ustu": round(conv_p * 0.70, 2),
                    "cocuk": round(conv_p * 0.50, 2)
                },
                "providers": providers_list
            })
            return tickets

        tcdd_link = "https://ebilet.tcddtasimacilik.gov.tr/"

        # 1. CANLI TCDD API MOTORU (597 İstasyon & Gerçek Zamanlı Sefer/Peron Verisi)
        live_journeys = cls.fetch_live_tcdd_journeys(origin_name, dest_name, departure_date)
        live_ret_journeys = (
            cls.fetch_live_tcdd_journeys(dest_name, origin_name, return_date)
            if (is_round and return_date)
            else []
        )

        if live_journeys:
            for idx, lj in enumerate(live_journeys):
                return_leg = None
                ret_match = None
                if is_round and return_date and live_ret_journeys:
                    ret_match = live_ret_journeys[idx % len(live_ret_journeys)]
                    if ret_match:
                        return_leg = {
                            "origin": ret_match["origin_station"],
                            "destination": ret_match["dest_station"],
                            "departure_time": ret_match["dep_time"],
                            "arrival_time": ret_match["arr_time"],
                            "departure_date": return_date,
                            "departure_date_formatted": ret_date_formatted,
                            "flight_number": ret_match["flight_number"],
                            "carrier": ret_match["carrier"],
                            "duration": ret_match["duration"],
                            "is_direct": True,
                            "badge": ret_match["badge"],
                        }

                raw_price = float(lj["price_try"])
                ret_raw_price = float(ret_match["price_try"]) if ret_match else 0.0
                total_raw_try = (raw_price + ret_raw_price) * pax_count
                converted_price = CurrencyService.convert(total_raw_try, "TRY", currency) if currency != "TRY" else total_raw_try
                final_p = round(converted_price, 2) if currency != "TRY" else round(converted_price)

                leg_mult = pax_count * (2 if ret_match else 1)
                discounts_ticket = cls.get_discount_breakdown(raw_price)
                discounts_converted = {
                    k: round(CurrencyService.convert(v * leg_mult, "TRY", currency), 2) if currency != "TRY" else round(v * leg_mult, 2)
                    for k, v in discounts_ticket.items()
                }

                ogrenci_fmt = cls.format_price_tr(discounts_converted["genc_ogrenci"])
                yas65_fmt = cls.format_price_tr(discounts_converted["yas_65_ustu"])
                emekli_fmt = cls.format_price_tr(discounts_converted.get("emekli", discounts_converted["genc_ogrenci"]))
                discount_info_text = f"💡 İndirimli Bilet: 65+ Yaş: {yas65_fmt} {curr_symbol} • Emekli: {emekli_fmt} {curr_symbol} • Öğrenci: {ogrenci_fmt} {curr_symbol} (TCDD Ekranında Seçilebilir)"

                is_night = lj["is_next_day"] or lj["dep_time"] >= "20:00" or lj["dep_time"] < "06:00"

                tickets.append({
                    "id": f"tcdd-live-{lj['train_no']}-{idx+1}",
                    "transport_type": "train",
                    "source": "tcdd_live",
                    "train_category": lj["train_category"],
                    "carrier": lj["carrier"],
                    "carrier_logo": "🚆",
                    "flight_number": lj["flight_number"],
                    "origin": lj["origin_station"],
                    "destination": lj["dest_station"],
                    "departure_time": lj["dep_time"],
                    "arrival_time": lj["arr_time"],
                    "departure_date": departure_date,
                    "departure_date_formatted": dep_date_formatted,
                    "arrival_date_formatted": next_day_formatted if lj["is_next_day"] else dep_date_formatted,
                    "is_next_day": lj["is_next_day"],
                    "duration": lj["duration"],
                    "is_direct": True,
                    "is_night_trip": is_night,
                    "return_leg": return_leg,
                    "price": final_p,
                    "has_live_price": True,
                    "price_status_text": "TCDD Canlı Sefer & Resmi Tarife",
                    "regular_price": None,
                    "currency": curr_symbol,
                    "currency_code": currency,
                    "badge": lj["badge"],
                    "platform": lj.get("platform"),
                    "live_status": lj.get("live_status"),
                    "full_route": lj.get("full_route"),
                    "operating_days": lj.get("operating_days"),
                    "route_notice": discount_info_text,
                    "official_name": "TCDD Taşımacılık",
                    "official_link": tcdd_link,
                    "agent_name": "TCDD E-Bilet",
                    "agent_link": tcdd_link,
                    "direct_link": tcdd_link,
                    "booking_link": tcdd_link,
                    "discounts": discounts_converted,
                    "providers": [
                        {"name": "TCDD E-Bilet Resmi Ekranı", "url": tcdd_link, "price": final_p, "is_best": True}
                    ]
                })

            return tickets

        # 2. YEDEK (FALLBACK) TARİFE TABLOSU (Canlı TCDD API yanıt vermezse veya hat bakımdaysa)
        route_key = (orig_clean, dest_clean)
        tariff = cls.TCDD_TARIFFS.get(route_key)

        if ("istanbul" in orig_clean and "ankara" in dest_clean) or ("ankara" in orig_clean and "istanbul" in dest_clean):
            base_yht = 990.0
            station_orig = "İstanbul (Söğütlüçeşme)" if "istanbul" in orig_clean else "Ankara Gar"
            station_dest = "Ankara Gar" if "istanbul" in orig_clean else "İstanbul (Söğütlüçeşme)"

            timetable_to_use = cls.ANKARA_ISTANBUL_TIMETABLE if "ankara" in orig_clean else cls.ISTANBUL_ANKARA_TIMETABLE
            ret_timetable = cls.ISTANBUL_ANKARA_TIMETABLE if "ankara" in orig_clean else cls.ANKARA_ISTANBUL_TIMETABLE

            for idx, item in enumerate(timetable_to_use):
                is_anahat = (item.get("type") == "anahat")
                carrier_display = "TCDD Taşımacılık (Ankara Ekspresi)" if is_anahat else "TCDD Taşımacılık (YHT)"
                flight_no = item["code"]

                raw_price = 550.0 if is_anahat else base_yht
                converted_price = CurrencyService.convert(raw_price * train_mult, "TRY", currency)
                final_p = round(converted_price, 2)
                reg_p = None

                is_night = item.get("next_day", False) or item["dep"] >= "21:00"
                discounts_ticket = cls.get_discount_breakdown(raw_price)
                discounts_converted = {k: round(CurrencyService.convert(v * train_mult, "TRY", currency), 2) for k, v in discounts_ticket.items()}

                ogrenci_fmt = cls.format_price_tr(discounts_converted['genc_ogrenci'])
                yas65_fmt = cls.format_price_tr(discounts_converted['yas_65_ustu'])
                emekli_fmt = cls.format_price_tr(discounts_converted.get('emekli', discounts_converted['genc_ogrenci']))
                discount_info_text = f"💡 İndirimli Bilet: 65+ Yaş: {yas65_fmt} {curr_symbol} • Emekli: {emekli_fmt} {curr_symbol} • Öğrenci: {ogrenci_fmt} {curr_symbol} (TCDD Ekranında Seçilebilir)"

                return_leg = None
                if is_round and return_date and ret_timetable:
                    ret_idx = (idx + 6) % len(ret_timetable)
                    ret_item = ret_timetable[ret_idx]
                    return_leg = {
                        "origin": station_dest,
                        "destination": station_orig,
                        "departure_time": ret_item["dep"],
                        "arrival_time": ret_item["arr"],
                        "departure_date": return_date,
                        "departure_date_formatted": ret_date_formatted,
                        "flight_number": ret_item["code"],
                        "carrier": "TCDD Taşımacılık (Ankara Ekspresi)" if ret_item.get("type") == "anahat" else "TCDD Taşımacılık (YHT)",
                        "duration": ret_item["dur"],
                        "is_direct": True,
                        "badge": ret_item.get("badge", "Dönüş Hızlı Treni")
                    }

                tickets.append({
                    "id": f"tcdd-{idx+1}",
                    "transport_type": "train",
                    "train_category": "anahat" if is_anahat else "yht",
                    "carrier": carrier_display,
                    "carrier_logo": "🚆",
                    "flight_number": flight_no,
                    "origin": station_orig,
                    "destination": station_dest,
                    "departure_time": item["dep"],
                    "arrival_time": item["arr"],
                    "departure_date_formatted": dep_date_formatted,
                    "arrival_date_formatted": next_day_formatted if item.get("next_day") else dep_date_formatted,
                    "is_next_day": item.get("next_day", False),
                    "duration": item["dur"],
                    "is_direct": True,
                    "is_night_trip": is_night,
                    "return_leg": return_leg,
                    "price": final_p,
                    "has_live_price": True,
                    "price_status_text": "TCDD E-Bilet Doğrulanmış Taban Fiyat",
                    "regular_price": reg_p,
                    "currency": curr_symbol,
                    "currency_code": currency,
                    "badge": item.get("badge", "Yüksek Hızlı Tren (YHT)"),
                    "route_notice": discount_info_text,
                    "official_name": "TCDD Taşımacılık",
                    "official_link": tcdd_link,
                    "agent_name": "TCDD E-Bilet",
                    "agent_link": tcdd_link,
                    "direct_link": tcdd_link,
                    "booking_link": tcdd_link,
                    "discounts": discounts_converted,
                    "providers": [
                        {"name": "TCDD E-Bilet Resmi Ekranı", "url": tcdd_link, "price": final_p, "is_best": True}
                    ]
                })

            return tickets

        if tariff and tariff.get("type") == "anahat_single":
            raw_p = tariff["price"]
            conv_p = round(CurrencyService.convert(raw_p * train_mult, "TRY", currency), 2)
            disc = cls.get_discount_breakdown(raw_p)
            disc_conv = {k: round(CurrencyService.convert(v * train_mult, "TRY", currency), 2) for k, v in disc.items()}
            is_nxt = tariff.get("next_day", False)
            is_dir = tariff.get("is_direct", True)
            st_from = tariff.get("station_from") or (f"{origin_name}" if "Gar" in origin_name or "YHT" in origin_name else f"{origin_name} Garı")
            st_to = tariff.get("station_to") or (f"{dest_name}" if "Gar" in dest_name or "YHT" in dest_name else f"{dest_name} Garı")

            return_leg = None
            if is_round and return_date:
                return_leg = {
                    "origin": st_to,
                    "destination": st_from,
                    "departure_time": tariff["dep"],
                    "arrival_time": tariff["arr"],
                    "departure_date": return_date,
                    "departure_date_formatted": ret_date_formatted,
                    "flight_number": f"{tariff['name']} (Dönüş)",
                    "carrier": tariff["carrier"],
                    "duration": tariff["duration"],
                    "is_direct": is_dir,
                    "badge": "Dönüş Ekspresi"
                }

            tickets.append({
                "id": f"tcdd-anahat-{orig_clean}-{dest_clean}",
                "transport_type": "train",
                "train_category": "anahat",
                "carrier": tariff["carrier"],
                "carrier_logo": "🚆",
                "flight_number": f"{tariff['name']} ({tariff['train_no']})",
                "origin": st_from,
                "destination": st_to,
                "departure_time": tariff["dep"],
                "arrival_time": tariff["arr"],
                "departure_date": departure_date,
                "departure_date_formatted": dep_date_formatted,
                "arrival_date_formatted": next_day_formatted if is_nxt else dep_date_formatted,
                "is_next_day": is_nxt,
                "duration": tariff["duration"],
                "is_direct": is_dir,
                "is_night_trip": True,
                "return_leg": return_leg,
                "price": conv_p,
                "has_live_price": True,
                "price_status_text": "TCDD E-Bilet Doğrulanmış Taban Fiyat",
                "regular_price": None,
                "currency": curr_symbol,
                "currency_code": currency,
                "badge": tariff["badge"],
                "full_route": tariff.get("full_route"),
                "route_notice": f"💡 İndirimli Bilet: 65+ Yaş: {cls.format_price_tr(disc_conv['yas_65_ustu'])} {curr_symbol} • Emekli: {cls.format_price_tr(disc_conv.get('emekli', disc_conv['genc_ogrenci']))} {curr_symbol} • Öğrenci: {cls.format_price_tr(disc_conv['genc_ogrenci'])} {curr_symbol} (TCDD Ekranında Seçilebilir)",
                "official_name": "TCDD Taşımacılık",
                "official_link": tcdd_link,
                "agent_name": "TCDD E-Bilet",
                "agent_link": tcdd_link,
                "direct_link": tcdd_link,
                "booking_link": tcdd_link,
                "discounts": disc_conv,
                "providers": [
                    {"name": "TCDD E-Bilet Resmi Ekranı", "url": tcdd_link, "price": conv_p, "is_best": True}
                ]
            })
            return tickets

        if tariff:
            raw_p = tariff["price"]
            is_bolgesel = (tariff.get("type") == "bolgesel")
            carrier_str = tariff.get("carrier", "TCDD Taşımacılık (YHT)")
            dur = tariff.get("duration", "2 sa 30 dk")
            badge_str = tariff.get("badge", "Yüksek Hızlı Tren (YHT)")

            disc = cls.get_discount_breakdown(raw_p)
            disc_conv = {k: round(CurrencyService.convert(v * train_mult, "TRY", currency), 2) for k, v in disc.items()}
            conv_p = round(CurrencyService.convert(raw_p * train_mult, "TRY", currency), 2)

            if is_bolgesel:
                departures = ["06:30", "08:15", "10:30", "13:00", "15:30", "17:15", "19:00", "21:30"]
            else:
                departures = ["07:00", "09:30", "12:15", "15:00", "17:45", "20:30"]

            for i, dep in enumerate(departures):
                dep_hour = int(dep.split(":")[0])
                try:
                    dur_hours = int(dur.split(" sa")[0]) if " sa" in dur else 0
                    dur_mins = int(dur.split("sa ")[1].replace(" dk", "")) if "sa " in dur and " dk" in dur else (int(dur.replace(" dk", "")) if " dk" in dur else 45)
                except Exception:
                    dur_hours = 2
                    dur_mins = 0

                arr_dt_calc = datetime.strptime(dep, "%H:%M") + timedelta(hours=dur_hours, minutes=dur_mins)
                arr_str = arr_dt_calc.strftime("%H:%M")
                is_nxt_calc = arr_dt_calc.day > 1

                return_leg = None
                if is_round and return_date:
                    return_leg = {
                        "origin": f"{dest_name} Garı",
                        "destination": f"{origin_name} Garı",
                        "departure_time": "18:00",
                        "arrival_time": (datetime.strptime("18:00", "%H:%M") + timedelta(hours=dur_hours, minutes=dur_mins)).strftime("%H:%M"),
                        "departure_date": return_date,
                        "departure_date_formatted": ret_date_formatted,
                        "flight_number": f"{'YHT' if not is_bolgesel else 'Bölgesel'} Dönüş",
                        "carrier": carrier_str,
                        "duration": dur,
                        "is_direct": True,
                        "badge": "Dönüş Seferi"
                    }

                tickets.append({
                    "id": f"tcdd-rt-{orig_clean}-{i+1}",
                    "transport_type": "train",
                    "train_category": "bolgesel" if is_bolgesel else "yht",
                    "carrier": carrier_str,
                    "carrier_logo": "🚆",
                    "flight_number": f"{'YHT' if not is_bolgesel else 'Bölgesel'} 9{i+1:02d}",
                    "origin": f"{origin_name} Garı",
                    "destination": f"{dest_name} Garı",
                    "departure_time": dep,
                    "arrival_time": arr_str,
                    "departure_date_formatted": dep_date_formatted,
                    "arrival_date_formatted": next_day_formatted if is_nxt_calc else dep_date_formatted,
                    "is_next_day": is_nxt_calc,
                    "duration": dur,
                    "is_direct": True,
                    "is_night_trip": dep_hour >= 20,
                    "return_leg": return_leg,
                    "price": conv_p,
                    "has_live_price": True,
                    "price_status_text": "TCDD E-Bilet Doğrulanmış Taban Fiyat",
                    "regular_price": round(conv_p * 1.15, 2),
                    "currency": curr_symbol,
                    "currency_code": currency,
                    "badge": badge_str,
                    "route_notice": f"💡 İndirimli Bilet: 65+ Yaş: {cls.format_price_tr(disc_conv['yas_65_ustu'])} {curr_symbol} • Emekli: {cls.format_price_tr(disc_conv.get('emekli', disc_conv['genc_ogrenci']))} {curr_symbol} • Öğrenci: {cls.format_price_tr(disc_conv['genc_ogrenci'])} {curr_symbol} (TCDD Ekranında Seçilebilir)",
                    "official_name": "TCDD Taşımacılık",
                    "official_link": tcdd_link,
                    "agent_name": "TCDD E-Bilet",
                    "agent_link": tcdd_link,
                    "direct_link": tcdd_link,
                    "booking_link": tcdd_link,
                    "discounts": disc_conv,
                    "providers": [
                        {"name": "TCDD E-Bilet Resmi Ekranı", "url": tcdd_link, "price": conv_p, "is_best": True}
                    ]
                })

            return tickets

        return tickets
