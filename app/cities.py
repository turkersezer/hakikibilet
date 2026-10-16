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
    {"name": "Bodrum (Muğla)", "slug": "bodrum", "iata": "BJV", "train_station": None, "has_airport": True, "has_train": False, "lat": 37.0344, "lng": 27.4305},
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
    {"name": "Balıkesir", "slug": "balikesir", "iata": "BZI", "train_station": "Balıkesir Gar", "has_airport": True, "has_train": True, "lat": 39.6484, "lng": 27.8826},
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
    {"name": "Uşak", "slug": "usak", "iata": "USQ", "train_station": "Uşak Gar", "has_airport": True, "has_train": True, "lat": 38.6823, "lng": 29.4082},
    {"name": "Manisa", "slug": "manisa", "iata": None, "train_station": "Manisa Gar", "has_airport": False, "has_train": True, "lat": 38.6191, "lng": 27.4289,
     "nearest_domestic_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "45 dk", "transport": "bus_or_train"},
     "nearest_intl_hub": {"name": "İzmir Adnan Menderes (ADB)", "iata": "ADB", "city": "İzmir", "duration": "45 dk", "transport": "bus_or_train"}},
    {"name": "Tekirdağ", "slug": "tekirdag", "iata": "TEQ", "train_station": None, "has_airport": True, "has_train": False, "lat": 40.9833, "lng": 27.5167},
    {"name": "Yalova", "slug": "yalova", "iata": None, "train_station": None, "has_airport": False, "has_train": False, "lat": 40.6500, "lng": 29.2667,
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
     "nearest_intl_hub": {"name": "İstanbul Havalimanı (IST)", "iata": "IST", "city": "İstanbul", "duration": "2 sa", "transport": "bus"}}
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
    {"name": "Paris (CDG/ORY)", "slug": "paris", "country": "Fransa", "region": "Avrupa", "iata": "CDG", "alt_iata": "ORY", "train_station": "Paris Gare du Nord (Eurostar/TGV)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Londra (LHR/STN)", "slug": "londra", "country": "İngiltere", "region": "Avrupa", "iata": "LHR", "alt_iata": "STN", "train_station": "London St Pancras Int (Eurostar)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Roma (FCO)", "slug": "roma", "country": "İtalya", "region": "Avrupa", "iata": "FCO", "alt_iata": "CIA", "train_station": "Roma Termini (Frecciarossa)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Milano (MXP)", "slug": "milano", "country": "İtalya", "region": "Avrupa", "iata": "MXP", "alt_iata": "LIN", "train_station": "Milano Centrale (Frecciarossa)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Venedik (VCE)", "slug": "venedik", "country": "İtalya", "region": "Avrupa", "iata": "VCE", "train_station": "Venezia Santa Lucia (Frecciarossa)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Berlin (BER)", "slug": "berlin", "country": "Almanya", "region": "Avrupa", "iata": "BER", "train_station": "Berlin Hbf (ICE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Amsterdam (AMS)", "slug": "amsterdam", "country": "Hollanda", "region": "Avrupa", "iata": "AMS", "train_station": "Amsterdam Centraal (Eurostar)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Brüksel (BRU)", "slug": "bruksel", "country": "Belçika", "region": "Avrupa", "iata": "BRU", "alt_iata": "CRL", "train_station": "Bruxelles-Midi (Eurostar)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Viyana (VIE)", "slug": "viyana", "country": "Avusturya", "region": "Avrupa", "iata": "VIE", "train_station": "Wien Hbf (ÖBB Railjet)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Prag (PRG)", "slug": "prag", "country": "Çekya", "region": "Avrupa", "iata": "PRG", "train_station": "Praha hlavní nádraží", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Budapeşte (BUD)", "slug": "budapeste", "country": "Macaristan", "region": "Avrupa", "iata": "BUD", "train_station": "Budapest Keleti", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Barselona (BCN)", "slug": "barselona", "country": "İspanya", "region": "Avrupa", "iata": "BCN", "train_station": "Barcelona Sants (AVE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Madrid (MAD)", "slug": "madrid", "country": "İspanya", "region": "Avrupa", "iata": "MAD", "train_station": "Madrid Puerta de Atocha (AVE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Frankfurt (FRA)", "slug": "frankfurt", "country": "Almanya", "region": "Avrupa", "iata": "FRA", "train_station": "Frankfurt (Main) Hbf (ICE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Münih (MUC)", "slug": "munih", "country": "Almanya", "region": "Avrupa", "iata": "MUC", "train_station": "München Hbf (ICE)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Zürih (ZRH)", "slug": "zurih", "country": "İsviçre", "region": "Avrupa", "iata": "ZRH", "train_station": "Zürich HB (SBB)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Nice (NCE)", "slug": "nice", "country": "Fransa", "region": "Avrupa", "iata": "NCE", "train_station": "Gare de Nice-Ville (TER Monaco)", "has_airport": True, "has_train": True, "is_international": True},
    {"name": "Monaco / Monte Carlo", "slug": "monaco", "country": "Monaco", "region": "Avrupa", "iata": "NCE", "train_station": "Gare de Monaco-Monte Carlo", "has_airport": True, "nearest_airport_iata": "NCE", "nearest_airport_name": "Nice Côte d'Azur (NCE)", "has_train": True, "is_international": True},

    # 🚌 Komşu Ülkeler (Uçak + Karayolu Otobüs Seferleri Aktif)
    {"name": "Selanik (SKG)", "slug": "selanik", "country": "Yunanistan", "region": "Balkanlar", "iata": "SKG", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Atina (ATH)", "slug": "atina", "country": "Yunanistan", "region": "Balkanlar", "iata": "ATH", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Sofya (SOF)", "slug": "sofya", "country": "Bulgaristan", "region": "Balkanlar", "iata": "SOF", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Filibe / Plovdiv (PDV)", "slug": "filibe", "country": "Bulgaristan", "region": "Balkanlar", "iata": "PDV", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Varna (VAR)", "slug": "varna", "country": "Bulgaristan", "region": "Balkanlar", "iata": "VAR", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Batum (BUS)", "slug": "batum", "country": "Gürcistan", "region": "Kafkaslar", "iata": "BUS", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Tiflis (TBS)", "slug": "tiflis", "country": "Gürcistan", "region": "Kafkaslar", "iata": "TBS", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},
    {"name": "Bakü (GYD)", "slug": "baku", "country": "Azerbaycan", "region": "Kafkaslar", "iata": "GYD", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Üsküp (SKP)", "slug": "uskup", "country": "Kuzey Makedonya", "region": "Balkanlar", "iata": "SKP", "has_airport": True, "has_train": False, "has_bus": True, "is_international": True, "is_overland_neighbor": True},

    # 🇦🇪 Orta Doğu & Körfez
    {"name": "Dubai (DXB)", "slug": "dubai", "country": "BAE", "region": "Orta Doğu", "iata": "DXB", "has_airport": True, "has_train": False, "is_international": True},
    {"name": "Doha (DOH)", "slug": "doha", "country": "Katar", "region": "Orta Doğu", "iata": "DOH", "has_airport": True, "has_train": False, "is_international": True},
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
    {"name": "Sakız Adası (Chios)", "slug": "sakiz-adasi", "port_code": "JKH", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "requires_visa": True, "lat": 38.3680, "lng": 26.1360},
    {"name": "Bodrum Limanı (Muğla)", "slug": "bodrum-liman", "port_code": "BXN", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 37.0310, "lng": 27.4290},
    {"name": "Kos Adası (İstanköy)", "slug": "kos-adasi", "port_code": "KGS", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "requires_visa": True, "lat": 36.8930, "lng": 27.2880},
    {"name": "Ayvalık Limanı (Balıkesir)", "slug": "ayvalik", "port_code": "AYV", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 39.3190, "lng": 26.6930},
    {"name": "Midilli Adası (Lesvos)", "slug": "midilli-adasi", "port_code": "MJT", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "requires_visa": True, "lat": 39.1050, "lng": 26.5550},
    {"name": "Kuşadası Limanı (Aydın)", "slug": "kusadasi", "port_code": "KUS", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 37.8610, "lng": 27.2600},
    {"name": "Samos Adası (Sisam)", "slug": "samos-adasi", "port_code": "SMI", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "requires_visa": True, "lat": 37.7550, "lng": 26.9770},
    {"name": "Fethiye Limanı (Muğla)", "slug": "fethiye", "port_code": "FTH", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 36.6210, "lng": 29.1120},
    {"name": "Rodos Adası (Rhodes)", "slug": "rodos-adasi", "port_code": "RHO", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "requires_visa": True, "lat": 36.4340, "lng": 28.2170},
    {"name": "Marmaris Limanı (Muğla)", "slug": "marmaris", "port_code": "MRM", "region": "Ege", "is_ferry": True, "country": "Türkiye", "lat": 36.8520, "lng": 28.2740},
    {"name": "Kaş Limanı (Antalya)", "slug": "kas", "port_code": "KAS", "region": "Akdeniz", "is_ferry": True, "country": "Türkiye", "lat": 36.1990, "lng": 29.6380},
    {"name": "Meis Adası (Kastellorizo)", "slug": "meis-adasi", "port_code": "KZS", "region": "Yunan Adaları", "is_ferry": True, "country": "Yunanistan", "requires_visa": True, "lat": 36.1480, "lng": 29.5930}
]

ALL_LOCATIONS = TURKEY_CITIES + INTERNATIONAL_CITIES + FERRY_PORTS

def find_city(city_name: str):
    return find_location(city_name)

def find_location(location_name: str):
    if not location_name:
        return None
    raw = location_name.strip()
    loc_clean = raw.lower()
    
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

    # 1. Parantez içindeki IATA / Liman Kodlarını öncelikli kontrol et (Örn: "Antalya (AYT)")
    codes = re.findall(r'\b[A-Za-z]{3}\b', raw)
    for code in codes:
        c_code = code.upper()
        for c in ALL_LOCATIONS:
            if (c.get("iata") == c_code or 
                c.get("alt_iata") == c_code or 
                c.get("port_code") == c_code):
                return c

    # 1. Tam eşleşme (name, slug veya iata)
    for c in ALL_LOCATIONS:
        if (c.get("name", "").lower() == loc_clean or 
            c.get("slug", "").lower() == loc_clean or 
            (c.get("iata") and c.get("iata", "").lower() == loc_clean)):
            return c

    # 2. Parantezleri temizleyip eşleştir (Örn: "Antalya (AYT)" -> "antalya")
    base_name = re.sub(r'\(.*?\)', '', loc_clean).strip()
    if base_name:
        for c in ALL_LOCATIONS:
            c_name = c.get("name", "").lower()
            c_slug = c.get("slug", "").lower()
            if base_name == c_name or base_name == c_slug:
                return c
            
    # 3. Başlangıç veya alt dize eşleşmesi (çift yönlü esnek eşleşme)
    for c in ALL_LOCATIONS:
        c_name = c.get("name", "").lower()
        if (loc_clean in c_name or c_name in loc_clean or
            (base_name and (base_name in c_name or c_name in base_name))):
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
        tr_buses = TURKEY_CITIES
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
