import asyncio
import logging
import os
import urllib.request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.services.tracker_service import TrackerService
from app.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _ping_url_sync(url: str) -> int:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 HakikiKeepAlive/1.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


async def scheduled_render_keep_alive_ping():
    """
    Render Free Tier 15 dakikalık uyku (Cold-Start / 'SERVİS UYANIYOR') ekranını
    kalıcı olarak engellemek için her 9 dakikada bir dış ağ (Cloudflare & Render Ingress)
    üzerinden /api/health uç noktasını dürter.
    """
    targets = []
    render_ext = (os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    if render_ext and render_ext.startswith("http"):
        targets.append(f"{render_ext}/api/health")
    domain = (getattr(settings, "APP_DOMAIN", "hakikibilet.com") or "hakikibilet.com").strip()
    primary_health = f"https://{domain}/api/health"
    if primary_health not in targets:
        targets.append(primary_health)

    for url in targets:
        try:
            status = await asyncio.to_thread(_ping_url_sync, url)
            logger.info(f"💓 [KEEP-ALIVE] Render uyku önleyici ping başarılı: {url} (HTTP {status})")
        except Exception as e:
            logger.debug(f"⚠️ [KEEP-ALIVE] Ping uyarısı ({url}): {e}")


async def scheduled_price_and_campaign_check():
    """
    Arka planda periyodik olarak çalışan görev (Cron Job)
    """
    logger.info("⏰ [CRON TETİKLENDİ] Fiyat taraması ve kampanya kontrolü başlatılıyor...")
    try:
        # 1. Yeni kampanyaları tara
        deals_count = await CampaignService.scan_and_update_deals()
        logger.info(f"✨ [CRON] {deals_count} yeni potansiyel fırsat kontrol edildi.")
        
        # 2. Takip listesindeki rotaların fiyatlarını kontrol et ve bildirim gönder
        results = await TrackerService.check_all_tracked_routes()
        logger.info(f"✅ [CRON TAMAMLANDI] Kontrol edilen rota: {results['total_routes_checked']}, Tetiklenen alarm: {results['triggered_alerts']}")
    except Exception as e:
        logger.error(f"❌ [CRON HATASI] {e}", exc_info=True)

def start_scheduler():
    interval_hours = settings.PRICE_CHECK_INTERVAL_HOURS
    scheduler.add_job(
        scheduled_price_and_campaign_check,
        "interval",
        hours=interval_hours,
        id="price_check_job",
        replace_existing=True
    )
    # Render 15 dk uyku (cold-start) engelleyici: Her 9 dakikada bir dış URL'den /api/health pingler
    scheduler.add_job(
        scheduled_render_keep_alive_ping,
        "interval",
        minutes=9,
        id="render_keep_alive_job",
        replace_existing=True
    )
    if not scheduler.running:
        scheduler.start()
    logger.info(
        f"🚀 [ZAMANLAYICI AKTİF] Fiyat taraması: {interval_hours} saatte bir | "
        f"Render Uyku Önleyici (Keep-Alive): 9 dakikada bir aktif."
    )

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 [ZAMANLAYICI DURDURULDU]")
