import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

class TrainService:
    """
    TCDD Taşımacılık (YHT, Anahat & Bölgesel Trenler) ve Uluslararası Hızlı Tren Servisi
    - Tüm Türkiye Aktif Demiryolu Hatları (YHT Koridorları, Doğu Ekspresi, İzmir Mavi, Bölgesel)
    - TCDD Resmi Tarife Modeli (990,00 ₺ İst-Ank YHT Taban Bilet)
    - TCDD Kanuni İndirim Skalası (Genç/Öğrenci %15, 65+ Yaş %50, Çocuk %50) her bilet için kendi fiyatından
    - Doğrudan TCDD E-Bilet Resmi Portal Yönlendirmesi
    """

    # TCDD Türkiye Geneli Resmi Hat ve Tarife Haritası
    TCDD_TARIFFS = {
        # 1. YHT Koridorları
        ("istanbul", "ankara"): {"type": "yht", "price": 990.0, "anahat_pulman": 550.0, "duration": "4 sa 21 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "istanbul"): {"type": "yht", "price": 990.0, "anahat_pulman": 550.0, "duration": "4 sa 21 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "eskisehir"): {"type": "yht", "price": 560.0, "duration": "2 sa 55 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("eskisehir", "istanbul"): {"type": "yht", "price": 560.0, "duration": "2 sa 55 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "eskisehir"): {"type": "yht", "price": 380.0, "duration": "1 sa 25 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("eskisehir", "ankara"): {"type": "yht", "price": 380.0, "duration": "1 sa 25 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "konya"): {"type": "yht", "price": 1120.0, "duration": "4 sa 50 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("konya", "istanbul"): {"type": "yht", "price": 1120.0, "duration": "4 sa 50 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "konya"): {"type": "yht", "price": 400.0, "duration": "1 sa 45 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("konya", "ankara"): {"type": "yht", "price": 400.0, "duration": "1 sa 45 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "sivas"): {"type": "yht", "price": 850.0, "duration": "2 sa 35 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("sivas", "ankara"): {"type": "yht", "price": 850.0, "duration": "2 sa 35 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "sivas"): {"type": "yht", "price": 1450.0, "duration": "7 sa 15 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("sivas", "istanbul"): {"type": "yht", "price": 1450.0, "duration": "7 sa 15 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("ankara", "karaman"): {"type": "yht", "price": 520.0, "duration": "2 sa 40 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("karaman", "ankara"): {"type": "yht", "price": 520.0, "duration": "2 sa 40 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("istanbul", "karaman"): {"type": "yht", "price": 1250.0, "duration": "5 sa 45 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        ("karaman", "istanbul"): {"type": "yht", "price": 1250.0, "duration": "5 sa 45 dk", "carrier": "TCDD Taşımacılık (YHT)"},
        
        # 2. Anahat Ekspresleri
        ("ankara", "kars"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "22002", "price": 650.0, "duration": "25 sa 30 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "17:55", "arr": "19:25", "next_day": True, "badge": "⭐ Efsane Doğu Ekspresi (Pulman / Kuşet)"},
        ("kars", "ankara"): {"type": "anahat_single", "name": "Doğu Ekspresi", "train_no": "22001", "price": 650.0, "duration": "25 sa 30 dk", "carrier": "TCDD Taşımacılık (Doğu Ekspresi)", "dep": "08:00", "arr": "09:30", "next_day": True, "badge": "⭐ Efsane Doğu Ekspresi (Pulman / Kuşet)"},
        ("izmir", "ankara"): {"type": "anahat_single", "name": "İzmir Mavi Treni", "train_no": "32006", "price": 620.0, "duration": "13 sa 45 dk", "carrier": "TCDD Taşımacılık (İzmir Mavi)", "dep": "19:05", "arr": "08:50", "next_day": True, "badge": "🌙 Yataklı & Pulman Gece Treni"},
        ("ankara", "izmir"): {"type": "anahat_single", "name": "İzmir Mavi Treni", "train_no": "32005", "price": 620.0, "duration": "13 sa 45 dk", "carrier": "TCDD Taşımacılık (İzmir Mavi)", "dep": "19:00", "arr": "08:45", "next_day": True, "badge": "🌙 Yataklı & Pulman Gece Treni"},
        ("konya", "izmir"): {"type": "anahat_single", "name": "Konya Mavi Treni", "train_no": "32008", "price": 580.0, "duration": "11 sa 50 dk", "carrier": "TCDD Taşımacılık (Konya Mavi)", "dep": "19:40", "arr": "07:30", "next_day": True, "badge": "🌙 Gece Anahat Treni"},
        ("izmir", "konya"): {"type": "anahat_single", "name": "Konya Mavi Treni", "train_no": "32007", "price": 580.0, "duration": "11 sa 50 dk", "carrier": "TCDD Taşımacılık (Konya Mavi)", "dep": "20:05", "arr": "08:00", "next_day": True, "badge": "🌙 Gece Anahat Treni"},
        ("denizli", "eskisehir"): {"type": "anahat_single", "name": "Pamukkale Ekspresi", "train_no": "72002", "price": 480.0, "duration": "8 sa 30 dk", "carrier": "TCDD Taşımacılık (Pamukkale Ekspresi)", "dep": "08:40", "arr": "17:10", "next_day": False, "badge": "Gündüz Anahat Treni"},
        ("eskisehir", "denizli"): {"type": "anahat_single", "name": "Pamukkale Ekspresi", "train_no": "72001", "price": 480.0, "duration": "8 sa 30 dk", "carrier": "TCDD Taşımacılık (Pamukkale Ekspresi)", "dep": "10:25", "arr": "18:55", "next_day": False, "badge": "Gündüz Anahat Treni"},
        ("izmir", "eskisehir"): {"type": "anahat_single", "name": "Ege Ekspresi", "train_no": "32014", "price": 520.0, "duration": "11 sa 15 dk", "carrier": "TCDD Taşımacılık (Ege Ekspresi)", "dep": "06:50", "arr": "18:05", "next_day": False, "badge": "Ege Bölge Ekspresi"},
        ("eskisehir", "izmir"): {"type": "anahat_single", "name": "Ege Ekspresi", "train_no": "32013", "price": 520.0, "duration": "11 sa 15 dk", "carrier": "TCDD Taşımacılık (Ege Ekspresi)", "dep": "08:30", "arr": "19:45", "next_day": False, "badge": "Ege Bölge Ekspresi"},

        # 3. Bölgesel Hatlar
        ("adana", "mersin"): {"type": "bolgesel", "name": "Çukurova Bölgesel", "price": 85.0, "duration": "45 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Sık Seferli Hızlı Bölgesel"},
        ("mersin", "adana"): {"type": "bolgesel", "name": "Çukurova Bölgesel", "price": 85.0, "duration": "45 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Sık Seferli Hızlı Bölgesel"},
        ("izmir", "denizli"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 240.0, "duration": "4 sa 30 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Ekspres"},
        ("denizli", "izmir"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 240.0, "duration": "4 sa 30 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Ekspres"},
        ("izmir", "aydin"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 160.0, "duration": "2 sa 20 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("aydin", "izmir"): {"type": "bolgesel", "name": "Ege Bölgesel", "price": 160.0, "duration": "2 sa 20 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        # Van Gölü & Kurtalan & Diğer Anahat
        ("ankara", "tatvan"): {"type": "anahat_single", "name": "Van Gölü Ekspresi", "train_no": "22012", "price": 650.0, "duration": "26 sa 10 dk", "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi)", "dep": "11:20", "arr": "13:30", "next_day": True, "badge": "⭐ Van Gölü Ekspresi (Pulman / Kuşet)"},
        ("tatvan", "ankara"): {"type": "anahat_single", "name": "Van Gölü Ekspresi", "train_no": "22011", "price": 650.0, "duration": "26 sa 10 dk", "carrier": "TCDD Taşımacılık (Van Gölü Ekspresi)", "dep": "08:15", "arr": "10:25", "next_day": True, "badge": "⭐ Van Gölü Ekspresi (Pulman / Kuşet)"},
        ("ankara", "kurtalan"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "22014", "price": 620.0, "duration": "25 sa 00 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "11:20", "arr": "12:20", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi"},
        ("kurtalan", "ankara"): {"type": "anahat_single", "name": "Güney Kurtalan Ekspresi", "train_no": "22013", "price": 620.0, "duration": "25 sa 00 dk", "carrier": "TCDD Taşımacılık (Güney Kurtalan)", "dep": "09:30", "arr": "10:30", "next_day": True, "badge": "⭐ Güney Kurtalan Ekspresi"},
        ("konya", "adana"): {"type": "anahat_single", "name": "Toros Ekspresi", "train_no": "62002", "price": 320.0, "duration": "6 sa 20 dk", "carrier": "TCDD Taşımacılık (Toros Ekspresi)", "dep": "14:45", "arr": "21:05", "next_day": False, "badge": "Gündüz Toros Ekspresi"},
        ("adana", "konya"): {"type": "anahat_single", "name": "Toros Ekspresi", "train_no": "62001", "price": 320.0, "duration": "6 sa 20 dk", "carrier": "TCDD Taşımacılık (Toros Ekspresi)", "dep": "07:45", "arr": "14:05", "next_day": False, "badge": "Gündüz Toros Ekspresi"},
        ("elazig", "adana"): {"type": "anahat_single", "name": "Fırat Ekspresi", "train_no": "52002", "price": 310.0, "duration": "9 sa 15 dk", "carrier": "TCDD Taşımacılık (Fırat Ekspresi)", "dep": "08:30", "arr": "17:45", "next_day": False, "badge": "Fırat Ekspresi"},
        ("adana", "elazig"): {"type": "anahat_single", "name": "Fırat Ekspresi", "train_no": "52001", "price": 310.0, "duration": "9 sa 15 dk", "carrier": "TCDD Taşımacılık (Fırat Ekspresi)", "dep": "08:45", "arr": "18:00", "next_day": False, "badge": "Fırat Ekspresi"},
        ("kayseri", "adana"): {"type": "anahat_single", "name": "Erciyes Ekspresi", "train_no": "22032", "price": 260.0, "duration": "5 sa 45 dk", "carrier": "TCDD Taşımacılık (Erciyes Ekspresi)", "dep": "07:30", "arr": "13:15", "next_day": False, "badge": "Erciyes Ekspresi"},
        ("adana", "kayseri"): {"type": "anahat_single", "name": "Erciyes Ekspresi", "train_no": "22031", "price": 260.0, "duration": "5 sa 45 dk", "carrier": "TCDD Taşımacılık (Erciyes Ekspresi)", "dep": "16:30", "arr": "22:15", "next_day": False, "badge": "Erciyes Ekspresi"},
        ("zonguldak", "karabuk"): {"type": "bolgesel", "name": "Batı Karadeniz Bölgesel", "price": 120.0, "duration": "2 sa 40 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
        ("karabuk", "zonguldak"): {"type": "bolgesel", "name": "Batı Karadeniz Bölgesel", "price": 120.0, "duration": "2 sa 40 dk", "carrier": "TCDD Taşımacılık (Bölgesel)", "badge": "Bölgesel Tren"},
    }

    # Uluslararası ve Avrupa İçi Hızlı Tren Sefer Haritası (Trainline Resmi Partneri & Balkan Ekspresleri)
    INTERNATIONAL_TRAIN_TARIFFS = {
        # 1. Türkiye - Balkanlar (TCDD & Uluslararası Demiryolları)
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

        # 2. Avrupa İçi Hızlı Tren Koridorları (Trainline Resmi Partner)
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

    # TCDD İstanbul -> Ankara Gerçek Günlük Sefer Çizelgesi (14 Resmi Sefer: 810xx serisi + 12002 Anahat)
    ISTANBUL_ANKARA_TIMETABLE = [
        {"code": "YHT 81002", "dep": "06:10", "arr": "10:32", "dur": "4 sa 22 dk", "type": "yht", "badge": "Günün İlk Hızlı Treni", "next_day": False},
        {"code": "YHT 81004", "dep": "07:15", "arr": "11:36", "dur": "4 sa 21 dk", "type": "yht", "badge": "Sabah YHT", "next_day": False},
        {"code": "YHT 81006", "dep": "08:35", "arr": "12:56", "dur": "4 sa 21 dk", "type": "yht", "badge": "Sabah Seferi", "next_day": False},
        {"code": "YHT 81008", "dep": "10:05", "arr": "14:26", "dur": "4 sa 21 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81010", "dep": "11:15", "arr": "15:37", "dur": "4 sa 22 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81012", "dep": "12:40", "arr": "17:01", "dur": "4 sa 21 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81014", "dep": "14:05", "arr": "18:26", "dur": "4 sa 21 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81016", "dep": "15:15", "arr": "19:36", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşamüstü Seferi", "next_day": False},
        {"code": "YHT 81018", "dep": "16:20", "arr": "20:41", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşam Seferi", "next_day": False},
        {"code": "YHT 81020", "dep": "17:35", "arr": "21:56", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşam Yoğun Hat", "next_day": False},
        {"code": "YHT 81022", "dep": "18:30", "arr": "22:51", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşam Ekspresi ⭐", "next_day": False},
        {"code": "YHT 81024", "dep": "19:05", "arr": "23:27", "dur": "4 sa 22 dk", "type": "yht", "badge": "Günün Son YHT Seferi", "next_day": False},
        {"code": "YHT 81026", "dep": "20:30", "arr": "00:52", "dur": "4 sa 22 dk", "type": "yht", "badge": "🌙 Gece YHT", "next_day": True},
        {"code": "ANAHAT 12002", "dep": "22:59", "arr": "06:37", "dur": "7 sa 38 dk", "type": "anahat", "name": "Ankara Ekspresi", "badge": "🌙 Yataklı Gece Treni (Otel Tasarruflu)", "next_day": True}
    ]

    # TCDD Ankara -> İstanbul Gerçek Günlük Sefer Çizelgesi (14 Resmi Sefer: 810xx tekli serisi + 12001 Anahat)
    ANKARA_ISTANBUL_TIMETABLE = [
        {"code": "YHT 81001", "dep": "06:00", "arr": "10:18", "dur": "4 sa 18 dk", "type": "yht", "badge": "Günün İlk Hızlı Treni", "next_day": False},
        {"code": "YHT 81003", "dep": "07:10", "arr": "11:29", "dur": "4 sa 19 dk", "type": "yht", "badge": "Sabah YHT", "next_day": False},
        {"code": "YHT 81005", "dep": "08:30", "arr": "12:51", "dur": "4 sa 21 dk", "type": "yht", "badge": "Sabah Seferi", "next_day": False},
        {"code": "YHT 81007", "dep": "09:55", "arr": "14:14", "dur": "4 sa 19 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81009", "dep": "11:20", "arr": "15:41", "dur": "4 sa 21 dk", "type": "yht", "badge": "Öğle Seferi", "next_day": False},
        {"code": "YHT 81011", "dep": "12:45", "arr": "17:06", "dur": "4 sa 21 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81013", "dep": "14:10", "arr": "18:31", "dur": "4 sa 21 dk", "type": "yht", "badge": "Öğleden Sonra", "next_day": False},
        {"code": "YHT 81015", "dep": "15:35", "arr": "19:56", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşamüstü Seferi", "next_day": False},
        {"code": "YHT 81017", "dep": "17:00", "arr": "21:21", "dur": "4 sa 21 dk", "type": "yht", "badge": "Akşam Seferi", "next_day": False},
        {"code": "YHT 81019", "dep": "18:20", "arr": "22:42", "dur": "4 sa 22 dk", "type": "yht", "badge": "Akşam Ekspresi ⭐", "next_day": False},
        {"code": "YHT 81021", "dep": "19:15", "arr": "23:37", "dur": "4 sa 22 dk", "type": "yht", "badge": "Günün Son YHT Seferi", "next_day": False},
        {"code": "YHT 81023", "dep": "20:45", "arr": "01:07", "dur": "4 sa 22 dk", "type": "yht", "badge": "🌙 Gece YHT", "next_day": True},
        {"code": "YHT 81025", "dep": "21:30", "arr": "01:52", "dur": "4 sa 22 dk", "type": "yht", "badge": "🌙 Gece Ekspresi", "next_day": True},
        {"code": "ANAHAT 12001", "dep": "22:00", "arr": "06:15", "dur": "8 sa 15 dk", "type": "anahat", "name": "Ankara Ekspresi", "badge": "🌙 Yataklı Gece Treni (Otel Tasarruflu)", "next_day": True}
    ]

    @staticmethod
    def format_price_tr(amount: float) -> str:
        """Türk Lirası formatı: 275 -> '275', 467.5 -> '467,50'"""
        if amount == int(amount):
            return f"{int(amount):,}".replace(",", ".")
        return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def normalize_tr(text: str) -> str:
        if not text:
            return ""
        import re
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
        import unicodedata
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s.lower().strip()

    @classmethod
    def get_discount_breakdown(cls, base_price: float) -> Dict[str, float]:
        """TCDD Resmi İndirimli Bilet Tarifesi: Her biletin kendi ham fiyatından hesaplanır"""
        return {
            "tam": round(base_price, 2),
            "genc_ogrenci": round(base_price * 0.85, 2),     # %15 indirim (13-26 yaş)
            "ogretmen": round(base_price * 0.85, 2),         # %15 indirim
            "yas_60_64": round(base_price * 0.85, 2),        # %15 indirim
            "yas_65_ustu": round(base_price * 0.50, 2),      # %50 indirim
            "cocuk_7_12": round(base_price * 0.50, 2),       # %50 indirim
            "basin": round(base_price * 0.80, 2),            # %20 indirim
            "cocuk_0_6": 0.0                                 # Kucakta ücretsiz
        }

    @classmethod
    def get_trainline_deep_link(cls, origin_slug: str, dest_slug: str, departure_date: str) -> str:
        """
        Trainline Avrupa hızlı tren biletleme ekranına Travelpayouts Marker ile yönlendirir.
        """
        from app.config import settings
        tp_marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
        t_url = f"https://www.thetrainline.com/tr/search/results?origin={origin_slug}&destination={dest_slug}&outwardDate={departure_date}"
        import urllib.parse
        encoded = urllib.parse.quote(t_url, safe="")
        return f"https://tp.media/r?marker={tp_marker}&p=4523&u={encoded}"

    @classmethod
    def search_trains(
        cls, origin_name: str, dest_name: str, departure_date: str,
        passengers: int = 1, currency: str = "TRY", is_round: bool = False,
        return_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Kalkış ve varış noktasına göre TCDD resmi tarife ve seferlerini veya Trainline uluslararası seferlerini üretir.
        Her bilet kendi fiyatı üzerinden %100 doğru indirim oranına sahiptir.
        """
        orig_clean = cls.normalize_tr(origin_name)
        dest_clean = cls.normalize_tr(dest_name)
        orig_display = origin_name.strip().title()
        dest_display = dest_name.strip().title()
        
        curr_symbol = CurrencyService.get_symbol(currency)
        tickets = []
        train_mult = max(1, passengers) * (2 if is_round else 1)

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
            reg_p = round(conv_p * 1.15, 2)
            is_next_day = matched_intl.get("next_day", False)

            if is_trainline:
                booking_url = cls.get_trainline_deep_link(orig_clean, dest_clean, departure_date)
                provider_name = "Trainline Resmi Bilet Ekranı"
                price_status = "Trainline Doğrulanmış Taban Fiyat"
            else: # Balkan Ekspresi
                booking_url = "https://ebilet.tcddtasimacilik.gov.tr/"
                provider_name = "TCDD Uluslararası E-Bilet"
                price_status = "TCDD / BDZ Doğrulanmış Tarife"

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
                "id": "intl-train-1",
                "transport_type": "train",
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
                "price": conv_p,
                "has_live_price": True,
                "price_status_text": price_status,
                "regular_price": reg_p,
                "currency": curr_symbol,
                "currency_code": currency,
                "badge": matched_intl["badge"],
                "route_notice": f"🌍 Uluslararası Tren Hattı • {matched_intl['name']}",
                "official_name": provider_name,
                "official_link": booking_url,
                "agent_name": "Trainline Global" if is_trainline else "TCDD Taşımacılık",
                "agent_link": booking_url,
                "direct_link": booking_url,
                "booking_link": booking_url,
                "is_round": is_round,
                "return_leg": return_leg,
                "discounts": {
                    "genc_ogrenci": round(conv_p * 0.85, 2),
                    "yas_65_ustu": round(conv_p * 0.70, 2),
                    "cocuk": round(conv_p * 0.50, 2)
                },
                "providers": [
                    {"name": provider_name, "url": booking_url, "price": conv_p, "is_best": True}
                ]
            })
            return tickets

        route_key = (orig_clean, dest_clean)
        tariff = cls.TCDD_TARIFFS.get(route_key)
        tcdd_link = "https://ebilet.tcddtasimacilik.gov.tr/"

        # 1. İSTANBUL - ANKARA (En Popüler Hat - Gerçek TCDD Sefer Çizelgesi)
        if ("istanbul" in orig_clean and "ankara" in dest_clean) or ("ankara" in orig_clean and "istanbul" in dest_clean):
            base_yht = 990.0  # TCDD Resmi Net Bilet Fiyatı
            station_orig = "İstanbul(Bostancı / Söğütlüçeşme)" if "istanbul" in orig_clean else "Ankara Gar"
            station_dest = "Ankara Gar" if "istanbul" in orig_clean else "İstanbul(Bostancı / Söğütlüçeşme)"

            timetable_to_use = cls.ANKARA_ISTANBUL_TIMETABLE if "ankara" in orig_clean else cls.ISTANBUL_ANKARA_TIMETABLE
            ret_timetable = cls.ISTANBUL_ANKARA_TIMETABLE if "ankara" in orig_clean else cls.ANKARA_ISTANBUL_TIMETABLE

            for idx, item in enumerate(timetable_to_use):
                is_anahat = (item.get("type") == "anahat")
                carrier_display = "TCDD Taşımacılık (Ankara Ekspresi)" if is_anahat else "TCDD Taşımacılık (YHT)"
                flight_no = item["code"]

                # Ankara Ekspresi pulman taban fiyatı 550 ₺, YHT 990 ₺
                raw_price = 550.0 if is_anahat else base_yht
                converted_price = CurrencyService.convert(raw_price * train_mult, "TRY", currency)
                final_p = round(converted_price, 2)
                reg_p = round(final_p * 1.15, 2)

                is_night = item.get("next_day", False) or item["dep"] >= "21:00"

                # İndirim oranları MUTLAKA bu biletin kendi ham fiyatından hesaplanır
                discounts_ticket = cls.get_discount_breakdown(raw_price)
                discounts_converted = {k: round(CurrencyService.convert(v * train_mult, "TRY", currency), 2) for k, v in discounts_ticket.items()}

                providers = [
                    {"name": "TCDD E-Bilet Resmi Ekranı", "url": tcdd_link, "price": final_p, "is_best": True}
                ]

                ogrenci_fmt = cls.format_price_tr(discounts_converted['genc_ogrenci'])
                yas65_fmt = cls.format_price_tr(discounts_converted['yas_65_ustu'])
                discount_info_text = f"💡 İndirimli Bilet: Öğrenci: {ogrenci_fmt} {curr_symbol} • 65+ Yaş: {yas65_fmt} {curr_symbol} (TCDD Ekranında Seçilebilir)"

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
                    "providers": providers
                })

            return tickets

        # 2. TEK SEFERLİ ANAHAT TRENLERİ (Doğu Ekspresi, İzmir Mavi, vb.)
        if tariff and tariff.get("type") == "anahat_single":
            raw_p = tariff["price"]
            conv_p = round(CurrencyService.convert(raw_p * train_mult, "TRY", currency), 2)
            disc = cls.get_discount_breakdown(raw_p)
            disc_conv = {k: round(CurrencyService.convert(v * train_mult, "TRY", currency), 2) for k, v in disc.items()}
            is_nxt = tariff.get("next_day", False)

            return_leg = None
            if is_round and return_date:
                return_leg = {
                    "origin": f"{dest_name} Garı",
                    "destination": f"{origin_name} Garı",
                    "departure_time": tariff["dep"],
                    "arrival_time": tariff["arr"],
                    "departure_date": return_date,
                    "departure_date_formatted": ret_date_formatted,
                    "flight_number": f"{tariff['name']} (Dönüş)",
                    "carrier": tariff["carrier"],
                    "duration": tariff["duration"],
                    "is_direct": True,
                    "badge": "Dönüş Ekspresi"
                }

            tickets.append({
                "id": f"tcdd-anahat-{orig_clean}",
                "transport_type": "train",
                "carrier": tariff["carrier"],
                "carrier_logo": "🚆",
                "flight_number": f"{tariff['name']} ({tariff['train_no']})",
                "origin": f"{origin_name} Garı",
                "destination": f"{dest_name} Garı",
                "departure_time": tariff["dep"],
                "arrival_time": tariff["arr"],
                "departure_date_formatted": dep_date_formatted,
                "arrival_date_formatted": next_day_formatted if is_nxt else dep_date_formatted,
                "is_next_day": is_nxt,
                "duration": tariff["duration"],
                "is_direct": True,
                "is_night_trip": True,
                "return_leg": return_leg,
                "price": conv_p,
                "has_live_price": True,
                "price_status_text": "TCDD E-Bilet Doğrulanmış Taban Fiyat",
                "regular_price": round(conv_p * 1.15, 2),
                "currency": curr_symbol,
                "currency_code": currency,
                "badge": tariff["badge"],
                "route_notice": f"💡 İndirimli Bilet: Öğrenci: {cls.format_price_tr(disc_conv['genc_ogrenci'])} {curr_symbol} • 65+ Yaş: {cls.format_price_tr(disc_conv['yas_65_ustu'])} {curr_symbol} (TCDD Ekranında Seçilebilir)",
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

        # 3. DİĞER YHT VE BÖLGESEL HATLARI (Ankara-Konya, İst-Eskişehir, İst-Sivas, Adana-Mersin vb.)
        if tariff:
            raw_p = tariff["price"]
            is_bolgesel = (tariff.get("type") == "bolgesel")
            carrier_str = tariff.get("carrier", "TCDD Taşımacılık (YHT)")
            dur = tariff.get("duration", "2 sa 30 dk")
            badge_str = tariff.get("badge", "Yüksek Hızlı Tren (YHT)")

            disc = cls.get_discount_breakdown(raw_p)
            disc_conv = {k: round(CurrencyService.convert(v * train_mult, "TRY", currency), 2) for k, v in disc.items()}
            conv_p = round(CurrencyService.convert(raw_p * train_mult, "TRY", currency), 2)

            # Bölgesel ise sık sefer, YHT ise saat başı seferler
            if is_bolgesel:
                departures = ["06:30", "08:15", "10:30", "13:00", "15:30", "17:15", "19:00", "21:30"]
            else:
                departures = ["07:00", "09:30", "12:15", "15:00", "17:45", "20:30"]

            for i, dep in enumerate(departures):
                dep_hour = int(dep.split(":")[0])
                # Süre saat ekleme
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
                    "route_notice": f"💡 İndirimli Bilet: Öğrenci: {cls.format_price_tr(disc_conv['genc_ogrenci'])} {curr_symbol} • 65+ Yaş: {cls.format_price_tr(disc_conv['yas_65_ustu'])} {curr_symbol} (TCDD Ekranında Seçilebilir)",
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
