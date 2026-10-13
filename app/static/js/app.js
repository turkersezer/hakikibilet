// Hakiki Bilet (hakikibilet.com) — Frontend Core Application
// Slogan: Hakiki Fiyat, Hakiki Bilet

let currentMasterMode = 'fast'; // 'fast' (1. Hızlı Bilet Karşılaştır A ➔ B) or 'smart_route' (2. Akıllı Rota & Seyahat Planla)
let currentIncludeHotel = false; // İsteğe bağlı konaklama/otel seçeneği
let currentTransportMode = 'flight'; // Varsayılan: Uçak Bileti
let currentTripType = 'one_way'; // 'one_way' or 'round_trip'
let currentSearchData = null;
let currentActiveSummaryFilter = 'flight';
let currentCalendarRange = 7; // 7, 15, or 30 days
let currentCurrency = localStorage.getItem('preferredCurrency') || 'TRY';
let currentSortMode = 'price_asc'; // 'price_asc', 'dep_asc', 'dep_desc', 'dur_asc'
let currentCarrierFilter = 'all'; // 'all' or carrier name

function parseDurationToMinutes(durStr) {
    if (!durStr) return 99999;
    let total = 0;
    const hMatch = durStr.match(/(\d+)\s*sa/);
    const mMatch = durStr.match(/(\d+)\s*dk/);
    if (hMatch) total += parseInt(hMatch[1]) * 60;
    if (mMatch) total += parseInt(mMatch[1]);
    return total > 0 ? total : 99999;
}

function setSortMode(mode) {
    currentSortMode = mode;
    updateSortButtonsUI();
    filterAndRenderTickets('');
}

function onCarrierFilterChange(carrier) {
    currentCarrierFilter = carrier;
    filterAndRenderTickets('');
}

function updateSortButtonsUI() {
    const buttons = [
        { id: 'sortBtnPriceAsc', mode: 'price_asc' },
        { id: 'sortBtnDepAsc', mode: 'dep_asc' },
        { id: 'sortBtnDepDesc', mode: 'dep_desc' },
        { id: 'sortBtnDurAsc', mode: 'dur_asc' }
    ];
    buttons.forEach(b => {
        const el = document.getElementById(b.id);
        if (!el) return;
        if (b.mode === currentSortMode) {
            el.className = 'sort-bar-btn px-3 py-1.5 rounded-xl text-xs font-black transition flex items-center gap-1 bg-blue-600 text-white shadow-xs';
        } else {
            el.className = 'sort-bar-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1 bg-slate-100 text-slate-700 hover:bg-slate-200';
        }
    });
}

const CURRENCY_SYMBOLS = {
    'TRY': '₺',
    'EUR': '€',
    'USD': '$',
    'GBP': '£'
};

function getCurrencySymbol(curr) {
    return CURRENCY_SYMBOLS[curr] || curr || '₺';
}

function changeCurrency(curr) {
    currentCurrency = curr;
    localStorage.setItem('preferredCurrency', curr);
    const sel = document.getElementById('currencySelector');
    if (sel && sel.value !== curr) sel.value = curr;

    showToast(`Para birimi ${curr} olarak güncellendi.`, 'info');
    if (currentSearchData) {
        handleSearch();
    }
}

// ==================== İKİ ANA KULLANIM MODU VE OTEL YÖNETİMİ ====================

function switchMasterMode(mode) {
    currentMasterMode = mode;
    const fastBtn = document.getElementById('masterModeFastBtn');
    const routeBtn = document.getElementById('masterModeRouteBtn');
    const tabs = document.getElementById('transportTabs');
    const noticeBox = document.getElementById('smartRouteNoticeBox');
    const submitBtn = document.getElementById('searchSubmitBtn');
    const modeStatusLabel = document.getElementById('modeStatusLabel');

    if (mode === 'fast') {
        if (fastBtn) fastBtn.className = 'px-5 py-2.5 rounded-xl font-black text-xs sm:text-sm transition bg-white text-blue-700 shadow-md flex items-center gap-2';
        if (routeBtn) routeBtn.className = 'px-5 py-2.5 rounded-xl font-black text-xs sm:text-sm text-white/90 hover:text-white transition flex items-center gap-2';
        if (tabs) tabs.classList.remove('hidden');
        if (noticeBox) noticeBox.classList.add('hidden');
        if (submitBtn) {
            const span = submitBtn.querySelector('span');
            if (span) span.innerText = (currentTransportMode === 'car') ? 'Araç Ara' : 'Bilet Ara';
        }
        if (modeStatusLabel) {
            modeStatusLabel.innerHTML = '⚡ <strong>Hızlı Bilet Modu:</strong> A noktasından B noktasına doğrudan tek vasıta seferlerini karşılaştırır.';
        }
    } else {
        // smart_route
        if (routeBtn) routeBtn.className = 'px-5 py-2.5 rounded-xl font-black text-xs sm:text-sm transition bg-white text-emerald-700 shadow-md flex items-center gap-2';
        if (fastBtn) fastBtn.className = 'px-5 py-2.5 rounded-xl font-black text-xs sm:text-sm text-white/90 hover:text-white transition flex items-center gap-2';
        if (tabs) tabs.classList.add('hidden');
        if (noticeBox) noticeBox.classList.remove('hidden');
        if (submitBtn) {
            const span = submitBtn.querySelector('span');
            if (span) span.innerText = '🧭 Akıllı Rotayı Planla';
        }
        if (modeStatusLabel) {
            modeStatusLabel.innerHTML = '🧭 <strong>Akıllı Rota & Seyahat Planı:</strong> Şehirlerarası aktarmalar, havalimanı servisleri, biletler ve isteğe bağlı otel konaklaması tek ekranda!';
        }
    }

    if (currentSearchData) {
        handleSearch();
    }
}

function toggleHotelSelection() {
    const chk = document.getElementById('includeHotelCheck');
    currentIncludeHotel = chk ? chk.checked : false;
    showToast(currentIncludeHotel ? '🏨 Konaklama / Otel seçeneği seyahat planına dahil edildi.' : '🏨 Konaklama seyahat planından çıkarıldı.', 'info');
    if (currentSearchData && currentMasterMode === 'smart_route') {
        handleSearch();
    }
}

function selectCuratedEvent(city, depDate, retDate, transportMode) {
    // 1. Şehir kontrolü ve Kapsam belirleme
    const cityObj = (window.ALL_CITIES || []).find(c => c.name.toLowerCase() === city.toLowerCase() || c.name.toLowerCase().includes(city.toLowerCase()));
    if (cityObj && (cityObj.is_international || cityObj.is_ferry)) {
        if (currentScope !== 'international') {
            setScope('international');
        }
    } else if (currentScope !== 'domestic' && cityObj && !cityObj.is_international) {
        setScope('domestic');
    }

    // 2. Akıllı Rota Moduna geçir ve Otel seçeneğini aktif yap
    switchMasterMode('smart_route');
    const hotelChk = document.getElementById('includeHotelCheck');
    if (hotelChk) hotelChk.checked = true;
    currentIncludeHotel = true;

    // 3. Varış noktasını seç
    const destSelect = document.getElementById('destCity');
    if (destSelect) {
        let optFound = Array.from(destSelect.options).find(o => o.value.toLowerCase().includes(city.toLowerCase()));
        if (!optFound && cityObj) {
            destSelect.add(new Option(cityObj.name, cityObj.name), 0);
            destSelect.value = cityObj.name;
        } else if (optFound) {
            destSelect.value = optFound.value;
        }
    }

    // 4. Tarihleri ayarla
    const depInput = document.getElementById('departureDate');
    const retInput = document.getElementById('returnDate');
    if (depInput && depDate) depInput.value = depDate;
    if (retDate) {
        setTripType('round_trip');
        if (retInput) retInput.value = retDate;
    }

    // 5. Ulaşım modunu ayarla
    if (transportMode && transportMode !== 'flight') {
        currentTransportMode = transportMode;
    } else {
        currentTransportMode = 'flight';
    }

    showToast(`✨ ${city} festival ve seyahat planı hazırlanıyor...`, 'success');
    handleSearch();
}


document.addEventListener('DOMContentLoaded', () => {
    // Para birimi seçici durumunu yükle
    const savedCurr = localStorage.getItem('preferredCurrency') || 'TRY';
    currentCurrency = savedCurr;
    const currSel = document.getElementById('currencySelector');
    if (currSel) currSel.value = savedCurr;

    // Default departure date: 7 days in future
    const depInput = document.getElementById('departureDate');
    const retInput = document.getElementById('returnDate');
    
    if (depInput && !depInput.value) {
        const d = new Date();
        d.setDate(d.getDate() + 7);
        depInput.value = d.toISOString().split('T')[0];
        
        if (retInput) {
            const retDate = new Date(d);
            retDate.setDate(retDate.getDate() + 3);
            retInput.value = retDate.toISOString().split('T')[0];
        }
    }

    // Kabin sınıfı değiştiğinde canlı güncelleme
    const cabinSelect = document.getElementById('cabinClass');
    if (cabinSelect) {
        cabinSelect.addEventListener('change', () => {
            if (currentSearchData) {
                handleSearch();
            }
        });
    }

    // Check Push notification status
    if ('Notification' in window && Notification.permission === 'granted') {
        const banner = document.getElementById('pushBanner');
        if (banner) banner.style.display = 'none';
    }

    // Register Service Worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js')
            .catch(err => console.log('SW registration error:', err));
    }

    // Dropdown listelerini ilk açılışta kapsam ve moda göre senkronize et
    updateCityDropdowns(currentTransportMode);
});

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    let bgClass = 'bg-slate-900 border-emerald-500 text-white';
    let icon = 'fa-circle-check text-emerald-400';

    if (type === 'error') {
        bgClass = 'bg-rose-900 border-rose-500 text-white';
        icon = 'fa-circle-exclamation text-rose-400';
    } else if (type === 'info') {
        bgClass = 'bg-slate-900 border-blue-500 text-white';
        icon = 'fa-circle-info text-blue-400';
    }

    toast.className = `${bgClass} border-l-4 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs font-semibold animate-fade-in pointer-events-auto max-w-sm`;
    toast.innerHTML = `
        <i class="fa-solid ${icon} text-base"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4500);
}

// ==================== GİDİŞ - DÖNÜŞ VE SEYAHAT SEÇENEKLERİ ====================

function setTripType(type) {
    currentTripType = type;
    const oneWayBtn = document.getElementById('tripOneWayBtn');
    const roundBtn = document.getElementById('tripRoundBtn');
    const returnContainer = document.getElementById('returnDateContainer');

    const searchForm = document.getElementById('searchForm');

    if (type === 'round_trip') {
        roundBtn.className = 'px-4 py-1.5 rounded-lg text-xs font-bold transition bg-white text-blue-700 shadow-sm';
        oneWayBtn.className = 'px-4 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition';
        if (returnContainer) {
            returnContainer.classList.remove('hidden');
            const depVal = document.getElementById('departureDate').value;
            const retInput = document.getElementById('returnDate');
            if (depVal && (!retInput.value || retInput.value < depVal)) {
                const depD = new Date(depVal);
                depD.setDate(depD.getDate() + 3);
                retInput.value = depD.toISOString().split('T')[0];
            }
        }
        if (searchForm) {
            searchForm.classList.remove('lg:grid-cols-5');
            searchForm.classList.add('lg:grid-cols-6');
        }
    } else {
        oneWayBtn.className = 'px-4 py-1.5 rounded-lg text-xs font-bold transition bg-white text-blue-700 shadow-sm';
        roundBtn.className = 'px-4 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition';
        if (returnContainer) {
            returnContainer.classList.add('hidden');
        }
        if (searchForm) {
            searchForm.classList.remove('lg:grid-cols-6');
            searchForm.classList.add('lg:grid-cols-5');
        }
    }
}

// ==================== MODÜL 1: DİNAMİK İSTASYON & ARAMA ====================

let currentScope = 'domestic'; // 'domestic' or 'international'

function setScope(scope) {
    currentScope = scope;
    const domBtn = document.getElementById('scopeDomesticBtn');
    const intlBtn = document.getElementById('scopeIntlBtn');
    const hint = document.getElementById('scopeHintText');

    if (scope === 'domestic') {
        if (domBtn) domBtn.className = 'px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold transition bg-white text-blue-700 shadow-sm flex items-center gap-1.5';
        if (intlBtn) intlBtn.className = 'px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5';
        if (hint) hint.innerText = 'Türkiye geneli tüm havalimanı, tren, otobüs ve feribot seferleri';
    } else {
        if (intlBtn) intlBtn.className = 'px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold transition bg-white text-blue-700 shadow-sm flex items-center gap-1.5';
        if (domBtn) domBtn.className = 'px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5';
        if (hint) hint.innerText = 'Dünya metropolleri (Amerika, Avrupa, Asya, Körfez), Avrupa YHT ve Ege feribot seferleri';
    }

    updateCityDropdowns(currentTransportMode);
    showToast(scope === 'domestic' ? '🇹🇷 Yurt İçi sefer moduna geçildi.' : '🌍 Yurt Dışı & Global sefer moduna geçildi.', 'info');

    if (currentSearchData) {
        handleSearch();
    }
}

function detectUserLocation() {
    if (!navigator.geolocation) {
        showToast('Tarayıcınız konum servisini desteklemiyor.', 'error');
        return;
    }

    showToast('📍 Konumunuz hesaplanıyor...', 'info');

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const userLat = pos.coords.latitude;
            const userLng = pos.coords.longitude;

            let nearestCity = null;
            let minDistance = Infinity;
            const R = 6371; // km

            (window.ALL_CITIES || []).forEach(city => {
                if (city.lat && city.lng && city.country !== 'Yunanistan' && !city.is_international) {
                    const dLat = (city.lat - userLat) * Math.PI / 180;
                    const dLng = (city.lng - userLng) * Math.PI / 180;
                    const a = 
                        Math.sin(dLat/2) * Math.sin(dLat/2) +
                        Math.cos(userLat * Math.PI / 180) * Math.cos(city.lat * Math.PI / 180) * 
                        Math.sin(dLng/2) * Math.sin(dLng/2);
                    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                    const d = R * c;
                    if (d < minDistance) {
                        minDistance = d;
                        nearestCity = city;
                    }
                }
            });

            if (nearestCity) {
                const originSelect = document.getElementById('originCity');
                if (originSelect) {
                    let optExists = Array.from(originSelect.options).some(o => o.value === nearestCity.name);
                    if (!optExists) {
                        originSelect.add(new Option(`${nearestCity.name} (Konumunuz)`, nearestCity.name), 0);
                    }
                    originSelect.value = nearestCity.name;
                    showToast(`📍 Konumunuz belirlendi: ${nearestCity.name} (~${Math.round(minDistance)} km mesafede)`, 'success');
                }
            } else {
                showToast('En yakın şehir tespit edilemedi.', 'error');
            }
        },
        (err) => {
            console.warn('Geolocation error:', err);
            showToast('Konum izni alınamadı. Lütfen tarayıcı izinlerini kontrol edin.', 'error');
        },
        { enableHighAccuracy: true, timeout: 8000 }
    );
}

function updateCityDropdowns(mode) {
    const originSelect = document.getElementById('originCity');
    const destSelect = document.getElementById('destCity');
    const originLabel = document.getElementById('originLabel');
    const destLabel = document.getElementById('destLabel');
    const modeStatusLabel = document.getElementById('modeStatusLabel');

    if (!window.ALL_CITIES || !originSelect || !destSelect) return;

    const currentOrigin = originSelect.value;
    const currentDest = destSelect.value;

    let originCities = [];
    let destCities = [];
    let originLabelHtml = '<i class="fa-solid fa-location-dot text-blue-600 mr-1"></i> Kalkış';
    let destLabelHtml = '<i class="fa-solid fa-location-arrow text-indigo-600 mr-1"></i> Varış';
    let statusText = 'Tüm seyahat alternatifleri karşılaştırmalı olarak listelenir.';

    const trCities = window.ALL_CITIES.filter(c => !c.is_international && !c.is_ferry);
    const intlCities = window.ALL_CITIES.filter(c => c.is_international);
    const ferryPorts = window.ALL_CITIES.filter(c => c.is_ferry);

    if (currentScope === 'domestic') {
        if (mode === 'car') {
            if (currentCarLocationType === 'airport') {
                originCities = trCities.filter(c => c.has_airport);
                destCities = originCities;
                statusText = '✈️ <strong>Havalimanı Kiralama:</strong> Terminal içi ofisler ve uçuş inişi teslimat (Yolcu360, Enuygun, Obilet, Avis, Garenta).';
            } else if (currentCarLocationType === 'station') {
                originCities = trCities;
                destCities = trCities;
                statusText = '🚆 <strong>Gar & Otogar Kiralama:</strong> YHT istasyonları ve şehirlerarası otogar teslim araçlar.';
            } else {
                originCities = trCities;
                destCities = trCities;
                statusText = '🏙️ <strong>Şehir Merkezi Kiralama:</strong> Şehir ve ilçe ofisleri, adrese/otele teslimat imkanı.';
            }
        } else if (mode === 'train') {
            originCities = trCities.filter(c => c.has_train);
            destCities = originCities;
            statusText = '🚆 <strong>TCDD YHT Tren Seferleri:</strong> Ankara, İstanbul, Eskişehir, Konya, Karaman, Sivas, Yozgat vb. garlar listeleniyor.';
        } else if (mode === 'flight') {
            originCities = trCities.filter(c => c.has_airport);
            destCities = originCities;
            statusText = '✈️ <strong>Yurt İçi Uçuşlar:</strong> Türkiye\'nin tüm 58 aktif havalimanı listeleniyor.';
        } else if (mode === 'bus') {
            originCities = trCities;
            destCities = trCities;
            statusText = '🚌 <strong>Yurt İçi Otobüs:</strong> Türkiye\'nin tüm 81 ili ve ilçe otogarları listeleniyor.';
        } else if (mode === 'ferry') {
            originCities = ferryPorts.filter(p => p.country === 'Türkiye');
            destCities = originCities;
            statusText = '⛴️ <strong>Yurt İçi Feribot & Deniz Otobüsü:</strong> İDO ve BUDO Marmara hatları listeleniyor.';
        } else {
            // mode === 'all'
            originCities = trCities;
            destCities = trCities;
            statusText = '🇹🇷 <strong>Yurt İçi Karşılaştırma:</strong> Uçak, TCDD tren, otobüs ve feribot seferleri tek ekranda karşılaştırılır.';
        }
    } else {
        // currentScope === 'international'
        // Kalkış: Türkiye'deki tüm şehirler (Havalimanı olmayan Bolu, Yalova gibi iller için Akıllı Kombine Rota tetiklenir)
        if (mode === 'flight') {
            originCities = trCities;
            destCities = intlCities;
            statusText = '🌍 <strong>Yurt Dışı Uçuşlar:</strong> Amerika, Avrupa, Asya ve Körfez havalimanları listeleniyor. Havalimanı olmayan illerden akıllı aktarmalı rota planlanır.';
        } else if (mode === 'train') {
            originCities = intlCities.filter(c => c.has_train).concat(trCities.filter(c => c.has_train && (c.slug === 'istanbul' || c.slug === 'edirne')));
            destCities = intlCities.filter(c => c.has_train);
            statusText = '🚆 <strong>Avrupa Hızlı Trenleri:</strong> Eurostar (Londra/Paris), Frecciarossa (Roma/Milano), DB ICE (Almanya), Renfe AVE (Madrid/Barselona).';
        } else if (mode === 'bus') {
            originCities = trCities;
            destCities = intlCities.filter(c => c.has_bus);
            statusText = '🚌 <strong>Uluslararası Otobüs Hatları:</strong> Yunanistan (Selanik, Atina), Bulgaristan (Sofya, Varna, Plovdiv) ve Gürcistan (Batum) seferleri.';
        } else if (mode === 'ferry') {
            originCities = ferryPorts.filter(p => p.region === 'Ege' && p.country === 'Türkiye');
            destCities = ferryPorts.filter(p => p.country === 'Yunanistan' || p.requires_visa);
            statusText = '⛴️ <strong>Ege Yunan Adaları:</strong> Çeşme-Sakız, Bodrum-Kos, Ayvalık-Midilli, Kuşadası-Samos, Fethiye-Rodos, Kaş-Meis hatları.';
        } else if (mode === 'car') {
            originCities = trCities.filter(c => c.has_airport);
            destCities = originCities;
            statusText = '🚗 <strong>Araç Kiralama:</strong> Yurt içi havalimanı ve şehir ofisleri teslim.';
        } else {
            // mode === 'all'
            originCities = trCities;
            destCities = intlCities.concat(ferryPorts.filter(p => p.country === 'Yunanistan'));
            statusText = '🌍 <strong>Yurt Dışı Karşılaştırma:</strong> Dünya uçuşları, Avrupa hızlı trenleri, komşu ülke otobüsleri ve Ege feribotları tek ekranda!';
        }
    }

    if (originLabel) originLabel.innerHTML = originLabelHtml;
    if (destLabel) destLabel.innerHTML = destLabelHtml;
    if (modeStatusLabel) modeStatusLabel.innerHTML = statusText;

    originSelect.innerHTML = '';
    destSelect.innerHTML = '';

    function formatOptionText(c, isOrigin, currentMode) {
        if (currentMode === 'car') {
            if (currentCarLocationType === 'airport') return `${c.name} (${c.iata || 'Havalimanı'}) Terminal Ofisi`;
            if (currentCarLocationType === 'station') return `${c.name} — ${c.train_station || 'Otogar / Terminal'}`;
            return `${c.name} — Şehir Merkezi & İlçe Ofisleri`;
        }
        if (currentMode === 'train') return `${c.name} — ${c.train_station || 'Tren Garı'}`;
        if (currentMode === 'flight') return c.iata ? `${c.name} (${c.iata})` : c.name;
        if (currentMode === 'bus') return `${c.name} Otogarı`;
        if (currentMode === 'ferry') return `${c.name}`;
        return `${c.name}${c.iata ? ' (' + c.iata + ')' : ''}`;
    }

    originCities.forEach(c => {
        const text = formatOptionText(c, true, mode);
        originSelect.add(new Option(text, c.name));
    });

    destCities.forEach(c => {
        const text = formatOptionText(c, false, mode);
        destSelect.add(new Option(text, c.name));
    });

    const hasOrigin = originCities.some(c => c.name === currentOrigin);
    const hasDest = destCities.some(c => c.name === currentDest);

    if (hasOrigin) {
        originSelect.value = currentOrigin;
    } else {
        originSelect.value = originCities[0]?.name || 'İstanbul';
    }

    if (mode === 'car') {
        destSelect.value = originSelect.value;
    } else if (hasDest) {
        destSelect.value = currentDest;
    } else {
        if (currentScope === 'international') {
            destSelect.value = destCities.find(c => c.name === 'Paris')?.name || destCities[0]?.name || 'Paris';
        } else {
            const altCity = destCities.find(c => c.name !== originSelect.value);
            destSelect.value = altCity ? altCity.name : (destCities[1]?.name || 'Ankara');
        }
    }
}

let currentCarLocationType = 'city';

function setCarLocationType(type) {
    currentCarLocationType = type;
    const cityBtn = document.getElementById('carLocCityBtn');
    const airBtn = document.getElementById('carLocAirportBtn');
    const stnBtn = document.getElementById('carLocStationBtn');

    [cityBtn, airBtn, stnBtn].forEach(b => {
        if (!b) return;
        b.className = 'px-3 py-1 rounded-lg text-xs font-bold transition text-slate-600 hover:text-slate-900';
    });

    if (type === 'city' && cityBtn) {
        cityBtn.className = 'px-3 py-1 rounded-lg text-xs font-bold transition bg-white text-indigo-700 shadow-sm';
    } else if (type === 'airport' && airBtn) {
        airBtn.className = 'px-3 py-1 rounded-lg text-xs font-bold transition bg-white text-indigo-700 shadow-sm';
    } else if (type === 'station' && stnBtn) {
        stnBtn.className = 'px-3 py-1 rounded-lg text-xs font-bold transition bg-white text-indigo-700 shadow-sm';
    }

    updateCityDropdowns('car');

    if (currentSearchData && currentTransportMode === 'car') {
        handleSearch();
    }
}

let currentFerryVehicleType = 'passenger';

function setFerryVehicleType(type) {
    currentFerryVehicleType = type;
    const passBtn = document.getElementById('ferryVehPassengerBtn');
    const carBtn = document.getElementById('ferryVehCarBtn');
    const motoBtn = document.getElementById('ferryVehMotoBtn');

    [passBtn, carBtn, motoBtn].forEach(b => {
        if (!b) return;
        b.className = 'px-3 py-1 rounded-lg text-xs font-bold transition text-slate-600 hover:text-slate-900';
    });

    if (type === 'passenger' && passBtn) {
        passBtn.className = 'px-3 py-1 rounded-lg text-xs font-bold transition bg-white text-cyan-700 shadow-sm';
    } else if (type === 'car' && carBtn) {
        carBtn.className = 'px-3 py-1 rounded-lg text-xs font-bold transition bg-white text-cyan-700 shadow-sm';
    } else if (type === 'motorcycle' && motoBtn) {
        motoBtn.className = 'px-3 py-1 rounded-lg text-xs font-bold transition bg-white text-cyan-700 shadow-sm';
    }

    if (currentSearchData && currentTransportMode === 'ferry') {
        handleSearch();
    }
}

function selectTransport(mode) {
    currentTransportMode = mode;
    currentActiveSummaryFilter = mode;
    document.querySelectorAll('.transport-tab').forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active-tab');
            btn.classList.remove('text-slate-600', 'hover:bg-slate-100');
        } else {
            btn.classList.remove('active-tab');
            btn.classList.add('text-slate-600', 'hover:bg-slate-100');
        }
    });

    const originLabel = document.getElementById('originLabel');
    const destLabel = document.getElementById('destLabel');
    const returnDateContainer = document.getElementById('returnDateContainer');
    const modeStatusLabel = document.getElementById('modeStatusLabel');
    const searchSubmitBtn = document.getElementById('searchSubmitBtn');
    const carLocContainer = document.getElementById('carLocationTypeContainer');
    const ferryVehContainer = document.getElementById('ferryVehicleContainer');
    const cabinContainer = document.getElementById('cabinClassContainer');
    const nightOnlyCheck = document.getElementById('nightOnlyCheck')?.parentElement;
    const tripToggle = document.getElementById('tripOneWayBtn')?.parentElement;

    if (mode === 'car') {
        if (carLocContainer) carLocContainer.classList.remove('hidden');
        if (ferryVehContainer) ferryVehContainer.classList.add('hidden');
        if (cabinContainer) cabinContainer.classList.add('hidden');
        if (nightOnlyCheck) nightOnlyCheck.classList.add('hidden');
        if (tripToggle) tripToggle.classList.add('hidden');
        if (returnDateContainer) returnDateContainer.classList.remove('hidden');
        if (searchSubmitBtn) {
            const span = searchSubmitBtn.querySelector('span');
            if (span) span.innerText = 'Araç Ara';
        }
    } else if (mode === 'ferry') {
        if (carLocContainer) carLocContainer.classList.add('hidden');
        if (ferryVehContainer) ferryVehContainer.classList.remove('hidden');
        if (cabinContainer) cabinContainer.classList.add('hidden');
        if (nightOnlyCheck) nightOnlyCheck.classList.add('hidden');
        if (tripToggle) tripToggle.classList.remove('hidden');
        if (currentTripType === 'one_way' && returnDateContainer) returnDateContainer.classList.add('hidden');
        if (searchSubmitBtn) {
            const span = searchSubmitBtn.querySelector('span');
            if (span) span.innerText = 'Feribot Ara';
        }
    } else {
        if (carLocContainer) carLocContainer.classList.add('hidden');
        if (ferryVehContainer) ferryVehContainer.classList.add('hidden');
        if (cabinContainer) cabinContainer.classList.remove('hidden');
        if (nightOnlyCheck) nightOnlyCheck.classList.remove('hidden');
        if (tripToggle) tripToggle.classList.remove('hidden');
        if (currentTripType === 'one_way' && returnDateContainer) returnDateContainer.classList.add('hidden');
        if (searchSubmitBtn) {
            const span = searchSubmitBtn.querySelector('span');
            if (span) span.innerText = 'Bilet Ara';
        }
    }

    updateCityDropdowns(mode);

    if (currentSearchData) {
        if (mode === 'car') {
            handleSearch();
        } else {
            renderModelASummary(currentSearchData.summary);
            renderPriceCalendar(currentSearchData.price_calendar, currentSearchData.origin, currentSearchData.destination);
            filterAndRenderTickets('');
        }
    }
}

async function handleSearch(e) {
    if (e && e.preventDefault) e.preventDefault();
    const origin = document.getElementById('originCity').value;
    const dest = document.getElementById('destCity').value;
    const depDate = document.getElementById('departureDate').value;
    let retDate = (currentTripType === 'round_trip' || currentTransportMode === 'car') ? document.getElementById('returnDate').value : null;
    const passengers = parseInt(document.getElementById('passengers').value) || 1;
    const nightOnly = document.getElementById('nightOnlyCheck') ? document.getElementById('nightOnlyCheck').checked : false;
    const cabinClass = document.getElementById('cabinClass') ? document.getElementById('cabinClass').value : 'economy';

    if (currentTransportMode === 'car' && !retDate) {
        const d = new Date(depDate);
        d.setDate(d.getDate() + 3);
        retDate = d.toISOString().split('T')[0];
        const retInput = document.getElementById('returnDate');
        if (retInput) retInput.value = retDate;
    }

    if (currentTransportMode !== 'car' && origin === dest) {
        showToast('Kalkış ve varış şehri aynı olamaz!', 'error');
        return;
    }

    if ((currentTripType === 'round_trip' || currentTransportMode === 'car') && retDate && retDate < depDate) {
        showToast('İade/Dönüş tarihi alış/gidiş tarihinden önce olamaz!', 'error');
        return;
    }

    const searchSection = document.getElementById('searchResultsSection');
    const skeletonLoader = document.getElementById('skeletonLoader');
    const ticketsList = document.getElementById('ticketsList');

    if (searchSection) searchSection.classList.remove('hidden');
    if (skeletonLoader) skeletonLoader.classList.remove('hidden');
    if (ticketsList) ticketsList.classList.add('hidden');

    const submitBtn = document.getElementById('searchSubmitBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Aranıyor...`;
    }

    const hotelChecked = (currentMasterMode === 'smart_route')
        ? (document.getElementById('includeHotelCheck') ? document.getElementById('includeHotelCheck').checked : false)
        : false;

    currentActiveSummaryFilter = (currentTransportMode === 'car') ? 'car' : currentTransportMode;
    const effectiveTransport = (currentTransportMode === 'car') ? 'car' : 'all';

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin: origin,
                destination: dest,
                departure_date: depDate,
                return_date: retDate,
                trip_type: currentTripType,
                passengers: passengers,
                transport_type: effectiveTransport,
                cabin_class: cabinClass,
                calendar_range: currentCalendarRange,
                night_only: nightOnly,
                location_type: (currentTransportMode === 'car' ? currentCarLocationType : 'city'),
                ferry_vehicle_type: currentFerryVehicleType,
                currency: currentCurrency,
                search_mode: currentMasterMode,
                include_hotel: hotelChecked
            })
        });

        const data = await res.json();
        currentSearchData = data;
        renderSearchResults(data);

        if (skeletonLoader) skeletonLoader.classList.add('hidden');
        if (ticketsList) ticketsList.classList.remove('hidden');

        document.getElementById('searchResultsSection').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        console.error(err);
        if (skeletonLoader) skeletonLoader.classList.add('hidden');
        if (ticketsList) ticketsList.classList.remove('hidden');
        showToast('Arama sırasında hata oluştu.', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            let btnText = 'Bilet Ara';
            if (currentMasterMode === 'smart_route') {
                btnText = '🧭 Akıllı Rotayı Planla';
            } else if (currentTransportMode === 'car') {
                btnText = 'Araç Ara';
            }
            submitBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>${btnText}</span>`;
        }
    }
}

// ==================== AKILLI ÇOK MODLU KOMBİNE SEYAHAT PLANI (ROME2RIO MODELİ) ====================

function renderSmartMultimodalPlan(plan) {
    const container = document.getElementById('smartMultimodalContainer');
    if (!container) return;

    if (!plan || !plan.routes || plan.routes.length === 0) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    const routesHtml = plan.routes.map((route, idx) => {
        const isOpt1 = (idx === 0);
        const borderClass = isOpt1 ? 'border-emerald-300 bg-gradient-to-br from-emerald-50/70 via-white to-slate-50' : 'border-blue-300 bg-gradient-to-br from-blue-50/70 via-white to-slate-50';
        const badgeBg = isOpt1 ? 'bg-emerald-600 text-white' : 'bg-blue-600 text-white';
        const tagBadge = `<span class="text-[11px] font-black px-2.5 py-0.5 rounded-full ${isOpt1 ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-blue-100 text-blue-800 border border-blue-200'}">${route.tag || ''}</span>`;

        const stepsHtml = (route.steps || []).map(step => `
            <div class="flex items-start gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                <div class="w-8 h-8 rounded-lg ${isOpt1 ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-blue-50 text-blue-600 border border-blue-200'} flex items-center justify-center text-base shrink-0 font-bold">
                    ${step.icon || '📍'}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-xs font-black text-slate-900">${step.title}</div>
                    <div class="text-[11px] text-slate-500 font-medium mt-0.5">${step.desc}</div>
                </div>
                <div class="shrink-0">
                    <a href="${step.link}" target="_blank" class="inline-flex items-center gap-1 ${isOpt1 ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-500/20' : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20'} text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm transition">
                        <span>${step.action_text || 'Bileti Gör'}</span>
                    </a>
                </div>
            </div>
        `).join('<div class="flex justify-center py-0.5"><i class="fa-solid fa-arrow-down text-slate-400 text-xs"></i></div>');

        const whatsappMsg = encodeURIComponent(
            `🎫 Hakiki Bilet (Hakiki Fiyat, Hakiki Bilet):\n` +
            `📍 Güzergah: ${route.title}\n` +
            (route.steps || []).map(s => `• ${s.title}: ${s.desc}`).join('\n') +
            `\n🔗 Biletleri incele: ${window.location.href}`
        );

        return `
            <div class="rounded-2xl border-2 ${borderClass} p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <span class="${badgeBg} text-xs font-black px-3 py-1 rounded-xl shadow-xs">
                            ${route.badge}
                        </span>
                        ${tagBadge}
                    </div>
                    <h4 class="text-sm sm:text-base font-black text-slate-900 mb-3 flex items-center gap-1.5">
                        <i class="fa-solid fa-route ${isOpt1 ? 'text-emerald-600' : 'text-blue-600'}"></i>
                        <span>${route.title}</span>
                    </h4>
                    <div class="space-y-2 mb-4">
                        ${stepsHtml}
                    </div>
                </div>
                <div class="pt-3 border-t border-slate-200/80 flex items-center justify-between">
                    <span class="text-[11px] font-semibold text-slate-500">
                        <i class="fa-solid fa-shield-halved text-emerald-600"></i> Tek ekranda bağımsız rezervasyon
                    </span>
                    <a href="https://api.whatsapp.com/send?text=${whatsappMsg}" target="_blank" class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-lg transition" title="Bu rotayı WhatsApp ile paylaş">
                        <i class="fa-brands fa-whatsapp text-emerald-600"></i> Rotayı Paylaş
                    </a>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-xl border border-indigo-500/30">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5 pb-4 border-b border-indigo-800/60">
                <div>
                    <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-black border border-emerald-400/30 mb-2">
                        <i class="fa-solid fa-compass animate-spin text-[10px]" style="animation-duration: 8s;"></i> AKILLI ÇOK MODLU KOMBİNE SEYAHAT PLANI (ROME2RIO MODELİ)
                    </div>
                    <h3 class="text-lg sm:text-xl font-black text-white">
                        ${plan.title || `${plan.origin} ➔ ${plan.destination} Kombine Seyahat Rehberi`}
                    </h3>
                    <p class="text-xs text-slate-300 font-medium mt-1">
                        ${plan.description || `${plan.origin} kalkışlı seyahatiniz için 2 farklı rota alternatifi hazırlandı:`}
                    </p>
                </div>
                <div class="shrink-0 flex items-center gap-2">
                    <span class="bg-indigo-900/80 text-indigo-200 border border-indigo-700/60 text-xs font-bold px-3 py-1.5 rounded-xl flex items-center gap-1.5">
                        <i class="fa-solid fa-code-compare text-amber-400"></i> A/B Rota Karşılaştırması
                    </span>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                ${routesHtml}
            </div>
        </div>
    `;

    container.classList.remove('hidden');
}

// ==================== ARAMA SONUÇLARI VE MODEL A GÖRÜNÜMÜ ====================

function renderSearchResults(data) {
    const section = document.getElementById('searchResultsSection');
    const title = document.getElementById('resultsTitle');
    const subtitle = document.getElementById('resultsSubtitle');
    const modelAContainer = document.getElementById('modelASummaryContainer');
    const calendarContainer = document.getElementById('priceCalendarContainer');
    const deepLinksContainer = document.getElementById('deepLinksContainer');
    const ticketsList = document.getElementById('ticketsList');
    const carCrossContainer = document.getElementById('carCrossSellContainer');
    const multiContainer = document.getElementById('smartMultimodalContainer');

    section.classList.remove('hidden');

    // 🚗 ÖZEL ARAÇ KİRALAMA SONUÇ MODU
    if (data.transport_type === 'car') {
        const locLabel = data.car_rental?.location_type_label || 'Şehir Merkezi';
        title.innerText = `🚗 ${data.origin} Araç Kiralama Fırsatları`;
        subtitle.innerText = `${data.date} - ${data.return_date} • ${data.car_rental?.days_count || 3} Gün • ${locLabel} • ${data.results_count} Araç Segmenti`;

        if (multiContainer) multiContainer.classList.add('hidden');
        if (modelAContainer) modelAContainer.innerHTML = '';
        if (calendarContainer) calendarContainer.classList.add('hidden');
        if (carCrossContainer) carCrossContainer.classList.add('hidden');
        const crossAlertContainer = document.getElementById('crossModalAlertContainer');
        if (crossAlertContainer) crossAlertContainer.classList.add('hidden');
        const hotelContainer = document.getElementById('hotelRecommendationContainer');
        if (hotelContainer) hotelContainer.classList.add('hidden');
        const sortFilterBar = document.getElementById('sortFilterBarContainer');
        if (sortFilterBar) sortFilterBar.classList.add('hidden');

        if (data.car_rental && data.car_rental.deep_links) {
            const cl = data.car_rental.deep_links;
            deepLinksContainer.innerHTML = `
                <a href="${cl.yolcu360}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Yolcu360 (100+ Ofis)</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
                <a href="${cl.enuygun}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-sky-50 text-sky-800 border border-sky-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Enuygun Araç</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
                <a href="${cl.obilet}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-amber-50 text-amber-800 border border-amber-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Obilet Araç</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
                <a href="${cl.rentalcars}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-blue-50 text-blue-800 border border-blue-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Rentalcars.com</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        }

        renderCarRentalCards(data.car_rental);
        return;
    }

    // Normal Bilet Arama Sonuçları
    if (calendarContainer) calendarContainer.classList.remove('hidden');

    const tripLabel = data.trip_type === 'round_trip' ? 'Gidiş - Dönüş' : 'Tek Yön';
    title.innerText = `${data.origin} → ${data.destination} Seferleri`;
    subtitle.innerText = `${data.date}${data.return_date ? ' - ' + data.return_date : ''} • ${tripLabel} • ${data.passengers} Yolcu • ${data.results_count} Sefer Bulundu`;

    // -1. AKILLI ÇAPRAZ ULAŞIM İPUCU (Cross-Modal Hint)
    renderCrossModalHint(data.cross_modal_hint);

    // 0. AKILLI ÇOK MODLU KOMBİNE SEYAHAT PLANI (Rome2rio Modeli)
    renderSmartMultimodalPlan(data.smart_multimodal_plan);

    // 1. MODEL A: ULAŞIM TÜRÜNE GÖRE ÖZET KARTLARI (TABS)
    renderModelASummary(data.summary);

    // 2. ESNEK TARİH & EN UCUZ GÜNÜ BUL (FİYAT TAKVİMİ)
    renderPriceCalendar(data.price_calendar, data.origin, data.destination);

    // 2.5. AKILLI HAVALİMANI ARAÇ KİRALAMA ÇAPRAZ SATIŞ KUTUSU (Cross-Sell Widget)
    const carCross = data.car_rental;
    if (carCross && carCrossContainer) {
        carCrossContainer.classList.remove('hidden');
        carCrossContainer.innerHTML = `
            <div class="bg-gradient-to-r from-blue-950 via-indigo-900 to-slate-900 text-white rounded-2xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4 border border-blue-700/50">
                <div class="space-y-1">
                    <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-xs font-bold border border-blue-400/30">
                        <i class="fa-solid fa-car"></i> SEYAHAT EKSTRASI • ÇOKLU ARAÇ KİRALAMA
                    </div>
                    <h3 class="text-base font-black text-white">
                        ${data.destination}'e Vardığınızda Aracınız Hazır Olsun!
                    </h3>
                    <p class="text-xs text-slate-300 font-medium">
                        ${carCross.location_type_label || 'Havalimanı veya Şehir'} teslim araçlar günlük <span class="text-emerald-400 font-extrabold">${carCross.min_daily_price.toFixed(2)} ${data.currency || '₺'}</span>'den başlayan fiyatlarla.
                    </p>
                </div>
                <div class="flex items-center gap-2 self-start md:self-auto flex-wrap">
                    <a href="${carCross.deep_links.yolcu360}" target="_blank" class="bg-emerald-500 hover:bg-emerald-600 text-white font-extrabold text-xs px-3.5 py-2.5 rounded-xl shadow-md transition flex items-center gap-1.5 whitespace-nowrap">
                        <span>Yolcu360</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                    </a>
                    <a href="${carCross.deep_links.enuygun}" target="_blank" class="bg-sky-500 hover:bg-sky-600 text-white font-bold text-xs px-3.5 py-2.5 rounded-xl transition flex items-center gap-1.5 whitespace-nowrap">
                        <span>Enuygun</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                    </a>
                    <a href="${carCross.deep_links.obilet}" target="_blank" class="bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs px-3.5 py-2.5 rounded-xl transition flex items-center gap-1.5 whitespace-nowrap">
                        <span>Obilet</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                    </a>
                    <a href="${carCross.deep_links.rentalcars}" target="_blank" class="bg-white/10 hover:bg-white/20 text-white border border-white/20 font-bold text-xs px-3 py-2.5 rounded-xl transition flex items-center gap-1.5 whitespace-nowrap">
                        <span>Rentalcars</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                    </a>
                </div>
            </div>
        `;
    } else if (carCrossContainer) {
        carCrossContainer.classList.add('hidden');
    }

    // 3. Bilgilendirme Uyarıları
    let noticesHtml = '';
    if (data.notices && data.notices.length > 0) {
        noticesHtml = `
            <div class="bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl p-4 mb-6 shadow-sm">
                <div class="flex items-start gap-3">
                    <i class="fa-solid fa-triangle-exclamation text-amber-600 text-lg mt-0.5"></i>
                    <div class="space-y-1 text-xs font-semibold leading-relaxed">
                        ${data.notices.map(n => `<div>${n}</div>`).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    // 4. Doğrudan Arama Linkleri
    const links = data.deep_links;
    let flightLinksHtml = '';
    if (links.flight && links.flight.available) {
        flightLinksHtml = `
            ${links.flight.pegasus ? `
                <a href="${links.flight.pegasus}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-amber-50 text-amber-900 border border-amber-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Pegasus Bilet</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            ` : ''}
            <a href="${links.flight.enuygun}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                <span>Enuygun Uçak</span>
                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
            <a href="${links.flight.skyscanner}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-sky-50 text-sky-800 border border-sky-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                <span>Skyscanner</span>
                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
            <a href="${links.flight.google_flights}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-blue-50 text-blue-800 border border-blue-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                <span>Google Flights</span>
                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
        `;
    } else if (links.flight) {
        flightLinksHtml = `
            <span class="inline-flex items-center gap-1.5 bg-slate-100 text-slate-400 border border-slate-200 font-semibold px-3 py-1.5 rounded-lg text-xs cursor-not-allowed" title="${links.flight.reason || 'Havalimanı bulunmuyor'}">
                <i class="fa-solid fa-plane-slash text-[10px]"></i>
                <span>Uçuş Yok (Havalimanı Yok)</span>
            </span>
        `;
    }

    let trainLinksHtml = '';
    if (links.train && links.train.available) {
        if (links.train.is_international) {
            trainLinksHtml = `
                <a href="${links.train.trainline}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Trainline (Avrupa)</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
                <a href="${links.train.omio}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-indigo-50 text-indigo-800 border border-indigo-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Omio Tren</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        } else {
            trainLinksHtml = `
                <a href="${links.train.tcdd}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-rose-50 text-rose-800 border border-rose-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>TCDD E-Bilet</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        }
    } else if (links.train) {
        trainLinksHtml = `
            <span class="inline-flex items-center gap-1.5 bg-rose-50 text-rose-700 border border-rose-200 font-bold px-3 py-1.5 rounded-lg text-xs cursor-not-allowed" title="${links.train.reason || 'Demiryolu hattı bulunmuyor'}">
                <i class="fa-solid fa-circle-xmark text-[10px]"></i>
                <span>TCDD Tren Hattı Yok</span>
            </span>
        `;
    }

    let busLinksHtml = (links.bus && links.bus.available) ? `
        <a href="${links.bus.obilet}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-amber-50 text-amber-800 border border-amber-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
            <span>Obilet Otobüs</span>
            <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
        </a>
    ` : '';

    let ferryLinksHtml = '';
    if (links.ferry && links.ferry.available) {
        if (links.ferry.ido) {
            ferryLinksHtml += `
                <a href="${links.ferry.ido}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-cyan-50 text-cyan-800 border border-cyan-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>İDO Bilet</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        }
        if (links.ferry.budo) {
            ferryLinksHtml += `
                <a href="${links.ferry.budo}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-cyan-50 text-cyan-800 border border-cyan-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>BUDO Bilet</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        }
        if (links.ferry.erturk) {
            ferryLinksHtml += `
                <a href="${links.ferry.erturk}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-cyan-50 text-cyan-800 border border-cyan-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Ertürk Lines</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        }
        if (links.ferry.feribotlines) {
            ferryLinksHtml += `
                <a href="${links.ferry.feribotlines}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-cyan-50 text-cyan-800 border border-cyan-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                    <span>Feribotlines</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
            `;
        }
    }

    deepLinksContainer.innerHTML = flightLinksHtml + trainLinksHtml + busLinksHtml + ferryLinksHtml;

    // 5. Bilet Listesi
    filterAndRenderTickets(noticesHtml);

    // 6. Akıllı Otel ve Konaklama Metasearch (Seçenek A: Booking.com / Enuygun Otel)
    renderHotelRecommendations(data.hotel_info);
}

// ==================== AKILLI ÇAPRAZ ULAŞIM İPUCU (CROSS-MODAL HINT) ====================

function renderCrossModalHint(hint) {
    const container = document.getElementById('crossModalAlertContainer');
    if (!container) return;

    if (!hint) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="bg-gradient-to-r from-amber-50 via-emerald-50 to-blue-50 border border-amber-300/80 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex items-start gap-3">
                <div class="w-9 h-9 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 text-base font-bold shadow-2xs">
                    💡
                </div>
                <div>
                    <div class="text-xs font-black text-slate-900">${hint.title}</div>
                    <div class="text-[11px] text-slate-600 font-medium mt-0.5">${hint.desc}</div>
                </div>
            </div>
            <button type="button" onclick="selectTransport('${hint.mode}')" class="shrink-0 bg-white hover:bg-amber-50 text-amber-900 border border-amber-300 font-extrabold text-xs px-3.5 py-2 rounded-xl shadow-2xs transition flex items-center gap-1.5 self-start sm:self-auto">
                <span>${hint.action_text}</span>
            </button>
        </div>
    `;
}

// ==================== AKILLI OTEL VE KONAKLAMA METASEARCH (SEÇENEK A) ====================

function renderHotelRecommendations(hotel) {
    const container = document.getElementById('hotelRecommendationContainer');
    if (!container) return;

    if (!hotel) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    const categoriesHtml = (hotel.categories || []).map(cat => `
        <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs hover:shadow-sm transition flex flex-col justify-between">
            <div>
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-black text-slate-900">${cat.title}</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${cat.badge_color === 'emerald' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : (cat.badge_color === 'purple' ? 'bg-purple-50 text-purple-700 border border-purple-200' : 'bg-blue-50 text-blue-700 border border-blue-200')}">${cat.badge}</span>
                </div>
                <p class="text-[11px] text-slate-500 font-medium mb-3">${cat.desc}</p>
            </div>
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
                <div>
                    <div class="text-[10px] text-slate-400 font-bold uppercase">Gecelik ~${cat.est_nightly.toFixed(2)} ${hotel.currency}</div>
                    <div class="text-base font-black text-slate-900">${cat.est_total.toFixed(2)} ${hotel.currency}</div>
                </div>
                <a href="${cat.link}" target="_blank" class="bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs px-3 py-1.5 rounded-lg shadow-sm transition flex items-center gap-1">
                    <span>Oda Seç ↗</span>
                </a>
            </div>
        </div>
    `).join('');

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="bg-gradient-to-r from-blue-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-xl border border-blue-500/30">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5 pb-4 border-b border-indigo-800/60">
                <div>
                    <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-black border border-emerald-400/30 mb-2">
                        <i class="fa-solid fa-hotel"></i> AKILLI KONAKLAMA & OTEL METASEARCH
                    </div>
                    <h3 class="text-lg sm:text-xl font-black text-white">
                        🏨 ${hotel.destination} İçin ${hotel.nights} Gece Konaklama Seçenekleri
                    </h3>
                    <p class="text-xs text-slate-300 font-medium mt-1">
                        ${hotel.checkin_date} - ${hotel.checkout_date} • ${hotel.guests} Misafir • ${hotel.region_label}
                    </p>
                </div>
                <div class="flex items-center gap-2 flex-wrap">
                    <a href="${hotel.deep_links.booking}" target="_blank" class="bg-blue-600 hover:bg-blue-500 text-white font-black text-xs px-4 py-2.5 rounded-xl shadow-md transition flex items-center gap-1.5">
                        <span>Booking.com'da İncele</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>
                    <a href="${hotel.deep_links.enuygun}" target="_blank" class="bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs px-4 py-2.5 rounded-xl shadow-md transition flex items-center gap-1.5">
                        <span>Enuygun Otel</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>
                    <a href="${hotel.deep_links.agoda}" target="_blank" class="bg-white/10 hover:bg-white/20 text-white border border-white/20 font-bold text-xs px-3.5 py-2.5 rounded-xl transition flex items-center gap-1.5">
                        <span>Agoda</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>
                </div>
            </div>

            <!-- Fiyat Seviyesi Kartları -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-slate-800">
                ${categoriesHtml}
            </div>

            <!-- Şeffaflık İlkesi Notu -->
            <div class="text-[11px] text-slate-400 font-semibold flex items-center gap-2 pt-2 border-t border-indigo-900/60">
                <i class="fa-solid fa-shield-halved text-emerald-400"></i>
                <span>${hotel.disclaimer}</span>
            </div>
        </div>
    `;
}

// MODEL A: ÖZET KARTLARININ ÇİZİMİ
function renderModelASummary(summary) {
    const container = document.getElementById('modelASummaryContainer');
    if (!container || !summary) return;

    const f = summary.flight;
    const t = summary.train;
    const b = summary.bus;
    const ferry = summary.ferry;

    const hasFerry = ferry && (ferry.available || currentTransportMode === 'ferry');
    if (hasFerry) {
        container.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6";
    } else {
        container.className = "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-6";
    }

    let ferryCardHtml = '';
    if (hasFerry) {
        ferryCardHtml = `
        <!-- Feribot Kartı -->
        <div onclick="filterByTransportMode('ferry')" class="cursor-pointer bg-white rounded-2xl border ${currentActiveSummaryFilter === 'ferry' ? 'border-cyan-600 ring-2 ring-cyan-500/20 shadow-md' : 'border-slate-200'} p-5 transition hover:shadow-lg flex flex-col justify-between ${!ferry.available ? 'opacity-60 bg-slate-50 cursor-not-allowed' : ''}">
            <div class="flex items-center justify-between mb-3">
                <span class="font-bold text-sm text-slate-800 flex items-center gap-2">
                    <span class="text-xl">⛴️</span> FERİBOT & ADALAR
                </span>
                ${ferry.available ? `<span class="bg-cyan-50 text-cyan-700 text-xs font-bold px-2 py-0.5 rounded-full">${ferry.count} Hat</span>` : `<span class="bg-rose-50 text-rose-700 text-[10px] font-bold px-2 py-0.5 rounded">Hattı Yok</span>`}
            </div>
            ${ferry.available ? `
                <div class="flex items-baseline justify-between mt-2">
                    <div>
                        ${ferry.min_price != null ? `
                            <span class="text-sm font-black text-cyan-700 block">${Math.round(ferry.min_price).toLocaleString('tr-TR')} ₺'den Başlayan</span>
                        ` : `
                            <span class="text-[11px] text-cyan-600 font-bold block">Canlı Sefer & Fiyat</span>
                        `}
                        <span class="text-xs font-bold text-slate-700">İDO / BUDO / Feribot</span>
                    </div>
                    <div class="text-right">
                        <span class="text-[11px] text-slate-400 font-semibold block">Süre</span>
                        <span class="text-xs font-bold text-slate-700">${ferry.min_duration || '30 dk'}</span>
                    </div>
                </div>
            ` : `
                <p class="text-xs text-slate-400 mt-2">${ferry.reason || 'Bu rotada feribot hattı bulunmuyor.'}</p>
            `}
        </div>
        `;
    }

    container.innerHTML = `
        <!-- Uçak Kartı -->
        <div onclick="filterByTransportMode('flight')" class="cursor-pointer bg-white rounded-2xl border ${currentActiveSummaryFilter === 'flight' ? 'border-blue-600 ring-2 ring-blue-500/20 shadow-md' : 'border-slate-200'} p-5 transition hover:shadow-lg flex flex-col justify-between ${!f.available ? 'opacity-60 bg-slate-50 cursor-not-allowed' : ''}">
            <div class="flex items-center justify-between mb-3">
                <span class="font-bold text-sm text-slate-800 flex items-center gap-2">
                    <span class="text-xl">✈️</span> UÇAK BİLETİ
                </span>
                ${f.available ? `<span class="bg-blue-50 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full">${f.count} Hat</span>` : `<span class="bg-rose-50 text-rose-700 text-[10px] font-bold px-2 py-0.5 rounded">Havalimanı Yok</span>`}
            </div>
            ${f.available ? `
                <div class="flex items-baseline justify-between mt-2">
                    <div>
                        ${f.min_price != null ? `
                            <span class="text-sm font-black text-blue-700 block">${Math.round(f.min_price).toLocaleString('tr-TR')} ₺'den Başlayan</span>
                        ` : `
                            <span class="text-[11px] text-blue-600 font-bold block">Canlı Uçuşlar</span>
                        `}
                        <span class="text-xs font-bold text-slate-700">Pegasus / AJet / THY</span>
                    </div>
                    <div class="text-right">
                        <span class="text-[11px] text-slate-400 font-semibold block">En Hızlı</span>
                        <span class="text-xs font-bold text-slate-700">${f.min_duration || '1 sa 10 dk'}</span>
                    </div>
                </div>
            ` : `
                <p class="text-xs text-slate-400 mt-2">${f.reason || 'Bu rotada havalimanı bulunmuyor.'}</p>
            `}
        </div>

        <!-- Tren Kartı -->
        <div onclick="filterByTransportMode('train')" class="cursor-pointer bg-white rounded-2xl border ${currentActiveSummaryFilter === 'train' ? 'border-emerald-600 ring-2 ring-emerald-500/20 shadow-md' : 'border-slate-200'} p-5 transition hover:shadow-lg flex flex-col justify-between ${!t.available ? 'opacity-60 bg-slate-50 cursor-not-allowed' : ''}">
            <div class="flex items-center justify-between mb-3">
                <span class="font-bold text-sm text-slate-800 flex items-center gap-2">
                    <span class="text-xl">🚆</span> TCDD TREN (YHT)
                </span>
                ${t.available ? `<span class="bg-emerald-50 text-emerald-700 text-xs font-bold px-2 py-0.5 rounded-full">${t.count} Hat</span>` : `<span class="bg-rose-50 text-rose-700 text-[10px] font-bold px-2 py-0.5 rounded">Tren Hattı Yok</span>`}
            </div>
            ${t.available ? `
                <div class="flex items-baseline justify-between mt-2">
                    <div>
                        ${t.min_price != null ? `
                            <span class="text-sm font-black text-emerald-700 block">${Math.round(t.min_price).toLocaleString('tr-TR')} ₺'den Başlayan</span>
                        ` : `
                            <span class="text-[11px] text-emerald-600 font-bold block">Canlı YHT Seferleri</span>
                        `}
                        <span class="text-xs font-bold text-slate-700">TCDD E-Bilet</span>
                    </div>
                    <div class="text-right">
                        <span class="text-[11px] text-slate-400 font-semibold block">Süre</span>
                        <span class="text-xs font-bold text-slate-700">${t.min_duration || '4 sa 25 dk'}</span>
                    </div>
                </div>
            ` : `
                <p class="text-xs text-slate-400 mt-2">${t.reason || 'Bu rotada demiryolu hattı bulunmuyor.'}</p>
            `}
        </div>

        <!-- Otobüs Kartı -->
        <div onclick="filterByTransportMode('bus')" class="cursor-pointer bg-white rounded-2xl border ${currentActiveSummaryFilter === 'bus' ? 'border-amber-600 ring-2 ring-amber-500/20 shadow-md' : 'border-slate-200'} p-5 transition hover:shadow-lg flex flex-col justify-between">
            <div class="flex items-center justify-between mb-3">
                <span class="font-bold text-sm text-slate-800 flex items-center gap-2">
                    <span class="text-xl">🚌</span> OTOBÜS BİLETİ
                </span>
                <span class="bg-amber-50 text-amber-800 text-xs font-bold px-2 py-0.5 rounded-full">${b.count} Hat</span>
            </div>
            <div class="flex items-baseline justify-between mt-2">
                <div>
                    ${b.min_price != null ? `
                        <span class="text-sm font-black text-amber-700 block">${Math.round(b.min_price).toLocaleString('tr-TR')} ₺'den Başlayan</span>
                    ` : `
                        <span class="text-[11px] text-amber-700 font-bold block">2+1 Koltuk Seçimi</span>
                    `}
                    <span class="text-xs font-bold text-slate-700">Obilet (Kamil Koç / Pamukkale)</span>
                </div>
                <div class="text-right">
                    <span class="text-[11px] text-slate-400 font-semibold block">Süre</span>
                    <span class="text-xs font-bold text-slate-700">${b.min_duration || '6 sa 30 dk'}</span>
                </div>
            </div>
        </div>

        ${ferryCardHtml}
    `;
}

// ESNEK TARİH & SEFER TAKVİMİ (SIFIR YANILTICI FİYAT İLKESİ)
function renderPriceCalendar(calendarData, origin, dest) {
    const container = document.getElementById('priceCalendarContainer');
    if (!container || !calendarData || !calendarData.days) return;

    const days = calendarData.days;
    const daysCount = calendarData.range_type || currentCalendarRange || 7;

    const daysHtml = days.map(d => {
        let modesHtml = '';
        if (d.has_flight) modesHtml += '<span title="Uçak Seferleri">✈️</span> ';
        if (d.has_train) modesHtml += '<span title="YHT Tren Seferleri">🚆</span> ';
        if (d.has_bus) modesHtml += '<span title="Otobüs Seferleri">🚌</span> ';
        if (d.has_ferry) modesHtml += '<span title="Feribot Seferleri">⛴️</span> ';

        const isSelected = d.is_selected;

        return `
            <button type="button" onclick="selectCalendarDate('${d.date}')" class="min-w-[120px] max-w-[145px] p-2.5 rounded-2xl border transition flex flex-col justify-between text-center relative ${isSelected ? 'bg-blue-50 border-blue-600 ring-2 ring-blue-500/30 shadow-md' : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-sm'}">
                <div class="flex items-center justify-between border-b border-slate-100 pb-1 mb-1">
                    <span class="text-[11px] font-extrabold uppercase text-slate-500">${d.day_name}</span>
                    <span class="text-xs font-black text-slate-800">${d.day_num} ${d.month_name}</span>
                </div>

                <div class="my-2 py-1 text-center">
                    <div class="text-sm my-0.5 flex items-center justify-center gap-1">${modesHtml}</div>
                    <div class="text-[10px] font-bold text-slate-500 mt-1">Seferler Mevcut</div>
                </div>

                <div class="pt-1 border-t border-slate-100 flex items-center justify-center">
                    <span class="text-[10px] font-bold ${isSelected ? 'text-blue-700' : 'text-slate-400 hover:text-blue-600'}">
                        ${isSelected ? '✓ Seçili Gün' : 'Seferleri Gör →'}
                    </span>
                </div>
            </button>
        `;
    }).join('');

    const googleFlightsUrl = currentSearchData?.deep_links?.flight?.google_flights || '#';
    const hasFlight = currentSearchData?.deep_links?.flight?.available;

    container.innerHTML = `
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-calendar-days text-indigo-600 text-base"></i>
                <div>
                    <h3 class="text-xs font-black text-indigo-950 uppercase tracking-wide">Esnek Tarih & Sefer Takvimi</h3>
                    <p class="text-[11px] text-slate-500 font-medium">Haftanın diğer günlerine tek tıkla geçiş yapabilir, canlı seferleri sorgulayabilirsiniz</p>
                </div>
            </div>

            ${hasFlight ? `
                <a href="${googleFlightsUrl}" target="_blank" class="inline-flex items-center gap-1.5 text-xs font-bold text-blue-700 bg-white hover:bg-blue-50 px-3 py-1.5 rounded-xl border border-blue-200 shadow-sm transition">
                    <i class="fa-solid fa-chart-line text-blue-600"></i>
                    <span>Google Flights Canlı Çoklu Gün Fiyat Grafiği ↗</span>
                </a>
            ` : ''}
        </div>

        <!-- Gün Kartları Kaydırma Alanı -->
        <div class="flex gap-2.5 overflow-x-auto pb-3 pt-2 scrollbar-thin">
            ${daysHtml}
        </div>

        <!-- Bilgilendirme -->
        <div class="mt-3 pt-3 border-t border-indigo-100 text-xs text-indigo-950 font-semibold flex items-center gap-2">
            <span>💡 Güven İlkesi: Tarihlere tıklayarak o güne ait seferleri doğrudan listeleyebilirsiniz.</span>
        </div>
    `;
}

function selectCalendarDate(dateStr) {
    const depInput = document.getElementById('departureDate');
    if (depInput) {
        depInput.value = dateStr;
        handleSearch();
    }
}

async function changeCalendarRange(days) {
    if (currentCalendarRange === days) return;
    currentCalendarRange = days;
    await handleSearch();
}

function filterByTransportMode(mode) {
    currentActiveSummaryFilter = mode;
    currentTransportMode = mode;
    currentCarrierFilter = 'all'; // Sekme değiştiğinde firma filtresini sıfırla

    // Üst sekmeleri senkronize et
    document.querySelectorAll('.transport-tab').forEach(btn => {
        if (btn.dataset.mode === currentActiveSummaryFilter) {
            btn.classList.add('active-tab');
            btn.classList.remove('text-slate-600', 'hover:bg-slate-100');
        } else {
            btn.classList.remove('active-tab');
            btn.classList.add('text-slate-600', 'hover:bg-slate-100');
        }
    });

    renderModelASummary(currentSearchData.summary);
    renderPriceCalendar(currentSearchData.price_calendar, currentSearchData.origin, currentSearchData.destination);
    filterAndRenderTickets('');
}

function filterAndRenderTickets(prefixHtml = '') {
    const ticketsList = document.getElementById('ticketsList');
    if (!currentSearchData || !ticketsList) return;

    const sortFilterBar = document.getElementById('sortFilterBarContainer');
    if (sortFilterBar) {
        if (currentSearchData.transport_type === 'car') {
            sortFilterBar.classList.add('hidden');
        } else {
            sortFilterBar.classList.remove('hidden');
        }
    }

    let list = currentSearchData.tickets || [];
    if (currentActiveSummaryFilter !== 'all') {
        list = list.filter(t => t.transport_type === currentActiveSummaryFilter);
    }

    // Firma filtresi dropdown'unu aktif sonuçlara göre dinamik güncelle
    const carrierSelect = document.getElementById('carrierFilterSelect');
    if (carrierSelect) {
        const uniqueCarriers = Array.from(new Set(list.map(t => t.carrier).filter(Boolean))).sort();
        const prevSelected = currentCarrierFilter;

        carrierSelect.innerHTML = `<option value="all">Tüm Firmalar (${uniqueCarriers.length})</option>`;
        uniqueCarriers.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            if (c === prevSelected) {
                opt.selected = true;
            }
            carrierSelect.appendChild(opt);
        });

        if (prevSelected !== 'all' && !uniqueCarriers.includes(prevSelected)) {
            currentCarrierFilter = 'all';
            carrierSelect.value = 'all';
        } else {
            carrierSelect.value = currentCarrierFilter;
        }
    }

    // Seçili firma filtresini uygula
    if (currentCarrierFilter !== 'all') {
        list = list.filter(t => t.carrier === currentCarrierFilter);
    }

    // Sıralama kriterini uygula
    if (currentSortMode === 'price_asc') {
        list.sort((a, b) => {
            const pA = (a.price != null) ? a.price : 999999;
            const pB = (b.price != null) ? b.price : 999999;
            return pA - pB;
        });
    } else if (currentSortMode === 'dep_asc') {
        list.sort((a, b) => (a.departure_time || '').localeCompare(b.departure_time || ''));
    } else if (currentSortMode === 'dep_desc') {
        list.sort((a, b) => (b.departure_time || '').localeCompare(a.departure_time || ''));
    } else if (currentSortMode === 'dur_asc') {
        list.sort((a, b) => parseDurationToMinutes(a.duration) - parseDurationToMinutes(b.duration));
    }

    // Sıralama butonlarının aktif stilini güncelle
    updateSortButtonsUI();

    // Sefer sayısını güncelle
    const countNum = document.getElementById('resultsCountNum');
    if (countNum) countNum.innerText = list.length;

    const isFx = (currentCurrency && currentCurrency !== 'TRY');
    const fxBannerHtml = isFx ? `
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/80 rounded-xl p-3.5 mb-4 text-xs text-amber-900 font-semibold flex items-start gap-2.5 shadow-2xs">
            <i class="fa-solid fa-coins text-amber-600 text-sm mt-0.5 shrink-0"></i>
            <div>
                <span class="font-extrabold text-amber-950">💱 Döviz & Kur Bilgilendirmesi:</span>
                Tüm yurt içi ve uluslararası biletlerde net fiyatlar doğrudan ilgili sağlayıcı ve havayolu sisteminde teyit edilir. Bankanızın uygulayacağı anlık döviz satış kuru ve kart komisyonuna göre ekstrenize yansıyacak tutarda farklılıklar oluşabilir.
            </div>
        </div>
    ` : '';

    ticketsList.innerHTML = prefixHtml + fxBannerHtml;

    if (list.length === 0) {
        ticketsList.innerHTML += `
            <div class="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
                <div class="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400 text-2xl">
                    <i class="fa-solid fa-route"></i>
                </div>
                <h3 class="text-base font-bold text-slate-800">Bu Filtrede Sefer Bulunamadı</h3>
                <p class="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-5 leading-relaxed">
                    Seçilen kriter veya seyahat türü için doğrudan sefer bulunmamaktadır. Tüm alternatifleri inceleyebilirsiniz.
                </p>
                <button onclick="filterByTransportMode('all')" class="bg-blue-600 text-white font-bold px-4 py-2 rounded-xl text-xs">Tüm Seferleri Göster</button>
            </div>
        `;
        return;
    }

    list.forEach(ticket => {
        let typeBadge = '';
        if (ticket.transport_type === 'flight') {
            typeBadge = `<span class="bg-blue-100 text-blue-800 text-[11px] font-bold px-2 py-0.5 rounded">✈️ Uçuş</span>`;
        } else if (ticket.transport_type === 'train') {
            typeBadge = `<span class="bg-emerald-100 text-emerald-800 text-[11px] font-bold px-2 py-0.5 rounded">🚆 Hızlı Tren</span>`;
        } else if (ticket.transport_type === 'ferry') {
            typeBadge = `<span class="bg-cyan-100 text-cyan-800 text-[11px] font-bold px-2 py-0.5 rounded">⛴️ Feribot / Denizyolu</span>`;
        } else {
            typeBadge = `<span class="bg-amber-100 text-amber-800 text-[11px] font-bold px-2 py-0.5 rounded">🚌 Otobüs</span>`;
        }

        const card = document.createElement('div');
        card.className = 'bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-all flex flex-col md:flex-row md:items-center justify-between gap-4';

        let providersHtml = '';
        if (ticket.providers) {
            providersHtml = ticket.providers.map(p => `
                <a href="${p.url}" target="_blank" class="text-[11px] font-bold ${p.is_best ? 'text-blue-700 bg-blue-50 border-blue-200' : 'text-slate-600 bg-slate-100 border-slate-200'} border px-2.5 py-1 rounded-lg hover:underline flex items-center gap-1.5 shadow-2xs">
                    <span>${p.name}${p.price ? ': ' + p.price.toFixed(2) + ' ' + (ticket.currency || '₺') : ' ↗'}</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                </a>
            `).join('');
        }

        // Seçili bilet ve koltuk seçim sayfasına doğrudan giden öncelikli bağlantı
        const bookingLink = ticket.direct_link || ticket.booking_link || ticket.agent_link || ticket.official_link;
        const officialLink = ticket.official_link || ticket.direct_link;
        let officialName = ticket.official_name || ticket.carrier;
        let brandClean = officialName
            .replace(' Resmi Bilet Ekranı', '')
            .replace(' Resmi Ekranı', '')
            .replace(' Bilet Ekranı', '')
            .replace(' Resmi', '')
            .replace(' Ekranı', '')
            .replace(' Airlines', '')
            .replace(' (AnadoluJet)', '')
            .replace(' Taşımacılık (YHT)', '')
            .replace(' Taşımacılık', '')
            .replace(' Turizm', '')
            .trim();

        const agentLink = ticket.agent_link || ticket.direct_link;
        const agentName = ticket.agent_name || (ticket.transport_type === 'bus' ? 'Obilet' : (ticket.transport_type === 'train' ? 'TCDD E-Bilet' : 'Enuygun'));

        // Birincil aksiyon butonu başlığı (Doğrudan sefer seçim ve koltuk ekranına yönlendirir)
        let actionBtnText = `Bileti Seç & Satın Al ➔`;
        if (ticket.transport_type === 'bus') {
            actionBtnText = `Bileti Al ➔ Obilet (${brandClean})`;
        } else if (ticket.transport_type === 'train') {
            const carr = ticket.carrier.toLowerCase();
            if (carr.includes('eurostar') || carr.includes('frecciarossa') || carr.includes('ice') || carr.includes('trenitalia') || carr.includes('deutsche bahn') || carr.includes('trainline') || carr.includes('ave') || carr.includes('tgv') || carr.includes('sbb')) {
                actionBtnText = `Bileti Al ➔ Trainline / Omio`;
            } else {
                actionBtnText = `Bileti Al ➔ TCDD E-Bilet`;
            }
        } else if (ticket.transport_type === 'ferry') {
            actionBtnText = `Bileti Al ➔ ${brandClean}`;
        } else if (ticket.transport_type === 'flight') {
            if (ticket.carrier.toLowerCase().includes('pegasus')) {
                actionBtnText = `Bileti Al ➔ Pegasus (Canlı Koltuk)`;
            } else if (ticket.carrier.toLowerCase().includes('ajet')) {
                actionBtnText = `Bileti Al ➔ Enuygun / AJet`;
            } else {
                actionBtnText = `Bileti Al ➔ Skyscanner / THY`;
            }
        }

        // İkincil bağlantı: alternatif sağlayıcı veya fiyat grafiği
        let secondaryLinkHtml = '';
        const isOfficialDirect = (bookingLink === officialLink && !officialLink.includes('ajet.com') && !officialLink.includes('pamukkale.com.tr') && !officialLink.includes('kamilkoc.com.tr'));
        
        if (isOfficialDirect) {
            secondaryLinkHtml = `
                <a href="${agentLink}" target="_blank" class="font-semibold text-slate-500 hover:text-blue-600 flex items-center gap-1 transition" title="${agentName} ekranında gör">
                    <span>${agentName}'da da Gör</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                </a>
            `;
        } else if (officialLink && officialLink !== bookingLink) {
            secondaryLinkHtml = `
                <a href="${officialLink}" target="_blank" class="font-semibold text-slate-500 hover:text-blue-600 flex items-center gap-1 transition" title="${brandClean} resmi web sitesi">
                    <span>${brandClean} Resmi Sitesi</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                </a>
            `;
        } else {
            secondaryLinkHtml = `
                <a href="${agentLink}" target="_blank" class="font-semibold text-slate-500 hover:text-blue-600 flex items-center gap-1 transition" title="${agentName} ekranında gör">
                    <span>${agentName}'da da Gör</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                </a>
            `;
        }

        card.innerHTML = `
            <div class="flex-1 space-y-2">
                <div class="flex items-center flex-wrap gap-2">
                    ${typeBadge}
                    <span class="font-extrabold text-slate-900 text-sm">${ticket.carrier}</span>
                    <span class="text-xs text-slate-400 font-semibold">• ${ticket.flight_number}</span>
                    ${ticket.badge ? `<span class="bg-rose-50 text-rose-700 font-bold text-[10px] px-2 py-0.5 rounded-full border border-rose-200">${ticket.badge}</span>` : ''}
                    ${ticket.visa_required ? `<span class="bg-amber-50 text-amber-800 font-bold text-[10px] px-2 py-0.5 rounded-full border border-amber-200">🇪🇺 Kapı Vizesi Gerekir</span>` : ''}
                    ${ticket.cabin_class === 'business' ? `<span class="bg-purple-50 text-purple-700 font-extrabold text-[10px] px-2 py-0.5 rounded-full border border-purple-200"><i class="fa-solid fa-crown text-purple-600 mr-1"></i>Business Class ⭐</span>` : ''}
                    ${ticket.is_night_trip ? `<span class="bg-indigo-50 text-indigo-700 font-bold text-[10px] px-2 py-0.5 rounded-full border border-indigo-200">🌙 Otel Tasarruflu</span>` : ''}
                </div>

                ${ticket.route_notice ? `<div class="text-[11px] font-bold text-amber-900 bg-amber-50 px-2.5 py-1.5 rounded-lg border border-amber-200 flex items-center gap-1.5"><i class="fa-solid fa-circle-info text-amber-600"></i> ${ticket.route_notice}</div>` : ''}

                <div class="flex items-center gap-4 sm:gap-6 pt-1">
                    <div>
                        <div class="text-[11px] text-slate-500 font-bold mb-0.5">${ticket.departure_date_formatted || currentSearchData.date}</div>
                        <div class="text-xl font-black text-slate-900">${ticket.departure_time}</div>
                        <div class="text-xs text-slate-500 font-semibold">${ticket.origin}</div>
                    </div>

                    <div class="flex flex-col items-center">
                        <span class="text-[10px] font-bold text-slate-400">${ticket.duration}</span>
                        <div class="w-16 sm:w-20 h-0.5 bg-slate-300 relative my-1">
                            <i class="fa-solid ${ticket.transport_type === 'flight' ? 'fa-plane' : ticket.transport_type === 'train' ? 'fa-train' : ticket.transport_type === 'ferry' ? 'fa-ship text-cyan-600' : 'fa-bus'} text-[10px] absolute -top-1.5 left-1/2 -translate-x-1/2 bg-white px-0.5"></i>
                        </div>
                        <span class="text-[10px] font-semibold text-emerald-600">${ticket.is_direct ? 'Aktarmasız' : 'Aktarmalı'}</span>
                    </div>

                    <div>
                        <div class="text-[11px] text-slate-500 font-bold mb-0.5 flex items-center gap-1">
                            <span>${ticket.arrival_date_formatted || currentSearchData.date}</span>
                            ${ticket.is_next_day ? `<span class="bg-indigo-100 text-indigo-700 font-black text-[9px] px-1.5 py-0.2 rounded-full border border-indigo-200">+1 Gün</span>` : ''}
                        </div>
                        <div class="text-xl font-black text-slate-900 flex items-center gap-1.5">
                            <span>${ticket.arrival_time}</span>
                            ${ticket.is_next_day ? `<span class="text-xs font-black text-indigo-600">(+1 Gün)</span>` : ''}
                        </div>
                        <div class="text-xs text-slate-500 font-semibold">${ticket.destination}</div>
                    </div>
                </div>

                <div class="flex flex-wrap gap-2 pt-2">
                    ${providersHtml}
                </div>
            </div>

            <div class="flex flex-col md:items-end justify-between border-t md:border-t-0 md:border-l border-slate-100 pt-3 md:pt-0 md:pl-6 gap-3 min-w-[220px]">
                <!-- Tıklanabilir Fiyat Alanı: Doğrudan Bilet Sayfasına Gider -->
                <a href="${bookingLink}" target="_blank" class="block group text-left md:text-right w-full cursor-pointer hover:opacity-90 transition">
                    ${(ticket.has_live_price && ticket.price != null) ? `
                        ${ticket.regular_price ? `<div class="text-xs text-slate-400 line-through font-semibold">${ticket.regular_price.toLocaleString('tr-TR', {minimumFractionDigits: 0, maximumFractionDigits: 2})} ${ticket.currency || '₺'}</div>` : ''}
                        <div class="text-2xl sm:text-3xl font-black text-emerald-600 tracking-tight group-hover:text-emerald-700">${ticket.price.toLocaleString('tr-TR', {minimumFractionDigits: 0, maximumFractionDigits: 2})} ${ticket.currency || '₺'}</div>
                        <div class="text-[10px] text-emerald-700 font-extrabold flex items-center md:justify-end gap-1">
                            <i class="fa-solid fa-circle-check text-emerald-600"></i> ${ticket.price_status_text || 'Doğrulanmış Fiyat'}
                        </div>
                    ` : `
                        <div class="text-xl font-black text-blue-700 group-hover:text-blue-800">Canlı Fiyat & Koltuk ↗</div>
                        <div class="text-[10px] text-slate-400 font-semibold mt-0.5">Net ücret sağlayıcıda doğrulanır</div>
                    `}
                </a>

                <!-- Doğrudan Bilet Alma ve Koltuk Seçim Butonu -->
                <div class="w-full space-y-2">
                    <a href="${bookingLink}" target="_blank" class="w-full bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-700 hover:from-emerald-700 hover:to-teal-800 text-white font-black text-xs sm:text-sm py-2.5 px-3 rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 hover:shadow-lg transition">
                        <span>${actionBtnText}</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>

                    <!-- Alt Satır: Alternatif Bağlantı & Fiyat Alarmı -->
                    <div class="flex items-center justify-between px-1 text-xs pt-0.5">
                        ${secondaryLinkHtml}
                        <button onclick="openTrackModalWithData('${ticket.origin}', '${ticket.destination}', ${ticket.price || 0}, '${currentSearchData.date}')" class="font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 transition" title="Bu rota için fiyat alarmı kur">
                            <i class="fa-solid fa-bell text-[10px]"></i>
                            <span>Fiyat Alarmı</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        ticketsList.appendChild(card);
    });
}

// ==================== MODÜL 6: ARAÇ KİRALAMA KARTLARI ÇİZİMİ ====================

function renderCarRentalCards(carData) {
    const ticketsList = document.getElementById('ticketsList');
    if (!ticketsList || !carData || !carData.vehicles) return;

    const locType = carData.location_type_label || '🏙️ Şehir Merkezi & İlçe';
    const currSym = carData.currency || getCurrencySymbol(currentCurrency);

    ticketsList.innerHTML = `
        <div class="bg-gradient-to-r from-indigo-50 via-blue-50 to-slate-50 border border-indigo-200 text-slate-800 rounded-2xl p-4 mb-4 text-xs font-semibold flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
            <div class="flex items-center gap-2.5">
                <i class="fa-solid fa-car text-indigo-600 text-base"></i>
                <span>Tüm fiyatlar ${carData.days_count} günlük kiralama için hesaplanmıştır. Sınırsız kilometre ve standart kasko dahildir.</span>
            </div>
            <div class="flex items-center gap-2 self-start sm:self-auto">
                <span class="bg-white border border-indigo-200 px-3 py-1 rounded-xl text-indigo-900 font-extrabold">${carData.location}</span>
                <span class="bg-indigo-600 text-white px-3 py-1 rounded-xl font-bold">${locType}</span>
            </div>
        </div>
    `;

    carData.vehicles.forEach(car => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-all flex flex-col lg:flex-row lg:items-start justify-between gap-5';

        card.innerHTML = `
            <div class="flex-1 space-y-3">
                <div class="flex items-center flex-wrap gap-2">
                    <span class="bg-indigo-100 text-indigo-800 text-[11px] font-bold px-2 py-0.5 rounded">${car.image_icon} ${car.category}</span>
                    <span class="font-extrabold text-slate-900 text-base">${car.car_model}</span>
                    <span class="bg-amber-50 text-amber-700 font-bold text-[10px] px-2 py-0.5 rounded-full border border-amber-200">${car.badge}</span>
                </div>

                <div class="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-600">
                    <span class="flex items-center gap-1 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100 font-semibold">
                        <i class="fa-solid fa-gear text-slate-400"></i> ${car.transmission}
                    </span>
                    <span class="flex items-center gap-1 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100 font-semibold">
                        <i class="fa-solid fa-gas-pump text-slate-400"></i> ${car.fuel}
                    </span>
                    <span class="flex items-center gap-1 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100 font-semibold">
                        <i class="fa-solid fa-users text-slate-400"></i> ${car.seats} Kişilik
                    </span>
                    <span class="flex items-center gap-1 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100 font-semibold">
                        <i class="fa-solid fa-suitcase text-slate-400"></i> ${car.luggage}
                    </span>
                    <span class="flex items-center gap-1 bg-emerald-50 text-emerald-800 px-2.5 py-1 rounded-lg border border-emerald-100 font-bold">
                        <i class="fa-solid fa-road text-emerald-600"></i> Sınırsız Km
                    </span>
                </div>

                <div class="text-[11px] text-slate-500 font-medium pt-1 flex items-center flex-wrap gap-2">
                    <span class="flex items-center gap-1 text-slate-800 font-bold bg-slate-100 px-2.5 py-1 rounded-lg">
                        <i class="fa-solid fa-location-dot text-indigo-600"></i> ${car.pickup_point}
                    </span>
                    <span class="text-slate-300">•</span>
                    <span class="text-slate-500 font-medium">${car.deposit}</span>
                    <span class="text-slate-300">•</span>
                    <span class="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded">Standart Kasko Dahil</span>
                </div>
            </div>

            <!-- Sağ Taraf: Şeffaf Firma Fiyat Karşılaştırması -->
            <div class="flex flex-col justify-between border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6 gap-3 w-full lg:w-[360px] flex-shrink-0">
                <!-- En İyi Teklif Özeti -->
                <div class="w-full bg-emerald-50/80 border border-emerald-200 rounded-2xl p-3 flex items-center justify-between">
                    <div>
                        <div class="text-[10px] font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1">
                            <span>🏆 EN UCUZ SAĞLAYICI</span>
                        </div>
                        <div class="text-sm font-black text-slate-900">${car.cheapest_provider_name || 'En İyi Fiyat'}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-black text-emerald-600">${car.daily_price.toFixed(0)} ${currSym} <span class="text-xs text-slate-500 font-semibold">/ gün</span></div>
                        <div class="text-[11px] text-slate-500 font-bold">${car.total_price.toFixed(0)} ${currSym} Toplam (${carData.days_count} Gün)</div>
                    </div>
                </div>

                <!-- Şeffaf Firma Listesi (Fiyatına Göre Sıralı) -->
                <div class="w-full space-y-1.5">
                    <div class="text-[11px] font-bold text-slate-600 flex items-center justify-between px-1">
                        <span>Firma Fiyat Karşılaştırması:</span>
                        <span class="text-[10px] text-emerald-600 font-extrabold">En Ucuzdan Pahalıya ↓</span>
                    </div>

                    <div class="space-y-1.5 w-full">
                        ${(car.providers || []).map(p => `
                            <a href="${p.url}" target="_blank" class="flex items-center justify-between px-3 py-2 rounded-xl border ${p.is_cheapest ? 'border-emerald-500 bg-emerald-50/50 hover:bg-emerald-100/70 shadow-sm' : 'border-slate-200 bg-white hover:bg-slate-50'} transition group">
                                <div class="flex items-center gap-2">
                                    <span class="font-extrabold text-xs text-slate-900">${p.name}</span>
                                    ${p.is_cheapest ? '<span class="bg-emerald-600 text-white text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-wide">🏆 En Ucuz</span>' : `<span class="text-[10px] text-slate-400 font-semibold">${p.badge}</span>`}
                                </div>
                                <div class="flex items-center gap-2.5">
                                    <div class="text-right">
                                        <span class="text-xs font-black ${p.is_cheapest ? 'text-emerald-700' : 'text-slate-800'}">${p.daily_price.toFixed(0)} ${currSym}</span>
                                        <span class="text-[10px] text-slate-400 block -mt-1">/gün</span>
                                    </div>
                                    <span class="${p.is_cheapest ? 'bg-emerald-600 group-hover:bg-emerald-700' : 'bg-slate-800 group-hover:bg-slate-900'} text-white text-[11px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1 transition shadow-sm whitespace-nowrap">
                                        <span>Kirala</span>
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>
                                    </span>
                                </div>
                            </a>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        ticketsList.appendChild(card);
    });
}

// ==================== MODÜL 2: FİYAT TAKİBİ ====================

function openTrackModal() {
    const origin = document.getElementById('originCity').value;
    const dest = document.getElementById('destCity').value;
    const depDate = document.getElementById('departureDate').value;

    openTrackModalWithData(origin, dest, 500, depDate);
}

function openTrackModalWithData(origin, dest, currentPrice, depDate) {
    document.getElementById('trackOrigin').value = origin;
    document.getElementById('trackDest').value = dest;
    document.getElementById('trackTargetPrice').value = Math.max(100, Math.floor(currentPrice * 0.85));
    document.getElementById('trackDate').value = depDate || new Date().toISOString().split('T')[0];

    document.getElementById('trackModal').classList.remove('hidden');
}

function quickTrackFromDeal(origin, dest, dealPrice, transportType) {
    const target = Math.max(100, Math.floor(dealPrice * 0.9));
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 7);
    openTrackModalWithData(origin, dest, dealPrice, tomorrow.toISOString().split('T')[0]);
}

function closeTrackModal() {
    document.getElementById('trackModal').classList.add('hidden');
}

async function handleSaveTracker(e) {
    e.preventDefault();
    const origin = document.getElementById('trackOrigin').value;
    const dest = document.getElementById('trackDest').value;
    const targetPrice = parseFloat(document.getElementById('trackTargetPrice').value);
    const date = document.getElementById('trackDate').value;
    const email = document.getElementById('trackEmail').value;

    const channels = [];
    if (document.getElementById('channelEmail').checked) channels.push('email');
    if (document.getElementById('channelPush').checked) channels.push('push');
    if (document.getElementById('channelTelegram').checked) channels.push('telegram');

    const btn = document.getElementById('saveTrackerBtn');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Takip Başlatılıyor...`;

    try {
        const res = await fetch('/api/trackers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin_city: origin,
                destination_city: dest,
                target_price: targetPrice,
                travel_date_start: date,
                channels: channels,
                user_email: email
            })
        });

        const data = await res.json();
        if (data.success) {
            closeTrackModal();
            showToast(`🎉 ${origin} → ${dest} rotası takibe alındı! Fiyat ${targetPrice} ${getCurrencySymbol(currentCurrency)} altına düşerse bildireceğiz.`);
        }
    } catch (err) {
        console.error(err);
        showToast('Takip başlatılamadı.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-check"></i> Takibi Başlat ve Nöbete Geç`;
    }
}

// ==================== MODÜL 3 & 4: TEST & DASHBOARD ====================

function requestPushPermission() {
    if (!('Notification' in window)) {
        showToast('Bu tarayıcı bildirimleri desteklemiyor.', 'error');
        return;
    }

    Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
            document.getElementById('pushBanner').style.display = 'none';
            showToast('✅ Tarayıcı bildirimlerine başarıyla izin verildi!');
            new Notification('Hakiki Bilet — Bildirimler Aktif!', {
                body: 'Hakiki Fiyat, Hakiki Bilet! Flaş indirimler ve hedef fiyat uyarıları anında ekranınızda.',
                icon: '/static/img/favicon.png'
            });
        } else {
            showToast('Bildirim izni reddedildi.', 'error');
        }
    });
}

async function testNotificationChannel(channel) {
    showToast(`${channel.toUpperCase()} bildirimi gönderiliyor...`);
    try {
        const res = await fetch('/api/notifications/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                channel: channel,
                route: "İstanbul → Ankara",
                price: 299.00,
                regular_price: 650.00,
                link: "https://www.enuygun.com"
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${channel.toUpperCase()} bildirimi başarıyla tetiklendi!`);

            if (channel === 'push' && 'Notification' in window && Notification.permission === 'granted') {
                new Notification('🎉 FIRSAT ALARMI: İstanbul → Ankara', {
                    body: 'Bilet fiyatı 299 ₺ oldu! (Eski Fiyat: 650 ₺)',
                    icon: '/static/icons/ticket.png'
                });
            }
        }
    } catch (err) {
        showToast('Bildirim testi başarısız oldu.', 'error');
    }
}

async function triggerCronNow() {
    showToast('⏰ Arka plan zamanlayıcısı (Cron) çalıştırılıyor...');
    try {
        const res = await fetch('/api/cron/trigger', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('✅ Fiyat ve kampanya taraması tamamlandı! Rotalar kontrol edildi.');
            setTimeout(() => { location.reload(); }, 1200);
        }
    } catch (err) {
        showToast('Cron tetiklenemedi.', 'error');
    }
}

async function toggleRoute(id, newStatus) {
    try {
        const res = await fetch(`/api/trackers/${id}/toggle?is_active=${Boolean(newStatus)}`, { method: 'PUT' });
        const data = await res.json();
        if (data.success) {
            showToast('Rota durumu güncellendi.');
            location.reload();
        }
    } catch (err) {
        showToast('Durum güncellenemedi.', 'error');
    }
}

async function deleteRoute(id) {
    if (!confirm('Bu rotayı takipten çıkarmak istediğinize emin misiniz?')) return;
    try {
        const res = await fetch(`/api/trackers/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            const row = document.getElementById(`route-row-${id}`);
            if (row) row.remove();
            showToast('Rota takipten çıkarıldı.');
        }
    } catch (err) {
        showToast('Silinemedi.', 'error');
    }
}

// ==================== MODÜL 5: KAMPANYA & FIRSAT RADARI ====================

let currentDealsTab = 'radar';
let currentDealsFilter = 'all';

function switchDealsTab(tabName) {
    currentDealsTab = tabName;
    const radarBtn = document.getElementById('tabRadarBtn');
    const annBtn = document.getElementById('tabAnnouncementsBtn');
    const radarGrid = document.getElementById('radarGrid');
    const annGrid = document.getElementById('announcementsGrid');
    const subheaderText = document.getElementById('dealsSubheaderText');

    if (tabName === 'radar') {
        if (radarBtn) radarBtn.className = 'px-4 py-2 rounded-xl text-xs font-extrabold transition bg-white text-blue-700 shadow-sm flex items-center gap-2';
        if (annBtn) annBtn.className = 'px-4 py-2 rounded-xl text-xs font-extrabold text-slate-600 hover:text-slate-900 transition flex items-center gap-2';
        if (radarGrid) radarGrid.classList.remove('hidden');
        if (annGrid) annGrid.classList.add('hidden');
        if (subheaderText) subheaderText.innerText = 'Tüm biletler 30-90 gün sonrası için doğrulanmış satın alınabilir gerçek indirimli seferlerdir.';
    } else {
        if (annBtn) annBtn.className = 'px-4 py-2 rounded-xl text-xs font-extrabold transition bg-white text-rose-700 shadow-sm flex items-center gap-2';
        if (radarBtn) radarBtn.className = 'px-4 py-2 rounded-xl text-xs font-extrabold text-slate-600 hover:text-slate-900 transition flex items-center gap-2';
        if (radarGrid) radarGrid.classList.add('hidden');
        if (annGrid) annGrid.classList.remove('hidden');
        if (subheaderText) subheaderText.innerText = 'Pegasus, THY, AJet, TCDD ve Obilet resmi kampanya koşulları ve katılım sayfaları listelenir.';
    }

    applyDealsFilter();
}

function filterDeals(type) {
    currentDealsFilter = type;
    document.querySelectorAll('.deal-filter-btn').forEach(b => {
        b.classList.remove('active-filter');
        b.classList.add('text-slate-600', 'hover:bg-slate-100');
    });
    if (event && event.target) {
        event.target.classList.add('active-filter');
        event.target.classList.remove('text-slate-600', 'hover:bg-slate-100');
    }

    applyDealsFilter();
}

function applyDealsFilter() {
    const activeGridId = (currentDealsTab === 'radar') ? 'radarGrid' : 'announcementsGrid';
    const activeGrid = document.getElementById(activeGridId);
    if (!activeGrid) return;

    activeGrid.querySelectorAll('.deal-card').forEach(card => {
        if (currentDealsFilter === 'all' || card.dataset.type === currentDealsFilter) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}
