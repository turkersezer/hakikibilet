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

def _check_rate_limit(ip: str, bucket: str, max_requests: int = 5, window_sec: int = 60) -> bool:
    now = time.time()
    key = f"{bucket}:{ip or 'unknown'}"
    timestamps = [t for t in _RATE_LIMIT_BUCKETS[key] if now - t < window_sec]
    if len(timestamps) >= max_requests:
        _RATE_LIMIT_BUCKETS[key] = timestamps
        return False
    timestamps.append(now)
    _RATE_LIMIT_BUCKETS[key] = timestamps
    return True

def _is_valid_admin_key(val: str) -> bool:
    if not val:
        return False
    clean = str(val).strip()
    env_key = str(getattr(settings, "MAINTENANCE_BYPASS_KEY", "") or "").strip()
    valid_lower = {"hakiki2026", "hakikibilet2026"}
    if env_key:
        valid_lower.add(env_key.lower())
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
    if query_key == settings.MAINTENANCE_BYPASS_KEY:
        if path.startswith("/api"):
            return await call_next(request)
        clean_url = str(request.url.remove_query_params(["onizleme", "preview"]))
        response = RedirectResponse(url=clean_url)
        response.set_cookie(
            key="hakiki_preview_access",
            value=settings.MAINTENANCE_BYPASS_KEY,
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
        if preview_cookie != settings.MAINTENANCE_BYPASS_KEY:
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

    return await call_next(request)

@app.post("/admin/unlock")
async def admin_unlock(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, "admin_unlock", max_requests=15, window_sec=60):
        return JSONResponse(content={"success": False, "message": "Çok fazla deneme yapıldı. Lütfen 1 dakika bekleyiniz."}, status_code=429)
    try:
        data = await request.json()
        passcode = data.get("passcode", "")
    except Exception:
        passcode = ""
        
    if _is_valid_admin_key(passcode):
        response = JSONResponse(content={"success": True, "message": "Giriş başarılı."})
        response.set_cookie(
            key="hakiki_preview_access",
            value="hakiki2026",
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return response
    return JSONResponse(content={"success": False, "message": "Geçersiz şifre. (Lütfen hakiki2026 giriniz)"}, status_code=401)

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
async def get_cities(transport_type: str = Query("all"), scope: str = Query("all")):
    """Türkiye ve dünya şehirler listesi (seyahat moduna ve kapsama göre filtrelenebilir)"""
    from app.cities import get_cities_by_transport
    filtered = get_cities_by_transport(transport_type, scope=scope)
    return {"cities": filtered, "mode": transport_type, "scope": scope, "count": len(filtered)}

@app.get("/api/system/slots")
async def get_extension_slots():
    """Tek Beyin, Üç Ekran (Web, Mobil Uygulama, WhatsApp Botu) için aktif priz/modül şalter durumu"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "extension_slots": getattr(settings, "EXTENSION_SLOTS", {}),
    }

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
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")

    try:
        result = await asyncio.to_thread(
            SearchService.search_all_tickets,
            origin_city=req.origin,
            dest_city=req.destination,
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
        try:
            from app.services.analytics_service import AnalyticsService
            res_count = int(result.get("results_count") or len(result.get("tickets") or []))
            asyncio.create_task(AnalyticsService.log_event(
                event_type="search",
                transport_type=req.transport_type or "flight",
                origin=str(result.get("origin") or req.origin),
                destination=str(result.get("destination") or req.destination),
                results_count=res_count,
                ip=client_ip,
                user_agent=ua,
                referrer=ref,
            ))
        except Exception:
            pass
        return result
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
        links = SearchService.generate_deep_links(
            req.origin, req.destination, req.departure_date, req.return_date,
            total_pax, req.trip_type, cabin_class=req.cabin_class,
            adults=adults, children=children, infants=infants
        )
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
            "deep_links": links,
            "extension_slots": getattr(settings, "EXTENSION_SLOTS", {}),
            "notices": ["🛡️ Anlık yoğunluk nedeniyle doğrudan resmi acente bağlantıları hazırlandı."],
            "results_count": 0,
            "tickets": []
        }


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
        client_ip = request.client.host if request.client else "unknown"
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
async def create_tracker(req: TrackRouteRequest):
    """MODÜL 2: Bu rotayı takibe al"""
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
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, "early_access", max_requests=5, window_sec=60):
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
        
    client_ip = request.client.host if request.client else None
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
    cookie = request.cookies.get("hakiki_preview_access")
    param = request.query_params.get("onizleme") or request.query_params.get("preview")
    if cookie != settings.MAINTENANCE_BYPASS_KEY and param != settings.MAINTENANCE_BYPASS_KEY:
        raise HTTPException(status_code=403, detail="Bu listeyi görüntülemek için yetkiniz bulunmamaktadır.")
        
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
    cookie = request.cookies.get("hakiki_preview_access")
    param = request.query_params.get("onizleme") or request.query_params.get("preview")
    if cookie != settings.MAINTENANCE_BYPASS_KEY and param != settings.MAINTENANCE_BYPASS_KEY:
        raise HTTPException(status_code=403, detail="Yetkiniz bulunmamaktadır.")
        
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

    response = templates.TemplateResponse(
        request=request,
        name="admin_analytics.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "is_authenticated": is_authenticated,
        }
    )
    if _is_valid_admin_key(param) and not _is_valid_admin_key(cookie):
        response.set_cookie(
            key="hakiki_preview_access",
            value="hakiki2026",
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
    return response


@app.post("/api/analytics/event")
async def record_analytics_event(request: Request):
    """Kullanıcı etkileşimlerini (sayfa görüntüleme, mail dönüşü, acente tıklaması, özellik talebi, uyarı) kaydeder"""
    client_ip = request.client.host if request.client else "unknown"
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



