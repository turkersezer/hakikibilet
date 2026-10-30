import urllib.parse
import urllib.request
import unicodedata
import json
import re
import time
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from app.config import settings
from app.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

class HotelService:
    """
    MODÜL: Akıllı Canlı Otel ve Konaklama Metasearch Servisi
    - RapidAPI Booking.com Canlı Veri Motoru (Gerçek otel adları, puanlar, HD fotoğraflar ve canlı fiyatlar)
    - 2 Saatlik Akıllı Önbellek (Kota tasarrufu ve ultra hızlı yanıt)
    - Yurt dışı / Ada güvenliği (Enuygun 404 hatasını önlemek için adalarda ve yurt dışında sadece Booking & Agoda)
    - Hatasız Yedekleme (API erişilemezse kesintisiz parametrik Booking.com yönlendirmesi)
    """

    # Canlı sorgu önbelleği: {cache_key: (timestamp, data)}
    _HOTEL_CACHE: Dict[str, tuple] = {}
    _ENUYGUN_DIRECT_SLUG_CACHE: Dict[str, Optional[str]] = {}
    _ETSTUR_DIRECT_SLUG_CACHE: Dict[str, Optional[str]] = {}
    _CACHE_TTL = 7200  # 2 saat

    @classmethod
    def sanitize_hotel_city_name(cls, raw_city: str) -> str:
        """
        Havalimanı, feribot iskelesi, liman, tren garı ve otogar eklerini temizleyerek
        saf şehir/belde adını döndürür (örn. 'Fethiye Limanı (Muğla)' -> 'Fethiye',
        'Pendik (İstanbul - İDO)' -> 'İstanbul', 'Mudanya (Bursa İskelesi - BUDO)' -> 'Bursa').
        """
        raw = str(raw_city or "").strip()
        if not raw:
            return "İstanbul"

        raw_lower = raw.lower()
        # Banliyö iskele/havalimanı eşleştirmeleri -> Ana Büyükşehir
        if any(k in raw_lower for k in ["sabiha gökçen", "sabiha gokcen", "yenikapı", "yenikapi", "pendik", "kabataş", "kabatas", "bostancı", "bostanci", "kadıköy", "kadikoy", "eminönü", "eminonu", "sirkeci", "harem", "bakırköy", "bakirkoy", "halkalı", "halkali", "söğütlüçeşme", "sogutlucesme"]):
            return "İstanbul"
        if any(k in raw_lower for k in ["mudanya", "güzelyalı", "guzelyali", "budo"]):
            return "Bursa"
        if any(k in raw_lower for k in ["esenboğa", "esenboga", "eryaman"]):
            return "Ankara"
        if any(k in raw_lower for k in ["adnan menderes", "alsancak", "karşıyaka", "karsiyaka", "konak"]):
            return "İzmir"
        if "çukurova" in raw_lower or "cukurova" in raw_lower or "şakirpaşa" in raw_lower:
            return "Adana"

        base = raw.split("(")[0].strip()
        if "/" in base:
            base = base.split("/")[0].strip()
        if " - " in base:
            base = base.split(" - ")[0].strip()

        # Terminal / İskele / Liman / Havalimanı son eklerini temizle
        base = re.sub(
            r"\s+(Feribot\s+İskelesi|Deniz\s+Otobüsü\s+İskelesi|İskelesi|İskele|Limanı|Liman|Havalimanı|Havaalanı|Airport|Otogarı|Otogar|YHT\s+Garı|Tren\s+Garı|Garı|İstasyonu)\b.*$",
            "",
            base,
            flags=re.I,
        ).strip()

        cleaned = base or raw.split("(")[0].strip()
        if cleaned and (cleaned.islower() or cleaned.isupper()):
            words = []
            for w in cleaned.split():
                first_c = w[0]
                rest_c = w[1:].replace("I", "ı").replace("İ", "i").lower()
                if first_c in ("i", "İ"):
                    first_up = "İ"
                elif first_c in ("ı", "I"):
                    first_up = "I"
                else:
                    first_up = first_c.upper()
                words.append(first_up + rest_c)
            cleaned = " ".join(words)
        return cleaned

    # Trip.com Doğrulanmış City ID Haritası (Asla '0 properties found' veya boş arama kutusu vermez)
    TRIP_CITY_ID_MAP: Dict[str, Dict[str, Any]] = {
        "istanbul": {"id": 532, "name": "İstanbul"},
        "ankara": {"id": 1218, "name": "Ankara"},
        "izmir": {"id": 1216, "name": "İzmir"},
        "antalya": {"id": 1217, "name": "Antalya"},
        "bodrum": {"id": 1761, "name": "Bodrum"},
        "fethiye": {"id": 3773, "name": "Fethiye"},
        "marmaris": {"id": 3775, "name": "Marmaris"},
        "selimiye": {"id": 102640710, "name": "Selimiye"},
        "bozburun": {"id": 245546, "name": "Bozburun"},
        "hisaronu": {"id": 3775, "name": "Hisarönü Marmaris"},
        "icmeler": {"id": 3775, "name": "İçmeler Marmaris"},
        "turunc": {"id": 3775, "name": "Turunç Marmaris"},
        "akyaka": {"id": 243958, "name": "Akyaka"},
        "dalyan": {"id": 40485, "name": "Dalyan"},
        "gocek": {"id": 40500, "name": "Göcek"},
        "oludeniz": {"id": 6793045, "name": "Ölüdeniz"},
        "dalaman": {"id": 1749, "name": "Dalaman"},
        "datca": {"id": 9540, "name": "Datça"},
        "cesme": {"id": 3772, "name": "Çeşme"},
        "alacati": {"id": 243200, "name": "Alaçatı"},
        "ilica": {"id": 3772, "name": "Ilıca Çeşme"},
        "sigacik": {"id": 1216, "name": "Sığacık Seferihisar"},
        "urla": {"id": 40538, "name": "Urla"},
        "kusadasi": {"id": 40519, "name": "Kuşadası"},
        "didim": {"id": 40486, "name": "Didim"},
        "aydin": {"id": 52947, "name": "Aydın"},
        "ayvalik": {"id": 40475, "name": "Ayvalık"},
        "cunda": {"id": 40475, "name": "Cunda Ayvalık"},
        "alanya": {"id": 40464, "name": "Alanya"},
        "kemer": {"id": 40513, "name": "Kemer"},
        "olimpos": {"id": 40513, "name": "Olimpos Kemer"},
        "cirali": {"id": 40513, "name": "Çıralı Kemer"},
        "adrasan": {"id": 40513, "name": "Adrasan"},
        "belek": {"id": 1217, "name": "Belek Antalya"},
        "side": {"id": 1217, "name": "Side Antalya"},
        "kas": {"id": 40510, "name": "Kaş"},
        "kalkan": {"id": 40510, "name": "Kalkan Kaş"},
        "trabzon": {"id": 1760, "name": "Trabzon"},
        "uzungol": {"id": 53133, "name": "Uzungöl"},
        "caykara": {"id": 240979, "name": "Çaykara"},
        "rize": {"id": 40521, "name": "Rize"},
        "ayder": {"id": 246161, "name": "Ayder Çamlıhemşin"},
        "camlihemsin": {"id": 246161, "name": "Çamlıhemşin"},
        "samsun": {"id": 1758, "name": "Samsun"},
        "ordu": {"id": 20002, "name": "Ordu"},
        "giresun": {"id": 53013, "name": "Giresun"},
        "sinop": {"id": 20797, "name": "Sinop"},
        "artvin": {"id": 61168, "name": "Artvin"},
        "kars": {"id": 7238, "name": "Kars"},
        "sarikamis": {"id": 53103, "name": "Sarıkamış"},
        "erzurum": {"id": 1754, "name": "Erzurum"},
        "palandoken": {"id": 1754, "name": "Palandöken Erzurum"},
        "van": {"id": 1750, "name": "Van"},
        "agri": {"id": 4263, "name": "Ağrı"},
        "igdir": {"id": 53021, "name": "Iğdır"},
        "erzincan": {"id": 5280, "name": "Erzincan"},
        "malatya": {"id": 1752, "name": "Malatya"},
        "elazig": {"id": 6723, "name": "Elazığ"},
        "gaziantep": {"id": 1753, "name": "Gaziantep"},
        "sanliurfa": {"id": 40537, "name": "Şanlıurfa"},
        "mardin": {"id": 5317, "name": "Mardin"},
        "diyarbakir": {"id": 1755, "name": "Diyarbakır"},
        "adana": {"id": 1748, "name": "Adana"},
        "mersin": {"id": 9942, "name": "Mersin"},
        "hatay": {"id": 97804, "name": "Hatay"},
        "kahramanmaras": {"id": 20795, "name": "Kahramanmaraş"},
        "kayseri": {"id": 1756, "name": "Kayseri"},
        "erciyes": {"id": 1756, "name": "Erciyes Kayseri"},
        "nevsehir": {"id": 7732, "name": "Nevşehir"},
        "kapadokya": {"id": 7732, "name": "Kapadokya"},
        "urgup": {"id": 9169, "name": "Ürgüp"},
        "goreme": {"id": 9660, "name": "Göreme"},
        "avanos": {"id": 7732, "name": "Avanos"},
        "konya": {"id": 1757, "name": "Konya"},
        "eskisehir": {"id": 9585, "name": "Eskişehir"},
        "bursa": {"id": 4898, "name": "Bursa"},
        "uludag": {"id": 4898, "name": "Uludağ Bursa"},
        "sapanca": {"id": 40533, "name": "Sapanca"},
        "masukiye": {"id": 40315, "name": "Maşukiye Kartepe"},
        "kartepe": {"id": 40315, "name": "Kartepe"},
        "agva": {"id": 40461, "name": "Ağva"},
        "sile": {"id": 40535, "name": "Şile"},
        "abant": {"id": 705625, "name": "Abant Bolu"},
        "kartalkaya": {"id": 705625, "name": "Kartalkaya Bolu"},
        "canakkale": {"id": 7636, "name": "Çanakkale"},
        "bozcaada": {"id": 40483, "name": "Bozcaada"},
        "gokceada": {"id": 92396, "name": "Gökçeada"},
        "assos": {"id": 227517, "name": "Assos Ayvacık"},
        "behramkale": {"id": 227517, "name": "Behramkale Assos"},
        "ayvacik": {"id": 227517, "name": "Ayvacık"},
        "kucukkuyu": {"id": 227517, "name": "Küçükkuyu"},
        "balikesir": {"id": 4999, "name": "Balıkesir"},
        "edremit": {"id": 684699, "name": "Edremit"},
        "akcay": {"id": 684699, "name": "Akçay Edremit"},
        "altinoluk": {"id": 684699, "name": "Altınoluk Edremit"},
        "denizli": {"id": 1762, "name": "Denizli"},
        "pamukkale": {"id": 3776, "name": "Pamukkale"},
        "mugla": {"id": 97783, "name": "Muğla"},
        "isparta": {"id": 53024, "name": "Isparta"},
        "sivas": {"id": 20798, "name": "Sivas"},
        "tokat": {"id": 53126, "name": "Tokat"},
        "amasya": {"id": 52938, "name": "Amasya"},
        "corum": {"id": 52918, "name": "Çorum"},
        "kastamonu": {"id": 40511, "name": "Kastamonu"},
        "safranbolu": {"id": 7726, "name": "Safranbolu"},
        "amasra": {"id": 40466, "name": "Amasra"},
        "bartin": {"id": 40477, "name": "Bartın"},
        "zonguldak": {"id": 53144, "name": "Zonguldak"},
        "bolu": {"id": 705625, "name": "Bolu"},
        "edirne": {"id": 40471, "name": "Edirne"},
        "tekirdag": {"id": 53125, "name": "Tekirdağ"},
        "kocaeli": {"id": 40315, "name": "Kocaeli"},
        "sakarya": {"id": 40315, "name": "Sakarya"},
        "yalova": {"id": 62336, "name": "Yalova"},
        "afyonkarahisar": {"id": 6660, "name": "Afyonkarahisar"},
        "kutahya": {"id": 20531, "name": "Kütahya"},
        "manisa": {"id": 40522, "name": "Manisa"},
        "batman": {"id": 4512, "name": "Batman"},
        "siirt": {"id": 77925, "name": "Siirt"},
        "sirnak": {"id": 230419, "name": "Şırnak"},
        "hakkari": {"id": 53015, "name": "Hakkari"},
        "bingol": {"id": 233014, "name": "Bingöl"},
        "tunceli": {"id": 53128, "name": "Tunceli"},
        "adiyaman": {"id": 6625, "name": "Adıyaman"},
        "girne": {"id": 40314, "name": "Girne"},
        "lefkosa": {"id": 4191, "name": "Lefkoşa"},
        "gazimagusa": {"id": 84382, "name": "Gazimağusa"},
        "sakiz-adasi": {"id": 7085, "name": "Chios"},
        "sakiz": {"id": 7085, "name": "Chios"},
        "chios": {"id": 7085, "name": "Chios"},
        "rodos-adasi": {"id": 3570, "name": "Rhodes"},
        "rodos": {"id": 3570, "name": "Rhodes"},
        "rhodes": {"id": 3570, "name": "Rhodes"},
        "kos-adasi": {"id": 7159, "name": "Kos"},
        "kos": {"id": 7159, "name": "Kos"},
        "midilli-adasi": {"id": 93173, "name": "Mytilene"},
        "midilli": {"id": 93173, "name": "Mytilene"},
        "lesbos": {"id": 93173, "name": "Mytilene"},
        "samos-adasi": {"id": 5902, "name": "Samos"},
        "samos": {"id": 5902, "name": "Samos"},
        "simi-adasi": {"id": 3570, "name": "Symi Rhodes"},
        "simi": {"id": 3570, "name": "Symi Rhodes"},
        "meis-adasi": {"id": 3570, "name": "Kastellorizo"},
        "meis": {"id": 3570, "name": "Kastellorizo"},
        "paris": {"id": 192, "name": "Paris"},
        "londra": {"id": 338, "name": "Londra"},
        "roma": {"id": 343, "name": "Roma"},
        "milano": {"id": 361, "name": "Milano"},
        "venedik": {"id": 688, "name": "Venedik"},
        "barselona": {"id": 40795, "name": "Barselona"},
        "madrid": {"id": 357, "name": "Madrid"},
        "amsterdam": {"id": 176, "name": "Amsterdam"},
        "berlin": {"id": 193, "name": "Berlin"},
        "munih": {"id": 363, "name": "Münih"},
        "frankfurt": {"id": 250, "name": "Frankfurt"},
        "viyana": {"id": 651, "name": "Viyana"},
        "prag": {"id": 1288, "name": "Prag"},
        "budapeste": {"id": 637, "name": "Budapeşte"},
        "atina": {"id": 710, "name": "Atina"},
        "selanik": {"id": 4327178, "name": "Selanik"},
        "sofya": {"id": 4326612, "name": "Sofya"},
        "bukres": {"id": 674, "name": "Bükreş"},
        "belgrad": {"id": 10257, "name": "Belgrad"},
        "saraybosna": {"id": 10260, "name": "Saraybosna"},
        "uskup": {"id": 4326599, "name": "Üsküp"},
        "tiran": {"id": 36649, "name": "Tiran"},
        "tiflis": {"id": 7612, "name": "Tiflis"},
        "batum": {"id": 4912, "name": "Batum"},
        "baku": {"id": 650, "name": "Bakü"},
        "dubai": {"id": 220, "name": "Dubai"},
        "abu-dabi": {"id": 766, "name": "Abu Dabi"},
        "doha": {"id": 1401, "name": "Doha"},
        "kahire": {"id": 332, "name": "Kahire"},
        "tokyo": {"id": 228, "name": "Tokyo"},
        "seul": {"id": 274, "name": "Seul"},
        "bangkok": {"id": 359, "name": "Bangkok"},
        "new-york": {"id": 633, "name": "New York"},
    }

    # Enuygun Otel Doğrulanmış /otel/bolge/{slug}/ Haritası (Asla /otel/ ana sayfasına düşmez)
    ENUYGUN_HOTEL_SLUG_MAP: Dict[str, str] = {
        "istanbul": "istanbul-1639",
        "ankara": "ankara-386",
        "izmir": "izmir-1665",
        "antalya": "antalya-481",
        "bodrum": "bodrum-745",
        "fethiye": "fethiye-6341134",
        "marmaris": "marmaris-4302",
        "selimiye": "selimiye-6054846",
        "bozburun": "bozburun-6154991",
        "hisaronu": "hisaronu-6054853",
        "icmeler": "icmeler-6054842",
        "turunc": "turunc-6054844",
        "akyaka": "akyaka-city-center-553248633981743303",
        "dalyan": "dalyan-city-center-3000661317",
        "gocek": "gocek-6054856",
        "oludeniz": "oludeniz-6054859",
        "dalaman": "dalaman-1031",
        "datca": "datca-4291",
        "cesme": "cesme-4275",
        "alacati": "alacati-6054832",
        "ilica": "ilica-6127319",
        "sigacik": "sigacik-6140100",
        "urla": "urla-6140101",
        "kusadasi": "kusadasi-4227",
        "didim": "didim-6069857",
        "aydin": "aydin-4488",
        "ayvalik": "ayvalik-4498",
        "cunda": "cunda-adasi-6324180",
        "alanya": "alanya-4671",
        "kemer": "kemer-8281",
        "olimpos": "olimpos-6134144",
        "cirali": "cirali-6049272",
        "adrasan": "adrasan-6134143",
        "belek": "belek-6034717",
        "side": "antalya-481",
        "kas": "kas-6047444",
        "kalkan": "kalkan-6054861",
        "trabzon": "trabzon-3597",
        "uzungol": "uzungol-6157520",
        "caykara": "caykara-6321576",
        "rize": "rize-4473",
        "ayder": "camlihemsin-6144612",
        "camlihemsin": "camlihemsin-6144612",
        "samsun": "samsun-3278",
        "ordu": "ordu-4654",
        "giresun": "giresun-4555",
        "sinop": "sinop-6063189",
        "artvin": "artvin-6323606",
        "kars": "kars-1931",
        "sarikamis": "sarikamis-6323604",
        "erzurum": "erzurum-1161",
        "palandoken": "palandoken-553248635290254679",
        "van": "van-3677",
        "agri": "agri-6063167",
        "igdir": "igdir-6202684",
        "erzincan": "erzincan-1156",
        "malatya": "malatya-2354",
        "elazig": "elazig-1188",
        "gaziantep": "gaziantep-1420",
        "sanliurfa": "sanliurfa-3133",
        "mardin": "mardin-4512",
        "diyarbakir": "diyarbakir-1016",
        "adana": "adana-288",
        "mersin": "mersin-province-553248635458625001",
        "hatay": "hatay-6246842",
        "kahramanmaras": "kahramanmaras-6063186",
        "kayseri": "kayseri-430",
        "erciyes": "erciyes-6323221",
        "nevsehir": "nevsehir-4605",
        "kapadokya": "nevsehir-4605",
        "urgup": "urgup-4423",
        "goreme": "goreme-6224480",
        "avanos": "avanos-6063195",
        "konya": "konya-8367",
        "eskisehir": "eskisehir-7119",
        "bursa": "bursa-6431",
        "uludag": "uludag-6130489",
        "sapanca": "sapanca-6049293",
        "masukiye": "masukiye-6149334",
        "kartepe": "kartepe-553248635290254672",
        "agva": "agva-6046184",
        "sile": "sile-6127677",
        "abant": "abant-6321966",
        "kartalkaya": "bolu-4644",
        "canakkale": "canakkale-857",
        "bozcaada": "bozcaada-6125621",
        "gokceada": "gokceada-6323657",
        "assos": "assos-6134121",
        "behramkale": "assos-6134121",
        "ayvacik": "ayvacik-6323760",
        "kucukkuyu": "kucukkuyu-6134122",
        "balikesir": "balikesir-553248635924013473",
        "edremit": "edremit-6063182",
        "akcay": "akcay-6128011",
        "altinoluk": "altinoluk-6128013",
        "denizli": "denizli-1043",
        "pamukkale": "pamukkale-6063014",
        "mugla": "mugla-4556",
        "isparta": "isparta-4450",
        "sivas": "sivas-3680",
        "tokat": "tokat-4483",
        "amasya": "amasya-4449",
        "corum": "corum-4554",
        "kastamonu": "kastamonu-4578",
        "safranbolu": "safranbolu-4482",
        "amasra": "amasra-6054670",
        "bartin": "bartin-4551",
        "zonguldak": "zonguldak-4416",
        "bolu": "bolu-4644",
        "edirne": "edirne-5280",
        "tekirdag": "tekirdag-5282",
        "kocaeli": "kocaeli-553248635924013345",
        "sakarya": "sakarya-6242347",
        "yalova": "yalova-4946",
        "afyonkarahisar": "afyonkarahisar-6056",
        "kutahya": "kutahya-4458",
        "manisa": "manisa-4490",
        "batman": "batman-493",
        "siirt": "siirt-3339",
        "sirnak": "sirnak-6323236",
        "hakkari": "hakkari-4617",
        "mus": "mus-2428",
        "bingol": "bingol-4616",
        "tunceli": "tunceli-6323547",
        "adiyaman": "adiyaman-4615",
        "girne": "girne",
        "lefkosa": "lefkosa",
        "gazimagusa": "famagusta-6123037",
        "sakiz-adasi": "sakiz-adasi-1703",
        "sakiz": "sakiz-adasi-1703",
        "chios": "sakiz-adasi-1703",
        "rodos-adasi": "rodos-11286",
        "rodos": "rodos-11286",
        "rhodes": "rodos-11286",
        "kos-adasi": "istankoy-1804",
        "kos": "istankoy-1804",
        "midilli-adasi": "lesvos-181073",
        "midilli": "lesvos-181073",
        "lesbos": "lesvos-181073",
        "samos-adasi": "samos-3216",
        "samos": "samos-3216",
        "paris": "paris-2734",
        "londra": "londra-2114",
        "roma": "roma-3023",
        "milano": "milano-2394",
        "venedik": "venedik-3694",
        "barselona": "barselona-513",
        "madrid": "madrid-2198",
        "amsterdam": "amsterdam-378",
        "berlin": "berlin-598",
        "munih": "munih-2491",
        "frankfurt": "frankfurt-1276",
        "viyana": "viyana-3709",
        "prag": "prag-2863",
        "budapeste": "budapeste-795",
        "atina": "atina-438",
        "selanik": "selanik-3186",
        "sofya": "sofya-6050209",
        "bukres": "bukres-6057278",
        "belgrad": "belgrad-6333",
        "saraybosna": "sarajevo-9875",
        "uskup": "uskup-3191",
        "tiran": "tiran-3433",
        "tiflis": "tiflis-3381",
        "batum": "batumi-726",
        "baku": "baku-492",
        "dubai": "dubai-6053839",
    }

    @classmethod
    def resolve_trip_city_meta(
        cls,
        city_clean: str,
        city_slug: str,
        trip_aid: str = "11051531",
        trip_sid: str = "333747492",
    ) -> Optional[Dict[str, Any]]:
        """
        Trip.com City ID haritasında olmayan tüm il ve ilçeleri (örn. Aydın, Manisa, Datça, Amasra vb.)
        Trip.com resmi getHotelKeywords SOA2 servisinden dinamik çözüp önbelleğe alır.
        Eğer ilk dönen kayıt bir otel (tripType == 'H') veya POI ise, controlInfo.regionInfo.basicCityModel.cityId
        üzerinden gerçek şehir ID'sini alır (Asla otel ID'sini cityId olarak kullanmaz).
        """
        meta = cls.TRIP_CITY_ID_MAP.get(city_slug)
        if meta and meta.get("id"):
            return meta

        try:
            body_bytes = json.dumps({
                "queryInfo": {"keyword": city_clean, "actionType": "destination"},
                "head": {
                    "platform": "PC",
                    "cver": "0",
                    "bu": "IBU",
                    "group": "trip",
                    "aid": trip_aid,
                    "sid": trip_sid,
                    "locale": "tr-TR",
                    "region": "TR",
                    "timezone": "3",
                    "currency": "TRY",
                    "isSSR": False,
                },
            }).encode("utf-8")

            rdata = None
            try:
                client = cls._create_primp_client(timeout=3.0)
                resp = client.post(
                    "https://tr.trip.com/restapi/soa2/34951/getHotelKeywords",
                    content=body_bytes,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200 and resp.text:
                    rdata = json.loads(resp.text)
            except Exception:
                req = urllib.request.Request(
                    "https://tr.trip.com/restapi/soa2/34951/getHotelKeywords",
                    data=body_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    rdata = json.loads(resp.read().decode("utf-8", "ignore"))

            if isinstance(rdata, dict):
                kw_list = rdata.get("data", {}).get("mainKeywordList", {}).get("keywords", [])
                fallback_meta = None
                for kw_entry in kw_list:
                    kw_obj = kw_entry.get("keyword") or {}
                    kinfo = kw_obj.get("keywordContentInfo") or {}
                    trip_type = str(kinfo.get("tripType") or "").upper()
                    has_hotel_info = bool((kw_obj.get("hotelInfo") or {}).get("hotelId"))
                    reg_info = (kw_entry.get("controlInfo") or {}).get("regionInfo") or {}
                    basic_city = reg_info.get("basicCityModel") or {}
                    disp_city = reg_info.get("displayCityModel") or {}
                    basic_cid = basic_city.get("cityId")
                    country_name = str(disp_city.get("countryName") or "").strip()

                    kid = kinfo.get("keywordId")
                    kname = kinfo.get("keyword") or kinfo.get("content") or disp_city.get("cityName") or city_clean
                    if not has_hotel_info and trip_type not in ("H", "P", "S") and kid:
                        meta = {"id": int(kid), "name": kname, "country": country_name}
                        cls.TRIP_CITY_ID_MAP[city_slug] = meta
                        return meta
                    elif basic_cid and not fallback_meta:
                        fallback_meta = {
                            "id": int(basic_cid),
                            "name": disp_city.get("cityName") or city_clean,
                            "country": country_name,
                        }
                if fallback_meta:
                    cls.TRIP_CITY_ID_MAP[city_slug] = fallback_meta
                    return fallback_meta
        except Exception as e:
            logger.debug(f"Trip.com dynamic cityId resolve warning ({city_clean}): {e}")

        return None

    @classmethod
    def resolve_trip_hotel_url(
        cls,
        city_clean: str,
        city_slug: str,
        cin: str,
        cout: str,
        guests: int,
        is_international: bool = False,
        trip_aid: str = "11051531",
        trip_sid: str = "333747492",
    ) -> str:
        """
        Trip.com'un /hotels/list SPA ekranında '0 properties found' hatasını önlemek için
        doğrulanmış cityId, searchType=CT, optionId ve searchValue parametreleriyle doğrudan otel listesini açar.
        """
        trip_domain = "www.trip.com" if is_international else "tr.trip.com"
        locale = "en-US" if is_international else "tr-TR"
        meta = cls.resolve_trip_city_meta(city_clean, city_slug, trip_aid=trip_aid, trip_sid=trip_sid)

        q_city = urllib.parse.quote(city_clean)
        if meta and meta.get("id"):
            cid = meta["id"]
            cname = urllib.parse.quote(str(meta.get("name") or city_clean))
            return (
                f"https://{trip_domain}/hotels/list?"
                f"flexType=1&cityId={cid}&cityName={cname}&destName={cname}&searchWord={q_city}"
                f"&searchType=CT&optionId={cid}&searchValue=19%7C{cid}*19*{cid}"
                f"&checkin={cin}&checkout={cout}"
                f"&crn=1&adult={guests}&curr=TRY&locale={locale}"
                f"&Allianceid={trip_aid}&SID={trip_sid}"
            )

        return (
            f"https://{trip_domain}/hotels/list?"
            f"flexType=1&searchWord={q_city}&keyword={q_city}"
            f"&checkin={cin}&checkout={cout}"
            f"&crn=1&adult={guests}&curr=TRY&locale={locale}"
            f"&Allianceid={trip_aid}&SID={trip_sid}"
        )

    @classmethod
    def resolve_enuygun_region_slug(cls, city_clean: str, city_slug: str) -> Optional[str]:
        """
        Enuygun bölge haritasında olmayan tüm il ve ilçelerin gerçek /otel/bolge/{slug}-{id}/
        adresini hot-autocomplete-api.enuygun.com üzerinden dinamik çözüp önbelleğe alır.
        """
        en_slug = cls.ENUYGUN_HOTEL_SLUG_MAP.get(city_slug)
        if en_slug:
            return en_slug

        try:
            u = f"https://hot-autocomplete-api.enuygun.com/api/v1/autocomplete?q={urllib.parse.quote(city_clean)}&locale=tr"
            raw = cls._http_get_text(
                u,
                headers={"Accept": "application/json", "Referer": "https://www.enuygun.com/otel/"},
                timeout=3.0,
            )
            payload = json.loads(raw)
            items = payload if isinstance(payload, list) else ((payload.get("data") or {}).get("items") or [])
            fallback_slug = None
            for it in items:
                if not isinstance(it, dict):
                    continue
                itype = str(it.get("type") or "").lower()
                url_path = str(it.get("url") or "").strip()
                slug_val = str(it.get("slug") or "").strip().strip("/")
                if itype == "hotel" or url_path.startswith("/otel/detay/"):
                    continue
                if not slug_val and "/otel/bolge/" in url_path:
                    slug_val = url_path.split("/otel/bolge/")[-1].strip("/")
                elif not slug_val and url_path:
                    slug_val = url_path.strip("/").split("/")[-1]
                if slug_val:
                    if itype in ("city", "town", "district", "village"):
                        cls.ENUYGUN_HOTEL_SLUG_MAP[city_slug] = slug_val
                        return slug_val
                    elif not fallback_slug:
                        fallback_slug = slug_val
            if fallback_slug:
                cls.ENUYGUN_HOTEL_SLUG_MAP[city_slug] = fallback_slug
                return fallback_slug
        except Exception as e:
            logger.debug(f"Enuygun region slug resolve warning ({city_clean}): {e}")

        return None

    @classmethod
    def resolve_enuygun_hotel_url(
        cls,
        city_clean: str,
        city_slug: str,
        enuygun_cin: str,
        enuygun_cout: str,
        guests: int,
    ) -> str:
        """
        Enuygun Otel'in /otel/bolge/{slug}-{id}/?checkInDate=DD.MM.YYYY&checkOutDate=DD.MM.YYYY&rooms=N
        formatında doğrudan canlı şehir otel listesine inen URL'sini üretir.
        """
        en_slug = cls.resolve_enuygun_region_slug(city_clean, city_slug) or city_slug
        return (
            f"https://www.enuygun.com/otel/bolge/{en_slug}/?"
            f"checkInDate={enuygun_cin}&checkOutDate={enuygun_cout}&rooms={guests}"
        )

    # Popüler destinasyonların önceden haritalandırılmış Booking.com bölge ve şehir ID'leri
    DEST_ID_MAP = {
        "sakiz-adasi": {"dest_id": "2810", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Sakız Adası (Chios)"},
        "chios": {"dest_id": "2810", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Sakız Adası (Chios)"},
        "rodos-adasi": {"dest_id": "2668", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Rodos Eski Şehir"},
        "rodos": {"dest_id": "2668", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Rodos"},
        "midilli-adasi": {"dest_id": "2811", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Midilli (Lesbos)"},
        "midilli": {"dest_id": "2811", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Midilli"},
        "kos-adasi": {"dest_id": "2665", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Kos Adası"},
        "kos": {"dest_id": "2665", "dest_type": "region", "is_intl": True, "label": "Yunanistan / Kos"},
        "paris": {"dest_id": "-1456928", "dest_type": "city", "is_intl": True, "label": "Fransa / Paris"},
        "roma": {"dest_id": "-126693", "dest_type": "city", "is_intl": True, "label": "İtalya / Roma"},
        "munih": {"dest_id": "-1829149", "dest_type": "city", "is_intl": True, "label": "Almanya / Münih"},
        "viyana": {"dest_id": "-1995499", "dest_type": "city", "is_intl": True, "label": "Avusturya / Viyana"},
        "londra": {"dest_id": "-2601889", "dest_type": "city", "is_intl": True, "label": "İngiltere / Londra"},
        "venedik": {"dest_id": "-132007", "dest_type": "city", "is_intl": True, "label": "İtalya / Venedik"},
        "tokyo": {"dest_id": "-246227", "dest_type": "city", "is_intl": True, "label": "Japonya / Tokyo"},
        "kyoto": {"dest_id": "-235553", "dest_type": "city", "is_intl": True, "label": "Japonya / Kyoto"},
        "new-york": {"dest_id": "20088325", "dest_type": "city", "is_intl": True, "label": "ABD / New York"},
        "nice": {"dest_id": "-1454984", "dest_type": "city", "is_intl": True, "label": "Fransa / Nice & Côte d'Azur"},
        "monaco": {"dest_id": "-1454984", "dest_type": "city", "is_intl": True, "label": "Monaco / Monte Carlo & Nice Sahili"},
        "baku": {"dest_id": "-2417770", "dest_type": "city", "is_intl": True, "label": "Azerbaycan / Bakü Sahil & İçeri Şehir"},
        "ankara": {"dest_id": "-735340", "dest_type": "city", "is_intl": False, "label": "Türkiye / Ankara & Kızılay"},
        "antalya": {"dest_id": "-735346", "dest_type": "city", "is_intl": False, "label": "Türkiye / Antalya & Kaleiçi"},
        "istanbul": {"dest_id": "-755070", "dest_type": "city", "is_intl": False, "label": "Türkiye / İstanbul"},
        "izmir": {"dest_id": "-754964", "dest_type": "city", "is_intl": False, "label": "Türkiye / İzmir"},
        "bodrum": {"dest_id": "-739775", "dest_type": "city", "is_intl": False, "label": "Türkiye / Bodrum"},
        "adana": {"dest_id": "-733575", "dest_type": "city", "is_intl": False, "label": "Türkiye / Adana"},
        "nevsehir": {"dest_id": "-766579", "dest_type": "city", "is_intl": False, "label": "Türkiye / Kapadokya"},
        "balikesir": {"dest_id": "-737225", "dest_type": "city", "is_intl": False, "label": "Türkiye / Balıkesir & Körfez"}
    }

    # Yedek referans piyasa fiyat profilleri (TRY bazında)
    CITY_HOTEL_PROFILES = {
        "paris": {"min_try": 2200, "max_try": 5500, "label": "Fransa / Paris Metropolü"},
        "nice": {"min_try": 2400, "max_try": 6200, "label": "Fransa / Nice & Côte d'Azur"},
        "monaco": {"min_try": 3500, "max_try": 9000, "label": "Monaco / Monte Carlo & Nice Sahili"},
        "baku": {"min_try": 1400, "max_try": 3800, "label": "Azerbaycan / Bakü Sahil"},
        "ankara": {"min_try": 1200, "max_try": 3100, "label": "Türkiye / Ankara & Çankaya"},
        "roma": {"min_try": 1800, "max_try": 4200, "label": "İtalya / Roma Tarihi Merkez"},
        "milano": {"min_try": 1900, "max_try": 4500, "label": "İtalya / Milano Merkez"},
        "venedik": {"min_try": 1800, "max_try": 4400, "label": "İtalya / Venedik & San Marco"},
        "munih": {"min_try": 1900, "max_try": 4500, "label": "Almanya / Münih & Bavyera"},
        "londra": {"min_try": 2500, "max_try": 6200, "label": "İngiltere / Londra Merkez"},
        "new-york": {"min_try": 3500, "max_try": 8500, "label": "ABD / New York"},
        "viyana": {"min_try": 1700, "max_try": 3900, "label": "Avusturya / Viyana Merkez"},
        "sakiz-adasi": {"min_try": 1300, "max_try": 2800, "label": "Yunanistan / Sakız Adası Liman"},
        "kos-adasi": {"min_try": 1400, "max_try": 3100, "label": "Yunanistan / Kos Adası"},
        "midilli-adasi": {"min_try": 1300, "max_try": 2900, "label": "Yunanistan / Midilli Liman"},
        "rodos-adasi": {"min_try": 1500, "max_try": 3400, "label": "Yunanistan / Rodos Eski Şehir"},
        "antalya": {"min_try": 1100, "max_try": 3500, "label": "Türkiye / Antalya & Kaleiçi"},
        "istanbul": {"min_try": 1100, "max_try": 3200, "label": "Türkiye / İstanbul"},
        "izmir": {"min_try": 1200, "max_try": 3000, "label": "Türkiye / İzmir"},
        "bodrum": {"min_try": 1800, "max_try": 4800, "label": "Türkiye / Bodrum"},
        "adana": {"min_try": 1000, "max_try": 2600, "label": "Türkiye / Adana"},
        "nevsehir": {"min_try": 1400, "max_try": 3900, "label": "Türkiye / Kapadokya"},
        "balikesir": {"min_try": 1100, "max_try": 2800, "label": "Türkiye / Balıkesir & Edremit"}
    }

    @staticmethod
    def slugify_hotel_name(name: str) -> str:
        s = str(name or "")
        for tr_c, en_c in [
            ("İ", "i"), ("I", "i"), ("ı", "i"),
            ("Ş", "s"), ("ş", "s"),
            ("Ç", "c"), ("ç", "c"),
            ("Ğ", "g"), ("ğ", "g"),
            ("Ü", "u"), ("ü", "u"),
            ("Ö", "o"), ("ö", "o"),
            ("’", ""), ("'", ""), ('"', ""), ("&", "and"), (".", ""),
        ]:
            s = s.replace(tr_c, en_c)
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")

    @classmethod
    def normalize_hotel_match_key(cls, name: str, city_clean: str = "") -> str:
        """
        Enuygun, Trip.com ve Etstur'dan gelen aynı oteli (örn. 'Concorde De Luxe Resort Lara' ile
        'Concorde De Luxe Resort Lara Antalya – Prive Ultra All Inclusive') tek kartta birleştirmek için anahtar üretir.
        """
        cleaned_raw = re.sub(
            r"\s*[-–|]\s*(Prive\s+|Ultra\s+|All\s+Inclusive.*|All-Inclusive.*|Her\s+Şey\s+Dahil.*|Adult\s+Only.*|Adults\s+Only.*|Sadece\s+Yetişkin.*|Special\s+Class.*)$",
            "",
            str(name or ""),
            flags=re.I,
        ).strip()
        s = cls.slugify_hotel_name(cleaned_raw or name)
        city_s = cls.slugify_hotel_name(city_clean)
        stop_words = {
            "hotel", "hotels", "otel", "oteli", "resort", "resorts", "spa", "and", "the", "by",
            "prive", "ultra", "all", "inclusive", "luxury", "collection", "boutique",
            "butik", "palace", "beach", "club", "suites", "suite", "residence",
            "adult", "adults", "only", "sadece", "yetiskin", "special", "class", "thermal",
            "lara", "kundu", "belek", "kemer", "kaleici", "konyaalti", "sarikamis", "sehir", "merkezi",
            city_s
        }
        tokens = [t for t in s.split("-") if t and len(t) > 1 and t not in stop_words and not t.isdigit()]
        if not tokens:
            tokens = [t for t in s.split("-") if t and t not in stop_words]
        if not tokens:
            tokens = [t for t in s.split("-") if t and not t.isdigit()]
        return "-".join(tokens[:3])

    @staticmethod
    def _create_primp_client(timeout: float = 6.5):
        import primp
        for imp in ("chrome", "chrome_131", "chrome_124", "chrome_120"):
            try:
                return primp.Client(impersonate=imp, timeout=timeout, follow_redirects=True)
            except Exception:
                try:
                    return primp.Client(impersonate=imp, timeout=timeout)
                except Exception:
                    continue
        return primp.Client(timeout=timeout)

    @classmethod
    def _http_get_text(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 6.5,
        accept_language: Optional[str] = None,
    ) -> str:
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": accept_language or "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if headers:
            req_headers.update(headers)
        try:
            client = cls._create_primp_client(timeout=timeout)
            resp = client.get(url, headers=req_headers)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception as e:
            logger.debug(f"primp fetch fallback ({url[:60]}): {e}")

        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "ignore")

    @classmethod
    def _build_hotel_search_queries(cls, hotel_name: str, city_clean: str) -> List[str]:
        """
        Otel adındaki konsept eklerini ('- All Inclusive', '– Prive Ultra All Inclusive' vb.) ve
        sondaki mükerrer bölge kelimelerini ('Lara Antalya' vb.) temizleyerek aday arama sorguları üretir.
        """
        q1 = re.sub(
            r"\s*[-–|]\s*(Prive\s+|Ultra\s+|All\s+Inclusive.*|All-Inclusive.*|Her\s+Şey\s+Dahil.*|Adult\s+Only.*|Adults\s+Only.*|Sadece\s+Yetişkin.*|Special\s+Class.*)$",
            "",
            str(hotel_name or ""),
            flags=re.I,
        ).strip()
        if not q1:
            q1 = str(hotel_name or "").strip()

        queries = [q1]
        q2 = re.sub(
            rf"\s+\b(Lara|Kundu|Belek|Kemer|Konyaaltı|Kaleiçi|{re.escape(city_clean)})\b(\s+\b(Lara|Kundu|Belek|Kemer|Konyaaltı|Kaleiçi|{re.escape(city_clean)})\b)*\s*$",
            "",
            q1,
            flags=re.I,
        ).strip()
        if q2 and q2.lower() != q1.lower() and len(q2) >= 4:
            queries.append(q2)
        return queries

    _PARENT_LOCATION_TOKENS_MAP: Dict[str, tuple] = {
        "bodrum": ("mugla",),
        "fethiye": ("mugla",),
        "marmaris": ("mugla",),
        "dalaman": ("mugla",),
        "datca": ("mugla",),
        "selimiye": ("marmaris", "mugla"),
        "bozburun": ("marmaris", "mugla"),
        "hisaronu": ("marmaris", "mugla"),
        "icmeler": ("marmaris", "mugla"),
        "turunc": ("marmaris", "mugla"),
        "akyaka": ("ula", "marmaris", "mugla"),
        "dalyan": ("ortaca", "koycegiz", "mugla"),
        "gocek": ("fethiye", "dalaman", "mugla"),
        "oludeniz": ("fethiye", "mugla"),
        "alanya": ("antalya",),
        "kemer": ("antalya",),
        "belek": ("serik", "antalya"),
        "side": ("manavgat", "antalya"),
        "kas": ("antalya",),
        "kalkan": ("kas", "antalya"),
        "olimpos": ("kumluca", "kemer", "antalya"),
        "cirali": ("kemer", "kumluca", "antalya"),
        "adrasan": ("kumluca", "kemer", "antalya"),
        "cesme": ("izmir",),
        "alacati": ("cesme", "izmir"),
        "ilica": ("cesme", "izmir"),
        "sigacik": ("seferihisar", "izmir"),
        "urla": ("izmir",),
        "kusadasi": ("aydin",),
        "didim": ("aydin",),
        "ayvalik": ("balikesir",),
        "cunda": ("ayvalik", "alibey", "balikesir"),
        "edremit": ("balikesir",),
        "akcay": ("edremit", "balikesir"),
        "altinoluk": ("edremit", "balikesir"),
        "bozcaada": ("canakkale",),
        "gokceada": ("canakkale",),
        "assos": ("ayvacik", "behram", "canakkale"),
        "behramkale": ("assos", "ayvacik", "canakkale"),
        "ayvacik": ("assos", "canakkale"),
        "kucukkuyu": ("ayvacik", "canakkale"),
        "kapadokya": ("nevsehir", "urgup", "goreme", "avanos"),
        "urgup": ("nevsehir", "kapadokya"),
        "goreme": ("nevsehir", "kapadokya"),
        "avanos": ("nevsehir", "kapadokya"),
        "sapanca": ("sakarya",),
        "masukiye": ("kartepe", "sapanca", "kocaeli", "sakarya"),
        "kartepe": ("masukiye", "kocaeli"),
        "agva": ("sile", "istanbul"),
        "sile": ("istanbul",),
        "abant": ("bolu", "mudurnu"),
        "kartalkaya": ("bolu",),
        "pamukkale": ("denizli",),
        "amasra": ("bartin",),
        "safranbolu": ("karabuk",),
        "uzungol": ("caykara", "trabzon"),
        "caykara": ("uzungol", "trabzon"),
        "ayder": ("camlihemsin", "rize"),
        "camlihemsin": ("ayder", "rize"),
        "uludag": ("osmangazi", "bursa"),
        "sarikamis": ("kars",),
        "palandoken": ("erzurum",),
        "erciyes": ("melikgazi", "kayseri"),
    }

    @classmethod
    def resolve_enuygun_direct_hotel_slug(cls, hotel_name: str, city_clean: str, city_slug: str) -> Optional[str]:
        """
        Enuygun resmi autocomplete API'sini (hot-autocomplete-api.enuygun.com) kullanarak
        bir otelin gerçek /otel/detay/{slug}/ adresini doğrular. Eşleşme yoksa None döner (Asla bölge sayfasına düşürmez).
        """
        mkey = cls.normalize_hotel_match_key(hotel_name, city_clean)
        if not mkey:
            return None
        cache_key = f"{city_slug}:{mkey}"
        if cache_key in cls._ENUYGUN_DIRECT_SLUG_CACHE:
            return cls._ENUYGUN_DIRECT_SLUG_CACHE[cache_key]

        allowed_loc_tokens = {city_slug, cls.slugify_hotel_name(city_clean)}
        if city_slug in cls._PARENT_LOCATION_TOKENS_MAP:
            allowed_loc_tokens.update(cls._PARENT_LOCATION_TOKENS_MAP[city_slug])

        target_tokens = [t for t in mkey.split("-") if t]
        for query_str in cls._build_hotel_search_queries(hotel_name, city_clean):
            api_url = f"https://hot-autocomplete-api.enuygun.com/api/v1/autocomplete?q={urllib.parse.quote(query_str)}"
            try:
                raw = cls._http_get_text(
                    api_url,
                    headers={"Accept": "application/json", "Referer": "https://www.enuygun.com/otel/"},
                    timeout=3.5,
                )
                payload = json.loads(raw)
                items = (payload.get("data") or {}).get("items") or []

                for x in items:
                    if not isinstance(x, dict) or x.get("type") != "hotel":
                        continue
                    url_path = str(x.get("url") or "").strip()
                    slug = str(x.get("slug") or "").strip().strip("/")
                    if not slug and url_path.startswith("/otel/detay/"):
                        slug = url_path.replace("/otel/detay/", "").strip("/")
                    if not slug:
                        continue

                    extra = x.get("extra") or {}
                    loc_str = " ".join([
                        str(x.get("path") or ""),
                        str(x.get("name") or ""),
                        str(extra.get("city") or ""),
                        str(extra.get("town") or ""),
                        str(extra.get("subtown") or ""),
                    ])
                    loc_slug = cls.slugify_hotel_name(loc_str)
                    if not any(tok and tok in loc_slug for tok in allowed_loc_tokens):
                        continue

                    cand_key = cls.normalize_hotel_match_key(str(x.get("name") or ""), city_clean)
                    cand_tokens = [t for t in cand_key.split("-") if t]
                    if not cand_tokens or not target_tokens:
                        continue

                    is_name_match = (
                        cand_key == mkey
                        or (
                            cand_tokens[0] == target_tokens[0]
                            and (set(cand_tokens) <= set(target_tokens) or set(target_tokens) <= set(cand_tokens))
                        )
                    )
                    if is_name_match:
                        cls._ENUYGUN_DIRECT_SLUG_CACHE[cache_key] = slug
                        return slug
            except Exception as e:
                logger.debug(f"Enuygun autocomplete slug resolve warning ({hotel_name}): {e}")

        cls._ENUYGUN_DIRECT_SLUG_CACHE[cache_key] = None
        return None

    @classmethod
    def resolve_etstur_direct_hotel_slug(cls, hotel_name: str, city_clean: str, city_slug: str) -> Optional[str]:
        """
        Etstur resmi /v2/autocomplete API'sini kullanarak bir otelin gerçek Etstur detay URL slug'ını
        (örn. 'costa-sariyaz-hotel') doğrular. Etstur'da satılmayan tesisler için None döner (Asla 404 /Arama?q= üretmez).
        """
        mkey = cls.normalize_hotel_match_key(hotel_name, city_clean)
        if not mkey:
            return None
        cache_key = f"{city_slug}:{mkey}"
        if cache_key in cls._ETSTUR_DIRECT_SLUG_CACHE:
            return cls._ETSTUR_DIRECT_SLUG_CACHE[cache_key]

        allowed_loc_tokens = {city_slug, cls.slugify_hotel_name(city_clean)}
        if city_slug in cls._PARENT_LOCATION_TOKENS_MAP:
            allowed_loc_tokens.update(cls._PARENT_LOCATION_TOKENS_MAP[city_slug])

        target_tokens = [t for t in mkey.split("-") if t]
        for query_str in cls._build_hotel_search_queries(hotel_name, city_clean):
            api_url = f"https://www.etstur.com/v2/autocomplete?q={urllib.parse.quote(query_str)}"
            try:
                raw = cls._http_get_text(
                    api_url,
                    headers={"Accept": "application/json", "Referer": "https://www.etstur.com/"},
                    timeout=3.0,
                )
                payload = json.loads(raw)
                items = payload.get("result") or []
                if not isinstance(items, list):
                    continue

                for x in items:
                    if not isinstance(x, dict) or str(x.get("type") or "").upper() != "HOTEL":
                        continue
                    ets_slug = str(x.get("url") or "").strip().strip("/")
                    if not ets_slug or "/" in ets_slug:
                        continue

                    state_list = x.get("state") if isinstance(x.get("state"), list) else []
                    loc_str = " ".join([
                        str(x.get("title") or ""),
                        str(x.get("city") or ""),
                        str(x.get("country") or ""),
                        " ".join(str(s) for s in state_list),
                    ])
                    loc_slug = cls.slugify_hotel_name(loc_str)
                    if not any(tok and tok in loc_slug for tok in allowed_loc_tokens):
                        continue

                    cand_title = str(x.get("title") or "").split(",")[0].strip()
                    cand_key = cls.normalize_hotel_match_key(cand_title, city_clean)
                    cand_tokens = [t for t in cand_key.split("-") if t]
                    if not cand_tokens or not target_tokens:
                        continue

                    is_name_match = (
                        cand_key == mkey
                        or (
                            cand_tokens[0] == target_tokens[0]
                            and (set(cand_tokens) <= set(target_tokens) or set(target_tokens) <= set(cand_tokens))
                        )
                    )
                    if is_name_match:
                        cls._ETSTUR_DIRECT_SLUG_CACHE[cache_key] = ets_slug
                        return ets_slug
            except Exception as e:
                logger.debug(f"Etstur autocomplete slug resolve warning ({hotel_name}): {e}")

        cls._ETSTUR_DIRECT_SLUG_CACHE[cache_key] = None
        return None

    @classmethod
    def resolve_enuygun_direct_hotel_urls_batch(
        cls,
        items: List[Dict[str, Any]],
        city_clean: str,
        city_slug: str,
        enuygun_cin: str,
        enuygun_cout: str,
        guests: int,
    ) -> None:
        """
        Yurt içi otel kartlarında:
        1. Enuygun doğrudan otel detay linki (/otel/detay/{slug}/) eksik olanları Enuygun Autocomplete API ile,
        2. Etstur doğrudan otel detay linkini (https://www.etstur.com/{ets_slug}?check_in=...) Etstur Autocomplete API ile
        paralel doğrular. Eşleşme olmayanlarda asla 404 veya genel şehir listesine düşürmez.
        """
        if not items:
            return

        def _resolve_one(it: Dict[str, Any]):
            hname = it.get("name")
            if not hname:
                return
            if not it.get("enuygun_hotel_url"):
                slug = cls.resolve_enuygun_direct_hotel_slug(hname, city_clean, city_slug)
                if slug:
                    it["enuygun_slug"] = slug
                    it["enuygun_hotel_url"] = (
                        f"https://www.enuygun.com/otel/detay/{slug}/?"
                        f"checkInDate={enuygun_cin}&checkOutDate={enuygun_cout}&rooms={guests}"
                        f"&utm_source=hakikibilet&utm_medium=affiliate"
                    )
            if not it.get("etstur_hotel_url"):
                ets_slug = cls.resolve_etstur_direct_hotel_slug(hname, city_clean, city_slug)
                if ets_slug:
                    it["etstur_slug"] = ets_slug
                    it["etstur_hotel_url"] = (
                        f"https://www.etstur.com/{ets_slug}?"
                        f"check_in={enuygun_cin}&check_out={enuygun_cout}&adult_1={guests}"
                        f"&utm_source=hakikibilet&utm_medium=affiliate"
                    )

        try:
            with ThreadPoolExecutor(max_workers=min(12, len(items))) as pool:
                list(pool.map(_resolve_one, items, timeout=6.0))
        except Exception as e:
            logger.debug(f"Batch Enuygun/Etstur direct slug resolve warning: {e}")

    @staticmethod
    def _extract_balanced_json_array(text: str, bracket_start: int) -> Optional[str]:
        if bracket_start < 0 or bracket_start >= len(text) or text[bracket_start] != "[":
            return None
        depth = 0
        in_str = False
        esc = False
        for i in range(bracket_start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        return text[bracket_start : i + 1]
        return None

    @classmethod
    def get_destination_context(cls, city_slug: str, is_international: bool) -> Dict[str, Any]:
        coastal_slugs = {
            "antalya", "bodrum", "fethiye", "marmaris", "selimiye", "bozburun", "hisaronu", "icmeler", "turunc",
            "akyaka", "dalyan", "gocek", "oludeniz", "dalaman", "datca", "cesme", "alacati", "ilica", "sigacik", "urla",
            "kusadasi", "didim", "ayvalik", "cunda", "alanya", "kemer", "olimpos", "cirali", "adrasan", "belek", "side",
            "kas", "kalkan", "bozcaada", "gokceada", "assos", "behramkale", "ayvacik", "kucukkuyu", "edremit", "akcay",
            "altinoluk", "agva", "sile", "amasra", "mersin", "girne", "gazimagusa", "sakiz-adasi", "sakiz",
            "rodos-adasi", "rodos", "kos-adasi", "kos", "midilli-adasi", "midilli", "samos-adasi", "samos",
            "nice", "barselona", "dubai", "batum"
        }
        ski_slugs = {
            "kars", "sarikamis", "erzurum", "palandoken", "kayseri", "erciyes",
            "bursa", "uludag", "bolu", "abant", "kartalkaya", "kartepe", "isparta", "erzincan"
        }
        thermal_slugs = {"afyonkarahisar", "yalova", "pamukkale", "denizli", "bursa", "kutahya", "bolu", "sakarya", "sapanca", "masukiye", "ayder", "camlihemsin"}
        boutique_slugs = {
            "nevsehir", "kapadokya", "urgup", "goreme", "avanos", "mardin", "safranbolu", "amasra",
            "alacati", "bozcaada", "gokceada", "assos", "cunda", "selimiye", "bozburun", "akyaka",
            "kas", "kalkan", "olimpos", "cirali", "uzungol", "ayder", "amasya", "gaziantep", "sanliurfa"
        }

        profile_types = []
        if city_slug in coastal_slugs:
            profile_types.append("coastal")
        if city_slug in ski_slugs:
            profile_types.append("ski")
        if city_slug in thermal_slugs:
            profile_types.append("thermal")
        if city_slug in boutique_slugs:
            profile_types.append("boutique")
        if not profile_types:
            profile_types.append("metropolis")

        return {
            "types": profile_types,
            "is_coastal": "coastal" in profile_types,
            "is_ski": "ski" in profile_types,
            "is_thermal": "thermal" in profile_types,
            "is_boutique": "boutique" in profile_types,
            "is_metropolis": "metropolis" in profile_types,
            "is_international": is_international,
        }

    @classmethod
    def fetch_live_enuygun_hotels(
        cls,
        en_slug: str,
        city_clean: str,
        city_slug: str,
        cin: str,
        cout: str,
        enuygun_cin: str,
        enuygun_cout: str,
        nights: int,
        guests: int,
        currency: str = "TRY",
    ) -> List[Dict[str, Any]]:
        """
        Enuygun /otel/bolge/{en_slug}/ SSR sayfasından 20 gerçek otelin adını, HD fotoğraflarını,
        konseptini (Her Şey Dahil, Oda Kahvaltı vb.), popüler olanaklarını, misafir puanını,
        canlı fiyatını ve doğrudan otel detay sayfası (/otel/detay/{slug}/) linkini çeker.
        64KB üzeri Next.js RSC parçalanmalarını (örn. antalya-481 ve alanya-4671) eksiksiz birleştirir.
        """
        if not en_slug:
            return []
        url = (
            f"https://www.enuygun.com/otel/bolge/{en_slug}/?"
            f"checkInDate={enuygun_cin}&checkOutDate={enuygun_cout}&rooms={guests}"
        )
        try:
            html = cls._http_get_text(
                url,
                headers={
                    "Accept-Language": "tr-TR,tr;q=0.9",
                    "Referer": "https://www.enuygun.com/otel/",
                },
                timeout=6.5,
            )
            if not html:
                return []

            arr = None
            raw_chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
            if raw_chunks:
                decoded_parts: List[str] = []
                for ch in raw_chunks:
                    try:
                        decoded_parts.append(json.loads('"' + ch + '"'))
                    except Exception:
                        decoded_parts.append(ch.encode("utf-8").decode("unicode_escape", errors="ignore"))
                full_rsc = "".join(decoded_parts)

                search_from = 0
                best_priced_count = 0
                while True:
                    pos = full_rsc.find('[{"id":', search_from)
                    if pos == -1:
                        break
                    arr_str = cls._extract_balanced_json_array(full_rsc, pos)
                    if arr_str:
                        try:
                            cand_arr = json.loads(arr_str)
                            if (
                                isinstance(cand_arr, list)
                                and cand_arr
                                and isinstance(cand_arr[0], dict)
                                and ("slug" in cand_arr[0] or "ratingGeneral" in cand_arr[0] or "images" in cand_arr[0])
                            ):
                                priced_cnt = sum(
                                    1
                                    for x in cand_arr
                                    if isinstance(x, dict) and (x.get("price") or x.get("minPrice"))
                                )
                                if priced_cnt > best_priced_count:
                                    best_priced_count = priced_cnt
                                    arr = cand_arr
                        except Exception:
                            pass
                    search_from = pos + 7

            if not isinstance(arr, list):
                return []

            results = []
            for h in arr:
                if not isinstance(h, dict):
                    continue
                name = (h.get("name") or "").strip()
                slug = (h.get("slug") or "").strip().strip("/")
                if not name or not slug:
                    continue

                direct_price = h.get("price")
                min_price_eur = h.get("minPrice")
                price_try = 0.0
                if direct_price is not None and float(direct_price) >= 650:
                    price_try = float(direct_price)
                elif min_price_eur is not None and float(min_price_eur) > 0:
                    mp_val = float(min_price_eur)
                    # Enuygun SSR'da price=None olduğunda minPrice alanı EUR bazındadır (örn. 119.34 EUR)
                    price_try = CurrencyService.convert(mp_val, "EUR", "TRY") if mp_val < 650 else mp_val

                if price_try < 650:
                    continue

                nightly_val = CurrencyService.convert(price_try, "TRY", currency) if currency != "TRY" else price_try
                total_val = nightly_val * max(1, nights)

                concept_obj = ((h.get("concepts") or {}).get("concept") or {}) if isinstance(h.get("concepts"), dict) else {}
                concept_name = (concept_obj.get("name") or "").strip()
                concept_code = (concept_obj.get("code") or "").strip().upper()

                facs = [
                    str(f.get("name")).strip()
                    for f in (h.get("popularFacilities") or [])
                    if isinstance(f, dict) and f.get("name")
                ]
                rtags = [
                    str(t.get("name")).strip()
                    for t in (h.get("reviewTags") or [])
                    if isinstance(t, dict) and t.get("name")
                ]
                imgs = [str(u).strip() for u in (h.get("images") or []) if u]
                main_img = str(h.get("imageUrl") or (imgs[0] if imgs else "")).strip()
                if main_img and main_img not in imgs:
                    imgs.insert(0, main_img)

                town = (h.get("town") or "").strip()
                sub_town = (h.get("subTown") or "").strip()
                loc_label = f"{sub_town}, {town}" if (sub_town and town and sub_town != town) else (sub_town or town or city_clean)
                dist_center = h.get("distanceFromCenter")

                score_raw = float(h.get("ratingGeneral") or 0.0)
                score_val = round(score_raw, 1) if score_raw > 0 else 8.4
                review_count = int(h.get("reviewCount") or 0)
                score_word = (h.get("ratingGeneralText") or "").strip() or ("Mükemmel" if score_val >= 9.0 else ("Çok İyi" if score_val >= 8.2 else "İyi"))

                direct_enuygun_detail = (
                    f"https://www.enuygun.com/otel/detay/{slug}/?"
                    f"checkInDate={enuygun_cin}&checkOutDate={enuygun_cout}&rooms={guests}"
                    f"&utm_source=hakikibilet&utm_medium=affiliate"
                )

                results.append({
                    "source": "enuygun",
                    "enuygun_id": h.get("id"),
                    "name": name,
                    "enuygun_slug": slug,
                    "town": town or city_clean,
                    "sub_town": sub_town,
                    "location_label": loc_label,
                    "address": (h.get("address") or loc_label).strip(),
                    "distance_center_km": round(float(dist_center), 1) if dist_center is not None else None,
                    "score": score_val,
                    "score_word": score_word,
                    "review_count": review_count,
                    "concept_name": concept_name,
                    "concept_code": concept_code,
                    "facilities": facs,
                    "review_tags": rtags,
                    "photo": main_img,
                    "photos": imgs[:5],
                    "nightly_price": round(nightly_val, 2),
                    "total_price": round(total_val, 2),
                    "enuygun_price": round(nightly_val, 2),
                    "enuygun_total_price": round(total_val, 2),
                    "enuygun_hotel_url": direct_enuygun_detail,
                    "free_cancellation": bool(h.get("freeCancellation")),
                })
            return results
        except Exception as e:
            logger.warning(f"Enuygun live hotel SSR fetch warning ({en_slug}): {e}")
            return []

    @classmethod
    def fetch_live_trip_hotels(
        cls,
        city_id: Optional[int],
        city_clean: str,
        city_slug: str,
        cin: str,
        cout: str,
        nights: int,
        guests: int,
        currency: str = "TRY",
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Trip.com /hotels/list?cityId=... SSR sayfasından gerçek otelleri, yıldız sayılarını,
        oda tiplerini, çoklu HD fotoğraflarını, gecelik TRY fiyatlarını ve doğrudan
        Trip.com otel detay sayfası (/hotels/detail/?hotelId=...) linklerini çeker.
        Rezervasyona kapalı / 0 yorumlu pasif ilanları (örn. MIRA SUITES) ve düşük puanlı
        tesisleri sıfır varsayım ilkesiyle filtreler.
        """
        if not city_id:
            return []
        trip_domain = "www.trip.com" if is_international else "tr.trip.com"
        locale = "en-US" if is_international else "tr-TR"
        accept_lang = "en-US,en;q=0.9" if is_international else "tr-TR,tr;q=0.9,en-US;q=0.8"

        def _extract_hotel_list_from_html(raw_html: str) -> Optional[List[Dict[str, Any]]]:
            if not raw_html:
                return None
            scripts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw_html, re.S)
            if not scripts:
                return None
            decoded_chunks: List[str] = []
            for s in scripts:
                try:
                    unesc = json.loads('"' + s + '"')
                except Exception:
                    unesc = s.encode("utf-8").decode("unicode_escape", errors="ignore")
                decoded_chunks.append(unesc)
                if len(s) >= 10000 and '"hotelList":[' in unesc:
                    pos = unesc.find('"hotelList":[')
                    arr_str = cls._extract_balanced_json_array(unesc, pos + len('"hotelList":'))
                    if arr_str:
                        try:
                            parsed = json.loads(arr_str)
                            if isinstance(parsed, list) and parsed:
                                return parsed
                        except Exception:
                            pass
            full_stream = "".join(decoded_chunks)
            pos = full_stream.find('"hotelList":[')
            if pos != -1:
                arr_str = cls._extract_balanced_json_array(full_stream, pos + len('"hotelList":'))
                if arr_str:
                    try:
                        parsed = json.loads(arr_str)
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
            return None

        url = (
            f"https://{trip_domain}/hotels/list?"
            f"cityId={city_id}&cityName={urllib.parse.quote(city_clean)}"
            f"&checkin={cin}&checkout={cout}&adult={guests}&crn=1&curr=TRY&locale={locale}"
        )
        try:
            html = cls._http_get_text(url, timeout=6.0, accept_language=accept_lang)
            hotel_list_raw = _extract_hotel_list_from_html(html)
            if not hotel_list_raw:
                # Birincil Trip.com domaini anlık boş dönerse alternatif domain üzerinden yedekle
                fb_domain = "tr.trip.com" if is_international else "www.trip.com"
                fallback_url = (
                    f"https://{fb_domain}/hotels/list?"
                    f"cityId={city_id}&cityName={urllib.parse.quote(city_clean)}"
                    f"&checkin={cin}&checkout={cout}&adult={guests}&crn=1&curr=TRY&locale=tr-TR"
                )
                html_fb = cls._http_get_text(fallback_url, timeout=5.5, accept_language=accept_lang)
                hotel_list_raw = _extract_hotel_list_from_html(html_fb)

            if not isinstance(hotel_list_raw, list):
                return []

            trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
            trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")

            results = []
            for item in hotel_list_raw:
                if not isinstance(item, dict):
                    continue
                hinfo = item.get("hotelInfo") or {}
                summary = hinfo.get("summary") or {}
                hotel_id = str(summary.get("hotelId") or "").strip()
                name = str((hinfo.get("nameInfo") or {}).get("name") or "").strip()
                if not hotel_id or not name:
                    continue
                # Ham sokak/mahalle adresi başlığıyla girilmiş kayıtsız apart ilanlarını (örn. 'Arapsuyu Mah. 600. Sok. No:19') ele
                if re.search(r"\b(mah\.|mahallesi|sok\.|sokak|cad\.|caddesi|no\s*:)\b", name.lower()):
                    continue

                def _to_float(val: Any, default: float = 0.0) -> float:
                    if val is None or val == "":
                        return default
                    try:
                        return float(str(val).strip().replace(",", "."))
                    except Exception:
                        return default

                rooms = item.get("roomInfo") or []
                if not isinstance(rooms, list) or not rooms:
                    continue
                first_room = rooms[0] if isinstance(rooms[0], dict) else {}
                room_sum = first_room.get("summary") or {}
                room_id = str(room_sum.get("roomId") or "").strip()
                room_qty = int(room_sum.get("roomQuantity") or 0)
                pinfo = first_room.get("priceInfo") or {}
                raw_price = _to_float(pinfo.get("price"), 0.0)
                if not room_id or room_qty <= 0 or pinfo.get("isHiddenPrice") or raw_price < 650:
                    continue

                price_try = raw_price
                nightly_val = CurrencyService.convert(price_try, "TRY", currency) if currency != "TRY" else price_try
                total_val = nightly_val * max(1, nights)

                del_price_val = _to_float(pinfo.get("deletePrice"), 0.0)
                old_nightly_val = (
                    CurrencyService.convert(del_price_val, "TRY", currency)
                    if del_price_val > price_try
                    else None
                )

                star_val = int((hinfo.get("hotelStar") or {}).get("star") or 0)
                cinfo = hinfo.get("commentInfo") or {}
                raw_score = _to_float(cinfo.get("commentScore"), 0.0)
                full_rating = _to_float(cinfo.get("fullRating"), 10.0)
                if raw_score > 0:
                    score_10 = round(raw_score * (10.0 / full_rating), 1) if full_rating > 0 else round(raw_score, 1)
                else:
                    score_10 = 0.0
                rev_num_str = re.sub(r"[^0-9]", "", str(cinfo.get("commenterNumber") or "0"))
                rev_count = int(rev_num_str) if rev_num_str else 0

                # SIFIR VARSAYIM & REZERVASYON GÜVENLİĞİ:
                # 0 puanlı / 0 yorumlu pasif tesisleri (örn. MIRA SUITES -> 'Bu otel şu anda rezervasyon kabul etmiyor')
                # ve 10 üzerinden 7.0'ın altındaki düşük puanlı tesisleri (örn. Sunpoint 4.8/10) kesin olarak filtrele.
                if score_10 < 7.0 or rev_count < 3:
                    continue

                score_word = str(cinfo.get("commentDescription") or "").strip() or ("Mükemmel" if score_10 >= 9.0 else "Çok İyi")
                ugc_quote = str(cinfo.get("ugcSentence") or "").strip()

                pos_info = hinfo.get("positionInfo") or {}
                pos_desc = str(pos_info.get("positionDesc") or city_clean).strip()

                img_info = hinfo.get("hotelImages") or {}
                main_img = str(img_info.get("url") or "").strip()
                multi_imgs = [
                    str(m.get("url")).strip()
                    for m in (img_info.get("multiImgs") or [])
                    if isinstance(m, dict) and m.get("url")
                ]
                if main_img and main_img not in multi_imgs:
                    multi_imgs.insert(0, main_img)

                room_name = str((first_room.get("summary") or {}).get("physicsName") or "").strip()
                rtags_obj = first_room.get("roomTags") or {}
                adv_tags = [
                    str(t.get("tagTitle")).strip()
                    for t in (rtags_obj.get("advantageTags") or [])
                    if isinstance(t, dict) and t.get("tagTitle")
                ]

                direct_trip_detail = (
                    f"https://{trip_domain}/hotels/detail/?"
                    f"hotelId={hotel_id}&cityId={city_id}"
                    f"&checkin={cin}&checkout={cout}&adult={guests}&crn=1&curr=TRY&locale={locale}"
                    f"&Allianceid={trip_aid}&SID={trip_sid}"
                )

                results.append({
                    "source": "trip",
                    "trip_id": hotel_id,
                    "name": name,
                    "stars": star_val,
                    "town": city_clean,
                    "sub_town": pos_desc.split("|")[0].strip() if "|" in pos_desc else pos_desc,
                    "location_label": pos_desc,
                    "address": pos_desc,
                    "distance_center_km": None,
                    "score": score_10,
                    "score_word": score_word,
                    "review_count": rev_count,
                    "ugc_quote": ugc_quote,
                    "room_name": room_name,
                    "concept_name": "",
                    "concept_code": "",
                    "facilities": adv_tags,
                    "review_tags": ([ugc_quote] if ugc_quote else []),
                    "photo": main_img,
                    "photos": multi_imgs[:5],
                    "nightly_price": round(nightly_val, 2),
                    "total_price": round(total_val, 2),
                    "old_nightly_price": round(old_nightly_val, 2) if old_nightly_val else None,
                    "trip_price": round(nightly_val, 2),
                    "trip_total_price": round(total_val, 2),
                    "trip_hotel_url": direct_trip_detail,
                    "free_cancellation": any("cancel" in t.lower() or "iptal" in t.lower() for t in adv_tags),
                })
            return results
        except Exception as e:
            logger.warning(f"Trip.com live hotel SSR fetch warning (cityId={city_id}): {e}")
            return []

    @classmethod
    def merge_and_score_live_hotels(
        cls,
        enuygun_hotels: List[Dict[str, Any]],
        trip_hotels: List[Dict[str, Any]],
        city_clean: str,
        city_slug: str,
        city_id: Optional[int],
        cin: str,
        cout: str,
        enuygun_cin: str,
        enuygun_cout: str,
        nights: int,
        guests: int,
        currency: str,
        is_international: bool,
    ) -> List[Dict[str, Any]]:
        """
        Enuygun ve Trip.com canlı otellerini birleştirir, aynı tesisleri tek kartta toplar,
        her karta doğrudan o otelin sayfasına inen linkleri bağlar ve Hakiki F/P Algoritması
        ile puanlayarak sıralar.
        """
        curr_sym = CurrencyService.get_symbol(currency)
        aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
        agoda_cid = getattr(settings, "AFFILIATE_AGODA_CID", "1924128")
        trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
        trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")
        trip_domain = "www.trip.com" if is_international else "tr.trip.com"
        locale = "en-US" if is_international else "tr-TR"

        merged_map: Dict[str, Dict[str, Any]] = {}
        ordered_items: List[Dict[str, Any]] = []

        for eh in enuygun_hotels:
            mkey = cls.normalize_hotel_match_key(eh["name"], city_clean)
            item = dict(eh)
            if mkey:
                merged_map[mkey] = item
            ordered_items.append(item)

        for th in trip_hotels:
            mkey = cls.normalize_hotel_match_key(th["name"], city_clean)
            existing = merged_map.get(mkey) if mkey else None
            if existing:
                existing["trip_id"] = th.get("trip_id")
                existing["trip_price"] = th.get("trip_price")
                existing["trip_total_price"] = th.get("trip_total_price")
                existing["trip_hotel_url"] = th.get("trip_hotel_url")
                if th.get("stars") and not existing.get("stars"):
                    existing["stars"] = th["stars"]
                if th.get("room_name") and not existing.get("room_name"):
                    existing["room_name"] = th["room_name"]
                if th.get("old_nightly_price") and not existing.get("old_nightly_price"):
                    existing["old_nightly_price"] = th["old_nightly_price"]
                if th.get("free_cancellation"):
                    existing["free_cancellation"] = True
                # En düşük canlı fiyatı ana fiyat olarak belirle
                ep = existing.get("enuygun_price")
                tp = th.get("trip_price")
                if ep and tp:
                    best_p = min(ep, tp)
                    existing["nightly_price"] = best_p
                    existing["total_price"] = round(best_p * max(1, nights), 2)
                for ph in th.get("photos") or []:
                    if ph and ph not in existing["photos"] and len(existing["photos"]) < 6:
                        existing["photos"].append(ph)
            else:
                item = dict(th)
                if mkey:
                    merged_map[mkey] = item
                ordered_items.append(item)

        if not ordered_items:
            return []

        # Yurt içi otellerde Enuygun doğrudan otel detay linki (/otel/detay/{slug}/) eksik olanları
        # Enuygun resmi Autocomplete API üzerinden paralel doğrula (Asla genel bölge listesine düşürme)
        if not is_international:
            cls.resolve_enuygun_direct_hotel_urls_batch(
                items=ordered_items,
                city_clean=city_clean,
                city_slug=city_slug,
                enuygun_cin=enuygun_cin,
                enuygun_cout=enuygun_cout,
                guests=guests,
            )

        prices = [float(x["nightly_price"]) for x in ordered_items if x.get("nightly_price") and float(x["nightly_price"]) > 0]
        median_price = statistics.median(prices) if prices else 3000.0
        resort_prices = [
            float(x["nightly_price"])
            for x in ordered_items
            if x.get("nightly_price") and (
                (x.get("concept_code") or "").upper() in ("AI", "AS", "UAI")
                or "her şey dahil" in (x.get("concept_name") or "").lower()
                or "all inclusive" in (x.get("name") or "").lower()
                or "resort" in (x.get("name") or "").lower()
                or "palace" in (x.get("name") or "").lower()
                or "de luxe" in (x.get("name") or "").lower()
                or "deluxe" in (x.get("name") or "").lower()
            )
        ]
        city_prices = [
            float(x["nightly_price"])
            for x in ordered_items
            if x.get("nightly_price") and float(x["nightly_price"]) not in resort_prices
        ]
        resort_median = statistics.median(resort_prices) if len(resort_prices) >= 2 else median_price
        city_median = statistics.median(city_prices) if len(city_prices) >= 2 else median_price
        dest_ctx = cls.get_destination_context(city_slug, is_international)

        enriched_list: List[Dict[str, Any]] = []
        for idx, h in enumerate(ordered_items):
            name = h.get("name") or ""
            name_lower = name.lower()
            ccode = (h.get("concept_code") or "").upper()
            cname = h.get("concept_name") or ""
            facs = [str(f) for f in (h.get("facilities") or [])]
            rtags = [str(t) for t in (h.get("review_tags") or [])]
            all_text = " ".join([name, cname] + facs + rtags + [h.get("location_label") or ""]).lower()

            # 1. Konsept (Pansiyon / Yeme-İçme) Sınıflandırması
            tags: List[str] = []
            is_conservative_prop = (
                "alkolsüz" in all_text
                or "muhafazakar" in all_text
                or "islami" in all_text
                or "tesettür" in all_text
                or "helal" in all_text
                or any(k in name_lower for k in ["adenya", "wome", "angel's", "angels", "bera alanya", "selge beach", "adass", "rizom", "modern saraylar", "altis resort"])
            )
            if is_conservative_prop:
                tags.append("conservative")
                tags.append("all_inclusive")
                concept_tr = "Alkolsüz Her Şey Dahil"
                concept_en = "Halal / Alcohol-Free All-Inclusive"
                board_bonus = 95.0
            elif ccode in ("AI", "AS", "UAI") or "her şey dahil" in all_text or "ultra all inclusive" in all_text or "all inclusive" in all_text or "all-inclusive" in all_text:
                tags.append("all_inclusive")
                is_ultra = (ccode in ("AS", "UAI")) or ("ultra" in all_text) or ("prive" in all_text)
                concept_tr = "Ultra Her Şey Dahil" if is_ultra else "Her Şey Dahil"
                concept_en = "Ultra All-Inclusive" if is_ultra else "All-Inclusive"
                board_bonus = 95.0 if is_ultra else 92.0
            elif ccode in ("FB", "HB") or "yarım pansiyon" in all_text or "tam pansiyon" in all_text or "half board" in all_text or "full board" in all_text:
                tags.append("half_board")
                tags.append("breakfast")
                concept_tr = cname or "Yarım / Tam Pansiyon"
                concept_en = "Half / Full Board"
                board_bonus = 86.0
            elif ccode == "BB" or "kahvaltı" in all_text or "breakfast" in all_text:
                tags.append("breakfast")
                concept_tr = "Oda Kahvaltı Dahil"
                concept_en = "Breakfast Included"
                board_bonus = 82.0
            else:
                concept_tr = cname or "Sadece Oda"
                concept_en = "Room Only"
                board_bonus = 70.0

            # 2. Yaşam Tarzı & Konum Etiketleri
            if h.get("free_cancellation") or "ücretsiz iptal" in all_text or "free cancellation" in all_text or "refundable" in all_text:
                tags.append("free_cancel")
                board_bonus = min(98.0, board_bonus + 4.0)

            if re.search(r"\b(pati|evcil hayvan|pet friendly|pet-friendly|pets allowed|hayvan dostu)\b", all_text):
                tags.append("pet_friendly")

            if "denize sıfır" in all_text or "özel plaj" in all_text or "mavi bayrak" in all_text or "beach" in all_text or "sahil" in all_text or "coast" in all_text or "seafront" in all_text:
                tags.append("beachfront")

            if "aile" in all_text or "çocuk" in all_text or "aquapark" in all_text or "su kaydıra" in all_text or "family" in all_text or "kids" in all_text or ("all_inclusive" in tags and dest_ctx["is_coastal"]):
                tags.append("family_aqua")

            if dest_ctx["is_ski"] and re.search(r"\b(kayak|ski|sarıkamış|sarikamis|palandöken|uludağ|erciyes|kartalkaya|kış)\b", all_text):
                tags.append("ski")

            if "termal" in all_text or "thermal" in all_text or "kaplıca" in all_text or "hamam" in all_text or "spa" in all_text:
                tags.append("thermal")

            dist_km = h.get("distance_center_km")
            if (dist_km is not None and dist_km <= 2.5) or "merkez" in all_text or "center" in all_text or "centre" in all_text or "near " in all_text or "metro" in all_text:
                tags.append("central")

            # 3. Üstteki 3 Alt Sekme (hotel | pension | airbnb) Sınıflandırması
            if re.search(r"\b(apart|villa|residence|rezidans|bungalov|bungalow|chalet|daire|studio|suites)\b", all_text):
                stay_sub_type = "airbnb"
            elif re.search(r"\b(pansiyon|butik|boutique|konak|konağı|sarayı|taş otel|cave|han|köşk|pension)\b", all_text):
                stay_sub_type = "pension"
            else:
                stay_sub_type = "hotel"

            # 4. Yıldız Tahmini
            stars = int(h.get("stars") or 0)
            if not stars:
                if "resort" in name_lower or "palace" in name_lower or "de luxe" in name_lower or "deluxe" in name_lower or "all_inclusive" in tags:
                    stars = 5
                elif h.get("nightly_price", 0) >= median_price * 1.15 or "spa" in all_text or "grand" in name_lower:
                    stars = 4
                else:
                    stars = 3

            # 5. Matematiksel Hakiki F/P Skoru (Bayesian Puan + Konsept + Konum / Segment Medyan Fiyat Oranı)
            raw_score = float(h.get("score") or 8.4)
            rev_count = int(h.get("review_count") or 20)
            bayes_score = ((rev_count * raw_score) + (25.0 * 8.2)) / (rev_count + 25.0)

            loc_score = 84.0
            if "beachfront" in tags or "ski" in tags:
                loc_score = 94.0
            elif "central" in tags:
                loc_score = 91.0

            star_score = 94.0 if stars >= 5 else (87.0 if stars == 4 else 81.0)
            quality_num = (0.45 * (bayes_score * 10.0)) + (0.20 * loc_score) + (0.20 * board_bonus) + (0.15 * star_score)

            segment_med = resort_median if ("all_inclusive" in tags or "resort" in name_lower or "palace" in name_lower) else city_median
            p_val = max(650.0, float(h.get("nightly_price") or segment_med))
            p_ratio = p_val / max(650.0, float(segment_med))
            # Segment medyanına göre dengeli fiyat çarpanı
            p_norm = max(0.88, min(1.25, p_ratio ** 0.24))
            fp_raw = (quality_num / p_norm) - 4.2
            # Çoklu acente (Enuygun + Trip.com) fiyat doğrulaması olan tesislere +2.0 güven bonusu
            if h.get("enuygun_price") and h.get("trip_price"):
                fp_raw += 2.0
            fp_score = int(round(max(75.0, min(97.0, fp_raw))))

            if fp_score >= 91:
                fp_badge_tr = f"🏆 F/P Şampiyonu • {fp_score}/100"
                fp_badge_en = f"🏆 Best Value Pick • {fp_score}/100"
            elif fp_score >= 86:
                fp_badge_tr = f"💎 Üstün Değer • {fp_score}/100"
                fp_badge_en = f"💎 Superior Value • {fp_score}/100"
            else:
                fp_badge_tr = f"👍 Dengeli Tercih • {fp_score}/100"
                fp_badge_en = f"👍 Balanced Choice • {fp_score}/100"

            # 6. Turizmci & CFO Danışman Notu (1 Cümlelik İkna Edici Değer Analizi)
            if "conservative" in tags:
                advisor_tr = "🕌 Alkolsüz aile konsepti, mahremiyet odaklı havuz/plaj alanları ve zengin açık büfesiyle muhafazakar tatil için doğrulanmış tesis."
                advisor_en = "🕌 Alcohol-free family concept with privacy-focused pool/beach areas and full board inclusions."
            elif "all_inclusive" in tags:
                advisor_tr = f"🍹 {concept_tr} konseptiyle gün boyu yemek ve ikramlar fiyata dahildir; dışarıda ekstra restoran masrafını sıfırlar."
                advisor_en = f"🍹 {concept_en} covers meals and refreshments all day, eliminating extra dining expenses."
            elif "ski" in tags:
                advisor_tr = "⛷️ Kayak pistlerine ve kış sporları merkezine hızlı erişim sağlar; dağ ulaşımı ve ekipman lojistiğinde zaman kazandırır."
                advisor_en = "⛷️ Fast access to ski slopes and winter sports facilities, saving daily mountain transit time."
            elif "thermal" in tags and dest_ctx["is_thermal"]:
                advisor_tr = "♨️ Termal havuz ve spa kullanımı konaklamaya dahildir; sağlık ve dinlenme odaklı seyahatler için yüksek F/P sunar."
                advisor_en = "♨️ Thermal pool and spa access included, offering high value for wellness stays."
            elif "breakfast" in tags and "central" in tags:
                advisor_tr = f"☕ Kahvaltı dahil ve merkeze yakın konumuyla ({h.get('location_label')}), günlük ekstra kahvaltı ve taksi masrafından tasarruf ettirir."
                advisor_en = f"☕ Breakfast included & central location ({h.get('location_label')}) saves daily dining and taxi costs."
            elif p_ratio <= 0.85 and raw_score >= 8.2:
                pct_save = int(round((1.0 - p_ratio) * 100))
                advisor_tr = f"🏷️ Bölge medyan fiyatının %{max(10, min(45, pct_save))} altında olmasına rağmen {raw_score}/10 misafir puanıyla bütçe dostu temiz tercih."
                advisor_en = f"🏷️ {max(10, min(45, pct_save))}% below city median rate while maintaining a strong {raw_score}/10 guest rating."
            else:
                advisor_tr = f"💎 {h.get('location_label')} konumunda {raw_score}/10 misafir memnuniyeti ve doğrulanmış oda fiyatıyla öne çıkan güvenilir seçim."
                advisor_en = f"💎 Verified {raw_score}/10 guest satisfaction in {h.get('location_label')} with direct partner room rates."

            # 7. Doğrudan Otelin Kendi Sayfasına İnen (Tarih ve Kişi Sayısı Dolu) Doğrulanmış Linkler
            q_hotel_city = urllib.parse.quote(f"{name} {city_clean}")

            # Trip.com Doğrudan Otel Detay Linki (/hotels/detail/?hotelId=...)
            trip_hotel_direct = h.get("trip_hotel_url")

            # Enuygun Doğrudan Otel Detay Linki (/otel/detay/{slug}/)
            # SIFIR VARSAYIM KURALI: Asla /otel/bolge/... genel şehir arama sayfasına fallback yapılmaz!
            enuygun_hotel_direct = h.get("enuygun_hotel_url")

            # Etstur Doğrudan Otel Detay Linki (https://www.etstur.com/{ets_slug}?check_in=...)
            # SIFIR VARSAYIM KURALI: Asla 404 veren /Arama?q=... adresine düşürülmez!
            etstur_hotel_direct = h.get("etstur_hotel_url") if not is_international else None

            # Agoda (Türkiye içi ve yurt dışında engelsiz çalışır)
            agoda_hotel_direct = (
                f"https://www.agoda.com/tr-tr/search?"
                f"text={q_hotel_city}&checkIn={cin}&checkOut={cout}"
                f"&rooms=1&adults={guests}&cid={agoda_cid}"
            )

            if is_international:
                booking_hotel_direct = (
                    f"https://www.booking.com/searchresults.html?"
                    f"ss={q_hotel_city}&checkin={cin}&checkout={cout}"
                    f"&group_adults={guests}&no_rooms=1&aid={aid}"
                )
            else:
                booking_hotel_direct = None

            # Birincil kazanan kanal ve buton (Yalnızca doğrulanmış doğrudan otel detay sayfası olan kanallar)
            ep = h.get("enuygun_price")
            tp = h.get("trip_price")
            if ep and tp and enuygun_hotel_direct and trip_hotel_direct:
                if ep <= tp:
                    primary_url = enuygun_hotel_direct
                    primary_provider = "Enuygun Otel"
                else:
                    primary_url = trip_hotel_direct
                    primary_provider = "Trip.com"
            elif enuygun_hotel_direct and (ep or not trip_hotel_direct):
                primary_url = enuygun_hotel_direct
                primary_provider = "Enuygun Otel"
            elif trip_hotel_direct:
                primary_url = trip_hotel_direct
                primary_provider = "Trip.com"
            else:
                continue

            nightly_num = float(h.get("nightly_price") or 0)
            total_num = float(h.get("total_price") or (nightly_num * max(1, nights)))

            # Gösterilecek özet rozetler (최대 3-4 yeşil hap)
            highlight_pills_tr = [concept_tr]
            highlight_pills_en = [concept_en]
            if "free_cancel" in tags:
                highlight_pills_tr.append("Ücretsiz İptal")
                highlight_pills_en.append("Free Cancellation")
            if "beachfront" in tags:
                highlight_pills_tr.append("Denize Sıfır / Plaj")
                highlight_pills_en.append("Beachfront / Pool")
            if "ski" in tags:
                highlight_pills_tr.append("Kayak & Kış Oteli")
                highlight_pills_en.append("Ski & Winter Hotel")
            if "thermal" in tags:
                highlight_pills_tr.append("Termal & Spa")
                highlight_pills_en.append("Thermal & Spa")
            if "pet_friendly" in tags:
                highlight_pills_tr.append("Pati Dostu")
                highlight_pills_en.append("Pet-Friendly")
            for f_item in facs[:3]:
                if len(highlight_pills_tr) < 4 and f_item not in highlight_pills_tr:
                    highlight_pills_tr.append(f_item)
                    highlight_pills_en.append(f_item)

            enriched_list.append({
                "id": f"htl-{idx}-{cls.slugify_hotel_name(name)[:24]}",
                "name": name,
                "stars": stars,
                "stay_sub_type": stay_sub_type,
                "score": round(raw_score, 1),
                "review_score": round(raw_score, 1),
                "bayes_score": round(bayes_score, 2),
                "score_word": h.get("score_word") or "Çok İyi",
                "review_count": rev_count,
                "fp_score": fp_score,
                "fp_badge_tr": fp_badge_tr,
                "fp_badge_en": fp_badge_en,
                "concept_tr": concept_tr,
                "concept_en": concept_en,
                "tags": list(dict.fromkeys(tags)),
                "highlight_pills_tr": highlight_pills_tr[:4],
                "highlight_pills_en": highlight_pills_en[:4],
                "advisor_note_tr": advisor_tr,
                "advisor_note_en": advisor_en,
                "photo": h.get("photo") or "",
                "photo_url": h.get("photo") or "",
                "photos": h.get("photos") or ([h.get("photo")] if h.get("photo") else []),
                "address": h.get("location_label") or h.get("address") or city_clean,
                "location_label": h.get("location_label") or city_clean,
                "distance_center_km": dist_km,
                "city": city_clean,
                "room_name": h.get("room_name") or "",
                "price": round(nightly_num, 2),
                "nightly_price": round(nightly_num, 2),
                "total_price": round(total_num, 2),
                "old_nightly_price": h.get("old_nightly_price"),
                "price_formatted": f"{int(round(nightly_num)):,} {curr_sym}".replace(",", "."),
                "total_price_formatted": f"{int(round(total_num)):,} {curr_sym}".replace(",", "."),
                "enuygun_price": h.get("enuygun_price"),
                "enuygun_price_formatted": f"{int(round(h['enuygun_price'])):,} {curr_sym}".replace(",", ".") if h.get("enuygun_price") else None,
                "trip_price": h.get("trip_price"),
                "trip_price_formatted": f"{int(round(h['trip_price'])):,} {curr_sym}".replace(",", ".") if h.get("trip_price") else None,
                "currency": curr_sym,
                "provider": primary_provider,
                "url": primary_url,
                "direct_url": primary_url,
                "booking_url": booking_hotel_direct if is_international else primary_url,
                "direct_booking_url": booking_hotel_direct,
                "trip_url": trip_hotel_direct,
                "enuygun_url": enuygun_hotel_direct,
                "etstur_url": etstur_hotel_direct,
                "agoda_url": agoda_hotel_direct,
                "is_domestic_tr": not is_international,
            })

        # Varsayılan sıralama: Hakiki F/P Şampiyonu (fp_score azalan, eşitlikte bayes_score azalan)
        enriched_list.sort(key=lambda x: (x.get("fp_score", 0), x.get("bayes_score", 0)), reverse=True)
        return enriched_list

    @staticmethod
    def calculate_dates(checkin_str: str, checkout_str: Optional[str] = None, default_nights: int = 2):
        try:
            cin_dt = datetime.strptime(checkin_str, "%Y-%m-%d")
        except Exception:
            cin_dt = datetime.now() + timedelta(days=7)

        if checkout_str:
            try:
                cout_dt = datetime.strptime(checkout_str, "%Y-%m-%d")
                if cout_dt <= cin_dt:
                    cout_dt = cin_dt + timedelta(days=default_nights)
            except Exception:
                cout_dt = cin_dt + timedelta(days=default_nights)
        else:
            cout_dt = cin_dt + timedelta(days=default_nights)

        nights = max(1, (cout_dt - cin_dt).days)
        return cin_dt.strftime("%Y-%m-%d"), cout_dt.strftime("%Y-%m-%d"), nights

    @classmethod
    def fetch_live_booking_hotels(
        cls, dest_id: str, dest_type: str, cin: str, cout: str, guests: int = 1, currency: str = "TRY"
    ) -> List[Dict[str, Any]]:
        """
        RapidAPI Booking.com üzerinden gerçek otel adı, HD fotoğraf, puan ve net canlı fiyat çeker.
        Doğrudan otele ait oda seçim ekranı linki oluşturur.
        """
        api_key = getattr(settings, "RAPIDAPI_BOOKING_KEY", "")
        api_host = getattr(settings, "RAPIDAPI_BOOKING_HOST", "apidojo-booking-v1.p.rapidapi.com")
        
        if not api_key:
            return []

        cache_key = f"{dest_id}_{dest_type}_{cin}_{cout}_{guests}_{currency}"
        now_ts = time.time()
        if cache_key in cls._HOTEL_CACHE:
            ts, cached_result = cls._HOTEL_CACHE[cache_key]
            if now_ts - ts < cls._CACHE_TTL:
                return cached_result

        now_dt = datetime.now()
        try:
            req_cin_dt = datetime.strptime(cin, "%Y-%m-%d")
            if req_cin_dt.date() < now_dt.date():
                api_cin = (now_dt + timedelta(days=14)).strftime("%Y-%m-%d")
                api_cout = (now_dt + timedelta(days=17)).strftime("%Y-%m-%d")
            else:
                api_cin = cin
                api_cout = cout
        except Exception:
            api_cin = (now_dt + timedelta(days=14)).strftime("%Y-%m-%d")
            api_cout = (now_dt + timedelta(days=17)).strftime("%Y-%m-%d")

        try:
            params = {
                "dest_ids": str(dest_id),
                "search_type": dest_type,
                "arrival_date": api_cin,
                "departure_date": api_cout,
                "adults": str(guests),
                "room_qty": "1",
                "currency_code": currency,
                "units": "metric",
                "languagecode": "tr"
            }
            url = f"https://{api_host}/properties/v2/list?" + urllib.parse.urlencode(params)
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": api_host,
                "User-Agent": "HakikiBilet/1.0"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                raw_hotels = [h for h in payload.get("result", []) if "hotel_name" in h]

                live_list = []
                for h in raw_hotels[:6]:
                    name = h.get("hotel_name")
                    score = h.get("review_score")
                    score_word = h.get("review_score_word", "İyi")
                    photo_raw = h.get("main_photo_url", "")
                    photo_hd = photo_raw.replace("square60", "max500") if photo_raw else ""
                    
                    cpb = h.get("composite_price_breakdown", {})
                    per_night_val = cpb.get("gross_amount_per_night", {}).get("value")
                    total_val = cpb.get("gross_amount", {}).get("value")
                    curr_returned = cpb.get("gross_amount", {}).get("currency", "USD")

                    # Fiyatı hedef para birimine (TRY vb.) çevir
                    if per_night_val:
                        nightly_target = CurrencyService.convert(per_night_val, curr_returned, currency)
                        total_target = CurrencyService.convert(total_val, curr_returned, currency)
                    else:
                        min_tot = h.get("min_total_price", 0)
                        nightly_target = CurrencyService.convert(min_tot / 2, "EUR", currency) if min_tot else 0
                        total_target = CurrencyService.convert(min_tot, "EUR", currency) if min_tot else 0

                    aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
                    agoda_cid = getattr(settings, "AFFILIATE_AGODA_CID", "1924128")
                    trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
                    trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")
                    country_code = (h.get("countrycode") or "gr").lower()
                    hotel_name = name or ""
                    hotel_city = h.get("city") or ""
                    hotel_slug = cls.slugify_hotel_name(hotel_name)
                    is_domestic = (country_code == "tr")

                    # 1. Doğrudan Booking.com Tesis Oda Rezervasyon Sayfası (.html ile temiz parametre)
                    direct_booking = (
                        f"https://www.booking.com/hotel/{country_code}/{hotel_slug}.html?"
                        f"checkin={cin}&checkout={cout}"
                        f"&group_adults={guests}&no_rooms=1"
                        f"&aid={aid}"
                    )
                    # 2. Doğrudan Trip.com Otel Arama & Rezervasyon Ekranı (Global & Türkiye Engelsiz)
                    direct_trip = (
                        f"https://www.trip.com/hotels/list?"
                        f"keyword={urllib.parse.quote(hotel_name + ' ' + hotel_city)}"
                        f"&checkin={cin}&checkout={cout}"
                        f"&crn=1&adult={guests}"
                        f"&Allianceid={trip_aid}&SID={trip_sid}"
                    )
                    # 3. Doğrudan Agoda Canlı Oda ve Fiyat Ekranı (Türkiye içi ve dışı yasal, engelsiz)
                    direct_agoda = (
                        f"https://www.agoda.com/tr-tr/search?"
                        f"text={urllib.parse.quote(hotel_name + ' ' + hotel_city)}"
                        f"&checkIn={cin}&checkOut={cout}&rooms=1&adults={guests}"
                        f"&cid={agoda_cid}"
                    )
                    # 4. Doğrudan Google Hotels Karşılaştırma Ekranı
                    direct_google = (
                        f"https://www.google.com/travel/hotels?"
                        f"q={urllib.parse.quote(hotel_name + ' ' + hotel_city)}"
                    )

                    # Türkiye içindeki otellerde Booking.com Türk IP'lerine mahkeme kararıyla kapalı olduğundan,
                    # yerli otellerde birincil link Trip.com / Agoda atanır. Yurt dışında ise doğrudan Booking.com / Trip.com verilir.
                    if is_domestic:
                        primary_url = direct_trip
                        primary_provider = "Trip.com"
                    else:
                        primary_url = direct_booking
                        primary_provider = "Booking.com"

                    curr_sym = CurrencyService.get_symbol(currency)
                    live_list.append({
                        "name": name,
                        "score": round(score, 1) if score else 9.0,
                        "review_score": round(score, 1) if score else 9.0,
                        "score_word": score_word,
                        "photo": photo_hd,
                        "photo_url": photo_hd,
                        "address": h.get("address", h.get("city", "")),
                        "city": hotel_city,
                        "price": round(nightly_target, 2),
                        "nightly_price": round(nightly_target, 2),
                        "total_price": round(total_target, 2),
                        "price_formatted": f"{int(round(nightly_target)):,} {curr_sym}".replace(",", "."),
                        "total_price_formatted": f"{int(round(total_target)):,} {curr_sym}".replace(",", "."),
                        "currency": curr_sym,
                        "booking_url": primary_url,
                        "url": primary_url,
                        "direct_url": primary_url,
                        "direct_booking_url": direct_booking,
                        "trip_url": direct_trip,
                        "agoda_url": direct_agoda,
                        "google_url": direct_google,
                        "provider": primary_provider,
                        "is_domestic_tr": is_domestic
                    })

                cls._HOTEL_CACHE[cache_key] = (now_ts, live_list)
                return live_list
        except Exception as e:
            logger.warning(f"RapidAPI Booking fetch warning: {e}")
            return []

    @classmethod
    def _get_fallback_hotels(
        cls,
        city_clean: str,
        city_slug: str,
        cin: str,
        cout: str,
        nights: int,
        guests: int,
        currency: str,
        is_international: bool,
        dest_id: Optional[str] = None,
        dest_type: str = "city"
    ) -> List[Dict[str, Any]]:
        # SIFIR VARSAYIM KURALI: Canlı API'den doğrulanmış gerçek otel odası gelmediyse
        # ASLA hayali gecelik fiyat veya uydurma otel üretilmez.
        # Kullanıcı doğrudan Trip.com, Booking.com, Enuygun ve Agoda'nın canlı sonuçlarına yönlendirilir.
        return []

    @classmethod
    def get_hotel_recommendation(
        cls,
        dest_city: str,
        checkin_date: str,
        checkout_date: Optional[str] = None,
        guests: int = 1,
        currency: str = "TRY"
    ) -> Dict[str, Any]:
        """
        Kullanıcının seyahat tarihlerini ve varış şehrini alarak:
        1. Varsa RapidAPI Booking.com'dan CANLI ve GERÇEK otel odalarını çeker.
        2. Yurt dışı/adalarda Enuygun linkini kaldırıp Booking ve Agoda'ya kusursuz yönlendirir.
        """
        cin, cout, nights = cls.calculate_dates(checkin_date, checkout_date)
        city_clean = cls.sanitize_hotel_city_name(dest_city)
        city_slug = (
            city_clean.replace("İ", "i")
            .replace("I", "i")
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("Ş", "s")
            .replace("ç", "c")
            .replace("Ç", "c")
            .replace("ö", "o")
            .replace("Ö", "o")
            .replace("ü", "u")
            .replace("Ü", "u")
            .replace("ğ", "g")
            .replace("Ğ", "g")
            .lower()
            .replace("\u0307", "")
            .replace(" ", "-")
        )
        
        # Destinasyonun yurt dışı / ada kontrolü (Önce şehir veritabanından, yoksa harita ve Trip.com ülke bilgisinden teyit)
        from app.cities import find_city
        matched_loc = find_city(dest_city) or find_city(city_clean)
        dest_meta = cls.DEST_ID_MAP.get(city_slug)

        intl_slugs = {
            "sakiz-adasi", "sakiz", "chios", "rodos-adasi", "rodos", "rhodes",
            "kos-adasi", "kos", "midilli-adasi", "midilli", "lesbos", "mytilene",
            "samos-adasi", "samos", "simi-adasi", "simi", "meis-adasi", "meis",
            "santorini", "mikonos", "mykonos", "girne", "lefkosa", "gazimagusa", "magusa",
            "kibris", "kktc", "paris", "londra", "roma", "milano", "venedik", "barselona",
            "madrid", "amsterdam", "berlin", "munih", "frankfurt", "viyana", "prag",
            "budapeste", "atina", "selanik", "sofya", "bukres", "belgrad", "saraybosna",
            "uskup", "tiran", "tiflis", "batum", "baku", "dubai", "abu-dabi", "doha",
            "kahire", "tokyo", "seul", "bangkok", "new-york", "nice", "monaco", "zurih",
            "cenevre", "bruksel", "lizbon", "kopenhag", "stockholm", "oslo", "varsova",
            "moskova", "podgorica", "pristine",
        }

        currency = (currency or "TRY").upper()
        curr_sym = CurrencyService.get_symbol(currency)
        aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
        agoda_cid = getattr(settings, "AFFILIATE_AGODA_CID", "1924128")
        trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
        trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")

        trip_meta = cls.resolve_trip_city_meta(city_clean, city_slug, trip_aid=trip_aid, trip_sid=trip_sid)
        trip_city_id = int(trip_meta["id"]) if (trip_meta and trip_meta.get("id")) else None
        trip_country = str((trip_meta or {}).get("country") or "").strip()

        if city_slug in intl_slugs:
            is_international = True
        elif matched_loc and (matched_loc.get("is_international") or (matched_loc.get("country") and matched_loc.get("country") != "Türkiye")):
            is_international = True
        elif dest_meta and dest_meta.get("is_intl"):
            is_international = True
        elif trip_country and trip_country.lower() not in ("türkiye", "turkiye", "turkey", "tr"):
            is_international = True
        else:
            is_international = bool("adasi" in city_slug and city_slug not in ("avsa-adasi", "marmara-adasi", "bozcaada", "gokceada", "cunda", "alibey-adasi"))

        dest_id = dest_meta.get("dest_id") if dest_meta else None
        dest_type = dest_meta.get("dest_type", "city") if dest_meta else "city"

        # 1. Trip.com Otel Resmi Seviye-3 Derin Arama Linki (Doğrulanmış cityId ile asla '0 properties found' vermez)
        trip_hotel_url = cls.resolve_trip_hotel_url(
            city_clean=city_clean,
            city_slug=city_slug,
            cin=cin,
            cout=cout,
            guests=guests,
            is_international=is_international,
            trip_aid=trip_aid,
            trip_sid=trip_sid,
        )

        # 2. Booking.com (Sadece Yurt Dışı) & Agoda (Yurt İçi + Yurt Dışı Engelsiz)
        dest_q = f"&dest_id={dest_id}&dest_type={dest_type}" if dest_id else ""
        agoda_url = (
            f"https://www.agoda.com/tr-tr/search?"
            f"text={urllib.parse.quote(city_clean)}"
            f"&checkIn={cin}&checkOut={cout}&rooms=1&adults={guests}"
            f"&cid={agoda_cid}"
        )
        if is_international:
            booking_url = (
                f"https://www.booking.com/searchresults.html?"
                f"ss={urllib.parse.quote(city_clean)}"
                f"{dest_q}"
                f"&checkin={cin}&checkout={cout}"
                f"&group_adults={guests}&no_rooms=1"
                f"&sb=1"
                f"&aid={aid}"
            )
        else:
            booking_url = None

        # 3. Enuygun Otel (/otel/bolge/...), Obilet Otel, Bilet.com Otel & Etstur Linkleri
        from app.services.revenue_service import RevenueService
        try:
            cin_dt = datetime.strptime(cin, "%Y-%m-%d")
            cout_dt = datetime.strptime(cout, "%Y-%m-%d")
            enuygun_cin = cin_dt.strftime("%d.%m.%Y")
            enuygun_cout = cout_dt.strftime("%d.%m.%Y")
        except Exception:
            enuygun_cin, enuygun_cout = cin, cout

        en_region_slug = cls.resolve_enuygun_region_slug(city_clean, city_slug)

        if not is_international:
            raw_enuygun_url = cls.resolve_enuygun_hotel_url(
                city_clean=city_clean,
                city_slug=city_slug,
                enuygun_cin=enuygun_cin,
                enuygun_cout=enuygun_cout,
                guests=guests,
            )
            enuygun_url = RevenueService.enrich_url(
                raw_enuygun_url,
                provider="enuygun",
                vertical="hotel",
            )
            obilet_hotel_url = RevenueService.enrich_url(
                f"https://www.obilet.com/otel/{city_slug}-otelleri",
                provider="obilet",
                vertical="hotel",
            )
            bilet_hotel_url = RevenueService.enrich_url(
                f"https://www.bilet.com/otel/arama?location=turkiye-{city_slug}&checkin={enuygun_cin}&checkout={enuygun_cout}&guests={guests}",
                provider="biletcom",
                vertical="hotel",
            )
            ets_slug = "-".join(w.capitalize() for w in city_slug.split("-") if w)
            etstur_url = RevenueService.enrich_url(
                f"https://www.etstur.com/{ets_slug}-Otelleri?check_in={enuygun_cin}&check_out={enuygun_cout}&adult_1={guests}",
                provider="etstur",
                vertical="hotel",
            )
            primary_city_url = trip_hotel_url
            primary_provider = "Trip.com"
        else:
            if en_region_slug:
                raw_enuygun_url = (
                    f"https://www.enuygun.com/otel/bolge/{en_region_slug}/?"
                    f"checkInDate={enuygun_cin}&checkOutDate={enuygun_cout}&rooms={guests}"
                )
                enuygun_url = RevenueService.enrich_url(
                    raw_enuygun_url,
                    provider="enuygun",
                    vertical="hotel",
                )
            else:
                enuygun_url = None
            obilet_hotel_url = None
            bilet_hotel_url = None
            etstur_url = None
            primary_city_url = trip_hotel_url
            primary_provider = "Trip.com"

        # 4. CANLI MULTI-SOURCE OTEL MOTORU (Enuygun SSR + Trip.com SSR + Hakiki F/P Algoritması)
        live_cache_key = f"faz1_v4_live_{city_slug}_{cin}_{cout}_{guests}_{currency}_{int(is_international)}"
        now_ts = time.time()
        live_hotels: List[Dict[str, Any]] = []

        if live_cache_key in cls._HOTEL_CACHE:
            ts, cached_hotels = cls._HOTEL_CACHE[live_cache_key]
            if now_ts - ts < cls._CACHE_TTL and cached_hotels:
                live_hotels = cached_hotels

        if not live_hotels:
            en_list: List[Dict[str, Any]] = []
            tr_list: List[Dict[str, Any]] = []
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_en = (
                    pool.submit(
                        cls.fetch_live_enuygun_hotels,
                        en_region_slug,
                        city_clean,
                        city_slug,
                        cin,
                        cout,
                        enuygun_cin,
                        enuygun_cout,
                        nights,
                        guests,
                        currency,
                    )
                    if en_region_slug
                    else None
                )
                fut_tr = (
                    pool.submit(
                        cls.fetch_live_trip_hotels,
                        trip_city_id,
                        city_clean,
                        city_slug,
                        cin,
                        cout,
                        nights,
                        guests,
                        currency,
                        is_international,
                    )
                    if trip_city_id
                    else None
                )
                if fut_en:
                    try:
                        en_list = fut_en.result(timeout=7.5) or []
                    except Exception as e:
                        logger.warning(f"Enuygun future timeout/error ({city_slug}): {e}")
                if fut_tr:
                    try:
                        tr_list = fut_tr.result(timeout=7.5) or []
                    except Exception as e:
                        logger.warning(f"Trip.com future timeout/error ({city_slug}): {e}")

            if en_list or tr_list:
                live_hotels = cls.merge_and_score_live_hotels(
                    enuygun_hotels=en_list,
                    trip_hotels=tr_list,
                    city_clean=city_clean,
                    city_slug=city_slug,
                    city_id=trip_city_id,
                    cin=cin,
                    cout=cout,
                    enuygun_cin=enuygun_cin,
                    enuygun_cout=enuygun_cout,
                    nights=nights,
                    guests=guests,
                    currency=currency,
                    is_international=is_international,
                )
                if live_hotels:
                    cls._HOTEL_CACHE[live_cache_key] = (now_ts, live_hotels)

        # Yurt dışında RapidAPI Booking yedeği
        if not live_hotels and dest_id and is_international:
            live_hotels = cls.fetch_live_booking_hotels(
                dest_id=dest_id,
                dest_type=dest_type,
                cin=cin,
                cout=cout,
                guests=guests,
                currency=currency
            )

        if not live_hotels:
            live_hotels = cls._get_fallback_hotels(
                city_clean=city_clean,
                city_slug=city_slug,
                cin=cin,
                cout=cout,
                nights=nights,
                guests=guests,
                currency=currency,
                is_international=is_international,
                dest_id=dest_id,
                dest_type=dest_type
            )

        dest_context = cls.get_destination_context(city_slug, is_international)
        profile = cls.CITY_HOTEL_PROFILES.get(city_slug, {"min_try": 0, "max_try": 0, "label": f"{city_clean} Merkez"})
        has_live = len(live_hotels) > 0
        min_rate = min((h["nightly_price"] for h in live_hotels if h.get("nightly_price")), default=0.0) if has_live else None
        max_rate = max((h["nightly_price"] for h in live_hotels if h.get("nightly_price")), default=0.0) if has_live else None

        # Kategori kartları (Sıfır Varsayım: Canlı veya doğrudan parametrik derin link)
        second_cat_action = "Booking.com'da İncele ↗" if is_international else "Obilet Otel'de İncele ↗"
        second_cat_link = booking_url if is_international else (obilet_hotel_url or trip_hotel_url)
        categories = [
            {
                "title": "🌟 Bütçe Dostu & Şehir Butik Otelleri",
                "badge": "Canlı Müsaitlik",
                "badge_color": "emerald",
                "desc": f"{city_clean} merkezinde gezginlerin en çok tercih ettiği ekonomik ve butik oteller.",
                "est_nightly": round(min_rate, 2) if min_rate else None,
                "est_total": round(min_rate * nights, 2) if min_rate else None,
                "action_text": "Trip.com'da Odaları Gör ↗",
                "link": trip_hotel_url
            },
            {
                "title": "🏨 Merkez & Sahil / 4 Yıldız Konfor",
                "badge": "Popüler Seçim",
                "badge_color": "blue",
                "desc": "Turistik noktalara, limana ve merkeze yürüme mesafesinde konforlu oteller.",
                "est_nightly": round((min_rate + max_rate) / 2, 2) if (min_rate and max_rate) else None,
                "est_total": round(((min_rate + max_rate) / 2) * nights, 2) if (min_rate and max_rate) else None,
                "action_text": second_cat_action,
                "link": second_cat_link
            },
            {
                "title": "💎 Taş Konak & Premium Resort Seçenekleri",
                "badge": "Üst Düzey Puan",
                "badge_color": "purple",
                "desc": "Tarihi taş mimarili oteller, deniz manzaralı süitler ve spa otelleri.",
                "est_nightly": round(max_rate, 2) if max_rate else None,
                "est_total": round(max_rate * nights, 2) if max_rate else None,
                "action_text": f"{'Enuygun Otel' if enuygun_url else 'Agoda'}'da İncele ↗",
                "link": enuygun_url or agoda_url or trip_hotel_url
            }
        ]

        return {
            "destination": city_clean,
            "city_slug": city_slug,
            "trip_city_id": trip_city_id,
            "destination_context": dest_context,
            "region_label": dest_meta.get("label", profile["label"]) if dest_meta else profile["label"],
            "checkin_date": cin,
            "checkout_date": cout,
            "enuygun_cin": enuygun_cin,
            "enuygun_cout": enuygun_cout,
            "nights": nights,
            "guests": guests,
            "currency": curr_sym,
            "currency_code": currency,
            "is_international": is_international,
            "avg_nightly_min": round(min_rate, 2) if min_rate else None,
            "avg_nightly_max": round(max_rate, 2) if max_rate else None,
            "total_stay_min": round(min_rate * nights, 2) if min_rate else None,
            "total_stay_max": round(max_rate * nights, 2) if max_rate else None,
            "is_live": has_live,
            "live_hotels": live_hotels,
            "booking_url": booking_url,
            "primary_city_url": primary_city_url,
            "primary_provider": primary_provider,
            "enuygun_url": enuygun_url,
            "obilet_hotel_url": obilet_hotel_url,
            "bilet_hotel_url": bilet_hotel_url,
            "etstur_url": etstur_url,
            "agoda_url": agoda_url,
            "trip_hotel_url": trip_hotel_url,
            "deep_links": {
                "trip": trip_hotel_url,
                "booking": booking_url,
                "agoda": agoda_url,
                "enuygun": enuygun_url,
                "obilet": obilet_hotel_url,
                "bilet": bilet_hotel_url,
                "etstur": etstur_url,
                "primary": primary_city_url
            },
            "categories": categories,
            "disclaimer": "Oda ve kesin fiyatlar anlık doluluk ve oda tipine göre doğrudan sağlayıcı sisteminde teyit edilir."
        }
