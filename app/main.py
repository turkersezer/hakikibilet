from fastapi import FastAPI, Request, Query, HTTPException, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse, Response
from contextlib import asynccontextmanager
import os
import json
import re
import asyncio
import csv
import io

from app.config import settings
from app.database import init_db, get_db, get_db_dep
import time
from collections import defaultdict

# Basit IP Bazlı Hız Sınırlayıcı (Rate Limiter - Bot ve Spam Koruması)
_RATE_LIMIT_BUCKETS = defaultdict(list)
_LAST_BUCKET_CLEANUP = 0.0

# Otomasyon / Kazıyıcı Bot İmza Listesi (Gerçek tarayıcıları asla etkilemez)
_SCRAPER_BOT_SIGNATURES = (
    "python-requests", "python-httpx", "aiohttp/", "scrapy", "urllib/", "pycurl",
    "go-http-client", "java/", "libwww-perl", "wget/", "masscan", "zgrab",
    "nikto", "sqlmap", "nmap", "headlesschrome", "phantomjs"
)


def _get_real_client_ip(request: Request) -> str:
    """Render, Cloudflare ve Nginx ters vekil (Reverse Proxy) arkasındaki gerçek kullanıcı IP'sini çözer."""
    if not request:
        return "unknown"
    for header_name in ("cf-connecting-ip", "true-client-ip", "x-real-ip"):
        val = (request.headers.get(header_name) or "").strip()
        if val:
            return val.split(",")[0].strip()[:64]
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        first_ip = xff.split(",")[0].strip()
        if first_ip:
            return first_ip[:64]
    return (request.client.host if request.client and request.client.host else "unknown")[:64]


def _cleanup_stale_rate_limit_buckets(now: float, max_idle_sec: int = 300) -> None:
    """Bellek şişmesini (Memory Leak) önlemek için süresi dolmuş IP kovalarını periyodik temizler."""
    global _LAST_BUCKET_CLEANUP
    if (now - _LAST_BUCKET_CLEANUP) < 180 and len(_RATE_LIMIT_BUCKETS) < 2000:
        return
    _LAST_BUCKET_CLEANUP = now
    stale_keys = []
    for k, ts_list in list(_RATE_LIMIT_BUCKETS.items()):
        fresh = [t for t in ts_list if (now - t) < max_idle_sec]
        if fresh:
            _RATE_LIMIT_BUCKETS[k] = fresh
        else:
            stale_keys.append(k)
    for k in stale_keys:
        _RATE_LIMIT_BUCKETS.pop(k, None)


def _check_rate_limit(ip: str, bucket: str, max_requests: int = 5, window_sec: int = 60) -> bool:
    now = time.time()
    _cleanup_stale_rate_limit_buckets(now, max_idle_sec=max(300, window_sec * 2))
    key = f"{bucket}:{ip or 'unknown'}"
    timestamps = [t for t in _RATE_LIMIT_BUCKETS[key] if now - t < window_sec]
    if len(timestamps) >= max_requests:
        _RATE_LIMIT_BUCKETS[key] = timestamps
        return False
    timestamps.append(now)
    _RATE_LIMIT_BUCKETS[key] = timestamps
    return True


def _is_automated_scraper_bot(request: Request, honeypot_val: str = "") -> bool:
    """
    Görünmez Bot & Kazıyıcı Tespiti:
    - Honeypot (bal küpü) alanı doldurulmuşsa anında bot olarak işaretler.
    - Bilinen agresif kazıyıcı kütüphaneleri (Scrapy, python-requests, sqlmap vb.) yakalar.
    - Gerçek kullanıcı tarayıcılarını (Chrome, Safari, Firefox, Edge, Mobil WebView) asla engellemez.
    """
    if honeypot_val and str(honeypot_val).strip():
        return True
    if not request:
        return False
    ua = (request.headers.get("user-agent") or "").strip().lower()
    if not ua or len(ua) < 4:
        return True
    if any(sig in ua for sig in _SCRAPER_BOT_SIGNATURES):
        return True
    return False

def _is_valid_admin_key(val: str) -> bool:
    if not val:
        return False
    clean = str(val).strip()
    env_key = str(getattr(settings, "MAINTENANCE_BYPASS_KEY", "") or "").strip()
    try:
        from app.services.analytics_service import AnalyticsService
        custom_key = AnalyticsService.get_custom_admin_password_sync()
    except Exception:
        custom_key = ""
    if custom_key and custom_key not in ("hakiki2026", "hakikibilet2026"):
        # Eğer yönetici panelinden özel bir şifre belirlendiyse onu (veya ortam değişkenini) kabul et
        valid_lower = {custom_key.lower()}
        if env_key:
            valid_lower.add(env_key.lower())
        return clean == custom_key or clean.lower() in valid_lower
    valid_lower = {"hakiki2026", "hakikibilet2026"}
    if env_key:
        valid_lower.add(env_key.lower())
    if custom_key:
        valid_lower.add(custom_key.lower())
    return clean == env_key or clean.lower() in valid_lower


def _require_admin_access(request: Request):
    cookie = request.cookies.get("hakiki_preview_access")
    param = request.query_params.get("onizleme") or request.query_params.get("preview")
    header_key = request.headers.get("X-Admin-Key")
    if not (_is_valid_admin_key(cookie) or _is_valid_admin_key(param) or _is_valid_admin_key(header_key)):
        raise HTTPException(status_code=403, detail="Bu işlemi gerçekleştirmek için yönetici yetkisi gereklidir.")
from app.cities import TURKEY_CITIES, ALL_LOCATIONS, find_city, get_cities_by_transport
from app.models import (
    SearchRequest, CarSearchRequest, TrackRouteRequest, UserSettingsUpdate, TestNotificationRequest,
    EarlyAccessRequest
)
from app.services.search_service import SearchService
from app.services.campaign_service import CampaignService
from app.services.tracker_service import TrackerService
from app.services.notification_service import NotificationService
from app.services.scheduler_service import start_scheduler, stop_scheduler, scheduled_price_and_campaign_check

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlangıçta veritabanını oluştur ve tohum verileri yükle
    await init_db()
    # Resend Bulut Rehberi ile yerel SQLite veritabanını iki yönlü eşitle (Sıfır veri kaybı güvencesi)
    try:
        await NotificationService.sync_resend_audience_with_db()
    except Exception as e:
        print(f"Resend audience senkronizasyon uyarısı: {e}")
    # Arka plan Cron zamanlayıcısını başlat
    start_scheduler()
    yield
    # Kapanırken zamanlayıcıyı durdur
    stop_scheduler()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Türkiye ve Dünya Uçak, Tren, Otobüs, Feribot Bileti Arama, Fiyat Takibi ve Çok Kanallı Bildirim Platformu",
    lifespan=lifespan
)

# Statik ve Şablon dizinleri
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# ==================== BAKIM / LANSMAN ÖNCESİ MODU MIDDLEWARE ====================

@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    path = request.url.path
    
    # Yasal uyum sayfaları, doğrudan lansman vitrini, erken kayıt API'si, bülten ayrılma, yönetici paneli, analitik ping, statik dosyalar, favicon ve robots her zaman herkese açık
    legal_paths = ("/lansman", "/yonetim", "/yonetici", "/yönetici", "/admin", "/api/erken-kayit", "/api/analytics/event", "/bulten/ayril", "/yasal-uyari", "/kullanim-kosullari", "/kvkk", "/cerez-politikasi", "/etkinlik-kurallari", "/iletisim", "/hukuk", "/legal")
    if path.startswith("/static") or path in ("/favicon.ico", "/robots.txt") or path in legal_paths:
        response = await call_next(request)
        if path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response
        
    # URL parametresiyle doğrudan yönetici girişi: ?onizleme=hakiki2026 veya ?preview=hakiki2026
    query_key = request.query_params.get("onizleme") or request.query_params.get("preview")
    if _is_valid_admin_key(query_key):
        if path.startswith("/api"):
            return await call_next(request)
        clean_url = str(request.url.remove_query_params(["onizleme", "preview"]))
        response = RedirectResponse(url=clean_url)
        response.set_cookie(
            key="hakiki_preview_access",
            value=str(query_key).strip(),
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return response

    # Admin kilit açma / kapama yolları serbest
    if path == "/admin/unlock" and request.method == "POST":
        return await call_next(request)
    if path == "/admin/lock":
        return await call_next(request)

    # Sağlık kontrolü (Render uykusunu önleyen UptimeRobot / Keep-alive ping'i için 200 döner)
    if path in ("/api/health", "/health"):
        return JSONResponse(content={"status": "ok", "service": "hakikibilet", "status_code": 200}, status_code=200)

    # Bakım modu devredeyse ve tarayıcıda yönetici çerezi yoksa vitrin sayfasını sun
    if settings.MAINTENANCE_MODE:
        preview_cookie = request.cookies.get("hakiki_preview_access")
        if not _is_valid_admin_key(preview_cookie):
            if not path.startswith("/api"):
                return templates.TemplateResponse(
                    request=request,
                    name="coming_soon.html",
                    context={
                        "app_name": settings.APP_NAME,
                        "app_slogan": settings.APP_SLOGAN,
                        "app_domain": settings.APP_DOMAIN,
                        "legal_disclaimer": settings.LEGAL_DISCLAIMER
                    }
                )
            else:
                return JSONResponse(
                    content={"detail": "Hakiki Bilet lansman hazırlığındadır.", "maintenance": True},
                    status_code=503
                )

    response = await call_next(request)
    if path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

@app.post("/admin/unlock")
async def admin_unlock(request: Request):
    client_ip = _get_real_client_ip(request)
    if not _check_rate_limit(client_ip, "admin_unlock", max_requests=15, window_sec=60):
        return JSONResponse(content={"success": False, "message": "Çok fazla deneme yapıldı. Lütfen 1 dakika bekleyiniz."}, status_code=429)
    try:
        data = await request.json()
        passcode = data.get("passcode", "")
    except Exception:
        passcode = ""
        
    if _is_valid_admin_key(passcode):
        try:
            from app.services.analytics_service import AnalyticsService
            active_token = AnalyticsService.get_admin_password_sync()
        except Exception:
            active_token = str(passcode).strip() or "hakiki2026"
        response = JSONResponse(content={"success": True, "message": "Giriş başarılı.", "token": active_token})
        response.set_cookie(
            key="hakiki_preview_access",
            value=active_token,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return response
    return JSONResponse(content={"success": False, "message": "Geçersiz yönetici şifresi."}, status_code=401)

@app.get("/admin/lock")
async def admin_lock():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="hakiki_preview_access")
    return response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(os.path.join(static_dir, "img", "favicon.png"))

@app.get("/lansman", response_class=HTMLResponse)
@app.get("/coming-soon", response_class=HTMLResponse)
async def view_coming_soon_page(request: Request):
    """Her zaman doğrudan lansman öncesi ekranını (coming_soon.html) sunar"""
    return templates.TemplateResponse(
        request=request,
        name="coming_soon.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "legal_disclaimer": settings.LEGAL_DISCLAIMER
        }
    )


# ==================== HUKUK & YASAL UYUM MERKEZİ ROTALARI ====================

@app.get("/yasal-uyari", response_class=HTMLResponse)
@app.get("/kullanim-kosullari", response_class=HTMLResponse)
@app.get("/kvkk", response_class=HTMLResponse)
@app.get("/cerez-politikasi", response_class=HTMLResponse)
@app.get("/etkinlik-kurallari", response_class=HTMLResponse)
@app.get("/iletisim", response_class=HTMLResponse)
@app.get("/hukuk", response_class=HTMLResponse)
@app.get("/legal", response_class=HTMLResponse)
async def legal_center_page(request: Request):
    """Hukuk, Mevzuat, TÜRSAB Metasearch, KVKK ve Şartlar Merkezi"""
    path = request.url.path
    tab_map = {
        "/yasal-uyari": "tursab",
        "/kullanim-kosullari": "kullanim",
        "/kvkk": "kvkk",
        "/cerez-politikasi": "cerez",
        "/etkinlik-kurallari": "etkinlik",
        "/iletisim": "kunye",
    }
    initial_tab = tab_map.get(path, "tursab")
    return templates.TemplateResponse(
        request=request,
        name="legal.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "legal_disclaimer": settings.LEGAL_DISCLAIMER,
            "initial_tab": initial_tab
        }
    )

# ==================== SAYFA ROTALARI (HTML) ====================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Ana Sayfa: Arama Motoru + Doğrulanmış Fırsat Radarı & Şirket Kampanyaları & Gezgin Keşif Rehberi"""
    radar_deals = await CampaignService.get_radar_deals()
    announcements = await CampaignService.get_official_announcements()
    curated_events = SearchService.get_curated_events()
    v_param = request.query_params.get("v")
    if v_param == "1":
        template_name = "index.html"
    elif v_param == "2":
        template_name = "index_v2.html"
    else:
        template_name = "index_v3.html"
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "cities": ALL_LOCATIONS,
            "radar_deals": radar_deals,
            "announcements": announcements,
            "deals": radar_deals,
            "curated_events": curated_events,
            "legal_disclaimer": settings.LEGAL_DISCLAIMER
        }
    )

@app.get("/v2", response_class=HTMLResponse)
async def home_page_v2(request: Request):
    """Yeni Nesil Sekmeli Portal (V2)"""
    radar_deals = await CampaignService.get_radar_deals()
    announcements = await CampaignService.get_official_announcements()
    curated_events = SearchService.get_curated_events()
    return templates.TemplateResponse(
        request=request,
        name="index_v2.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "cities": ALL_LOCATIONS,
            "radar_deals": radar_deals,
            "announcements": announcements,
            "deals": radar_deals,
            "curated_events": curated_events,
            "legal_disclaimer": settings.LEGAL_DISCLAIMER
        }
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Kullanıcı Paneli: Takip Listesi, Bildirim Geçmişi, Ayarlar"""
    # Demo kullanıcı ID'si üzerinden paneli yükle
    demo_user_id = "demo-user-1"
    tracked_routes = await TrackerService.get_user_tracked_routes(demo_user_id)
    logs = await TrackerService.get_notification_logs(demo_user_id)
    
    conn = await get_db()
    try:
        user_row = await conn.execute("SELECT * FROM users WHERE id = ?", (demo_user_id,))
        user = dict(await user_row.fetchone() or {})
        if user.get("notification_preferences"):
            try:
                user["notification_preferences"] = json.loads(user["notification_preferences"])
            except Exception:
                pass
    finally:
        await conn.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name": settings.APP_NAME,
            "cities": TURKEY_CITIES,
            "routes": tracked_routes,
            "logs": logs,
            "user": user
        }
    )

# ==================== API ENDPOINT'LERİ ====================

@app.get("/api/cities")
async def get_cities(request: Request, transport_type: str = Query("all"), scope: str = Query("all")):
    """Türkiye ve dünya şehirler listesi (seyahat moduna ve kapsama göre filtrelenebilir)"""
    client_ip = _get_real_client_ip(request)
    if not _check_rate_limit(client_ip, "public_cities", max_requests=120, window_sec=60):
        return JSONResponse(status_code=429, content={"cities": [], "mode": transport_type, "scope": scope, "count": 0, "rate_limited": True})
    from app.cities import get_cities_by_transport
    filtered = get_cities_by_transport(transport_type, scope=scope)
    return {"cities": filtered, "mode": transport_type, "scope": scope, "count": len(filtered)}

@app.get("/api/hotel-autocomplete")
async def hotel_autocomplete(request: Request, q: str = Query("", min_length=0)):
    """Canlı Otel Adı + Şehir/Bölge Hibrit Autocomplete (Enuygun & Etstur Canlı Öneri Motoru)"""
    from app.services.hotel_service import HotelService
    q_clean = (q or "").strip()[:80]
    if len(q_clean) < 2:
        return {"query": q_clean, "suggestions": [], "count": 0}
    client_ip = _get_real_client_ip(request)
    if _is_automated_scraper_bot(request) or not _check_rate_limit(client_ip, "hotel_autocomplete", max_requests=60, window_sec=60):
        return {"query": q_clean, "suggestions": [], "count": 0, "rate_limited": True}
    suggestions = await asyncio.to_thread(HotelService.autocomplete_hotels_and_regions, q_clean)
    return {"query": q_clean, "suggestions": suggestions, "count": len(suggestions)}

@app.get("/api/system/slots")
async def get_extension_slots():
    """Tek Beyin, Üç Ekran (Web, Mobil Uygulama, WhatsApp Botu) için aktif priz/modül şalter durumu"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "extension_slots": getattr(settings, "EXTENSION_SLOTS", {}),
    }


def _build_safe_fallback_search_payload(
    req: SearchRequest,
    adults: int,
    children: int,
    infants: int,
    total_pax: int,
    notice_message: str,
) -> dict:
    """Yoğunluk, hata veya hız sınırı anında dış kazıma yapmadan 0.01s içinde güvenli resmi derin linkleri üretir."""
    try:
        links = SearchService.generate_deep_links(
            req.origin, req.destination, req.departure_date, req.return_date,
            total_pax, req.trip_type, cabin_class=req.cabin_class,
            adults=adults, children=children, infants=infants
        )
    except Exception:
        links = {}
    fallback_hotel_info = None
    if getattr(req, "include_hotel", False):
        try:
            from app.services.hotel_service import HotelService
            fallback_hotel_info = HotelService.get_hotel_recommendation(
                dest_city=req.destination,
                checkin_date=req.departure_date,
                checkout_date=req.return_date,
                guests=total_pax,
                currency=getattr(req, "currency", "TRY") or "TRY",
            )
        except Exception:
            fallback_hotel_info = None
    return {
        "origin": req.origin,
        "destination": req.destination,
        "date": req.departure_date,
        "return_date": req.return_date,
        "trip_type": req.trip_type,
        "passengers": total_pax,
        "adults": adults,
        "children": children,
        "infants": infants,
        "cabin_class": req.cabin_class,
        "transport_type": req.transport_type,
        "currency": "₺",
        "currency_code": "TRY",
        "hotel_info": fallback_hotel_info,
        "deep_links": links,
        "extension_slots": getattr(settings, "EXTENSION_SLOTS", {}),
        "notices": [notice_message],
        "results_count": 0,
        "tickets": []
    }


# ==================== #18 VP ENGINEERING & #21 SRE: 5 DAKİKALIK SICAK ÖNBELLEK (WARM CACHE) ====================
_SEARCH_WARM_CACHE: dict[str, tuple[float, dict]] = {}
_SEARCH_WARM_CACHE_TTL_SEC = 300.0
_SEARCH_WARM_CACHE_MAX_SIZE = 256


def _build_search_warm_cache_key(req: SearchRequest, adults: int, children: int, infants: int, total_pax: int) -> str:
    parts = [
        str(req.transport_type or "flight").strip().lower(),
        str(req.origin or "").strip().lower(),
        str(req.destination or "").strip().lower(),
        str(getattr(req, "raw_origin", "") or "").strip().lower(),
        str(getattr(req, "raw_destination", "") or "").strip().lower(),
        str(req.departure_date or "").strip(),
        str(req.return_date or "").strip(),
        str(req.trip_type or "one_way").strip().lower(),
        str(req.cabin_class or "economy").strip().lower(),
        str(getattr(req, "ferry_vehicle_type", "passenger") or "passenger").strip().lower(),
        str(getattr(req, "currency", "TRY") or "TRY").strip().upper(),
        f"{adults}-{children}-{infants}-{total_pax}",
    ]
    return "|".join(parts)


def _get_search_warm_cache(key: str) -> dict | None:
    entry = _SEARCH_WARM_CACHE.get(key)
    if not entry:
        return None
    ts, payload = entry
    if time.time() - ts > _SEARCH_WARM_CACHE_TTL_SEC:
        _SEARCH_WARM_CACHE.pop(key, None)
        return None
    cached_copy = dict(payload)
    cached_copy["cache_hit"] = True
    return cached_copy


def _set_search_warm_cache(key: str, payload: dict) -> None:
    if not isinstance(payload, dict):
        return
    if len(_SEARCH_WARM_CACHE) >= _SEARCH_WARM_CACHE_MAX_SIZE:
        oldest_key = min(_SEARCH_WARM_CACHE.keys(), key=lambda k: _SEARCH_WARM_CACHE[k][0])
        _SEARCH_WARM_CACHE.pop(oldest_key, None)
    _SEARCH_WARM_CACHE[key] = (time.time(), dict(payload))


@app.post("/api/search")
async def search_tickets(req: SearchRequest, request: Request):
    """
    MODÜL 1: Bilet Arama ve Parametreli Deep Linkler (Tek Yön, Gidiş-Dönüş, Gezgin Modu)
    Skyscanner, Google Flights, Enuygun, TCDD, Obilet, Kamil Koç
    """
    adults = req.adults if req.adults is not None else req.passengers
    children = req.children if req.children is not None else 0
    infants = req.infants if req.infants is not None else 0
    total_pax = max(1, adults + children + infants)
    client_ip = _get_real_client_ip(request)
    ua = request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")

    # KATMAN 1: Görünmez Bot (Scraper / Honeypot) & Aşırı Saldırı (Flood > 80/dk) Kalkanı
    is_bot = _is_automated_scraper_bot(request, getattr(req, "website_url", "") or "")
    if is_bot or not _check_rate_limit(client_ip, "search_hard_flood", max_requests=80, window_sec=60):
        safe_payload = _build_safe_fallback_search_payload(
            req, adults, children, infants, total_pax,
            "🛡️ Güvenlik Kalkanı: Otomatik bot/kazıyıcı veya aşırı istek tespit edildi. Doğrudan resmi acente bağlantıları hazırlandı."
        )
        safe_payload["rate_limited"] = True
        safe_payload["blocked_bot"] = bool(is_bot)
        return JSONResponse(status_code=429, content=safe_payload)

    # KATMAN 1.5: 5 Dakikalık Sıcak Önbellek (Warm Cache) — Tekrarlanan Aramada 0.01s Anlık Yanıt
    cache_key = _build_search_warm_cache_key(req, adults, children, infants, total_pax)
    cached_result = _get_search_warm_cache(cache_key)
    if cached_result is not None:
        return JSONResponse(content=cached_result, headers={"X-Hakiki-Cache": "HIT"})

    # KATMAN 2: Kırılmaz "Yumuşak Hız Sınırı" (Dakikada 30 Canlı Arama Üzerinde 200 OK + Resmi Derin Linkler)
    if not _check_rate_limit(client_ip, "search_live_scrape", max_requests=30, window_sec=60):
        return _build_safe_fallback_search_payload(
            req, adults, children, infants, total_pax,
            "🛡️ Anlık yüksek sorgu yoğunluğu nedeniyle sunucu hızını korumak adına doğrudan resmi acente bağlantıları hazırlandı."
        )

    try:
        result = await asyncio.to_thread(
            SearchService.search_all_tickets,
            origin_city=req.origin,
            dest_city=req.destination,
            raw_origin=getattr(req, "raw_origin", None),
            raw_destination=getattr(req, "raw_destination", None),
            departure_date=req.departure_date,
            return_date=req.return_date,
            passengers=total_pax,
            adults=adults,
            children=children,
            infants=infants,
            transport_type=req.transport_type,
            trip_type=req.trip_type,
            night_only=req.night_only,
            cabin_class=req.cabin_class,
            calendar_range=req.calendar_range,
            location_type=getattr(req, "location_type", "city"),
            ferry_vehicle_type=getattr(req, "ferry_vehicle_type", "passenger"),
            currency=getattr(req, "currency", "TRY"),
            search_mode=getattr(req, "search_mode", "fast"),
            include_hotel=getattr(req, "include_hotel", False),
            hotel_nights=getattr(req, "hotel_nights", None)
        )
        from fastapi.encoders import jsonable_encoder
        encoded_result = jsonable_encoder(result)
        if isinstance(encoded_result, dict) and (encoded_result.get("tickets") or encoded_result.get("car_rental") or encoded_result.get("smart_hub_analysis")):
            encoded_result["cache_hit"] = False
            _set_search_warm_cache(cache_key, encoded_result)
        try:
            from app.services.analytics_service import AnalyticsService
            res_count = int(encoded_result.get("results_count") or len(encoded_result.get("tickets") or []))
            asyncio.create_task(AnalyticsService.log_event(
                event_type="search",
                transport_type=req.transport_type or "flight",
                origin=str(encoded_result.get("origin") or req.origin),
                destination=str(encoded_result.get("destination") or req.destination),
                results_count=res_count,
                ip=client_ip,
                user_agent=ua,
                referrer=ref,
            ))
        except Exception:
            pass
        return JSONResponse(content=encoded_result, headers={"X-Hakiki-Cache": "MISS"})
    except Exception as exc:
        print(f"[/api/search Hata Kalkanı Devrede]: {exc}")
        try:
            from app.services.analytics_service import AnalyticsService
            asyncio.create_task(AnalyticsService.log_event(
                event_type="search",
                transport_type=req.transport_type or "flight",
                origin=req.origin,
                destination=req.destination,
                results_count=0,
                ip=client_ip,
                user_agent=ua,
                referrer=ref,
            ))
        except Exception:
            pass
        return _build_safe_fallback_search_payload(
            req, adults, children, infants, total_pax,
            "🛡️ Anlık yoğunluk nedeniyle doğrudan resmi acente bağlantıları hazırlandı."
        )


@app.get("/api/currency/rates")
async def get_currency_rates():
    """Çoklu Para Birimi: Güncel kurlar ve semboller"""
    from app.services.currency_service import CurrencyService
    return {
        "rates": CurrencyService.get_rates(),
        "currencies": CurrencyService.CURRENCIES,
        "base": "EUR"
    }

@app.get("/api/deals")
async def get_deals(
    transport_type: str = Query("all"),
    city: str = Query(None),
    max_price: float = Query(None),
    deal_type: str = Query("all")
):
    """MODÜL 5: Güncel Resmi Kampanyalar ve Fırsatlar Vitrini"""
    deals = await CampaignService.get_all_deals(transport_type, city, max_price, deal_type=deal_type)
    return {"deals": deals, "count": len(deals)}

@app.post("/api/cars/search")
async def search_car_rentals(req: CarSearchRequest, request: Request):
    """MODÜL 6: Araç Kiralama Çoklu Karşılaştırma Modülü (Yolcu360, Enuygun, Obilet, Avis, Garenta)"""
    client_ip = _get_real_client_ip(request)
    if _is_automated_scraper_bot(request, getattr(req, "website_url", "") or "") or not _check_rate_limit(client_ip, "car_search", max_requests=40, window_sec=60):
        return JSONResponse(status_code=429, content={"cars": [], "vehicles": [], "providers": [], "rate_limited": True})
    from app.services.car_rental_service import CarRentalService
    res = CarRentalService.search_cars(
        location=req.location,
        pickup_date=req.pickup_date,
        dropoff_date=req.dropoff_date,
        location_type=getattr(req, "location_type", "city"),
        currency=getattr(req, "currency", "TRY") or "TRY"
    )
    try:
        from app.services.analytics_service import AnalyticsService
        ua = request.headers.get("user-agent", "")
        ref = request.headers.get("referer", "")
        asyncio.create_task(AnalyticsService.log_event(
            event_type="search",
            transport_type="car",
            origin=req.location,
            destination=req.location,
            results_count=len(res.get("cars") or res.get("providers") or [1]),
            ip=client_ip,
            user_agent=ua,
            referrer=ref,
        ))
    except Exception:
        pass
    return res

@app.post("/api/trackers")
async def create_tracker(req: TrackRouteRequest, request: Request):
    """MODÜL 2: Bu rotayı takibe al"""
    client_ip = _get_real_client_ip(request)
    if _is_automated_scraper_bot(request, getattr(req, "website_url", "") or "") or not _check_rate_limit(client_ip, "trackers_write", max_requests=15, window_sec=60):
        return JSONResponse(status_code=429, content={"success": False, "message": "Çok fazla işlem yapıldı. Lütfen 1 dakika sonra tekrar deneyiniz."})
    user_id = "demo-user-1"
    
    # Kullanıcı e-posta / telegram bilgisini güncelle
    if req.user_email or req.telegram_chat_id:
        conn = await get_db()
        try:
            if req.telegram_chat_id:
                await conn.execute("UPDATE users SET telegram_chat_id = ? WHERE id = ?", (req.telegram_chat_id, user_id))
            if req.user_email:
                await conn.execute("UPDATE users SET email = ? WHERE id = ?", (req.user_email, user_id))
            await conn.commit()
        finally:
            await conn.close()

    tracked = await TrackerService.create_tracked_route(
        user_id=user_id,
        origin_city=req.origin_city,
        destination_city=req.destination_city,
        target_price=req.target_price,
        travel_date_start=req.travel_date_start,
        travel_date_end=req.travel_date_end,
        transport_type=req.transport_type,
        channels=req.channels
    )
    return {"success": True, "tracker": tracked}

@app.get("/api/trackers")
async def get_trackers():
    """MODÜL 4: Kullanıcının Takip Listesi"""
    user_id = "demo-user-1"
    trackers = await TrackerService.get_user_tracked_routes(user_id)
    return {"trackers": trackers}

@app.put("/api/trackers/{route_id}/toggle")
async def toggle_tracker(route_id: str, is_active: bool = Query(...)):
    """Takip durumunu duraklat / aktif et"""
    success = await TrackerService.toggle_route_status(route_id, is_active)
    return {"success": success}

@app.delete("/api/trackers/{route_id}")
async def delete_tracker(route_id: str):
    """Takip edilen rotayı sil"""
    success = await TrackerService.delete_route(route_id)
    return {"success": success}

@app.get("/api/notifications/logs")
async def get_logs():
    """MODÜL 4: Bildirim Geçmişi"""
    user_id = "demo-user-1"
    logs = await TrackerService.get_notification_logs(user_id)
    return {"logs": logs}

@app.post("/api/notifications/test")
async def test_notification(req: TestNotificationRequest, request: Request):
    """MODÜL 3: Bildirim Kanallarını Anlık Test Et (E-posta, Telegram, Web Push) - Yönetici Korumalı"""
    _require_admin_access(request)
    res = {}
    if req.channel == "email":
        res = await NotificationService.send_email(
            to_email=req.email or "demo@ucuzbilet.com",
            route=req.route,
            price=req.price,
            regular_price=req.regular_price,
            link=req.link
        )
    elif req.channel == "telegram":
        res = await NotificationService.send_telegram(
            chat_id=req.telegram_chat_id or "123456789",
            route=req.route,
            price=req.price,
            regular_price=req.regular_price,
            link=req.link
        )
    elif req.channel == "push":
        res = await NotificationService.send_browser_push(
            title=f"🎉 Test Fırsat Alarmı: {req.route}",
            body=f"Bilet fiyatı {req.price:,.0f} ₺ oldu! (Eski Fiyat: {req.regular_price:,.0f} ₺)",
            target_url=req.link
        )
    return {"success": True, "result": res}

@app.post("/api/cron/trigger")
async def trigger_cron_now(request: Request):
    """Zamanlayıcıyı (Cron Job) Anında Tetikle - Yönetici Korumalı"""
    _require_admin_access(request)
    await scheduled_price_and_campaign_check()
    return {"success": True, "message": "Cron fiyat ve kampanya taraması anında çalıştırıldı."}

# ==================== LANSMAN ÖNCESİ ERKEN ERİŞİM & KAYIT API ====================

@app.post("/api/erken-kayit")
async def register_early_access(payload: EarlyAccessRequest, request: Request, db=Depends(get_db_dep)):
    """Ziyaretçiyi erken erişim bültenine kaydeder"""
    client_ip = _get_real_client_ip(request)
    if _is_automated_scraper_bot(request) or not _check_rate_limit(client_ip, "early_access", max_requests=5, window_sec=60):
        return JSONResponse(
            status_code=429,
            content={"success": False, "message": "Çok fazla kayıt denemesi yapıldı. Lütfen 1 dakika sonra tekrar deneyiniz."}
        )
    email = payload.email.strip().lower()
    
    # E-posta format kontrolü
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Lütfen geçerli bir e-posta adresi giriniz."}
        )
        
    if not payload.kvkk_consent:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Lütfen KVKK Aydınlatma Metni'ni onaylayınız."}
        )
        
    user_agent = request.headers.get("user-agent", "")[:255]
    
    try:
        # Zaten kayıtlı mı?
        cursor = await db.execute("SELECT id, is_active FROM prelaunch_subscribers WHERE email = ?", (email,))
        existing = await cursor.fetchone()
        
        if existing:
            # Daha önce listeden çıkmışsa tekrar aktif et
            if existing["is_active"] == 0:
                await db.execute("UPDATE prelaunch_subscribers SET is_active = 1, unsubscribed_at = NULL WHERE id = ?", (existing["id"],))
                await db.commit()
                asyncio.create_task(NotificationService.send_early_access_welcome(email))
                asyncio.create_task(NotificationService.add_contact_to_resend_audience(email, unsubscribed=False))
                return {
                    "success": True,
                    "already_registered": False,
                    "message": "Erken erişim üyeliğiniz yeniden aktif edildi! Hoş geldin e-postanız info@hakikibilet.com üzerinden gönderildi."
                }
            return {
                "success": True,
                "already_registered": True,
                "message": "Harika! Bu e-posta adresi zaten erken erişim listemizde kayıtlı. Lansman gününde ilk siz haberdar olacaksınız!"
            }
            
        await db.execute(
            "INSERT INTO prelaunch_subscribers (email, ip_address, user_agent, kvkk_consent, is_active) VALUES (?, ?, ?, ?, 1)",
            (email, client_ip, user_agent, 1 if payload.kvkk_consent else 0)
        )
        await db.commit()

        # Toplam kayıt sayısını al
        count_cursor = await db.execute("SELECT COUNT(*) as count FROM prelaunch_subscribers WHERE is_active = 1")
        count_row = await count_cursor.fetchone()
        total_subscribers = count_row["count"] if count_row else 1

        # Arka planda anında hoş geldin e-postası, yönetici bildirimi ve Resend Bulut Rehberi senkronizasyonu
        asyncio.create_task(NotificationService.send_early_access_welcome(email))
        asyncio.create_task(NotificationService.send_admin_new_lead_alert(email, total_subscribers, client_ip))
        asyncio.create_task(NotificationService.add_contact_to_resend_audience(email, unsubscribed=False))
        
        return {
            "success": True,
            "already_registered": False,
            "message": "Tebrikler! Erken erişim listemize başarıyla kaydoldunuz. Onay e-postanız info@hakikibilet.com üzerinden gönderildi."
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Kayıt işlemi sırasında bir hata oluştu: {str(e)}"}
        )

# ==================== BÜLTEN & ERKEN ERİŞİM ABONELİKTEN ÇIKMA (UNSUBSCRIBE) ====================

@app.get("/bulten/ayril", response_class=HTMLResponse)
async def unsubscribe_page(request: Request, email: str = Query("", description="Ayrılacak e-posta"), onayla: int = Query(0, description="Onay bayrağı"), db=Depends(get_db_dep)):
    """Erken erişim ve bülten listesinden çıkış sayfası (Bot/Crawler korumalı)"""
    clean_email = email.strip().lower()
    unsubscribed = False
    
    # Kurumsal e-posta güvenlik robotlarının (Microsoft SafeLinks, Proofpoint vb.)
    # linkleri arka planda otomatik tararken kullanıcıyı yanlışlıkla listeden çıkarmasını engellemek için:
    # Sadece kullanıcı sayfadaki onay butonuna bastığında (onayla=1) işlem tamamlanır.
    if clean_email and onayla == 1:
        try:
            await db.execute(
                "UPDATE prelaunch_subscribers SET is_active = 0, unsubscribed_at = CURRENT_TIMESTAMP WHERE email = ?",
                (clean_email,)
            )
            await db.commit()
            asyncio.create_task(NotificationService.add_contact_to_resend_audience(clean_email, unsubscribed=True))
            unsubscribed = True
        except Exception:
            pass
            
    return templates.TemplateResponse(
        request=request,
        name="unsubscribe.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "email": clean_email or "Belirtilmedi",
            "unsubscribed": unsubscribed
        }
    )

@app.post("/bulten/ayril", response_class=HTMLResponse)
async def unsubscribe_post(request: Request, email: str = Form(""), db=Depends(get_db_dep)):
    """Butona tıklandığında POST isteğiyle güvenli abonelik iptali"""
    clean_email = email.strip().lower()
    unsubscribed = False
    if clean_email:
        try:
            await db.execute(
                "UPDATE prelaunch_subscribers SET is_active = 0, unsubscribed_at = CURRENT_TIMESTAMP WHERE email = ?",
                (clean_email,)
            )
            await db.commit()
            asyncio.create_task(NotificationService.add_contact_to_resend_audience(clean_email, unsubscribed=True))
            unsubscribed = True
        except Exception:
            pass
            
    return templates.TemplateResponse(
        request=request,
        name="unsubscribe.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "email": clean_email or "Belirtilmedi",
            "unsubscribed": unsubscribed
        }
    )

@app.get("/api/admin/erken-kayit-listesi")
async def get_early_access_subscribers(request: Request, db=Depends(get_db_dep)):
    """Yönetici için erken kayıt listesini JSON olarak listeler"""
    _require_admin_access(request)
        
    cursor = await db.execute("SELECT id, email, is_active, unsubscribed_at, created_at, ip_address FROM prelaunch_subscribers ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    subscribers = [
        {
            "id": r["id"],
            "email": r["email"],
            "status": "Aktif" if r["is_active"] == 1 else "Ayrıldı",
            "is_active": bool(r["is_active"]),
            "created_at": r["created_at"],
            "unsubscribed_at": r["unsubscribed_at"],
            "ip": r["ip_address"]
        }
        for r in rows
    ]
    return {
        "total": len(subscribers),
        "active_total": len([s for s in subscribers if s["is_active"]]),
        "subscribers": subscribers
    }

@app.get("/api/admin/erken-kayit-csv")
async def export_early_access_csv(request: Request, db=Depends(get_db_dep)):
    """Yönetici için erken kayıt listesini Excel uyumlu CSV olarak indirir"""
    _require_admin_access(request)
        
    cursor = await db.execute("SELECT id, email, is_active, created_at, ip_address FROM prelaunch_subscribers ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    
    def _safe_csv_cell(val):
        s = str(val or "")
        if s.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{s}"
        return s

    output = io.StringIO()
    # Excel'in Türkçe karakterleri düzgün açması için UTF-8 BOM
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Sıra No", "E-posta Adresi", "Durum", "Kayıt Tarihi", "IP Adresi"])
    
    for r in rows:
        status_text = "Aktif" if r["is_active"] == 1 else "Ayrıldı"
        writer.writerow([
            r["id"],
            _safe_csv_cell(r["email"]),
            status_text,
            _safe_csv_cell(r["created_at"]),
            _safe_csv_cell(r["ip_address"] or "")
        ])
        
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=hakikibilet_erken_kayit_listesi.csv",
            "Cache-Control": "no-cache"
        }
    )

@app.post("/api/admin/toplu-lansman-duyurusu")
async def trigger_launch_announcement(request: Request, db=Depends(get_db_dep)):
    """Lansman günü SADECE aktif (ayrılmamış) erken kayıtlı kullanıcılara açılış e-postasını gönderir"""
    _require_admin_access(request)
        
    cursor = await db.execute("SELECT email FROM prelaunch_subscribers WHERE is_active = 1")
    rows = await cursor.fetchall()
    emails = [r["email"] for r in rows if r["email"]]
    
    sent_count = 0
    failed_count = 0
    
    for email in emails:
        try:
            res = await NotificationService.send_launch_announcement(email)
            if res.get("success"):
                sent_count += 1
            else:
                failed_count += 1
            # Rate limit koruması için ufak bekleme
            await asyncio.sleep(0.15)
        except Exception:
            failed_count += 1
            
    return {
        "success": True,
        "total_active": len(emails),
        "sent": sent_count,
        "failed": failed_count,
        "message": f"Toplam {len(emails)} aktif kayıtlı gezginden {sent_count} kişiye açılış müjdesi başarıyla ulaştırıldı."
    }

@app.get("/api/admin/erken-kayit-senkronize")
@app.post("/api/admin/erken-kayit-senkronize")
async def sync_early_access_audience(request: Request):
    """Resend Bulut Rehberi (Audience) ile yerel veritabanı arasında manuel tam eşitleme yapar"""
    _require_admin_access(request)
    result = await NotificationService.sync_resend_audience_with_db()
    return result


# ==================== YÖNETİCİ & ANALİTİK MODÜLÜ (/yonetim) ====================

@app.get("/yonetim", response_class=HTMLResponse)
@app.get("/yonetici", response_class=HTMLResponse)
@app.get("/yönetici", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
async def admin_analytics_page(request: Request):
    """Şifre Korumalı Yönetici & Analitik Paneli"""
    cookie = request.cookies.get("hakiki_preview_access")
    param = request.query_params.get("onizleme") or request.query_params.get("preview")
    is_authenticated = _is_valid_admin_key(cookie) or _is_valid_admin_key(param)

    from app.services.analytics_service import AnalyticsService
    active_admin_key = AnalyticsService.get_admin_password_sync()
    response = templates.TemplateResponse(
        request=request,
        name="admin_analytics.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "is_authenticated": is_authenticated,
            "active_admin_key": active_admin_key if is_authenticated else "",
        }
    )
    if _is_valid_admin_key(param) and not _is_valid_admin_key(cookie):
        response.set_cookie(
            key="hakiki_preview_access",
            value=active_admin_key,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
    return response


@app.post("/api/analytics/event")
async def record_analytics_event(request: Request):
    """Kullanıcı etkileşimlerini (sayfa görüntüleme, mail dönüşü, acente tıklaması, özellik talebi, uyarı) kaydeder"""
    client_ip = _get_real_client_ip(request)
    if not _check_rate_limit(client_ip, "analytics_event", max_requests=90, window_sec=60):
        return JSONResponse(content={"ok": False, "reason": "rate_limited"}, status_code=200)
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    allowed_types = {
        "page_view", "email_return", "affiliate_click",
        "feature_interest", "route_warning", "geo_resolve", "search"
    }
    ev_type = str(payload.get("event_type") or "page_view").strip()
    if ev_type not in allowed_types:
        return {"ok": False}

    ua = request.headers.get("user-agent", "")
    ref = str(payload.get("referrer") or request.headers.get("referer") or "")
    lang = str(payload.get("lang") or "tr")[:5]

    from app.services.analytics_service import AnalyticsService
    asyncio.create_task(AnalyticsService.log_event(
        event_type=ev_type,
        transport_type=str(payload.get("transport_type") or "")[:30],
        origin=str(payload.get("origin") or "")[:80],
        destination=str(payload.get("destination") or "")[:80],
        provider_name=str(payload.get("provider_name") or "")[:80],
        ticket_price=float(payload.get("ticket_price") or 0.0),
        currency=str(payload.get("currency") or "TRY")[:8],
        feature_name=str(payload.get("feature_name") or "")[:80],
        results_count=int(payload.get("results_count") if payload.get("results_count") is not None else -1),
        warning_text=str(payload.get("warning_text") or "")[:200],
        lang=lang,
        referrer=ref,
        utm_source=str(payload.get("utm_source") or "")[:60],
        utm_campaign=str(payload.get("utm_campaign") or "")[:60],
        ip=client_ip,
        user_agent=ua,
    ))
    return {"ok": True}


@app.get("/api/admin/analytics/summary")
async def get_admin_analytics_summary(request: Request):
    """Yönetici paneli için tüm analitik ve istatistik verilerini döner"""
    _require_admin_access(request)
    from app.services.analytics_service import AnalyticsService
    return await AnalyticsService.get_dashboard_summary()


@app.get("/api/admin/analytics/export-json")
async def export_admin_analytics_backup(request: Request):
    """Tüm analitik, abone ve alarm verilerini tek tıkla JSON yedek dosyası olarak indirir"""
    _require_admin_access(request)
    from app.services.analytics_service import AnalyticsService
    backup_data = await AnalyticsService.export_full_backup_json()
    content_bytes = json.dumps(backup_data, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=content_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=hakikibilet_analitik_yedek.json",
            "Cache-Control": "no-cache"
        }
    )


@app.post("/api/admin/analytics/import-json")
async def import_admin_analytics_backup(request: Request):
    """İndirilmiş JSON yedek dosyasını veritabanına kayıpsız geri yükler"""
    _require_admin_access(request)
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Geçersiz JSON dosyası: {e}")
    from app.services.analytics_service import AnalyticsService
    result = await AnalyticsService.import_full_backup_json(payload)
    return result


@app.post("/api/admin/change-password")
async def change_admin_password(request: Request):
    """Yönetici panelinden mevcut şifreyi doğrulayarak yeni yönetici şifresi belirler"""
    _require_admin_access(request)
    try:
        data = await request.json()
    except Exception:
        data = {}
    current_pass = str(data.get("current_password") or "").strip()
    new_pass = str(data.get("new_password") or "").strip()
    confirm_pass = str(data.get("confirm_password") or "").strip()

    if not _is_valid_admin_key(current_pass):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Mevcut şifrenizi hatalı girdiniz."}
        )
    if len(new_pass) < 4:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Yeni şifre en az 4 karakter olmalıdır."}
        )
    if new_pass != confirm_pass:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Yeni şifre ile şifre tekrarı eşleşmiyor."}
        )

    from app.services.analytics_service import AnalyticsService
    res = await AnalyticsService.update_admin_password(new_pass)
    if not res.get("success"):
        return JSONResponse(status_code=400, content=res)

    response = JSONResponse(content={
        "success": True,
        "message": "Yönetici şifreniz başarıyla güncellendi ve yedeklendi!",
        "new_token": new_pass,
    })
    response.set_cookie(
        key="hakiki_preview_access",
        value=new_pass,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax"
    )
    return response




