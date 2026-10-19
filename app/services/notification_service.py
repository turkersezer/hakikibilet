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
                    <span class="badge">🔥 Hakiki Fiyat Alarmı</span>
                    <h1>Hedef Fiyatınızın Altında Bilet Bulundu!</h1>
                    <p style="margin: 0; opacity: 0.9; font-size: 14px;">Hakiki Bilet fırsat takip radarı en uygun fiyatı yakaladı.</p>
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
                    Bu e-posta <strong>Hakiki Bilet</strong> (hakikibilet.com) takip listenizdeki kural uyarınca gönderilmiştir.<br>
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
                            "Content-Type": "application/json",
                            "User-Agent": "HakikiBiletApp/1.0"
                        },
                        json={
                            "from": settings.RESEND_FROM_EMAIL,
                            "to": [to_email],
                            "reply_to": settings.RESEND_REPLY_TO,
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
    async def send_custom_email(cls, to_email: str, subject: str, html_content: str, reply_to: Optional[str] = None) -> Dict[str, Any]:
        """Resend üzerinden genel amaçlı kurumsal e-posta gönderir"""
        if not settings.RESEND_API_KEY:
            logger.warning(f"Resend API anahtarı tanımlı değil. E-posta simüle edildi: {to_email}")
            return {"success": False, "simulated": True, "message": "Resend API anahtarı yok."}
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                        "User-Agent": "HakikiBiletApp/1.0"
                    },
                    json={
                        "from": settings.RESEND_FROM_EMAIL,
                        "to": [to_email],
                        "reply_to": reply_to or settings.RESEND_REPLY_TO,
                        "subject": subject,
                        "html": html_content,
                        "headers": {
                            "List-Unsubscribe": f"<https://hakikibilet.com/bulten/ayril?email={to_email}>",
                            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
                        }
                    }
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"✅ Kurumsal e-posta gönderildi: {to_email} (ID: {data.get('id')})")
                    return {"success": True, "id": data.get("id")}
                else:
                    logger.error(f"Resend API hatası ({response.status_code}): {response.text}")
                    return {"success": False, "status_code": response.status_code, "error": response.text}
        except Exception as e:
            logger.error(f"E-posta gönderim istisnası: {str(e)}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def send_early_access_welcome(cls, subscriber_email: str) -> Dict[str, Any]:
        """Yeni erken kayıt yaptıran kullanıcıya şık kurumsal hoş geldin e-postası gönderir"""
        subject = "✈️ Hakiki Bilet Erken Erişim Kulübüne Hoş Geldiniz!"
        html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
                .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(15,23,42,0.08); border: 1px solid #e2e8f0; }}
                .hero {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: #ffffff; padding: 40px 32px; text-align: center; border-bottom: 3px solid #f59e0b; }}
                .brand-title {{ font-size: 28px; font-weight: 900; letter-spacing: -0.5px; margin: 0; color: #ffffff; }}
                .brand-gold {{ color: #f59e0b; }}
                .brand-slogan {{ font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; color: #fde68a; margin-top: 6px; }}
                .badge {{ display: inline-block; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; font-size: 11px; font-weight: 800; padding: 4px 14px; border-radius: 9999px; text-transform: uppercase; margin-bottom: 12px; }}
                .body-content {{ padding: 36px 32px; line-height: 1.7; font-size: 15px; color: #334155; }}
                .body-content h2 {{ font-size: 20px; font-weight: 800; color: #0f172a; margin-top: 0; }}
                .feature-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 18px 20px; margin: 24px 0; }}
                .feature-item {{ margin: 8px 0; font-size: 14px; color: #1e293b; }}
                .button {{ display: block; text-align: center; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0f172a !important; font-weight: 800; font-size: 15px; padding: 16px 28px; border-radius: 12px; text-decoration: none; margin-top: 28px; box-shadow: 0 4px 14px rgba(217,119,6,0.3); }}
                .footer {{ background: #f8fafc; padding: 24px 32px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #f1f5f9; }}
                .unsub-link {{ color: #94a3b8; text-decoration: underline; margin-top: 8px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="hero">
                    <span class="badge">✨ Erken Erişim Kulübü</span>
                    <h1 class="brand-title">HAKİKİ <span class="brand-gold">BİLET</span></h1>
                    <div class="brand-slogan">Hakiki Fiyat, Hakiki Bilet</div>
                </div>
                <div class="body-content">
                    <h2>Aramıza Hoş Geldiniz! ✈️</h2>
                    <p>
                        Kulaktan dolma fiyatlara, yanıltıcı indirimlere ve gizli acente komisyonlarına son verecek bağımsız seyahat hareketimizde yerinizi aldınız.
                    </p>
                    <p>
                        Şu an kapalı beta sürecindeyiz ve platformumuzun son hazırlıklarını tamamlıyoruz. Kapılar açıldığında:
                    </p>
                    <div class="feature-box">
                        <div class="feature-item">✈️ <strong>Tüm Havayolları:</strong> THY, Pegasus, AJet ve dünya uçuşları tek ekranda.</div>
                        <div class="feature-item">🌙 <strong>Dip Fiyat Radarı:</strong> Gece ve erken saatlerdeki gizli dip fiyatlar anında en üstte.</div>
                        <div class="feature-item">🚌 <strong>Şehirlerarası Otobüsler:</strong> Türkiye'nin tüm otobüs güzergahları.</div>
                        <div class="feature-item">🛡️ <strong>%100 Şeffaflık:</strong> Sıfır gizli komisyon, doğrudan resmi acente/taşıyıcı yönlendirmesi.</div>
                    </div>
                    <p>
                        Lansman günümüzde kapılar açıldığı an ilk haberdar olan ayrıcalıklı kitle arasında olacaksınız.
                    </p>
                    <a href="https://hakikibilet.com" class="button">Hakiki Bilet'i İnceleyin →</a>
                    <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
                        <em>Sorularınız veya seyahat önerileriniz için bu e-postayı doğrudan yanıtlayabilirsiniz.</em>
                    </p>
                </div>
                <div class="footer">
                    <strong>Hakiki Bilet</strong> — Bağımsız Seyahat ve Fiyat Karşılaştırma Portalı<br>
                    hakikibilet.com • info@hakikibilet.com<br>
                    Bu e-posta, hakikibilet.com erken erişim talebiniz doğrultusunda gönderilmiştir.<br>
                    <a href="https://hakikibilet.com/bulten/ayril?email={subscriber_email}" class="unsub-link">Erken Erişim Listesinden Çık</a>
                </div>
            </div>
        </body>
        </html>
        """
        return await cls.send_custom_email(subscriber_email, subject, html)

    @classmethod
    async def send_admin_new_lead_alert(cls, subscriber_email: str, total_count: int, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Yeni bir kayıt olduğunda hakikibilet@gmail.com adresine yönetici bildirimi gönderir"""
        subject = f"🔔 Yeni Erken Kayıt: {subscriber_email} (Toplam: {total_count})"
        html = f"""
        <div style="font-family: sans-serif; padding: 20px; color: #1e293b;">
            <h2 style="color: #0f172a;">🎉 Yeni Bir Ziyaretçi Erken Erişime Kaydoldu!</h2>
            <div style="background: #f1f5f9; padding: 16px; border-radius: 12px; margin: 16px 0;">
                <p><strong>E-posta:</strong> {subscriber_email}</p>
                <p><strong>IP Adresi:</strong> {ip_address or 'Bilinmiyor'}</p>
                <p><strong>Toplam Kayıtlı Gezgin Sayısı:</strong> <span style="color: #d97706; font-size: 18px; font-weight: bold;">{total_count}</span></p>
            </div>
            <p style="font-size: 12px; color: #64748b;">
                Bu bildirim Hakiki Bilet erken kayıt motoru tarafından otomatik olarak gönderilmiştir.
            </p>
        </div>
        """
        return await cls.send_custom_email(settings.ADMIN_NOTIFICATION_EMAIL, subject, html)

    @classmethod
    async def send_launch_announcement(cls, to_email: str) -> Dict[str, Any]:
        """Lansman günü tüm erken kayıtlı kullanıcılara açılış müjdesi gönderir"""
        subject = "🚀 Kapılar Açıldı: Hakiki Bilet Artık Canlı Yayında!"
        html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
                .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(15,23,42,0.08); border: 1px solid #e2e8f0; }}
                .hero {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: #ffffff; padding: 40px 32px; text-align: center; border-bottom: 3px solid #f59e0b; }}
                .brand-title {{ font-size: 28px; font-weight: 900; letter-spacing: -0.5px; margin: 0; color: #ffffff; }}
                .brand-gold {{ color: #f59e0b; }}
                .brand-slogan {{ font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; color: #fde68a; margin-top: 6px; }}
                .badge {{ display: inline-block; background: #10b981; color: #ffffff; font-size: 11px; font-weight: 800; padding: 4px 14px; border-radius: 9999px; text-transform: uppercase; margin-bottom: 12px; }}
                .body-content {{ padding: 36px 32px; line-height: 1.7; font-size: 15px; color: #334155; }}
                .body-content h2 {{ font-size: 22px; font-weight: 900; color: #0f172a; margin-top: 0; }}
                .button {{ display: block; text-align: center; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0f172a !important; font-weight: 900; font-size: 16px; padding: 18px 28px; border-radius: 14px; text-decoration: none; margin: 32px 0 20px 0; box-shadow: 0 4px 16px rgba(217,119,6,0.35); }}
                .footer {{ background: #f8fafc; padding: 24px 32px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #f1f5f9; }}
                .unsub-link {{ color: #94a3b8; text-decoration: underline; margin-top: 8px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="hero">
                    <span class="badge">🚀 RESMİ LANSMAN</span>
                    <h1 class="brand-title">HAKİKİ <span class="brand-gold">BİLET</span></h1>
                    <div class="brand-slogan">Hakiki Fiyat, Hakiki Bilet</div>
                </div>
                <div class="body-content">
                    <h2>Beklediğiniz Gün Geldi: Kapılar Açıldı! 🎉</h2>
                    <p>
                        Erken erişim davetimize katıldığınız için teşekkür ederiz. Türkiye'nin bağımsız seyahat ve dip fiyat arama motoru <strong>Hakiki Bilet</strong> resmen yayında!
                    </p>
                    <p>
                        Artık gizli komisyonlar, yapay fiyat artışları ve yanıltıcı rakamlar olmadan Türkiye'nin tüm havayolu ve otobüs seferlerini tek tıkla canlı karşılaştırabilirsiniz.
                    </p>
                    <a href="https://hakikibilet.com" class="button">Hemen Hakiki Fiyatları Karşılaştırın →</a>
                    <p style="font-size: 13px; color: #64748b;">
                        İlk seyahatinizde hakiki fiyat avantajını keşfedin. Bizi tercih ettiğiniz için teşekkür ederiz!
                    </p>
                </div>
                <div class="footer">
                    <strong>Hakiki Bilet</strong> — Bağımsız Seyahat Portalı<br>
                    hakikibilet.com • info@hakikibilet.com<br>
                    <a href="https://hakikibilet.com/bulten/ayril?email={to_email}" class="unsub-link">Duyuru Listesinden Çık</a>
                </div>
            </div>
        </body>
        </html>
        """
        return await cls.send_custom_email(to_email, subject, html)

    @classmethod
    async def send_telegram(cls, chat_id: str, route: str, price: float, regular_price: float, link: str, carrier: str = "Havayolu / Tren") -> Dict[str, Any]:
        """
        Telegram Bot API üzerinden anlık bildirim mesajı gönderir
        """
        savings = max(0, regular_price - price)
        discount_pct = int((savings / regular_price) * 100) if regular_price > 0 else 0
        
        message_text = (
            f"🎫 *HAKİKİ BİLET — FİYAT ALARMI!*\n"
            f"🏷 _Hakiki Fiyat, Hakiki Bilet_\n\n"
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

    # ==================== RESEND AUDIENCES (BULUT REHBER SENKRONİZASYONU) ====================

    @classmethod
    async def add_contact_to_resend_audience(cls, email: str, unsubscribed: bool = False) -> Dict[str, Any]:
        """
        Kayıt olan ziyaretçiyi anında Resend Cloud Audience listesine ekler veya günceller.
        Bu sayede Render sunucusu yeniden başlasa veya disk sıfırlansa bile veriler Resend'de güvenle saklanır.
        """
        if not settings.RESEND_API_KEY or not getattr(settings, "RESEND_AUDIENCE_ID", None):
            return {"success": False, "message": "Resend API veya Audience ID eksik."}

        clean_email = email.strip().lower()
        url = f"https://api.resend.com/audiences/{settings.RESEND_AUDIENCE_ID}/contacts"
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                if unsubscribed:
                    # Önce email ile PATCH dene, olmazsa POST et
                    patch_resp = await client.patch(f"{url}/{clean_email}", headers=headers, json={"unsubscribed": True})
                    if patch_resp.status_code in (200, 201):
                        return {"success": True, "action": "unsubscribed_patched"}
                    post_resp = await client.post(url, headers=headers, json={"email": clean_email, "unsubscribed": True})
                    return {"success": post_resp.status_code in (200, 201), "action": "unsubscribed_created"}
                else:
                    # Yeni abone veya yeniden aktifleşen
                    post_resp = await client.post(url, headers=headers, json={"email": clean_email, "unsubscribed": False})
                    if post_resp.status_code in (200, 201):
                        return {"success": True, "action": "created_or_active"}
                    patch_resp = await client.patch(f"{url}/{clean_email}", headers=headers, json={"unsubscribed": False})
                    return {"success": patch_resp.status_code in (200, 201), "action": "reactivated"}
        except Exception as e:
            logger.error(f"Resend Audience güncelleme hatası ({clean_email}): {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def fetch_resend_contacts(cls) -> list:
        """Resend Cloud Audience listesindeki tüm kişileri çeker"""
        if not settings.RESEND_API_KEY or not getattr(settings, "RESEND_AUDIENCE_ID", None):
            return []
        url = f"https://api.resend.com/audiences/{settings.RESEND_AUDIENCE_ID}/contacts"
        headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", [])
        except Exception as e:
            logger.error(f"Resend Audience kişi listesi çekilemedi: {e}")
        return []

    @classmethod
    async def sync_resend_audience_with_db(cls) -> Dict[str, Any]:
        """
        Resend Bulut Rehberi ile yerel SQLite veritabanı arasında iki yönlü tam eşitleme yapar.
        1. Resend'deki tüm kişileri SQLite'a aktarır (Render restart sonrası sıfır veri kaybı).
        2. SQLite'ta olup Resend'e henüz gitmemiş kayıtları Resend'e yükler.
        """
        import aiosqlite
        contacts = await cls.fetch_resend_contacts()
        resend_emails = {c["email"].strip().lower(): c for c in contacts if c.get("email")}
        
        restored_count = 0
        pushed_count = 0
        
        async with aiosqlite.connect(settings.DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT id, email, is_active FROM prelaunch_subscribers")
            db_rows = await cursor.fetchall()
            db_emails = {r["email"].strip().lower(): r for r in db_rows if r["email"]}
            
            # Adım 1: Resend'de olan ama yerel DB'de olmayanları geri yükle
            for email, c in resend_emails.items():
                is_active = 0 if c.get("unsubscribed") else 1
                if email not in db_emails:
                    created_at = c.get("created_at")
                    await conn.execute(
                        "INSERT OR IGNORE INTO prelaunch_subscribers (email, is_active, created_at) VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP))",
                        (email, is_active, created_at)
                    )
                    restored_count += 1
                else:
                    # Durum farkı varsa eşitle
                    if db_emails[email]["is_active"] != is_active:
                        await conn.execute(
                            "UPDATE prelaunch_subscribers SET is_active = ? WHERE email = ?",
                            (is_active, email)
                        )
            await conn.commit()
            
            # Adım 2: Yerel DB'de olup Resend'de henüz olmayanları buluta yedekle
            for email, r in db_emails.items():
                if email not in resend_emails:
                    unsub = (r["is_active"] == 0)
                    await cls.add_contact_to_resend_audience(email, unsubscribed=unsub)
                    pushed_count += 1
                    
        logger.info(f"🔄 [RESEND SENKRONİZASYON] Tamamlandı: {restored_count} geri yüklendi, {pushed_count} buluta aktarıldı.")
        return {
            "success": True,
            "resend_total": len(resend_emails),
            "restored_to_local_db": restored_count,
            "pushed_to_resend": pushed_count
        }
