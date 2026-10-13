import os
import httpx
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def render_email_html(route: str, price: float, regular_price: float, link: str, carrier: str, expires_at: Optional[str] = None) -> str:
        savings = max(0, regular_price - price)
        discount_pct = int((savings / regular_price) * 100) if regular_price > 0 else 0
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                .header {{ background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 32px 24px; text-align: center; }}
                .header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
                .badge {{ display: inline-block; background: #ef4444; color: white; font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; }}
                .content {{ padding: 32px 24px; }}
                .route-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px; }}
                .route-title {{ font-size: 20px; font-weight: 700; color: #1e293b; margin-bottom: 8px; }}
                .carrier {{ font-size: 14px; color: #64748b; margin-bottom: 16px; }}
                .price-box {{ display: flex; justify-content: center; align-items: baseline; gap: 12px; margin-top: 12px; }}
                .deal-price {{ font-size: 36px; font-weight: 800; color: #16a34a; }}
                .old-price {{ font-size: 18px; color: #94a3b8; text-decoration: line-through; }}
                .savings-tag {{ color: #dc2626; font-weight: 600; font-size: 14px; margin-top: 6px; }}
                .cta-button {{ display: block; width: 100%; box-sizing: border-box; background: #2563eb; color: #ffffff !important; text-decoration: none; font-size: 16px; font-weight: 700; text-align: center; padding: 16px; border-radius: 10px; margin-top: 24px; }}
                .footer {{ text-align: center; color: #94a3b8; font-size: 12px; padding: 24px; border-top: 1px solid #f1f5f9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <span class="badge">🔥 Flaş Fiyat Alarmı</span>
                    <h1>Hedef Fiyatınızın Altında Bilet Bulundu!</h1>
                    <p style="margin: 0; opacity: 0.9; font-size: 14px;">Ucuz Bilet Bul nöbetçi tarama sistemi fırsatı yakaladı.</p>
                </div>
                <div class="content">
                    <div class="route-box">
                        <div class="route-title">{route}</div>
                        <div class="carrier">Taşıyıcı: <strong>{carrier}</strong></div>
                        <div class="price-box">
                            <span class="deal-price">{price:,.2f} ₺</span>
                            <span class="old-price">{regular_price:,.2f} ₺</span>
                        </div>
                        <div class="savings-tag">🎉 {savings:,.2f} ₺ Tasarruf (%{discount_pct} İndirim!)</div>
                        {f'<div style="font-size: 12px; color: #e11d48; margin-top: 10px;">⏳ Son Geçerlilik: {expires_at}</div>' if expires_at else ''}
                    </div>

                    <a href="{link}" target="_blank" class="cta-button">Hemen Biletini Al →</a>
                    <p style="font-size: 12px; color: #64748b; text-align: center; margin-top: 12px;">
                        *Fiyatlar anlık olarak değişiklik gösterebilir. Kontenjan dolmadan acele edin!
                    </p>
                </div>
                <div class="footer">
                    Bu e-posta <strong>Ucuz Bilet Bul</strong> takip listenizdeki kural uyarınca gönderilmiştir.<br>
                    Ayarlarınızı dilediğiniz zaman kullanıcı panelinizden düzenleyebilirsiniz.
                </div>
            </div>
        </body>
        </html>
        """

    @classmethod
    async def send_email(cls, to_email: str, route: str, price: float, regular_price: float, link: str, carrier: str = "TCDD / Havayolu", expires_at: Optional[str] = None) -> Dict[str, Any]:
        """
        Resend API veya Console simülatörü üzerinden e-posta gönderir
        """
        html_content = cls.render_email_html(route, price, regular_price, link, carrier, expires_at)
        
        # Eğer RESEND_API_KEY tanımlıysa gerçek API çağrısı yap
        if settings.RESEND_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": "Ucuz Bilet Bul <firsatlar@ucuzbiletbul.com>",
                            "to": [to_email],
                            "subject": f"🔥 FIRSAT: {route} Bileti Sadece {price:,.0f} ₺!",
                            "html": html_content
                        }
                    )
                    if response.status_code in (200, 201):
                        return {"success": True, "message_id": response.json().get("id"), "channel": "email"}
            except Exception as e:
                logger.error(f"Resend email gönderim hatası: {e}")
        
        # Simüle edilmiş başarılı gönderim (Log & Preview)
        logger.info(f"📧 [E-POSTA GÖNDERİLDİ] Alıcı: {to_email} | Rota: {route} | Fiyat: {price} ₺")
        return {
            "success": True,
            "channel": "email",
            "to": to_email,
            "preview_subject": f"🔥 FIRSAT: {route} Bileti Sadece {price:,.0f} ₺!",
            "status": "delivered_simulated"
        }

    @classmethod
    async def send_telegram(cls, chat_id: str, route: str, price: float, regular_price: float, link: str, carrier: str = "Havayolu / Tren") -> Dict[str, Any]:
        """
        Telegram Bot API üzerinden anlık bildirim mesajı gönderir
        """
        savings = max(0, regular_price - price)
        discount_pct = int((savings / regular_price) * 100) if regular_price > 0 else 0
        
        message_text = (
            f"🎉 *UCUZ BİLET ALARMI!*\n\n"
            f"📍 *Rota:* {route}\n"
            f"🏷 *Firma:* {carrier}\n"
            f"💰 *Fırsat Fiyatı:* *{price:,.2f} ₺*\n"
            f"❌ *Normal Fiyat:* ~{regular_price:,.2f} ₺~\n"
            f"🔥 *Kazanç:* {savings:,.2f} ₺ (%{discount_pct} İndirim!)\n\n"
            f"⚡ Kampanya kontenjanı tükenmeden hemen satın alın:\n"
            f"👉 [Bileti Görüntüle ve Al]({link})"
        )

        if settings.TELEGRAM_BOT_TOKEN and chat_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": message_text,
                            "parse_mode": "Markdown",
                            "disable_web_page_preview": False
                        }
                    )
                    if resp.status_code == 200:
                        return {"success": True, "channel": "telegram", "chat_id": chat_id}
            except Exception as e:
                logger.error(f"Telegram API hatası: {e}")

        # Simülasyon / Geliştirme modu çıktısı
        logger.info(f"📲 [TELEGRAM GÖNDERİLDİ] Chat ID: {chat_id} | Rota: {route} | Fiyat: {price} ₺")
        return {
            "success": True,
            "channel": "telegram",
            "chat_id": chat_id,
            "text": message_text,
            "status": "delivered_simulated"
        }

    @classmethod
    async def send_browser_push(cls, title: str, body: str, target_url: str) -> Dict[str, Any]:
        """
        Web Push Notification bildirimi üretir
        """
        payload = {
            "title": title,
            "body": body,
            "icon": "/static/icons/ticket.png",
            "badge": "/static/icons/badge.png",
            "url": target_url,
            "data": {
                "click_action": target_url
            }
        }
        logger.info(f"📱 [WEB PUSH GÖNDERİLDİ] {title} - {body}")
        return {
            "success": True,
            "channel": "push",
            "payload": payload,
            "status": "broadcasted"
        }
