# 🏛️ HAKİKİ BİLET — MASTER REFERANS DÖKÜMANI (PRD & PLATFORM ANAYASASI)

> **Sürüm:** 2.0  
> **Tarih:** 18 Ekim 2026  
> **Alan Adı:** https://hakikibilet.com  
> **Slogan:** *Hakiki Fiyat, Hakiki Bilet*  
> **Repo:** `github.com/turkersezer/hakikibilet` (`main` dalı, Render otomatik dağıtım)
>
> **Bu dökümanın amacı:** Projeye dahil olan tüm yapay zekalar (Claude, Gemini, GPT vb.) ve geliştiriciler için tek referans kaynağıdır. Yeni bir oturuma başlarken önce bu dosya okunmalıdır.
>
> **Okuma kuralı:** Her bölüm iki şeyi ayırır: ✅ **MEVCUT** (kodda çalışıyor) ve 🎯 **HEDEF** (henüz yapılmadı). Hedefleri mevcutmuş gibi anlatmayın ve kullanıcıya öyle sunmayın.

---

## 1. AMAÇ VE VİZYON

**Hedef:** Kullanıcı bir bilet almak istediğinde aklına gelen ilk site olmak.

Kapsam, bilet gerektiren her şeydir:

| Dikey | Örnekler |
|---|---|
| Ulaşım | Uçak, otobüs, tren (TCDD), feribot (Ege adaları, Marmara) |
| Konaklama | Otel, butik otel, resort |
| Etkinlik | Konser, tiyatro, sinema, müzikal, festival |
| Spor | Formula 1, UEFA finalleri, Wimbledon vb. |
| Gemi turu | Kruvaziyer, Yunan adaları ve Akdeniz turları |

**Çalışma biçimi:** Hakiki Bilet bir **Metasearch (fiyat arama ve karşılaştırma) motorudur**. Kendisi bilet satmaz, ödeme almaz. Kullanıcının seçtiği **tam sefere, etkinliğe veya otele** yönlendirir ve bu yönlendirmeden **komisyon** kazanır.

**Kullanıcıyı harekete geçiren öneriler:** Sitenin yalnızca arama kutusu olmaması hedeflenir. Örnekler: *"Bu hafta sonu için Sakız Adası kaçamağı"*, *"Cadılar Bayramı yaklaşıyor"*, *"Harbiye sezonu açıldı"*.

---

## 2. DEĞİŞMEZ KURALLAR (ANAYASA)

### 2.1 Şeffaflık
1. **Sahte indirim yok.** Bir sitede göstereceğimiz rakam, kullanıcı oraya gittiğinde de aynı olmalıdır.
2. **Doğrulanmamış fiyat yazılmaz.** Bir sağlayıcının canlı fiyatını çekemiyorsak karta rakam koymayız. Bunun yerine *"Canlı Fiyatı Gör ↗"* gibi etiket kullanırız.
3. **Her kart, kendi sitesindeki gerçek en düşük tutarı göstermelidir.** Bir kartta, o sitede bulunmayan bir rakam görünmez.
4. Yalnızca resmi organizatör veya federasyon tarafından teyit edilmiş etkinlikler listelenir. Kulaktan dolma tarih yazılmaz.

### 2.2 Ticari öncelik
1. Projenin amacı yönlendirmeden gelir elde etmektir.
2. **Komisyon getiren ortaklar birinci plandadır:** ana buton, en belirgin yer, varsayılan seçenek.
3. **Komisyon getirmeyen yerlere yönlendirme ikinci plandadır.** Güven için gösterilebilir ama ana CTA olamaz.
4. İstisna: TCDD. Komisyon yok ve derin link teknik olarak mümkün değil. Kullanıcıya yararlı olduğu için resmi bilet sayfasına yönlendirilir.

### 2.3 Derin link
1. Kullanıcı firmanın ana sayfasına bırakılmaz. Hedef, **seçilen sefer/etkinlik/otel için arama sonucu veya ödeme adımı** olmalıdır (tarih, yolcu sayısı ve kalkış-varış dolu).
2. Her linkte ortaklık takip kodu bulunmalıdır. Kodsuz link = gelir kaybı.
3. TCDD dışında tüm kanallarda derin link hedeflenir. Kanal bazında gerçek durum için Bölüm 5'e bakın.

### 2.4 Hukuk
- Sitede bilet satışı, kart bilgisi veya ödeme tahsilatı yoktur. Bu durum, TÜRSAB/metasearch pozisyonumuzun dayanağıdır.
- "Partner", "resmi ortak" gibi ifadeler yalnızca sözleşme onaylanıp doğrulanmış olan firmalar için kullanılır. Onaysız firma için nötr ifade (örn. "karşılaştırılan sağlayıcı") kullanılır.
- Kullanıcıya gösterilen yasal metinler: `/yasal-uyari`, `/kullanim-kosullari`, `/kvkk`, `/cerez-politikasi`, `/etkinlik-kurallari`, `/iletisim`.

### 2.5 Dil
Her yeni kullanıcı metni **TR ve EN** karşılığıyla birlikte eklenir (Bölüm 6).

---

## 3. GELİR ORTAKLIKLARI (AFFILIATE) — GÜNCEL DURUM

| Ortak | Durum | Takip kodu | Notlar |
|---|---|---|---|
| **Trip.com** | ✅ **Onaylı** (18 Ekim 2026) | `Allianceid=11051531`, `SID=333747492` | Komisyon "%7'ye kadar", rezervasyon sayısına göre değişir. Uçuş linklerinde aktif. Otel/diğer ürün linkleri için ayrıca üretilmeli. Panel: trip.com/partners |
| **Travelpayouts / Aviasales** | ✅ Aktif | `marker=585474` | Uçuş (Aviasales) linkleri |
| **Booking.com** | ⚠️ Kod tanımlı, durumu doğrulanmalı | `AFFILIATE_BOOKING_AID=585474` | Aynı sayı Travelpayouts marker ile aynı; doğru AID olup olmadığı kontrol edilmeli |
| **Enuygun** | ⚠️ SubID tanımlı, onaylı program olup olmadığı doğrulanmalı | `hakikibilet` | Gerçek ortaklık sözleşmesi varsa takip parametresi formatı teyit edilmeli |
| **Obilet** | ⚠️ Aynı durum | `hakikibilet` | Otobüs; link formatı `BusService.get_obilet_deep_link` |
| **Turna.com** | ❓ Ortaklık yok/bilinmiyor | — | Linkte takip kodu yok → şu an komisyon getirmiyor olabilir |
| **Bubilet / Biletix / Passo** | 🎯 Başvuru yapılmadı | — | Etkinlik biletleri için hedef |
| **TCDD** | Komisyon yok | — | Sadece resmi yönlendirme |
| **Kruvaziyer (Celestyal, MSC, Costa vb.)** | 🎯 Başlanmadı | — | Hedef dikey |

> **Görev notu:** Yukarıdaki ⚠️ ve ❓ satırları için, takip parametresinin ilgili firmanın programında gerçekten komisyon yazdığı doğrulanmadan "komisyon alıyoruz" denmemelidir.

---

## 4. TEKNİK MİMARİ

### 4.1 Teknoloji
- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **Arayüz:** Jinja2 (`app/templates/index_v2.html`), Tailwind CSS, Vanilla JS (`app/static/js/app_v2.js`), FontAwesome
- **Uçuş verisi:** `fast_flights` + Google Flights verisi (`app/services/live_flights.py`)
- **Otel verisi:** RapidAPI Booking.com + 2 saatlik bellek önbelleği (`app/services/hotel_service.py`)
- **Veritabanı:** SQLite (`data/ucuz_bilet.db`)
- **E-posta:** Resend (`app/services/notification_service.py`)
- **Barındırma:** Render (`render.yaml`, `Procfile`) + Cloudflare

### 4.2 Dosya haritası
| Dosya | Rol |
|---|---|
| `app/main.py` | Rotalar: sayfalar, `/api/search`, `/api/erken-kayit`, admin uçları |
| `app/config.py` | Ayarlar ve affiliate kodları (ortam değişkeni → varsayılan) |
| `app/models.py` | Pydantic istek modelleri (`SearchRequest` vb.) |
| `app/cities.py` | Şehir/havalimanı/istasyon listesi, IATA kodları |
| `app/services/search_service.py` | Arama orkestrasyonu, link üretimi, **küratörlü etkinlik listesi** (`get_curated_events`) |
| `app/services/live_flights.py` | Canlı uçuş çekme ve sağlayıcı butonları |
| `app/services/hotel_service.py` | Otel arama |
| `app/services/train_service.py`, `ferry_service.py`, `car_rental_service.py` | Tren, feribot, araç |
| `app/services/campaign_service.py` | Radar fırsatları ve duyurular |
| `app/services/tracker_service.py`, `scheduler_service.py` | Fiyat alarmı |
| `app/templates/legal.html` | Yasal sayfalar |
| `HAKIKI_BILET_MASTER_REFERENCE.md` | Bu dosya |

### 4.3 Çalıştırma ve dağıtım
- Yerel: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8145`
- Canlı: `git push origin main` → Render otomatik dağıtır (birkaç dakika).
- Script önbelleği: `index_v2.html` içindeki `app_v2.js?v=...` sürümü, JS değiştiğinde artırılmalıdır.
- Bakım modu: `MAINTENANCE_MODE=false` kalmalıdır.

### 4.4 Bilinen teknik riskler
1. **SQLite ve Render:** Render'ın ücretsiz planında disk kalıcı değildir. Her dağıtımda veya yeniden başlatmada bülten kayıtları, fiyat alarmları silinebilir. Kalıcı bir veritabanına geçiş değerlendirilmelidir.
2. **Gizli bilgi:** `config.py` içinde bir RapidAPI anahtarı varsayılan değer olarak yazılıdır ve repoya commit'lidir. Anahtar yenilenip yalnızca ortam değişkeninde tutulmalıdır. `.env` repoda değildir (iyi).
3. **Google Flights verisine bağımlılık:** Resmi API değil. Biçim değişirse bozulabilir.
4. **Tahmini fiyat riski:** `search_service.py` içinde bazı yerlerde "benchmark" (referans) fiyat üreten kod vardır (örn. `get_flight_benchmark_price`). Bu, Bölüm 2.1 ile çelişebilir; kullanıcıya gerçek diye gösterilen bir tahmin olup olmadığı denetlenmelidir.
5. **Eski dosyalar:** `index.html`, `app.js`, `backups/`, çok sayıda `scratch_*.py` ve logo deneme dosyaları repoda/klasörde durur; temizlik gerekir.

---

## 5. KANAL BAZINDA GERÇEK DURUM (DERİN LİNK VE FİYAT)

> Bu tablo koddan çıkarılmış tespittir. Hedef, "seçilen tam sefere" yönlendirmektir. Şu an çoğu kanal **aranan rota ve tarih için arama sonuç sayfasına** gider, belirli bir seferi önceden seçmez.

| Kanal | Mevcut link | Fiyat kaynağı | Hedef |
|---|---|---|---|
| Uçak – Trip.com | Rota+tarih+yolcu arama sayfası, takip kodlu | Canlı değil (fiyat gösterilmez) | Seçilen uçuş sayfasına, canlı fiyatla |
| Uçak – Aviasales | Rota+tarih arama linki, marker'lı | — | Aynı |
| Uçak – Enuygun | Rota+tarih+yolcu arama sayfası (havayolu filtresi ile) | — | Takip parametresi teyidi, sefer seçili |
| Uçak – Turna | Rota+tarih arama | — | Ortaklık yoksa ikincil plana |
| Uçak – Google Flights verisi | Gerçek sefer, saat, kodu, fiyat | ✅ Canlı | Mevcut kaynak |
| Otel | Booking arama sayfası | RapidAPI canlı | Otel sayfasına derin link |
| Otobüs | Obilet rota+tarih sayfası | Doğrulanmalı | Sefer seçili |
| Tren (TCDD) | `ebilet.tcddtasimacilik.gov.tr` ana adresi | Doğrulanmalı | İstisna: yalnızca resmi sayfa |
| Feribot | `ferry_service.py` | Doğrulanmalı | Tarih+rota derin link |
| Etkinlik | Küratörlü liste: resmi bilet gişesi adresi | Elle girilmiş aralık/örnek | Bubilet/Biletix/Passo ortaklığı ve etkinlik sayfası |

Bir kartta kullanıcıya gösterilen fiyat yalnızca **canlı doğrulanmış** ise rakam olarak yazılır (Madde 2.1).

---

## 6. TR / EN DİL MOTORU (✅ MEVCUT)

- Sağ üstteki `TR | EN` butonu, sayfa yenilenmeden tüm arayüzü değiştirir. Varsayılan dil **Türkçe**; seçim `localStorage["hakiki_lang"]` içinde saklanır.
- Çeviri sözlüğü: `index_v2.html` içinde `window.APP_TRANSLATIONS = { tr: {...}, en: {...} }`.
- Statik metinler `data-i18n="anahtar"` ile, placeholder'lar `data-i18n-ph` ile bağlanır.
- Sunucudan gelen etkinlik kartları: `search_service.py` içinde `title_en`, `desc_en`, `dates_en`, `city_en`, `country_en`, `badge_en`, `urgency_badge_en`, `urgency_desc_en` alanlarıyla; kart HTML'inde `data-*-tr` / `data-*-en` özellikleriyle.
- Yeni bir metin eklendiğinde: sözlüğe iki dilde anahtar eklenir, HTML'e `data-i18n` konur. Etkinlik eklenirse `_en` alanları da doldurulur.

---

## 7. ETKİNLİK SİSTEMİ

### ✅ Mevcut
- `SearchService.get_curated_events()` içinde **elle yazılmış** etkinlik listesi (Sakız kaçamağı, Harbiye/Zorlu, Aspendos, F1 Monako/Silverstone/Monza/Bakü, UEFA finali, Wimbledon).
- Geçmiş tarihli etkinlikler otomatik gizlenir.
- Kalan güne göre aciliyet rozeti hesaplanır (≤15 gün kritik, ≤30 gün uyarı, sonrası erken rezervasyon).
- Takvimi olmayan "kaçamak" rotası (`is_escape`) en yakın Cuma-Pazar tarihiyle çalışır.
- Radar bülteni formu: e-posta toplar (`/api/erken-kayit`).

### 🎯 Hedef
- **Yeni etkinlik, festival ve organizasyonların otomatik eklenmesi.** Şu an böyle bir tarayıcı veya veri akışı yoktur; her etkinlik elle koda eklenir.
- Gereken: bir veri kaynağı (resmi takvim, bilet platformu ortaklık beslemesi veya API), düzenli çalışan bir görev, tekrarlayan kayıtları ayıklama, `_en` alanlarının otomatik üretimi, kaynağı doğrulanamayan kaydın yayınlanmaması.
- Bu iş büyük olasılıkla etkinlik verisini **ortaklık programı üzerinden** (Bubilet/Biletix/Passo gibi) almayı gerektirir. Önce ortaklık, sonra otomasyon.

---

## 8. ÖNERİ VE TETİKLEYİCİ MOTORU

- ✅ Etkinlik kartları ve aciliyet rozetleri.
- ✅ Hafta sonu kaçamağı kartı.
- 🎯 Takvim tabanlı kampanyalar (Cadılar Bayramı, yılbaşı, bayramlar, uzun hafta sonları).
- 🎯 Kullanıcıya özel hatırlatma (fiyat alarmı e-postası, bülten).
- Tüm önerilerde "Hakiki Bilet kendi fiyatını yazmaz" ilkesi geçerlidir.

---

## 9. YOL HARİTASI (ÖNCELİK SIRASIYLA ÖNERİ)

Aşağıdaki sıra bir **öneridir**; kullanıcı onayı olmadan başlanmaz.

1. **Gelir doğrulaması:** Trip.com linklerinin canlıda takip kodu taşıdığını ve panelde tıklamanın göründüğünü teyit et. Diğer ortakların (Enuygun, Obilet, Booking, Turna) komisyon gerçekten yazıyor mu denetle.
2. **Fiyat dürüstlüğü denetimi:** Benchmark/tahmin fiyat üreten kod yollarını bul; kullanıcıya gerçek gibi gösterilenleri kaldır veya etiketle.
3. **Derin link iyileştirme:** Kanal bazında "arama sayfası" yerine "seçilen sefer/otel" sayfasına gitmenin mümkün olduğu yerleri belirle (Bölüm 5).
4. **Kalıcı veritabanı:** SQLite'ı Render üzerinde kalıcı bir çözüme taşı.
5. **Ortaklık başvuruları:** Bubilet, Biletix, Passo, kruvaziyer firmaları, Booking/Enuygun/Obilet resmi programları.
6. **Etkinlik otomasyonu:** 5. maddeden sonra, ortaklık verisi üzerinden.
7. **Yeni dikeyler:** Kruvaziyer sekmesi, sinema/tiyatro.
8. **Temizlik:** Eski şablon, scratch dosyaları, yedek klasörleri, gizli anahtarlar.

---

## 10. YAPAY ZEKALAR İÇİN ÇALIŞMA KURALLARI

1. İşe başlamadan bu dosyayı oku. Bölüm 2 (Anayasa) ve Bölüm 5 (gerçek durum) bağlayıcıdır.
2. Kullanıcı "işlem yapma" derse yalnızca anlat. Onay almadan kod değiştirme, commit veya push yapma.
3. Her değişiklikte komisyon kodunu koru. Link üretimini değiştirirsen takip parametresini taşıdığını test et.
4. Fiyat gösterirken Bölüm 2.1'e uy. Emin değilsen rakam yazma.
5. Yeni metin = TR + EN.
6. JS değişirse `app_v2.js?v=` sürümünü artır.
7. Canlıya almak: `git push origin main`. Windows PowerShell'de komutları `&&` ile birleştirme, ayrı çalıştır.
8. Sunucu eski kodla çalışıyorsa değişiklikler görünmez: eski uvicorn sürecini kapatıp yeniden başlat.
9. Gizli anahtarları (`.env`, API anahtarları) sohbete veya repoya yazma.
10. Bu dosyayı, büyük bir karar veya durum değişikliğinden sonra güncel tut (özellikle Bölüm 3 ve Bölüm 5).

---

*Son güncelleme notu: v2.0, v1.0'dan farklı olarak mevcut durumu ve hedefi ayırır; bazı iddiaları (otomatik etkinlik tarayıcı, her kanalda seçili sefere derin link) hedef olarak işaretler.*
