"""
Hakiki Bilet — Merkezi 360° Gelir Ortaklığı (Affiliate) & Partner Yönlendirme Motoru (RevenueService)
====================================================================================================
1. SEVİYE 2 DERİN LİNK KORUMASI (Ana Ekrana Düşmeme Garantisi):
   - Hiçbir sağlayıcının URL path (yol) veya arama/rota/tarih parametrelerine dokunulmaz.
   - Feribotlines (/search?from=...&to=...) ve resmi kamu/operatör portalları (TCDD, GESTAŞ, İDO, BUDO,
     HAVAİST, HAVABUS, HAVAŞ, MUTTAŞ) gibi fazladan sorgu parametresine hassas siteler
     STRICT_PASSTHROUGH_DOMAINS listesinde korunur ve olduğu gibi geçirilir.
2. ÇAPRAZ KART GELİR PRİZİ (Uçak • Otobüs • Tren • Feribot • Araç • Transfer • Otel • Etkinlik):
   - Trip.com (AllianceID + SID), Booking.com (aid), Travelpayouts (marker), Awin (publisher),
     Obilet, Enuygun, Yolcu360, Bilet.com, Welcome Pickups, Rentalcars, Ferryhopper, Garenta ve Avis
     linklerine tek merkezden affiliate ve UTM takip parametrelerini ekler.
3. ÇİFT KADEMELİ (DUAL-MODE) ŞEMSİYE AĞ DESTEĞİ:
   - Ortam değişkenlerinde (AFFILIATE_WRAPPER_*) bir şemsiye ağ sarmalayıcısı tanımlandığında
     hiçbir kod değişikliği gerektirmeden derin linki sarmalayıcı üzerinden geçirir.
"""
import urllib.parse
from typing import Any, Dict, List, Optional

from app.config import settings


class RevenueService:
    # Fazladan bilinmeyen query parametresi eklendiğinde 302 redirect / hata verebilen hassas domainler
    STRICT_PASSTHROUGH_DOMAINS = (
        "feribotlines.com",
        "ebilet.tcddtasimacilik.gov.tr",
        "gdu.com.tr",
        "budo.burulas.com.tr",
        "ido.com.tr",
        "hava.ist",
        "havabus.com",
        "havas.net",
        "ulasim.muttas.com.tr",
        "erturk.com.tr",
        "turyol.com",
        "meisferrylines.com",
    )

    @classmethod
    def _append_safe_params(cls, raw_url: str, extra_params: Dict[str, str]) -> str:
        """
        Mevcut URL'nin path ve mevcut query parametrelerinin sırasını hiç bozmadan,
        yalnızca eksik olan affiliate/takip parametrelerini sona ekler.
        """
        if not raw_url or not extra_params:
            return raw_url
        try:
            parts = urllib.parse.urlsplit(raw_url)
            existing_pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            existing_keys = {k.lower() for k, _ in existing_pairs}

            for k, v in extra_params.items():
                if v and k.lower() not in existing_keys:
                    existing_pairs.append((k, str(v)))
                    existing_keys.add(k.lower())

            new_query = urllib.parse.urlencode(existing_pairs, doseq=True)
            return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
        except Exception:
            return raw_url

    @classmethod
    def enrich_deep_link(
        cls,
        provider_key: str,
        raw_url: str,
        vertical: str = "travel",
    ) -> str:
        """
        Doğrulanmış Seviye 2 derin linki alır ve ilgili sağlayıcının gelir ortaklığı (affiliate)
        parametrelerini güvenli biçimde ekler.
        """
        if not raw_url or not raw_url.startswith("http"):
            return raw_url

        low_url = raw_url.lower()
        for strict_dom in cls.STRICT_PASSTHROUGH_DOMAINS:
            if strict_dom in low_url:
                return raw_url

        pkey = (provider_key or "").lower().strip()

        # 1. Trip.com (Uçak, Otel, Tren, Akıllı Rota)
        if pkey == "trip" or "trip.com" in low_url:
            return cls._append_safe_params(
                raw_url,
                {
                    "Allianceid": getattr(settings, "AFFILIATE_TRIP_ALLIANCE_ID", "11051531"),
                    "SID": getattr(settings, "AFFILIATE_TRIP_SID", "333747492"),
                },
            )

        # 2. Booking.com (Otel, Uçak Çapraz Satış)
        if pkey == "booking" or "booking.com" in low_url:
            return cls._append_safe_params(
                raw_url,
                {
                    "aid": getattr(settings, "AFFILIATE_BOOKING_AID", "585474"),
                    "label": f"hakikibilet-{vertical}",
                },
            )

        # 3. Rentalcars / Booking Car Rental
        if pkey == "rentalcars" or "rentalcars.com" in low_url:
            return cls._append_safe_params(
                raw_url,
                {
                    "affiliateCode": "booking-com",
                    "adplat": f"hakikibilet_{vertical}",
                    "utm_source": "hakikibilet",
                },
            )

        # 4. Yolcu360 (Kiralık Araç & Uçuş Altı Çapraz Satış)
        if pkey == "yolcu360" or "yolcu360.com" in low_url:
            subid = getattr(settings, "AFFILIATE_YOLCU360_SUBID", "hakikibilet")
            enriched = cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "utm_campaign": vertical,
                    "subid": subid,
                },
            )
            wrapper = getattr(settings, "AFFILIATE_WRAPPER_YOLCU360", "")
            if wrapper:
                return f"{wrapper}{urllib.parse.quote(enriched, safe='')}"
            return enriched

        # 5. Enuygun (Uçak, Otobüs, Kiralık Araç, Otel)
        if pkey in ("enuygun", "agency") or "enuygun.com" in low_url:
            subid = getattr(settings, "AFFILIATE_ENUYGUN_SUBID", "hakikibilet")
            enriched = cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "utm_campaign": vertical,
                    "subid": subid,
                },
            )
            wrapper = getattr(settings, "AFFILIATE_WRAPPER_ENUYGUN", "")
            if wrapper:
                return f"{wrapper}{urllib.parse.quote(enriched, safe='')}"
            return enriched

        # 6. Obilet (Otobüs, Uçak, Feribot, Kiralık Araç)
        if pkey == "obilet" or "obilet.com" in low_url:
            subid = getattr(settings, "AFFILIATE_OBILET_SUBID", "hakikibilet")
            enriched = cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "utm_campaign": vertical,
                    "subid": subid,
                },
            )
            wrapper = getattr(settings, "AFFILIATE_WRAPPER_OBILET", "")
            if wrapper:
                return f"{wrapper}{urllib.parse.quote(enriched, safe='')}"
            return enriched

        # 7. Bilet.com (VIP Transfer, Feribot, Otobüs, Etkinlik)
        if pkey == "biletcom" or "bilet.com" in low_url:
            subid = getattr(settings, "AFFILIATE_BILETCOM_SUBID", "hakikibilet")
            enriched = cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "utm_campaign": vertical,
                    "ref": subid,
                },
            )
            wrapper = getattr(settings, "AFFILIATE_WRAPPER_BILETCOM", "")
            if wrapper:
                return f"{wrapper}{urllib.parse.quote(enriched, safe='')}"
            return enriched

        # 8. Welcome Pickups (Global Havalimanı Karşılama & Transfer)
        if pkey == "welcomepickups" or "welcomepickups.com" in low_url:
            marker = getattr(settings, "AFFILIATE_TRAVELPAYOUTS_MARKER", "585474")
            return cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "tap_s": marker,
                },
            )

        # 9. Ferryhopper (Yunan Adaları & Akdeniz Feribot)
        if pkey == "ferryhopper" or "ferryhopper.com" in low_url:
            subid = getattr(settings, "AFFILIATE_FERRY_SUBID", "hakikibilet")
            return cls._append_safe_params(
                raw_url,
                {
                    "aff": subid,
                    "utm_source": "hakikibilet",
                },
            )

        # 10. Garenta & Avis Türkiye (Kurumsal Araç Filosu)
        if pkey == "garenta" or "garenta.com" in low_url:
            subid = getattr(settings, "AFFILIATE_GARENTA_SUBID", "hakikibilet")
            return cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "ref": subid,
                },
            )

        if pkey == "avis" or "avis.com.tr" in low_url:
            subid = getattr(settings, "AFFILIATE_AVIS_SUBID", "hakikibilet")
            return cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "ref": subid,
                },
            )

        # 11. Setur, Jolly Tur, CruiseDirect & Bubilet
        if any(d in low_url for d in ("setur.com.tr", "jollytur.com", "cruisedirect.com", "bubilet.com.tr")):
            return cls._append_safe_params(
                raw_url,
                {
                    "utm_source": "hakikibilet",
                    "utm_medium": "affiliate",
                    "utm_campaign": vertical,
                },
            )

        return raw_url

    @classmethod
    def get_partner_priority(cls, provider_key: str) -> int:
        """
        Fiyat eşitliği durumunda (tie-breaker) hangi sağlayıcının öne çıkacağını belirleyen
        merkezi komisyon öncelik puanını döndürür.
        """
        rules = getattr(settings, "PARTNER_COMMISSION_RULES", {})
        rule = rules.get((provider_key or "").lower(), {})
        if not rule.get("active_affiliate", False):
            return int(rule.get("tie_breaker_rank", 10))
        return int(rule.get("tie_breaker_rank", 50))
