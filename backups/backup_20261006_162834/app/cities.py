"""
Türkiye Şehirleri, Havalimanı (IATA) Kodları, TCDD Gar Kodları ve Otobüs Arama Bilgileri
"""

TURKEY_CITIES = [
    {"name": "İstanbul", "slug": "istanbul", "iata": "IST", "alt_iata": "SAW", "train_station": "İstanbul (Söğütlüçeşme/Halkalı)", "has_airport": True, "has_train": True},
    {"name": "Ankara", "slug": "ankara", "iata": "ESB", "train_station": "Ankara Gar (YHT)", "has_airport": True, "has_train": True},
    {"name": "İzmir", "slug": "izmir", "iata": "ADB", "train_station": "İzmir (Basmane)", "has_airport": True, "has_train": True},
    {"name": "Antalya", "slug": "antalya", "iata": "AYT", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Adana", "slug": "adana", "iata": "ADA", "train_station": "Adana Gar", "has_airport": True, "has_train": True},
    {"name": "Trabzon", "slug": "trabzon", "iata": "TZX", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Bursa", "slug": "bursa", "iata": "YEI", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Eskişehir", "slug": "eskisehir", "iata": "AOE", "train_station": "Eskişehir Gar (YHT)", "has_airport": True, "has_train": True},
    {"name": "Konya", "slug": "konya", "iata": "KYA", "train_station": "Konya Gar (YHT)", "has_airport": True, "has_train": True},
    {"name": "Gaziantep", "slug": "gaziantep", "iata": "GZT", "train_station": "Gaziantep Gar", "has_airport": True, "has_train": True},
    {"name": "Diyarbakır", "slug": "diyarbakir", "iata": "DIY", "train_station": "Diyarbakır Gar", "has_airport": True, "has_train": True},
    {"name": "Samsun", "slug": "samsun", "iata": "SZF", "train_station": "Samsun Gar", "has_airport": True, "has_train": True},
    {"name": "Kayseri", "slug": "kayseri", "iata": "ASR", "train_station": "Kayseri Gar", "has_airport": True, "has_train": True},
    {"name": "Bodrum (Muğla)", "slug": "bodrum", "iata": "BJV", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Dalaman (Muğla)", "slug": "dalaman", "iata": "DLM", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Van", "slug": "van", "iata": "VAN", "train_station": "Van İskele", "has_airport": True, "has_train": True},
    {"name": "Erzurum", "slug": "erzurum", "iata": "ERZ", "train_station": "Erzurum Gar", "has_airport": True, "has_train": True},
    {"name": "Sivas", "slug": "sivas", "iata": "VAS", "train_station": "Sivas Gar (YHT)", "has_airport": True, "has_train": True},
    {"name": "Kars", "slug": "kars", "iata": "KSY", "train_station": "Kars Gar (Doğu Ekspresi)", "has_airport": True, "has_train": True},
    {"name": "Mersin", "slug": "mersin", "iata": "COV", "train_station": "Mersin Gar", "has_airport": True, "has_train": True},
    {"name": "Denizli", "slug": "denizli", "iata": "DNZ", "train_station": "Denizli Gar", "has_airport": True, "has_train": True},
    {"name": "Hatay", "slug": "hatay", "iata": "HTY", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Şanlıurfa", "slug": "sanliurfa", "iata": "GNY", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Malatya", "slug": "malatya", "iata": "MLX", "train_station": "Malatya Gar", "has_airport": True, "has_train": True},
    {"name": "Çanakkale", "slug": "canakkale", "iata": "CKZ", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Balıkesir", "slug": "balikesir", "iata": "BZI", "train_station": "Balıkesir Gar", "has_airport": True, "has_train": True},
    {"name": "Kütahya", "slug": "kutahya", "iata": "KZR", "train_station": "Kütahya Gar", "has_airport": True, "has_train": True},
    {"name": "Afyonkarahisar", "slug": "afyon", "iata": "AFY", "train_station": "Afyon Ali Çetinkaya Gar", "has_airport": False, "has_train": True},
    {"name": "Edirne", "slug": "edirne", "iata": None, "train_station": "Edirne Gar", "has_airport": False, "has_train": True},
    {"name": "Kocaeli (İzmit)", "slug": "kocaeli", "iata": "KCO", "train_station": "İzmit YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Sakarya (Adapazarı)", "slug": "sakarya", "iata": None, "train_station": "Arifiye YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Bilecik", "slug": "bilecik", "iata": None, "train_station": "Bilecik YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Karaman", "slug": "karaman", "iata": None, "train_station": "Karaman YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Yozgat", "slug": "yozgat", "iata": None, "train_station": "Yozgat YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Kırıkkale", "slug": "kirikkale", "iata": None, "train_station": "Kırıkkale YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Aydın", "slug": "aydin", "iata": "AYDN", "train_station": "Aydın Gar", "has_airport": False, "has_train": True},
    {"name": "Rize / Artvin", "slug": "rize", "iata": "RZV", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Ordu / Giresun", "slug": "ordu", "iata": "OGU", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Nevşehir (Kapadokya)", "slug": "nevsehir", "iata": "NAV", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Kastamonu", "slug": "kastamonu", "iata": "KFS", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Sinop", "slug": "sinop", "iata": "NOP", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Isparta", "slug": "isparta", "iata": "ISE", "train_station": "Isparta Gar", "has_airport": True, "has_train": True},
    {"name": "Bolu", "slug": "bolu", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Zonguldak", "slug": "zonguldak", "iata": "ONQ", "train_station": "Zonguldak Gar", "has_airport": True, "has_train": True},
    {"name": "Tokat", "slug": "tokat", "iata": "TJK", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Amasya", "slug": "amasya", "iata": "MZH", "train_station": "Amasya Gar", "has_airport": True, "has_train": True},
    {"name": "Elazığ", "slug": "elazig", "iata": "EZS", "train_station": "Elazığ Gar", "has_airport": True, "has_train": True},
    {"name": "Batman", "slug": "batman", "iata": "BAL", "train_station": "Batman Gar", "has_airport": True, "has_train": True},
    {"name": "Mardin", "slug": "mardin", "iata": "MQM", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Şırnak", "slug": "sirnak", "iata": "NKT", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Hakkari (Yüksekova)", "slug": "hakkari", "iata": "YKO", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Iğdır", "slug": "igdir", "iata": "IGD", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Ağrı", "slug": "agri", "iata": "AJI", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Bingöl", "slug": "bingol", "iata": "BGG", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Muş", "slug": "mus", "iata": "MSR", "train_station": "Muş Gar", "has_airport": True, "has_train": True},
    {"name": "Uşak", "slug": "usak", "iata": "USQ", "train_station": "Uşak Gar", "has_airport": True, "has_train": True},
    {"name": "Manisa", "slug": "manisa", "iata": None, "train_station": "Manisa Gar", "has_airport": False, "has_train": True},
    {"name": "Tekirdağ", "slug": "tekirdag", "iata": "TEQ", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Yalova", "slug": "yalova", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Düzce", "slug": "duzce", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Bartın", "slug": "bartin", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Karabük", "slug": "karabuk", "iata": None, "train_station": "Karabük Gar", "has_airport": False, "has_train": True},
    {"name": "Çankırı", "slug": "cankiri", "iata": None, "train_station": "Çankırı Gar", "has_airport": False, "has_train": True},
    {"name": "Kırşehir", "slug": "kirsehir", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Niğde", "slug": "nigde", "iata": None, "train_station": "Niğde Gar", "has_airport": False, "has_train": True},
    {"name": "Aksaray", "slug": "aksaray", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Karaman", "slug": "karaman", "iata": None, "train_station": "Karaman YHT Gar", "has_airport": False, "has_train": True},
    {"name": "Burdur", "slug": "burdur", "iata": None, "train_station": "Burdur Gar", "has_airport": False, "has_train": True},
    {"name": "Osmaniye", "slug": "osmaniye", "iata": None, "train_station": "Osmaniye Gar", "has_airport": False, "has_train": True},
    {"name": "Kilis", "slug": "kilis", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Adıyaman", "slug": "adiyaman", "iata": "ADF", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Siirt", "slug": "siirt", "iata": "SXZ", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Bitlis", "slug": "bitlis", "iata": None, "train_station": "Tatvan Gar", "has_airport": False, "has_train": True},
    {"name": "Tunceli", "slug": "tunceli", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Bayburt", "slug": "bayburt", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Gümüşhane", "slug": "gumushane", "iata": None, "train_station": None, "has_airport": False, "has_train": False},
    {"name": "Artvin", "slug": "artvin", "iata": "RZV", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Giresun", "slug": "giresun", "iata": "OGU", "train_station": None, "has_airport": True, "has_train": False},
    {"name": "Kırklareli", "slug": "kirklareli", "iata": None, "train_station": None, "has_airport": False, "has_train": False}
]

def find_city(city_name: str):
    if not city_name:
        return None
    city_name_clean = city_name.strip().lower()
    # 1. Tam eşleşme (name veya slug)
    for c in TURKEY_CITIES:
        if c["name"].lower() == city_name_clean or c["slug"].lower() == city_name_clean:
            return c
    # 2. Parantez içi veya alt dize eşleşmesi (örn: "bodrum" -> "Bodrum (Muğla)")
    for c in TURKEY_CITIES:
        if city_name_clean in c["name"].lower() or c["name"].lower().startswith(city_name_clean):
            return c
    return None

def get_cities_by_transport(transport_type: str = "all"):
    """Seçilen seyahat moduna uygun geçerli şehirleri filtreler"""
    if transport_type == "flight":
        return [c for c in TURKEY_CITIES if c.get("has_airport")]
    elif transport_type == "train":
        return [c for c in TURKEY_CITIES if c.get("has_train")]
    return TURKEY_CITIES
