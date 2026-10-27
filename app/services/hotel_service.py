import urllib.parse
import urllib.request
import json
import time
import logging
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
    _CACHE_TTL = 7200  # 2 saat

    # Trip.com Doğrulanmış City ID Haritası (Asla '0 properties found' veya boş arama kutusu vermez)
    TRIP_CITY_ID_MAP: Dict[str, Dict[str, Any]] = {
        "istanbul": {"id": 532, "name": "İstanbul"},
        "ankara": {"id": 1218, "name": "Ankara"},
        "izmir": {"id": 1216, "name": "İzmir"},
        "antalya": {"id": 1217, "name": "Antalya"},
        "bodrum": {"id": 1761, "name": "Bodrum"},
        "fethiye": {"id": 3773, "name": "Fethiye"},
        "marmaris": {"id": 3775, "name": "Marmaris"},
        "dalaman": {"id": 1749, "name": "Dalaman"},
        "cesme": {"id": 3772, "name": "Çeşme"},
        "alacati": {"id": 243200, "name": "Alaçatı"},
        "kusadasi": {"id": 40519, "name": "Kuşadası"},
        "didim": {"id": 40486, "name": "Didim"},
        "ayvalik": {"id": 40475, "name": "Ayvalık"},
        "alanya": {"id": 40464, "name": "Alanya"},
        "kemer": {"id": 40513, "name": "Kemer"},
        "belek": {"id": 1217, "name": "Belek Antalya"},
        "side": {"id": 1217, "name": "Side Antalya"},
        "kas": {"id": 40510, "name": "Kaş"},
        "trabzon": {"id": 1760, "name": "Trabzon"},
        "rize": {"id": 40521, "name": "Rize"},
        "samsun": {"id": 1758, "name": "Samsun"},
        "ordu": {"id": 20002, "name": "Ordu"},
        "giresun": {"id": 53013, "name": "Giresun"},
        "sinop": {"id": 20797, "name": "Sinop"},
        "artvin": {"id": 61168, "name": "Artvin"},
        "kars": {"id": 7238, "name": "Kars"},
        "erzurum": {"id": 1754, "name": "Erzurum"},
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
        "nevsehir": {"id": 7732, "name": "Nevşehir"},
        "kapadokya": {"id": 7732, "name": "Kapadokya"},
        "urgup": {"id": 9169, "name": "Ürgüp"},
        "goreme": {"id": 9660, "name": "Göreme"},
        "konya": {"id": 1757, "name": "Konya"},
        "eskisehir": {"id": 9585, "name": "Eskişehir"},
        "bursa": {"id": 4898, "name": "Bursa"},
        "sapanca": {"id": 40533, "name": "Sapanca"},
        "abant": {"id": 705625, "name": "Abant Bolu"},
        "canakkale": {"id": 7636, "name": "Çanakkale"},
        "bozcaada": {"id": 40483, "name": "Bozcaada"},
        "balikesir": {"id": 4999, "name": "Balıkesir"},
        "edremit": {"id": 684699, "name": "Edremit"},
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
        "zonguldak": {"id": 53144, "name": "Zonguldak"},
        "bolu": {"id": 705625, "name": "Bolu"},
        "edirne": {"id": 40471, "name": "Edirne"},
        "tekirdag": {"id": 53125, "name": "Tekirdağ"},
        "kocaeli": {"id": 40315, "name": "Kocaeli"},
        "sakarya": {"id": 40315, "name": "Sakarya"},
        "yalova": {"id": 62336, "name": "Yalova"},
        "afyonkarahisar": {"id": 6660, "name": "Afyonkarahisar"},
        "kutahya": {"id": 20531, "name": "Kütahya"},
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
        "dalaman": "dalaman-1031",
        "cesme": "cesme-4275",
        "alacati": "alacati-6054832",
        "kusadasi": "kusadasi-4227",
        "didim": "didim-6069857",
        "ayvalik": "ayvalik-4498",
        "alanya": "alanya-4671",
        "kemer": "kemer-8281",
        "belek": "belek-6034717",
        "side": "antalya-481",
        "kas": "kas-6047444",
        "trabzon": "trabzon-3597",
        "rize": "rize-4473",
        "samsun": "samsun-3278",
        "ordu": "ordu-4654",
        "giresun": "giresun-4555",
        "sinop": "sinop-6063189",
        "artvin": "artvin-6323606",
        "kars": "kars-1931",
        "erzurum": "erzurum-1161",
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
        "nevsehir": "nevsehir-4605",
        "kapadokya": "nevsehir-4605",
        "urgup": "urgup-4423",
        "goreme": "goreme-6224480",
        "konya": "konya-8367",
        "eskisehir": "eskisehir-7119",
        "bursa": "bursa-6431",
        "sapanca": "sapanca-6049293",
        "abant": "abant-6321966",
        "canakkale": "canakkale-857",
        "bozcaada": "bozcaada-6125621",
        "balikesir": "balikesir-553248635924013473",
        "edremit": "edremit-6063182",
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
        "zonguldak": "zonguldak-4416",
        "bolu": "bolu-4644",
        "edirne": "edirne-5280",
        "tekirdag": "tekirdag-5282",
        "kocaeli": "kocaeli-553248635924013345",
        "sakarya": "sakarya-6242347",
        "yalova": "yalova-4946",
        "afyonkarahisar": "afyonkarahisar-6056",
        "kutahya": "kutahya-4458",
        "batman": "batman-493",
        "siirt": "siirt-3339",
        "sirnak": "sirnak-6323236",
        "hakkari": "hakkari-4617",
        "mus": "mus-2428",
        "bingol": "bingol-4616",
        "tunceli": "tunceli-6323547",
        "adiyaman": "adiyaman-4615",
    }

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
        meta = cls.TRIP_CITY_ID_MAP.get(city_slug)

        if not meta:
            try:
                body = json.dumps({
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
                req = urllib.request.Request(
                    "https://tr.trip.com/restapi/soa2/34951/getHotelKeywords",
                    data=body,
                    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    rdata = json.loads(resp.read().decode("utf-8", "ignore"))
                    kw_list = rdata.get("data", {}).get("mainKeywordList", {}).get("keywords", [])
                    if kw_list:
                        kinfo = kw_list[0].get("keyword", {}).get("keywordContentInfo", {})
                        kid = kinfo.get("keywordId")
                        kname = kinfo.get("content") or city_clean
                        if kid:
                            meta = {"id": int(kid), "name": kname}
                            cls.TRIP_CITY_ID_MAP[city_slug] = meta
            except Exception:
                pass

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
        en_slug = cls.ENUYGUN_HOTEL_SLUG_MAP.get(city_slug)
        if not en_slug:
            try:
                u = f"https://hot-autocomplete-api.enuygun.com/api/v1/autocomplete?q={urllib.parse.quote(city_clean)}&locale=tr"
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    items = json.loads(resp.read().decode("utf-8", "ignore"))
                    if isinstance(items, list) and items:
                        s = items[0].get("slug") or items[0].get("url")
                        if s:
                            en_slug = str(s).strip("/").split("/")[-1]
                            cls.ENUYGUN_HOTEL_SLUG_MAP[city_slug] = en_slug
            except Exception:
                pass
        if not en_slug:
            en_slug = city_slug
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
        import re
        s = (name or "").lower()
        for tr_c, en_c in [
            ('ı', 'i'), ('ş', 's'), ('ç', 'c'), ('ğ', 'g'), ('ü', 'u'), ('ö', 'o'),
            ('’', ''), ("'", ""), ('"', ''), ('&', 'and'), ('.', '')
        ]:
            s = s.replace(tr_c, en_c)
        s = re.sub(r'[^a-z0-9]+', '-', s)
        return s.strip('-')

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
        city_clean = dest_city.split("(")[0].strip()
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
        
        # Destinasyonun yurt dışı / ada kontrolü (Önce şehir veritabanından, yoksa haritadan teyit)
        from app.cities import find_city
        matched_loc = find_city(dest_city)
        dest_meta = cls.DEST_ID_MAP.get(city_slug)
        if matched_loc and "is_international" in matched_loc:
            is_international = bool(matched_loc.get("is_international", False))
        elif dest_meta:
            is_international = bool(dest_meta.get("is_intl", False))
        else:
            is_international = bool("adasi" in city_slug or "island" in city_slug or "nce" in city_slug or "nice" in city_slug)
            
        dest_id = dest_meta.get("dest_id") if dest_meta else None
        dest_type = dest_meta.get("dest_type", "city") if dest_meta else "city"

        currency = (currency or "TRY").upper()
        curr_sym = CurrencyService.get_symbol(currency)
        aid = getattr(settings, "AFFILIATE_BOOKING_AID", "585474")
        trip_aid = getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531")
        trip_sid = getattr(settings, "AFFILIATE_TRIP_SID", "333747492")

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

        # 2. Booking.com & Agoda (SADECE YURT DIŞI / ULUSLARARASI DESTİNASYONLARDA AKTİF!
        # Türkiye içi şehirlerde Booking.com Türk IP'lerine mahkeme kararıyla kapalıdır ve Kars ➔ Karlsruhe gibi yanlış yönlendirme + kırmızı uyarı verir)
        dest_q = f"&dest_id={dest_id}&dest_type={dest_type}" if dest_id else ""
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
            agoda_url = (
                f"https://www.agoda.com/tr-tr/search?"
                f"city={urllib.parse.quote(city_clean)}"
                f"&checkIn={cin}&checkOut={cout}&rooms=1&adults={guests}"
                f"&cid={settings.AFFILIATE_AGODA_CID}"
            )
        else:
            booking_url = None
            agoda_url = None

        # 3. Enuygun Otel (/otel/bolge/...), Obilet Otel, Bilet.com Otel & Etstur Linkleri (YURT İÇİ TÜRKİYE İÇİN AKTİF)
        from app.services.revenue_service import RevenueService
        if not is_international:
            try:
                cin_dt = datetime.strptime(cin, "%Y-%m-%d")
                cout_dt = datetime.strptime(cout, "%Y-%m-%d")
                enuygun_cin = cin_dt.strftime("%d.%m.%Y")
                enuygun_cout = cout_dt.strftime("%d.%m.%Y")
            except Exception:
                enuygun_cin, enuygun_cout = cin, cout

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
                f"https://www.etstur.com/{ets_slug}-Otelleri",
                provider="etstur",
                vertical="hotel",
            )
            primary_city_url = trip_hotel_url
            primary_provider = "Trip.com"
        else:
            enuygun_url = None
            obilet_hotel_url = None
            bilet_hotel_url = None
            etstur_url = None
            primary_city_url = trip_hotel_url
            primary_provider = "Trip.com"

        # 4. CANLI BOOKING.COM VERİSİ SORGULA (Yalnızca yurt dışı destinasyonlarda)
        live_hotels = []
        if dest_id and is_international:
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
            "region_label": dest_meta.get("label", profile["label"]) if dest_meta else profile["label"],
            "checkin_date": cin,
            "checkout_date": cout,
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
