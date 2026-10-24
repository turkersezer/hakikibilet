from fastapi import Request
from fastapi.responses import HTMLResponse
from app.main import (
    app,
    templates,
    settings,
    ALL_LOCATIONS,
    CampaignService,
    SearchService,
)

# Sadece 8143 portundaki süreçte "/" rotasını index_v3.html olarak переопределяем (8000 portuna dokunmaz)
app.router.routes = [
    r for r in app.router.routes
    if not (getattr(r, "path", None) == "/" and "GET" in getattr(r, "methods", set()))
]

@app.get("/", response_class=HTMLResponse)
async def home_page_v3(request: Request):
    """Minimalist Bento Vitrin + Kompakt Arama Çalışma Alanı (v3 - Port 8143)"""
    radar_deals = await CampaignService.get_radar_deals()
    announcements = await CampaignService.get_official_announcements()
    curated_events = SearchService.get_curated_events()
    return templates.TemplateResponse(
        request=request,
        name="index_v3.html",
        context={
            "app_name": settings.APP_NAME,
            "app_slogan": settings.APP_SLOGAN,
            "app_domain": settings.APP_DOMAIN,
            "cities": ALL_LOCATIONS,
            "radar_deals": radar_deals,
            "announcements": announcements,
            "deals": radar_deals,
            "curated_events": curated_events,
            "legal_disclaimer": settings.LEGAL_DISCLAIMER,
        },
    )
