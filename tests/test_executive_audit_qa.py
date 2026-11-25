from fastapi.testclient import TestClient
from app.main import app, _SEARCH_WARM_CACHE, _RATE_LIMIT_BUCKETS

client = TestClient(app)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


def test_homepage_renders_executive_audit_controls():
    res = client.get("/", headers=BROWSER_HEADERS)
    assert res.status_code == 200
    html = res.text
    assert "hakiki-currency-select" in html
    assert "tabPriceHint-flight" in html
    assert "hbTransportWebsiteTrap" in html
    assert "app_v3.js?v=20261124_v52" in html


def test_all_26_approved_global_affiliate_programs_enrichment():
    from app.services.revenue_service import RevenueService

    # 1. Trip.com Doğrudan Ortaklık
    trip_link = RevenueService.enrich_deep_link("trip", "https://tr.trip.com/flights/", "flight")
    assert "Allianceid=11051531" in trip_link and "SID=333747492" in trip_link

    # 2. 24 Travelpayouts Deep-Link Programı (Marker: 789884, TRS: 585474)
    expected_tp = {
        "kiwi": ("https://www.kiwi.com/tr/", "campaign_id=111", "p=4136"),
        "aviasales": ("https://www.aviasales.com/", "campaign_id=100", "p=4114"),
        "welcomepickups": ("https://www.welcomepickups.com/istanbul/airport-transfer/", "campaign_id=627", "p=8919"),
        "kiwitaxi": ("https://kiwitaxi.com/en/turkey", "campaign_id=1", "p=647"),
        "gettransfer": ("https://gettransfer.com/tr", "campaign_id=147", "p=4439"),
        "localrent": ("https://www.localrent.com/tr/turkey/", "campaign_id=87", "p=2043"),
        "economybookings": ("https://www.economybookings.com/tr", "campaign_id=10", "p=2018"),
        "tiqets": ("https://www.tiqets.com/en/", "campaign_id=89", "p=2074"),
        "yesim": ("https://yesim.app/", "campaign_id=224", "p=5998"),
        "airhelp": ("https://www.airhelp.com/", "campaign_id=120", "p=9139"),
        "klook": ("https://www.klook.com/", "campaign_id=137", "p=4110"),
        "airalo": ("https://www.airalo.com/", "campaign_id=541", "p=8310"),
        "drimsim": ("https://w1.drimsim.com/", "campaign_id=102", "p=2762"),
        "getrentacar": ("https://getrentacar.com/", "campaign_id=222", "p=5996"),
        "gocity": ("https://gocity.com/", "campaign_id=62", "p=1942"),
        "bikesbooking": ("https://bikesbooking.com/", "campaign_id=57", "p=1767"),
        "qeeq": ("https://www.qeeq.com/", "campaign_id=172", "p=4845"),
        "wegotrip": ("https://wegotrip.com/", "campaign_id=150", "p=4487"),
        "autoeurope": ("https://www.autoeurope.eu/", "campaign_id=143", "p=4354"),
        "radicalstorage": ("https://radicalstorage.com/", "campaign_id=209", "p=5867"),
        "intui": ("https://en.intui.travel/", "campaign_id=22", "p=657"),
        "compensair": ("https://www.compensair.com/", "campaign_id=86", "p=4129"),
        "saily": ("https://saily.com/", "campaign_id=629", "p=8979"),
        "kkday": ("https://www.kkday.com/", "campaign_id=633", "p=9074"),
    }
    for key, (raw_u, cid, pid) in expected_tp.items():
        wrapped = RevenueService.enrich_deep_link(key, raw_u, "travel")
        assert "tp.media/r?" in wrapped, f"{key} failed tp.media/r wrap"
        assert cid in wrapped and pid in wrapped and "marker=789884" in wrapped and "trs=585474" in wrapped

    # 3. GigSky Ready-Made Click Link (campaign_id=636, promo_id=9150)
    gigsky_url = RevenueService.enrich_deep_link("gigsky", "https://www.gigsky.com/", "esim")
    assert "tp.media/click?shmarker=789884&promo_id=9150" in gigsky_url
    assert "campaign_id=636&trs=585474" in gigsky_url


def test_search_warm_cache_hit_and_deep_links():
    _SEARCH_WARM_CACHE.clear()
    _RATE_LIMIT_BUCKETS.clear()
    payload = {
        "origin": "İstanbul",
        "destination": "Ankara",
        "departure_date": "2026-11-20",
        "passengers": 1,
        "adults": 1,
        "transport_type": "train",
        "trip_type": "one_way",
        "currency": "TRY",
        "website_url": ""
    }
    res1 = client.post("/api/search", json=payload, headers=BROWSER_HEADERS)
    assert res1.status_code == 200
    assert res1.headers.get("X-Hakiki-Cache") == "MISS"
    data1 = res1.json()
    assert len(data1.get("tickets", [])) > 0
    assert data1.get("cache_hit") is False

    # İkinci özdeş istek 5 dakikalık Warm Cache'ten anında dönmeli (#18 VP Engineering & #21 SRE)
    res2 = client.post("/api/search", json=payload, headers=BROWSER_HEADERS)
    assert res2.status_code == 200
    assert res2.headers.get("X-Hakiki-Cache") == "HIT"
    data2 = res2.json()
    assert data2.get("cache_hit") is True
    assert len(data2.get("tickets", [])) == len(data1.get("tickets", []))


def test_multi_modal_deep_links_validity():
    _RATE_LIMIT_BUCKETS.clear()
    for mode, orig, dest in [
        ("bus", "İstanbul", "İzmir"),
        ("ferry", "Çeşme", "Sakız Adası"),
    ]:
        res = client.post(
            "/api/search",
            json={
                "origin": orig,
                "destination": dest,
                "departure_date": "2026-11-22",
                "passengers": 1,
                "adults": 1,
                "transport_type": mode,
                "trip_type": "one_way",
                "currency": "TRY",
                "website_url": ""
            },
            headers=BROWSER_HEADERS,
        )
        assert res.status_code == 200
        body = res.json()
        tickets = body.get("tickets") or []
        assert len(tickets) > 0
        first_url = tickets[0].get("winner_url") or tickets[0].get("direct_link") or tickets[0].get("official_link") or ""
        assert first_url.startswith("https://")


def test_cybersecurity_honeypot_blocks_bots_gracefully():
    _RATE_LIMIT_BUCKETS.clear()
    res = client.post(
        "/api/search",
        json={
            "origin": "İstanbul",
            "destination": "Antalya",
            "departure_date": "2026-11-25",
            "passengers": 1,
            "transport_type": "flight",
            "website_url": "http://spam-bot.example.com"
        },
        headers=BROWSER_HEADERS,
    )
    assert res.status_code == 429
    body = res.json()
    assert body.get("rate_limited") is True
    assert body.get("blocked_bot") is True
    assert "deep_links" in body


def test_render_keep_alive_health_endpoint_and_scheduler_job():
    res = client.get("/api/health", headers=BROWSER_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "ok"

    from app.services.scheduler_service import scheduled_render_keep_alive_ping
    assert callable(scheduled_render_keep_alive_ping)
