"""
Hakiki Bilet — Yönetici Analitik, Tıklama Sayacı, E-Posta Dönüş ve Kalıcı Yedekleme Servisi
(/yonetim Paneli için gerçek zamanlı ziyaretçi, arama, acente tıklaması, talep ölçer ve e-posta dönüş metrikleri)
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import aiosqlite
from app.config import settings

logger = logging.getLogger(__name__)

ANALYTICS_BACKUP_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "analytics_backup_snapshot.json",
)
BACKUP_SNAPSHOT_PATH = ANALYTICS_BACKUP_FILE
os.makedirs(os.path.dirname(ANALYTICS_BACKUP_FILE), exist_ok=True)


def _hash_visitor(ip: str, user_agent: str) -> str:
    raw = f"{ip or 'unknown'}|{(user_agent or '')[:120]}"
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _detect_device(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if any(k in ua for k in ("iphone", "ipad", "android", "mobile", "iemobile", "opera mini")):
        return "mobile"
    return "desktop"


def _classify_referrer(referrer: str, utm_source: str = "", utm_campaign: str = "") -> str:
    u_src = (utm_source or "").lower().strip()
    ref = (referrer or "").lower().strip()
    if u_src in ("email", "mail", "newsletter", "bulten") or "utm_source=email" in ref:
        return "email"
    if any(k in ref for k in ("google.", "bing.", "yandex.", "duckduckgo.", "yahoo.")):
        return "search_engine"
    if any(k in ref for k in ("instagram.", "facebook.", "t.co", "twitter.", "x.com", "linkedin.", "tiktok.", "youtube.")):
        return "social"
    if any(k in ref for k in ("whatsapp.", "wa.me", "telegram.", "t.me")):
        return "messaging"
    if not ref or "hakikibilet.com" in ref or "localhost" in ref or "127.0.0.1" in ref:
        return "direct"
    return "referral"


class AnalyticsService:
    @staticmethod
    async def ensure_tables(conn: aiosqlite.Connection):
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,          -- 'page_view', 'search', 'affiliate_click', 'feature_interest', 'email_sent', 'email_return', 'geo_resolve'
            visitor_hash TEXT,
            device_type TEXT,                  -- 'mobile', 'desktop'
            lang TEXT DEFAULT 'tr',            -- 'tr', 'en'
            traffic_source TEXT DEFAULT 'direct', -- 'direct', 'search_engine', 'social', 'messaging', 'email', 'referral'
            utm_campaign TEXT,
            transport_type TEXT,               -- 'flight', 'bus', 'train', 'ferry', 'car', 'stay', 'events', 'smartroute'
            origin TEXT,
            destination TEXT,
            provider_name TEXT,                -- 'Trip.com', 'Skyscanner', 'Obilet', 'Enuygun', 'Kiwi.com', 'Booking / Kayak', etc.
            carrier_name TEXT,
            ticket_price REAL DEFAULT 0,
            results_count INTEGER DEFAULT -1,
            meta_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at);")
        await conn.commit()

    @classmethod
    async def log_event(
        cls,
        event_type: str,
        ip: str = "",
        user_agent: str = "",
        lang: str = "tr",
        referrer: str = "",
        utm_source: str = "",
        utm_campaign: str = "",
        transport_type: str = "",
        origin: str = "",
        destination: str = "",
        provider_name: str = "",
        carrier_name: str = "",
        ticket_price: float = 0.0,
        currency: str = "TRY",
        feature_name: str = "",
        warning_text: str = "",
        results_count: int = -1,
        meta: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Arka planda sıfır gecikmeyle analitik olayını SQLite'a kaydeder."""
        try:
            visitor_hash = _hash_visitor(ip, user_agent)
            device_type = _detect_device(user_agent)
            traffic_source = _classify_referrer(referrer, utm_source, utm_campaign)
            meta_obj = dict(meta or {})
            if warning_text:
                meta_obj["warning_text"] = warning_text
            if feature_name:
                meta_obj["feature_name"] = feature_name
                if not transport_type:
                    transport_type = feature_name
            meta_str = json.dumps(meta_obj, ensure_ascii=False)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            async with aiosqlite.connect(settings.DB_PATH, timeout=10.0) as conn:
                await cls.ensure_tables(conn)
                await conn.execute(
                    """
                    INSERT INTO analytics_events (
                        event_type, visitor_hash, device_type, lang, traffic_source,
                        utm_campaign, transport_type, origin, destination,
                        provider_name, carrier_name, ticket_price, results_count, meta_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        visitor_hash,
                        device_type,
                        (lang or "tr")[:5],
                        traffic_source,
                        (utm_campaign or "")[:64],
                        (transport_type or "")[:32],
                        (origin or "")[:80],
                        (destination or "")[:80],
                        (provider_name or "")[:64],
                        (carrier_name or "")[:64],
                        float(ticket_price or 0.0),
                        int(results_count if results_count is not None else -1),
                        meta_str,
                        now_str,
                    ),
                )
                await conn.commit()
        except Exception as exc:
            logger.debug(f"Analytics log warning: {exc}")

    @classmethod
    async def get_dashboard_summary(cls) -> Dict[str, Any]:
        """Yönetici paneli (/yonetim) için tüm istatistikleri hesaplar ve döndürür."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")

        async with aiosqlite.connect(settings.DB_PATH, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            await cls.ensure_tables(conn)

            # 1. Ziyaretçi ve Sayfa Görüntüleme (Page Views & Unique Visitors)
            cur = await conn.execute("""
                SELECT
                    COUNT(*) AS total_views,
                    COUNT(DISTINCT visitor_hash) AS total_unique,
                    SUM(CASE WHEN substr(created_at, 1, 10) = ? THEN 1 ELSE 0 END) AS today_views,
                    COUNT(DISTINCT CASE WHEN substr(created_at, 1, 10) = ? THEN visitor_hash END) AS today_unique,
                    SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS week_views,
                    COUNT(DISTINCT CASE WHEN created_at >= ? THEN visitor_hash END) AS week_unique,
                    SUM(CASE WHEN device_type = 'mobile' THEN 1 ELSE 0 END) AS mobile_views,
                    SUM(CASE WHEN device_type = 'desktop' THEN 1 ELSE 0 END) AS desktop_views,
                    SUM(CASE WHEN lang = 'en' THEN 1 ELSE 0 END) AS en_views,
                    SUM(CASE WHEN lang != 'en' THEN 1 ELSE 0 END) AS tr_views
                FROM analytics_events
                WHERE event_type = 'page_view'
            """, (today_str, today_str, seven_days_ago, seven_days_ago))
            pv_row = dict(await cur.fetchone() or {})

            # Trafik Kaynakları Dağılımı
            cur = await conn.execute("""
                SELECT traffic_source, COUNT(*) AS cnt
                FROM analytics_events
                WHERE event_type IN ('page_view', 'email_return')
                GROUP BY traffic_source
                ORDER BY cnt DESC
            """)
            traffic_sources = {r["traffic_source"] or "direct": r["cnt"] for r in await cur.fetchall()}

            # 2. Arama İstatistikleri & Ulaşım Modu Dağılımı
            cur = await conn.execute("""
                SELECT
                    COUNT(*) AS total_searches,
                    SUM(CASE WHEN substr(created_at, 1, 10) = ? THEN 1 ELSE 0 END) AS today_searches,
                    SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS week_searches
                FROM analytics_events
                WHERE event_type = 'search'
            """, (today_str, seven_days_ago))
            sr_row = dict(await cur.fetchone() or {})

            cur = await conn.execute("""
                SELECT transport_type, COUNT(*) AS cnt
                FROM analytics_events
                WHERE event_type = 'search' AND transport_type != ''
                GROUP BY transport_type
                ORDER BY cnt DESC
            """)
            search_by_mode = {r["transport_type"]: r["cnt"] for r in await cur.fetchall()}

            # En Çok Aranan 10 Rota
            cur = await conn.execute("""
                SELECT origin, destination, transport_type, COUNT(*) AS cnt
                FROM analytics_events
                WHERE event_type = 'search' AND origin != '' AND destination != ''
                GROUP BY origin, destination, transport_type
                ORDER BY cnt DESC
                LIMIT 10
            """)
            top_routes = [dict(r) for r in await cur.fetchall()]

            # Sonuç Bulunamayan / Uyarı Verilen Aramalar & İlçe Çözümlemeleri
            cur = await conn.execute("""
                SELECT origin, destination, transport_type, event_type, meta_json, COUNT(*) AS cnt
                FROM analytics_events
                WHERE (event_type = 'search' AND results_count = 0)
                   OR event_type IN ('route_warning', 'geo_resolve')
                GROUP BY origin, destination, transport_type, event_type
                ORDER BY cnt DESC
                LIMIT 12
            """)
            zero_and_geo_rows = [dict(r) for r in await cur.fetchall()]

            # 3. Acente Satın Alma Tıklamaları (Affiliate Clicks)
            cur = await conn.execute("""
                SELECT
                    COUNT(*) AS total_clicks,
                    SUM(CASE WHEN substr(created_at, 1, 10) = ? THEN 1 ELSE 0 END) AS today_clicks,
                    SUM(CASE WHEN ticket_price > 0 THEN ticket_price ELSE 0 END) AS total_lead_volume_try,
                    AVG(CASE WHEN ticket_price > 0 THEN ticket_price END) AS avg_ticket_price_try
                FROM analytics_events
                WHERE event_type = 'affiliate_click'
            """, (today_str,))
            cl_row = dict(await cur.fetchone() or {})

            cur = await conn.execute("""
                SELECT
                    provider_name,
                    COUNT(*) AS clicks,
                    SUM(CASE WHEN ticket_price > 0 THEN ticket_price ELSE 0 END) AS volume_try,
                    AVG(CASE WHEN ticket_price > 0 THEN ticket_price END) AS avg_price
                FROM analytics_events
                WHERE event_type = 'affiliate_click' AND provider_name != ''
                GROUP BY provider_name
                ORDER BY clicks DESC
            """)
            clicks_by_provider = [dict(r) for r in await cur.fetchall()]

            cur = await conn.execute("""
                SELECT transport_type, COUNT(*) AS clicks
                FROM analytics_events
                WHERE event_type = 'affiliate_click' AND transport_type != ''
                GROUP BY transport_type
            """)
            clicks_by_mode = {r["transport_type"]: r["cnt"] if "cnt" in r.keys() else r["clicks"] for r in await cur.fetchall()}

            # 4. "Yakında / Entegrasyon Sürecinde" Kartlarına Tıklama Sayacı (Müşteri Talep Ölçer)
            cur = await conn.execute("""
                SELECT transport_type AS feature_name, provider_name AS sub_item, COUNT(*) AS clicks
                FROM analytics_events
                WHERE event_type = 'feature_interest'
                GROUP BY transport_type, provider_name
                ORDER BY clicks DESC
            """)
            feature_interest = [dict(r) for r in await cur.fetchall()]

            # 5. E-Posta & Bülten Dönüş İstatistikleri
            cur = await conn.execute("""
                SELECT
                    COUNT(*) AS total_subscribers,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_subscribers,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS unsubscribed_count,
                    SUM(CASE WHEN substr(created_at, 1, 10) = ? THEN 1 ELSE 0 END) AS today_subscribers
                FROM prelaunch_subscribers
            """, (today_str,))
            sub_row = dict(await cur.fetchone() or {})

            cur = await conn.execute("""
                SELECT id, email, is_active, created_at, unsubscribed_at, ip_address
                FROM prelaunch_subscribers
                ORDER BY created_at DESC
                LIMIT 50
            """)
            recent_subscribers = [dict(r) for r in await cur.fetchall()]

            cur = await conn.execute("""
                SELECT utm_campaign, COUNT(*) AS sent_count
                FROM analytics_events
                WHERE event_type = 'email_sent'
                GROUP BY utm_campaign
            """)
            emails_sent_by_campaign = {r["utm_campaign"] or "genel": r["sent_count"] for r in await cur.fetchall()}

            cur = await conn.execute("""
                SELECT
                    utm_campaign,
                    COUNT(*) AS return_visits,
                    COUNT(DISTINCT visitor_hash) AS unique_returners
                FROM analytics_events
                WHERE event_type = 'email_return' OR traffic_source = 'email'
                GROUP BY utm_campaign
            """)
            email_returns_by_campaign = [dict(r) for r in await cur.fetchall()]

            # Mailden dönen ziyaretçilerin yaptığı arama ve satın alma tıklaması sayısı
            cur = await conn.execute("""
                SELECT
                    SUM(CASE WHEN event_type = 'search' THEN 1 ELSE 0 END) AS email_user_searches,
                    SUM(CASE WHEN event_type = 'affiliate_click' THEN 1 ELSE 0 END) AS email_user_clicks
                FROM analytics_events
                WHERE visitor_hash IN (
                    SELECT DISTINCT visitor_hash FROM analytics_events
                    WHERE event_type = 'email_return' OR traffic_source = 'email'
                )
            """)
            email_conv_row = dict(await cur.fetchone() or {})

            # 6. Canlı Hareket Radarı (Son 30 İşlem)
            cur = await conn.execute("""
                SELECT
                    id, event_type, device_type, lang, traffic_source, utm_campaign,
                    transport_type, origin, destination, provider_name, carrier_name,
                    ticket_price, results_count, meta_json, created_at
                FROM analytics_events
                ORDER BY id DESC
                LIMIT 30
            """)
            recent_events_raw = [dict(r) for r in await cur.fetchall()]

            # Aktif fiyat alarmı sayısı
            try:
                cur_al = await conn.execute("SELECT COUNT(*) FROM tracked_routes WHERE is_active = 1")
                active_alarms = (await cur_al.fetchone())[0]
            except Exception:
                active_alarms = 0

        total_searches = int(sr_row.get("total_searches") or 0)
        total_clicks = int(cl_row.get("total_clicks") or 0)
        ctr_pct = round((total_clicks / total_searches) * 100, 1) if total_searches > 0 else 0.0

        total_emails_sent = sum(emails_sent_by_campaign.values())
        total_email_returns = sum(r.get("return_visits", 0) for r in email_returns_by_campaign)
        total_email_unique = sum(r.get("unique_returners", 0) for r in email_returns_by_campaign)

        total_subs = int(sub_row.get("total_subscribers") or 0)
        active_subs = int(sub_row.get("active_subscribers") or 0)
        unsub_subs = int(sub_row.get("unsubscribed_count") or 0)
        unsub_rate_pct = round((unsub_subs / total_subs) * 100, 1) if total_subs > 0 else 0.0

        # Feature demand dict
        feature_demand_map = {"stay": 0, "events": 0, "smartroute": 0}
        for fi in feature_interest:
            fn = (fi.get("feature_name") or "").lower()
            feature_demand_map[fn] = feature_demand_map.get(fn, 0) + int(fi.get("clicks") or 0)

        # Zero / Warning vs Geo resolutions
        zero_or_warning_routes = []
        geo_resolutions = []
        for zr in zero_and_geo_rows:
            try:
                m_obj = json.loads(zr.get("meta_json") or "{}")
            except Exception:
                m_obj = {}
            note_txt = m_obj.get("warning_text") or ""
            if zr.get("event_type") == "geo_resolve":
                geo_resolutions.append({
                    "origin": zr.get("origin") or "",
                    "destination": zr.get("destination") or "",
                    "note": note_txt or f"{zr.get('origin')} ➔ {zr.get('destination')}",
                    "count": int(zr.get("cnt") or 1),
                })
            else:
                zero_or_warning_routes.append({
                    "origin": zr.get("origin") or "",
                    "destination": zr.get("destination") or "",
                    "note": note_txt or "0 sonuç döndü",
                    "count": int(zr.get("cnt") or 1),
                })

        recent_feed = []
        for ev in recent_events_raw:
            try:
                m_obj = json.loads(ev.get("meta_json") or "{}")
            except Exception:
                m_obj = {}
            recent_feed.append({
                "id": ev.get("id"),
                "event_type": ev.get("event_type"),
                "device": ev.get("device_type") or "desktop",
                "lang": ev.get("lang") or "tr",
                "utm_source": ev.get("traffic_source") or "direct",
                "utm_campaign": ev.get("utm_campaign") or "",
                "transport_type": ev.get("transport_type") or "",
                "origin": ev.get("origin") or "",
                "destination": ev.get("destination") or "",
                "provider_name": ev.get("provider_name") or "",
                "ticket_price": float(ev.get("ticket_price") or 0.0),
                "feature_name": m_obj.get("feature_name") or ev.get("transport_type") or "",
                "warning_text": m_obj.get("warning_text") or "",
                "created_at": ev.get("created_at") or "",
            })

        return {
            "generated_at": now.strftime("%d.%m.%Y %H:%M:%S"),
            "active_price_alarms": active_alarms,
            "visitors": {
                "total_views": int(pv_row.get("total_views") or 0),
                "total_unique": int(pv_row.get("total_unique") or 0),
                "today_views": int(pv_row.get("today_views") or 0),
                "today_unique": int(pv_row.get("today_unique") or 0),
                "week_views": int(pv_row.get("week_views") or 0),
                "week_unique": int(pv_row.get("week_unique") or 0),
            },
            "audience": {
                "devices": {
                    "mobile": int(pv_row.get("mobile_views") or 0),
                    "desktop": int(pv_row.get("desktop_views") or 0),
                },
                "languages": {
                    "tr": int(pv_row.get("tr_views") or 0),
                    "en": int(pv_row.get("en_views") or 0),
                },
                "traffic_sources": traffic_sources,
            },
            "searches": {
                "total": total_searches,
                "today": int(sr_row.get("today_searches") or 0),
                "week": int(sr_row.get("week_searches") or 0),
                "by_mode": search_by_mode,
                "top_routes": [
                    {
                        "origin": r["origin"],
                        "destination": r["destination"],
                        "mode": r["transport_type"] or "flight",
                        "count": r["cnt"],
                    }
                    for r in top_routes
                ],
                "zero_or_warning_routes": zero_or_warning_routes,
                "geo_resolutions": geo_resolutions,
            },
            "affiliate": {
                "total_clicks": total_clicks,
                "today_clicks": int(cl_row.get("today_clicks") or 0),
                "search_to_click_ctr_pct": ctr_pct,
                "total_lead_volume_try": round(float(cl_row.get("total_lead_volume_try") or 0.0), 2),
                "avg_ticket_price_try": round(float(cl_row.get("avg_ticket_price_try") or 0.0), 2),
                "by_provider": [
                    {
                        "provider": p["provider_name"],
                        "clicks": p["clicks"],
                        "volume_try": round(float(p.get("volume_try") or 0.0), 2),
                    }
                    for p in clicks_by_provider
                ],
                "by_mode": clicks_by_mode,
            },
            "feature_demand": feature_demand_map,
            "email_stats": {
                "subscribers_total": total_subs,
                "subscribers_active": active_subs,
                "subscribers_unsubscribed": unsub_subs,
                "unsubscribe_rate_pct": unsub_rate_pct,
                "emails_sent_total": total_emails_sent,
                "emails_sent_by_campaign": emails_sent_by_campaign,
                "email_link_returns_total": total_email_returns,
                "email_link_returns_unique": total_email_unique,
                "email_returns_by_campaign": {
                    (r.get("utm_campaign") or "bulten_genel"): int(r.get("return_visits") or 0)
                    for r in email_returns_by_campaign
                },
                "email_visitor_searches": int(email_conv_row.get("email_user_searches") or 0),
                "email_visitor_affiliate_clicks": int(email_conv_row.get("email_user_clicks") or 0),
                "subscriber_list": [
                    {
                        "id": s["id"],
                        "email": s["email"],
                        "is_active": bool(s["is_active"]),
                        "created_at": s["created_at"],
                        "ip": s["ip_address"],
                    }
                    for s in recent_subscribers
                ],
            },
            "recent_feed": recent_feed,
        }

    @classmethod
    async def export_full_backup_json(cls) -> Dict[str, Any]:
        """Tüm analitik olaylarını ve abone listesini taşınabilir JSON paketi olarak dışa aktarır."""
        async with aiosqlite.connect(settings.DB_PATH, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            await cls.ensure_tables(conn)
            cur1 = await conn.execute("SELECT * FROM analytics_events ORDER BY id ASC")
            events = [dict(r) for r in await cur1.fetchall()]
            cur2 = await conn.execute("SELECT * FROM prelaunch_subscribers ORDER BY id ASC")
            subscribers = [dict(r) for r in await cur2.fetchall()]

        payload = {
            "exported_at": datetime.now().isoformat(),
            "app": settings.APP_DOMAIN,
            "events_count": len(events),
            "subscribers_count": len(subscribers),
            "analytics_events": events,
            "prelaunch_subscribers": subscribers,
        }
        try:
            with open(ANALYTICS_BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return payload

    @classmethod
    async def import_full_backup_json(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dışa aktarılmış JSON yedeğini veritabanına (mükerrer oluşturmadan) geri yükler."""
        events = payload.get("analytics_events") or []
        subscribers = payload.get("prelaunch_subscribers") or []
        inserted_events = 0
        inserted_subs = 0

        async with aiosqlite.connect(settings.DB_PATH, timeout=10.0) as conn:
            await cls.ensure_tables(conn)
            for s in subscribers:
                email = (s.get("email") or "").strip().lower()
                if not email:
                    continue
                cur = await conn.execute("SELECT id FROM prelaunch_subscribers WHERE email = ?", (email,))
                if not await cur.fetchone():
                    await conn.execute(
                        """
                        INSERT INTO prelaunch_subscribers (email, ip_address, user_agent, kvkk_consent, is_active, unsubscribed_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            email,
                            s.get("ip_address"),
                            s.get("user_agent"),
                            s.get("kvkk_consent", 1),
                            s.get("is_active", 1),
                            s.get("unsubscribed_at"),
                            s.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    inserted_subs += 1

            for ev in events:
                cur = await conn.execute(
                    "SELECT id FROM analytics_events WHERE event_type = ? AND visitor_hash = ? AND created_at = ? AND COALESCE(provider_name,'') = ? LIMIT 1",
                    (
                        ev.get("event_type", ""),
                        ev.get("visitor_hash", ""),
                        ev.get("created_at", ""),
                        ev.get("provider_name", "") or "",
                    ),
                )
                if not await cur.fetchone():
                    await conn.execute(
                        """
                        INSERT INTO analytics_events (
                            event_type, visitor_hash, device_type, lang, traffic_source,
                            utm_campaign, transport_type, origin, destination,
                            provider_name, carrier_name, ticket_price, results_count, meta_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ev.get("event_type", "page_view"),
                            ev.get("visitor_hash", ""),
                            ev.get("device_type", "desktop"),
                            ev.get("lang", "tr"),
                            ev.get("traffic_source", "direct"),
                            ev.get("utm_campaign", ""),
                            ev.get("transport_type", ""),
                            ev.get("origin", ""),
                            ev.get("destination", ""),
                            ev.get("provider_name", ""),
                            ev.get("carrier_name", ""),
                            float(ev.get("ticket_price") or 0.0),
                            int(ev.get("results_count") if ev.get("results_count") is not None else -1),
                            ev.get("meta_json") or "{}",
                            ev.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    inserted_events += 1
            await conn.commit()

        return {
            "success": True,
            "restored_events": inserted_events,
            "restored_subscribers": inserted_subs,
        }
