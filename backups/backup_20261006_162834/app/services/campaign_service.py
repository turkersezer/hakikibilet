from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from app.database import get_db

class CampaignService:
    @classmethod
    async def get_all_deals(
        cls, 
        transport_type: Optional[str] = None, 
        city: Optional[str] = None, 
        max_price: Optional[float] = None,
        deal_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = await get_db()
        try:
            query = "SELECT * FROM deals WHERE is_active = 1"
            params = []

            if deal_type and deal_type != "all":
                query += " AND deal_type = ?"
                params.append(deal_type)

            if transport_type and transport_type != "all":
                query += " AND transport_type = ?"
                params.append(transport_type)

            if city:
                query += " AND (LOWER(origin_city) LIKE ? OR LOWER(destination_city) LIKE ?)"
                city_param = f"%{city.lower()}%"
                params.extend([city_param, city_param])

            if max_price:
                query += " AND deal_price <= ?"
                params.append(max_price)

            query += " ORDER BY discount_percentage DESC, deal_price ASC"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_radar_deals(cls, transport_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """30-90 gün sonrası doğrulanmış gerçek erken rezervasyon biletleri"""
        return await cls.get_all_deals(transport_type=transport_type, deal_type="radar")

    @classmethod
    async def get_official_announcements(cls, transport_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pegasus, THY, AJet, TCDD ve Obilet resmi kampanya duyuruları"""
        return await cls.get_all_deals(transport_type=transport_type, deal_type="announcement")

    @classmethod
    async def scan_and_update_deals(cls):
        """
        Sistem belirli aralıklarla (Cron) süresi dolan duyuruları arşivler
        ve doğrulanmış radar fırsatlarını günceller.
        """
        conn = await get_db()
        try:
            # Süresi geçmiş kampanyaları deaktif et
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            await conn.execute("UPDATE deals SET is_active = 0 WHERE expires_at < ?", (now_str,))
            await conn.commit()
            return True
        finally:
            await conn.close()
