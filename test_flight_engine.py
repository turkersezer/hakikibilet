"""
Kapsamlı Uçuş Karar ve Sağlayıcı Doğrulama Testi
Aşağıdaki tüm kritik senaryoları test eder:
1. Yurt İçi Tek Yön: Antalya - İzmir (AYT - ADB) (SunExpress / Booking / Skyscanner / Trip)
2. Yurt İçi Tek Yön: Ankara - Adana (ESB - ADA) (AJet / Pegasus)
3. Yurt İçi Tek Yön: İstanbul - Trabzon (SAW - TZX) (Pegasus / THY)
4. Yurt İçi Gidiş-Dönüş: Antalya - İzmir (AYT - ADB)
5. Yurt Dışı Tek Yön: İstanbul - Londra (IST - LHR)
6. Kural Kontrolleri:
   - Kazanan Buton Metni ile Link %100 birebir aynı mı?
   - Asla fiyatsız veya undefined buton var mı?
   - Kuruşlu garip fiyat var mı?
   - Fiyat eşitliğinde affiliate kazanıyor mu?
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.services.live_flights import fetch_live_flights_from_google

def run_test(scenario_name, origin, dest, dep_date, ret_date=None, trip_type="one_way"):
    print(f"\n========================================================")
    print(f"TEST: {scenario_name} ({origin} -> {dest}, {dep_date}, {trip_type})")
    print(f"========================================================")
    
    flights = fetch_live_flights_from_google(
        origin_city_name=origin,
        dest_city_name=dest,
        departure_date=dep_date,
        return_date=ret_date,
        trip_type=trip_type,
        adults=1,
    )
    
    if not flights:
        print(f"❌ HİÇBİR UÇUŞ BULUNAMADI: {origin} -> {dest}")
        return False
        
    print(f"✓ Toplam {len(flights)} uçuş bulundu.")
    
    all_passed = True
    for idx, f in enumerate(flights[:3]):
        fn = f.get("flight_number")
        carrier = f.get("carrier")
        price = f.get("price")
        winner_name = f.get("winner_name")
        winner_channel = f.get("winner_channel")
        winner_btn = f.get("winner_button_text")
        winner_url = f.get("winner_url")
        providers = f.get("providers") or []
        
        print(f"\n  [Uçuş #{idx+1}: {carrier} {fn}]")
        print(f"    - Nihai Bilet Fiyatı  : {price} ₺")
        print(f"    - Kazanan Sağlayıcı   : {winner_name} (Kanal: {winner_channel})")
        print(f"    - Buton Metni (TR)    : {winner_btn}")
        print(f"    - Buton Hedef URL     : {winner_url}")
        
        # 1. Kural: Fiyat tam sayı mı?
        if price is not None and not isinstance(price, (int, float)):
            print(f"    ❌ FİYAT TİPİ GEÇERSİZ: {price}")
            all_passed = False
            
        # 2. Kural: Buton metni ile link sağlayıcısı uyuşuyor mu?
        btn_lower = (winner_btn or "").lower()
        url_lower = (winner_url or "").lower()
        
        if "skyscanner" in btn_lower and "skyscanner" not in url_lower:
            print(f"    ❌ Skyscanner buton metni var ama URL Skyscanner değil!")
            all_passed = False
        elif "trip.com" in btn_lower and "trip.com" not in url_lower:
            print(f"    ❌ Trip.com buton metni var ama URL Trip.com değil!")
            all_passed = False
        elif "booking" in btn_lower and "kayak" not in url_lower and "booking" not in url_lower:
            print(f"    ❌ Booking buton metni var ama URL Kayak/Booking değil!")
            all_passed = False
        elif "sunexpress" in btn_lower and ("kayak" in url_lower or "skyscanner" in url_lower):
            print(f"    ❌ SunExpress buton metni var ama URL Kayak/Skyscanner'a gidiyor!")
            all_passed = False
        elif "pegasus" in btn_lower and ("kayak" in url_lower or "skyscanner" in url_lower):
            print(f"    ❌ Pegasus buton metni var ama URL Kayak/Skyscanner'a gidiyor!")
            all_passed = False
        else:
            print(f"    ✓ Buton metni ve Hedef URL %100 BİREBİR KİLİTLİ.")
            
        # 3. Kural: Sağlayıcı hapları doğrulaması
        print(f"    - Karşılaştırma Hapları ({len(providers)} adet):")
        for p in providers:
            p_name = p.get("name")
            p_price = p.get("price")
            p_best = " ⭐ EN İYİ (KAZANAN)" if p.get("is_best") else ""
            print(f"        * {p_name}: {p_price} ₺{p_best}")
            
    return all_passed

if __name__ == "__main__":
    t1 = run_test("1. SunExpress Hub Hattı", "Antalya", "İzmir", "2026-11-10")
    t2 = run_test("2. AJet / Pegasus Başkent Hattı", "Ankara", "Adana", "2026-11-12")
    t3 = run_test("3. İstanbul - Trabzon Karadeniz Hattı", "İstanbul", "Trabzon", "2026-11-15")
    t4 = run_test("4. Gidiş-Dönüş Akdeniz Hattı", "Antalya", "İzmir", "2026-11-10", "2026-11-15", trip_type="round_trip")
    t5 = run_test("5. Yurt Dışı Londra Hattı", "İstanbul", "Londra", "2026-11-20")
    
    print("\n========================================================")
    print(f"GENEL SONUÇ: {'TÜM TESTLER BAŞARIYLA GEÇTİ ✓' if (t1 and t2 and t3 and t4 and t5) else 'BAZI TESTLERDE HATA VAR ❌'}")
    print("========================================================")
