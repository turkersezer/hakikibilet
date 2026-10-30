"""
Türkiye Şehirleri, Havalimanı (IATA) Kodları, TCDD Gar Kodları, En Yakın Hub Bilgileri ve Koordinatları
"""
import re

TURKEY_CITIES = [
    {"name": "İstanbul Sabiha Gökçen", "slug": "istanbul-sabiha-gokcen", "iata": "SAW", "train_station": "Pendik YHT (Havalimanı Bağlantılı)", "has_airport": True, "has_train": True, "lat": 40.8986, "lng": 29.3092},
    {"name": "İstanbul Havalimanı", "slug": "istanbul-havalimani", "iata": "IST", "train_station": "İstanbul Havalimanı YHT / Gayrettepe Metro", "has_airport": True, "has_train": True, "lat": 41.2753, "lng": 28.7519},
    {"name": "İstanbul", "slug": "istanbul", "iata": "IST", "alt_iata": "SAW", "train_station": "İstanbul (Söğütlüçeşme/Halkalı)", "has_airport": True, "has_train": True, "lat": 41.0082, "lng": 28.9784},
    {"name": "Ankara", "slug": "ankara", "iata": "ESB", "train_station": "Ankara Gar (YHT)", "has_airport": True, "has_train": True, "lat": 39.9334, "lng": 32.8597},
    {"name": "İzmir", "slug": "izmir", "iata": "ADB", "train_station": "İzmir (Basmane)", "has_airport": True, "has_train": True, "lat": 38.4237, "lng": 27.1428},
    {"name": "Antalya", "slug": "antalya", "iata": "AYT", "train_station": None, "has_airport": True, "has_train": False, "lat": 36.8969, "lng": 30.7133},
    {"name": "Adana", "slug": "adana", "iata": "COV", "alt_iata": "ADA", "train_station": "Adana Gar", "has_airport": True, "has_train": True, "lat": 37.0000, "lng": 35.3213},
    {"name": "Trabzon", "slug": "trabzon", "iata": "TZX", "train_station": None, "has_airport": True, "has_train": False, "lat": 41.0027, "lng": 39.7168},
    {"name": "Bursa", "slug": "bursa", "iata": "YEI", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.1885, "lng": 29.0610},
    {"name": "Eskişehir", "slug": "eskisehir", "iata": "AOE", "train_station": "Eskişehir Gar (YHT)", "has_airport": True, "has_train": True, "lat": 39.7767, "lng": 30.5206},
    {"name": "Konya", "slug": "konya", "iata": "KYA", "train_station": "Konya Gar (YHT)", "has_airport": True, "has_train": True, "lat": 37.8746, "lng": 32.4932},
    {"name": "Gaziantep", "slug": "gaziantep", "iata": "GZT", "train_station": "Gaziantep Gar", "has_airport": True, "has_train": True, "lat": 37.0662, "lng": 37.3833},
    {"name": "Diyarbakır", "slug": "diyarbakir", "iata": "DIY", "train_station": "Diyarbakır Gar", "has_airport": True, "has_train": True, "lat": 37.9144, "lng": 40.2306},
    {"name": "Samsun", "slug": "samsun", "iata": "SZF", "train_station": "Samsun Gar", "has_airport": True, "has_train": True, "lat": 41.2867, "lng": 36.3300},
    {"name": "Kayseri", "slug": "kayseri", "iata": "ASR", "train_station": "Kayseri Gar", "has_airport": True, "has_train": True, "lat": 38.7312, "lng": 35.4787},
    {"name": "Bodrum (Muğla)", "slug": "bodrum", "iata": "BJV", "train_station": None, "has_airport": True, "has_train": False, "is_ferry": True, "port_code": "BXN", "lat": 37.0344, "lng": 27.4305},
    {"name": "Dalaman (Muğla)", "slug": "dalaman", "iata": "DLM", "train_station": None, "has_airport": True, "has_train": False, "lat": 36.7656, "lng": 28.8044},
    {"name": "Van", "slug": "van", "iata": "VAN", "train_station": "Van İskele", "has_airport": True, "has_train": True, "lat": 38.4891, "lng": 43.4089},
    {"name": "Erzurum", "slug": "erzurum", "iata": "ERZ", "train_station": "Erzurum Gar", "has_airport": True, "has_train": True, "lat": 39.9043, "lng": 41.2679},
    {"name": "Sivas", "slug": "sivas", "iata": "VAS", "train_station": "Sivas Gar (YHT)", "has_airport": True, "has_train": True, "lat": 39.7505, "lng": 37.0150},
    {"name": "Kars", "slug": "kars", "iata": "KSY", "train_station": "Kars Gar (Doğu Ekspresi)", "has_airport": True, "has_train": True, "lat": 40.6013, "lng": 43.0975},
    {"name": "Mersin", "slug": "mersin", "iata": "COV", "train_station": "Mersin Gar", "has_airport": True, "has_train": True, "lat": 36.8121, "lng": 34.6415},
    {"name": "Denizli", "slug": "denizli", "iata": "DNZ", "train_station": "Denizli Gar", "has_airport": True, "has_train": True, "lat": 37.7765, "lng": 29.0864},
    {"name": "Hatay", "slug": "hatay", "iata": "HTY", "train_station": None, "has_airport": True, "has_train": False, "lat": 36.2023, "lng": 36.1613},
    {"name": "Şanlıurfa", "slug": "sanliurfa", "iata": "GNY", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.1674, "lng": 38.7955},
    {"name": "Malatya", "slug": "malatya", "iata": "MLX", "train_station": "Malatya Gar", "has_airport": True, "has_train": True, "lat": 38.3552, "lng": 38.3095},
    {"name": "Çanakkale", "slug": "canakkale", "iata": "CKZ", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.1553, "lng": 26.4142},
    {"name": "Balıkesir", "slug": "balikesir", "iata": "EDO", "en_name": "Edremit Koca Seyit Balikesir BZI", "train_station": "Balıkesir Gar", "has_airport": True, "has_train": True, "lat": 39.6484, "lng": 27.8826},
    {"name": "Kütahya", "slug": "kutahya", "iata": "KZR", "train_station": "Kütahya Gar", "has_airport": True, "has_train": True, "lat": 39.4167, "lng": 29.9833},
    {"name": "Afyonkarahisar", "slug": "afyon", "iata": "AFY", "train_station": "Afyon Ali Çetinkaya Gar", "has_airport": False, "has_train": True, "lat": 38.7507, "lng": 30.5567,
     "nearest_domestic_hub": {"name": "Kütahya Zafer (KZR)", "iata": "KZR", "city": "Kütahya", "duration": "45 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "3 sa 30 dk", "transport": "bus"}},
    {"name": "Edirne", "slug": "edirne", "iata": None, "train_station": "Edirne Gar", "has_airport": False, "has_train": True, "lat": 41.6768, "lng": 26.5603,
     "nearest_domestic_hub": {"name": "Tekirdağ Çorlu (TEQ)", "iata": "TEQ", "city": "Tekirdağ", "duration": "1 sa 20 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Havalimanı (IST)", "iata": "IST", "city": "İstanbul", "duration": "2 sa 15 dk (HAVAİST/Otobüs)", "transport": "bus"}},
    {"name": "Kocaeli (İzmit)", "slug": "kocaeli", "iata": "KCO", "train_station": "İzmit YHT Gar", "has_airport": False, "has_train": True, "lat": 40.7654, "lng": 29.9408,
     "nearest_domestic_hub": {"name": "Kocaeli Cengiz Topel (KCO)", "iata": "KCO", "city": "Kocaeli", "duration": "20 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Sabiha Gökçen (SAW)", "iata": "SAW", "city": "İstanbul", "duration": "45 dk (Otobüs/Havaş)", "transport": "bus"}},
    {"name": "Sakarya (Adapazarı)", "slug": "sakarya", "iata": None, "train_station": "Arifiye YHT Gar", "has_airport": False, "has_train": True, "lat": 40.7569, "lng": 30.3783,
     "nearest_domestic_hub": {"name": "Kocaeli Cengiz Topel (KCO)", "iata": "KCO", "city": "Kocaeli", "duration": "35 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Sabiha Gökçen (SAW)", "iata": "SAW", "city": "İstanbul", "duration": "1 sa 15 dk (YHT Pendik veya Otobüs)", "transport": "train_or_bus"}},
    {"name": "Bilecik", "slug": "bilecik", "iata": None, "train_station": "Bilecik YHT Gar", "has_airport": False, "has_train": True, "lat": 40.1426, "lng": 29.9793,
     "nearest_domestic_hub": {"name": "Eskişehir Hasan Polatkan (AOE)", "iata": "AOE", "city": "Eskişehir", "duration": "35 dk (YHT)", "transport": "train"},
     "nearest_intl_hub": {"name": "İstanbul Sabiha Gökçen (SAW)", "iata": "SAW", "city": "İstanbul", "duration": "1 sa 40 dk (YHT Pendik + Metro)", "transport": "train"}},
    {"name": "Karaman", "slug": "karaman", "iata": None, "train_station": "Karaman YHT Gar", "has_airport": False, "has_train": True, "lat": 37.1759, "lng": 33.2287,
     "nearest_domestic_hub": {"name": "Konya Havalimanı (KYA)", "iata": "KYA", "city": "Konya", "duration": "50 dk (YHT)", "transport": "train"},
     "nearest_intl_hub": {"name": "Antalya Havalimanı (AYT)", "iata": "AYT", "city": "Antalya", "duration": "3 sa 30 dk", "transport": "bus"}},
    {"name": "Yozgat", "slug": "yozgat", "iata": None, "train_station": "Yozgat YHT Gar", "has_airport": False, "has_train": True, "lat": 39.8181, "lng": 34.8147,
     "nearest_domestic_hub": {"name": "Kayseri Havalimanı (ASR)", "iata": "ASR", "city": "Kayseri", "duration": "1 sa 30 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "1 sa (YHT Ankara Gar + Havaş)", "transport": "train"}},
    {"name": "Kırıkkale", "slug": "kirikkale", "iata": None, "train_station": "Kırıkkale YHT Gar", "has_airport": False, "has_train": True, "lat": 39.8468, "lng": 33.5153,
     "nearest_domestic_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "1 sa", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "1 sa (Havaş/Otobüs)", "transport": "bus"}},
    {"name": "Aydın", "slug": "aydin", "iata": "AYDN", "train_station": "Aydın Gar", "has_airport": False, "has_train": True, "lat": 37.8560, "lng": 27.8416,
     "nearest_domestic_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "1 sa (Tren/Havaş)", "transport": "train_or_bus"},
     "nearest_intl_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "1 sa", "transport": "train_or_bus"}},
    {"name": "Rize / Artvin", "slug": "rize", "iata": "RZV", "train_station": None, "has_airport": True, "has_train": False, "lat": 41.0201, "lng": 40.5234},
    {"name": "Ordu / Giresun", "slug": "ordu", "iata": "OGU", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.9839, "lng": 37.8764},
    {"name": "Nevşehir (Kapadokya)", "slug": "nevsehir", "iata": "NAV", "train_station": None, "has_airport": True, "has_train": False, "lat": 38.6244, "lng": 34.7144},
    {"name": "Kastamonu", "slug": "kastamonu", "iata": "KFS", "train_station": None, "has_airport": True, "has_train": False, "lat": 41.3887, "lng": 33.7827},
    {"name": "Sinop", "slug": "sinop", "iata": "NOP", "train_station": None, "has_airport": True, "has_train": False, "lat": 42.0231, "lng": 35.1531},
    {"name": "Isparta", "slug": "isparta", "iata": "ISE", "train_station": "Isparta Gar", "has_airport": True, "has_train": True, "lat": 37.7648, "lng": 30.5566},
    {"name": "Bolu", "slug": "bolu", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 40.7350, "lng": 31.6061,
     "nearest_domestic_hub": {"name": "Zonguldak Çaycuma (ONQ)", "iata": "ONQ", "city": "Zonguldak", "duration": "1 sa 30 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Sabiha Gökçen (SAW)", "iata": "SAW", "city": "İstanbul", "duration": "2 sa 15 dk (Otobüs)", "transport": "bus"}},
    {"name": "Zonguldak", "slug": "zonguldak", "iata": "ONQ", "train_station": "Zonguldak Gar", "has_airport": True, "has_train": True, "lat": 41.4564, "lng": 31.7987},
    {"name": "Tokat", "slug": "tokat", "iata": "TJK", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.3167, "lng": 36.5500},
    {"name": "Amasya", "slug": "amasya", "iata": "MZH", "train_station": "Amasya Gar", "has_airport": True, "has_train": True, "lat": 40.6501, "lng": 35.8353},
    {"name": "Elazığ", "slug": "elazig", "iata": "EZS", "train_station": "Elazığ Gar", "has_airport": True, "has_train": True, "lat": 38.6810, "lng": 39.2264},
    {"name": "Batman", "slug": "batman", "iata": "BAL", "train_station": "Batman Gar", "has_airport": True, "has_train": True, "lat": 37.8812, "lng": 41.1293},
    {"name": "Mardin", "slug": "mardin", "iata": "MQM", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.3212, "lng": 40.7245},
    {"name": "Şırnak", "slug": "sirnak", "iata": "NKT", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.5164, "lng": 42.4594},
    {"name": "Hakkari (Yüksekova)", "slug": "hakkari", "iata": "YKO", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.5744, "lng": 43.7408},
    {"name": "Iğdır", "slug": "igdir", "iata": "IGD", "train_station": None, "has_airport": True, "has_train": False, "lat": 39.9196, "lng": 44.0458},
    {"name": "Ağrı", "slug": "agri", "iata": "AJI", "train_station": None, "has_airport": True, "has_train": False, "lat": 39.7191, "lng": 43.0503},
    {"name": "Bingöl", "slug": "bingol", "iata": "BGG", "train_station": None, "has_airport": True, "has_train": False, "lat": 38.8853, "lng": 40.4983},
    {"name": "Muş", "slug": "mus", "iata": "MSR", "train_station": "Muş Gar", "has_airport": True, "has_train": True, "lat": 38.7432, "lng": 41.5064},
    {"name": "Uşak", "slug": "usak", "iata": None, "train_station": "Uşak Gar", "has_airport": False, "has_train": True, "lat": 38.6823, "lng": 29.4082,
     "nearest_domestic_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "2 sa 15 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "2 sa 15 dk", "transport": "bus"}},
    {"name": "Manisa", "slug": "manisa", "iata": None, "train_station": "Manisa Gar", "has_airport": False, "has_train": True, "lat": 38.6191, "lng": 27.4289,
     "nearest_domestic_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "45 dk", "transport": "bus_or_train"},
     "nearest_intl_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "45 dk", "transport": "bus_or_train"}},
    {"name": "Tekirdağ", "slug": "tekirdag", "iata": "TEQ", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.9833, "lng": 27.5167},
    {"name": "Yalova", "slug": "yalova", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "is_ferry": True, "port_code": "YLV", "lat": 40.6500, "lng": 29.2667,
     "nearest_domestic_hub": {"name": "Bursa Yenişehir (YEI)", "iata": "YEI", "city": "Bursa", "duration": "55 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Sabiha Gökçen (SAW)", "iata": "SAW", "city": "İstanbul", "duration": "45 dk (İDO Hızlı Feribot) veya 1 sa 10 dk (Otobüs)", "transport": "ferry_or_bus"}},
    {"name": "Düzce", "slug": "duzce", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 40.8438, "lng": 31.1565,
     "nearest_domestic_hub": {"name": "Kocaeli Cengiz Topel (KCO)", "iata": "KCO", "city": "Kocaeli", "duration": "1 sa 10 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Sabiha Gökçen (SAW)", "iata": "SAW", "city": "İstanbul", "duration": "2 sa", "transport": "bus"}},
    {"name": "Bartın", "slug": "bartin", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 41.6344, "lng": 32.3375,
     "nearest_domestic_hub": {"name": "Zonguldak Çaycuma (ONQ)", "iata": "ONQ", "city": "Zonguldak", "duration": "45 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "3 sa 15 dk", "transport": "bus"}},
    {"name": "Karabük", "slug": "karabuk", "iata": None, "train_station": "Karabük Gar", "has_airport": False, "has_train": True, "lat": 41.2061, "lng": 32.6204,
     "nearest_domestic_hub": {"name": "Kastamonu Havalimanı (KFS)", "iata": "KFS", "city": "Kastamonu", "duration": "1 sa 30 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "2 sa 45 dk", "transport": "bus"}},
    {"name": "Çankırı", "slug": "cankiri", "iata": None, "train_station": "Çankırı Gar", "has_airport": False, "has_train": True, "lat": 40.6013, "lng": 33.6134,
     "nearest_domestic_hub": {"name": "Kastamonu Havalimanı (KFS)", "iata": "KFS", "city": "Kastamonu", "duration": "1 sa 15 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "1 sa 30 dk", "transport": "bus"}},
    {"name": "Kırşehir", "slug": "kirsehir", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 39.1425, "lng": 34.1709,
     "nearest_domestic_hub": {"name": "Nevşehir Kapadokya (NAV)", "iata": "NAV", "city": "Nevşehir", "duration": "1 sa", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "2 sa 15 dk", "transport": "bus"}},
    {"name": "Niğde", "slug": "nigde", "iata": None, "train_station": "Niğde Gar", "has_airport": False, "has_train": True, "lat": 37.9667, "lng": 34.6833,
     "nearest_domestic_hub": {"name": "Nevşehir Kapadokya (NAV)", "iata": "NAV", "city": "Nevşehir", "duration": "1 sa 15 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Adana Şakirpaşa (ADA)", "iata": "ADA", "city": "Adana", "duration": "2 sa", "transport": "bus"}},
    {"name": "Aksaray", "slug": "aksaray", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 38.3687, "lng": 34.0370,
     "nearest_domestic_hub": {"name": "Nevşehir Kapadokya (NAV)", "iata": "NAV", "city": "Nevşehir", "duration": "55 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "2 sa 30 dk", "transport": "bus"}},
    {"name": "Burdur", "slug": "burdur", "iata": None, "train_station": "Burdur Gar", "has_airport": False, "has_train": True, "lat": 37.7203, "lng": 30.2908,
     "nearest_domestic_hub": {"name": "Isparta Süleyman Demirel (ISE)", "iata": "ISE", "city": "Isparta", "duration": "35 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Antalya Havalimanı (AYT)", "iata": "AYT", "city": "Antalya", "duration": "1 sa 45 dk", "transport": "bus"}},
    {"name": "Osmaniye", "slug": "osmaniye", "iata": None, "train_station": "Osmaniye Gar", "has_airport": False, "has_train": True, "lat": 37.0742, "lng": 36.2472,
     "nearest_domestic_hub": {"name": "Adana Şakirpaşa (ADA)", "iata": "ADA", "city": "Adana", "duration": "1 sa", "transport": "bus"},
     "nearest_intl_hub": {"name": "Adana Şakirpaşa (ADA)", "iata": "ADA", "city": "Adana", "duration": "1 sa", "transport": "bus"}},
    {"name": "Kilis", "slug": "kilis", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 36.7184, "lng": 37.1212,
     "nearest_domestic_hub": {"name": "Gaziantep Havalimanı (GZT)", "iata": "GZT", "city": "Gaziantep", "duration": "50 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Gaziantep Havalimanı (GZT)", "iata": "GZT", "city": "Gaziantep", "duration": "50 dk", "transport": "bus"}},
    {"name": "Adıyaman", "slug": "adiyaman", "iata": "ADF", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.7648, "lng": 38.2786},
    {"name": "Siirt", "slug": "siirt", "iata": "SXZ", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.9333, "lng": 41.9500},
    {"name": "Bitlis", "slug": "bitlis", "iata": None, "train_station": "Tatvan Gar", "has_airport": False, "has_train": True, "lat": 38.4006, "lng": 42.1095,
     "nearest_domestic_hub": {"name": "Muş Sultan Alparslan (MSR)", "iata": "MSR", "city": "Muş", "duration": "1 sa 15 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Van Ferit Melen (VAN)", "iata": "VAN", "city": "Van", "duration": "2 sa", "transport": "bus"}},
    {"name": "Tunceli", "slug": "tunceli", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 39.1079, "lng": 39.5401,
     "nearest_domestic_hub": {"name": "Elazığ Havalimanı (EZS)", "iata": "EZS", "city": "Elazığ", "duration": "1 sa 45 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Erzurum Havalimanı (ERZ)", "iata": "ERZ", "city": "Erzurum", "duration": "3 sa", "transport": "bus"}},
    {"name": "Bayburt", "slug": "bayburt", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 40.2552, "lng": 40.2249,
     "nearest_domestic_hub": {"name": "Erzurum Havalimanı (ERZ)", "iata": "ERZ", "city": "Erzurum", "duration": "1 sa 30 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Trabzon Havalimanı (TZX)", "iata": "TZX", "city": "Trabzon", "duration": "2 sa", "transport": "bus"}},
    {"name": "Gümüşhane", "slug": "gumushane", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 40.4600, "lng": 39.4814,
     "nearest_domestic_hub": {"name": "Trabzon Havalimanı (TZX)", "iata": "TZX", "city": "Trabzon", "duration": "1 sa 20 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Trabzon Havalimanı (TZX)", "iata": "TZX", "city": "Trabzon", "duration": "1 sa 20 dk", "transport": "bus"}},
    {"name": "Artvin", "slug": "artvin", "iata": "RZV", "train_station": None, "has_airport": True, "has_train": False, "lat": 41.1828, "lng": 41.8183},
    {"name": "Giresun", "slug": "giresun", "iata": "OGU", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.9128, "lng": 38.3895},
    {"name": "Kırklareli", "slug": "kirklareli", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 41.7333, "lng": 27.2167,
     "nearest_domestic_hub": {"name": "Tekirdağ Çorlu (TEQ)", "iata": "TEQ", "city": "Tekirdağ", "duration": "1 sa 10 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "İstanbul Havalimanı (IST)", "iata": "IST", "city": "İstanbul", "duration": "2 sa", "transport": "bus"}},
    {"name": "Erzincan", "slug": "erzincan", "iata": "ERC", "train_station": "Erzincan Gar (Doğu Ekspresi)", "has_airport": True, "has_train": True, "lat": 39.7500, "lng": 39.5000},
    {"name": "Kahramanmaraş", "slug": "kahramanmaras", "iata": "KCM", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.5753, "lng": 36.9228},
    {"name": "Muğla", "slug": "mugla", "iata": "DLM", "alt_iata": "BJV", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.2153, "lng": 28.3636},
    {"name": "Çorum", "slug": "corum", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 40.5499, "lng": 34.9537,
     "nearest_domestic_hub": {"name": "Amasya Merzifon (MZH)", "iata": "MZH", "city": "Amasya", "duration": "45 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Ankara Esenboğa (ESB)", "iata": "ESB", "city": "Ankara", "duration": "2 sa 30 dk", "transport": "bus"}},
    {"name": "Ardahan", "slug": "ardahan", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 41.1105, "lng": 42.7022,
     "nearest_domestic_hub": {"name": "Kars Harakani (KSY)", "iata": "KSY", "city": "Kars", "duration": "1 sa 10 dk", "transport": "bus"},
     "nearest_intl_hub": {"name": "Kars Harakani (KSY)", "iata": "KSY", "city": "Kars", "duration": "1 sa 10 dk", "transport": "bus"}}
]

# ==================== YURT DIŞI POPÜLER METROPOLLER & AVRUPA TREN MERKEZLERİ ====================
INTERNATIONAL_CITIES = [
    # 🇺🇸 Kuzey Amerika
    {"name": "New York (JFK/EWR)", "slug": "new-york", "country": "ABD", "region": "Amerika", "iata": "JFK", "alt_iata": "EWR", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Los Angeles (LAX)", "slug": "los-angeles", "country": "ABD", "region": "Amerika", "iata": "LAX", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Miami (MIA)", "slug": "miami", "country": "ABD", "region": "Amerika", "iata": "MIA", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Chicago (ORD)", "slug": "chicago", "country": "ABD", "region": "Amerika", "iata": "ORD", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "San Francisco (SFO)", "slug": "san-francisco", "country": "ABD", "region": "Amerika", "iata": "SFO", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Washington D.C. (IAD)", "slug": "washington", "country": "ABD", "region": "Amerika", "iata": "IAD", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Boston (BOS)", "slug": "boston", "country": "ABD", "region": "Amerika", "iata": "BOS", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Toronto (YYZ)", "slug": "toronto", "country": "Kanada", "region": "Amerika", "iata": "YYZ", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Montreal (YUL)", "slug": "montreal", "country": "Kanada", "region": "Amerika", "iata": "YUL", "has_airport": True, "has_train": False, "is_international": True},

    # 🇪🇺 Avrupa Metropolleri & Hızlı Tren Merkezleri
    {"name": "Paris (CDG/ORY)", "en_name": "Paris", "slug": "paris", "country": "Fransa", "region": "Avrupa", "iata": "CDG", "alt_iata": "ORY", "train_station": "Paris Gare du Nord (Eurostar/TGV)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Londra (LHR/STN)", "en_name": "London Londra", "slug": "londra", "country": "İngiltere", "region": "Avrupa", "iata": "LHR", "alt_iata": "STN", "train_station": "London St Pancras Int (Eurostar)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Roma (FCO)", "en_name": "Rome Roma", "slug": "roma", "country": "İtalya", "region": "Avrupa", "iata": "FCO", "alt_iata": "CIA", "train_station": "Roma Termini (Frecciarossa)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Milano (MXP)", "en_name": "Milan Milano", "slug": "milano", "country": "İtalya", "region": "Avrupa", "iata": "MXP", "alt_iata": "LIN", "train_station": "Milano Centrale (Frecciarossa)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Venedik (VCE)", "en_name": "Venice Venedik Venezia", "slug": "venedik", "country": "İtalya", "region": "Avrupa", "iata": "VCE", "train_station": "Venezia Santa Lucia (Frecciarossa)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Berlin (BER)", "en_name": "Berlin", "slug": "berlin", "country": "Almanya", "region": "Avrupa", "iata": "BER", "train_station": "Berlin Hbf (ICE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Amsterdam (AMS)", "en_name": "Amsterdam", "slug": "amsterdam", "country": "Hollanda", "region": "Avrupa", "iata": "AMS", "train_station": "Amsterdam Centraal (Eurostar)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Brüksel (BRU)", "en_name": "Brussels Bruksel Bruxelles", "slug": "bruksel", "country": "Belçika", "region": "Avrupa", "iata": "BRU", "alt_iata": "CRL", "train_station": "Bruxelles-Midi (Eurostar)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Viyana (VIE)", "en_name": "Vienna Viyana Wien", "slug": "viyana", "country": "Avusturya", "region": "Avrupa", "iata": "VIE", "train_station": "Wien Hbf (ÖBB Railjet)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Prag (PRG)", "en_name": "Prague Prag Praha", "slug": "prag", "country": "Çekya", "region": "Avrupa", "iata": "PRG", "train_station": "Praha hlavní nádraží", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Budapeşte (BUD)", "en_name": "Budapest Budapeste", "slug": "budapeste", "country": "Macaristan", "region": "Avrupa", "iata": "BUD", "train_station": "Budapest Keleti", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Barselona (BCN)", "en_name": "Barcelona Barselona", "slug": "barselona", "country": "İspanya", "region": "Avrupa", "iata": "BCN", "train_station": "Barcelona Sants (AVE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Madrid (MAD)", "en_name": "Madrid", "slug": "madrid", "country": "İspanya", "region": "Avrupa", "iata": "MAD", "train_station": "Madrid Puerta de Atocha (AVE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Frankfurt (FRA)", "en_name": "Frankfurt", "slug": "frankfurt", "country": "Almanya", "region": "Avrupa", "iata": "FRA", "train_station": "Frankfurt (Main) Hbf (ICE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Münih (MUC)", "en_name": "Munich Munih Munchen", "slug": "munih", "country": "Almanya", "region": "Avrupa", "iata": "MUC", "train_station": "München Hbf (ICE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Zürih (ZRH)", "en_name": "Zurich Zurih", "slug": "zurih", "country": "İsviçre", "region": "Avrupa", "iata": "ZRH", "train_station": "Zürich HB (SBB)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Cenevre (GVA)", "en_name": "Geneva Cenevre Geneve", "slug": "cenevre", "country": "İsviçre", "region": "Avrupa", "iata": "GVA", "train_station": "Genève Cornavin", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Basel (BSL)", "en_name": "Basel Mulhouse", "slug": "basel", "country": "İsviçre", "region": "Avrupa", "iata": "BSL", "train_station": "Basel SBB", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Düsseldorf (DUS)", "en_name": "Dusseldorf Duesseldorf", "slug": "dusseldorf", "country": "Almanya", "region": "Avrupa", "iata": "DUS", "train_station": "Düsseldorf Hbf", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Köln / Bonn (CGN)", "en_name": "Cologne Koln Koeln", "slug": "koln", "country": "Almanya", "region": "Avrupa", "iata": "CGN", "train_station": "Köln Hbf", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Stuttgart (STR)", "en_name": "Stuttgart", "slug": "stuttgart", "country": "Almanya", "region": "Avrupa", "iata": "STR", "train_station": "Stuttgart Hbf", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Hamburg (HAM)", "en_name": "Hamburg", "slug": "hamburg", "country": "Almanya", "region": "Avrupa", "iata": "HAM", "train_station": "Hamburg Hbf", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Nice (NCE)", "en_name": "Nice", "slug": "nice", "country": "Fransa", "region": "Avrupa", "iata": "NCE", "train_station": "Gare de Nice-Ville (TER Monaco)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Monaco / Monte Carlo", "en_name": "Monaco Monte Carlo", "slug": "monaco", "country": "Monaco", "region": "Avrupa", "iata": "NCE", "train_station": "Gare de Monaco-Monte Carlo", "has_airport": True, "nearest_airport_iata": "NCE", "nearest_airport_name": "Nice Côte d'Azur (NCE)", "has_train": True, "is_international": True},
    {"name": "Lefkoşa / Ercan (ECN)", "en_name": "Nicosia Ercan Lefkosa Girne Kibris", "slug": "lefkosa", "country": "Kuzey Kıbrıs", "region": "Akdeniz", "iata": "ECN", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Moskova (SVO/DME/VKO)", "en_name": "Moscow Moskova", "slug": "moskova", "country": "Rusya", "region": "Doğu Avrupa", "iata": "SVO", "alt_iata": "VKO", "has_airport": True, "has_train": False, "is_international": True},

    # 🚌 Komşu Ülkeler (Uçak + Karayolu Otobüs Seferleri Aktif)
    {"name": "Selanik (SKG)", "en_name": "Thessaloniki Selanik", "slug": "selanik", "country": "Yunanistan", "region": "Balkanlar", "iata": "SKG", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Atina (ATH)", "en_name": "Athens Atina", "slug": "atina", "country": "Yunanistan", "region": "Balkanlar", "iata": "ATH", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Sofya (SOF)", "en_name": "Sofia Sofya", "slug": "sofya", "country": "Bulgaristan", "region": "Balkanlar", "iata": "SOF", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Filibe / Plovdiv (PDV)", "en_name": "Plovdiv Filibe", "slug": "filibe", "country": "Bulgaristan", "region": "Balkanlar", "iata": "PDV", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Varna (VAR)", "en_name": "Varna", "slug": "varna", "country": "Bulgaristan", "region": "Balkanlar", "iata": "VAR", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Batum (BUS)", "en_name": "Batumi Batum", "slug": "batum", "country": "Gürcistan", "region": "Kafkaslar", "iata": "BUS", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Tiflis (TBS)", "en_name": "Tbilisi Tiflis", "slug": "tiflis", "country": "Gürcistan", "region": "Kafkaslar", "iata": "TBS", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Bakü (GYD)", "en_name": "Baku", "slug": "baku", "country": "Azerbaycan", "region": "Kafkaslar", "iata": "GYD", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Üsküp (SKP)", "en_name": "Skopje Uskup", "slug": "uskup", "country": "Kuzey Makedonya", "region": "Balkanlar", "iata": "SKP", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Belgrad (BEG)", "en_name": "Belgrade Belgrad", "slug": "belgrad", "country": "Sırbistan", "region": "Balkanlar", "iata": "BEG", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True},
    {"name": "Saraybosna (SJJ)", "en_name": "Sarajevo Saraybosna", "slug": "saraybosna", "country": "Bosna-Hersek", "region": "Balkanlar", "iata": "SJJ", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True},
    {"name": "Tiran (TIA)", "en_name": "Tirana Tiran", "slug": "tiran", "country": "Arnavutluk", "region": "Balkanlar", "iata": "TIA", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True},
    {"name": "Bükreş (OTP)", "en_name": "Bucharest Bukres", "slug": "bukres", "country": "Romanya", "region": "Balkanlar", "iata": "OTP", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Podgorica (TGD)", "en_name": "Podgorica Karadag Montenegro", "slug": "podgorica", "country": "Karadağ", "region": "Balkanlar", "iata": "TGD", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Priştine (PRN)", "en_name": "Pristina Pristine Kosova", "slug": "pristine", "country": "Kosova", "region": "Balkanlar", "iata": "PRN", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Lizbon (LIS)", "en_name": "Lisbon Lizbon Lisboa", "slug": "lizbon", "country": "Portekiz", "region": "Avrupa", "iata": "LIS", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Kopenhag (CPH)", "en_name": "Copenhagen Kopenhag", "slug": "kopenhag", "country": "Danimarka", "region": "Avrupa", "iata": "CPH", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Stockholm (ARN)", "en_name": "Stockholm", "slug": "stockholm", "country": "İsveç", "region": "Avrupa", "iata": "ARN", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Oslo (OSL)", "en_name": "Oslo", "slug": "oslo", "country": "Norveç", "region": "Avrupa", "iata": "OSL", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Varşova (WAW)", "en_name": "Warsaw Varsova", "slug": "varsova", "country": "Polonya", "region": "Avrupa", "iata": "WAW", "has_airport": True, "has_train": True, "is_international": True},

    # 🇦🇪 Orta Doğu & Körfez
    {"name": "Dubai (DXB)", "slug": "dubai", "country": "BAE", "region": "Orta Doğu", "iata": "DXB", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Abu Dabi (AUH)", "en_name": "Abu Dhabi", "slug": "abu-dabi", "country": "BAE", "region": "Orta Doğu", "iata": "AUH", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Doha (DOH)", "slug": "doha", "country": "Katar", "region": "Orta Doğu", "iata": "DOH", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Kahire (CAI)", "en_name": "Cairo Kahire", "slug": "kahire", "country": "Mısır", "region": "Orta Doğu", "iata": "CAI", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Şarm El-Şeyh (SSH)", "en_name": "Sharm El Sheikh", "slug": "sarm-el-seyh", "country": "Mısır", "region": "Orta Doğu", "iata": "SSH", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Riyad (RUH)", "slug": "riyad", "country": "Suudi Arabistan", "region": "Orta Doğu", "iata": "RUH", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Cidde (JED)", "slug": "cidde", "country": "Suudi Arabistan", "region": "Orta Doğu", "iata": "JED", "has_airport": True, "has_train": False, "is_international": True},

    # 🌏 Asya & Pasifik
    {"name": "Tokyo (NRT/HND)", "slug": "tokyo", "country": "Japonya", "region": "Asya", "iata": "HND", "alt_iata": "NRT", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Singapur (SIN)", "slug": "singapur", "country": "Singapur", "region": "Asya", "iata": "SIN", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Bangkok (BKK)", "slug": "bangkok", "country": "Tayland", "region": "Asya", "iata": "BKK", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Seul (ICN)", "slug": "seul", "country": "Güney Kore", "region": "Asya", "iata": "ICN", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Bali (DPS)", "slug": "bali", "country": "Endonezya", "region": "Asya", "iata": "DPS", "has_airport": True, "has_train": False, "is_international": True}
]

# ==================== DENİZ YOLLARI & FERİBOT LİMANLARI ====================
FERRY_PORTS = [
    {"name": "Yenikapı (İstanbul - İDO)", "slug": "yenikapi-ido", "port_code": "YNK", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 41.0028, "lng": 28.9567},
    {"name": "Eminönü / Sirkeci (İstanbul - BUDO)", "slug": "eminonu-budo", "port_code": "EMN", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 41.0180, "lng": 28.9740},
    {"name": "Pendik (İstanbul - İDO)", "slug": "pendik-ido", "port_code": "PND", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.8753, "lng": 29.2336},
    {"name": "Bursa (Güzelyalı İskelesi - İDO)", "slug": "bursa-guzelyali-ido", "port_code": "GZY", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.3644, "lng": 28.9100},
    {"name": "Mudanya (Bursa İskelesi - BUDO)", "slug": "mudanya-bursa-budo", "port_code": "MDN", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.3753, "lng": 28.8828},
    {"name": "Yalova İskelesi", "slug": "yalova-iskele", "port_code": "YLV", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.6580, "lng": 29.2780},
    {"name": "Bandırma Limanı", "slug": "bandirma", "port_code": "BND", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.3540, "lng": 27.9730},
    {"name": "Avşa Adası", "slug": "avsa-adasi", "port_code": "AVS", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.5050, "lng": 27.5110},
    {"name": "Armutlu İskelesi", "slug": "armutlu", "port_code": "ARM", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.5180, "lng": 28.8280},
    {"name": "Çeşme Limanı (İzmir)", "slug": "cesme", "port_code": "CSM", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 38.3240, "lng": 26.3020},
    {"name": "Sakız Adası (Chios)", "slug": "sakiz-adasi", "port_code": "JKH", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 38.3680, "lng": 26.1360},
    {"name": "Bodrum Limanı (Muğla)", "slug": "bodrum-liman", "port_code": "BXN", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 37.0310, "lng": 27.4290},
    {"name": "Kos Adası (İstanköy)", "slug": "kos-adasi", "port_code": "KGS", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 36.8930, "lng": 27.2880},
    {"name": "Ayvalık Limanı (Balıkesir)", "slug": "ayvalik", "port_code": "AYV", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 39.3190, "lng": 26.6930},
    {"name": "Midilli Adası (Lesvos)", "slug": "midilli-adasi", "port_code": "MJT", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 39.1050, "lng": 26.5550},
    {"name": "Kuşadası Limanı (Aydın)", "slug": "kusadasi", "port_code": "KUS", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 37.8610, "lng": 27.2600},
    {"name": "Samos Adası (Sisam)", "slug": "samos-adasi", "port_code": "SMI", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 37.7550, "lng": 26.9770},
    {"name": "Fethiye Limanı (Muğla)", "slug": "fethiye", "port_code": "FTH", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 36.6210, "lng": 29.1120},
    {"name": "Rodos Adası (Rhodes)", "slug": "rodos-adasi", "port_code": "RHO", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 36.4340, "lng": 28.2170},
    {"name": "Marmaris Limanı (Muğla)", "slug": "marmaris", "port_code": "MRM", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 36.8520, "lng": 28.2740},
    {"name": "Kaş Limanı (Antalya)", "slug": "kas", "port_code": "KAS", "region": "Akdeniz", "is_ferry": True, "country": "Türkiye", "lat": 36.1990, "lng": 29.6380},
    {"name": "Meis Adası (Kastellorizo)", "slug": "meis-adasi", "port_code": "KZS", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 36.1480, "lng": 29.5930},
    {"name": "Simi Adası (Symi)", "slug": "simi-adasi", "port_code": "SYM", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "is_international": True, "requires_visa": True, "lat": 36.6150, "lng": 27.8360},
    {"name": "Çanakkale İskelesi (Gestaş)", "slug": "canakkale-iskele", "port_code": "CNK", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.1510, "lng": 26.4020},
    {"name": "Eceabat / Gelibolu İskelesi (Gestaş)", "slug": "eceabat", "port_code": "ECB", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.1840, "lng": 26.3570},
    {"name": "Geyikli İskelesi (Çanakkale)", "slug": "geyikli", "port_code": "GYK", "region": "Kuzey Ege", "is_ferry": True, "country": "Türkiye", "lat": 39.7980, "lng": 26.1530},
    {"name": "Bozcaada Limanı (Gestaş)", "slug": "bozcaada", "port_code": "BZC", "region": "Kuzey Ege", "is_ferry": True, "country": "Türkiye", "lat": 39.8360, "lng": 26.0710},
    {"name": "Kabatepe İskelesi (Çanakkale)", "slug": "kabatepe", "port_code": "KBT", "region": "Kuzey Ege", "is_ferry": True, "country": "Türkiye", "lat": 40.2010, "lng": 26.2680},
    {"name": "Gökçeada Kuzu Limanı (Gestaş)", "slug": "gokceada", "port_code": "GKC", "region": "Kuzey Ege", "is_ferry": True, "country": "Türkiye", "lat": 40.2310, "lng": 25.9500},
    {"name": "Taşucu Limanı (Mersin - KKTC Feribot)", "slug": "tasucu", "port_code": "TSC", "region": "Akdeniz", "is_ferry": True, "country": "Türkiye", "lat": 36.3160, "lng": 33.8840},
    {"name": "Girne Limanı (KKTC - Kıbrıs)", "slug": "girne", "port_code": "KYR", "region": "KKTC", "is_ferry": True, "country": "KKTC", "is_international": True, "lat": 35.3410, "lng": 33.3200},
    {"name": "Galataport Kruvaziyer Limanı (İstanbul)", "slug": "galataport", "port_code": "GLT", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 41.0260, "lng": 28.9830},
    {"name": "Erdek İskelesi (Balıkesir - GESTAŞ)", "slug": "erdek-iskele", "port_code": "ERD", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.3980, "lng": 27.7920},
    {"name": "Eskihisar İskelesi (Gebze / Kocaeli - İDO)", "slug": "eskihisar", "port_code": "ESK", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.7690, "lng": 29.4270},
    {"name": "Topçular İskelesi (Yalova - İDO)", "slug": "topcular", "port_code": "TOP", "region": "Marmara", "is_ferry": True, "country": "Türkiye", "lat": 40.6880, "lng": 29.4420},
    {"name": "Dikili Limanı (İzmir)", "slug": "dikili", "port_code": "DIK", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 39.0720, "lng": 26.8860},
    {"name": "Seferihisar Sığacık Teos Limanı (İzmir)", "slug": "sigacik-liman", "port_code": "SIG", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 38.1940, "lng": 26.7840}
]

from app.turkey_districts import TURKEY_DISTRICTS

ALL_LOCATIONS = TURKEY_CITIES + INTERNATIONAL_CITIES + FERRY_PORTS + TURKEY_DISTRICTS

def _norm_ascii(s: str) -> str:
    if not s:
        return ""
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return s.translate(tr_map).lower().strip()

def find_city(city_name: str):
    return find_location(city_name)

def find_location(location_name: str):
    if not location_name:
        return None
    raw = location_name.strip()
    loc_clean = raw.lower()
    loc_ascii = _norm_ascii(raw)
    
    # 0. İstanbul çoklu havalimanı ayrıştırması
    if "tüm havalimanları" in loc_clean or "tum havalimanlari" in loc_clean or ("ist" in loc_clean and "saw" in loc_clean):
        for c in ALL_LOCATIONS:
            if c.get("slug") == "istanbul":
                return c

    if "sabiha" in loc_clean or (re.search(r'\bsaw\b', loc_clean) and not re.search(r'\bist\b', loc_clean)):
        for c in ALL_LOCATIONS:
            if c.get("slug") == "istanbul-sabiha-gokcen":
                return c

    if "istanbul havalimanı" in loc_clean or "istanbul havalimani" in loc_clean or (re.search(r'\bist\b', loc_clean) and not re.search(r'\bsaw\b', loc_clean) and "istanbul" in loc_clean):
        for c in ALL_LOCATIONS:
            if c.get("slug") == "istanbul-havalimani":
                return c

    # 0.5. "Merkez (Çorum)" / "Merkez (Erzincan)" formatındaki merkez ilçe kayıtlarını doğrudan il adına çevir
    m_merkez = re.match(r'^\s*merkez\s*\(([^)]+)\)', loc_clean, flags=re.IGNORECASE)
    if m_merkez:
        loc_clean = m_merkez.group(1).strip().lower()
        loc_ascii = _norm_ascii(loc_clean)

    # 1. Parantez içindeki IATA / Liman Kodlarını öncelikli kontrol et (Örn: "Antalya (AYT)")
    codes = re.findall(r'\b[A-Za-z]{3}\b', raw)
    for code in codes:
        c_code = code.upper()
        for c in ALL_LOCATIONS:
            if (c.get("iata") == c_code or 
                c.get("alt_iata") == c_code or 
                c.get("port_code") == c_code):
                return c

    # 1. Tam eşleşme (name, slug, en_name veya iata - Türkçe/ASCII normalize dahil)
    for c in ALL_LOCATIONS:
        c_name = c.get("name", "").lower()
        c_slug = c.get("slug", "").lower()
        c_en = c.get("en_name", "").lower()
        if (c_name == loc_clean or 
            _norm_ascii(c_name) == loc_ascii or
            c_slug == loc_clean or 
            c_slug == loc_ascii or
            (c_en and (loc_clean in c_en.split() or loc_ascii in _norm_ascii(c_en).split())) or
            (c.get("iata") and c.get("iata", "").lower() == loc_clean)):
            return c

    # 2. Parantezleri temizleyip eşleştir (Örn: "Antalya (AYT)" -> "antalya", "Merkez (Çorum)" -> "çorum")
    m_merkez = re.match(r'^\s*merkez\s*\(([^)]+)\)', loc_clean, flags=re.IGNORECASE)
    if m_merkez:
        base_name = m_merkez.group(1).strip()
    else:
        base_name = re.sub(r'\(.*?\)', '', loc_clean).strip()
    base_ascii = _norm_ascii(base_name)
    if base_name:
        for c in ALL_LOCATIONS:
            c_name = re.sub(r'\(.*?\)', '', c.get("name", "").lower()).strip()
            c_slug = c.get("slug", "").lower()
            if (base_name == c_name or base_name == c_slug or
                base_ascii == _norm_ascii(c_name) or base_ascii == c_slug):
                return c
            
    # 3. Başlangıç veya alt dize eşleşmesi (çift yönlü esnek eşleşme + ASCII/İngilizce destekli)
    for c in ALL_LOCATIONS:
        c_name = c.get("name", "").lower()
        c_ascii = _norm_ascii(c_name)
        c_en = _norm_ascii(c.get("en_name", ""))
        if (loc_clean in c_name or c_name in loc_clean or
            (len(loc_ascii) >= 3 and (loc_ascii in c_ascii or (c_en and loc_ascii in c_en))) or
            (base_name and (base_name in c_name or c_name in base_name or (len(base_ascii) >= 3 and base_ascii in c_ascii)))):
            return c
            
    return None

def get_cities_by_transport(transport_type: str = "all", scope: str = "all"):
    """
    Seçilen seyahat moduna (flight, train, bus, ferry) ve kapsama (domestic, international, all) göre lokasyonları filtreler
    """
    if transport_type == "flight":
        tr_airports = [c for c in TURKEY_CITIES if c.get("has_airport")]
        if scope == "domestic":
            return tr_airports
        elif scope == "international":
            return tr_airports + INTERNATIONAL_CITIES
        return tr_airports + INTERNATIONAL_CITIES
    elif transport_type == "train":
        tr_trains = [c for c in TURKEY_CITIES if c.get("has_train")]
        int_trains = [c for c in INTERNATIONAL_CITIES if c.get("has_train")]
        if scope == "domestic":
            return tr_trains
        elif scope == "international":
            return tr_trains + int_trains
        return tr_trains + int_trains
    elif transport_type == "bus":
        tr_buses = TURKEY_CITIES + TURKEY_DISTRICTS
        overland_buses = [c for c in INTERNATIONAL_CITIES if c.get("has_bus")]
        if scope == "domestic":
            return tr_buses
        elif scope == "international":
            return tr_buses + overland_buses
        return tr_buses + overland_buses
    elif transport_type == "ferry":
        return FERRY_PORTS
    elif transport_type == "car":
        return [c for c in TURKEY_CITIES if c.get("has_airport") or c.get("slug") in ("istanbul", "ankara", "izmir", "antalya", "bursa", "mugla", "bodrum")]
    
    # "all" modu
    if scope == "domestic":
        return TURKEY_CITIES + [p for p in FERRY_PORTS if p.get("country") == "Türkiye"]
    elif scope == "international":
        tr_airports = [c for c in TURKEY_CITIES if c.get("has_airport")]
        return tr_airports + INTERNATIONAL_CITIES + [p for p in FERRY_PORTS if p.get("country") != "Türkiye"]
        
    return ALL_LOCATIONS


_SPECIAL_DISTRICT_AIRPORT_SLUGS = {
    "manavgat": "antalya",
    "side": "antalya",
    "alanya": "antalya",
    "gazipasa": "antalya",
    "kemer": "antalya",
    "kas": "dalaman",
    "serik": "antalya",
    "belek": "antalya",
    "kumluca": "antalya",
    "finike": "antalya",
    "demre": "antalya",
    "fethiye": "dalaman",
    "marmaris": "dalaman",
    "datca": "dalaman",
    "ortaca": "dalaman",
    "koycegiz": "dalaman",
    "dalaman": "dalaman",
    "ula": "dalaman",
    "mentese": "dalaman",
    "mugla": "dalaman",
    "bodrum": "bodrum",
    "milas": "bodrum",
    "cesme": "izmir",
    "alacati": "izmir",
    "urla": "izmir",
    "seferihisar": "izmir",
    "foca": "izmir",
    "selcuk": "izmir",
    "kusadasi": "izmir",
    "didim": "bodrum",
    "soke": "izmir",
    "nazilli": "izmir",
    "aydin": "izmir",
    "manisa": "izmir",
    "akhisar": "izmir",
    "turgutlu": "izmir",
    "salihli": "izmir",
    "soma": "izmir",
    "ayvalik": "balikesir",
    "edremit": "balikesir",
    "burhaniye": "balikesir",
    "bandirma": "balikesir",
    "erdek": "balikesir",
    "gonen": "balikesir",
    "kocaeli": "istanbul-sabiha-gokcen",
    "izmit": "istanbul-sabiha-gokcen",
    "gebze": "istanbul-sabiha-gokcen",
    "sakarya": "istanbul-sabiha-gokcen",
    "adapazari": "istanbul-sabiha-gokcen",
    "sapanca": "istanbul-sabiha-gokcen",
    "yalova": "istanbul-sabiha-gokcen",
    "bolu": "istanbul-sabiha-gokcen",
    "duzce": "istanbul-sabiha-gokcen",
    "edirne": "istanbul-havalimani",
    "kirklareli": "istanbul-havalimani",
    "luleburgaz": "istanbul-havalimani",
    "corlu": "istanbul-havalimani",
    "cerkezkoy": "istanbul-havalimani",
    "safranbolu": "ankara",
    "karabuk": "ankara",
    "bartin": "ankara",
    "pamukkale": "denizli",
    "iskenderun": "hatay",
    "antakya": "hatay",
    "dortyol": "hatay",
    "tarsus": "adana",
    "mersin": "adana",
    "cukurova": "adana",
    "cizre": "sirnak",
    "silopi": "sirnak",
    "yuksekova": "hakkari",
    "semdinli": "hakkari",
    "dogubayazit": "agri",
    "ercis": "van",
    "siverek": "sanliurfa",
    "viransehir": "sanliurfa",
    "birecik": "sanliurfa",
    "bozcaada": "canakkale",
    "gokceada": "canakkale",
    "assos": "balikesir",
    "behramkale": "balikesir",
    "girne": "lefkosa",
    "magusa": "lefkosa",
    "gazimagusa": "lefkosa",
    "kapadokya": "nevsehir",
    "urgup": "nevsehir",
    "goreme": "nevsehir",
    "avanos": "nevsehir",
    "nigde": "kayseri",
    "aksaray": "nevsehir",
    "karaman": "konya",
    "afyon": "ankara",
    "afyonkarahisar": "ankara",
    "usak": "izmir",
    "kutahya": "kutahya",
    "bilecik": "istanbul-sabiha-gokcen",
    "gumushane": "trabzon",
    "bayburt": "trabzon",
    "ardahan": "kars",
    "bitlis": "mus",
    "tunceli": "elazig",
    "kilis": "gaziantep",
    "osmaniye": "adana",
    "selimiye": "dalaman",
    "bozburun": "dalaman",
    "hisaronu": "dalaman",
    "icmeler": "dalaman",
    "turunc": "dalaman",
    "akyaka": "dalaman",
    "dalyan": "dalaman",
    "gocek": "dalaman",
    "oludeniz": "dalaman",
    "kalkan": "dalaman",
    "olimpos": "antalya",
    "cirali": "antalya",
    "adrasan": "antalya",
    "ilica": "izmir",
    "sigacik": "izmir",
    "kucukkuyu": "balikesir",
    "altinoluk": "balikesir",
    "akcay": "balikesir",
    "cunda": "balikesir",
    "agva": "istanbul-sabiha-gokcen",
    "sile": "istanbul-sabiha-gokcen",
    "masukiye": "istanbul-sabiha-gokcen",
    "kartepe": "istanbul-sabiha-gokcen",
    "abant": "istanbul-sabiha-gokcen",
    "kartalkaya": "istanbul-sabiha-gokcen",
    "amasra": "ankara",
    "uzungol": "trabzon",
    "caykara": "trabzon",
    "ayder": "rize",
    "camlihemsin": "rize",
    "uludag": "bursa",
    "sarikamis": "kars",
    "palandoken": "erzurum",
    "erciyes": "kayseri",
    "corum": "amasya",
    "sungurlu": "amasya",
    "osmancik": "amasya",
    "cankiri": "ankara",
    "kirikkale": "ankara",
    "kirsehir": "nevsehir",
    "yozgat": "kayseri",
    "sorgun": "kayseri",
    "burdur": "antalya",
    "bucak": "antalya",
    "salda": "denizli",
    "afsin": "kahramanmaras",
    "elbistan": "kahramanmaras",
    "erzincan": "erzincan",
    "kahramanmaras": "kahramanmaras",
    "maras": "kahramanmaras",
}


# Kısıtlı / Sezonluk Havalimanlarının 0 Sonuç Durumunda Yönlendirileceği 7/24 Aktif Ana Hub Tablosu
FALLBACK_MAJOR_HUB_BY_IATA = {
    "AOE": {"hub_slug": "ankara", "hub_iata": "ESB", "hub_name": "Ankara Esenboğa (ESB)", "transfer_note": "YHT ile Eskişehir 1 sa 15 dk", "domestic_inactive": True},
    "USQ": {"hub_slug": "izmir", "hub_iata": "ADB", "hub_name": "İzmir Adnan Menderes (ADB)", "transfer_note": "Otobüs ile Uşak 2 sa 15 dk", "domestic_inactive": True},
    "YEI": {"hub_slug": "istanbul-sabiha-gokcen", "hub_iata": "SAW", "hub_name": "İstanbul Sabiha Gökçen (SAW)", "transfer_note": "BBBUS ile Bursa 1 sa 15 dk", "domestic_inactive": False},
    "KZR": {"hub_slug": "ankara", "hub_iata": "ESB", "hub_name": "Ankara Esenboğa (ESB)", "transfer_note": "YHT / Otobüs bağlantılı", "domestic_inactive": False},
    "ISE": {"hub_slug": "antalya", "hub_iata": "AYT", "hub_name": "Antalya Havalimanı (AYT)", "transfer_note": "Otobüs/Transfer ile 1 sa 45 dk", "domestic_inactive": False},
    "ONQ": {"hub_slug": "ankara", "hub_iata": "ESB", "hub_name": "Ankara Esenboğa (ESB)", "transfer_note": "Karayolu ile 2 sa 45 dk", "domestic_inactive": False},
    "TEQ": {"hub_slug": "istanbul-havalimani", "hub_iata": "IST", "hub_name": "İstanbul Havalimanı (IST)", "transfer_note": "HAVAİST / Otobüs ile 1 sa 15 dk", "domestic_inactive": False},
    "CKZ": {"hub_slug": "izmir", "hub_iata": "ADB", "hub_name": "İzmir Adnan Menderes (ADB)", "transfer_note": "Karayolu bağlantılı", "domestic_inactive": False},
    "KFS": {"hub_slug": "ankara", "hub_iata": "ESB", "hub_name": "Ankara Esenboğa (ESB)", "transfer_note": "Havaş / Otobüs ile 2 sa 30 dk", "domestic_inactive": False},
    "NOP": {"hub_slug": "samsun", "hub_iata": "SZF", "hub_name": "Samsun Çarşamba (SZF)", "transfer_note": "Havaş / Otobüs ile 2 sa", "domestic_inactive": False},
    "TJK": {"hub_slug": "samsun", "hub_iata": "SZF", "hub_name": "Samsun Çarşamba (SZF)", "transfer_note": "Karayolu ile 2 sa 15 dk", "domestic_inactive": False},
    "SXZ": {"hub_slug": "diyarbakir", "hub_iata": "DIY", "hub_name": "Diyarbakır Havalimanı (DIY)", "transfer_note": "Karayolu ile 2 sa", "domestic_inactive": False},
}


def resolve_nearest_airport_city(location_or_name):
    """
    Havalimanı olmayan ilçe veya şehirler (Örn: Manavgat, Alanya, Fethiye, Marmaris, Çeşme, Kuşadası, Bolu)
    için en yakın aktif havalimanına sahip şehir nesnesini (city dict) ve (is_nearby: bool) bayrağını döndürür.
    Doğrudan havalimanı olan şehirlerde (city, False) döner.
    """
    input_str = ""
    if isinstance(location_or_name, dict):
        loc = location_or_name
        input_str = loc.get("name") or loc.get("slug") or ""
    else:
        input_str = str(location_or_name or "").strip()
        loc = find_location(input_str)

    if loc and loc.get("has_airport") and loc.get("iata"):
        return loc, False

    # Doğrudan girilen metni aday slug olarak hazırla
    norm_input = (
        input_str.replace("İ", "i")
        .replace("I", "i")
        .replace("ı", "i")
        .lower()
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
        .replace("\u0307", "")
    )
    raw_cand = re.sub(r"[^a-z0-9-]+", "-", norm_input).strip("-")
    slug = (loc.get("slug") or "").lower().strip() if loc else ""
    raw_slug = re.sub(r"[^a-z0-9-]+", "-", (loc.get("raw_name") or "").lower().strip()).strip("-") if loc else ""

    for candidate_slug in (raw_cand, slug, raw_slug):
        if candidate_slug and candidate_slug in _SPECIAL_DISTRICT_AIRPORT_SLUGS:
            target_slug = _SPECIAL_DISTRICT_AIRPORT_SLUGS[candidate_slug]
            for c in (TURKEY_CITIES + INTERNATIONAL_CITIES):
                if c.get("slug") == target_slug and c.get("has_airport") and c.get("iata"):
                    return c, True

    if not loc:
        return None, False

    # İl (Province) üzerinden çözümle (Örn: Manavgat (Antalya) -> Antalya (AYT))
    province_name = loc.get("province")
    if province_name:
        prov_norm = province_name.lower().strip()
        if prov_norm in ("muğla", "mugla"):
            for c in TURKEY_CITIES:
                if c.get("slug") == "dalaman":
                    return c, True
        prov_city = find_location(province_name)
        if prov_city:
            if prov_city.get("has_airport") and prov_city.get("iata"):
                return prov_city, True
            hub = prov_city.get("nearest_intl_hub") or prov_city.get("nearest_domestic_hub")
            if hub:
                hub_city = find_location(hub.get("iata") or hub.get("city") or "")
                if hub_city and hub_city.get("has_airport") and hub_city.get("iata"):
                    return hub_city, True

    # Şehir nesnesinin kendi nearest_intl_hub / nearest_domestic_hub bilgisi üzerinden çözümle
    hub = loc.get("nearest_intl_hub") or loc.get("nearest_domestic_hub")
    if hub:
        hub_city = find_location(hub.get("iata") or hub.get("city") or "")
        if hub_city and hub_city.get("has_airport") and hub_city.get("iata"):
            return hub_city, True

    return None, False


# Obilet Gerçek Uçuş Sonuçları (/ucuslar/{orig_id}-{dest_id}/{YYYYMMDD}/{pax}/{cabin}/all) İçin Doğrulanmış Havalimanı ID Tablosu
OBILET_AIRPORT_IDS = {
    "IST_ALL": "250_0",
    "IST": "349_5157",
    "SAW": "350_67",
    "ADB": "251_18",
    "ESB": "222_4",
    "GZP": "223_6",
    "COV": "217_8298",
    "ADF": "218_2",
    "AJI": "220_3",
    "MZH": "221_5136",
    "EDO": "226_7",
    "BGG": "228_5137",
    "YEI": "232_8",
    "CKZ": "233_9",
    "DNZ": "236_10",
    "DIY": "237_11",
    "EZS": "239_12",
    "ERC": "240_13",
    "ERZ": "241_14",
    "AOE": "242_15",
    "YKO": "246_5138",
    "AYT": "223_5",
    "ADA": "217_8298",
    "TZX": "277_33",
    "KYA": "258_21",
    "GZT": "243_16",
    "SZF": "271_28",
    "ASR": "254_20",
    "BJV": "476_68",
    "DLM": "508_69",
    "VAN": "281_35",
    "VAS": "274_31",
    "KSY": "252_19",
    "HTY": "247_5139",
    "GNY": "279_34",
    "MLX": "260_22",
    "KZR": "259_5145",
    "AFY": "14410_5522",
    "KCO": "257_5141",
    "AYDN": "3132_1543",
    "RZV": "269_5163",
    "OGU": "268_27",
    "NAV": "266_26",
    "KFS": "253_5140",
    "NOP": "273_30",
    "ISE": "248_17",
    "ONQ": "283_5146",
    "TJK": "276_5144",
    "BAL": "288_36",
    "MQM": "263_24",
    "NKT": "289_5150",
    "IGD": "292_5148",
    "MSR": "265_25",
    "USQ": "280_5156",
    "TEQ": "506_32",
    "SXZ": "272_29",
    "JFK": "3441_1946",
    "EWR": "3434_1938",
    "LAX": "6587_363",
    "MIA": "3332_1785",
    "ORD": "3356_1834",
    "SFO": "1885_136",
    "IAD": "4077_2659",
    "BOS": "3390_1882",
    "YYZ": "2028_312",
    "YUL": "2025_307",
    "CDG": "2333_654",
    "ORY": "2333_655",
    "LHR": "2395_732",
    "STN": "2395_733",
    "FCO": "2572_935",
    "CIA": "2572_934",
    "MXP": "5355_3961",
    "LIN": "5355_946",
    "VCE": "2568_928",
    "BER": "303_5162",
    "AMS": "2836_1227",
    "BRU": "1938_204",
    "CRL": "4596_3194",
    "VIE": "1912_170",
    "PRG": "334_58",
    "BUD": "305_47",
    "BCN": "2296_613",
    "MAD": "2289_605",
    "FRA": "3576_2131",
    "MUC": "2205_506",
    "ZRH": "2054_344",
    "GVA": "5342_3948",
    "BSL": "6520_5152",
    "DUS": "2211_514",
    "CGN": "3578_2133",
    "STR": "2202_503",
    "HAM": "2209_511",
    "NCE": "2337_659",
    "SVO": "3029_1433",
    "VKO": "3029_1434",
    "SKG": "336_59",
    "ATH": "298_39",
    "SOF": "337_60",
    "PDV": "8631_57",
    "VAR": "343_65",
    "BUS": "302_42",
    "TBS": "341_63",
    "GYD": "301_41",
    "SKP": "1814_1105",
    "DXB": "1836_70",
    "DOH": "3004_5651",
    "RUH": "3072_1479",
    "JED": "6278_4892",
    "HND": "2609_979",
    "NRT": "2609_978",
    "SIN": "3120_1530",
    "BKK": "3237_1653",
    "ICN": "2660_1040",
    "DPS": "2498_856",
}


def resolve_obilet_airport_id(iata_code: str, fallback_query: str = "") -> str:
    """IATA kodunu (örn: ZRH, SAW, IST, EDO) Obilet gerçek havalimanı ID'sine (örn: 2054_344) çevirir."""
    code = (iata_code or "").upper().strip()
    if code in OBILET_AIRPORT_IDS:
        return OBILET_AIRPORT_IDS[code]
    for q in [code, (fallback_query or "").split("(")[0].strip()]:
        if not q:
            continue
        try:
            import httpx
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Referer": "https://www.obilet.com/ucak-bileti",
                "Content-Type": "application/json",
            }
            with httpx.Client(headers=headers, timeout=3.5) as client:
                r = client.post("https://www.obilet.com/json/ucak-duraklari", json={"query": q, "page": 1, "element": "origin"})
                if r.status_code == 200:
                    items = r.json().get("items") or []
                    exact = next((x for x in items if x.get("refCode") == code), None)
                    chosen = exact or (items[0] if items else None)
                    if chosen and chosen.get("id"):
                        OBILET_AIRPORT_IDS[code] = chosen["id"]
                        return chosen["id"]
        except Exception:
            pass
    return ""


def build_obilet_flight_url(
    from_code: str,
    to_code: str,
    departure_date: str,
    return_date: str = None,
    is_round: bool = False,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: str = "economy",
    orig_slug: str = "",
    dest_slug: str = "",
) -> str:
    """
    Obilet'in statik SEO sayfası (/ucak-bileti/zurih-istanbul) yerine doğrudan seçilen tarihin
    canlı uçuş sonuçları ekranına (/ucuslar/2054_344-350_67/20261107/1a/economy/all) giden URL'i üretir.
    """
    orig_id = resolve_obilet_airport_id(from_code, orig_slug)
    dest_id = resolve_obilet_airport_id(to_code, dest_slug)

    dep_compact = (departure_date or "").replace("-", "").strip()
    ret_compact = (return_date or "").replace("-", "").strip() if (is_round and return_date) else ""

    pax_parts = [f"{max(1, int(adults or 1))}a"]
    if int(children or 0) > 0:
        pax_parts.append(f"{int(children)}c")
    if int(infants or 0) > 0:
        pax_parts.append(f"{int(infants)}b")
    pax_seg = "_".join(pax_parts)

    cabin_seg = "business" if str(cabin_class or "").lower() == "business" else "economy"

    if orig_id and dest_id and len(dep_compact) == 8:
        date_seg = f"{dep_compact}-{ret_compact}" if (is_round and len(ret_compact) == 8) else dep_compact
        return f"https://www.obilet.com/ucuslar/{orig_id}-{dest_id}/{date_seg}/{pax_seg}/{cabin_seg}/all"

    # Yedek URL
    ob_orig = "istanbul" if orig_slug.startswith("istanbul") else (orig_slug or from_code.lower())
    ob_dest = "istanbul" if dest_slug.startswith("istanbul") else (dest_slug or to_code.lower())
    return f"https://www.obilet.com/ucak-bileti/{ob_orig}-{ob_dest}"

