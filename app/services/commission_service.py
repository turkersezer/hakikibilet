"""
Merkezi Gelir Modeli ve Dinamik Komisyon Karar Motoru (Dynamic Commission & Tie-Breaker Engine)

Bu servis, Hakiki Bilet'in gelir ortaklığı (affiliate) kurallarını tek bir merkezden yönetir:
1. Her zaman EN UCUZ doğrulanmış canlı fiyatı veren firma 1. sıraya ve ana 'Bileti Al' butonuna yerleşir.
2. İki veya daha fazla firma KURUŞU KURUŞUNA AYNI FİYATI verdiğinde (Tie-Breaker):
   - Aktif ortaklığımız (active_affiliate=True) olan ve o bilet/kategori/hat (Yurt İçi / Yurt Dışı) için
     bize EN YÜKSEK NET TL KOMİSYON (expected_commission_try) kazandıran firma otomatik olarak kazanır.
3. İleride yeni ortaklıklar eklendiğinde veya komisyon oranları değiştiğinde (ör. Enuygun, Obilet, Bubilet
   aktif olduğunda veya oran artırdığında), hiçbir uçuş/otel/etkinlik koduna dokunmadan yalnızca
   `app/config.py` (veya Render ortam değişkenleri) güncellenerek tüm sitede yeni kazanan otomatik seçilir.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.config import settings


def get_partner_rule(channel: str) -> Dict[str, Any]:
    """
    Kanal koduna göre (trip, kiwi, agency, obilet, booking, bubilet, official, meta)
    güncel komisyon kurallarını döndürür.
    """
    rules = getattr(settings, "PARTNER_COMMISSION_RULES", {}) or {}
    default_rule = {
        "name": channel.capitalize(),
        "active_affiliate": False,
        "model": "percentage",
        "domestic_rate": 0.0,
        "international_rate": 0.0,
        "hotel_rate": 0.0,
        "fixed_try": 0.0,
        "tie_breaker_rank": 0,
    }
    return rules.get(channel, default_rule)


def calculate_expected_commission(
    channel: str,
    ticket_price: Optional[float],
    category: str = "flight",
    is_international: bool = False,
) -> Dict[str, Any]:
    """
    Belirli bir bilet fiyatı, kategori (flight, hotel, bus, event vb.) ve hat türü (yurt içi / yurt dışı)
    için ilgili ortağın bize kazandıracağı net TL komisyonu ve öncelik puanını dinamik hesaplar.
    """
    rule = get_partner_rule(channel)
    active_affiliate = bool(rule.get("active_affiliate", False))
    model = str(rule.get("model", "percentage")).lower()
    fixed_try = float(rule.get("fixed_try", 0.0) or 0.0)
    tie_breaker_rank = int(rule.get("tie_breaker_rank", 0) or 0)

    if category == "hotel" and "hotel_rate" in rule:
        rate = float(rule.get("hotel_rate", 0.0) or 0.0)
    elif is_international:
        rate = float(rule.get("international_rate", rule.get("domestic_rate", 0.0)) or 0.0)
    else:
        rate = float(rule.get("domestic_rate", 0.0) or 0.0)

    expected_commission_try = 0.0
    if active_affiliate and ticket_price is not None and float(ticket_price) > 0:
        price_val = float(ticket_price)
        if model == "fixed_try":
            expected_commission_try = round(fixed_try, 2)
        else:
            expected_commission_try = round((price_val * rate / 100.0) + fixed_try, 2)

    # Aktif ortaklar her zaman pasif kanalların önünde yer alır; eşitlikte oran ve rank belirleyicidir
    effective_priority = (1000 if active_affiliate else 0) + int(round(rate * 100)) + tie_breaker_rank

    return {
        "channel": channel,
        "partner_name": rule.get("name", channel),
        "active_affiliate": active_affiliate,
        "commission_model": model,
        "commission_rate": rate,
        "fixed_try": fixed_try,
        "expected_commission_try": expected_commission_try,
        "tie_breaker_rank": tie_breaker_rank,
        "commission_priority": effective_priority,
    }


def select_winning_offer(
    providers: List[Dict[str, Any]],
    category: str = "flight",
    is_international: bool = False,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Kazanan Teklif (Winner Offer) ve Eşit Fiyat (Tie-Breaker) Karar Motoru:
    1. Yalnızca gerçek, doğrulanmış canlı fiyatı olan (price > 0) sağlayıcıları fiyat yarışmasına sokar.
    2. En ucuz fiyatı veren sağlayıcı kazanır (price ASC).
    3. Fiyatlar kuruşu kuruşuna eşitse:
       - Önce aktif ortaklığımız olan (active_affiliate=True) tercih edilir,
       - Ardından bize EN YÜKSEK NET TL KOMİSYON (expected_commission_try) kazandıran firma seçilir,
       - Komisyon tutarı da eşitse tie_breaker_rank değeri yüksek olan kazanır.
    4. Henüz canlı fiyatı çekilmemiş alternatif kanallar (price=None) uydurma fiyat yazılmadan
       aktif ortaklık ve komisyon potansiyeli sırasıyla altta listelenir.
    """
    priced: List[Dict[str, Any]] = []
    unpriced: List[Dict[str, Any]] = []

    for p in providers:
        p_copy = dict(p)
        channel = p_copy.get("channel", "meta")
        raw_p = p_copy.get("price")
        has_valid_price = raw_p is not None and float(raw_p) > 0
        clean_price = round(float(raw_p), 2) if has_valid_price else None

        comm_meta = calculate_expected_commission(
            channel=channel,
            ticket_price=clean_price,
            category=category,
            is_international=is_international,
        )

        p_copy["active_affiliate"] = comm_meta["active_affiliate"]
        p_copy["commission_rate"] = comm_meta["commission_rate"]
        p_copy["expected_commission_try"] = comm_meta["expected_commission_try"]
        p_copy["tie_breaker_rank"] = comm_meta["tie_breaker_rank"]
        p_copy["commission_priority"] = comm_meta["commission_priority"]

        if has_valid_price:
            p_copy["price"] = clean_price
            p_copy["verified_live"] = True
            priced.append(p_copy)
        else:
            p_copy["price"] = None
            p_copy["verified_live"] = False
            unpriced.append(p_copy)

    # Fiyatı olanları:
    # 1) EN DÜŞÜK FİYAT
    # 2) Eşit fiyatta AKTİF ORTAKLIK (True önce gelir)
    # 3) Eşit fiyatta EN YÜKSEK BEKLENEN TL KOMİSYON (expected_commission_try DESC)
    # 4) Eşit komisyonda EN YÜKSEK TIE-BREAKER RANK
    priced.sort(
        key=lambda x: (
            x["price"],
            0 if x.get("active_affiliate") else 1,
            -float(x.get("expected_commission_try", 0.0)),
            -int(x.get("tie_breaker_rank", 0)),
        )
    )

    # Fiyatı henüz olmayan alternatif kanalları gelir potansiyeline göre sırala
    unpriced.sort(
        key=lambda x: (
            0 if x.get("active_affiliate") else 1,
            -float(x.get("commission_rate", 0.0)),
            -int(x.get("tie_breaker_rank", 0)),
        )
    )

    ordered = priced + unpriced
    winner = None
    for idx, item in enumerate(ordered):
        item["is_best"] = (idx == 0)
        if item["is_best"]:
            winner = item

    return ordered, winner
