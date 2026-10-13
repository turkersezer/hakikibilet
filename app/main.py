from fastapi import FastAPI, Request, Query, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from contextlib import asynccontextmanager
import os
import json

from app.config import settings
from app.database import init_db, get_db
from app.cities import TURKEY_CITIES, ALL_LOCATIONS, find_city, get_cities_by_transport
from app.models import (
    SearchRequest, CarSearchRequest, TrackRouteRequest, UserSettingsUpdate, TestNotificationRequest
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
    
    # Statik dosyalar, favicon ve robots her zaman açık
    if path.startswith("/static") or path in ("/favicon.ico", "/robots.txt"):
        return await call_next(request)
        
    # URL parametresiyle doğrudan yönetici girişi: ?onizleme=hakiki2026 veya ?preview=hakiki2026
    query_key = request.query_params.get("onizleme") or request.query_params.get("preview")
    if query_key == settings.MAINTENANCE_BYPASS_KEY:
        clean_url = str(request.url.remove_query_params(["onizleme", "preview"]))
        response = RedirectResponse(url=clean_url)
        response.set_cookie(
            key="hakiki_preview_access",
            value=settings.MAINTENANCE_BYPASS_KEY,
            max_age=30 * 24 * 3600,
            httponly=False,
            samesite="lax"
        )
        return response

    # Admin kilit açma / kapama yolları serbest
    if path == "/admin/unlock" and request.method == "POST":
        return await call_next(request)
    if path == "/admin/lock":
        return await call_next(request)

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
    try:
        data = await request.json()
        passcode = data.get("passcode", "")
    except Exception:
        passcode = ""
        
    if passcode == settings.MAINTENANCE_BYPASS_KEY:
        response = JSONResponse(content={"success": True, "message": "Giriş başarılı."})
        response.set_cookie(
            key="hakiki_preview_access",
            value=settings.MAINTENANCE_BYPASS_KEY,
            max_age=30 * 24 * 3600,
            httponly=False,
            samesite="lax"
        )
        return response
    return JSONResponse(content={"success": False, "message": "Geçersiz şifre."}, status_code=401)

@app.get("/admin/lock")
async def admin_lock():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="hakiki_preview_access")
    return response

# ==================== SAYFA ROTALARI (HTML) ====================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Ana Sayfa: Arama Motoru + Doğrulanmış Fırsat Radarı & Şirket Kampanyaları & Gezgin Keşif Rehberi"""
    radar_deals = await CampaignService.get_radar_deals()
    announcements = await CampaignService.get_official_announcements()
    curated_events = SearchService.get_curated_events()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
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

@app.post("/api/search")
async def search_tickets(req: SearchRequest):
    """
    MODÜL 1: Bilet Arama ve Parametreli Deep Linkler (Tek Yön, Gidiş-Dönüş, Gezgin Modu)
    Skyscanner, Google Flights, Enuygun, TCDD, Obilet, Kamil Koç
    """
    result = SearchService.search_all_tickets(
        origin_city=req.origin,
        dest_city=req.destination,
        departure_date=req.departure_date,
        return_date=req.return_date,
        passengers=req.passengers,
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
    return result

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
async def search_car_rentals(req: CarSearchRequest):
    """MODÜL 6: Araç Kiralama Çoklu Karşılaştırma Modülü (Yolcu360, Enuygun, Obilet, Avis, Garenta)"""
    from app.services.car_rental_service import CarRentalService
    return CarRentalService.search_cars(
        location=req.location,
        pickup_date=req.pickup_date,
        dropoff_date=req.dropoff_date,
        location_type=getattr(req, "location_type", "city"),
        currency=getattr(req, "currency", "TRY") or "TRY"
    )

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
async def test_notification(req: TestNotificationRequest):
    """MODÜL 3: Bildirim Kanallarını Anlık Test Et (E-posta, Telegram, Web Push)"""
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
async def trigger_cron_now():
    """Zamanlayıcıyı (Cron Job) Anında Tetikle"""
    await scheduled_price_and_campaign_check()
    return {"success": True, "message": "Cron fiyat ve kampanya taraması anında çalıştırıldı."}
