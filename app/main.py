from fastapi import FastAPI, Request, Query, HTTPException, Depends
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
from app.database import init_db, get_db
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
    
    # Yasal uyum sayfaları, doğrudan lansman vitrini, erken kayıt API'si, bülten ayrılma, statik dosyalar, favicon ve robots her zaman herkese açık
    legal_paths = ("/lansman", "/api/erken-kayit", "/bulten/ayril", "/yasal-uyari", "/kullanim-kosullari", "/kvkk", "/cerez-politikasi", "/etkinlik-kurallari", "/iletisim", "/hukuk", "/legal")
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
    template_name = "index.html" if request.query_params.get("v") == "1" else "index_v2.html"
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

@app.post("/api/search")
async def search_tickets(req: SearchRequest):
    """
    MODÜL 1: Bilet Arama ve Parametreli Deep Linkler (Tek Yön, Gidiş-Dönüş, Gezgin Modu)
    Skyscanner, Google Flights, Enuygun, TCDD, Obilet, Kamil Koç
    """
    adults = req.adults if req.adults is not None else req.passengers
    children = req.children if req.children is not None else 0
    infants = req.infants if req.infants is not None else 0
    total_pax = max(1, adults + children + infants)

    result = SearchService.search_all_tickets(
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

# ==================== LANSMAN ÖNCESİ ERKEN ERİŞİM & KAYIT API ====================

@app.post("/api/erken-kayit")
async def register_early_access(payload: EarlyAccessRequest, request: Request, db=Depends(get_db)):
    """Ziyaretçiyi erken erişim bültenine kaydeder"""
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

        # Arka planda anında hoş geldin e-postası ve yönetici bildirimi gönder (ziyaretçiyi bekletmeden)
        asyncio.create_task(NotificationService.send_early_access_welcome(email))
        asyncio.create_task(NotificationService.send_admin_new_lead_alert(email, total_subscribers, client_ip))
        
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
async def unsubscribe_page(request: Request, email: str = Query("", description="Ayrılacak e-posta"), db=Depends(get_db)):
    """Erken erişim ve bülten listesinden güvenli tek tıkla çıkış sayfası"""
    clean_email = email.strip().lower()
    if clean_email:
        try:
            await db.execute(
                "UPDATE prelaunch_subscribers SET is_active = 0, unsubscribed_at = CURRENT_TIMESTAMP WHERE email = ?",
                (clean_email,)
            )
            await db.commit()
        except Exception:
            pass
            
    return templates.TemplateResponse(
        request=request,
        name="unsubscribe.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "email": clean_email or "Belirtilmedi"
        }
    )

@app.get("/api/admin/erken-kayit-listesi")
async def get_early_access_subscribers(request: Request, db=Depends(get_db)):
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
async def export_early_access_csv(request: Request, db=Depends(get_db)):
    """Yönetici için erken kayıt listesini Excel uyumlu CSV olarak indirir"""
    cookie = request.cookies.get("hakiki_preview_access")
    param = request.query_params.get("onizleme") or request.query_params.get("preview")
    if cookie != settings.MAINTENANCE_BYPASS_KEY and param != settings.MAINTENANCE_BYPASS_KEY:
        raise HTTPException(status_code=403, detail="Yetkiniz bulunmamaktadır.")
        
    cursor = await db.execute("SELECT id, email, is_active, created_at, ip_address FROM prelaunch_subscribers ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    
    output = io.StringIO()
    # Excel'in Türkçe karakterleri düzgün açması için UTF-8 BOM
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Sıra No", "E-posta Adresi", "Durum", "Kayıt Tarihi", "IP Adresi"])
    
    for r in rows:
        status_text = "Aktif" if r["is_active"] == 1 else "Ayrıldı"
        writer.writerow([r["id"], r["email"], status_text, r["created_at"], r["ip_address"] or ""])
        
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
async def trigger_launch_announcement(request: Request, db=Depends(get_db)):
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

