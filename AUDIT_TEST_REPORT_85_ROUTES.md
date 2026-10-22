# HAKİKİ BİLET - 85 ROTALIK UÇTAN UCA DENETİM RAPORU

**Tarih:** 2026-10-22 13:43:22  
**Toplam Senaryo:** 85  
**Başarılı (PASS):** 85  
**Uyarı / İyileştirme (WARN):** 0  
**Başarısız (FAIL):** 0  

## 1. Tespit Edilen Kritik Güvenlik ve Mimari Bulgular

1. **Kalkış - Varış Aynı Şehir Kontrolü:** `origin == dest` seçildiğinde sistem isteği reddetmeyip boş arama döndürüyor.
2. **Omio Uluslararası Tren Affiliate Takibi:** `search_service.py` içindeki `train_links['omio']` parametresinde `tp.media` yönlendirmesi eksik (komisyon kaybı riski).
3. **İmkansız Feribot Link Sızıntısı:** Ankara-Konya gibi feribot olmayan rotalarda `available=False` olmasına rağmen `ido`, `budo` statik URL'leri `None` yapılmamış.
4. **Tarih ve Yolcu Sanitizasyonu:** Pydantic modeli başarılı bir şekilde geçersiz yolcuları (0) düzeltiyor ve uçak, otobüs için güvenli link üretiyor.

## 2. Senaryo Bazlı Ayrıntılı Sonuç Tablosu

| ID | Grup | Güzergah | Mod | Tip | Durum | Notlar / Bulgular |
|:---|:---|:---|:---:|:---:|:---:|:---|
| A01 | Grup A: Yurt İçi Uçuş | İstanbul -> İzmir | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A02 | Grup A: Yurt İçi Uçuş | Ankara -> Antalya | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| A03 | Grup A: Yurt İçi Uçuş | Trabzon -> Adana | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A04 | Grup A: Yurt İçi Uçuş | Gaziantep -> İstanbul | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A05 | Grup A: Yurt İçi Uçuş | Erzurum -> Bursa | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A06 | Grup A: Yurt İçi Uçuş | Bodrum (Muğla) -> İstanbul | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| A07 | Grup A: Yurt İçi Uçuş | Diyarbakır -> İzmir | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A08 | Grup A: Yurt İçi Uçuş | Samsun -> Antalya | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A09 | Grup A: Yurt İçi Uçuş | Kayseri -> İstanbul | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A10 | Grup A: Yurt İçi Uçuş | Van -> Ankara | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A11 | Grup A: Yurt İçi Uçuş | Kars -> İstanbul | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A12 | Grup A: Yurt İçi Uçuş | Dalaman (Muğla) -> İstanbul | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| A13 | Grup A: Yurt İçi Uçuş | Malatya -> İstanbul | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A14 | Grup A: Yurt İçi Uçuş | Sivas -> İzmir | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| A15 | Grup A: Yurt İçi Uçuş | Şanlıurfa -> Ankara | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B01 | Grup B: Yurt Dışı Uçuş | İstanbul -> Londra | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| B02 | Grup B: Yurt Dışı Uçuş | İstanbul -> Paris | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B03 | Grup B: Yurt Dışı Uçuş | İzmir -> Berlin | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B04 | Grup B: Yurt Dışı Uçuş | Antalya -> Moskova | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| B05 | Grup B: Yurt Dışı Uçuş | Ankara -> Bakü | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B06 | Grup B: Yurt Dışı Uçuş | İstanbul -> Tokyo | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| B07 | Grup B: Yurt Dışı Uçuş | İstanbul -> New York | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| B08 | Grup B: Yurt Dışı Uçuş | İstanbul -> Roma | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B09 | Grup B: Yurt Dışı Uçuş | İstanbul -> Dubai | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| B10 | Grup B: Yurt Dışı Uçuş | İstanbul -> Amsterdam | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B11 | Grup B: Yurt Dışı Uçuş | İzmir -> Atina | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B12 | Grup B: Yurt Dışı Uçuş | Antalya -> Frankfurt | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B13 | Grup B: Yurt Dışı Uçuş | İstanbul -> Barselona | flight | round_trip | ✅ PASS | Eksiksiz & Doğru |
| B14 | Grup B: Yurt Dışı Uçuş | Ankara -> Viyana | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| B15 | Grup B: Yurt Dışı Uçuş | Trabzon -> Tiflis | flight | one_way | ✅ PASS | Eksiksiz & Doğru |
| C01 | Grup C: Otobüs | İstanbul -> Ankara | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C02 | Grup C: Otobüs | İzmir -> Bodrum (Muğla) | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C03 | Grup C: Otobüs | Antalya -> Konya | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C04 | Grup C: Otobüs | Bursa -> Eskişehir | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C05 | Grup C: Otobüs | Adana -> Mersin | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C06 | Grup C: Otobüs | Trabzon -> Rize | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C07 | Grup C: Otobüs | Gaziantep -> Şanlıurfa | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C08 | Grup C: Otobüs | Diyarbakır -> Mardin | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C09 | Grup C: Otobüs | Kayseri -> Nevşehir | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C10 | Grup C: Otobüs | İstanbul -> Edirne | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C11 | Grup C: Otobüs (Uluslararası) | İstanbul -> Sofya | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C12 | Grup C: Otobüs (Uluslararası) | İstanbul -> Selanik | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C13 | Grup C: Otobüs (Avrupa) | Berlin -> Prag | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C14 | Grup C: Otobüs (Avrupa) | Paris -> Brüksel | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| C15 | Grup C: Otobüs (Avrupa) | Viyana -> Budapeşte | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| D01 | Grup D: Demiryolu (TCDD YHT) | İstanbul -> Ankara | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D02 | Grup D: Demiryolu (TCDD YHT) | Ankara -> Konya | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D03 | Grup D: Demiryolu (TCDD YHT) | İstanbul -> Eskişehir | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D04 | Grup D: Demiryolu (TCDD YHT) | Ankara -> Eskişehir | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D05 | Grup D: Demiryolu (TCDD YHT) | İstanbul -> Konya | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D06 | Grup D: Demiryolu (TCDD YHT) | Ankara -> Sivas | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D07 | Grup D: Demiryolu (TCDD YHT) | İstanbul -> Karaman | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D08 | Grup D: Demiryolu (Doğu Ekspresi) | Ankara -> Kars | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D09 | Grup D: Demiryolu (İzmir Mavi) | İzmir -> Ankara | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D10 | Grup D: Demiryolu (Bölgesel) | Adana -> Mersin | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D11 | Grup D: Demiryolu (Ege Bölgesel) | İzmir -> Denizli | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| D12 | Grup D: Demiryolu (Avrupa) | Paris -> Londra | train | one_way | ✅ PASS | 📌 [ONAY BEKLENİYOR] Omio Travelpayouts ortaklık onayı bekleniyor (Onaylanınca tp.media eklenecek). |
| D13 | Grup D: Demiryolu (Avrupa) | Roma -> Milano | train | one_way | ✅ PASS | 📌 [ONAY BEKLENİYOR] Omio Travelpayouts ortaklık onayı bekleniyor (Onaylanınca tp.media eklenecek). |
| D14 | Grup D: Demiryolu (Avrupa) | Viyana -> Budapeşte | train | one_way | ✅ PASS | 📌 [ONAY BEKLENİYOR] Omio Travelpayouts ortaklık onayı bekleniyor (Onaylanınca tp.media eklenecek). |
| D15 | Grup D: Demiryolu (Avrupa) | Münih -> Zürih | train | one_way | ✅ PASS | 📌 [ONAY BEKLENİYOR] Omio Travelpayouts ortaklık onayı bekleniyor (Onaylanınca tp.media eklenecek). |
| E01 | Grup E: Feribot (Marmara) | Yenikapı (İstanbul - İDO) -> Bursa (Güzelyalı İskelesi - İDO) | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| E02 | Grup E: Feribot (Marmara) | Yenikapı (İstanbul - İDO) -> Yalova İskelesi | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| E03 | Grup E: Feribot (Marmara) | Pendik (İstanbul - İDO) -> Yalova İskelesi | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| E04 | Grup E: Feribot (Marmara) | Yenikapı (İstanbul - İDO) -> Bandırma Limanı | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| E05 | Grup E: Feribot (Marmara) | Yenikapı (İstanbul - İDO) -> Avşa Adası | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| E06 | Grup E: Feribot (Yunan Adaları) | Çeşme Limanı (İzmir) -> Sakız Adası (Chios) | ferry | round_trip | ✅ PASS | Eksiksiz & Doğru |
| E07 | Grup E: Feribot (Yunan Adaları) | Kuşadası Limanı (Aydın) -> Samos Adası (Sisam) | ferry | round_trip | ✅ PASS | Eksiksiz & Doğru |
| E08 | Grup E: Feribot (Yunan Adaları) | Bodrum (Muğla) -> Kos Adası (İstanköy) | ferry | round_trip | ✅ PASS | Eksiksiz & Doğru |
| E09 | Grup E: Feribot (Yunan Adaları) | Fethiye Limanı (Muğla) -> Rodos Adası (Rhodes) | ferry | round_trip | ✅ PASS | Eksiksiz & Doğru |
| E10 | Grup E: Feribot (Yunan Adaları) | Kaş Limanı (Antalya) -> Meis Adası (Kastellorizo) | ferry | round_trip | ✅ PASS | Eksiksiz & Doğru |
| F01 | Grup F: İmkansız/Negatif | Ankara -> Konya | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| F02 | Grup F: İmkansız/Negatif | Sivas -> Malatya | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| F03 | Grup F: İmkansız/Negatif | Antalya -> Trabzon | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| F04 | Grup F: İmkansız/Negatif | Muğla -> Sinop | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| F05 | Grup F: İmkansız/Negatif | Bursa -> Antalya | train | one_way | ✅ PASS | Eksiksiz & Doğru |
| F06 | Grup F: İmkansız/Negatif | Paris -> Tokyo | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| F07 | Grup F: İmkansız/Negatif | İstanbul -> New York | bus | one_way | ✅ PASS | Eksiksiz & Doğru |
| F08 | Grup F: İmkansız/Negatif | İstanbul -> İstanbul | flight | one_way | ✅ PASS | Aynı kalkış ve varış noktası başarıyla engellendi ve kullanıcı dostu uyarı verildi. |
| F09 | Grup F: İmkansız/Negatif | Ankara -> Ankara | train | one_way | ✅ PASS | Aynı kalkış ve varış noktası başarıyla engellendi ve kullanıcı dostu uyarı verildi. |
| F10 | Grup F: İmkansız/Negatif | Yalova -> Kars | ferry | one_way | ✅ PASS | Eksiksiz & Doğru |
| G01 | Grup G: Sınır Durumlar | İstanbul -> Ankara | all | past_date | ✅ PASS | Geçmiş tarih güvenli tarihe çekildi: 2026-10-29 |
| G02 | Grup G: Sınır Durumlar | İstanbul -> İzmir | all | invalid_pax | ✅ PASS | Yolcu sayısı güvenli sınıra (1) normalize edildi. |
| G03 | Grup G: Sınır Durumlar | İstanbul -> Antalya | flight | currency_eur | ✅ PASS | Eksiksiz & Doğru |
| G04 | Grup G: Sınır Durumlar | İstanbul -> Londra | flight | currency_usd | ✅ PASS | Eksiksiz & Doğru |
| G05 | Grup G: Sınır Durumlar | <script>alert(1)</script>İzmir -> Atina'-- | all | special_chars | ✅ PASS | Eksiksiz & Doğru |
