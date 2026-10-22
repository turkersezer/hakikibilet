"""
Merkezi Sağlayıcı ve Derin Bağlantı Kayıt Defteri (Universal Provider & Deep-Link Registry)

Hakiki Bilet'in tüm havayolları (Pegasus, AJet, THY, SunExpress, Corendon vb.)
ve aracı acente / meta arama motorları (Trip.com, Booking/Kayak, Skyscanner, Kiwi, Enuygun, Turna, Obilet vb.)
için tek ve kurallı sözleşmesidir (KURAL 3).

Kurallar:
1. EN UCUZ FİYAT HER ZAMAN KAZANIR.
2. FİYAT EŞİTLİĞİNDE (TIE): Aktif gelir ortaklığı (affiliate) olan sağlayıcı kazanır.
3. BUTON METNİ VE LİNK %100 BİREBİR KİLİTLİDİR:
   - Kazanan Trip.com ise: "Trip.com'dan Al" -> Trip.com linki.
   - Kazanan Booking ise: "Booking'den Al" -> Kayak / Booking linki.
   - Kazanan Skyscanner ise: "Skyscanner'dan Al" -> Skyscanner linki.
   - Kazanan Pegasus ise: "Pegasus'tan Al" -> Pegasus resmi linki.
   - Kazanan SunExpress ise: "SunExpress'ten Al" -> SunExpress resmi linki.
   - Asla bir sağlayıcının adı yazıp başkasının linkine yönlendirilemez.
4. KURUŞ FARKI VE YUVARLAMA KURALI:
   - Tüm TL fiyatları tam sayıya yuvarlanır (Ör: 2.477 ₺, 2.501 ₺).
"""

from typing import List, Dict, Any, Optional, Tuple
import urllib.parse
from datetime import datetime
import logging
from app.config import settings

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. SAĞLAYICI KAYIT DEFTERİ (PROVIDER DEFINITIONS)
# ==============================================================================

PROVIDERS_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- GELİR ORTAKLARI (OTA / META) ---
    "trip": {
        "id": "trip",
        "name": "Trip.com",
        "channel": "trip",
        "category": "ota",
        "prefix_tr": "Trip.com'dan",
        "prefix_en": "Trip.com",
        "pill_css": "bg-sky-50 text-sky-950 border border-sky-300 font-bold shadow-2xs hover:bg-sky-100",
        "pill_icon": '<i class="fa-solid fa-plane text-sky-600 text-[9px]"></i>',
        "active_affiliate": True,
        "default_rank": 100,
    },
    "booking": {
        "id": "booking",
        "name": "Booking.com Flights",
        "channel": "booking",
        "category": "ota",
        "prefix_tr": "Booking'den",
        "prefix_en": "Booking.com",
        "pill_css": "bg-blue-50 text-blue-950 border border-blue-300 font-bold shadow-2xs hover:bg-blue-100",
        "pill_icon": '<i class="fa-solid fa-plane-departure text-blue-700 text-[9px]"></i>',
        "active_affiliate": True,
        "default_rank": 80,
    },
    "skyscanner": {
        "id": "skyscanner",
        "name": "Skyscanner",
        "channel": "skyscanner",
        "category": "meta",
        "prefix_tr": "Skyscanner'dan",
        "prefix_en": "Skyscanner",
        "pill_css": "bg-cyan-50 text-cyan-950 border border-cyan-300 font-bold shadow-2xs hover:bg-cyan-100",
        "pill_icon": '<i class="fa-solid fa-compass text-cyan-700 text-[9px]"></i>',
        "active_affiliate": False,
        "default_rank": 60,
    },
    "kiwi": {
        "id": "kiwi",
        "name": "Kiwi.com",
        "channel": "kiwi",
        "category": "ota",
        "prefix_tr": "Kiwi.com'dan",
        "prefix_en": "Kiwi.com",
        "pill_css": "bg-teal-50 text-teal-950 border border-teal-300 font-bold shadow-2xs hover:bg-teal-100",
        "pill_icon": '<i class="fa-solid fa-bolt text-teal-600 text-[9px]"></i>',
        "active_affiliate": True,
        "default_rank": 85,
    },
    "agency": {
        "id": "agency",
        "name": "Enuygun",
        "channel": "agency",
        "category": "ota",
        "prefix_tr": "Enuygun'dan",
        "prefix_en": "Enuygun",
        "pill_css": "bg-emerald-50 text-emerald-950 border border-emerald-300 font-bold shadow-2xs hover:bg-emerald-100",
        "pill_icon": '<i class="fa-solid fa-ticket text-emerald-600 text-[9px]"></i>',
        "active_affiliate": False,
        "default_rank": 70,
    },
    "turna": {
        "id": "turna",
        "name": "Turna",
        "channel": "turna",
        "category": "ota",
        "prefix_tr": "Turna'dan",
        "prefix_en": "Turna",
        "pill_css": "bg-orange-50 text-orange-950 border border-orange-300 font-bold shadow-2xs hover:bg-orange-100",
        "pill_icon": '<i class="fa-solid fa-dove text-orange-600 text-[9px]"></i>',
        "active_affiliate": False,
        "default_rank": 50,
    },
    "obilet": {
        "id": "obilet",
        "name": "Obilet",
        "channel": "obilet",
        "category": "ota",
        "prefix_tr": "Obilet'ten",
        "prefix_en": "Obilet",
        "pill_css": "bg-rose-50 text-rose-950 border border-rose-300 font-bold shadow-2xs hover:bg-rose-100",
        "pill_icon": '<i class="fa-solid fa-ticket-simple text-rose-600 text-[9px]"></i>',
        "active_affiliate": False,
        "default_rank": 75,
    },
    # --- RESMİ HAVAYOLLARI (OFFICIAL CARRIERS) ---
    "official_pegasus": {
        "id": "official_pegasus",
        "name": "Pegasus Resmi",
        "channel": "official",
        "category": "airline",
        "prefix_tr": "Pegasus'tan",
        "prefix_en": "Pegasus",
        "carrier_codes": ["PC"],
        "default_rank": 10,
    },
    "official_ajet": {
        "id": "official_ajet",
        "name": "AJet Resmi",
        "channel": "official",
        "category": "airline",
        "prefix_tr": "AJet'ten",
        "prefix_en": "AJet",
        "carrier_codes": ["VF"],
        "default_rank": 10,
    },
    "official_thy": {
        "id": "official_thy",
        "name": "THY Resmi",
        "channel": "official",
        "category": "airline",
        "prefix_tr": "THY'den",
        "prefix_en": "THY",
        "carrier_codes": ["TK"],
        "default_rank": 10,
    },
    "official_sunexpress": {
        "id": "official_sunexpress",
        "name": "SunExpress Resmi",
        "channel": "official",
        "category": "airline",
        "prefix_tr": "SunExpress'ten",
        "prefix_en": "SunExpress",
        "carrier_codes": ["XQ"],
        "default_rank": 10,
    },
    "official_generic": {
        "id": "official_generic",
        "name": "Resmi Havayolu",
        "channel": "official",
        "category": "airline",
        "prefix_tr": "Havayolundan",
        "prefix_en": "Official Airline",
        "carrier_codes": [],
        "default_rank": 10,
    },
}


# ==============================================================================
# 2. HAVAYOLU RESMİ BİLGİ VE LİNK ÜRETİCİ
# ==============================================================================

def resolve_carrier_meta(
    carrier_name: str,
    carrier_code: str,
    from_code: str,
    to_code: str,
    dep_date: str,
    ret_date: Optional[str] = None,
    is_round: bool = False,
    adults: int = 1,
    cabin_class: str = "economy"
) -> Dict[str, Any]:
    """
    Havayolu ismine ve IATA koduna göre (PC, VF, TK, XQ vb.) doğru Türkçe takı,
    resmi arama bağlantısı ve gösterim etiketlerini oluşturur.
    """
    c_lower = (carrier_name or "").lower()
    c_code = (carrier_code or "").upper()
    
    # Pegasus (PC)
    if "pegasus" in c_lower or c_code == "PC" or "flypgs" in c_lower:
        display_name = "Pegasus Airlines"
        official_name = "Pegasus Resmi"
        prefix_tr = "Pegasus'tan"
        prefix_en = "Pegasus"
        provider_id = "official_pegasus"
        badge = "Comfort Flex ⭐" if cabin_class == "business" else "Pegasus Seferi"
        # Pegasus rota bazlı doğrudan arama linki
        if is_round and ret_date:
            official_link = f"https://web.flypgs.com/booking?departureAirport={from_code}&arrivalAirport={to_code}&departureDate={dep_date}&returnAirport={from_code}&returnDate={ret_date}&currency=TRY&adultCount={adults}"
        else:
            official_link = f"https://web.flypgs.com/booking?departureAirport={from_code}&arrivalAirport={to_code}&departureDate={dep_date}&currency=TRY&adultCount={adults}"

    # AJet / AnadoluJet (VF)
    elif "ajet" in c_lower or "anadolu" in c_lower or c_code == "VF":
        display_name = "AJet (AnadoluJet)"
        official_name = "AJet Resmi"
        prefix_tr = "AJet'ten"
        prefix_en = "AJet"
        provider_id = "official_ajet"
        badge = "Business ⭐" if cabin_class == "business" else "AJet Seferi"
        # AJet doğrudan oturum tokeni gerektirdiği için ana sayfaya düşüşü önleyen parametreli resmi uçuş köprüsü
        if is_round and ret_date:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+through+{ret_date}+AJet&hl=tr&gl=tr&curr=TRY"
        else:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+one+way+AJet&hl=tr&gl=tr&curr=TRY"

    # Türk Hava Yolları (TK)
    elif "turkish" in c_lower or "thy" in c_lower or "türk hava" in c_lower or c_code == "TK":
        display_name = "Türk Hava Yolları"
        official_name = "THY Resmi"
        prefix_tr = "THY'den"
        prefix_en = "THY"
        provider_id = "official_thy"
        badge = "Business Class ⭐" if cabin_class == "business" else "⭐ THY Konforu"
        if is_round and ret_date:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+through+{ret_date}+Turkish+Airlines&hl=tr&gl=tr&curr=TRY"
        else:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+one+way+Turkish+Airlines&hl=tr&gl=tr&curr=TRY"

    # SunExpress (XQ)
    elif "sunexpress" in c_lower or c_code == "XQ":
        display_name = "SunExpress"
        official_name = "SunExpress Resmi"
        prefix_tr = "SunExpress'ten"
        prefix_en = "SunExpress"
        provider_id = "official_sunexpress"
        badge = "SunClassic" if cabin_class == "business" else "SunExpress Seferi"
        if is_round and ret_date:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+through+{ret_date}+SunExpress&hl=tr&gl=tr&curr=TRY"
        else:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+one+way+SunExpress&hl=tr&gl=tr&curr=TRY"

    # Diğer / Uluslararası Havayolları (Lufthansa, Emirates, Qatar, Corendon vb.)
    else:
        display_name = carrier_name or "Tarifeli Havayolu"
        official_name = f"{display_name} Resmi"
        prefix_tr = f"{display_name}'den"
        prefix_en = display_name
        provider_id = "official_generic"
        badge = "Standart Sefer"
        # Havayolu özel sayfası için Google Flights parametreli sefer köprüsü
        bridge_code = c_code if c_code else "flights"
        if is_round and ret_date:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+through+{ret_date}+{bridge_code}&hl=tr&gl=tr&curr=TRY"
        else:
            official_link = f"https://www.google.com/travel/flights?q=flights+from+{from_code}+to+{to_code}+on+{dep_date}+one+way+{bridge_code}&hl=tr&gl=tr&curr=TRY"

    return {
        "provider_id": provider_id,
        "display_name": display_name,
        "official_name": official_name,
        "official_link": official_link,
        "prefix_tr": prefix_tr,
        "prefix_en": prefix_en,
        "badge": badge,
        "channel": "official",
        "carrier_code": c_code,
    }


# ==============================================================================
# 3. KAZANAN SAĞLAYICI SEÇİMİ VE BUTON KİLİTLEME MOTORU (SINGLE SOURCE OF TRUTH)
# ==============================================================================

def format_price_tr(price_val: float) -> str:
    """Türk Lirası formatında tam sayı string üretir (Ör: 2.477 ₺)."""
    rounded = int(round(price_val))
    formatted = f"{rounded:,}".replace(",", ".")
    return f"{formatted} ₺"


def format_button_label(prefix_tr: str, prefix_en: str, price_val: float) -> Tuple[str, str]:
    """Kusursuz Türkçe ve İngilizce satın alma butonu metni üretir."""
    price_tr = format_price_tr(price_val)
    rounded_num = int(round(price_val))
    price_en = f"{rounded_num:,} ₺"

    btn_tr = f"{prefix_tr} Al ({price_tr})"
    btn_en = f"Book on {prefix_en} ({price_en})"
    return btn_tr, btn_en


def decide_winning_flight_offer(
    raw_providers: List[Dict[str, Any]],
    carrier_meta: Dict[str, Any],
    is_international: bool = False
) -> Dict[str, Any]:
    """
    Bütün sağlayıcıları (Trip.com, Booking/Kayak, Skyscanner, Kiwi, Resmi Havayolu vb.)
    yarışmaya dahil ederek TEK VE KESİN KAZANANI belirler.
    
    Kurallar:
    1. Yalnızca canlı fiyatı olan (price > 0) sağlayıcılar yarışır.
    2. En ucuz fiyatı (price ASC) veren kesinlikle kazanır.
    3. Eşitlik durumunda (Tie-Breaker):
       - Aktif gelir ortaklığı (active_affiliate=True) resmi havayolunun önüne geçer.
       - Beklenen komisyon tutarı (expected_commission_try) yüksek olan kazanır.
       - Skyscanner gibi meta ortaklar da eşitlikte resmi havayoluna karşı gelir kazandırır.
    4. Buton metni ile gidilecek URL ASLA AYRIŞAMAZ.
    """
    from app.services.commission_service import calculate_expected_commission

    priced_candidates: List[Dict[str, Any]] = []
    unpriced_candidates: List[Dict[str, Any]] = []

    for item in raw_providers:
        p = dict(item)
        raw_price = p.get("price")
        has_valid_price = raw_price is not None and float(raw_price) > 0

        channel = p.get("channel", "official")
        reg_info = PROVIDERS_REGISTRY.get(channel, {})

        # Komisyon ve tie-breaker metriklerini hesapla
        comm_meta = calculate_expected_commission(
            channel=channel,
            ticket_price=float(raw_price) if has_valid_price else None,
            category="flight",
            is_international=is_international,
        )

        p["active_affiliate"] = comm_meta["active_affiliate"]
        p["expected_commission_try"] = comm_meta["expected_commission_try"]
        p["tie_breaker_rank"] = comm_meta["tie_breaker_rank"] or reg_info.get("default_rank", 10)
        p["prefix_tr"] = reg_info.get("prefix_tr", carrier_meta.get("prefix_tr", "Havayolundan"))
        p["prefix_en"] = reg_info.get("prefix_en", carrier_meta.get("prefix_en", "Official"))

        if has_valid_price:
            # Tam sayıya yuvarlanmış temiz fiyat
            clean_price = float(round(float(raw_price)))
            p["price"] = clean_price
            p["verified_live"] = True
            priced_candidates.append(p)
        else:
            p["price"] = None
            p["verified_live"] = False
            unpriced_candidates.append(p)

    if priced_candidates:
        # Fiyatı olan adayları sırala:
        # 1. En düşük fiyat (price ASC)
        # 2. Eşitlikte aktif affiliate (0: True, 1: False)
        # 3. Eşitlikte en yüksek komisyon (-expected_commission_try)
        # 4. Eşitlikte tie-breaker rank (-tie_breaker_rank)
        priced_candidates.sort(
            key=lambda x: (
                x["price"],
                0 if x.get("active_affiliate") else 1,
                -float(x.get("expected_commission_try", 0.0)),
                -int(x.get("tie_breaker_rank", 0)),
            )
        )
        winner = priced_candidates[0]
    else:
        # Hiç canlı fiyat çekilemediyse resmi havayolunu varsayılan yap
        winner = {
            "name": carrier_meta["official_name"],
            "url": carrier_meta["official_link"],
            "price": None,
            "channel": "official",
            "prefix_tr": carrier_meta["prefix_tr"],
            "prefix_en": carrier_meta["prefix_en"],
            "active_affiliate": False,
        }

    # Bütün sağlayıcı listesinde yalnızca doğrulanmış canlı fiyatı olanları listele (KURAL 4: Asla fiyatsız hap olmama yasası)
    for it in priced_candidates:
        it["is_best"] = (it.get("url") == winner.get("url") and it.get("channel") == winner.get("channel"))

    # Buton metinlerini üret
    w_price = winner.get("price")
    if w_price and float(w_price) > 0:
        btn_tr, btn_en = format_button_label(winner["prefix_tr"], winner["prefix_en"], float(w_price))
    else:
        btn_tr = f"{winner['prefix_tr']} Seferleri Gör →"
        btn_en = f"View on {winner['prefix_en']} →"

    return {
        "winner_id": winner.get("channel", "official"),
        "winner_name": winner.get("name", carrier_meta["official_name"]),
        "winner_channel": winner.get("channel", "official"),
        "winner_price": w_price,
        "winner_url": winner.get("url", carrier_meta["official_link"]),
        "winner_button_tr": btn_tr,
        "winner_button_en": btn_en,
        "providers": priced_candidates,
    }
