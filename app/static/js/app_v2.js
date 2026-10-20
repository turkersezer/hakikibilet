/**
 * Hakiki Bilet V2 — Sıcak, Görsel & Yeni Nesil Seyahat Portalı
 * Akıllı Mod Filtreleme (Uçakta feribot çıkmaz), HD Destinasyon Fotoğrafları, Derin Linkler
 */

// Global State
let currentMasterTab = 'transport'; // 'transport', 'hotel', 'events', 'deals'
let currentTransportSubTab = 'flight'; // 'flight', 'bus', 'train', 'ferry', 'car'
let currentEventCategory = 'all'; // 'all', 'sport', 'world', 'island', 'domestic'
let activeCurrency = 'TRY';
let currentHotelScope = 'intl'; // 'intl' (Booking.com & Agoda) or 'domestic' (Enuygun & Otelz)

// Uçuş Modu Özel Durumları
let currentFlightScope = 'domestic'; // 'domestic' (Yurtiçi) or 'international' (Yurtdışı)
let currentFlightTripType = 'round'; // 'round' (Gidiş-Dönüş) or 'one_way' (Tek Yön)
let currentFlightCabin = 'economy'; // 'economy' or 'business'
let flightPax = {
    adults: 1,
    children: 0,
    infants: 0
};

let verifiedCities = [];
let allCuratedEvents = [];

document.addEventListener("DOMContentLoaded", async () => {
    setupDynamicDates();
    await loadCitiesForTransport('flight', currentFlightScope); // Varsayılan uçuş havalimanları
    setupEventListeners();
    renderEvents();
});

// Dinamik Tarih Kurulumu (Bugünden 14 gün sonrası gidiş, 17 gün sonrası dönüş)
function setupDynamicDates() {
    const today = new Date();
    const dep = new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000);
    const ret = new Date(today.getTime() + 17 * 24 * 60 * 60 * 1000);

    const depStr = dep.toISOString().split('T')[0];
    const retStr = ret.toISOString().split('T')[0];

    const transDep = document.getElementById("transDepDate");
    const transRet = document.getElementById("transRetDate");
    const hotelCin = document.getElementById("hotelCheckin");
    const hotelCout = document.getElementById("hotelCheckout");

    if (transDep && !transDep.value) transDep.value = depStr;
    if (transRet && !transRet.value) transRet.value = retStr;
    if (hotelCin && !hotelCin.value) hotelCin.value = depStr;
    if (hotelCout && !hotelCout.value) hotelCout.value = retStr;

    // Minimum seçim bugünden önce olamaz
    const todayStr = today.toISOString().split('T')[0];
    if (transDep) transDep.min = todayStr;
    if (transRet) transRet.min = todayStr;
    if (hotelCin) hotelCin.min = todayStr;
    if (hotelCout) hotelCout.min = todayStr;

    // Embedded curated events
    if (window.INITIAL_EVENTS && window.INITIAL_EVENTS.length > 0) {
        allCuratedEvents = window.INITIAL_EVENTS;
    }
}

// 1. UÇUŞ KAPSAMI (YURTİÇİ / YURTDIŞI) SEÇİMİ
async function switchFlightScope(scope) {
    currentFlightScope = scope;
    const domBtn = document.getElementById("flightScope-domestic");
    const intlBtn = document.getElementById("flightScope-intl");
    const summaryBadge = document.getElementById("flightScopeSummary");
    const destInput = document.getElementById("transDest");
    const isEn = window.currentAppLang === 'en';

    if (scope === 'domestic') {
        if (domBtn) {
            domBtn.className = "flight-scope-btn px-3.5 py-1.5 rounded-lg text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-2xs transition flex items-center gap-1.5";
        }
        if (intlBtn) {
            intlBtn.className = "flight-scope-btn px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
        }
        if (summaryBadge) {
            summaryBadge.innerHTML = `<i class="fa-solid fa-plane-departure text-amber-500"></i><span>${isEn ? '55+ Verified Airports Across Turkey' : 'Türkiye İçi 55+ Teyitli Havalimanı'}</span>`;
        }
        if (destInput) {
            destInput.placeholder = isEn ? "Where do you want to fly? (e.g. Antalya, Izmir, Ankara)" : "Nereye uçmak istiyorsunuz? (Örn: Antalya, İzmir, Ankara, Trabzon)";
        }
    } else {
        if (intlBtn) {
            intlBtn.className = "flight-scope-btn px-3.5 py-1.5 rounded-lg text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-2xs transition flex items-center gap-1.5";
        }
        if (domBtn) {
            domBtn.className = "flight-scope-btn px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
        }
        if (summaryBadge) {
            summaryBadge.innerHTML = `<i class="fa-solid fa-globe text-amber-500"></i><span>${isEn ? 'Global Hubs & International Airports' : 'Dünya Metropolleri & Popüler Havalimanları'}</span>`;
        }
        if (destInput) {
            destInput.placeholder = isEn ? "Global airports (e.g. Paris, London, Rome, Berlin, Dubai)" : "Dünya havalimanları (Örn: Paris, Londra, Roma, Berlin, Dubai)";
        }
    }

    await loadCitiesForTransport('flight', scope);
}

// 2. UÇUŞ TİPİ (TEK YÖN / GİDİŞ - DÖNÜŞ) SEÇİMİ
function setFlightTripType(tripType) {
    currentFlightTripType = tripType;
    const roundBtn = document.getElementById("tripTypeBtn-round");
    const onewayBtn = document.getElementById("tripTypeBtn-oneway");
    const retWrapper = document.getElementById("returnDateWrapper");
    const depWrapper = document.getElementById("depDateWrapper");
    const depLabel = document.getElementById("depDateLabel");
    const retInput = document.getElementById("transRetDate");

    if (tripType === 'one_way') {
        if (onewayBtn) {
            onewayBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-black bg-slate-900 text-white shadow-2xs transition flex items-center gap-1.5";
        }
        if (roundBtn) {
            roundBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
        }
        if (retWrapper) {
            retWrapper.classList.add("hidden");
        }
        if (retInput) {
            retInput.disabled = true;
            retInput.required = false;
        }
        if (depWrapper) {
            depWrapper.classList.remove("lg:col-span-2");
            depWrapper.classList.add("lg:col-span-4");
        }
        if (depLabel) {
            depLabel.innerHTML = '✈️ Gidiş Tarihi <span class="text-amber-600 font-bold ml-1 text-[10px] bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">Tek Yön</span>';
        }
    } else {
        if (roundBtn) {
            roundBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-black bg-slate-900 text-white shadow-2xs transition flex items-center gap-1.5";
        }
        if (onewayBtn) {
            onewayBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
        }
        if (depWrapper) {
            depWrapper.classList.remove("lg:col-span-4");
            depWrapper.classList.add("lg:col-span-2");
        }
        if (depLabel) {
            depLabel.innerHTML = '✈️ Gidiş Tarihi';
        }
        if (retWrapper) {
            retWrapper.classList.remove("hidden");
        }
        if (retInput) {
            retInput.disabled = false;
            retInput.required = true;
            if (!retInput.value) {
                const depVal = document.getElementById("transDepDate")?.value;
                if (depVal) retInput.value = getNextDaysDate(depVal, 3);
            }
        }
    }
}

// 3. KALKIŞ VE VARIŞ HAVALİMANLARINI DEĞİŞTİR (SWAP)
function swapOriginDest() {
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    const swapBtn = document.getElementById("swapAirportsBtn");

    if (!originInput || !destInput) return;
    const temp = originInput.value;
    originInput.value = destInput.value;
    destInput.value = temp;
    updateAirportHints();

    if (swapBtn) {
        swapBtn.classList.add("rotate-180");
        setTimeout(() => swapBtn.classList.remove("rotate-180"), 300);
    }
}

// 4. YOLCU VE KABİN SEÇİMİ POPOVER KONTROLLERİ
function togglePaxDropdown(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const menu = document.getElementById("paxDropdownMenu");
    if (menu) {
        menu.classList.toggle("hidden");
    }
}

function closePaxDropdown(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const menu = document.getElementById("paxDropdownMenu");
    if (menu) {
        menu.classList.add("hidden");
    }
}

function modifyPax(type, delta, e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    if (type === 'adults') {
        flightPax.adults = Math.max(1, Math.min(9, flightPax.adults + delta));
        if (flightPax.infants > flightPax.adults) {
            flightPax.infants = flightPax.adults;
            const infSpan = document.getElementById("paxValInfants");
            if (infSpan) infSpan.textContent = flightPax.infants;
        }
        const span = document.getElementById("paxValAdults");
        if (span) span.textContent = flightPax.adults;
    } else if (type === 'children') {
        flightPax.children = Math.max(0, Math.min(9, flightPax.children + delta));
        const span = document.getElementById("paxValChildren");
        if (span) span.textContent = flightPax.children;
    } else if (type === 'infants') {
        flightPax.infants = Math.max(0, Math.min(flightPax.adults, flightPax.infants + delta));
        const span = document.getElementById("paxValInfants");
        if (span) span.textContent = flightPax.infants;
    }
    updatePaxSummaryDisplay();
}

function selectFlightCabin(cabin) {
    currentFlightCabin = cabin;
    const econBtn = document.getElementById("cabinBtn-economy");
    const bizBtn = document.getElementById("cabinBtn-business");

    if (cabin === 'economy') {
        if (econBtn) {
            econBtn.className = "cabin-btn py-1.5 px-2 rounded-xl text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-2xs transition text-center";
        }
        if (bizBtn) {
            bizBtn.className = "cabin-btn py-1.5 px-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition text-center";
        }
    } else {
        if (bizBtn) {
            bizBtn.className = "cabin-btn py-1.5 px-2 rounded-xl text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-2xs transition text-center";
        }
        if (econBtn) {
            econBtn.className = "cabin-btn py-1.5 px-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition text-center";
        }
    }
    updatePaxSummaryDisplay();
}

function updatePaxSummaryDisplay() {
    const label = document.getElementById("paxDisplayLabel");
    if (!label) return;

    const isEn = window.currentAppLang === 'en';
    const parts = [];
    const adultWord = isEn ? (flightPax.adults > 1 ? "Adults" : "Adult") : "Yetişkin";
    const childWord = isEn ? (flightPax.children > 1 ? "Children" : "Child") : "Çocuk";
    const infantWord = isEn ? (flightPax.infants > 1 ? "Infants" : "Infant") : "Bebek";

    parts.push(`${flightPax.adults} ${adultWord}`);
    if (flightPax.children > 0) parts.push(`${flightPax.children} ${childWord}`);
    if (flightPax.infants > 0) parts.push(`${flightPax.infants} ${infantWord}`);

    let str = parts.join(", ");
    if (currentFlightCabin === 'business') {
        str += " • Business";
    } else if (isEn) {
        str += " • Economy";
    }
    label.textContent = str;
}

// 5. MODA ÖZEL AKILLI ŞEHİR YÜKLEME (UÇAKTA ASLA FERİBOT ÇIKMAZ!)
async function loadCitiesForTransport(transportMode, scope) {
    const actualScope = scope || (transportMode === 'flight' ? currentFlightScope : 'all');
    try {
        const res = await fetch(`/api/cities?transport_type=${transportMode}&scope=${actualScope}`);
        if (res.ok) {
            const data = await res.json();
            verifiedCities = data.cities || [];
            populateDatalists(transportMode, actualScope);
        }
    } catch (e) {
        console.error("Şehirler yüklenirken hata:", e);
    }
}

function updateAirportHints() {
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    const originHint = document.getElementById("originAirportHint");
    const destHint = document.getElementById("destAirportHint");
    if (!originInput) return;

    if (currentTransportSubTab !== 'flight') {
        if (originHint) originHint.classList.add("hidden");
        if (destHint) destHint.classList.add("hidden");
        return;
    }

    const originVal = (originInput.value || "").trim().toLowerCase();
    const destVal = destInput ? (destInput.value || "").trim().toLowerCase() : "";

    if (originHint) {
        if (originVal.includes("sabiha") || originVal.includes("saw")) {
            originHint.innerHTML = '<i class="fa-solid fa-plane-departure text-amber-600"></i><span>Sadece <strong>Sabiha Gökçen (SAW)</strong> seçildi • Anadolu Yakası (Pegasus & AJet)</span>';
            originHint.classList.remove("hidden");
        } else if (originVal.includes("istanbul havalimanı") || (originVal.includes("ist") && !originVal.includes("saw"))) {
            originHint.innerHTML = '<i class="fa-solid fa-plane-departure text-amber-600"></i><span>Sadece <strong>İstanbul Havalimanı (IST)</strong> seçildi • Avrupa Yakası (THY & Dünya)</span>';
            originHint.classList.remove("hidden");
        } else if (originVal.includes("istanbul")) {
            originHint.innerHTML = '<i class="fa-solid fa-circle-info text-amber-600"></i><span><strong>İstanbul (Tüm Havalimanları):</strong> SAW ve IST birlikte taranır, en ucuz bilet öne çıkar.</span>';
            originHint.classList.remove("hidden");
        } else {
            originHint.classList.add("hidden");
        }
    }

    if (destHint) {
        if (destVal.includes("adana") || destVal.includes("çukurova") || destVal.includes("cov")) {
            destHint.innerHTML = '<i class="fa-solid fa-location-dot text-amber-600"></i><span><strong>Çukurova Uluslararası (COV):</strong> Adana ve Mersin ortak yeni havalimanı</span>';
            destHint.classList.remove("hidden");
        } else if (destVal.includes("sabiha") || destVal.includes("saw")) {
            destHint.innerHTML = '<i class="fa-solid fa-plane-arrival text-amber-600"></i><span>Sadece <strong>Sabiha Gökçen (SAW)</strong> varışlı</span>';
            destHint.classList.remove("hidden");
        } else if (destVal.includes("istanbul havalimanı") || (destVal.includes("ist") && !destVal.includes("saw"))) {
            destHint.innerHTML = '<i class="fa-solid fa-plane-arrival text-amber-600"></i><span>Sadece <strong>İstanbul Havalimanı (IST)</strong> varışlı</span>';
            destHint.classList.remove("hidden");
        } else if (destVal.includes("istanbul")) {
            destHint.innerHTML = '<i class="fa-solid fa-circle-info text-amber-600"></i><span><strong>İstanbul (Tüm Havalimanları):</strong> Her iki havalimanına inişler taranır.</span>';
            destHint.classList.remove("hidden");
        } else {
            destHint.classList.add("hidden");
        }
    }
}
window.updateAirportHints = updateAirportHints;

function populateDatalists(transportMode, scope) {
    const originList = document.getElementById("originCitiesList");
    const destList = document.getElementById("destCitiesList");

    let prefix = "✈️";
    if (transportMode === "bus") prefix = "🚌";
    if (transportMode === "train") prefix = "🚆";
    if (transportMode === "ferry") prefix = "⛴️";
    if (transportMode === "car") prefix = "🚗";

    if (transportMode === 'flight') {
        // Kalkış Havalimanları: İstanbul için çoklu net seçenekler + Türkiye Havalimanları
        const specialOrigins = `
            <option value="İstanbul">✈️ İstanbul - Tüm Havalimanları (IST, SAW)</option>
            <option value="İstanbul Sabiha Gökçen (SAW)">✈️ Sabiha Gökçen Havalimanı (SAW) - Anadolu Yakası</option>
            <option value="İstanbul Havalimanı (IST)">✈️ İstanbul Havalimanı (IST) - Avrupa Yakası</option>
            <option value="Ankara (ESB)">✈️ Ankara Esenboğa Havalimanı (ESB)</option>
            <option value="İzmir (ADB)">✈️ İzmir Adnan Menderes Havalimanı (ADB)</option>
            <option value="Antalya (AYT)">✈️ Antalya Havalimanı (AYT)</option>
            <option value="Adana / Çukurova (COV)">✈️ Adana / Çukurova Uluslararası (COV)</option>
            <option value="Trabzon (TZX)">✈️ Trabzon Havalimanı (TZX)</option>
            <option value="Bodrum (BJV)">✈️ Bodrum Milas Havalimanı (BJV)</option>
            <option value="Dalaman (DLM)">✈️ Dalaman Havalimanı (DLM)</option>
        `;
        const trAirports = verifiedCities.filter(c => (!c.country || c.country === 'Türkiye' || !c.is_international) && !['istanbul', 'ankara', 'izmir', 'antalya', 'adana', 'trabzon', 'bodrum', 'dalaman'].includes(c.slug));
        const originHtml = specialOrigins + trAirports.map(c => {
            const iataStr = c.iata ? ` (${c.iata})` : '';
            return `<option value="${c.name}">${prefix} ${c.name}${iataStr} Havalimanı</option>`;
        }).join("");
        if (originList) originList.innerHTML = originHtml;

        // Varış Havalimanları: Kapsama göre
        const specialDests = `
            <option value="Adana / Çukurova (COV)">✈️ Adana / Çukurova Uluslararası Havalimanı (COV)</option>
            <option value="Antalya (AYT)">✈️ Antalya Havalimanı (AYT)</option>
            <option value="İzmir (ADB)">✈️ İzmir Adnan Menderes Havalimanı (ADB)</option>
            <option value="İstanbul">✈️ İstanbul - Tüm Havalimanları (IST, SAW)</option>
            <option value="İstanbul Sabiha Gökçen (SAW)">✈️ Sabiha Gökçen Havalimanı (SAW) - Anadolu Yakası</option>
            <option value="İstanbul Havalimanı (IST)">✈️ İstanbul Havalimanı (IST) - Avrupa Yakası</option>
        `;
        const restDests = verifiedCities.filter(c => !['istanbul', 'antalya', 'izmir', 'adana'].includes(c.slug)).map(c => {
            const iataStr = c.iata ? ` (${c.iata})` : '';
            const countryStr = c.country ? ` • ${c.country}` : '';
            const icon = (c.is_international || (c.country && c.country !== 'Türkiye')) ? '🌍' : '🇹🇷';
            return `<option value="${c.name}">${icon} ${c.name}${iataStr}${countryStr}</option>`;
        }).join("");
        if (destList) destList.innerHTML = specialDests + restDests;
    } else {
        const html = verifiedCities.map(c => {
            const iataStr = c.iata ? ` (${c.iata})` : '';
            const regionStr = c.country ? ` • ${c.country}` : '';
            return `<option value="${c.name}">${prefix} ${c.region || ''}${regionStr}</option>`;
        }).join("");
        if (originList) originList.innerHTML = html;
        if (destList) destList.innerHTML = html;
    }

    populateHotelDatalist(currentHotelScope);
    updateAirportHints();
}

// Otel Kapsam Değişimi: Yurtdışı (Booking) vs Yurtiçi (Enuygun/Otelz)
function switchHotelScope(scope) {
    currentHotelScope = scope;
    const intlBtn = document.getElementById("hotelScope-intl");
    const domBtn = document.getElementById("hotelScope-domestic");
    const cityInput = document.getElementById("hotelCity");

    if (scope === 'intl') {
        if (intlBtn) {
            intlBtn.className = "hotel-scope-btn px-4 py-2 rounded-xl text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-xs transition";
        }
        if (domBtn) {
            domBtn.className = "hotel-scope-btn px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-white transition";
        }
        if (cityInput) {
            cityInput.placeholder = "Şehir, Ada veya Bölge (Örn: Nice, Sakız Adası, Paris, Roma, Londra)";
        }
    } else {
        if (domBtn) {
            domBtn.className = "hotel-scope-btn px-4 py-2 rounded-xl text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-xs transition";
        }
        if (intlBtn) {
            intlBtn.className = "hotel-scope-btn px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-white transition";
        }
        if (cityInput) {
            cityInput.placeholder = "Şehir veya Tatil Beldesi (Örn: Antalya, Bodrum, Kapadokya, Çeşme, Kaş, İzmir)";
        }
    }

    populateHotelDatalist(scope);
}

function populateHotelDatalist(scope) {
    const hotelCityList = document.getElementById("hotelCitiesList");
    if (!hotelCityList || !verifiedCities || verifiedCities.length === 0) return;

    let filtered = verifiedCities;
    if (scope === 'intl') {
        filtered = verifiedCities.filter(c => c.country && c.country !== 'Türkiye');
        if (filtered.length === 0) filtered = verifiedCities;
    } else {
        filtered = verifiedCities.filter(c => !c.country || c.country === 'Türkiye');
    }

    hotelCityList.innerHTML = filtered.map(c => {
        const flag = (c.country && c.country !== 'Türkiye') ? '🌍' : '🇹🇷';
        const regionStr = c.country ? ` • ${c.country}` : '';
        return `<option value="${c.name}">${flag} ${c.region || ''}${regionStr}</option>`;
    }).join("");
}

// 2. ANA SEKME DEĞİŞİMİ
function switchMasterTab(tabName) {
    currentMasterTab = tabName;
    
    document.querySelectorAll(".master-tab-btn").forEach(btn => {
        btn.classList.remove("active-master-tab", "bg-white", "text-amber-900", "shadow-xl");
        btn.classList.add("text-amber-100", "hover:text-white");
    });
    const activeBtn = document.getElementById(`tabBtn-${tabName}`);
    if (activeBtn) {
        activeBtn.classList.add("active-master-tab", "bg-white", "text-amber-900", "shadow-xl");
        activeBtn.classList.remove("text-amber-100", "hover:text-white");
    }

    document.querySelectorAll(".master-tab-pane").forEach(pane => {
        pane.classList.add("hidden");
    });
    const activePane = document.getElementById(`pane-${tabName}`);
    if (activePane) {
        activePane.classList.remove("hidden");
    }

    const mainSection = document.getElementById("mainPortalHub");
    if (mainSection && window.scrollY > 400) {
        mainSection.scrollIntoView({ behavior: "smooth" });
    }
}

// 3. ULAŞIM ALT SEKMELERİ (Uçak | Otobüs | Tren | Gemi & Feribot | Araç)
async function switchTransportSubTab(subTab) {
    currentTransportSubTab = subTab;

    document.querySelectorAll(".transport-sub-btn").forEach(btn => {
        btn.classList.remove("bg-gradient-to-r", "from-amber-500", "to-orange-500", "text-white", "font-black", "shadow-md");
        btn.classList.add("text-slate-600", "hover:bg-amber-50/60");
    });
    const activeSubBtn = document.getElementById(`subBtn-${subTab}`);
    if (activeSubBtn) {
        activeSubBtn.classList.add("bg-gradient-to-r", "from-amber-500", "to-orange-500", "text-white", "font-black", "shadow-md");
        activeSubBtn.classList.remove("text-slate-600", "hover:bg-amber-50/60");
    }

    // Seçilen moda göre şehir listesini hemen filtrele (Uçakta feribot çıkmasın!)
    await loadCitiesForTransport(subTab);

    // Form etiketlerini ve placeholder'larını moda özel güncelle
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    const subHintBadge = document.getElementById("transportSubHint");
    const originLabel = document.getElementById("originFieldLabel");
    const destLabel = document.getElementById("destFieldLabel");

    if (subTab === 'car') {
        if (originLabel) originLabel.innerHTML = '🚗 Alış Noktası (Havalimanı / Şehir)';
        if (destLabel) destLabel.innerHTML = '📍 İade Noktası';
        if (originInput) originInput.placeholder = 'Örn: Antalya Havalimanı (AYT)';
        if (destInput) destInput.placeholder = 'Aynı noktaya iade veya farklı şehir';
        if (subHintBadge) subHintBadge.innerHTML = '🚗 Enuygun, Yolcu360, Avis & Garenta Havalimanı Araç Kiralama Karşılaştırması';
    } else if (subTab === 'bus') {
        if (originLabel) originLabel.innerHTML = '🚌 Kalkış Şehri / Otogarı';
        if (destLabel) destLabel.innerHTML = '🎯 Varış Şehri (Türkiye & Balkanlar)';
        if (originInput) originInput.placeholder = 'Örn: İstanbul (Esenler/Alibeyköy)';
        if (destInput) destInput.placeholder = 'Örn: Sofya, Selanik, Ankara, İzmir';
        if (subHintBadge) subHintBadge.innerHTML = '🚌 Türkiye Şehirlerarası & Balkan Hatları (Kamil Koç/FlixBus, Metro, Obilet)';
    } else if (subTab === 'train') {
        if (originLabel) originLabel.innerHTML = '🚆 Kalkış İstasyonu / Garı';
        if (destLabel) destLabel.innerHTML = '🏁 Varış İstasyonu';
        if (originInput) originInput.placeholder = 'Örn: İstanbul (Söğütlüçeşme YHT)';
        if (destInput) destInput.placeholder = 'Örn: Ankara YHT Garı, Eskişehir';
        if (subHintBadge) subHintBadge.innerHTML = '🚆 TCDD Yüksek Hızlı Tren (YHT) & Doğu Ekspresi Hatları';
    } else if (subTab === 'ferry') {
        if (originLabel) originLabel.innerHTML = '⛴️ Kalkış Limanı / İskelesi';
        if (destLabel) destLabel.innerHTML = '🏝️ Varış Adası veya İskelesi';
        if (originInput) originInput.placeholder = 'Örn: Çeşme Limanı, Bodrum, Galataport';
        if (destInput) destInput.placeholder = 'Örn: Sakız Adası (Chios), Kos, Rodos';
        if (subHintBadge) subHintBadge.innerHTML = '⛴️ Kapıda Vize Yunan Adaları (Sakız, Rodos, Kos) & Galataport Kruvaziyer Gemi Turları';
    } else {
        if (originLabel) originLabel.innerHTML = '✈️ Kalkış Havalimanı';
        if (destLabel) destLabel.innerHTML = '🛬 Varış Havalimanı';
        if (originInput) originInput.placeholder = 'Örn: İstanbul (IST / SAW)';
        if (destInput) destInput.placeholder = currentFlightScope === 'domestic' ? 'Örn: Antalya (AYT), İzmir (ADB), Ankara (ESB)' : 'Örn: Nice (NCE), Roma (FCO), Paris (CDG)';
        if (subHintBadge) subHintBadge.innerHTML = '✈️ THY, Pegasus, AJet & Dünya Havayolları Canlı Bilet Karşılaştırması';
    }

    // Uçuş Seçenekleri Barını (Yurtiçi/Yurtdışı & Tek Yön/Gidiş-Dönüş) sadece uçak modunda göster
    const flightBar = document.getElementById("flightOptionsBar");
    if (flightBar) {
        if (subTab === 'flight') {
            flightBar.classList.remove("hidden");
        } else {
            flightBar.classList.add("hidden");
        }
    }
    updateAirportHints();
}

// 4. ULAŞIM ARAMASI ÇALIŞTIRMA (Uçak Odaklı, Kusursuz Yolcu & Kapsam Desteği)
async function executeTransportSearch(e) {
    if (e) e.preventDefault();

    const origin = document.getElementById("transOrigin").value.trim();
    const destination = document.getElementById("transDest").value.trim();
    const depDate = document.getElementById("transDepDate").value;
    const retDate = document.getElementById("transRetDate").value;
    const isRound = (currentFlightTripType === 'round');
    const totalPax = flightPax.adults + flightPax.children + flightPax.infants;

    if (!origin || !destination || !depDate) {
        alert("Lütfen kalkış noktası, varış noktası ve seyahat tarihini seçiniz.");
        return;
    }
    if (currentTransportSubTab === 'flight' && isRound && !retDate) {
        alert("Lütfen dönüş tarihini seçiniz veya 'Tek Yön' seçeneğini işaretleyiniz.");
        return;
    }

    const resultsArea = document.getElementById("transportResultsArea");
    resultsArea.innerHTML = `
        <style>
            @keyframes flyAcrossPlane {
                0% { left: 4%; transform: translateY(0px) rotate(45deg) scale(0.95); }
                50% { left: 48%; transform: translateY(-8px) rotate(42deg) scale(1.1); }
                100% { left: calc(96% - 36px); transform: translateY(0px) rotate(45deg) scale(0.95); }
            }
            @keyframes streamTrail {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            @keyframes pulseCloud {
                0%, 100% { opacity: 0.3; transform: scale(1); }
                50% { opacity: 0.6; transform: scale(1.15); }
            }
            .hakiki-plane-flyer {
                position: absolute;
                top: -16px;
                animation: flyAcrossPlane 2.4s ease-in-out infinite alternate;
            }
            .hakiki-route-trail {
                animation: streamTrail 1.8s linear infinite;
            }
        </style>
        <div class="p-8 sm:p-12 text-center bg-gradient-to-br from-slate-950 via-[#0B1728] to-slate-900 rounded-3xl border border-sky-500/30 shadow-2xl relative overflow-hidden my-6">
            <!-- Arka Plan Radar Ağı & Yumuşak Parıltı -->
            <div class="absolute inset-0 opacity-15 pointer-events-none" style="background-image: radial-gradient(#38bdf8 1px, transparent 1px); background-size: 28px 28px;"></div>
            <div class="absolute -top-12 -left-12 w-48 h-48 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-12 -right-12 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <!-- Uçuş Yolu & Süzülen Uçak -->
            <div class="relative max-w-md mx-auto my-6 px-4">
                <!-- Rota Çizgisi -->
                <div class="h-1.5 w-full bg-slate-800/80 rounded-full relative overflow-hidden border border-sky-900/50">
                    <div class="hakiki-route-trail h-full w-full bg-gradient-to-r from-transparent via-amber-400 to-sky-400"></div>
                </div>

                <!-- Uçan Uçak Figürü -->
                <div class="hakiki-plane-flyer">
                    <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-amber-300 text-slate-950 flex items-center justify-center shadow-lg shadow-amber-500/40 ring-2 ring-white/30">
                        <i class="fa-solid fa-plane text-lg text-slate-950"></i>
                    </div>
                </div>

                <!-- Kalkış & Varış Nokta Rozetleri -->
                <div class="flex items-center justify-between text-xs font-black mt-5 text-sky-200">
                    <span class="flex items-center gap-1.5 bg-slate-900/90 border border-sky-400/30 px-3.5 py-1.5 rounded-xl shadow-xs">
                        <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                        <span class="text-white">${origin}</span>
                    </span>
                    <span class="flex items-center gap-1.5 bg-slate-900/90 border border-amber-400/30 px-3.5 py-1.5 rounded-xl shadow-xs">
                        <i class="fa-solid fa-location-dot text-amber-400"></i>
                        <span class="text-amber-300">${destination}</span>
                    </span>
                </div>
            </div>

            <!-- Bilgilendirme Metinleri -->
            <div class="relative z-10 space-y-2 mt-4">
                <div class="text-lg sm:text-xl font-black text-white flex items-center justify-center gap-2">
                    <span>${origin}</span>
                    <i class="fa-solid fa-arrow-right-long text-amber-400 text-sm"></i>
                    <span>${destination}</span>
                </div>
                <div class="text-xs sm:text-sm text-amber-300 font-extrabold flex items-center justify-center gap-2">
                    <span class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                    <span>Canlı Seferler & Hakiki Fiyatlar Taranıyor...</span>
                </div>
                <div class="text-[11px] sm:text-xs text-slate-400 font-medium max-w-lg mx-auto">
                    Trip.com, Booking/Kayak, Skyscanner, THY, Pegasus, AJet ve SunExpress resmi acente biletleri anlık taranıyor.
                </div>
            </div>
        </div>
    `;
    resultsArea.classList.remove("hidden");
    resultsArea.scrollIntoView({ behavior: "smooth", block: "nearest" });

    try {
        const payload = {
            origin: origin,
            destination: destination,
            departure_date: depDate,
            return_date: isRound ? retDate : null,
            passengers: totalPax,
            adults: flightPax.adults,
            children: flightPax.children,
            infants: flightPax.infants,
            cabin_class: currentFlightCabin,
            transport_type: currentTransportSubTab === 'car' ? 'car' : currentTransportSubTab,
            trip_type: isRound ? 'round_trip' : 'one_way',
            include_hotel: false, // Kullanıcı talimatı: Şimdilik otel önerilerini kaldır
            currency: activeCurrency
        };

        const res = await fetch("/api/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Arama sunucusundan yanıt alınamadı.");
        const data = await res.json();
        renderTransportResults(data, payload);
    } catch (err) {
        resultsArea.innerHTML = `
            <div class="p-8 text-center bg-rose-50 border border-rose-200 rounded-3xl text-rose-800 shadow-xs">
                <i class="fa-solid fa-circle-exclamation text-2xl mb-2 text-rose-500"></i>
                <div class="font-bold text-base">Arama sırasında bir bağlantı sorunu oluştu.</div>
                <div class="text-xs mt-1 text-rose-600 font-medium">${err.message}</div>
            </div>
        `;
    }
}

// Ulaşım Sonuçlarını Render Et (Google Flights & Skyscanner Standardı • Canlı Sefer Saatleri & Çift Bacak)
function renderTransportResults(data, searchReq) {
    const resultsArea = document.getElementById("transportResultsArea");
    const tickets = data.tickets || [];
    window.lastTransportResults = tickets;
    window.lastSearchReq = searchReq;

    const cinDate = searchReq.departure_date;
    const coutDate = searchReq.return_date || getNextDaysDate(cinDate, 2);

    let html = '';

    const isEn = window.currentAppLang === 'en';
    // Uçuş Bilgi ve Kriter Özeti Çubuğu
    const adultWord = isEn ? ((searchReq.adults || 1) > 1 ? "Adults" : "Adult") : "Yetişkin";
    const childWord = isEn ? (searchReq.children > 1 ? "Children" : "Child") : "Çocuk";
    const infantWord = isEn ? (searchReq.infants > 1 ? "Infants" : "Infant") : "Bebek";
    const paxSummaryText = `${searchReq.adults || 1} ${adultWord}${searchReq.children ? ', ' + searchReq.children + ' ' + childWord : ''}${searchReq.infants ? ', ' + searchReq.infants + ' ' + infantWord : ''} • ${searchReq.cabin_class === 'business' ? 'Business' : (isEn ? 'Economy' : 'Ekonomi')}`;
    const tripTypeText = searchReq.trip_type === 'round_trip' 
        ? `${isEn ? 'Round-Trip' : 'Gidiş - Dönüş'} (${searchReq.departure_date} ⇄ ${searchReq.return_date})` 
        : `${isEn ? 'One-Way' : 'Tek Yön'} (${searchReq.departure_date})`;
    const scopeLabel = currentFlightScope === 'domestic' 
        ? (isEn ? '🇹🇷 Domestic Flight' : '🇹🇷 Yurtiçi Uçuş') 
        : (isEn ? '🌍 International Flight' : '🌍 Yurtdışı Uçuş');

    html += `
        <div class="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white rounded-3xl p-5 sm:p-6 mb-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl border border-slate-700">
            <div>
                <div class="flex flex-wrap items-center gap-2 mb-2">
                    <span class="px-3 py-1 rounded-full text-[10.5px] font-black uppercase tracking-wider bg-amber-400 text-slate-950 shadow-2xs">
                        ${scopeLabel}
                    </span>
                    <span class="px-3 py-1 rounded-full text-[10.5px] font-bold bg-white/10 text-amber-200 border border-white/10">
                        ${tripTypeText}
                    </span>
                </div>
                <h3 class="text-xl sm:text-2xl font-black text-white flex items-center gap-3">
                    <span>${searchReq.origin}</span>
                    <i class="fa-solid fa-plane-departure text-amber-400 text-base"></i>
                    <span>${searchReq.destination}</span>
                </h3>
            </div>
            <div class="text-left md:text-right border-t md:border-t-0 pt-3 md:pt-0 w-full md:w-auto">
                <div class="text-[10px] uppercase tracking-wider text-slate-400 font-bold">${isEn ? 'Selected Passengers & Class' : 'Seçili Yolcular & Sınıf'}</div>
                <div class="text-sm font-black text-amber-300 flex items-center md:justify-end gap-1.5 mt-0.5">
                    <i class="fa-solid fa-user-group text-xs"></i>
                    <span>${paxSummaryText}</span>
                </div>
                <div class="text-[10px] text-emerald-400 font-bold mt-1 flex items-center md:justify-end gap-1">
                    <i class="fa-solid fa-lock text-[9px]"></i>
                    <span>${isEn ? 'Direct Carrier Deep Link' : 'Doğrudan Taşıyıcı Derin Linki'}</span>
                </div>
            </div>
        </div>
    `;

    // Filtre & Hızlı Sıralama Çubuğu (En Erken / En Geç & 12-18 Öğle Slotu Dahil)
    if (currentTransportSubTab === 'flight' && tickets.length > 1) {
        window.currentFlightSort = 'cheapest';
        window.currentFlightTimeFilter = 'all';
        window.currentFlightAirportFilter = 'all';

        const ports = new Set();
        tickets.forEach(t => {
            if (t.from_code) ports.add(t.from_code.toUpperCase());
            if (t.to_code) ports.add(t.to_code.toUpperCase());
        });
        const hasSaw = ports.has('SAW');
        const hasIst = ports.has('IST');
        const isMultiAirportCity = (hasSaw && hasIst) || 
            (searchReq.origin && searchReq.origin.toLowerCase().includes('istanbul')) ||
            (searchReq.destination && searchReq.destination.toLowerCase().includes('istanbul'));

        html += `
            <div class="bg-white border-2 border-slate-200/90 rounded-2xl p-3.5 sm:p-4 mb-6 shadow-xs flex flex-col gap-3.5">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3.5">
                    <!-- 1. Sıralama Butonları (En Ucuz | En Hızlı | En Erken Kalkış | En Geç Kalkış) -->
                    <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <span class="text-xs font-black text-slate-800 flex items-center gap-1.5 mr-1">
                            <i class="fa-solid fa-arrow-down-wide-short text-amber-500"></i> Sırala:
                        </span>
                        <button type="button" onclick="setFlightSort('cheapest')" id="fltSort-cheapest" class="flt-sort-btn px-3 py-1.5 rounded-xl text-xs font-black bg-slate-900 text-white shadow-xs transition cursor-pointer">
                            💰 En Ucuz
                        </button>
                        <button type="button" onclick="setFlightSort('fastest')" id="fltSort-fastest" class="flt-sort-btn px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            ⚡ En Hızlı
                        </button>
                        <button type="button" onclick="setFlightSort('earliest')" id="fltSort-earliest" class="flt-sort-btn px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            🛫 En Erken Kalkış
                        </button>
                        <button type="button" onclick="setFlightSort('latest')" id="fltSort-latest" class="flt-sort-btn px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            🛬 En Geç Kalkış
                        </button>
                    </div>

                    <!-- 2. Zaman Dilimi Filtreleri (06-12 Sabah | 12-18 Öğle | 18+ Akşam) -->
                    <div class="flex flex-wrap items-center gap-1.5 border-t md:border-t-0 pt-2.5 md:pt-0">
                        <span class="text-[11px] font-black text-slate-500 mr-1 flex items-center gap-1">
                            <i class="fa-regular fa-clock text-amber-500"></i> Kalkış Saati:
                        </span>
                        <button type="button" onclick="setFlightTimeFilter('all')" id="fltTime-all" class="flt-time-btn px-2.5 py-1 rounded-lg text-xs font-black bg-amber-500 text-white shadow-xs transition cursor-pointer">
                            Tümü
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('night')" id="fltTime-night" class="flt-time-btn px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            🌙 Gece (00-06)
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('morning')" id="fltTime-morning" class="flt-time-btn px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            🌅 Sabah (06-12)
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('noon')" id="fltTime-noon" class="flt-time-btn px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            ☀️ Öğle (12-18)
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('evening')" id="fltTime-evening" class="flt-time-btn px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            🌆 Akşam (18+)
                        </button>
                        <span id="fltCountBadge" class="ml-1 text-xs font-bold text-slate-400">
                            (${tickets.length} uçuş)
                        </span>
                    </div>
                </div>

                <!-- 3. Çoklu Havalimanı Filtresi (İstanbul SAW vs IST) -->
                ${isMultiAirportCity ? `
                    <div class="flex flex-wrap items-center gap-2 pt-2.5 border-t border-slate-100">
                        <span class="text-[11px] font-black text-slate-700 mr-1 flex items-center gap-1">
                            <i class="fa-solid fa-plane-arrival text-amber-500"></i> Havalimanı:
                        </span>
                        <button type="button" onclick="setFlightAirportFilter('all')" id="fltPort-all" class="flt-port-btn px-3 py-1 rounded-xl text-xs font-black bg-slate-900 text-white shadow-2xs transition cursor-pointer">
                            Tüm Havalimanları (${tickets.length})
                        </button>
                        <button type="button" onclick="setFlightAirportFilter('SAW')" id="fltPort-SAW" class="flt-port-btn px-3 py-1 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            Sabiha Gökçen (SAW) • Anadolu
                        </button>
                        <button type="button" onclick="setFlightAirportFilter('IST')" id="fltPort-IST" class="flt-port-btn px-3 py-1 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            İstanbul Havalimanı (IST) • Avrupa
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }

    // A. SEFER KARTLARI
    if (tickets.length === 0) {
        html += `
            <div class="bg-white p-10 rounded-3xl border-2 border-slate-200 text-center shadow-xs mb-6">
                <i class="fa-solid fa-plane-slash text-3xl text-slate-400 mb-2"></i>
                <div class="font-black text-slate-800 text-base">Bu güzergahta seçili tarihte doğrudan sefer bulunamadı.</div>
                <div class="text-xs text-slate-500 mt-1 font-medium">Lütfen farklı bir tarih veya en yakın büyük merkez havalimanını seçiniz.</div>
            </div>
        `;
    } else {
        html += `<div id="ticketCardsContainer" class="space-y-4 mb-8">`;
        html += generateTicketCardsHtml(tickets, searchReq);
        html += `</div>`;
    }

    resultsArea.innerHTML = html;
}

// Bilet Kartlarını Profesyonel Formatla Üret (Google Flights & Skyscanner Standardı)
function generateTicketCardsHtml(tickets, searchReq) {
    const isRoundTrip = (searchReq.trip_type === 'round_trip');
    const isEn = window.currentAppLang === 'en';
    const totalPaxText = `${searchReq.passengers || 1} ${isEn ? (searchReq.passengers > 1 ? 'Passengers' : 'Passenger') : 'Yolcu'}`;

    return tickets.map(ticket => {
        const isFlight = (ticket.transport_type === 'flight');
        const directLink = ticket.direct_link || ticket.booking_link || ticket.official_link || '#';
        const currSym = ticket.currency || '₺';
        const formattedTicketPrice = ticket.price ? `${Number(ticket.price).toLocaleString(isEn ? 'en-US' : 'tr-TR')} ${currSym}` : '';
        const winnerChannel = ticket.winner_channel || 'official';
        const winnerLabel = ticket.winner_name || ticket.official_name || ticket.carrier || 'Resmi Kanal';

        let flightActionText = '';
        let flightTargetUrl = ticket.winner_url || directLink;
        if (isFlight) {
            if (isEn && ticket.winner_button_text_en) {
                flightActionText = ticket.winner_button_text_en;
            } else if (ticket.winner_button_text) {
                flightActionText = ticket.winner_button_text;
            } else if (ticket.price) {
                if (winnerChannel === 'trip') {
                    flightActionText = isEn ? `Book on Trip.com (${formattedTicketPrice})` : `Trip.com'dan Al (${formattedTicketPrice})`;
                } else if (winnerChannel === 'booking') {
                    flightActionText = isEn ? `Book on Booking.com (${formattedTicketPrice})` : `Booking'den Al (${formattedTicketPrice})`;
                } else if (winnerChannel === 'skyscanner') {
                    flightActionText = isEn ? `Book on Skyscanner (${formattedTicketPrice})` : `Skyscanner'dan Al (${formattedTicketPrice})`;
                } else if (winnerChannel === 'kiwi') {
                    flightActionText = isEn ? `Book on Kiwi.com (${formattedTicketPrice})` : `Kiwi.com'dan Al (${formattedTicketPrice})`;
                } else if (winnerChannel === 'agency') {
                    flightActionText = isEn ? `Book on ${winnerLabel} (${formattedTicketPrice})` : `${winnerLabel}'dan Al (${formattedTicketPrice})`;
                } else {
                    let carrierBrand = 'Resmi Web';
                    if (ticket.carrier) {
                        const cl = ticket.carrier.toLowerCase();
                        if (cl.includes('pegasus')) carrierBrand = "Pegasus'tan";
                        else if (cl.includes('ajet') || cl.includes('anadolu')) carrierBrand = "AJet'ten";
                        else if (cl.includes('türk') || cl.includes('thy')) carrierBrand = "THY'den";
                        else if (cl.includes('sunexpress')) carrierBrand = "SunExpress'ten";
                        else carrierBrand = `${ticket.carrier}'den`;
                    }
                    flightActionText = isEn ? `Book on ${carrierBrand} (${formattedTicketPrice})` : `${carrierBrand} Al (${formattedTicketPrice})`;
                }
            } else {
                flightActionText = isEn ? 'View Live Fares →' : 'Canlı Seferleri Gör →';
            }
        }

        const actionButtonText = isFlight
            ? flightActionText
            : (isEn
                ? 'Select Ticket →'
                : (ticket.transport_type === 'train'
                    ? `TCDD'de Aç (${ticket.flight_number || 'Sefer'})`
                    : (ticket.transport_type === 'bus'
                        ? `Obilet'te Seç`
                        : `Bileti Al`)));

        if (!isFlight) {
            // Otobüs, Tren, Feribot Kartı
            const isBus = ticket.transport_type === 'bus';
            const isTrain = ticket.transport_type === 'train';
            let typeIcon = isBus ? '🚌' : (isTrain ? '🚆' : '⛴️');
            let typeColor = isBus ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200';

            return `
                <div class="bg-white border-2 border-slate-200 hover:border-amber-400 rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-lg transition-all flex flex-col md:flex-row items-center justify-between gap-4">
                    <div class="flex items-center gap-4 w-full md:w-auto">
                        <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl ${typeColor} border shadow-xs flex-shrink-0">
                            ${ticket.carrier_logo || typeIcon}
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="font-black text-slate-900 text-base">${ticket.carrier}</span>
                                ${ticket.badge ? `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-900 border border-amber-200">${ticket.badge}</span>` : ''}
                            </div>
                            <div class="text-xs text-slate-500 mt-1 flex items-center gap-2 font-medium">
                                <span class="font-bold text-slate-700">${ticket.departure_time || '09:00'}</span>
                                <span>•</span>
                                <span>${ticket.origin} ➔ ${ticket.destination}</span>
                                <span>•</span>
                                <span>${ticket.duration || 'Direkt'}</span>
                            </div>
                            ${ticket.transport_type === 'train' ? `
                                <div class="mt-1.5 text-[10.5px] text-purple-800 bg-purple-50 border border-purple-200/70 rounded-lg px-2.5 py-1 flex items-center gap-1.5 font-medium">
                                    <i class="fa-solid fa-circle-info text-purple-600 shrink-0"></i>
                                    <span><strong>TCDD Resmi Portalı:</strong> Yasal tekel gereği tren biletleri yalnızca TCDD'de satılır.</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="flex items-center justify-between md:justify-end gap-6 w-full md:w-auto border-t md:border-t-0 pt-3 md:pt-0">
                        <div class="text-left md:text-right">
                            <div class="text-[10px] font-black uppercase tracking-wider text-slate-400">Doğrulanmış Fiyat</div>
                            <div class="text-2xl font-black text-[#0F172A]">
                                ${ticket.price ? `${Number(ticket.price).toLocaleString('tr-TR')} ${ticket.currency || '₺'}` : 'Canlı Fiyat'}
                            </div>
                        </div>
                        <a href="${directLink}" target="_blank" rel="noopener noreferrer" class="px-5 py-2.5 bg-gradient-to-r from-[#0F172A] via-[#0284C7] to-[#0284C7] text-white font-black text-xs sm:text-sm rounded-xl shadow-md transition flex items-center gap-2">
                            <span>${actionButtonText}</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i>
                        </a>
                    </div>
                </div>
            `;
        }

        // ==================== UÇUŞ KARTI (Google Flights & Skyscanner Standardı) ====================
        let fromCode = ticket.from_code || '';
        let fromCity = ticket.origin || searchReq.origin;
        const matchFrom = (ticket.origin || '').match(/(.*?)\s*\((.*?)\)/);
        if (matchFrom) { fromCity = matchFrom[1].trim(); fromCode = matchFrom[2].trim(); }

        let toCode = ticket.to_code || '';
        let toCity = ticket.destination || searchReq.destination;
        const matchTo = (ticket.destination || '').match(/(.*?)\s*\((.*?)\)/);
        if (matchTo) { toCity = matchTo[1].trim(); toCode = matchTo[2].trim(); }

        // Bagaj Rozetleri
        const carrierUpper = (ticket.carrier || '').toUpperCase();
        let baggageBadgeHtml = '';
        if (carrierUpper.includes('PEGASUS') || carrierUpper.includes('FLYPGS')) {
            baggageBadgeHtml = `
                <div class="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                        <i class="fa-solid fa-briefcase text-amber-500 text-[10px]"></i> Kabin El Çantası Dahil
                    </span>
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-amber-50 text-amber-900 border border-amber-200/80">
                        <i class="fa-solid fa-suitcase-rolling text-amber-600 text-[10px]"></i> 20 kg Bagaj (Havayolunda +350 ₺'den başlar)
                    </span>
                </div>
            `;
        } else if (carrierUpper.includes('THY') || carrierUpper.includes('TÜRK HAVA') || carrierUpper.includes('TURKISH')) {
            baggageBadgeHtml = `
                <div class="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-emerald-50 text-emerald-900 border border-emerald-200">
                        <i class="fa-solid fa-suitcase-rolling text-emerald-600 text-[10px]"></i> 15 kg Uçak Altı Bagaj Dahil
                    </span>
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                        <i class="fa-solid fa-briefcase text-slate-600 text-[10px]"></i> 8 kg Kabin Bagajı Dahil
                    </span>
                </div>
            `;
        } else if (carrierUpper.includes('AJET') || carrierUpper.includes('ANADOLUJET')) {
            baggageBadgeHtml = `
                <div class="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-emerald-50 text-emerald-900 border border-emerald-200">
                        <i class="fa-solid fa-suitcase-rolling text-emerald-600 text-[10px]"></i> 15 kg Standart Bagaj Dahil
                    </span>
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                        <i class="fa-solid fa-briefcase text-slate-600 text-[10px]"></i> Kabin Çantası Dahil
                    </span>
                </div>
            `;
        } else {
            baggageBadgeHtml = `
                <div class="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                        <i class="fa-solid fa-suitcase-rolling text-amber-500 text-[10px]"></i> Standart Havayolu Bagaj Politikası
                    </span>
                </div>
            `;
        }

        // 2. Bacak: Dönüş Uçuşu Bloğu (Yalnızca gerçek canlı dönüş seferi çekildiyse gösterilir, uydurma saat basılmaz)
        let returnLegHtml = '';
        if (isRoundTrip && ticket.return_leg) {
            const retLeg = ticket.return_leg;

            returnLegHtml = `
                <div class="bg-slate-50/80 p-3.5 sm:p-4 rounded-2xl border border-slate-200">
                    <div class="text-[11px] font-black text-slate-700 mb-2.5 flex items-center justify-between">
                        <span class="flex items-center gap-1.5 text-blue-700 font-black">
                            <i class="fa-solid fa-plane-arrival"></i> 🛬 DÖNÜŞ UÇUŞU • ${retLeg.departure_date_formatted || searchReq.return_date}
                        </span>
                        <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                            ${retLeg.flight_number || 'Dönüş Seferi'}
                        </span>
                    </div>
                    <div class="grid grid-cols-12 items-center gap-2">
                        <div class="col-span-4 sm:col-span-3 text-left">
                            <div class="text-xl sm:text-2xl font-black text-slate-900 leading-none">${retLeg.departure_time}</div>
                            <div class="text-xs font-black text-blue-700 mt-1 truncate">${retLeg.from_code || toCode}</div>
                            <div class="text-[11px] text-slate-500 font-semibold truncate">${toCity}</div>
                        </div>
                        <div class="col-span-4 sm:col-span-6 px-1 text-center">
                            <div class="text-xs font-bold text-slate-600 mb-1.5">${retLeg.duration || ticket.duration}</div>
                            <div class="relative flex items-center justify-center my-1">
                                <div class="w-full h-[2px] bg-slate-300"></div>
                                <div class="absolute bg-white px-2 py-0.5 rounded-full border border-slate-300 shadow-2xs">
                                    <i class="fa-solid fa-plane text-blue-600 text-[10px] transform rotate-180"></i>
                                </div>
                            </div>
                            <div class="text-[10.5px] font-bold text-emerald-600 mt-1.5">
                                ${retLeg.is_direct !== false ? '✓ Direkt • Aktarmasız' : '1 Aktarma'}
                            </div>
                        </div>
                        <div class="col-span-4 sm:col-span-3 text-right">
                            <div class="text-xl sm:text-2xl font-black text-slate-900 leading-none">${retLeg.arrival_time}</div>
                            <div class="text-xs font-black text-blue-700 mt-1 truncate">${retLeg.to_code || fromCode}</div>
                            <div class="text-[11px] text-slate-500 font-semibold truncate">${fromCity}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        return `
            <div class="bg-white border-2 border-slate-200 hover:border-amber-400 rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-xl transition-all mb-4">
                <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-6">
                    
                    <!-- Sol/Orta Detay Bloğu -->
                    <div class="flex-1 space-y-3.5">
                        
                        <!-- Havayolu & Sefer Başlığı -->
                        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                            <div class="flex items-center gap-3">
                                <div class="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-600 flex items-center justify-center font-bold text-base shadow-2xs">
                                    ✈️
                                </div>
                                <div class="flex items-center gap-2">
                                    <span class="font-black text-slate-900 text-sm sm:text-base">${ticket.carrier}</span>
                                    <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px] font-mono font-bold border border-slate-200">${ticket.flight_number || 'Tarifeli Sefer'}</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                ${ticket.badge ? `<span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-amber-100 text-amber-900 border border-amber-200">${ticket.badge}</span>` : ''}
                                <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-bold bg-slate-100 text-slate-700 border border-slate-200">${searchReq.cabin_class === 'business' ? 'Business' : 'Ekonomi'}</span>
                            </div>
                        </div>

                        <!-- 1. Bacak: GİDİŞ UÇUŞU SAATLERİ (Google Flights Standardı) -->
                        <div class="bg-slate-50/80 p-3.5 sm:p-4 rounded-2xl border border-slate-200">
                            ${isRoundTrip ? `
                                <div class="text-[11px] font-black text-slate-700 mb-2.5 flex items-center justify-between">
                                    <span class="flex items-center gap-1.5 text-amber-700 font-black">
                                        <i class="fa-solid fa-plane-departure"></i> 🛫 GİDİŞ UÇUŞU • ${ticket.departure_date_formatted || searchReq.departure_date}
                                    </span>
                                    <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                                        ${ticket.flight_number || 'Gidiş Seferi'}
                                    </span>
                                </div>
                            ` : ''}
                            <div class="grid grid-cols-12 items-center gap-2">
                                <div class="col-span-4 sm:col-span-3 text-left">
                                    <div class="text-2xl sm:text-3xl font-black text-slate-900 leading-none">${ticket.departure_time || '08:45'}</div>
                                    <div class="text-xs font-black text-amber-600 mt-1 truncate">${fromCode || 'Kalkış'}</div>
                                    <div class="text-[11px] text-slate-500 font-semibold truncate">${fromCity}</div>
                                </div>
                                <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                    <div class="text-xs font-bold text-slate-600 mb-1.5">${ticket.duration || '1 sa 15 dk'}</div>
                                    <div class="relative flex items-center justify-center my-1">
                                        <div class="w-full h-[2px] bg-slate-300"></div>
                                        <div class="absolute bg-white px-2 py-0.5 rounded-full border border-slate-300 shadow-2xs">
                                            <i class="fa-solid fa-plane text-amber-500 text-[10px]"></i>
                                        </div>
                                    </div>
                                    <div class="text-[10.5px] font-bold ${ticket.is_direct !== false ? 'text-emerald-600' : 'text-amber-600'} mt-1.5">
                                        ${ticket.is_direct !== false ? '✓ Direkt • Aktarmasız' : '1 Aktarma'}
                                    </div>
                                </div>
                                <div class="col-span-4 sm:col-span-3 text-right">
                                    <div class="text-2xl sm:text-3xl font-black text-slate-900 leading-none">${ticket.arrival_time || '10:00'}</div>
                                    <div class="text-xs font-black text-amber-600 mt-1 truncate">${toCode || 'Varış'}</div>
                                    <div class="text-[11px] text-slate-500 font-semibold truncate">${toCity}</div>
                                </div>
                            </div>
                        </div>

                        <!-- 2. Bacak: DÖNÜŞ UÇUŞU SAATLERİ (Gidiş-Dönüş ise) -->
                        ${returnLegHtml}

                        <!-- Bagaj Rozetleri -->
                        ${baggageBadgeHtml}

                        <!-- Biletleme ve Sağlayıcı Seçenekleri (Yalnızca Doğrulanmış Fiyatlar veya Doğrudan Sefer Ekranı) -->
                        ${(ticket.providers && ticket.providers.length > 0) || ticket.hotel_link ? `
                            <div class="pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-2 text-[11px]">
                                <span class="text-slate-500 font-black text-[10px] uppercase flex items-center gap-1">
                                    <i class="fa-solid fa-cart-shopping text-amber-500"></i> Biletleme Seçenekleri:
                                </span>
                                ${(ticket.providers || []).map(p => {
                                    const hasVerifiedPrice = (p.price !== null && p.price !== undefined && Number(p.price) > 0);
                                    let pillClass = 'bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 font-bold';
                                    let icon = '';
                                    if (p.is_best && hasVerifiedPrice) {
                                        pillClass = 'bg-amber-50 text-amber-900 border border-amber-300 font-black shadow-2xs hover:bg-amber-100';
                                    } else if (p.channel === 'trip' || (p.name && p.name.includes('Trip.com'))) {
                                        pillClass = 'bg-sky-50 text-sky-950 border border-sky-300 font-bold shadow-2xs hover:bg-sky-100';
                                        icon = '<i class="fa-solid fa-plane text-sky-600 text-[9px]"></i> ';
                                    } else if (p.channel === 'kiwi') {
                                        pillClass = 'bg-teal-50 text-teal-950 border border-teal-300 font-bold shadow-2xs hover:bg-teal-100';
                                        icon = '<i class="fa-solid fa-bolt text-teal-600 text-[9px]"></i> ';
                                    } else if (p.channel === 'booking') {
                                        pillClass = 'bg-blue-50 text-blue-950 border border-blue-300 font-bold shadow-2xs hover:bg-blue-100';
                                        icon = '<i class="fa-solid fa-plane-departure text-blue-700 text-[9px]"></i> ';
                                    } else if (p.channel === 'skyscanner') {
                                        pillClass = 'bg-cyan-50 text-cyan-950 border border-cyan-300 font-bold shadow-2xs hover:bg-cyan-100';
                                        icon = '<i class="fa-solid fa-compass text-cyan-700 text-[9px]"></i> ';
                                    }
                                    let priceText = '';
                                    if (hasVerifiedPrice) {
                                        priceText = `${Number(p.price).toLocaleString(isEn ? 'en-US' : 'tr-TR')} ${currSym}`;
                                    } else if (p.channel === 'trip') {
                                        priceText = isEn ? 'View Live Fare' : 'Canlı Fiyatı Gör';
                                    } else if (p.channel === 'agency') {
                                        priceText = isEn ? 'View on Enuygun' : 'Seferi Gör';
                                    } else if (p.channel === 'booking') {
                                        priceText = isEn ? 'Check Fare' : 'Fiyata Bak';
                                    } else if (p.channel === 'skyscanner') {
                                        priceText = isEn ? 'Verify' : 'Teyit Et';
                                    } else {
                                        priceText = isEn ? 'Select' : 'Seç';
                                    }
                                    return `
                                    <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl ${pillClass} transition" title="${p.name} üzerinden canlı sefer ve fiyat kontrolü">
                                         <span>${icon}${p.name}</span>
                                         <span class="${(p.is_best && hasVerifiedPrice) ? 'text-amber-800' : (p.channel === 'trip' ? 'text-sky-700' : (p.channel === 'kiwi' ? 'text-teal-800' : (p.channel === 'booking' ? 'text-blue-800' : (p.channel === 'skyscanner' ? 'text-cyan-800' : 'text-slate-900'))))} font-black">${priceText}</span>
                                         <i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-70"></i>
                                    </a>
                                    `;
                                }).join('')}
                                ${ticket.hotel_link ? `
                                    <a href="${ticket.hotel_link}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-blue-50 text-blue-900 border border-blue-200 hover:bg-blue-100 font-bold transition">
                                        <span>🏨 ${toCity} ${isEn ? 'Hotels (Booking.com)' : 'Otelleri (Booking.com)'}</span>
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-70"></i>
                                    </a>
                                ` : ''}
                            </div>
                        ` : ''}

                    </div>

                    <!-- Sağ Taraf: Fiyat & Bilet Satın Alma Butonu -->
                    <div class="lg:w-64 border-t lg:border-t-0 lg:border-l border-slate-200/90 pt-4 lg:pt-0 lg:pl-6 flex flex-row lg:flex-col items-center lg:items-end justify-between lg:justify-center gap-3">
                        <div class="text-left lg:text-right">
                            <div class="text-[10.5px] font-black uppercase tracking-wider text-slate-400">
                                ${isRoundTrip ? (isEn ? 'Round-Trip Total' : 'Gidiş-Dönüş Toplam') : (isEn ? 'One-Way Net Fare' : 'Tek Yön Net Fiyat')}
                            </div>
                            <div class="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
                                ${ticket.price ? `${Number(ticket.price).toLocaleString(isEn ? 'en-US' : 'tr-TR')} ${ticket.currency || '₺'}` : (isEn ? 'Live Fare' : 'Canlı Fiyat')}
                            </div>
                            <div class="text-[10px] text-slate-500 font-medium mt-0.5">
                                ${totalPaxText} ${isEn ? 'total' : 'için toplam'}${isRoundTrip && ticket.price ? ` <span class="text-amber-700 font-semibold">(${isEn ? 'One-way avg.' : 'Tek yön ort.'} ~${Math.round(ticket.price / (searchReq.passengers || 1) / 2).toLocaleString(isEn ? 'en-US' : 'tr-TR')} ₺)</span>` : ''}
                            </div>
                        </div>

                        <a href="${flightTargetUrl}" target="_blank" rel="noopener noreferrer" 
                           class="px-6 py-3 bg-gradient-to-r from-amber-500 via-orange-500 to-amber-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-black text-xs sm:text-sm rounded-2xl shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5 flex items-center justify-center gap-2 shrink-0">
                            <span>${actionButtonText}</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i>
                        </a>
                        
                        <div class="hidden lg:flex flex-col items-end gap-0.5 text-[9.5px] text-slate-400">
                            <div class="flex items-center gap-1 text-emerald-600 font-bold">
                                <i class="fa-solid fa-shield-check"></i>
                                <span>${isEn ? 'Official Partner Booking' : 'Resmi Partner Yönlendirmesi'}</span>
                            </div>
                            <span class="italic text-slate-400">${isEn ? '*Direct checkout via Trip.com & official airline portal.' : '*Trip.com ve resmi havayolu güvencesiyle doğrudan rezervasyon.'}</span>
                        </div>
                    </div>

                </div>
            </div>
        `;
    }).join("");
}

// Hızlı Uçuş Sıralama ve Filtreleme Sistemi (En Ucuz | En Hızlı | En Erken Kalkış | En Geç Kalkış + Sabah / Öğle / Akşam)
window.currentFlightSort = 'cheapest';
window.currentFlightTimeFilter = 'all';
window.currentFlightAirportFilter = 'all';

function setFlightSort(sortKey) {
    window.currentFlightSort = sortKey;
    applyFlightSortAndFilter();
}

function setFlightTimeFilter(timeKey) {
    window.currentFlightTimeFilter = timeKey;
    applyFlightSortAndFilter();
}

function setFlightAirportFilter(portKey) {
    window.currentFlightAirportFilter = portKey;
    applyFlightSortAndFilter();
}

function sortFlightTickets(criterion) {
    if (['cheapest', 'fastest', 'earliest', 'latest'].includes(criterion)) {
        setFlightSort(criterion);
    } else if (['all', 'morning', 'noon', 'evening'].includes(criterion)) {
        setFlightTimeFilter(criterion);
    }
}

function applyFlightSortAndFilter() {
    if (!window.lastTransportResults) return;
    let list = [...window.lastTransportResults];

    // 0. Havalimanı Filtresi (SAW vs IST)
    if (window.currentFlightAirportFilter === 'SAW') {
        list = list.filter(t => 
            (t.from_code && t.from_code.toUpperCase() === 'SAW') || 
            (t.to_code && t.to_code.toUpperCase() === 'SAW') || 
            (t.origin && t.origin.includes('SAW')) || 
            (t.destination && t.destination.includes('SAW'))
        );
    } else if (window.currentFlightAirportFilter === 'IST') {
        list = list.filter(t => 
            (t.from_code && t.from_code.toUpperCase() === 'IST') || 
            (t.to_code && t.to_code.toUpperCase() === 'IST') || 
            (t.origin && t.origin.includes('IST')) || 
            (t.destination && t.destination.includes('IST'))
        );
    }

    // 1. Saat Filtresi Uygula (00-06 Gece, 06-12 Sabah, 12-18 Öğle, 18+ Akşam)
    if (window.currentFlightTimeFilter === 'night') {
        list = list.filter(t => {
            const h = parseInt((t.departure_time || '12:00').split(':')[0], 10);
            return h < 6;
        });
    } else if (window.currentFlightTimeFilter === 'morning') {
        list = list.filter(t => {
            const h = parseInt((t.departure_time || '12:00').split(':')[0], 10);
            return h >= 6 && h < 12;
        });
    } else if (window.currentFlightTimeFilter === 'noon') {
        list = list.filter(t => {
            const h = parseInt((t.departure_time || '12:00').split(':')[0], 10);
            return h >= 12 && h < 18;
        });
    } else if (window.currentFlightTimeFilter === 'evening') {
        list = list.filter(t => {
            const h = parseInt((t.departure_time || '12:00').split(':')[0], 10);
            return h >= 18;
        });
    }

    // 2. Sıralama Uygula (En Ucuz, En Hızlı, En Erken Kalkış, En Geç Kalkış)
    const parseMins = (timeStr) => {
        if (!timeStr) return 0;
        const parts = timeStr.split(':');
        return (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
    };

    const getDurMins = (dur) => {
        if (!dur) return 999;
        const h = dur.match(/(\d+)\s*sa/);
        const m = dur.match(/(\d+)\s*dk/);
        return (h ? parseInt(h[1], 10) * 60 : 0) + (m ? parseInt(m[1], 10) : 0);
    };

    if (window.currentFlightSort === 'cheapest') {
        // En ucuz biletler; fiyatlar eşitse en erken saat en başa gelsin (00:20 -> 06:25 -> 12:00)
        list.sort((a, b) => {
            const pDiff = (Number(a.price) || 0) - (Number(b.price) || 0);
            if (Math.abs(pDiff) > 0.01) return pDiff;
            return parseMins(a.departure_time) - parseMins(b.departure_time);
        });
    } else if (window.currentFlightSort === 'fastest') {
        list.sort((a, b) => getDurMins(a.duration) - getDurMins(b.duration));
    } else if (window.currentFlightSort === 'earliest') {
        // En Erken Kalkış: 00:00'dan 23:59'a doğru artan sıra
        list.sort((a, b) => parseMins(a.departure_time) - parseMins(b.departure_time));
    } else if (window.currentFlightSort === 'latest') {
        // En Geç Kalkış: 23:59'dan 00:00'a doğru azalan sıra
        list.sort((a, b) => parseMins(b.departure_time) - parseMins(a.departure_time));
    }

    // 3. Sıralama Buton Stillerini Güncelle
    document.querySelectorAll(".flt-sort-btn").forEach(b => {
        b.className = "flt-sort-btn px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer";
    });
    const activeSortBtn = document.getElementById(`fltSort-${window.currentFlightSort}`);
    if (activeSortBtn) {
        activeSortBtn.className = "flt-sort-btn px-3 py-1.5 rounded-xl text-xs font-black bg-slate-900 text-white shadow-xs transition cursor-pointer";
    }

    // 4. Zaman Filtre Buton Stillerini Güncelle
    document.querySelectorAll(".flt-time-btn").forEach(b => {
        b.className = "flt-time-btn px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer";
    });
    const activeTimeBtn = document.getElementById(`fltTime-${window.currentFlightTimeFilter}`);
    if (activeTimeBtn) {
        activeTimeBtn.className = "flt-time-btn px-2.5 py-1 rounded-lg text-xs font-black bg-amber-500 text-white shadow-xs transition cursor-pointer";
    }

    // 5. Havalimanı Filtre Buton Stillerini Güncelle
    document.querySelectorAll(".flt-port-btn").forEach(b => {
        b.className = "flt-port-btn px-3 py-1 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer";
    });
    const activePortBtn = document.getElementById(`fltPort-${window.currentFlightAirportFilter}`);
    if (activePortBtn) {
        activePortBtn.className = "flt-port-btn px-3 py-1 rounded-xl text-xs font-black bg-slate-900 text-white shadow-2xs transition cursor-pointer";
    }

    // Sayaç Rozetini Güncelle
    const countBadge = document.getElementById("fltCountBadge");
    if (countBadge) {
        countBadge.textContent = `(${list.length} uçuş)`;
    }

    // 5. Kartları Render Et
    const container = document.getElementById("ticketCardsContainer");
    if (container) {
        if (list.length === 0) {
            container.innerHTML = `
                <div class="bg-amber-50/50 p-8 rounded-3xl border border-amber-200/80 text-center shadow-xs">
                    <i class="fa-regular fa-clock text-2xl text-amber-500 mb-2"></i>
                    <div class="font-bold text-slate-800 text-sm">Seçilen zaman diliminde sefer bulunamadı.</div>
                    <div class="text-xs text-slate-500 mt-1">Tüm uçuşları görmek için <strong>'Tümü'</strong> veya <strong>'En Erken Kalkış'</strong> butonuna tıklayabilirsiniz.</div>
                </div>
            `;
        } else {
            container.innerHTML = generateTicketCardsHtml(list, window.lastSearchReq);
        }
    }
}

// 5. OTEL ARAMASI ÇALIŞTIRMA (ÇİFT YÖNLÜ ÇAPRAZ SATIŞ: OTEL ➔ MULTI-MODAL ULAŞIM)
async function executeHotelSearch(e) {
    if (e) e.preventDefault();

    const city = document.getElementById("hotelCity").value.trim();
    const cin = document.getElementById("hotelCheckin").value;
    const cout = document.getElementById("hotelCheckout").value;
    const guests = document.getElementById("hotelGuests").value;

    if (!city || !cin || !cout) {
        alert("Lütfen şehir ve giriş-çıkış tarihlerini seçiniz.");
        return;
    }

    const resultsArea = document.getElementById("hotelResultsArea");
    resultsArea.innerHTML = `
        <div class="p-12 text-center bg-gradient-to-b from-amber-50/50 to-white rounded-3xl border border-amber-200/60 shadow-xs">
            <div class="inline-block w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <div class="text-lg font-black text-slate-800">${city} Otelleri ve Ulaşım Seçenekleri Canlı Taranıyor...</div>
            <div class="text-xs text-slate-500 mt-1.5 font-medium">Uçak, tren, otobüs ve feribot alternatifleri ile canlı otel odaları sorgulanıyor.</div>
        </div>
    `;
    resultsArea.classList.remove("hidden");
    resultsArea.scrollIntoView({ behavior: "smooth", block: "nearest" });

    try {
        const payload = {
            origin: "İstanbul",
            destination: city,
            departure_date: cin,
            return_date: cout,
            passengers: parseInt(guests) || 2,
            transport_type: "all", // Tüm ulaşım modlarını (uçak, tren, otobüs, feribot) aynı anda sorgula
            trip_type: "round_trip",
            include_hotel: true,
            currency: activeCurrency
        };

        const res = await fetch("/api/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        renderHotelResults(data.hotel_info, city, cin, cout, guests, data);
    } catch (err) {
        resultsArea.innerHTML = `
            <div class="p-8 text-center bg-rose-50 border border-rose-200 rounded-3xl text-rose-800">
                <i class="fa-solid fa-circle-exclamation text-2xl mb-2 text-rose-500"></i>
                <div class="font-bold">Otel araması sırasında bir hata oluştu.</div>
                <div class="text-xs mt-1 text-rose-600">${err.message}</div>
            </div>
        `;
    }
}

// OTEL ARAMA SONUÇLARI: MULTI-MODAL ULAŞIM BANDI + KOMBİNE SEPET + CANLI OTELLER
function renderHotelResults(hotelInfo, city, cin, cout, guests, data) {
    const resultsArea = document.getElementById("hotelResultsArea");
    if (!hotelInfo) {
        resultsArea.innerHTML = `
            <div class="bg-white p-10 rounded-3xl border border-slate-200 text-center shadow-xs">
                <div class="font-black text-lg text-slate-800">${city} için resmi arama linki hazırlandı.</div>
                <div class="mt-4">
                    <a href="https://www.booking.com/searchresults.tr.html?ss=${encodeURIComponent(city)}&checkin=${cin}&checkout=${cout}&aid=585474" target="_blank" class="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-black rounded-xl inline-flex items-center gap-2 shadow-md">
                        <span>Booking.com'da Canlı Odaları Aç</span>
                        <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    </a>
                </div>
            </div>
        `;
        return;
    }

    const isIntl = hotelInfo.is_international;
    const bookingUrl = hotelInfo.booking_url || `https://www.booking.com/searchresults.tr.html?ss=${encodeURIComponent(city)}&checkin=${cin}&checkout=${cout}&aid=585474`;
    const enuygunUrl = isIntl ? null : hotelInfo.enuygun_url;
    const liveHotels = hotelInfo.live_hotels || [];
    const topHotel = liveHotels.length > 0 ? liveHotels[0] : null;

    const tickets = (data && data.tickets) ? data.tickets : [];
    const deepLinks = (data && data.deep_links) ? data.deep_links : {};

    // Ulaşım Modlarını Ayrıştır
    let lowestFlight = null;
    const flightTickets = tickets.filter(t => t.transport_type === 'flight');
    if (flightTickets.length > 0) {
        const priced = flightTickets.filter(t => t.price && t.price > 0);
        lowestFlight = priced.length > 0 ? priced.reduce((prev, curr) => (curr.price < prev.price ? curr : prev), priced[0]) : flightTickets[0];
    }

    let lowestTrain = null;
    const trainTickets = tickets.filter(t => t.transport_type === 'train');
    if (trainTickets.length > 0) {
        const priced = trainTickets.filter(t => t.price && t.price > 0);
        lowestTrain = priced.length > 0 ? priced.reduce((prev, curr) => (curr.price < prev.price ? curr : prev), priced[0]) : trainTickets[0];
    }

    let lowestBus = null;
    const busTickets = tickets.filter(t => t.transport_type === 'bus');
    if (busTickets.length > 0) {
        const priced = busTickets.filter(t => t.price && t.price > 0);
        lowestBus = priced.length > 0 ? priced.reduce((prev, curr) => (curr.price < prev.price ? curr : prev), priced[0]) : busTickets[0];
    }

    let lowestFerry = null;
    const ferryTickets = tickets.filter(t => t.transport_type === 'ferry');
    if (ferryTickets.length > 0) {
        const priced = ferryTickets.filter(t => t.price && t.price > 0);
        lowestFerry = priced.length > 0 ? priced.reduce((prev, curr) => (curr.price < prev.price ? curr : prev), priced[0]) : ferryTickets[0];
    }

    // Kombine sepet hesaplaması (En Uygun Ulaşım + Otel)
    const bestTransport = lowestFlight || lowestTrain || lowestBus || lowestFerry;
    let transportPrice = bestTransport && bestTransport.price ? Number(bestTransport.price) : 0;
    let hotelNightly = topHotel && topHotel.nightly_price ? Number(topHotel.nightly_price) : (topHotel && topHotel.price ? Number(topHotel.price) : 0);
    let hotelTotal = topHotel && topHotel.total_price ? Number(topHotel.total_price) : (hotelNightly * (hotelInfo.nights || 2));
    let combinedTotal = transportPrice + hotelTotal;

    const bookingCityLink = hotelInfo.booking_url || `https://www.booking.com/searchresults.tr.html?ss=${encodeURIComponent(city)}&checkin=${cin}&checkout=${cout}&group_adults=${guests}&no_rooms=1&aid=585474&label=hakikibilet_kombine`;

    let html = `
        <!-- 🧭 MULTI-MODAL ULAŞIM ALTERNATİFLERİ BANDI (ÇİFT YÖNLÜ ÇAPRAZ SATIŞ) -->
        <div class="mb-6 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border border-slate-700/80 rounded-3xl p-5 sm:p-6 text-white shadow-xl">
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-700/80 pb-4 mb-4">
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-400 text-slate-950">
                            🧭 Şehre Ulaşım Alternatifleri
                        </span>
                        <span class="text-xs text-slate-400 font-bold">${city} Seyahatiniz İçin Ulaşım Seçenekleri</span>
                    </div>
                    <h4 class="text-base sm:text-lg font-black text-white">${city} Şehrine Nasıl Gidilir? (Doğrulanmış Taban Fiyatlar)</h4>
                </div>
                <button onclick="prefillTransportAndSwitch('İstanbul', '${city}', '${cin}', '${cout}')" class="px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-amber-300 font-bold text-xs rounded-xl transition flex items-center gap-1.5 shrink-0">
                    <span>Tüm Sefer Saatlerini Listele ▾</span>
                </button>
            </div>

            <!-- Mod Kartları Grid (Uçak, Tren, Otobüs, Feribot) -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                <!-- 1. UÇAK -->
                ${lowestFlight ? `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-amber-400/80 transition flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between text-xs mb-1.5">
                                <span class="font-black text-amber-400 flex items-center gap-1.5">✈️ Uçuş</span>
                                <span class="text-[10px] text-slate-400">${lowestFlight.duration || 'Direkt'}</span>
                            </div>
                            <div class="font-bold text-xs text-white line-clamp-1">${lowestFlight.carrier}</div>
                            <div class="text-lg font-black text-amber-300 mt-2">${lowestFlight.price ? lowestFlight.price + ' ' + (lowestFlight.currency || '₺') : 'Canlı Fiyat'}</div>
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-white/10">
                            <a href="${lowestFlight.direct_link || '#'}" target="_blank" rel="noopener noreferrer" class="w-full py-2 px-3 text-center bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                <span>Doğrudan Al ↗</span>
                            </a>
                        </div>
                    </div>
                ` : `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/5 text-slate-500 flex flex-col justify-between">
                        <div class="text-xs font-black text-slate-400 flex items-center gap-1.5">✈️ Uçak</div>
                        <div class="text-[11px] text-slate-500 my-2">Havalimanı veya direkt hat bulunmuyor.</div>
                        <div class="text-[10px] text-slate-600">Kara/Deniz tercih edin</div>
                    </div>
                `}

                <!-- 2. HIZLI TREN (YHT) -->
                ${lowestTrain ? `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-purple-400/80 transition flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between text-xs mb-1.5">
                                <span class="font-black text-purple-300 flex items-center gap-1.5">🚆 YHT Hızlı Tren</span>
                                <span class="text-[10px] text-slate-400">${lowestTrain.duration || 'YHT'}</span>
                            </div>
                            <div class="font-bold text-xs text-white line-clamp-1">TCDD Taşımacılık</div>
                            <div class="text-lg font-black text-purple-200 mt-2">${lowestTrain.price ? lowestTrain.price + ' ' + (lowestTrain.currency || '₺') : '430 ₺'}</div>
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-white/10">
                            <a href="${lowestTrain.direct_link || (deepLinks.train && deepLinks.train.tcdd) || 'https://ebilet.tcddtasimacilik.gov.tr/'}" target="_blank" rel="noopener noreferrer" class="w-full py-2 px-3 text-center bg-purple-600 hover:bg-purple-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                <span>Doğrudan Al ↗</span>
                            </a>
                        </div>
                    </div>
                ` : `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/5 text-slate-500 flex flex-col justify-between">
                        <div class="text-xs font-black text-slate-400 flex items-center gap-1.5">🚆 Tren (YHT)</div>
                        <div class="text-[11px] text-slate-500 my-2">${isIntl ? 'Uluslararası demiryolu' : 'Bu hatta tren hattı bulunmamaktadır.'}</div>
                        <div class="text-[10px] text-slate-600">Otobüs/Uçak mevcut</div>
                    </div>
                `}

                <!-- 3. OTOBÜS -->
                ${lowestBus ? `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-emerald-400/80 transition flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between text-xs mb-1.5">
                                <span class="font-black text-emerald-400 flex items-center gap-1.5">🚌 Otobüs</span>
                                <span class="text-[10px] text-slate-400">${lowestBus.duration || 'Ekspres'}</span>
                            </div>
                            <div class="font-bold text-xs text-white line-clamp-1">${lowestBus.carrier || 'Kamil Koç / Obilet'}</div>
                            <div class="text-lg font-black text-emerald-300 mt-2">${lowestBus.price ? lowestBus.price + ' ' + (lowestBus.currency || '₺') : 'Canlı Fiyat'}</div>
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-white/10">
                            <a href="${lowestBus.direct_link || (deepLinks.bus && deepLinks.bus.obilet) || '#'}" target="_blank" rel="noopener noreferrer" class="w-full py-2 px-3 text-center bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                <span>Doğrudan Al ↗</span>
                            </a>
                        </div>
                    </div>
                ` : `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/5 text-slate-500 flex flex-col justify-between">
                        <div class="text-xs font-black text-slate-400 flex items-center gap-1.5">🚌 Otobüs</div>
                        <div class="text-[11px] text-slate-500 my-2">Doğrudan karayolu hattı yok.</div>
                        <div class="text-[10px] text-slate-600">Uçak tercih edin</div>
                    </div>
                `}

                <!-- 4. FERİBOT / DENİZ YOLU -->
                ${lowestFerry ? `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-cyan-400/80 transition flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between text-xs mb-1.5">
                                <span class="font-black text-cyan-300 flex items-center gap-1.5">⛴️ Feribot</span>
                                <span class="text-[10px] text-slate-400">${lowestFerry.duration || 'Hızlı'}</span>
                            </div>
                            <div class="font-bold text-xs text-white line-clamp-1">${lowestFerry.carrier || 'Ertürk / Feribotlines'}</div>
                            <div class="text-lg font-black text-cyan-200 mt-2">${lowestFerry.price ? lowestFerry.price + ' ' + (lowestFerry.currency || '₺') : '35 €'}</div>
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-white/10">
                            <a href="${lowestFerry.direct_link || (deepLinks.ferry && deepLinks.ferry.erturk) || '#'}" target="_blank" rel="noopener noreferrer" class="w-full py-2 px-3 text-center bg-cyan-600 hover:bg-cyan-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                <span>Doğrudan Al ↗</span>
                            </a>
                        </div>
                    </div>
                ` : `
                    <div class="p-4 rounded-2xl bg-white/5 border border-white/5 text-slate-500 flex flex-col justify-between">
                        <div class="text-xs font-black text-slate-400 flex items-center gap-1.5">⛴️ Feribot</div>
                        <div class="text-[11px] text-slate-500 my-2">Deniz kıyısı veya ada hattı değil.</div>
                        <div class="text-[10px] text-slate-600">Uçak/Tren tercih edin</div>
                    </div>
                `}
            </div>
        </div>

        <!-- 🎒 KOMBİNE SEYAHAT SEPETİ (Ulaşım + Otel) -->
        ${(bestTransport && topHotel) ? `
        <div class="mb-8 bg-gradient-to-b from-white to-amber-50/20 border-2 border-amber-300/80 rounded-3xl p-6 shadow-lg relative overflow-hidden">
            <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5 pb-5 border-b border-amber-100">
                <div>
                    <div class="flex items-center gap-2 mb-1.5">
                        <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-400 text-slate-950 shadow-xs">
                            🎒 Akıllı Kombine Paket
                        </span>
                        <span class="text-xs text-slate-500 font-bold">${city} Seyahati (${hotelInfo.nights || 2} Gece • ${guests} Kişi)</span>
                    </div>
                    <h3 class="text-xl font-black text-slate-900 leading-snug">Ulaşım + Otel Birlikte Planlayın</h3>
                    <div class="flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-slate-700 mt-2 font-medium">
                        <span class="inline-flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-2xs">
                            ${bestTransport.transport_type === 'flight' ? '✈️' : (bestTransport.transport_type === 'train' ? '🚆' : (bestTransport.transport_type === 'bus' ? '🚌' : '⛴️'))} 
                            <strong>Ulaşım:</strong> ${bestTransport.carrier} (${bestTransport.price ? bestTransport.price + ' ₺' : 'Canlı Fiyat'})
                        </span>
                        <span class="text-slate-400 font-bold">+</span>
                        <span class="inline-flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-2xs">
                            🏨 <strong>Otel:</strong> ${topHotel.name} (${topHotel.total_price_formatted || (hotelTotal.toLocaleString('tr-TR') + ' ₺')})
                        </span>
                    </div>
                </div>

                <div class="text-left lg:text-right">
                    <div class="text-[10.5px] font-black uppercase tracking-wider text-slate-400">Tahmini Toplam Paket Tutarı</div>
                    <div class="text-2xl sm:text-3xl font-black text-[#0F172A]">${combinedTotal ? combinedTotal.toLocaleString('tr-TR') + ' ₺' : 'Canlı Fiyat'}</div>
                    <div class="text-[10px] text-emerald-600 font-bold mt-0.5 flex items-center lg:justify-end gap-1">
                        <i class="fa-solid fa-shield-check"></i>
                        <span>Sıfır Komisyon • Doğrudan Resmi Biletleme</span>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
                <div class="p-4 sm:p-5 rounded-2xl bg-white border border-amber-200 shadow-xs flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between mb-1.5">
                            <span class="font-black text-xs sm:text-sm text-slate-900 flex items-center gap-1.5">
                                ⚡ 1. Seçenek: 2 Tıkla Doğrudan Al
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-black bg-amber-100 text-amber-900 border border-amber-200">En Ekonomik • Sıfır Komisyon</span>
                        </div>
                        <p class="text-[11px] text-slate-600 leading-relaxed font-normal">
                            Ulaşımı doğrudan resmi taşıyıcıdan (${bestTransport.price ? bestTransport.price + ' ₺' : 'resmi ekran'}), oteli ${hotelInfo.is_international ? "Booking.com'dan" : "Agoda / Enuygun'dan"} en dip fiyattan aracı komisyonu olmadan alın.
                        </p>
                    </div>
                    <div class="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
                        <a href="${bestTransport.direct_link || '#'}" target="_blank" rel="noopener noreferrer" class="w-1/2 py-2.5 px-3 text-center bg-slate-900 hover:bg-black text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                            <span>${bestTransport.transport_type === 'flight' ? '✈️ Ulaşımı Al' : (bestTransport.transport_type === 'train' ? '🚆 Treni Al' : (bestTransport.transport_type === 'bus' ? '🚌 Otobüsü Al' : '⛴️ Feribotu Al'))}</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                        </a>
                        <a href="${topHotel ? (topHotel.booking_url || topHotel.direct_url) : (hotelInfo.primary_city_url || bookingCityLink)}" target="_blank" rel="noopener noreferrer" class="w-1/2 py-2.5 px-3 text-center bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                            <span>🏨 Odayı Al</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                        </a>
                    </div>
                </div>

                <div class="p-4 sm:p-5 rounded-2xl bg-white border border-blue-200 shadow-xs flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between mb-1.5">
                            <span class="font-black text-xs sm:text-sm text-slate-900 flex items-center gap-1.5">
                                🏨 2. Seçenek: Tüm Otelleri Karşılaştır
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-black bg-blue-100 text-blue-900 border border-blue-200">Canlı Otel Arama</span>
                        </div>
                        <p class="text-[11px] text-slate-600 leading-relaxed font-normal">
                            ${city} genelindeki tüm müsait otel, pansiyon ve butik konaklama seçeneklerini tarihleriniz ve ${guests} misafir için önceden doldurulmuş ekranda inceleyin.
                        </p>
                    </div>
                    <div class="mt-4 pt-3 border-t border-slate-100">
                        ${hotelInfo.is_international ? `
                            <a href="${hotelInfo.booking_url || bookingCityLink}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl shadow-md transition flex items-center justify-center gap-2">
                                <span>🏨 Tüm ${city} Otellerini Listele (Booking.com)</span>
                                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                            </a>
                        ` : `
                            <a href="${hotelInfo.agoda_url || hotelInfo.enuygun_url || bookingCityLink}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow-md transition flex items-center justify-center gap-2">
                                <span>🏨 Tüm ${city} Otellerini Listele (Agoda / Enuygun)</span>
                                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                            </a>
                        `}
                    </div>
                </div>
            </div>
        </div>
        ` : ''}

        <!-- Canlı Otel Seçenekleri Başlığı -->
        <div class="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200 shadow-sm mb-6">
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-5 mb-6">
                <div>
                    <h3 class="font-black text-xl text-slate-900">${hotelInfo.destination} Canlı Otel Seçenekleri</h3>
                    <div class="text-xs text-slate-500 mt-1 font-medium">${cin} — ${cout} (${hotelInfo.nights} Gece) • ${guests} Misafir • Canlı Müsaitlik</div>
                </div>
                <div class="flex items-center gap-2.5">
                    ${hotelInfo.is_international ? `
                        <a href="${bookingUrl}" target="_blank" rel="noopener noreferrer" class="px-5 py-2.5 bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl shadow-md transition flex items-center gap-2">
                            <i class="fa-solid fa-hotel"></i>
                            <span>Booking.com Resmi Liste</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                        </a>
                    ` : `
                        <a href="${hotelInfo.agoda_url || '#'}" target="_blank" rel="noopener noreferrer" class="px-5 py-2.5 bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl shadow-md transition flex items-center gap-2">
                            <i class="fa-solid fa-hotel"></i>
                            <span>Agoda Canlı Liste</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                        </a>
                    `}
                    ${enuygunUrl ? `
                        <a href="${enuygunUrl}" target="_blank" rel="noopener noreferrer" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow-md transition flex items-center gap-2">
                            <i class="fa-solid fa-bed"></i>
                            <span>Enuygun Otel</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                        </a>
                    ` : ''}
                </div>
            </div>

            <!-- Canlı Otel Kartları Grid -->
            ${liveHotels.length > 0 ? `
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    ${liveHotels.map(h => `
                        <div class="border border-slate-200 rounded-2xl overflow-hidden hover:shadow-xl transition-all duration-300 bg-white flex flex-col justify-between group">
                            <div>
                                <div class="relative overflow-hidden h-44">
                                    <img src="${h.photo_url || h.photo || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=600&q=80'}" alt="${h.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
                                    ${h.review_score ? `
                                        <span class="absolute top-3 right-3 px-2.5 py-1 bg-blue-600/90 text-white font-black text-xs rounded-lg shadow-md backdrop-blur-xs">
                                            ⭐ ${h.review_score} ${h.score_word ? '• ' + h.score_word : ''}
                                        </span>
                                    ` : ''}
                                    <span class="absolute bottom-3 left-3 px-2.5 py-1 bg-slate-900/80 text-white font-bold text-[10px] rounded-lg shadow-sm backdrop-blur-xs">
                                        ${h.provider || (hotelInfo.is_international ? 'Booking.com' : 'Agoda')}
                                    </span>
                                </div>
                                <div class="p-5">
                                    <h4 class="font-black text-base text-slate-900 group-hover:text-[#0284C7] transition-colors leading-snug line-clamp-2">${h.name}</h4>
                                    <div class="text-xs text-slate-500 mt-1.5 flex items-center gap-1.5">
                                        <i class="fa-solid fa-location-dot text-slate-400"></i>
                                        <span class="line-clamp-1">${h.address || h.city || city}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
                                <div>
                                    <div class="text-[10px] text-slate-400 font-black uppercase">Gecelik Fiyat</div>
                                    <div class="font-black text-lg text-[#0F172A]">${h.price_formatted || (h.price ? `${h.price} ₺` : 'Canlı Fiyat')}</div>
                                    ${h.total_price_formatted ? `
                                        <div class="text-[10px] text-slate-500 font-medium">${hotelInfo.nights} Gece: ${h.total_price_formatted}</div>
                                    ` : ''}
                                </div>
                                <a href="${h.booking_url || h.direct_booking_url || h.url || bookingUrl}" target="_blank" rel="noopener noreferrer" class="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 text-xs font-black rounded-xl shadow-xs transition flex items-center gap-1.5">
                                    <span>Odayı Seç</span>
                                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                                </a>
                            </div>
                        </div>
                    `).join("")}
                </div>
            ` : `
                <div class="p-8 bg-slate-50/80 rounded-2xl border border-slate-200 text-center">
                    <div class="text-base font-black text-slate-800">Canlı otel odalarını doğrudan ${hotelInfo.is_international ? 'Booking.com' : 'Agoda'} üzerinden görüntüleyin.</div>
                    <div class="text-xs text-slate-500 mt-1 font-medium">Gecelik tahmini fiyat yerine resmi rezervasyon motorunda teyitli müsaitlik açılacaktır.</div>
                    <div class="mt-4">
                        <a href="${hotelInfo.primary_city_url || bookingUrl}" target="_blank" class="px-6 py-3 bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl inline-flex items-center gap-2 shadow-md transition">
                            <span>${city} İçin Tüm Odaları Listele</span>
                            <i class="fa-solid fa-arrow-up-right-from-square"></i>
                        </a>
                    </div>
                </div>
            `}
        </div>
    `;

    resultsArea.innerHTML = html;
}

// 6. ETKİNLİKLER (HD GÖRSELLER, EDİTÖRYAL RUH & RESMİ BİLETLER)
function filterEvents(category) {
    currentEventCategory = category;

    document.querySelectorAll(".event-filter-btn").forEach(btn => {
        btn.classList.remove("bg-gradient-to-r", "from-amber-500", "to-orange-500", "text-white", "font-black", "shadow-md");
        btn.classList.add("text-slate-600", "hover:bg-amber-50/60");
    });
    const activeBtn = document.getElementById(`eventFilter-${category}`);
    if (activeBtn) {
        activeBtn.classList.add("bg-gradient-to-r", "from-amber-500", "to-orange-500", "text-white", "font-black", "shadow-md");
        activeBtn.classList.remove("text-slate-600", "hover:bg-amber-50/60");
    }

    renderEvents();
}

function renderEvents() {
    const container = document.getElementById("eventsGridContainer");
    if (!container) return;

    let filtered = allCuratedEvents;
    if (currentEventCategory !== 'all') {
        filtered = allCuratedEvents.filter(e => e.category === currentEventCategory);
    }

    const isEn = (window.currentAppLang === 'en');

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="col-span-full p-12 text-center bg-white rounded-3xl border border-slate-200">
                <i class="fa-solid fa-calendar-xmark text-4xl text-slate-400 mb-3"></i>
                <div class="font-black text-slate-800 text-lg">${isEn ? 'No confirmed official calendar events in this category yet.' : 'Bu kategoride henüz kesinleşmiş resmi takvim etkinliği bulunmuyor.'}</div>
                <div class="text-xs text-slate-500 mt-1 font-medium">${isEn ? 'In line with our verified policy, only federation-confirmed dates are listed.' : 'Kırmızı çizgimiz gereği kulaktan dolma tarihler listelenmez, sadece federasyon onaylı etkinlikler eklenir.'}</div>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(evt => {
        const coverImg = evt.image_url || 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80';
        const title = isEn ? (evt.title_en || evt.title) : evt.title;
        const badge = isEn ? (evt.badge_en || evt.badge || 'Official Calendar') : (evt.badge || 'Resmi Takvim');
        const dates = isEn ? (evt.dates_en || evt.dates) : evt.dates;
        const city = isEn ? (evt.city_en || evt.city) : evt.city;
        const country = isEn ? (evt.country_en || evt.country) : evt.country;
        const desc = isEn ? (evt.desc_en || evt.desc) : evt.desc;
        const isEscape = (evt.is_escape || evt.transport_mode === 'ferry');
        const ticketBtnText = isEn ? (isEscape ? '🛳️ Ferry Timetable & Tickets ↗' : '🎟️ Official Tickets & Seats ↗') : (isEscape ? '🛳️ Feribot Seferi & Bilet Al ↗' : '🎟️ Doğrudan Koltuk & Tribün Seç ↗');
        const planBtnText = isEn ? (isEscape ? '⛴️ Plan Island Getaway' : '✈️ Plan Travel & Hotels') : (isEscape ? '⛴️ Bu Kaçamağa Sefer & Otel Planla' : '✈️ Bu Etkinliğe Ulaşım & Otel Planla');
        const categoryHeader = isEn ? 'Verified Category Fares:' : 'Doğrulanmış Kategori Fiyatları:';
        const saleBadge = isEn ? 'Official Direct Sale' : 'Resmi Satış';

        return `
            <div class="bg-white border border-slate-200 hover:border-amber-400/80 rounded-3xl overflow-hidden shadow-xs hover:shadow-2xl transition-all duration-300 flex flex-col justify-between group">
                <div>
                    <!-- Kartın HD Fotoğraf Alanı & Dinamik Etiketler -->
                    <div class="relative h-52 overflow-hidden">
                        <img src="${coverImg}" alt="${title}" class="w-full h-full object-cover group-hover:scale-108 transition-transform duration-700 ease-out">
                        <div class="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-slate-950/30 to-transparent"></div>
                        
                        <!-- Üst Rozetler -->
                        <div class="absolute top-3.5 left-3.5 right-3.5 flex items-center justify-between gap-2">
                            <span class="px-3 py-1 rounded-full text-[10.5px] font-black uppercase tracking-wider bg-white/95 text-slate-900 shadow-md backdrop-blur-md">
                                ${badge}
                            </span>
                            <span class="px-3 py-1 rounded-full text-[11px] font-black bg-amber-400 text-slate-950 shadow-md flex items-center gap-1.5">
                                <i class="fa-regular fa-calendar"></i>
                                <span>${dates}</span>
                            </span>
                        </div>

                        <!-- Fotoğraf Üstü Lokasyon Bilgisi -->
                        <div class="absolute bottom-3.5 left-4 right-4">
                            <div class="text-xs font-bold text-cyan-200 flex items-center gap-1.5 drop-shadow-sm">
                                <i class="fa-solid fa-location-dot text-amber-400"></i>
                                <span>${city} • ${country}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Kart Gövdesi & İlham Verici Açıklama -->
                    <div class="p-6">
                        <h3 class="text-xl font-black text-slate-900 group-hover:text-[#0284C7] transition-colors leading-tight mb-2.5">
                            ${title}
                        </h3>

                        <p class="text-xs text-slate-600 line-clamp-3 leading-relaxed font-normal mb-3">
                            ${desc}
                        </p>

                        <!-- Kategori Bilet Fiyatları Dağılımı -->
                        ${evt.ticket_categories && evt.ticket_categories.length > 0 ? `
                            <div class="mt-3 pt-3 border-t border-slate-100">
                                <div class="text-[11px] font-black text-slate-700 mb-2 flex items-center justify-between">
                                    <span class="flex items-center gap-1.5"><i class="fa-solid fa-tags text-amber-500"></i> ${categoryHeader}</span>
                                    <span class="px-2 py-0.5 rounded text-[9.5px] font-black bg-emerald-100 text-emerald-800">${saleBadge}</span>
                                </div>
                                <div class="space-y-1.5">
                                    ${evt.ticket_categories.map(cat => `
                                        <div class="flex items-center justify-between text-xs py-1.5 px-3 rounded-xl bg-slate-50 border border-slate-150/70 hover:bg-amber-50/60 transition">
                                            <div class="pr-2">
                                                <div class="font-bold text-slate-800 text-[11px] leading-tight">${cat.name}</div>
                                                ${cat.desc ? `<div class="text-[9.5px] text-slate-500 leading-tight">${cat.desc}</div>` : ''}
                                            </div>
                                            <span class="font-black text-slate-900 text-xs shrink-0 px-2.5 py-0.5 bg-white rounded-lg shadow-2xs border border-slate-200">${cat.price}</span>
                                        </div>
                                    `).join("")}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <!-- Butonlar (Doğrudan Koltuk Seçimi + Ulaşım/Otel Planla) -->
                <div class="p-5 border-t border-slate-100 bg-slate-50/70 space-y-2.5">
                    <a href="${evt.ticket_url}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-4 bg-slate-900 hover:bg-black text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-2">
                        <span>${ticketBtnText}</span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>

                    <button onclick="planEventTrip('${evt.city}', '${evt.dep_date}', '${evt.ret_date}', '${evt.transport_mode}')" class="w-full py-2.5 px-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-black text-xs rounded-xl shadow-md transition flex items-center justify-center gap-2">
                        <span>${planBtnText}</span>
                        <i class="fa-solid fa-arrow-right text-[10px]"></i>
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

// Etkinliğe Ulaşım ve Otel Planla Tetikleyicisi
function planEventTrip(destCity, depDate, retDate, preferredMode) {
    if (window.switchUnifiedTab) {
        window.switchUnifiedTab(preferredMode || 'flight');
    } else if (window.switchMasterTab) {
        switchMasterTab('transport');
    }
    if (preferredMode && window.switchTransportSubTab) switchTransportSubTab(preferredMode);

    const destInput = document.getElementById("transDest");
    const depDateInput = document.getElementById("transDepDate");
    const retDateInput = document.getElementById("transRetDate");
    const tripTypeSelect = document.getElementById("transTripType");

    if (destInput) destInput.value = destCity;
    if (depDateInput) depDateInput.value = depDate;
    if (retDateInput) retDateInput.value = retDate;
    if (tripTypeSelect) tripTypeSelect.value = 'round';

    executeTransportSearch();
}

function prefillTransportAndSwitch(origin, dest, depDate, retDate) {
    switchMasterTab('transport');
    document.getElementById("transOrigin").value = origin;
    document.getElementById("transDest").value = dest;
    document.getElementById("transDepDate").value = depDate;
    document.getElementById("transRetDate").value = retDate;
    executeTransportSearch();
}

function getNextDaysDate(dateStr, days) {
    try {
        const d = new Date(dateStr);
        d.setDate(d.getDate() + days);
        return d.toISOString().split('T')[0];
    } catch {
        return dateStr;
    }
}

function setupEventListeners() {
    const transForm = document.getElementById("transportSearchForm");
    if (transForm) transForm.addEventListener("submit", executeTransportSearch);

    const hotelForm = document.getElementById("hotelSearchForm");
    if (hotelForm) hotelForm.addEventListener("submit", executeHotelSearch);

    // Canlı Havalimanı & Metropol Rehberlik Rozetleri (İstanbul SAW/IST, Çukurova COV vb.)
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    if (originInput) {
        originInput.addEventListener("input", updateAirportHints);
        originInput.addEventListener("change", updateAirportHints);
    }
    if (destInput) {
        destInput.addEventListener("input", updateAirportHints);
        destInput.addEventListener("change", updateAirportHints);
    }

    // Kapsam ve Uçuş Tipi Doğrudan Event Dinleyicileri (Inline bağımlılığını sıfırlama)
    const domScopeBtn = document.getElementById("flightScope-domestic");
    if (domScopeBtn) domScopeBtn.addEventListener("click", () => switchFlightScope('domestic'));

    const intlScopeBtn = document.getElementById("flightScope-intl");
    if (intlScopeBtn) intlScopeBtn.addEventListener("click", () => switchFlightScope('international'));

    const roundTripBtn = document.getElementById("tripTypeBtn-round");
    if (roundTripBtn) roundTripBtn.addEventListener("click", () => setFlightTripType('round'));

    const oneWayTripBtn = document.getElementById("tripTypeBtn-oneway");
    if (oneWayTripBtn) oneWayTripBtn.addEventListener("click", () => setFlightTripType('one_way'));

    const swapBtn = document.getElementById("swapAirportsBtn");
    if (swapBtn) swapBtn.addEventListener("click", swapOriginDest);

    const paxBtn = document.getElementById("paxTriggerBtn");
    if (paxBtn) paxBtn.addEventListener("click", togglePaxDropdown);

    // Gidiş tarihi değişince dönüş tarihi minimumunu otomatik güncelle
    const transDep = document.getElementById("transDepDate");
    const transRet = document.getElementById("transRetDate");
    if (transDep && transRet) {
        transDep.addEventListener("change", () => {
            transRet.min = transDep.value;
            if (transRet.value && transRet.value < transDep.value) {
                transRet.value = getNextDaysDate(transDep.value, 3);
            }
        });
    }

    // Yolcu popover menüsü dışına tıklandığında kapat
    document.addEventListener("click", (e) => {
        const paxContainer = document.getElementById("paxControlContainer");
        const menu = document.getElementById("paxDropdownMenu");
        if (menu && !menu.classList.contains("hidden")) {
            if (paxContainer && !paxContainer.contains(e.target)) {
                menu.classList.add("hidden");
            }
        }
    });

    // Otomatik Arama Parametresi Desteği (?auto_search=1)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("auto_search") === "1") {
        if (urlParams.get("origin")) document.getElementById("transOrigin").value = urlParams.get("origin");
        if (urlParams.get("destination")) document.getElementById("transDest").value = urlParams.get("destination");
        if (urlParams.get("dep_date")) document.getElementById("transDepDate").value = urlParams.get("dep_date");
        updateAirportHints();
        setTimeout(() => {
            executeTransportSearch();
        }, 500);
    }
}

// Etkinlik & Festival Habercisi Abonelik Yöneticisi
function handleRadarSubscribe(event) {
    if (event) event.preventDefault();
    const input = document.getElementById("radarEmailInput");
    const form = document.getElementById("radarSubscribeForm");
    if (!input || !form) return;
    
    const email = input.value.trim();
    if (!email || !email.includes("@")) {
        alert("Lütfen geçerli bir e-posta adresi giriniz.");
        return;
    }

    try {
        const stored = JSON.parse(localStorage.getItem("hakiki_radar_subscribers") || "[]");
        if (!stored.includes(email)) {
            stored.push(email);
            localStorage.setItem("hakiki_radar_subscribers", JSON.stringify(stored));
        }
    } catch (e) {
        console.warn("Storage error", e);
    }

    form.innerHTML = `
        <div class="px-4 py-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 font-bold text-xs flex items-center gap-2">
            <i class="fa-solid fa-circle-check text-emerald-400"></i>
            <span>Tebrikler! Yeni festival & yarış takvimleri açıldığında ilk sizin haberiniz olacak.</span>
        </div>
    `;
}

// Global scope window bindings (Tüm inline HTML fonksiyon çağrılarını güvenceye alma)
window.switchFlightScope = switchFlightScope;
window.setFlightTripType = setFlightTripType;
window.swapOriginDest = swapOriginDest;
window.togglePaxDropdown = togglePaxDropdown;
window.closePaxDropdown = closePaxDropdown;
window.modifyPax = modifyPax;
window.selectFlightCabin = selectFlightCabin;
window.switchTransportSubTab = switchTransportSubTab;
window.switchMasterTab = switchMasterTab;
window.switchHotelScope = switchHotelScope;
window.filterCuratedEvents = filterCuratedEvents;
window.planEventTrip = planEventTrip;
window.prefillTransportAndSwitch = prefillTransportAndSwitch;
window.executeTransportSearch = executeTransportSearch;
window.executeHotelSearch = executeHotelSearch;
window.sortFlightTickets = sortFlightTickets;
window.setFlightSort = setFlightSort;
window.setFlightTimeFilter = setFlightTimeFilter;
window.setFlightAirportFilter = setFlightAirportFilter;
window.applyFlightSortAndFilter = applyFlightSortAndFilter;
window.generateTicketCardsHtml = generateTicketCardsHtml;
window.updateAirportHints = updateAirportHints;
window.handleRadarSubscribe = handleRadarSubscribe;

// ==================== DİL MOTORU DESTEĞİ ====================
// Dil motoru index_v2.html içerisindeki window.APP_TRANSLATIONS ve window.setAppLanguage tarafından yönetilmektedir.
// Sayfa açılışında kaydedilmiş dil tercihi uygulanır.
document.addEventListener("DOMContentLoaded", () => {
    try {
        const saved = localStorage.getItem("hakiki_lang");
        if (saved && typeof window.setAppLanguage === 'function') {
            window.setAppLanguage(saved);
        }
    } catch (e) {}
});


