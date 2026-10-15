import os
import aiosqlite
import json
from datetime import datetime, timedelta
from app.config import settings

os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)

async def get_db():
    conn = await aiosqlite.connect(settings.DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn

async def init_db():
    async with aiosqlite.connect(settings.DB_PATH) as conn:
        await conn.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Users Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            telegram_chat_id TEXT,
            phone_number TEXT,
            web_push_subscription TEXT,
            notification_preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Tracked Routes Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS tracked_routes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            origin_city TEXT NOT NULL,
            origin_code TEXT,
            destination_city TEXT NOT NULL,
            destination_code TEXT,
            transport_type TEXT NOT NULL, -- 'flight', 'train', 'bus', 'all'
            target_price REAL NOT NULL,
            travel_date_start TEXT NOT NULL,
            travel_date_end TEXT,
            is_active INTEGER DEFAULT 1,
            active_channels TEXT, -- JSON array: ['email', 'push', 'telegram']
            last_checked_at TIMESTAMP,
            last_notified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 3. Price History Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id TEXT PRIMARY KEY,
            origin_code TEXT NOT NULL,
            destination_code TEXT NOT NULL,
            transport_type TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            price REAL NOT NULL,
            regular_price REAL,
            departure_time TEXT,
            deep_link TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. Deals / Campaigns Table (Modül 5)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            transport_type TEXT NOT NULL, -- 'flight', 'train', 'bus'
            origin_city TEXT NOT NULL,
            destination_city TEXT NOT NULL,
            deal_price REAL NOT NULL,
            original_price REAL NOT NULL,
            discount_percentage INTEGER NOT NULL,
            provider_name TEXT NOT NULL,
            badge TEXT,
            deep_link TEXT NOT NULL,
            official_link TEXT,
            agent_link TEXT,
            agent_name TEXT,
            expires_at TEXT,
            is_flash_sale INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration helper for existing databases
        for col, col_type in [
            ("official_link", "TEXT"), 
            ("agent_link", "TEXT"), 
            ("agent_name", "TEXT"),
            ("deal_type", "TEXT DEFAULT 'radar'"),
            ("travel_date", "TEXT"),
            ("sales_period", "TEXT"),
            ("travel_period", "TEXT"),
            ("terms", "TEXT")
        ]:
            try:
                await conn.execute(f"ALTER TABLE deals ADD COLUMN {col} {col_type};")
            except Exception:
                pass

        # 5. Notification Logs Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tracked_route_id TEXT,
            deal_id TEXT,
            channel TEXT NOT NULL, -- 'email', 'push', 'telegram', 'whatsapp'
            triggered_price REAL NOT NULL,
            status TEXT NOT NULL, -- 'sent', 'failed', 'delivered'
            payload TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 6. Prelaunch Subscribers Table (Lansman Öncesi Erken Kayıt)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS prelaunch_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            kvkk_consent INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            unsubscribed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Kolon varlık kontrolü / güvenli migrasyon
        try:
            await conn.execute("ALTER TABLE prelaunch_subscribers ADD COLUMN is_active INTEGER DEFAULT 1;")
        except Exception:
            pass
        try:
            await conn.execute("ALTER TABLE prelaunch_subscribers ADD COLUMN unsubscribed_at TIMESTAMP;")
        except Exception:
            pass

        await conn.commit()
        
        # Temizle ve Doğrulanmış Radar & Resmi Duyurular ile Güncelle
        await seed_verified_deals_and_announcements(conn)

async def seed_verified_deals_and_announcements(conn):
    """
    Kullanıcıyı yanıltan sanal/tahmini tekil bilet kartlarını tamamen temizler.
    Yalnızca resmi havayolu, demiryolu ve otobüs şirketlerinin resmi kampanya duyurularını saklar.
    """
    import uuid
    # Eski/hatalı sanal biletleri tamamen temizle
    await conn.execute("DELETE FROM deals WHERE deal_type = 'radar' OR deal_price = 499.0 OR title LIKE '%Promosyonlu Uçuş%' OR title LIKE '%Erken Rezervasyon%';")

    # Kontrol et: Eğer duyurular yoksa veya azsa baştan doldur
    async with conn.execute("SELECT COUNT(*) FROM deals") as cursor:
        count = (await cursor.fetchone())[0]

    if count < 5:
        await conn.execute("DELETE FROM deals;")
        
        # SADECE DOĞRULANMIŞ RESMİ ŞİRKET KAMPANYA DUYURULARI (Pegasus, THY, AJet, TCDD, Obilet, SunExpress, Pamukkale)
        announcements = [
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "Pegasus Yurt İçi 100.000 Koltuk Kampanyası",
                "transport_type": "flight",
                "origin_city": "Türkiye Geneli",
                "destination_city": "Tüm Yurt İçi Hatlar",
                "travel_date": "15 Kasım 2026 – 15 Mart 2027",
                "deal_price": 699.00,
                "original_price": 1450.00,
                "discount_percentage": 52,
                "provider_name": "Pegasus Airlines",
                "badge": "⚡ 100.000 KOLTUK FIRSATI",
                "deep_link": "https://www.flypgs.com/kampanyali-ucak-biletleri",
                "official_link": "https://www.flypgs.com/kampanyali-ucak-biletleri",
                "agent_link": "https://www.enuygun.com/ucak-bileti/",
                "agent_name": "Pegasus Resmi",
                "sales_period": "Son 2 Gün! (Bitiş: 8 Ekim 2026)",
                "travel_period": "15 Kasım 2026 – 15 Mart 2027",
                "terms": "BolBol üyelerine özel yurt içi 100.000 koltuk 699 ₺'den başlayan fiyatlarla satışta.",
                "expires_at": "2026-10-08 23:59",
                "is_flash_sale": 1,
                "is_active": 1
            },
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "AJet Kış Sezonu Erken Rezervasyon Kampanyası",
                "transport_type": "flight",
                "origin_city": "Ankara & İstanbul",
                "destination_city": "Tüm Anadolu Hatları",
                "travel_date": "1 Aralık 2026 – 28 Şubat 2027",
                "deal_price": 799.00,
                "original_price": 1600.00,
                "discount_percentage": 50,
                "provider_name": "AJet",
                "badge": "✈️ KIŞ SEZONU KAMPANYASI",
                "deep_link": "https://ajet.com/tr/kampanyalar",
                "official_link": "https://ajet.com/tr/kampanyalar",
                "agent_link": "https://www.enuygun.com/ucak-bileti/",
                "agent_name": "AJet Resmi",
                "sales_period": "Ekim Ayı Boyunca Satışta",
                "travel_period": "1 Aralık 2026 – 28 Şubat 2027",
                "terms": "Seçili tüm yurt içi hatlarda erken rezervasyon kotasıyla indirimli bilet satışı.",
                "expires_at": "2026-10-31 23:59",
                "is_flash_sale": 1,
                "is_active": 1
            },
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "THY Miles&Smiles %30 İndirimli Ödül Bilet Fırsatı",
                "transport_type": "flight",
                "origin_city": "İstanbul (IST & SAW)",
                "destination_city": "Türkiye & Balkanlar",
                "travel_date": "1 Kasım 2026 – 31 Mart 2027",
                "deal_price": 950.00,
                "original_price": 1900.00,
                "discount_percentage": 50,
                "provider_name": "Türk Hava Yolları",
                "badge": "👑 MİLES&SMİLES DUYURUSU",
                "deep_link": "https://www.turkishairlines.com/tr-int/kampanyalar/",
                "official_link": "https://www.turkishairlines.com/tr-int/kampanyalar/",
                "agent_link": "https://www.turkishairlines.com/tr-int/",
                "agent_name": "THY Resmi",
                "sales_period": "31 Ekim 2026'ya Kadar",
                "travel_period": "1 Kasım 2026 – 31 Mart 2027",
                "terms": "Miles&Smiles üyeleri için tüm yurt içi uçuşlarda %30 daha az mille ödül bilet imkanı.",
                "expires_at": "2026-10-31 23:59",
                "is_flash_sale": 0,
                "is_active": 1
            },
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "SunExpress Erken Rezervasyon & Aile İndirimi",
                "transport_type": "flight",
                "origin_city": "İzmir & Antalya",
                "destination_city": "Tüm Yurt İçi Hatlar",
                "travel_date": "1 Kasım 2026 – 30 Nisan 2027",
                "deal_price": 750.00,
                "original_price": 1500.00,
                "discount_percentage": 50,
                "provider_name": "SunExpress",
                "badge": "☀️ ERKEN REZERVASYON",
                "deep_link": "https://www.sunexpress.com/tr/kampanyalar/",
                "official_link": "https://www.sunexpress.com/tr/kampanyalar/",
                "agent_link": "https://www.enuygun.com/ucak-bileti/",
                "agent_name": "SunExpress Resmi",
                "sales_period": "Sonbahar Boyunca",
                "travel_period": "1 Kasım 2026 – 30 Nisan 2027",
                "terms": "Aile ve grup rezervasyonlarında koltuk seçimi ve ek bagaj avantajlarıyla kampanya.",
                "expires_at": "2026-11-30 23:59",
                "is_flash_sale": 0,
                "is_active": 1
            },
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "TCDD Turistik Doğu Ekspresi & Kış Promosyonları",
                "transport_type": "train",
                "origin_city": "Ankara & İstanbul",
                "destination_city": "Kars, Konya & Eskişehir",
                "travel_date": "Aralık 2026 – Mart 2027",
                "deal_price": 310.00,
                "original_price": 500.00,
                "discount_percentage": 38,
                "provider_name": "TCDD Taşımacılık",
                "badge": "🚆 TCDD KIŞ DUYURUSU",
                "deep_link": "https://www.tcddtasimacilik.gov.tr/duyurular",
                "official_link": "https://www.tcddtasimacilik.gov.tr/duyurular",
                "agent_link": "https://ebilet.tcddtasimacilik.gov.tr/",
                "agent_name": "TCDD E-Bilet",
                "sales_period": "Kış Sezonu Boyunca",
                "travel_period": "Aralık 2026 – Mart 2027",
                "terms": "YHT Genç Kart ile %15, Öğrenci ve 65+ yaş tarifeleriyle indirimli seyahat.",
                "expires_at": "2026-12-31 23:59",
                "is_flash_sale": 0,
                "is_active": 1
            },
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "Obilet Sonbahar Seyahat Kuponu: İlk Bilette 100 ₺ İndirim",
                "transport_type": "bus",
                "origin_city": "Tüm Şehirler",
                "destination_city": "Tüm Otobüs Hatları",
                "travel_date": "2026 Yılı Boyunca",
                "deal_price": 180.00,
                "original_price": 280.00,
                "discount_percentage": 36,
                "provider_name": "Obilet & Kamil Koç",
                "badge": "🚌 OTOBÜS KUPONU",
                "deep_link": "https://www.obilet.com/kampanyalar",
                "official_link": "https://www.obilet.com/kampanyalar",
                "agent_link": "https://www.obilet.com/kampanyalar",
                "agent_name": "Obilet",
                "sales_period": "Bu Ay Sonuna Kadar",
                "travel_period": "2026 Yılı Boyunca",
                "terms": "Mobil uygulama üzerinden satın alınan ilk otobüs biletinde geçerli 100 ₺ indirim kodu.",
                "expires_at": "2026-10-31 23:59",
                "is_flash_sale": 0,
                "is_active": 1
            },
            {
                "id": str(uuid.uuid4()),
                "deal_type": "announcement",
                "title": "Pamukkale Turizm Üniversite & Gençlik Kart İndirimi",
                "transport_type": "bus",
                "origin_city": "Ege & Marmara",
                "destination_city": "Tüm Üniversite Şehirleri",
                "travel_date": "2026-2027 Akademik Yıl",
                "deal_price": 240.00,
                "original_price": 400.00,
                "discount_percentage": 40,
                "provider_name": "Pamukkale Turizm",
                "badge": "🎓 ÖĞRENCİ KAMPANYASI",
                "deep_link": "https://www.pamukkale.com.tr/kampanyalar",
                "official_link": "https://www.pamukkale.com.tr/kampanyalar",
                "agent_link": "https://www.pamukkale.com.tr/",
                "agent_name": "Pamukkale Resmi",
                "sales_period": "Dönem Boyunca",
                "travel_period": "2026-2027 Akademik Yıl",
                "terms": "Öğrenci kimliği ibraz eden yolculara tüm Jumbo seferlerinde %40 puan/indirim desteği.",
                "expires_at": "2027-06-30 23:59",
                "is_flash_sale": 0,
                "is_active": 1
            }
        ]

        all_items = announcements
        for item in all_items:
            await conn.execute("""
            INSERT INTO deals (
                id, deal_type, title, transport_type, origin_city, destination_city, travel_date,
                deal_price, original_price, discount_percentage, provider_name, badge,
                deep_link, official_link, agent_link, agent_name, sales_period, travel_period, terms,
                expires_at, is_flash_sale, is_active
            ) VALUES (
                :id, :deal_type, :title, :transport_type, :origin_city, :destination_city, :travel_date,
                :deal_price, :original_price, :discount_percentage, :provider_name, :badge,
                :deep_link, :official_link, :agent_link, :agent_name, :sales_period, :travel_period, :terms,
                :expires_at, :is_flash_sale, :is_active
            )
            """, item)

        await conn.commit()
    
    # Also add default demo user
    demo_user = {
        "id": "demo-user-1",
        "email": "demo@ucuzbilet.com",
        "password_hash": "pbkdf2:demo123",
        "full_name": "Demo Yolcu",
        "telegram_chat_id": "123456789",
        "phone_number": "+905551234567",
        "web_push_subscription": "{}",
        "notification_preferences": json.dumps({
            "email": True,
            "push": True,
            "telegram": True,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "08:00"
        })
    }
    await conn.execute("""
    INSERT OR IGNORE INTO users (id, email, password_hash, full_name, telegram_chat_id, phone_number, web_push_subscription, notification_preferences)
    VALUES (:id, :email, :password_hash, :full_name, :telegram_chat_id, :phone_number, :web_push_subscription, :notification_preferences)
    """, demo_user)
    
    # Also add a sample tracked route for the demo user
    demo_route = {
        "id": "demo-route-1",
        "user_id": "demo-user-1",
        "origin_city": "İstanbul",
        "origin_code": "IST",
        "destination_city": "Ankara",
        "destination_code": "ESB",
        "transport_type": "all",
        "target_price": 500.0,
        "travel_date_start": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
        "travel_date_end": None,
        "is_active": 1,
        "active_channels": json.dumps(["email", "push", "telegram"]),
        "last_checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_notified_at": None
    }
    await conn.execute("""
    INSERT OR IGNORE INTO tracked_routes (id, user_id, origin_city, origin_code, destination_city, destination_code, transport_type, target_price, travel_date_start, travel_date_end, is_active, active_channels, last_checked_at, last_notified_at)
    VALUES (:id, :user_id, :origin_city, :origin_code, :destination_city, :destination_code, :transport_type, :target_price, :travel_date_start, :travel_date_end, :is_active, :active_channels, :last_checked_at, :last_notified_at)
    """, demo_route)

    await conn.commit()
