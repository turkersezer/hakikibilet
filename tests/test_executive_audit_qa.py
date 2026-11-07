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
    assert "app_v3.js?v=20261107_v51" in html


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
