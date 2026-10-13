import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.cities import find_city
from app.services.notification_service import NotificationService
from app.services.search_service import SearchService

class TrackerService:
    @classmethod
    async def create_tracked_route(
        cls,
        user_id: str,
        origin_city: str,
        destination_city: str,
        target_price: float,
        travel_date_start: str,
        travel_date_end: Optional[str] = None,
        transport_type: str = "all",
        channels: List[str] = None
    ) -> Dict[str, Any]:
        if channels is None:
            channels = ["email", "push", "telegram"]

        origin = find_city(origin_city)
        dest = find_city(destination_city)
        
        origin_code = origin["iata"] if origin and origin.get("iata") else "IST"
        dest_code = dest["iata"] if dest and dest.get("iata") else "ESB"

        route_id = str(uuid.uuid4())
        
        conn = await get_db()
        try:
            await conn.execute("""
            INSERT INTO tracked_routes (
                id, user_id, origin_city, origin_code, destination_city, destination_code,
                transport_type, target_price, travel_date_start, travel_date_end,
                is_active, active_channels, last_checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                route_id, user_id, origin_city, origin_code, destination_city, dest_code,
                transport_type, target_price, travel_date_start, travel_date_end,
                json.dumps(channels), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            await conn.commit()
            
            return {
                "id": route_id,
                "origin_city": origin_city,
                "destination_city": destination_city,
                "target_price": target_price,
                "travel_date_start": travel_date_start,
                "transport_type": transport_type,
                "channels": channels,
                "is_active": True
            }
        finally:
            await conn.close()

    @classmethod
    async def get_user_tracked_routes(cls, user_id: str) -> List[Dict[str, Any]]:
        conn = await get_db()
        try:
            cursor = await conn.execute("""
            SELECT * FROM tracked_routes WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("active_channels"):
                    try:
                        item["active_channels"] = json.loads(item["active_channels"])
                    except Exception:
                        item["active_channels"] = ["email"]
                results.append(item)
            return results
        finally:
            await conn.close()

    @classmethod
    async def toggle_route_status(cls, route_id: str, is_active: bool) -> bool:
        conn = await get_db()
        try:
            await conn.execute(
                "UPDATE tracked_routes SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, route_id)
            )
            await conn.commit()
            return True
        finally:
            await conn.close()

    @classmethod
    async def delete_route(cls, route_id: str) -> bool:
        conn = await get_db()
        try:
            await conn.execute("DELETE FROM tracked_routes WHERE id = ?", (route_id,))
            await conn.commit()
            return True
        finally:
            await conn.close()

    @classmethod
    async def get_notification_logs(cls, user_id: str) -> List[Dict[str, Any]]:
        conn = await get_db()
        try:
            cursor = await conn.execute("""
            SELECT * FROM notification_logs WHERE user_id = ? ORDER BY sent_at DESC LIMIT 50
            """, (user_id,))
            rows = await cursor.fetchall()
            logs = []
            for r in rows:
                item = dict(r)
                if item.get("payload"):
                    try:
                        item["payload"] = json.loads(item["payload"])
                    except Exception:
                        pass
                logs.append(item)
            return logs
        finally:
            await conn.close()

    @classmethod
    async def check_all_tracked_routes(cls) -> Dict[str, Any]:
        """
        Zamanlayıcı (Cron) tarafından çalıştırılan temel kontrol motoru.
        Aktif rotaları tarar, hedef fiyatın altında olan biletleri yakalarsa
        bildirim motorunu tetikler.
        """
        conn = await get_db()
        triggered_count = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor = await conn.execute("SELECT * FROM tracked_routes WHERE is_active = 1")
            routes = await cursor.fetchall()

            for r in routes:
                route_dict = dict(r)
                route_id = route_dict["id"]
                user_id = route_dict["user_id"]
                origin = route_dict["origin_city"]
                dest = route_dict["destination_city"]
                target_price = route_dict["target_price"]
                dep_date = route_dict["travel_date_start"]
                channels = json.loads(route_dict["active_channels"]) if route_dict["active_channels"] else ["email"]

                # Kullanıcı bilgilerini çek (e-posta, telegram, quiet hours)
                user_cur = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user = await user_cur.fetchone()
                if not user:
                    continue
                user_dict = dict(user)

                # Arama servisinden anlık bilet fiyatlarını al
                search_res = SearchService.search_all_tickets(
                    origin, dest, dep_date, passengers=1, transport_type=route_dict["transport_type"]
                )
                
                cheapest_ticket = None
                if search_res.get("tickets"):
                    cheapest_ticket = search_res["tickets"][0] # En ucuz bilet

                # Fiyat eşiği kontrolü
                if cheapest_ticket and cheapest_ticket["price"] <= target_price:
                    # Spam koruması: Son bildirim 6 saat içinde gönderilmişse bekle
                    last_notified = route_dict.get("last_notified_at")
                    if last_notified:
                        last_dt = datetime.strptime(last_notified, "%Y-%m-%d %H:%M:%S")
                        if datetime.now() - last_dt < timedelta(hours=6):
                            continue # Henüz spam süresi dolmadı

                    # Bildirim gönder
                    route_label = f"{origin} → {dest} ({cheapest_ticket['carrier']})"
                    direct_link = cheapest_ticket["direct_link"]
                    current_price = cheapest_ticket["price"]
                    regular_price = cheapest_ticket.get("regular_price", current_price * 1.5)

                    # Kanal dağıtımı (Fan-Out)
                    if "email" in channels and user_dict.get("email"):
                        await NotificationService.send_email(
                            to_email=user_dict["email"],
                            route=route_label,
                            price=current_price,
                            regular_price=regular_price,
                            link=direct_link,
                            carrier=cheapest_ticket["carrier"]
                        )
                        await cls._log_notification(conn, user_id, route_id, "email", current_price, {
                            "route": route_label,
                            "carrier": cheapest_ticket["carrier"],
                            "link": direct_link
                        })

                    if "telegram" in channels and user_dict.get("telegram_chat_id"):
                        await NotificationService.send_telegram(
                            chat_id=user_dict["telegram_chat_id"],
                            route=route_label,
                            price=current_price,
                            regular_price=regular_price,
                            link=direct_link,
                            carrier=cheapest_ticket["carrier"]
                        )
                        await cls._log_notification(conn, user_id, route_id, "telegram", current_price, {
                            "route": route_label,
                            "carrier": cheapest_ticket["carrier"],
                            "link": direct_link
                        })

                    if "push" in channels:
                        await NotificationService.send_browser_push(
                            title=f"🔥 Fırsat Yakalandı: {route_label}",
                            body=f"Fiyat hedefinizin altına düştü: {current_price:,.0f} ₺ (Eski: {regular_price:,.0f} ₺)",
                            target_url=direct_link
                        )
                        await cls._log_notification(conn, user_id, route_id, "push", current_price, {
                            "route": route_label,
                            "link": direct_link
                        })

                    # Rota last_notified_at güncelle
                    await conn.execute(
                        "UPDATE tracked_routes SET last_checked_at = ?, last_notified_at = ? WHERE id = ?",
                        (now_str, now_str, route_id)
                    )
                    triggered_count += 1
                else:
                    # Sadece last_checked_at güncelle
                    await conn.execute(
                        "UPDATE tracked_routes SET last_checked_at = ? WHERE id = ?",
                        (now_str, route_id)
                    )

            await conn.commit()
            return {
                "checked_at": now_str,
                "total_routes_checked": len(routes),
                "triggered_alerts": triggered_count
            }
        finally:
            await conn.close()

    @classmethod
    async def _log_notification(cls, conn, user_id: str, route_id: str, channel: str, price: float, payload: dict):
        log_id = str(uuid.uuid4())
        await conn.execute("""
        INSERT INTO notification_logs (id, user_id, tracked_route_id, channel, triggered_price, status, payload)
        VALUES (?, ?, ?, ?, ?, 'sent', ?)
        """, (log_id, user_id, route_id, channel, price, json.dumps(payload)))
