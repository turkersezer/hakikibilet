// Ucuz Bilet Bul — Frontend Core Application

let currentTransportMode = 'all';
let currentTripType = 'one_way'; // 'one_way' or 'round_trip'
let currentSearchData = null;
let currentActiveSummaryFilter = 'all';
let currentCalendarRange = 7; // 7, 15, or 30 days

document.addEventListener('DOMContentLoaded', () => {
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
    } else {
        oneWayBtn.className = 'px-4 py-1.5 rounded-lg text-xs font-bold transition bg-white text-blue-700 shadow-sm';
        roundBtn.className = 'px-4 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition';
        if (returnContainer) {
            returnContainer.classList.add('hidden');
        }
    }
}

// ==================== MODÜL 1: DİNAMİK İSTASYON & ARAMA ====================

function updateCityDropdowns(mode) {
    const originSelect = document.getElementById('originCity');
    const destSelect = document.getElementById('destCity');
    const originLabel = document.getElementById('originLabel');
    const destLabel = document.getElementById('destLabel');
    const modeStatusLabel = document.getElementById('modeStatusLabel');

    if (!window.ALL_CITIES || !originSelect || !destSelect) return;

    const currentOrigin = originSelect.value;
    const currentDest = destSelect.value;

    let filteredCities = window.ALL_CITIES;
    let originLabelHtml = '<i class="fa-solid fa-location-dot text-blue-600 mr-1"></i> Kalkış Şehri / İstasyonu';
    let destLabelHtml = '<i class="fa-solid fa-location-arrow text-indigo-600 mr-1"></i> Varış Şehri / İstasyonu';
    let statusText = 'Tüm seyahat alternatifleri (Uçak, Tren, Otobüs) karşılaştırmalı olarak listelenir.';

    if (mode === 'train') {
        filteredCities = window.ALL_CITIES.filter(c => c.has_train);
        originLabelHtml = '<i class="fa-solid fa-train text-emerald-600 mr-1"></i> Kalkış Tren Garı (TCDD)';
        destLabelHtml = '<i class="fa-solid fa-train text-emerald-600 mr-1"></i> Varış Tren Garı (TCDD)';
        statusText = '🚆 <strong>TCDD Tren Modu:</strong> Yalnızca aktif demiryolu ve TCDD garı olan iller listeleniyor (Örn: Ankara YHT Garı, İstanbul, Konya, Eskişehir, Sivas vb.).';
    } else if (mode === 'flight') {
        filteredCities = window.ALL_CITIES.filter(c => c.has_airport);
        originLabelHtml = '<i class="fa-solid fa-plane-departure text-blue-600 mr-1"></i> Kalkış Havalimanı';
        destLabelHtml = '<i class="fa-solid fa-plane-arrival text-blue-600 mr-1"></i> Varış Havalimanı';
        statusText = '✈️ <strong>Uçak Modu:</strong> Yalnızca aktif yolcu havalimanı bulunan iller listeleniyor (Örn: Bodrum BJV, İstanbul, Antalya, İzmir vb.).';
    } else if (mode === 'bus') {
        filteredCities = window.ALL_CITIES;
        originLabelHtml = '<i class="fa-solid fa-bus text-amber-600 mr-1"></i> Kalkış Otogarı';
        destLabelHtml = '<i class="fa-solid fa-bus text-amber-600 mr-1"></i> Varış Otogarı';
        statusText = '🚌 <strong>Otobüs Modu:</strong> Türkiye\'nin tüm 81 ili ve ilçe otogarları listeleniyor.';
    }

    if (originLabel) originLabel.innerHTML = originLabelHtml;
    if (destLabel) destLabel.innerHTML = destLabelHtml;
    if (modeStatusLabel) modeStatusLabel.innerHTML = statusText;

    originSelect.innerHTML = '';
    destSelect.innerHTML = '';

    // Gezgin Seçeneği: Her Yere / Farketmez seçeneğini varış kutusuna ekle
    const anywhereOpt = new Option("🌍 Her Yere / Farketmez (En Ucuz Rota)", "Her Yere");
    destSelect.add(anywhereOpt);

    filteredCities.forEach(c => {
        let text = c.name;
        if (mode === 'train') {
            text = `${c.name} — ${c.train_station || 'TCDD Garı'}`;
        } else if (mode === 'flight') {
            text = `${c.name} (${c.iata || 'Havalimanı'})`;
        } else if (mode === 'bus') {
            text = `${c.name} Otogarı`;
        } else {
            text = `${c.name} ${c.iata ? '(' + c.iata + ')' : ''}`;
        }

        const opt1 = new Option(text, c.name);
        const opt2 = new Option(text, c.name);

        originSelect.add(opt1);
        destSelect.add(opt2);
    });

    const hasOrigin = filteredCities.some(c => c.name === currentOrigin);
    const hasDest = (currentDest === "Her Yere") || filteredCities.some(c => c.name === currentDest);

    if (hasOrigin) {
        originSelect.value = currentOrigin;
    } else {
        originSelect.value = filteredCities[0]?.name || 'İstanbul';
        if (currentOrigin && mode === 'train') {
            showToast(`ℹ️ ${currentOrigin} bölgesinde TCDD tren hattı bulunmadığı için istasyon listesi TCDD seferlerine göre ayarlandı.`, 'info');
        }
    }

    if (hasDest && (currentDest === "Her Yere" || originSelect.value !== currentDest)) {
        destSelect.value = currentDest;
    } else {
        const altCity = filteredCities.find(c => c.name !== originSelect.value);
        destSelect.value = altCity ? altCity.name : (filteredCities[1]?.name || 'Ankara');
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

    updateCityDropdowns(mode);

    if (currentSearchData) {
        renderModelASummary(currentSearchData.summary);
        renderPriceCalendar(currentSearchData.price_calendar, currentSearchData.origin, currentSearchData.destination);
        filterAndRenderTickets('');
    }
}

async function handleSearch(e) {
    if (e && e.preventDefault) e.preventDefault();
    const origin = document.getElementById('originCity').value;
    const dest = document.getElementById('destCity').value;
    const depDate = document.getElementById('departureDate').value;
    const retDate = (currentTripType === 'round_trip') ? document.getElementById('returnDate').value : null;
    const passengers = parseInt(document.getElementById('passengers').value) || 1;
    const nightOnly = document.getElementById('nightOnlyCheck') ? document.getElementById('nightOnlyCheck').checked : false;
    const cabinClass = document.getElementById('cabinClass') ? document.getElementById('cabinClass').value : 'economy';

    if (dest !== 'Her Yere' && origin === dest) {
        showToast('Kalkış ve varış şehri aynı olamaz!', 'error');
        return;
    }

    if (currentTripType === 'round_trip' && retDate && retDate < depDate) {
        showToast('Dönüş tarihi gidiş tarihinden önce olamaz!', 'error');
        return;
    }

    const submitBtn = document.getElementById('searchSubmitBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Aranıyor...`;
    }

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
                transport_type: currentTransportMode,
                cabin_class: cabinClass,
                calendar_range: currentCalendarRange,
                night_only: nightOnly
            })
        });

        const data = await res.json();
        currentSearchData = data;
        renderSearchResults(data);

        document.getElementById('searchResultsSection').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        console.error(err);
        showToast('Arama sırasında hata oluştu.', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Bilet Ara`;
        }
    }
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

    section.classList.remove('hidden');
    
    const tripLabel = data.trip_type === 'round_trip' ? 'Gidiş - Dönüş' : 'Tek Yön';
    title.innerText = `${data.origin} → ${data.destination} Seferleri`;
    subtitle.innerText = `${data.date}${data.return_date ? ' - ' + data.return_date : ''} • ${tripLabel} • ${data.passengers} Yolcu • ${data.results_count} Sefer Bulundu`;

    // 1. MODEL A: ULAŞIM TÜRÜNE GÖRE ÖZET KARTLARI (TABS)
    renderModelASummary(data.summary);

    // 2. ESNEK TARİH & EN UCUZ GÜNÜ BUL (FİYAT TAKVİMİ)
    renderPriceCalendar(data.price_calendar, data.origin, data.destination);

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
        trainLinksHtml = `
            <a href="${links.train.tcdd}" target="_blank" class="inline-flex items-center gap-1.5 bg-white hover:bg-rose-50 text-rose-800 border border-rose-300 font-bold px-3 py-1.5 rounded-lg text-xs shadow-sm transition">
                <span>TCDD E-Bilet</span>
                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
        `;
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

    deepLinksContainer.innerHTML = flightLinksHtml + trainLinksHtml + busLinksHtml;

    // 5. Bilet Listesi
    filterAndRenderTickets(noticesHtml);
}

// MODEL A: ÖZET KARTLARININ ÇİZİMİ
function renderModelASummary(summary) {
    const container = document.getElementById('modelASummaryContainer');
    if (!container || !summary) return;

    const f = summary.flight;
    const t = summary.train;
    const b = summary.bus;

    container.innerHTML = `
        <!-- Uçak Kartı -->
        <div onclick="filterByTransportMode('flight')" class="cursor-pointer bg-white rounded-2xl border ${currentActiveSummaryFilter === 'flight' ? 'border-blue-600 ring-2 ring-blue-500/20 shadow-md' : 'border-slate-200'} p-5 transition hover:shadow-lg flex flex-col justify-between ${!f.available ? 'opacity-60 bg-slate-50 cursor-not-allowed' : ''}">
            <div class="flex items-center justify-between mb-3">
                <span class="font-bold text-sm text-slate-800 flex items-center gap-2">
                    <span class="text-xl">✈️</span> UÇAK BİLETİ
                </span>
                ${f.available ? `<span class="bg-blue-50 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full">${f.count} Sefer</span>` : `<span class="bg-rose-50 text-rose-700 text-[10px] font-bold px-2 py-0.5 rounded">Havalimanı Yok</span>`}
            </div>
            ${f.available ? `
                <div class="flex items-baseline justify-between mt-2">
                    <div>
                        <span class="text-[11px] text-slate-400 font-semibold block">En Ucuz Fiyat</span>
                        <span class="text-2xl font-black text-emerald-600">${f.min_price?.toFixed(2)} ₺</span>
                    </div>
                    <div class="text-right">
                        <span class="text-[11px] text-slate-400 font-semibold block">En Hızlı</span>
                        <span class="text-xs font-bold text-slate-700">${f.min_duration}</span>
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
                ${t.available ? `<span class="bg-emerald-50 text-emerald-700 text-xs font-bold px-2 py-0.5 rounded-full">${t.count} Sefer</span>` : `<span class="bg-rose-50 text-rose-700 text-[10px] font-bold px-2 py-0.5 rounded">Tren Hattı Yok</span>`}
            </div>
            ${t.available ? `
                <div class="flex items-baseline justify-between mt-2">
                    <div>
                        <span class="text-[11px] text-slate-400 font-semibold block">En Ucuz Fiyat</span>
                        <span class="text-2xl font-black text-emerald-600">${t.min_price?.toFixed(2)} ₺</span>
                    </div>
                    <div class="text-right">
                        <span class="text-[11px] text-slate-400 font-semibold block">Süre</span>
                        <span class="text-xs font-bold text-slate-700">${t.min_duration}</span>
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
                <span class="bg-amber-50 text-amber-800 text-xs font-bold px-2 py-0.5 rounded-full">${b.count} Sefer</span>
            </div>
            <div class="flex items-baseline justify-between mt-2">
                <div>
                    <span class="text-[11px] text-slate-400 font-semibold block">En Ucuz Fiyat</span>
                    <span class="text-2xl font-black text-emerald-600">${b.min_price?.toFixed(2)} ₺</span>
                </div>
                <div class="text-right">
                    <span class="text-[11px] text-slate-400 font-semibold block">Süre</span>
                    <span class="text-xs font-bold text-slate-700">${b.min_duration}</span>
                </div>
            </div>
        </div>
    `;
}

// ESNEK FİYAT TAKVİMİNİN ÇİZİMİ (TASARIM A: Kategori Şampiyonları & Çoklu Gün)
function renderPriceCalendar(calendarData, origin, dest) {
    const container = document.getElementById('priceCalendarContainer');
    if (!container || !calendarData || !calendarData.days) return;

    const days = calendarData.days;
    const activeMode = currentActiveSummaryFilter; // 'all', 'flight', 'train', 'bus'
    const daysCount = calendarData.range_type || currentCalendarRange || 7;

    const daysHtml = days.map(d => {
        let cardContentHtml = '';

        if (activeMode === 'flight') {
            // Sadece Uçak Modu Seçiliyken
            cardContentHtml = `
                <div class="my-2 py-1 text-center">
                    ${d.has_flight ? `
                        <div class="text-base sm:text-lg font-black ${d.is_cheapest_flight ? 'text-emerald-600' : 'text-slate-900'}">${d.prices.flight} ₺</div>
                        <div class="text-[10px] font-bold text-slate-400">✈️ Uçuş</div>
                        ${d.is_cheapest_flight ? `<div class="mt-1 inline-block bg-emerald-100 text-emerald-800 text-[9px] font-extrabold px-1.5 py-0.5 rounded-md">🔥 EN UCUZ</div>` : ''}
                    ` : `
                        <div class="text-xs font-bold text-slate-400 py-2">Uçuş Yok</div>
                    `}
                </div>
            `;
        } else if (activeMode === 'train') {
            // Sadece Tren Modu Seçiliyken
            cardContentHtml = `
                <div class="my-2 py-1 text-center">
                    ${d.has_train ? `
                        <div class="text-base sm:text-lg font-black ${d.is_cheapest_train ? 'text-blue-600' : 'text-slate-900'}">${d.prices.train} ₺</div>
                        <div class="text-[10px] font-bold text-slate-400">🚆 Tren</div>
                        ${d.is_cheapest_train ? `<div class="mt-1 inline-block bg-blue-100 text-blue-800 text-[9px] font-extrabold px-1.5 py-0.5 rounded-md">🔥 EN UCUZ</div>` : ''}
                    ` : `
                        <div class="text-xs font-bold text-slate-400 py-2">Tren Yok</div>
                    `}
                </div>
            `;
        } else if (activeMode === 'bus') {
            // Sadece Otobüs Modu Seçiliyken
            cardContentHtml = `
                <div class="my-2 py-1 text-center">
                    ${d.has_bus ? `
                        <div class="text-base sm:text-lg font-black ${d.is_cheapest_bus ? 'text-amber-600' : 'text-slate-900'}">${d.prices.bus} ₺</div>
                        <div class="text-[10px] font-bold text-slate-400">🚌 Otobüs</div>
                        ${d.is_cheapest_bus ? `<div class="mt-1 inline-block bg-amber-100 text-amber-800 text-[9px] font-extrabold px-1.5 py-0.5 rounded-md">🔥 EN UCUZ</div>` : ''}
                    ` : `
                        <div class="text-xs font-bold text-slate-400 py-2">Sefer Yok</div>
                    `}
                </div>
            `;
        } else {
            // TASARIM A: TÜMÜ MODU (Mini Özet Kartı - 3 Satır & Kategori Şampiyonları)
            cardContentHtml = `
                <div class="space-y-1 my-1.5 text-left text-xs w-full">
                    <!-- Uçak Satırı -->
                    <div class="flex items-center justify-between px-1.5 py-0.5 rounded ${d.is_cheapest_flight ? 'bg-emerald-100/90 text-emerald-900 font-black ring-1 ring-emerald-300' : 'text-slate-700 font-medium'}">
                        <span class="flex items-center gap-1 text-[11px]"><i class="fa-solid fa-plane text-[10px] text-blue-600"></i> Uçak:</span>
                        <div class="flex items-center gap-1">
                            <span class="font-bold text-[11px]">${d.has_flight ? d.prices.flight + ' ₺' : '-'}</span>
                            ${d.is_cheapest_flight ? `<span class="bg-emerald-600 text-white text-[8px] font-black px-1 rounded" title="Dönemin en ucuz uçuş günü">🔥</span>` : ''}
                        </div>
                    </div>

                    <!-- Tren Satırı -->
                    <div class="flex items-center justify-between px-1.5 py-0.5 rounded ${d.is_cheapest_train ? 'bg-blue-100/90 text-blue-900 font-black ring-1 ring-blue-300' : 'text-slate-700 font-medium'}">
                        <span class="flex items-center gap-1 text-[11px]"><i class="fa-solid fa-train text-[10px] text-emerald-600"></i> Tren:</span>
                        <div class="flex items-center gap-1">
                            <span class="font-bold text-[11px]">${d.has_train ? d.prices.train + ' ₺' : '-'}</span>
                            ${d.is_cheapest_train ? `<span class="bg-blue-600 text-white text-[8px] font-black px-1 rounded" title="Dönemin en ucuz tren günü">🔥</span>` : ''}
                        </div>
                    </div>

                    <!-- Otobüs Satırı -->
                    <div class="flex items-center justify-between px-1.5 py-0.5 rounded ${d.is_cheapest_bus ? 'bg-amber-100/90 text-amber-900 font-black ring-1 ring-amber-300' : 'text-slate-700 font-medium'}">
                        <span class="flex items-center gap-1 text-[11px]"><i class="fa-solid fa-bus text-[10px] text-amber-600"></i> Otobüs:</span>
                        <div class="flex items-center gap-1">
                            <span class="font-bold text-[11px]">${d.has_bus ? d.prices.bus + ' ₺' : '-'}</span>
                            ${d.is_cheapest_bus ? `<span class="bg-amber-600 text-white text-[8px] font-black px-1 rounded" title="Dönemin en ucuz otobüs günü">🔥</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }

        const isOverall = d.is_overall_cheapest && activeMode === 'all';
        const isSelected = d.is_selected;

        return `
            <button type="button" onclick="selectCalendarDate('${d.date}')" class="min-w-[135px] max-w-[155px] p-2.5 rounded-2xl border transition flex flex-col justify-between text-center relative ${isSelected ? 'bg-blue-50/95 border-blue-600 ring-2 ring-blue-500/30 shadow-md' : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-sm'}">
                ${isOverall ? `<div class="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-amber-500 to-rose-500 text-white text-[9px] font-black px-2 py-0.5 rounded-full shadow-sm whitespace-nowrap">👑 EN UCUZ GÜN</div>` : ''}
                
                <div class="flex items-center justify-between border-b border-slate-100 pb-1 mb-1">
                    <span class="text-[11px] font-extrabold uppercase ${d.is_weekend ? 'text-rose-600' : 'text-slate-500'}">${d.day_name}</span>
                    <span class="text-xs font-black text-slate-800">${d.day_num} ${d.month_name}</span>
                </div>

                ${cardContentHtml}

                <div class="pt-1 border-t border-slate-100 flex items-center justify-center">
                    <span class="text-[10px] font-bold ${isSelected ? 'text-blue-700' : 'text-slate-400 group-hover:text-blue-600'}">
                        ${isSelected ? '✓ Seçili Gün' : 'Biletleri Gör →'}
                    </span>
                </div>
            </button>
        `;
    }).join('');

    container.innerHTML = `
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-calendar-days text-indigo-600 text-base"></i>
                <div>
                    <h3 class="text-xs font-black text-indigo-950 uppercase tracking-wide">Esnek Fiyat Takvimi & Kategori Şampiyonları</h3>
                    <p class="text-[11px] text-slate-500 font-medium">Tüm seyahat türlerinde en ucuz günleri tek bakışta keşfedin</p>
                </div>
            </div>

            <!-- Takvim Aralık Seçici Butonları -->
            <div class="flex items-center bg-white border border-slate-200 p-1 rounded-xl shadow-sm self-start md:self-auto">
                <button type="button" onclick="changeCalendarRange(7)" class="px-2.5 py-1 text-xs font-bold rounded-lg transition ${daysCount === 7 ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}">
                    7 Günlük
                </button>
                <button type="button" onclick="changeCalendarRange(15)" class="px-2.5 py-1 text-xs font-bold rounded-lg transition ${daysCount === 15 ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}">
                    15 Günlük
                </button>
                <button type="button" onclick="changeCalendarRange(30)" class="px-2.5 py-1 text-xs font-bold rounded-lg transition ${daysCount === 30 ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}">
                    30 Günlük (Aylık)
                </button>
            </div>
        </div>

        <!-- Gün Kartları Kaydırma Alanı -->
        <div class="flex gap-2.5 overflow-x-auto pb-3 pt-2 scrollbar-thin">
            ${daysHtml}
        </div>

        <!-- Akıllı Gezgin Önerisi -->
        <div class="mt-3 pt-3 border-t border-indigo-100 text-xs text-indigo-950 font-semibold flex items-center gap-2">
            <span>${calendarData.tip || '💡 Seçtiğiniz dönem seyahat için en avantajlı tarihlerden biridir.'}</span>
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
    if (currentActiveSummaryFilter === mode) {
        currentActiveSummaryFilter = 'all'; // Toggle back to all
    } else {
        currentActiveSummaryFilter = mode;
    }

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

    let list = currentSearchData.tickets || [];
    if (currentActiveSummaryFilter !== 'all') {
        list = list.filter(t => t.transport_type === currentActiveSummaryFilter);
    }

    ticketsList.innerHTML = prefixHtml;

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
        } else {
            typeBadge = `<span class="bg-amber-100 text-amber-800 text-[11px] font-bold px-2 py-0.5 rounded">🚌 Otobüs</span>`;
        }

        const card = document.createElement('div');
        card.className = 'bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-all flex flex-col md:flex-row md:items-center justify-between gap-4';

        let providersHtml = '';
        if (ticket.providers) {
            providersHtml = ticket.providers.map(p => `
                <a href="${p.url}" target="_blank" class="text-[11px] font-bold ${p.is_best ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-600 bg-slate-100 border-slate-200'} border px-2 py-1 rounded-md hover:underline flex items-center gap-1">
                    <span>${p.name}: ${p.price.toFixed(2)} ₺</span>
                    <i class="fa-solid fa-external-link text-[9px]"></i>
                </a>
            `).join('');
        }

        const officialLink = ticket.official_link || ticket.direct_link;
        let officialName = ticket.official_name || ticket.carrier;
        let brandClean = officialName.replace(' Resmi', '').replace(' Airlines', '').replace(' (AnadoluJet)', '').replace(' Taşımacılık (YHT)', '').replace(' Taşımacılık', '').replace(' Turizm', '').trim();
        
        let buySuffix = "den";
        if (brandClean.toLowerCase().includes("pegasus") || brandClean.toLowerCase().includes("kamil koç") || brandClean.toLowerCase().includes("koç")) {
            buySuffix = "tan";
        } else if (brandClean.toLowerCase().includes("ajet")) {
            buySuffix = "ten";
        }

        const agentLink = ticket.agent_link || ticket.direct_link;
        const agentName = ticket.agent_name || (ticket.transport_type === 'bus' ? 'Obilet' : (ticket.transport_type === 'train' ? 'TCDD E-Bilet' : 'Enuygun'));

        card.innerHTML = `
            <div class="flex-1 space-y-2">
                <div class="flex items-center flex-wrap gap-2">
                    ${typeBadge}
                    <span class="font-extrabold text-slate-900 text-sm">${ticket.carrier}</span>
                    <span class="text-xs text-slate-400 font-semibold">• ${ticket.flight_number}</span>
                    ${ticket.badge ? `<span class="bg-rose-50 text-rose-700 font-bold text-[10px] px-2 py-0.5 rounded-full border border-rose-200">${ticket.badge}</span>` : ''}
                    ${ticket.cabin_class === 'business' ? `<span class="bg-purple-50 text-purple-700 font-extrabold text-[10px] px-2 py-0.5 rounded-full border border-purple-200"><i class="fa-solid fa-crown text-purple-600 mr-1"></i>Business Class ⭐</span>` : ''}
                    ${ticket.is_night_trip ? `<span class="bg-indigo-50 text-indigo-700 font-bold text-[10px] px-2 py-0.5 rounded-full border border-indigo-200">🌙 Otel Tasarruflu</span>` : ''}
                </div>

                <div class="flex items-center gap-4 sm:gap-6 pt-1">
                    <div>
                        <div class="text-[11px] text-slate-500 font-bold mb-0.5">${ticket.departure_date_formatted || currentSearchData.date}</div>
                        <div class="text-xl font-black text-slate-900">${ticket.departure_time}</div>
                        <div class="text-xs text-slate-500 font-semibold">${ticket.origin}</div>
                    </div>

                    <div class="flex flex-col items-center">
                        <span class="text-[10px] font-bold text-slate-400">${ticket.duration}</span>
                        <div class="w-16 sm:w-20 h-0.5 bg-slate-300 relative my-1">
                            <i class="fa-solid ${ticket.transport_type === 'flight' ? 'fa-plane' : ticket.transport_type === 'train' ? 'fa-train' : 'fa-bus'} text-[10px] text-blue-600 absolute -top-1.5 left-1/2 -translate-x-1/2 bg-white px-0.5"></i>
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

            <div class="flex flex-col md:items-end justify-between border-t md:border-t-0 md:border-l border-slate-100 pt-3 md:pt-0 md:pl-6 gap-3 min-w-[210px]">
                <div class="text-left md:text-right w-full">
                    ${ticket.regular_price ? `<div class="text-xs text-slate-400 line-through">${ticket.regular_price.toFixed(2)} ₺</div>` : ''}
                    <div class="text-2xl font-black text-emerald-600">${ticket.price.toFixed(2)} ₺</div>
                    <div class="text-[10px] text-slate-400 font-semibold">${currentSearchData.trip_type === 'round_trip' ? 'Gidiş - Dönüş Toplam' : 'Tek Yön / Kişi Başı'}</div>
                </div>

                <!-- Google Flights Standart Aksiyon Alanı -->
                <div class="w-full space-y-2">
                    <!-- Ana Buton: Doğrudan Resmi Havayolu / Taşıyıcı Rezervasyonu -->
                    <a href="${officialLink}" target="_blank" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-xs py-2.5 px-3 rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-blue-500/20 transition">
                        <span>${brandClean}'${buySuffix} Al (${ticket.price.toFixed(2)} ₺)</span>
                        <i class="fa-solid fa-arrow-right text-[10px]"></i>
                    </a>

                    <!-- Alt Satır: Acente Alternatifi & Fiyat Alarmı -->
                    <div class="flex items-center justify-between px-1 text-xs pt-0.5">
                        <a href="${agentLink}" target="_blank" class="font-semibold text-slate-500 hover:text-blue-600 flex items-center gap-1 transition" title="${agentName} acente ekranında karşılaştır">
                            <span>${agentName}'da da Gör</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                        </a>
                        <button onclick="openTrackModalWithData('${ticket.origin}', '${ticket.destination}', ${ticket.price}, '${currentSearchData.date}')" class="font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 transition" title="Bu rota için fiyat alarmı kur">
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
            showToast(`🎉 ${origin} → ${dest} rotası takibe alındı! Fiyat ${targetPrice} ₺ altına düşerse bildireceğiz.`);
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
            new Notification('Ucuz Bilet Bul — Bildirimler Aktif!', {
                body: 'Artık flaş indirimler ve hedef fiyat uyarıları anında ekranınıza gelecek.',
                icon: '/static/icons/ticket.png'
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
