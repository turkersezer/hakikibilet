import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.services.tracker_service import TrackerService
from app.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

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
    scheduler.start()
    logger.info(f"🚀 [ZAMANLAYICI AKTİF] Her {interval_hours} saatte bir otomatik fiyat ve kampanya taraması çalışacak.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 [ZAMANLAYICI DURDURULDU]")
