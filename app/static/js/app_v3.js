/**
 * Hakiki Bilet V2 — Sıcak, Görsel & Yeni Nesil Seyahat Portalı
 * Akıllı Mod Filtreleme (Uçakta feribot çıkmaz), HD Destinasyon Fotoğrafları, Derin Linkler
 */

// Güvenlik Kalkanı: DOM XSS Önleyici Yardımcı Fonksiyon
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

// Ortak Seyahat Hafızası (Tek Arama, Tüm Seyahat: Uçak -> Otel -> Araç -> Etkinlik -> Akıllı Rota)
window.HakikiTravelContext = {
    origin_name: "",
    destination_name: "",
    departure_date: "",
    return_date: null,
    trip_type: "one_way",
    adults: 1,
    children: 0,
    infants: 0,
    passengers: 1,
    cabin_class: "economy",
    is_international: false,
    currency: "TRY"
};

// Global State
let currentMasterTab = 'transport'; // 'transport', 'hotel', 'events', 'deals'
let currentTransportSubTab = 'flight'; // 'flight', 'bus', 'train', 'ferry', 'car'
let currentEventCategory = 'all'; // 'all', 'sport', 'world', 'island', 'domestic'
let activeCurrency = 'TRY';
let currentHotelScope = 'intl'; // 'intl' (Booking.com & Agoda) or 'domestic' (Enuygun & Otelz)

// Uçuş Modu Özel Durumları
let currentFlightScope = 'all'; // 'domestic' (Yurtiçi) or 'international' (Yurtdışı)
let currentFlightTripType = 'one_way'; // 'one_way' (Tek Yön) or 'round' (Gidiş-Dönüş)
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
    setFlightTripType('one_way');
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
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    const isEn = window.currentAppLang === 'en';

    // Sıfırla: Yurtiçi ve Yurtdışı arasında geçiş yapıldığında önceki seçili havalimanlarını temizle
    if (originInput) {
        originInput.value = "";
    }
    if (destInput) {
        destInput.value = "";
    }

    if (scope === 'domestic') {
        if (domBtn) {
            domBtn.className = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-2xs transition";
        }
        if (intlBtn) {
            intlBtn.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:text-slate-900 transition";
        }
        if (summaryBadge) {
            summaryBadge.innerHTML = `<i class="fa-solid fa-plane-departure text-amber-500"></i><span>${isEn ? '55+ Verified Airports Across Turkey' : 'Türkiye İçi 55+ Teyitli Havalimanı'}</span>`;
        }
        if (originInput) {
            originInput.placeholder = "";
        }
        if (destInput) {
            destInput.placeholder = "";
        }
    } else {
        if (intlBtn) {
            intlBtn.className = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-2xs transition";
        }
        if (domBtn) {
            domBtn.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:text-slate-900 transition";
        }
        if (summaryBadge) {
            summaryBadge.innerHTML = `<i class="fa-solid fa-globe text-amber-500"></i><span>${isEn ? 'Global Hubs & International Airports' : 'Dünya Metropolleri & Popüler Havalimanları'}</span>`;
        }
        if (originInput) {
            originInput.placeholder = "";
        }
        if (destInput) {
            destInput.placeholder = "";
        }
    }

    await loadCitiesForTransport('flight', scope);
}

// 2. UÇUŞ TİPİ (TEK YÖN / GİDİŞ - DÖNÜŞ) SEÇİMİ
function setFlightTripType(tripType) {
    currentFlightTripType = tripType;
    const roundBtn = document.getElementById("tripTypeBtn-round");
    const onewayBtn = document.getElementById("tripTypeBtn-oneway");
    const radioOneway = document.getElementById("radio-oneway");
    const radioRound = document.getElementById("radio-round");
    const retInput = document.getElementById("transRetDate");
    const retBox = document.getElementById("returnDateBox");
    const retPlaceholder = document.getElementById("returnDatePlaceholder");
    const retLabelIcon = document.querySelector("#returnDateLabel i");
    const isEn = window.currentAppLang === 'en';

    if (tripType === 'one_way') {
        if (radioOneway) radioOneway.checked = true;
        if (radioRound) radioRound.checked = false;
        const trainRadioOneway = document.getElementById("train-radio-oneway");
        const trainRadioRound = document.getElementById("train-radio-round");
        if (trainRadioOneway) trainRadioOneway.checked = true;
        if (trainRadioRound) trainRadioRound.checked = false;
        const busRadioOneway = document.getElementById("bus-radio-oneway");
        const busRadioRound = document.getElementById("bus-radio-round");
        if (busRadioOneway) busRadioOneway.checked = true;
        if (busRadioRound) busRadioRound.checked = false;
        const ferryRadioOneway = document.getElementById("ferry-radio-oneway");
        const ferryRadioRound = document.getElementById("ferry-radio-round");
        if (ferryRadioOneway) ferryRadioOneway.checked = true;
        if (ferryRadioRound) ferryRadioRound.checked = false;
        if (onewayBtn) {
            onewayBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-black bg-slate-900 text-white shadow-2xs transition flex items-center gap-1.5";
        }
        if (roundBtn) {
            roundBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
        }
        if (retInput) {
            retInput.disabled = true;
            retInput.required = false;
            retInput.classList.add("hidden");
        }
        if (retPlaceholder) {
            retPlaceholder.classList.remove("hidden");
        }
        if (retBox) {
            retBox.className = "input-box cursor-pointer opacity-60 bg-slate-50/80 transition-all hover:opacity-100";
            retBox.title = isEn ? "Click to select round-trip" : "Gidiş-Dönüş yapmak için tıklayın";
        }
        if (retLabelIcon) {
            retLabelIcon.className = "fa-solid fa-calendar-check text-slate-400";
        }
    } else {
        if (radioRound) radioRound.checked = true;
        if (radioOneway) radioOneway.checked = false;
        const trainRadioOneway = document.getElementById("train-radio-oneway");
        const trainRadioRound = document.getElementById("train-radio-round");
        if (trainRadioOneway) trainRadioOneway.checked = false;
        if (trainRadioRound) trainRadioRound.checked = true;
        const busRadioOneway = document.getElementById("bus-radio-oneway");
        const busRadioRound = document.getElementById("bus-radio-round");
        if (busRadioOneway) busRadioOneway.checked = false;
        if (busRadioRound) busRadioRound.checked = true;
        const ferryRadioOneway = document.getElementById("ferry-radio-oneway");
        const ferryRadioRound = document.getElementById("ferry-radio-round");
        if (ferryRadioOneway) ferryRadioOneway.checked = false;
        if (ferryRadioRound) ferryRadioRound.checked = true;
        if (roundBtn) {
            roundBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-black bg-slate-900 text-white shadow-2xs transition flex items-center gap-1.5";
        }
        if (onewayBtn) {
            onewayBtn.className = "flight-trip-btn px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
        }
        if (retPlaceholder) {
            retPlaceholder.classList.add("hidden");
        }
        if (retBox) {
            retBox.className = "input-box transition-all bg-white ring-1 ring-amber-400/50 shadow-2xs";
            retBox.title = "";
        }
        if (retLabelIcon) {
            retLabelIcon.className = "fa-solid fa-calendar-check text-amber-500";
        }
        if (retInput) {
            retInput.classList.remove("hidden");
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
let _isSwappingAirports = false;
function swapOriginDest(e) {
    if (e && e.preventDefault) {
        e.preventDefault();
        e.stopPropagation();
    }
    if (_isSwappingAirports) return;
    _isSwappingAirports = true;
    setTimeout(() => { _isSwappingAirports = false; }, 200);

    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    const swapBtn = document.getElementById("swapAirportsBtn");

    if (!originInput || !destInput) return;
    const temp = originInput.value;
    originInput.value = destInput.value;
    destInput.value = temp;

    originInput.dispatchEvent(new Event("input", { bubbles: true }));
    destInput.dispatchEvent(new Event("input", { bubbles: true }));
    updateAirportHints();

    if (swapBtn) {
        swapBtn.classList.add("rotate-180");
        setTimeout(() => swapBtn.classList.remove("rotate-180"), 300);
    }
}

// Hızlı Popüler Tren Hattı Seçimi & Anında Arama
function quickFillTrain(origin, dest) {
    if (window.switchUnifiedTab) {
        window.switchUnifiedTab('train');
    }
    const oInput = document.getElementById("transOrigin");
    const dInput = document.getElementById("transDest");
    if (oInput) oInput.value = origin;
    if (dInput) dInput.value = dest;
    executeTransportSearch();
}
window.quickFillTrain = quickFillTrain;

// Hızlı Popüler Otobüs Hattı Seçimi & Anında Arama
function quickFillBus(origin, dest) {
    if (window.switchUnifiedTab) {
        window.switchUnifiedTab('bus');
    }
    const oInput = document.getElementById("transOrigin");
    const dInput = document.getElementById("transDest");
    if (oInput) oInput.value = origin;
    if (dInput) dInput.value = dest;
    executeTransportSearch();
}
window.quickFillBus = quickFillBus;

// Otobüs ve Tren Kapsam Durum Değişkenleri (Yurtiçi vs Yurtdışı)
let currentBusScope = 'domestic'; // 'domestic', 'intl'
let currentTrainScope = 'domestic'; // 'domestic', 'intl'

function setBusScope(scope) {
    currentBusScope = scope;
    const domBtn = document.getElementById("busScope-domestic");
    const intlBtn = document.getElementById("busScope-intl");
    const domPills = document.getElementById("busDomesticPills");
    const intlPills = document.getElementById("busIntlPills");
    const summary = document.getElementById("busSummaryText");
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");

    const activeCls = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-2xs transition";
    const inactiveCls = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:text-slate-900 transition";

    if (domBtn) domBtn.className = scope === 'domestic' ? activeCls : inactiveCls;
    if (intlBtn) intlBtn.className = scope === 'intl' ? activeCls : inactiveCls;

    if (domPills) {
        domPills.classList.toggle("hidden", scope !== 'domestic');
        domPills.classList.toggle("flex", scope === 'domestic');
    }
    if (intlPills) {
        intlPills.classList.toggle("hidden", scope !== 'intl');
        intlPills.classList.toggle("flex", scope === 'intl');
    }

    if (summary) {
        if (scope === 'domestic') {
            summary.innerHTML = `<i class="fa-solid fa-bus text-emerald-600"></i><span>Kamil Koç, Pamukkale & Obilet Canlı Seferleri</span>`;
        } else {
            summary.innerHTML = `<i class="fa-solid fa-earth-europe text-emerald-600"></i><span>FlixBus ile Balkanlar & Avrupa Şehirlerarası Hatları</span>`;
        }
    }

    if (originInput && !originInput.value) {
        originInput.placeholder = "";
    }
    if (destInput && !destInput.value) {
        destInput.placeholder = "";
    }

    populateDatalists('bus', scope);
}
window.setBusScope = setBusScope;

function setTrainScope(scope) {
    currentTrainScope = scope;
    const domBtn = document.getElementById("trainScope-domestic");
    const intlBtn = document.getElementById("trainScope-intl");
    const domPills = document.getElementById("trainDomesticPills");
    const intlPills = document.getElementById("trainIntlPills");
    const summary = document.getElementById("trainSummaryText");
    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");

    const activeCls = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-gradient-to-r from-slate-800 to-slate-950 text-white shadow-2xs transition";
    const inactiveCls = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:text-slate-900 transition";

    if (domBtn) domBtn.className = scope === 'domestic' ? activeCls : inactiveCls;
    if (intlBtn) intlBtn.className = scope === 'intl' ? activeCls : inactiveCls;

    if (domPills) {
        domPills.classList.toggle("hidden", scope !== 'domestic');
        domPills.classList.toggle("flex", scope === 'domestic');
    }
    if (intlPills) {
        intlPills.classList.toggle("hidden", scope !== 'intl');
        intlPills.classList.toggle("flex", scope === 'intl');
    }

    if (summary) {
        if (scope === 'domestic') {
            summary.innerHTML = `<i class="fa-solid fa-train text-indigo-600"></i><span>TCDD Taşımacılık Resmi E-Bilet Tarifesi</span>`;
        } else {
            summary.innerHTML = `<i class="fa-solid fa-earth-europe text-indigo-600"></i><span>Trainline ile Eurostar, TGV & Avrupa Hızlı Trenleri</span>`;
        }
    }

    if (originInput && !originInput.value) {
        originInput.placeholder = "";
    }
    if (destInput && !destInput.value) {
        destInput.placeholder = "";
    }

    populateDatalists('train', scope);
}
window.setTrainScope = setTrainScope;

// Gemi & Feribot Segment & Araç Durum Değişkenleri
let currentFerryCategory = 'all'; // 'all', 'domestic', 'greek_islands', 'cruise'
let currentFerryVehicleType = 'passenger'; // 'passenger', 'car', 'motorcycle'

function setFerryCategory(cat) {
    currentFerryCategory = cat;
    const allBtn = document.getElementById("ferryCat-all");
    const domBtn = document.getElementById("ferryCat-domestic");
    const islBtn = document.getElementById("ferryCat-islands");
    const cruBtn = document.getElementById("ferryCat-cruise");

    const activeCls = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-sky-900 text-white transition cursor-pointer";
    const inactiveCls = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:text-sky-900 transition cursor-pointer";

    if (allBtn) allBtn.className = cat === 'all' ? activeCls : inactiveCls;
    if (domBtn) domBtn.className = cat === 'domestic' ? activeCls : inactiveCls;
    if (islBtn) islBtn.className = cat === 'greek_islands' ? activeCls : inactiveCls;
    if (cruBtn) cruBtn.className = cat === 'cruise' ? activeCls : inactiveCls;

    // Cruise kategorisine geçildiğinde araç seçimi otomatik olarak Yaya'ya döner
    if (cat === 'cruise' && currentFerryVehicleType !== 'passenger') {
        setFerryVehicleType('passenger', false);
    }

    // Popüler rota haplarını seçilen kategoriye göre filtrele
    document.querySelectorAll("[data-ferry-pill]").forEach(pill => {
        const pillCat = pill.getAttribute("data-ferry-pill");
        if (cat === 'all' || pillCat === cat) {
            pill.classList.remove("hidden");
        } else {
            pill.classList.add("hidden");
        }
    });

    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    if (originInput && destInput) {
        if (cat === 'domestic') {
            originInput.placeholder = "Örn: Yenikapı, Pendik, Çanakkale, Taşucu";
            destInput.placeholder = "Örn: Bursa, Yalova, Bozcaada, Girne";
        } else if (cat === 'greek_islands') {
            originInput.placeholder = "Örn: Çeşme, Bodrum, Kuşadası, Ayvalık";
            destInput.placeholder = "Örn: Sakız Adası, Kos Adası, Samos, Rodos";
        } else if (cat === 'cruise') {
            originInput.placeholder = "Örn: Galataport (İstanbul), Kuşadası";
            destInput.placeholder = "Örn: Cruise, Yunan Adaları";
        } else {
            originInput.placeholder = "";
            destInput.placeholder = "";
        }
    }
}
window.setFerryCategory = setFerryCategory;

function setFerryVehicleType(vType, autoSearch = true) {
    currentFerryVehicleType = vType || 'passenger';
    const passBtn = document.getElementById("ferryVeh-passenger");
    const carBtn = document.getElementById("ferryVeh-car");
    const motoBtn = document.getElementById("ferryVeh-motorcycle");

    const activeCls = "py-2 px-3 rounded-xl text-xs font-black bg-sky-900 text-white shadow-2xs flex items-center justify-between cursor-pointer transition";
    const inactiveCls = "py-2 px-3 rounded-xl text-xs font-bold text-slate-700 bg-slate-50 hover:bg-sky-50 border border-slate-200 flex items-center justify-between cursor-pointer transition";

    if (passBtn) passBtn.className = currentFerryVehicleType === 'passenger' ? activeCls : inactiveCls;
    if (carBtn) carBtn.className = currentFerryVehicleType === 'car' ? activeCls : inactiveCls;
    if (motoBtn) motoBtn.className = currentFerryVehicleType === 'motorcycle' ? activeCls : inactiveCls;

    updatePaxSummaryDisplay();

    if (autoSearch && currentTransportSubTab === 'ferry') {
        const oInput = document.getElementById("transOrigin");
        const dInput = document.getElementById("transDest");
        if (oInput && dInput && oInput.value.trim() && dInput.value.trim()) {
            executeTransportSearch();
        }
    }
}
window.setFerryVehicleType = setFerryVehicleType;

function toggleFerryVehicle() {
    const nextType = currentFerryVehicleType === 'passenger' ? 'car' : 'passenger';
    setFerryVehicleType(nextType, true);
}
window.toggleFerryVehicle = toggleFerryVehicle;

// Hızlı Popüler Feribot & Deniz Hattı Seçimi & Anında Arama
function quickFillFerry(origin, dest, cat = 'all', isVehicle = false) {
    if (window.switchUnifiedTab) {
        window.switchUnifiedTab('ferry');
    }
    if (cat && window.setFerryCategory) {
        window.setFerryCategory(cat);
    }
    const vehMode = (isVehicle === true || isVehicle === 'car') ? 'car' : 'passenger';
    setFerryVehicleType(vehMode, false);
    const oInput = document.getElementById("transOrigin");
    const dInput = document.getElementById("transDest");
    if (oInput) oInput.value = origin;
    if (dInput) dInput.value = dest;
    executeTransportSearch();
}
window.quickFillFerry = quickFillFerry;

// Cruise Kartı Üzerinde Dinamik Kabin Tipi Seçici (İç Kabin / Dış Kabin / Balkonlu Kabin)
function selectCruiseCabin(cardDomId, tierIdx) {
    const tickets = window.lastTransportResults || [];
    const ticket = tickets.find(t => String(t.id) === String(cardDomId));
    if (!ticket || !Array.isArray(ticket.cabin_tiers) || !ticket.cabin_tiers[tierIdx]) return;

    const selectedTier = ticket.cabin_tiers[tierIdx];
    const baseTier = ticket.cabin_tiers[0];
    const ratio = (baseTier && baseTier.price > 0) ? (selectedTier.price / baseTier.price) : 1.0;
    const paxCount = (window.lastSearchReq && window.lastSearchReq.passengers) ? window.lastSearchReq.passengers : 1;

    // 1. Ana fiyatı ve kırılım metnini güncelle
    const priceEl = document.getElementById(`ferryPriceVal-${cardDomId}`);
    if (priceEl && selectedTier.price) {
        priceEl.textContent = Number(selectedTier.price).toLocaleString('tr-TR');
    }
    const breakEl = document.getElementById(`ferryBreakdown-${cardDomId}`);
    if (breakEl) {
        breakEl.textContent = `${selectedTier.name} (${selectedTier.per_person_eur} € × ${paxCount} Kişi) • Her Şey Dahil`;
    }

    // 2. Kabin butonlarının aktif/pasif stillerini güncelle
    ticket.cabin_tiers.forEach((ct, idx) => {
        const btn = document.getElementById(`cabinBtn-${cardDomId}-${idx}`);
        if (!btn) return;
        const currSym = ct.currency || ticket.currency || '₺';
        const isSel = (idx === tierIdx);
        btn.className = `px-2.5 py-1 rounded-lg text-[11px] transition cursor-pointer inline-flex items-center gap-1.5 ${isSel
            ? 'bg-sky-900 text-white font-black shadow-2xs border border-sky-900'
            : 'bg-white hover:bg-sky-100 text-slate-700 font-bold border border-sky-200'}`;
        btn.innerHTML = `
            <span>${escapeHtml(ct.name)}:</span>
            <span class="${isSel ? 'text-amber-300 font-black' : 'text-sky-900 font-black'}">${Number(ct.price).toLocaleString('tr-TR')} ${currSym}</span>
            <span class="text-[9.5px] opacity-80">(${ct.per_person_eur}€/kişi)</span>
        `;
    });

    // 3. Alt şeritteki acente fiyatlarını seçilen kabin tipine göre güncelle
    if (Array.isArray(ticket.providers)) {
        ticket.providers.forEach((p, pIdx) => {
            const provEl = document.getElementById(`provPrice-${cardDomId}-${pIdx}`);
            if (provEl && p.price) {
                const updatedProvPrice = Math.round(p.price * ratio);
                provEl.textContent = `${Number(updatedProvPrice).toLocaleString('tr-TR')} ${p.currency || ticket.currency || '₺'}`;
            }
        });
    }
}
window.selectCruiseCabin = selectCruiseCabin;

// Araç Kiralama Filtre ve Durum Değişkenleri
let currentCarCategoryFilter = 'all'; // 'all', 'Ekonomi', 'SUV', 'Konfor', 'Premium'
let currentCarTransmissionFilter = 'all'; // 'all', 'Otomatik', 'Manuel'
let currentCarDifferentDropoff = false;

function setCarCategoryFilter(cat) {
    currentCarCategoryFilter = cat;
    const btns = {
        'all': document.getElementById('carCat-all'),
        'Ekonomi': document.getElementById('carCat-eco'),
        'SUV': document.getElementById('carCat-suv'),
        'Konfor': document.getElementById('carCat-comfort'),
        'Premium': document.getElementById('carCat-luxury')
    };
    Object.keys(btns).forEach(k => {
        if (!btns[k]) return;
        if (k === cat) {
            btns[k].className = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-slate-900 text-white transition";
        } else {
            btns[k].className = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:text-slate-900 transition";
        }
    });
    if (window.lastTransportData && window.lastTransportData.car_rental) {
        renderTransportResults(window.lastTransportData, window.lastTransportSearchReq || { transport_type: 'car' });
    }
}
window.setCarCategoryFilter = setCarCategoryFilter;

function setCarTransmissionFilter(trans) {
    currentCarTransmissionFilter = trans;
    const btns = {
        'all': document.getElementById('carTrans-all'),
        'Otomatik': document.getElementById('carTrans-auto'),
        'Manuel': document.getElementById('carTrans-manual')
    };
    Object.keys(btns).forEach(k => {
        if (!btns[k]) return;
        if (k === trans) {
            btns[k].className = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-amber-500 text-slate-950 transition";
        } else {
            btns[k].className = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:text-slate-900 transition";
        }
    });
    if (window.lastTransportData && window.lastTransportData.car_rental) {
        renderTransportResults(window.lastTransportData, window.lastTransportSearchReq || { transport_type: 'car' });
    }
}
window.setCarTransmissionFilter = setCarTransmissionFilter;

function toggleCarDropoffLocation(checked) {
    currentCarDifferentDropoff = !!checked;
    const destInput = document.getElementById("transDest");
    const destLabel = document.getElementById("destFieldLabel");
    if (checked) {
        if (destInput) {
            destInput.disabled = false;
            destInput.value = "";
            destInput.placeholder = "";
            destInput.focus();
        }
        if (destLabel) destLabel.innerHTML = '📍 Farklı İade Noktası';
    } else {
        const originVal = document.getElementById("transOrigin")?.value || "";
        if (destInput) {
            destInput.value = originVal;
            destInput.placeholder = "";
        }
        if (destLabel) destLabel.innerHTML = '📍 İade Noktası (Aynı Yer)';
    }
}
window.toggleCarDropoffLocation = toggleCarDropoffLocation;

function quickFillCar(location) {
    if (window.switchUnifiedTab) {
        window.switchUnifiedTab('car');
    }
    const oInput = document.getElementById("transOrigin");
    const dInput = document.getElementById("transDest");
    if (oInput) oInput.value = location;
    if (dInput && !currentCarDifferentDropoff) dInput.value = location;
    executeTransportSearch();
}
window.quickFillCar = quickFillCar;

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
    const subTab = window.currentTransportSubTab || currentTransportSubTab || 'flight';
    if (subTab === 'ferry') {
        if (currentFerryVehicleType === 'car') {
            str += isEn ? " • 🚗 Car" : " • 🚗 Otomobil";
        } else if (currentFerryVehicleType === 'motorcycle') {
            str += isEn ? " • 🏍️ Moto" : " • 🏍️ Motosiklet";
        } else {
            str += isEn ? " • 🚶 Foot" : " • 🚶 Yaya";
        }
    } else if (subTab === 'flight') {
        if (currentFlightCabin === 'business') {
            str += " • Business";
        } else if (isEn) {
            str += " • Economy";
        }
    }
    label.textContent = str;
}

// 5. MODA ÖZEL AKILLI ŞEHİR YÜKLEME (UÇAKTA ASLA FERİBOT ÇIKMAZ! + YARIŞ KORUMALI)
let _cityLoadSeq = 0;
async function loadCitiesForTransport(transportMode, scope) {
    const reqSeq = ++_cityLoadSeq;
    const actualScope = scope || (transportMode === 'flight' ? currentFlightScope : 'all');
    try {
        const res = await fetch(`/api/cities?transport_type=${encodeURIComponent(transportMode)}&scope=${encodeURIComponent(actualScope)}`);
        if (reqSeq !== _cityLoadSeq) return; // Daha yeni bir sekme geçişi yapıldıysa eski yanıtı yoksay
        if (res.ok) {
            const data = await res.json();
            if (reqSeq !== _cityLoadSeq) return;
            verifiedCities = data.cities || [];
            populateDatalists(transportMode, actualScope);
        }
    } catch (e) {
        console.error("Şehirler yüklenirken hata:", e);
    }
}

function updateAirportHints() {
    // Kutucuklarda kayma yapmaması için arama çubuğu sabit tutulur
    const originHint = document.getElementById("originAirportHint");
    const destHint = document.getElementById("destAirportHint");
    if (originHint) originHint.classList.add("hidden");
    if (destHint) destHint.classList.add("hidden");
}
window.updateAirportHints = updateAirportHints;

// Türkçe Karakter Normalizasyon Yardımcısı
function normalizeTurkish(str) {
    if (!str) return '';
    return String(str)
        .replace(/I/g, 'ı')
        .replace(/İ/g, 'i')
        .toLowerCase()
        .replace(/ı/g, 'i')
        .replace(/ğ/g, 'g')
        .replace(/ü/g, 'u')
        .replace(/ş/g, 's')
        .replace(/ö/g, 'o')
        .replace(/ç/g, 'c')
        .replace(/[^a-z0-9]/g, '')
        .trim();
}

// 81 İl, Tüm Popüler İlçeler & Dünya Metropolleri ➔ Havalimanı Eşleme Sözlüğü
const DISTRICT_TO_AIRPORT_MAP = {
    "adana": {
        "target": "Adana - Mersin / Çukurova (COV)",
        "label": "Adana",
        "note": null
    },
    "adiyaman": {
        "target": "Adıyaman (ADF)",
        "label": "Adıyaman",
        "note": null
    },
    "adıyaman": {
        "target": "Adıyaman (ADF)",
        "label": "Adıyaman",
        "note": null
    },
    "afyon": {
        "target": "Zafer (KZR)",
        "label": "Afyonkarahisar",
        "note": "Afyonkarahisar tarifeli uçuşları Kütahya Zafer Bölgesel Havalimanı (KZR) üzerinden icra edilmektedir."
    },
    "afyonkarahisar": {
        "target": "Zafer (KZR)",
        "label": "Afyonkarahisar",
        "note": "Afyonkarahisar tarifeli uçuşları Kütahya Zafer Bölgesel Havalimanı (KZR) üzerinden icra edilmektedir."
    },
    "agri": {
        "target": "Ağrı (AJI)",
        "label": "Ağrı",
        "note": null
    },
    "ağrı": {
        "target": "Ağrı (AJI)",
        "label": "Ağrı",
        "note": null
    },
    "aksaray": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Aksaray",
        "note": "Aksaray için en yakın aktif havalimanı Nevşehir Kapadokya (NAV) uçuşları listelenmektedir."
    },
    "amasya": {
        "target": "Amasya Merzifon (MZH)",
        "label": "Amasya",
        "note": null
    },
    "merzifon": {
        "target": "Amasya Merzifon (MZH)",
        "label": "Merzifon",
        "note": null
    },
    "ankara": {
        "target": "Ankara (ESB)",
        "label": "Ankara",
        "note": null
    },
    "antalya": {
        "target": "Antalya (AYT)",
        "label": "Antalya",
        "note": null
    },
    "ardahan": {
        "target": "Kars (KSY)",
        "label": "Ardahan",
        "note": "Ardahan için en yakın aktif havalimanı Kars Harakani (KSY) uçuşları listelenmektedir."
    },
    "artvin": {
        "target": "Rize - Artvin (RZV)",
        "label": "Artvin",
        "note": "Artvin uçuşları Rize-Artvin Havalimanı (RZV) üzerinden icra edilmektedir."
    },
    "aydin": {
        "target": "İzmir (ADB)",
        "label": "Aydın",
        "note": "Aydın için en yakın aktif havalimanı İzmir Adnan Menderes (ADB) uçuşları listelenmektedir."
    },
    "aydın": {
        "target": "İzmir (ADB)",
        "label": "Aydın",
        "note": "Aydın için en yakın aktif havalimanı İzmir Adnan Menderes (ADB) uçuşları listelenmektedir."
    },
    "balikesir": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Balıkesir",
        "note": "Balıkesir tarifeli ticari uçuşları Edremit Koca Seyit Havalimanı (EDO) üzerinden gerçekleştirilmektedir."
    },
    "balıkesir": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Balıkesir",
        "note": "Balıkesir tarifeli ticari uçuşları Edremit Koca Seyit Havalimanı (EDO) üzerinden gerçekleştirilmektedir."
    },
    "bartin": {
        "target": "Zonguldak (ONQ)",
        "label": "Bartın",
        "note": "Bartın için en yakın aktif havalimanı Zonguldak Çaycuma (ONQ) uçuşları listelenmektedir."
    },
    "bartın": {
        "target": "Zonguldak (ONQ)",
        "label": "Bartın",
        "note": "Bartın için en yakın aktif havalimanı Zonguldak Çaycuma (ONQ) uçuşları listelenmektedir."
    },
    "batman": {
        "target": "Batman (BAL)",
        "label": "Batman",
        "note": null
    },
    "bayburt": {
        "target": "Trabzon (TZX)",
        "label": "Bayburt",
        "note": "Bayburt için en yakın aktif havalimanı Trabzon (TZX) veya Erzurum (ERZ) uçuşları listelenmektedir."
    },
    "bilecik": {
        "target": "Eskişehir (AOE)",
        "label": "Bilecik",
        "note": "Bilecik için Eskişehir (AOE) veya Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "bingol": {
        "target": "Bingöl (BGG)",
        "label": "Bingöl",
        "note": null
    },
    "bingöl": {
        "target": "Bingöl (BGG)",
        "label": "Bingöl",
        "note": null
    },
    "bitlis": {
        "target": "Muş (MSR)",
        "label": "Bitlis",
        "note": "Bitlis için en yakın havalimanı Muş Sultan Alparslan (MSR) veya Van (VAN) uçuşları listelenmektedir."
    },
    "bolu": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Bolu",
        "note": "Bolu için en yakın aktif havalimanı Sabiha Gökçen (SAW) veya Ankara (ESB) uçuşları listelenmektedir."
    },
    "burdur": {
        "target": "Isparta (ISE)",
        "label": "Burdur",
        "note": "Burdur için en yakın havalimanı Isparta Süleyman Demirel (ISE) veya Antalya (AYT) uçuşları listelenmektedir."
    },
    "bursa": {
        "target": "Bursa (YEI)",
        "label": "Bursa",
        "note": "Bursa tarifeli uçuşları Yenişehir (YEI) veya Sabiha Gökçen (SAW) üzerinden icra edilmektedir."
    },
    "canakkale": {
        "target": "Çanakkale (CKZ)",
        "label": "Çanakkale",
        "note": null
    },
    "çanakkale": {
        "target": "Çanakkale (CKZ)",
        "label": "Çanakkale",
        "note": null
    },
    "cankiri": {
        "target": "Ankara (ESB)",
        "label": "Çankırı",
        "note": "Çankırı için en yakın havalimanı Ankara Esenboğa (ESB) uçuşları listelenmektedir."
    },
    "çankırı": {
        "target": "Ankara (ESB)",
        "label": "Çankırı",
        "note": "Çankırı için en yakın havalimanı Ankara Esenboğa (ESB) uçuşları listelenmektedir."
    },
    "corum": {
        "target": "Amasya Merzifon (MZH)",
        "label": "Çorum",
        "note": "Çorum için en yakın aktif havalimanı Amasya Merzifon (MZH) uçuşları listelenmektedir."
    },
    "çorum": {
        "target": "Amasya Merzifon (MZH)",
        "label": "Çorum",
        "note": "Çorum için en yakın aktif havalimanı Amasya Merzifon (MZH) uçuşları listelenmektedir."
    },
    "denizli": {
        "target": "Denizli (DNZ)",
        "label": "Denizli",
        "note": null
    },
    "diyarbakir": {
        "target": "Diyarbakır (DIY)",
        "label": "Diyarbakır",
        "note": null
    },
    "diyarbakır": {
        "target": "Diyarbakır (DIY)",
        "label": "Diyarbakır",
        "note": null
    },
    "duzce": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Düzce",
        "note": "Düzce için en yakın havalimanı Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "düzce": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Düzce",
        "note": "Düzce için en yakın havalimanı Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "edirne": {
        "target": "Tekirdağ (TEQ)",
        "label": "Edirne",
        "note": "Edirne için Tekirdağ Çorlu (TEQ) veya İstanbul Havalimanı (IST) uçuşları listelenmektedir."
    },
    "elazig": {
        "target": "Elazığ (EZS)",
        "label": "Elazığ",
        "note": null
    },
    "elazığ": {
        "target": "Elazığ (EZS)",
        "label": "Elazığ",
        "note": null
    },
    "erzincan": {
        "target": "Erzincan (ERC)",
        "label": "Erzincan",
        "note": null
    },
    "erzurum": {
        "target": "Erzurum (ERZ)",
        "label": "Erzurum",
        "note": null
    },
    "eskisehir": {
        "target": "Eskişehir (AOE)",
        "label": "Eskişehir",
        "note": null
    },
    "eskişehir": {
        "target": "Eskişehir (AOE)",
        "label": "Eskişehir",
        "note": null
    },
    "gaziantep": {
        "target": "Gaziantep (GZT)",
        "label": "Gaziantep",
        "note": null
    },
    "giresun": {
        "target": "Ordu - Giresun (OGU)",
        "label": "Giresun",
        "note": "Giresun uçuşları Ordu-Giresun Havalimanı (OGU) üzerinden icra edilmektedir."
    },
    "gumushane": {
        "target": "Trabzon (TZX)",
        "label": "Gümüşhane",
        "note": "Gümüşhane için en yakın havalimanı Trabzon (TZX) uçuşları listelenmektedir."
    },
    "gümüşhane": {
        "target": "Trabzon (TZX)",
        "label": "Gümüşhane",
        "note": "Gümüşhane için en yakın havalimanı Trabzon (TZX) uçuşları listelenmektedir."
    },
    "hakkari": {
        "target": "Hakkari Yüksekova (YKO)",
        "label": "Hakkari",
        "note": "Hakkari uçuşları Yüksekova Selahaddin Eyyubi Havalimanı (YKO) üzerinden icra edilmektedir."
    },
    "hatay": {
        "target": "Hatay (HTY)",
        "label": "Hatay",
        "note": null
    },
    "antakya": {
        "target": "Hatay (HTY)",
        "label": "Antakya",
        "note": null
    },
    "iskenderun": {
        "target": "Hatay (HTY)",
        "label": "İskenderun",
        "note": "İskenderun için Hatay Havalimanı (HTY) veya Çukurova (COV) uçuşları listelenmektedir."
    },
    "igdir": {
        "target": "Iğdır (IGD)",
        "label": "Iğdır",
        "note": null
    },
    "ığdır": {
        "target": "Iğdır (IGD)",
        "label": "Iğdır",
        "note": null
    },
    "isparta": {
        "target": "Isparta (ISE)",
        "label": "Isparta",
        "note": null
    },
    "ısparta": {
        "target": "Isparta (ISE)",
        "label": "Isparta",
        "note": null
    },
    "istanbul": {
        "target": "İstanbul",
        "label": "İstanbul",
        "note": null
    },
    "sabiha": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Sabiha Gökçen",
        "note": null
    },
    "saw": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "SAW",
        "note": null
    },
    "ist": {
        "target": "İstanbul Havalimanı (IST)",
        "label": "IST",
        "note": null
    },
    "izmir": {
        "target": "İzmir (ADB)",
        "label": "İzmir",
        "note": null
    },
    "kahramanmaras": {
        "target": "Kahramanmaraş (KCM)",
        "label": "Kahramanmaraş",
        "note": null
    },
    "kahramanmaraş": {
        "target": "Kahramanmaraş (KCM)",
        "label": "Kahramanmaraş",
        "note": null
    },
    "maras": {
        "target": "Kahramanmaraş (KCM)",
        "label": "Maraş",
        "note": null
    },
    "maraş": {
        "target": "Kahramanmaraş (KCM)",
        "label": "Maraş",
        "note": null
    },
    "karabuk": {
        "target": "Zonguldak (ONQ)",
        "label": "Karabük",
        "note": "Karabük / Safranbolu için Zonguldak Çaycuma (ONQ) veya Kastamonu (KFS) uçuşları listelenmektedir."
    },
    "karabük": {
        "target": "Zonguldak (ONQ)",
        "label": "Karabük",
        "note": "Karabük / Safranbolu için Zonguldak Çaycuma (ONQ) veya Kastamonu (KFS) uçuşları listelenmektedir."
    },
    "safranbolu": {
        "target": "Kastamonu (KFS)",
        "label": "Safranbolu",
        "note": "Safranbolu için en yakın aktif havalimanı Kastamonu (KFS) veya Zonguldak (ONQ) uçuşları listelenmektedir."
    },
    "karaman": {
        "target": "Konya (KYA)",
        "label": "Karaman",
        "note": "Karaman için en yakın aktif havalimanı Konya (KYA) uçuşları listelenmektedir."
    },
    "kars": {
        "target": "Kars (KSY)",
        "label": "Kars",
        "note": null
    },
    "kastamonu": {
        "target": "Kastamonu (KFS)",
        "label": "Kastamonu",
        "note": null
    },
    "kayseri": {
        "target": "Kayseri (ASR)",
        "label": "Kayseri",
        "note": null
    },
    "kilis": {
        "target": "Gaziantep (GZT)",
        "label": "Kilis",
        "note": "Kilis için en yakın havalimanı Gaziantep (GZT) uçuşları listelenmektedir."
    },
    "kirikkale": {
        "target": "Ankara (ESB)",
        "label": "Kırıkkale",
        "note": "Kırıkkale için en yakın havalimanı Ankara Esenboğa (ESB) uçuşları listelenmektedir."
    },
    "kırıkkale": {
        "target": "Ankara (ESB)",
        "label": "Kırıkkale",
        "note": "Kırıkkale için en yakın havalimanı Ankara Esenboğa (ESB) uçuşları listelenmektedir."
    },
    "kirklareli": {
        "target": "Tekirdağ (TEQ)",
        "label": "Kırklareli",
        "note": "Kırklareli için Tekirdağ Çorlu (TEQ) veya İstanbul (IST) uçuşları listelenmektedir."
    },
    "kırklareli": {
        "target": "Tekirdağ (TEQ)",
        "label": "Kırklareli",
        "note": "Kırklareli için Tekirdağ Çorlu (TEQ) veya İstanbul (IST) uçuşları listelenmektedir."
    },
    "kirsehir": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Kırşehir",
        "note": "Kırşehir için Nevşehir (NAV) veya Ankara (ESB) uçuşları listelenmektedir."
    },
    "kırşehir": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Kırşehir",
        "note": "Kırşehir için Nevşehir (NAV) veya Ankara (ESB) uçuşları listelenmektedir."
    },
    "kocaeli": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Kocaeli",
        "note": "Kocaeli / İzmit için Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "izmit": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "İzmit",
        "note": "İzmit için Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "gebze": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Gebze",
        "note": "Gebze için en yakın havalimanı Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "konya": {
        "target": "Konya (KYA)",
        "label": "Konya",
        "note": null
    },
    "kutahya": {
        "target": "Zafer (KZR)",
        "label": "Kütahya",
        "note": "Kütahya uçuşları Zafer Bölgesel Havalimanı (KZR) üzerinden icra edilmektedir."
    },
    "kütahya": {
        "target": "Zafer (KZR)",
        "label": "Kütahya",
        "note": "Kütahya uçuşları Zafer Bölgesel Havalimanı (KZR) üzerinden icra edilmektedir."
    },
    "malatya": {
        "target": "Malatya (MLX)",
        "label": "Malatya",
        "note": null
    },
    "manisa": {
        "target": "İzmir (ADB)",
        "label": "Manisa",
        "note": "Manisa için en yakın havalimanı İzmir Adnan Menderes (ADB - ~40 km) uçuşları listelenmektedir."
    },
    "mardin": {
        "target": "Mardin (MQM)",
        "label": "Mardin",
        "note": null
    },
    "mersin": {
        "target": "Adana - Mersin / Çukurova (COV)",
        "label": "Mersin",
        "note": null
    },
    "tarsus": {
        "target": "Adana - Mersin / Çukurova (COV)",
        "label": "Tarsus",
        "note": null
    },
    "cukurova": {
        "target": "Adana - Mersin / Çukurova (COV)",
        "label": "Çukurova",
        "note": null
    },
    "çukurova": {
        "target": "Adana - Mersin / Çukurova (COV)",
        "label": "Çukurova",
        "note": null
    },
    "mugla": {
        "target": "Dalaman (DLM)",
        "label": "Muğla",
        "note": "Muğla bölgesi Dalaman (DLM) ve Bodrum (BJV) havalimanları üzerinden hizmet almaktadır."
    },
    "muğla": {
        "target": "Dalaman (DLM)",
        "label": "Muğla",
        "note": "Muğla bölgesi Dalaman (DLM) ve Bodrum (BJV) havalimanları üzerinden hizmet almaktadır."
    },
    "mus": {
        "target": "Muş (MSR)",
        "label": "Muş",
        "note": null
    },
    "muş": {
        "target": "Muş (MSR)",
        "label": "Muş",
        "note": null
    },
    "nevsehir": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Nevşehir",
        "note": null
    },
    "nevşehir": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Nevşehir",
        "note": null
    },
    "kapadokya": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Kapadokya",
        "note": "Kapadokya bölgesine doğrudan Nevşehir Kapadokya (NAV) uçuşları listelenmektedir."
    },
    "urgup": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Ürgüp",
        "note": "Ürgüp için Nevşehir Kapadokya (NAV) uçuşları listelenmektedir."
    },
    "ürgüp": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Ürgüp",
        "note": "Ürgüp için Nevşehir Kapadokya (NAV) uçuşları listelenmektedir."
    },
    "goreme": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Göreme",
        "note": "Göreme için Nevşehir Kapadokya (NAV) uçuşları listelenmektedir."
    },
    "göreme": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Göreme",
        "note": "Göreme için Nevşehir Kapadokya (NAV) uçuşları listelenmektedir."
    },
    "nigde": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Niğde",
        "note": "Niğde için Nevşehir (NAV) veya Kayseri (ASR) uçuşları listelenmektedir."
    },
    "niğde": {
        "target": "Nevşehir Kapadokya (NAV)",
        "label": "Niğde",
        "note": "Niğde için Nevşehir (NAV) veya Kayseri (ASR) uçuşları listelenmektedir."
    },
    "ordu": {
        "target": "Ordu - Giresun (OGU)",
        "label": "Ordu",
        "note": null
    },
    "osmaniye": {
        "target": "Adana - Mersin / Çukurova (COV)",
        "label": "Osmaniye",
        "note": "Osmaniye için en yakın havalimanı Çukurova (COV) uçuşları listelenmektedir."
    },
    "rize": {
        "target": "Rize - Artvin (RZV)",
        "label": "Rize",
        "note": null
    },
    "sakarya": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Sakarya",
        "note": "Sakarya / Adapazarı için Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "adapazari": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Adapazarı",
        "note": "Adapazarı için Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "adapazarı": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Adapazarı",
        "note": "Adapazarı için Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "sapanca": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Sapanca",
        "note": "Sapanca için en yakın havalimanı Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "samsun": {
        "target": "Samsun (SZF)",
        "label": "Samsun",
        "note": null
    },
    "siirt": {
        "target": "Siirt (SXZ)",
        "label": "Siirt",
        "note": null
    },
    "sinop": {
        "target": "Sinop (NOP)",
        "label": "Sinop",
        "note": null
    },
    "sivas": {
        "target": "Sivas (VAS)",
        "label": "Sivas",
        "note": null
    },
    "sanliurfa": {
        "target": "Şanlıurfa (GNY)",
        "label": "Şanlıurfa",
        "note": null
    },
    "şanlıurfa": {
        "target": "Şanlıurfa (GNY)",
        "label": "Şanlıurfa",
        "note": null
    },
    "urfa": {
        "target": "Şanlıurfa (GNY)",
        "label": "Urfa",
        "note": null
    },
    "sirnak": {
        "target": "Şırnak (NKT)",
        "label": "Şırnak",
        "note": null
    },
    "şırnak": {
        "target": "Şırnak (NKT)",
        "label": "Şırnak",
        "note": null
    },
    "cizre": {
        "target": "Şırnak (NKT)",
        "label": "Cizre",
        "note": "Cizre için Şırnak Şerafettin Elçi Havalimanı (NKT) uçuşları listelenmektedir."
    },
    "tekirdag": {
        "target": "Tekirdağ (TEQ)",
        "label": "Tekirdağ",
        "note": null
    },
    "tekirdağ": {
        "target": "Tekirdağ (TEQ)",
        "label": "Tekirdağ",
        "note": null
    },
    "corlu": {
        "target": "Tekirdağ (TEQ)",
        "label": "Çorlu",
        "note": null
    },
    "çorlu": {
        "target": "Tekirdağ (TEQ)",
        "label": "Çorlu",
        "note": null
    },
    "tokat": {
        "target": "Tokat (TJK)",
        "label": "Tokat",
        "note": null
    },
    "trabzon": {
        "target": "Trabzon (TZX)",
        "label": "Trabzon",
        "note": null
    },
    "tunceli": {
        "target": "Elazığ (EZS)",
        "label": "Tunceli",
        "note": "Tunceli için en yakın aktif havalimanı Elazığ (EZS) veya Erzincan (ERC) uçuşları listelenmektedir."
    },
    "usak": {
        "target": "Zafer (KZR)",
        "label": "Uşak",
        "note": "Uşak için Zafer Bölgesel Havalimanı (KZR) veya İzmir (ADB) uçuşları listelenmektedir."
    },
    "uşak": {
        "target": "Zafer (KZR)",
        "label": "Uşak",
        "note": "Uşak için Zafer Bölgesel Havalimanı (KZR) veya İzmir (ADB) uçuşları listelenmektedir."
    },
    "van": {
        "target": "Van (VAN)",
        "label": "Van",
        "note": null
    },
    "yalova": {
        "target": "İstanbul Sabiha Gökçen (SAW)",
        "label": "Yalova",
        "note": "Yalova için en yakın havalimanı Sabiha Gökçen (SAW - ~60 km) uçuşları listelenmektedir."
    },
    "yozgat": {
        "target": "Kayseri (ASR)",
        "label": "Yozgat",
        "note": "Yozgat için Kayseri (ASR) veya Sivas (VAS) uçuşları listelenmektedir."
    },
    "zonguldak": {
        "target": "Zonguldak (ONQ)",
        "label": "Zonguldak",
        "note": null
    },
    "marmaris": {
        "target": "Dalaman (DLM)",
        "label": "Marmaris",
        "note": "Marmaris için en yakın havalimanı olan Dalaman Havalimanı (DLM - ~90 km) uçuşları listelenmektedir."
    },
    "datca": {
        "target": "Dalaman (DLM)",
        "label": "Datça",
        "note": "Datça için Dalaman Havalimanı (DLM) uçuşları listelenmektedir."
    },
    "datça": {
        "target": "Dalaman (DLM)",
        "label": "Datça",
        "note": "Datça için Dalaman Havalimanı (DLM) uçuşları listelenmektedir."
    },
    "fethiye": {
        "target": "Dalaman (DLM)",
        "label": "Fethiye",
        "note": "Fethiye için en yakın havalimanı olan Dalaman Havalimanı (DLM - ~45 km) uçuşları listelenmektedir."
    },
    "oludeniz": {
        "target": "Dalaman (DLM)",
        "label": "Ölüdeniz",
        "note": "Ölüdeniz için Dalaman Havalimanı (DLM - ~55 km) uçuşları listelenmektedir."
    },
    "ölüdeniz": {
        "target": "Dalaman (DLM)",
        "label": "Ölüdeniz",
        "note": "Ölüdeniz için Dalaman Havalimanı (DLM - ~55 km) uçuşları listelenmektedir."
    },
    "gocek": {
        "target": "Dalaman (DLM)",
        "label": "Göcek",
        "note": "Göcek için en yakın havalimanı Dalaman (DLM - ~20 km) uçuşları listelenmektedir."
    },
    "göcek": {
        "target": "Dalaman (DLM)",
        "label": "Göcek",
        "note": "Göcek için en yakın havalimanı Dalaman (DLM - ~20 km) uçuşları listelenmektedir."
    },
    "ortaca": {
        "target": "Dalaman (DLM)",
        "label": "Ortaca",
        "note": "Ortaca için Dalaman Havalimanı (DLM) uçuşları listelenmektedir."
    },
    "koycegiz": {
        "target": "Dalaman (DLM)",
        "label": "Köyceğiz",
        "note": "Köyceğiz için Dalaman Havalimanı (DLM) uçuşları listelenmektedir."
    },
    "köyceğiz": {
        "target": "Dalaman (DLM)",
        "label": "Köyceğiz",
        "note": "Köyceğiz için Dalaman Havalimanı (DLM) uçuşları listelenmektedir."
    },
    "dalyan": {
        "target": "Dalaman (DLM)",
        "label": "Dalyan",
        "note": "Dalyan için en yakın havalimanı Dalaman (DLM - ~30 km) uçuşları listelenmektedir."
    },
    "akyaka": {
        "target": "Dalaman (DLM)",
        "label": "Akyaka",
        "note": "Akyaka için en yakın havalimanı Dalaman (DLM - ~70 km) uçuşları listelenmektedir."
    },
    "kas": {
        "target": "Dalaman (DLM)",
        "label": "Kaş",
        "note": "Kaş için en yakın havalimanı olan Dalaman (DLM - ~150 km) veya Antalya (AYT) uçuşları listelenmektedir."
    },
    "kaş": {
        "target": "Dalaman (DLM)",
        "label": "Kaş",
        "note": "Kaş için en yakın havalimanı olan Dalaman (DLM - ~150 km) veya Antalya (AYT) uçuşları listelenmektedir."
    },
    "kalkan": {
        "target": "Dalaman (DLM)",
        "label": "Kalkan",
        "note": "Kalkan için en yakın havalimanı Dalaman (DLM - ~125 km) uçuşları listelenmektedir."
    },
    "bodrum": {
        "target": "Bodrum (BJV)",
        "label": "Bodrum",
        "note": null
    },
    "milas": {
        "target": "Bodrum (BJV)",
        "label": "Milas",
        "note": null
    },
    "didim": {
        "target": "Bodrum (BJV)",
        "label": "Didim",
        "note": "Didim için en yakın havalimanı Bodrum Milas (BJV - ~85 km) veya İzmir (ADB) uçuşları listelenmektedir."
    },
    "yalikavak": {
        "target": "Bodrum (BJV)",
        "label": "Yalıkavak",
        "note": "Yalıkavak için Bodrum Milas Havalimanı (BJV) uçuşları listelenmektedir."
    },
    "yalıkavak": {
        "target": "Bodrum (BJV)",
        "label": "Yalıkavak",
        "note": "Yalıkavak için Bodrum Milas Havalimanı (BJV) uçuşları listelenmektedir."
    },
    "turgutreis": {
        "target": "Bodrum (BJV)",
        "label": "Turgutreis",
        "note": "Turgutreis için Bodrum Milas Havalimanı (BJV) uçuşları listelenmektedir."
    },
    "cesme": {
        "target": "İzmir (ADB)",
        "label": "Çeşme",
        "note": "Çeşme için en yakın havalimanı olan İzmir Adnan Menderes (ADB - ~85 km) uçuşları listelenmektedir."
    },
    "çeşme": {
        "target": "İzmir (ADB)",
        "label": "Çeşme",
        "note": "Çeşme için en yakın havalimanı olan İzmir Adnan Menderes (ADB - ~85 km) uçuşları listelenmektedir."
    },
    "alacati": {
        "target": "İzmir (ADB)",
        "label": "Alaçatı",
        "note": "Alaçatı için en yakın havalimanı olan İzmir Adnan Menderes (ADB - ~80 km) uçuşları listelenmektedir."
    },
    "alaçatı": {
        "target": "İzmir (ADB)",
        "label": "Alaçatı",
        "note": "Alaçatı için en yakın havalimanı olan İzmir Adnan Menderes (ADB - ~80 km) uçuşları listelenmektedir."
    },
    "urla": {
        "target": "İzmir (ADB)",
        "label": "Urla",
        "note": "Urla için en yakın havalimanı İzmir Adnan Menderes (ADB - ~45 km) uçuşları listelenmektedir."
    },
    "seferihisar": {
        "target": "İzmir (ADB)",
        "label": "Seferihisar",
        "note": "Seferihisar için İzmir Adnan Menderes (ADB - ~55 km) uçuşları listelenmektedir."
    },
    "sigacik": {
        "target": "İzmir (ADB)",
        "label": "Sığacık",
        "note": "Sığacık için İzmir Adnan Menderes (ADB - ~60 km) uçuşları listelenmektedir."
    },
    "sığacık": {
        "target": "İzmir (ADB)",
        "label": "Sığacık",
        "note": "Sığacık için İzmir Adnan Menderes (ADB - ~60 km) uçuşları listelenmektedir."
    },
    "kusadasi": {
        "target": "İzmir (ADB)",
        "label": "Kuşadası",
        "note": "Kuşadası için en yakın havalimanı olan İzmir Adnan Menderes (ADB - ~80 km) uçuşları listelenmektedir."
    },
    "kuşadası": {
        "target": "İzmir (ADB)",
        "label": "Kuşadası",
        "note": "Kuşadası için en yakın havalimanı olan İzmir Adnan Menderes (ADB - ~80 km) uçuşları listelenmektedir."
    },
    "selcuk": {
        "target": "İzmir (ADB)",
        "label": "Selçuk",
        "note": "Selçuk / Efes için İzmir Adnan Menderes (ADB - ~60 km) uçuşları listelenmektedir."
    },
    "selçuk": {
        "target": "İzmir (ADB)",
        "label": "Selçuk",
        "note": "Selçuk / Efes için İzmir Adnan Menderes (ADB - ~60 km) uçuşları listelenmektedir."
    },
    "alanya": {
        "target": "Alanya (GZP)",
        "label": "Alanya",
        "note": "Alanya için Gazipaşa (GZP - ~40 km) veya Antalya (AYT - ~125 km) uçuşları listelenmektedir."
    },
    "gazipasa": {
        "target": "Alanya (GZP)",
        "label": "Gazipaşa",
        "note": null
    },
    "gazipaşa": {
        "target": "Alanya (GZP)",
        "label": "Gazipaşa",
        "note": null
    },
    "manavgat": {
        "target": "Antalya (AYT)",
        "label": "Manavgat",
        "note": "Manavgat için en yakın havalimanı olan Antalya (AYT - ~65 km) uçuşları listelenmektedir."
    },
    "side": {
        "target": "Antalya (AYT)",
        "label": "Side",
        "note": "Side için en yakın havalimanı olan Antalya (AYT - ~65 km) uçuşları listelenmektedir."
    },
    "belek": {
        "target": "Antalya (AYT)",
        "label": "Belek",
        "note": "Belek için en yakın havalimanı olan Antalya (AYT - ~30 km) uçuşları listelenmektedir."
    },
    "kemer": {
        "target": "Antalya (AYT)",
        "label": "Kemer",
        "note": "Kemer için en yakın havalimanı olan Antalya (AYT - ~55 km) uçuşları listelenmektedir."
    },
    "kumluca": {
        "target": "Antalya (AYT)",
        "label": "Kumluca",
        "note": "Kumluca için Antalya (AYT - ~90 km) uçuşları listelenmektedir."
    },
    "finike": {
        "target": "Antalya (AYT)",
        "label": "Finike",
        "note": "Finike için Antalya (AYT - ~115 km) uçuşları listelenmektedir."
    },
    "demre": {
        "target": "Antalya (AYT)",
        "label": "Demre",
        "note": "Demre için Antalya (AYT - ~140 km) uçuşları listelenmektedir."
    },
    "ayvalik": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Ayvalık",
        "note": "Ayvalık için en yakın havalimanı olan Edremit Koca Seyit (EDO - ~40 km) uçuşları listelenmektedir."
    },
    "ayvalık": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Ayvalık",
        "note": "Ayvalık için en yakın havalimanı olan Edremit Koca Seyit (EDO - ~40 km) uçuşları listelenmektedir."
    },
    "akcay": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Akçay",
        "note": "Akçay için en yakın havalimanı Edremit Koca Seyit (EDO - ~15 km) uçuşları listelenmektedir."
    },
    "akçay": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Akçay",
        "note": "Akçay için en yakın havalimanı Edremit Koca Seyit (EDO - ~15 km) uçuşları listelenmektedir."
    },
    "altinoluk": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Altınoluk",
        "note": "Altınoluk için en yakın havalimanı Edremit Koca Seyit (EDO - ~30 km) uçuşları listelenmektedir."
    },
    "altınoluk": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Altınoluk",
        "note": "Altınoluk için en yakın havalimanı Edremit Koca Seyit (EDO - ~30 km) uçuşları listelenmektedir."
    },
    "edremit": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Edremit",
        "note": null
    },
    "bandirma": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Bandırma",
        "note": "Bandırma için Edremit (EDO) veya Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "bandırma": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Bandırma",
        "note": "Bandırma için Edremit (EDO) veya Sabiha Gökçen (SAW) uçuşları listelenmektedir."
    },
    "burhaniye": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Burhaniye",
        "note": "Burhaniye için Edremit Koca Seyit (EDO) uçuşları listelenmektedir."
    },
    "assos": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Assos",
        "note": "Assos / Behramkale için en yakın havalimanı Edremit Koca Seyit (EDO - ~65 km) uçuşları listelenmektedir."
    },
    "behramkale": {
        "target": "Balıkesir - Edremit (EDO)",
        "label": "Behramkale",
        "note": "Behramkale için Edremit Koca Seyit (EDO) uçuşları listelenmektedir."
    },
    "bozcaada": {
        "target": "Çanakkale (CKZ)",
        "label": "Bozcaada",
        "note": "Bozcaada için en yakın havalimanı Çanakkale (CKZ) veya Edremit (EDO) uçuşları listelenmektedir."
    },
    "gokceada": {
        "target": "Çanakkale (CKZ)",
        "label": "Gökçeada",
        "note": "Gökçeada için Çanakkale Havalimanı (CKZ) uçuşları listelenmektedir."
    },
    "gökçeada": {
        "target": "Çanakkale (CKZ)",
        "label": "Gökçeada",
        "note": "Gökçeada için Çanakkale Havalimanı (CKZ) uçuşları listelenmektedir."
    },
    "pamukkale": {
        "target": "Denizli (DNZ)",
        "label": "Pamukkale",
        "note": "Pamukkale için Denizli Çardak Havalimanı (DNZ - ~65 km) uçuşları listelenmektedir."
    },
    "girne": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Girne",
        "note": "Girne ve KKTC seyahatleri için Ercan Havalimanı (ECN) uçuşları listelenmektedir."
    },
    "lefkosa": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Lefkoşa",
        "note": null
    },
    "lefkoşa": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Lefkoşa",
        "note": null
    },
    "ercan": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Ercan",
        "note": null
    },
    "kibris": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Kıbrıs",
        "note": null
    },
    "kıbrıs": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Kıbrıs",
        "note": null
    },
    "magusa": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Gazimağusa",
        "note": "Gazimağusa için Ercan Havalimanı (ECN) uçuşları listelenmektedir."
    },
    "gazimagusa": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Gazimağusa",
        "note": "Gazimağusa için Ercan Havalimanı (ECN) uçuşları listelenmektedir."
    },
    "gazimağusa": {
        "target": "Lefkoşa / Ercan (ECN)",
        "label": "Gazimağusa",
        "note": "Gazimağusa için Ercan Havalimanı (ECN) uçuşları listelenmektedir."
    },
    "londra": {
        "target": "Londra (LON)",
        "label": "Londra",
        "note": null
    },
    "london": {
        "target": "Londra (LON)",
        "label": "Londra",
        "note": null
    },
    "paris": {
        "target": "Paris (PAR)",
        "label": "Paris",
        "note": null
    },
    "berlin": {
        "target": "Berlin (BER)",
        "label": "Berlin",
        "note": null
    },
    "munih": {
        "target": "Münih (MUC)",
        "label": "Münih",
        "note": null
    },
    "münih": {
        "target": "Münih (MUC)",
        "label": "Münih",
        "note": null
    },
    "munich": {
        "target": "Münih (MUC)",
        "label": "Münih",
        "note": null
    },
    "frankfurt": {
        "target": "Frankfurt (FRA)",
        "label": "Frankfurt",
        "note": null
    },
    "amsterdam": {
        "target": "Amsterdam (AMS)",
        "label": "Amsterdam",
        "note": null
    },
    "roma": {
        "target": "Roma (ROM)",
        "label": "Roma",
        "note": null
    },
    "rome": {
        "target": "Roma (ROM)",
        "label": "Roma",
        "note": null
    },
    "milano": {
        "target": "Milano (MXP)",
        "label": "Milano",
        "note": null
    },
    "milan": {
        "target": "Milano (MXP)",
        "label": "Milano",
        "note": null
    },
    "viyana": {
        "target": "Viyana (VIE)",
        "label": "Viyana",
        "note": null
    },
    "vienna": {
        "target": "Viyana (VIE)",
        "label": "Viyana",
        "note": null
    },
    "zurih": {
        "target": "Zürih (ZRH)",
        "label": "Zürih",
        "note": null
    },
    "zürih": {
        "target": "Zürih (ZRH)",
        "label": "Zürih",
        "note": null
    },
    "zurich": {
        "target": "Zürih (ZRH)",
        "label": "Zürih",
        "note": null
    },
    "cenevre": {
        "target": "Cenevre (GVA)",
        "label": "Cenevre",
        "note": null
    },
    "geneva": {
        "target": "Cenevre (GVA)",
        "label": "Cenevre",
        "note": null
    },
    "barselona": {
        "target": "Barselona (BCN)",
        "label": "Barselona",
        "note": null
    },
    "barcelona": {
        "target": "Barselona (BCN)",
        "label": "Barselona",
        "note": null
    },
    "madrid": {
        "target": "Madrid (MAD)",
        "label": "Madrid",
        "note": null
    },
    "atina": {
        "target": "Atina (ATH)",
        "label": "Atina",
        "note": null
    },
    "athens": {
        "target": "Atina (ATH)",
        "label": "Atina",
        "note": null
    },
    "bruksel": {
        "target": "Brüksel (BRU)",
        "label": "Brüksel",
        "note": null
    },
    "brüksel": {
        "target": "Brüksel (BRU)",
        "label": "Brüksel",
        "note": null
    },
    "brussels": {
        "target": "Brüksel (BRU)",
        "label": "Brüksel",
        "note": null
    },
    "dubai": {
        "target": "Dubai (DXB)",
        "label": "Dubai",
        "note": null
    },
    "baku": {
        "target": "Bakü (GYD)",
        "label": "Bakü",
        "note": null
    },
    "bakü": {
        "target": "Bakü (GYD)",
        "label": "Bakü",
        "note": null
    },
    "tiflis": {
        "target": "Tiflis (TBS)",
        "label": "Tiflis",
        "note": null
    },
    "tbilisi": {
        "target": "Tiflis (TBS)",
        "label": "Tiflis",
        "note": null
    },
    "belgrad": {
        "target": "Belgrad (BEG)",
        "label": "Belgrad",
        "note": null
    },
    "belgrade": {
        "target": "Belgrad (BEG)",
        "label": "Belgrad",
        "note": null
    },
    "saraybosna": {
        "target": "Saraybosna (SJJ)",
        "label": "Saraybosna",
        "note": null
    },
    "sarajevo": {
        "target": "Saraybosna (SJJ)",
        "label": "Saraybosna",
        "note": null
    },
    "uskup": {
        "target": "Üsküp (SKP)",
        "label": "Üsküp",
        "note": null
    },
    "üsküp": {
        "target": "Üsküp (SKP)",
        "label": "Üsküp",
        "note": null
    },
    "skopje": {
        "target": "Üsküp (SKP)",
        "label": "Üsküp",
        "note": null
    },
    "newyork": {
        "target": "New York (NYC)",
        "label": "New York",
        "note": null
    }
};

// Tüm Kartlar (Uçak, Otobüs, Tren, Feribot, Araç Kiralama) İçin Akıllı Konum Çözümleyici

// Alan Altı Bilgilendirme ve Uyarı Rozeti Yardımcıları
function showFieldWarningNotice(inputEl, message) {
    if (!inputEl) return;
    const parent = inputEl.closest('.input-box') || inputEl.parentElement;
    if (!parent) return;
    let badge = parent.querySelector(".field-warning-badge");
    if (!badge) {
        badge = document.createElement("div");
        badge.className = "field-warning-badge text-[11px] font-bold text-amber-900 bg-amber-50 border border-amber-300 rounded-lg px-2.5 py-1 mt-1.5 shadow-2xs flex items-center gap-1.5";
        parent.appendChild(badge);
    }
    badge.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-amber-600 shrink-0"></i><span>${message}</span>`;
    badge.classList.remove("hidden"); if (typeof window.trackHakikiEvent === 'function') { window.trackHakikiEvent({ event_type: 'route_warning', transport_type: window.currentTransportSubTab || 'flight', origin: inputEl.value || '', warning_text: String(message || '').slice(0, 180) }); }
}
window.showFieldWarningNotice = showFieldWarningNotice;

function clearFieldWarningNotice(inputEl) {
    if (!inputEl) return;
    const parent = inputEl.closest('.input-box') || inputEl.parentElement;
    if (!parent) return;
    const badge = parent.querySelector(".field-warning-badge");
    if (badge) badge.classList.add("hidden");
}
window.clearFieldWarningNotice = clearFieldWarningNotice;

// Hızlı Ulaşım Modu Değiştirme ve Aramayı Tetikleme (Örn: Trenden Otobüse veya Uçağa)
window.switchToTransportAndSearch = function(targetMode) {
    if (typeof switchTransportSubTab === 'function') {
        switchTransportSubTab(targetMode);
    }
    const oInp = document.getElementById("transOrigin");
    const dInp = document.getElementById("transDest");
    if (oInp) {
        clearFieldWarningNotice(oInp);
        resolveLocationInput(oInp, targetMode);
    }
    if (dInp) {
        clearFieldWarningNotice(dInp);
        resolveLocationInput(dInp, targetMode);
    }
    if (typeof executeTransportSearch === 'function') {
        setTimeout(() => executeTransportSearch(), 120);
    }
};

function resolveLocationInput(inputEl, mode = null, onlyExactMatch = false) {
    if (!inputEl || !inputEl.value) return;
    const currentMode = mode || window.currentTransportSubTab || 'flight';
    const raw = inputEl.value.trim();
    if (!raw) return;

    const clean = normalizeTurkish(raw);
    if (!clean || clean.length < 2) return;

    if (currentMode === 'flight') {
        clearFieldWarningNotice(inputEl);
        // UÇAK MODU: Zaten parantezli IATA kodu varsa dokunma
        if (/\([A-Z0-9/ -]{3,}\)/.test(raw)) return;

        // 1. DISTRICT_TO_AIRPORT_MAP içinde ara
        for (const [key, item] of Object.entries(DISTRICT_TO_AIRPORT_MAP)) {
            const normKey = normalizeTurkish(key);
            const match = onlyExactMatch
                ? (clean === normKey)
                : (clean === normKey || (clean.length >= 3 && normKey.startsWith(clean)));

            if (match) {
                inputEl.value = item.target;
                if (item.note) {
                    window._lastDistrictNotice = item.note;
                }
                if (typeof window.trackHakikiEvent === 'function' && raw !== item.target) {
                    window.trackHakikiEvent({ event_type: 'geo_resolve', transport_type: currentMode, origin: raw, destination: item.target, warning_text: item.note || `${raw} ➔ ${item.target}` });
                }
                return;
            }
        }

        // 2. verifiedCities (Aktif Havalimanı Listesi) içinde ara
        if (Array.isArray(verifiedCities) && verifiedCities.length > 0) {
            for (const c of verifiedCities) {
                const normName = normalizeTurkish(c.name);
                const normSlug = normalizeTurkish(c.slug);
                const match = onlyExactMatch
                    ? (clean === normName || clean === normSlug)
                    : (clean === normName || clean === normSlug || (clean.length >= 3 && (normName.startsWith(clean) || normSlug.startsWith(clean))));

                if (match) {
                    if (c.iata) {
                        inputEl.value = `${c.name} (${c.iata})`;
                    } else {
                        inputEl.value = c.name;
                    }
                    return;
                }
            }
        }
    } else if (currentMode === 'bus') {
        clearFieldWarningNotice(inputEl);
        // OTOBÜS MODU: İstanbul Anadolu & Avrupa Şemsiye Bölgeleri, Büyükşehirler & İlçe Otogarları
        const BUS_DISTRICT_TO_TERMINAL_MAP = {
            // İstanbul Anadolu Yakası (Bostancı, Kadıköy, Ataşehir vb. hepsi İstanbul Anadolu çatısına eşlenir)
            'bostanci': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: 'Bostancı kalkışlı yolculuklar için İstanbul Anadolu (Dudullu / Harem / Samandıra) kalkışlı tüm seferler listelenir.' },
            'bostancı': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: 'Bostancı kalkışlı yolculuklar için İstanbul Anadolu (Dudullu / Harem / Samandıra) kalkışlı tüm seferler listelenir.' },
            'kadikoy': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kadıköy': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'atasehir': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'ataşehir': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'dudullu': { target: 'İstanbul - Dudullu Terminali', note: null },
            'harem': { target: 'İstanbul - Harem Otogarı', note: null },
            'samandira': { target: 'İstanbul - Samandıra Terminali', note: null },
            'samandıra': { target: 'İstanbul - Samandıra Terminali', note: null },
            'umraniye': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'ümraniye': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'uskudar': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'üsküdar': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'maltepe': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kartal': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'pendik': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'tuzla': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'cekmekoy': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'çekmeköy': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'sancaktepe': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'sultanbeyli': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'beykoz': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kavacik': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kavacık': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'goztepe': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'göztepe': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kozyatagi': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kozyatağı': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'kucukyali': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'küçükyalı': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'suadiye': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'caddebostan': { target: 'İstanbul (Anadolu - Dudullu / Harem / Samandıra)', note: null },
            'sabiha': { target: 'İstanbul (Sabiha Gökçen Havalimanı Otobüs Noktası)', note: null },

            // İstanbul Avrupa Yakası
            'esenler': { target: 'İstanbul - Esenler Otogarı', note: null },
            'alibeykoy': { target: 'İstanbul - Alibeyköy Cep Otogarı', note: null },
            'alibeyköy': { target: 'İstanbul - Alibeyköy Cep Otogarı', note: null },
            'besiktas': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'beşiktaş': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'sisli': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'şişli': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'bakirkoy': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'bakırköy': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'beyoglu': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'beyoğlu': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'avcilar': { target: 'İstanbul (Avrupa - Esenler / Avcılar)', note: null },
            'avcılar': { target: 'İstanbul (Avrupa - Esenler / Avcılar)', note: null },
            'beylikduzu': { target: 'İstanbul (Avrupa - Esenler / Beylikdüzü)', note: null },
            'beylikdüzü': { target: 'İstanbul (Avrupa - Esenler / Beylikdüzü)', note: null },
            'buyukcekmece': { target: 'İstanbul (Avrupa - Esenler / Büyükçekmece)', note: null },
            'büyükçekmece': { target: 'İstanbul (Avrupa - Esenler / Büyükçekmece)', note: null },
            'sariyer': { target: 'İstanbul (Avrupa - Alibeyköy / Esenler)', note: null },
            'sarıyer': { target: 'İstanbul (Avrupa - Alibeyköy / Esenler)', note: null },
            'taksim': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'fatih': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'basaksehir': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'başakşehir': { target: 'İstanbul (Avrupa - Esenler / Alibeyköy)', note: null },
            'silivri': { target: 'Silivri Otogarı', note: null },
            'catalca': { target: 'Çatalca Otogarı', note: null },
            'çatalca': { target: 'Çatalca Otogarı', note: null },

            // Ankara
            'asti': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'aşti': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'cankaya': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'çankaya': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'kizilay': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'kızılay': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'kecioren': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'keçiören': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'yenimahalle': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'mamak': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'etimesgut': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'sincan': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'eryaman': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'batikent': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'batıkent': { target: 'Ankara - AŞTİ Otobüs Terminali', note: null },
            'polatli': { target: 'Polatlı Otogarı', note: null },
            'polatlı': { target: 'Polatlı Otogarı', note: null },

            // İzmir
            'izotas': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'izotaş': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'bornova': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'karsiyaka': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'karşıyaka': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'konak': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'alsancak': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'buca': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'bayrakli': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'bayraklı': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'cigli': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'çiğli': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'balcova': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'balçova': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'gaziemir': { target: 'İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)', note: null },
            'cesme': { target: 'Çeşme Otogarı', note: null },
            'çeşme': { target: 'Çeşme Otogarı', note: null },
            'alacati': { target: 'Alaçatı Otogarı', note: null },
            'alaçatı': { target: 'Alaçatı Otogarı', note: null },
            'dikili': { target: 'Dikili Otogarı', note: null },
            'bergama': { target: 'Bergama Otogarı', note: null },

            // Bursa
            'nilufer': { target: 'Bursa Otogarı', note: null },
            'nilüfer': { target: 'Bursa Otogarı', note: null },
            'osmangazi': { target: 'Bursa Otogarı', note: null },
            'yildirim': { target: 'Bursa Otogarı', note: null },
            'yıldırım': { target: 'Bursa Otogarı', note: null },
            'inegol': { target: 'İnegöl Otogarı', note: null },
            'inegöl': { target: 'İnegöl Otogarı', note: null },
            'gemlik': { target: 'Gemlik Otogarı', note: null },
            'mudanya': { target: 'Mudanya Otogarı', note: null },

            // Antalya
            'muratpasa': { target: 'Antalya Şehirlerarası Otobüs Terminali', note: null },
            'muratpaşa': { target: 'Antalya Şehirlerarası Otobüs Terminali', note: null },
            'kepez': { target: 'Antalya Şehirlerarası Otobüs Terminali', note: null },
            'konyaalti': { target: 'Antalya Şehirlerarası Otobüs Terminali', note: null },
            'konyaaltı': { target: 'Antalya Şehirlerarası Otobüs Terminali', note: null },
            'lara': { target: 'Antalya Şehirlerarası Otobüs Terminali', note: null },
            'alanya': { target: 'Alanya Otogarı', note: null },
            'manavgat': { target: 'Manavgat Otogarı', note: null },
            'side': { target: 'Side Otogarı', note: null },
            'kemer': { target: 'Kemer Otogarı', note: null },
            'kas': { target: 'Kaş Otogarı', note: null },
            'kaş': { target: 'Kaş Otogarı', note: null },
            'kalkan': { target: 'Kalkan Otogarı', note: null },
            'serik': { target: 'Serik (Belek) Otogarı', note: null },
            'belek': { target: 'Serik (Belek) Otogarı', note: null },
            'finike': { target: 'Finike Otogarı', note: null },
            'kumluca': { target: 'Kumluca Otogarı', note: null },
            'gazipasa': { target: 'Gazipaşa Otogarı', note: null },
            'gazipaşa': { target: 'Gazipaşa Otogarı', note: null },

            // Muğla
            'bodrum': { target: 'Bodrum Otogarı', note: null },
            'marmaris': { target: 'Marmaris Otogarı', note: null },
            'fethiye': { target: 'Fethiye Otogarı', note: null },
            'oludeniz': { target: 'Fethiye (Ölüdeniz) Otogarı', note: null },
            'ölüdeniz': { target: 'Fethiye (Ölüdeniz) Otogarı', note: null },
            'datca': { target: 'Datça Otogarı', note: null },
            'datça': { target: 'Datça Otogarı', note: null },
            'dalaman': { target: 'Dalaman Otogarı', note: null },
            'ortaca': { target: 'Ortaca (Dalyan) Otogarı', note: null },
            'dalyan': { target: 'Ortaca (Dalyan) Otogarı', note: null },
            'koycegiz': { target: 'Köyceğiz Otogarı', note: null },
            'köyceğiz': { target: 'Köyceğiz Otogarı', note: null },
            'milas': { target: 'Milas Otogarı', note: null },

            // Aydın
            'kusadasi': { target: 'Kuşadası Otogarı', note: null },
            'kuşadası': { target: 'Kuşadası Otogarı', note: null },
            'didim': { target: 'Didim Otogarı', note: null },
            'soke': { target: 'Söke Otogarı', note: null },
            'söke': { target: 'Söke Otogarı', note: null },
            'nazilli': { target: 'Nazilli Otogarı', note: null },

            // Balıkesir
            'balikesir': { target: 'Balıkesir Şehirlerarası Otobüs Terminali', note: null },
            'balıkesir': { target: 'Balıkesir Şehirlerarası Otobüs Terminali', note: null },
            'ayvalik': { target: 'Ayvalık Otogarı', note: null },
            'ayvalık': { target: 'Ayvalık Otogarı', note: null },
            'edremit': { target: 'Edremit Otogarı', note: null },
            'akcay': { target: 'Akçay Otogarı', note: null },
            'akçay': { target: 'Akçay Otogarı', note: null },
            'altinoluk': { target: 'Altınoluk Otogarı', note: null },
            'bandirma': { target: 'Bandırma Otogarı', note: null },
            'bandırma': { target: 'Bandırma Otogarı', note: null },
            'erdek': { target: 'Erdek Otogarı', note: null },

            // Çanakkale
            'canakkale': { target: 'Çanakkale Otogarı', note: null },
            'çanakkale': { target: 'Çanakkale Otogarı', note: null },
            'biga': { target: 'Biga Otogarı', note: null },
            'gelibolu': { target: 'Gelibolu Otogarı', note: null },
            'assos': { target: 'Assos (Ayvacık) Otogarı', note: null },
            'ayvacik': { target: 'Ayvacık Otogarı', note: null },

            // Mersin
            'mesot': { target: 'Mersin - Şehirlerarası Otobüs Terminali (MEŞOT)', note: null },
            'meşot': { target: 'Mersin - Şehirlerarası Otobüs Terminali (MEŞOT)', note: null },
            'tarsus': { target: 'Tarsus Otogarı', note: null },
            'silifke': { target: 'Silifke Otogarı', note: null },
            'anamur': { target: 'Anamur Otogarı', note: null }
        };

        for (const [bk, bv] of Object.entries(BUS_DISTRICT_TO_TERMINAL_MAP)) {
            if (clean === normalizeTurkish(bk)) {
                inputEl.value = bv.target;
                if (bv.note) {
                    window._lastDistrictNotice = bv.note;
                }
                return;
            }
        }
        if (Array.isArray(verifiedCities) && verifiedCities.length > 0) {
            for (const c of verifiedCities) {
                const normName = normalizeTurkish(c.name);
                const normSlug = normalizeTurkish(c.slug);
                if (clean === normName || clean === normSlug || (clean.length >= 3 && normName.startsWith(clean))) {
                    inputEl.value = c.name;
                    return;
                }
            }
        }
        if (DISTRICT_TO_AIRPORT_MAP[clean] && DISTRICT_TO_AIRPORT_MAP[clean].label) {
            inputEl.value = DISTRICT_TO_AIRPORT_MAP[clean].label;
            return;
        }
    } else if (currentMode === 'train') {
        // TREN MODU: YHT & TCDD Gar Çözümleme + Aktif Yolcu Hattı Olmayan İller Uyarısı
        const TRAIN_INACTIVE_PROVINCES = {
            "antalya": { name: "Antalya", nearest: "Burdur veya Konya Gar (YHT)" },
            "mugla": { name: "Muğla (Bodrum / Marmaris / Fethiye)", nearest: "Denizli veya Aydın Gar" },
            "bodrum": { name: "Bodrum", nearest: "Aydın veya İzmir Basmane Gar" },
            "marmaris": { name: "Marmaris", nearest: "Denizli Gar (Pamukkale Ekspresi)" },
            "fethiye": { name: "Fethiye", nearest: "Denizli veya Burdur Gar" },
            "trabzon": { name: "Trabzon", nearest: "Erzincan veya Sivas Gar (YHT)" },
            "rize": { name: "Rize", nearest: "Erzurum veya Kars Gar" },
            "artvin": { name: "Artvin", nearest: "Kars Gar (Doğu Ekspresi)" },
            "giresun": { name: "Giresun", nearest: "Sivas Gar (YHT)" },
            "ordu": { name: "Ordu", nearest: "Samsun veya Sivas Gar" },
            "sinop": { name: "Sinop", nearest: "Samsun veya Çankırı Gar" },
            "kastamonu": { name: "Kastamonu", nearest: "Çankırı veya Karabük Gar" },
            "bartin": { name: "Bartın", nearest: "Zonguldak veya Karabük Gar" },
            "bolu": { name: "Bolu", nearest: "Bilecik veya Eskişehir YHT" },
            "duzce": { name: "Düzce", nearest: "Arifiye (Sakarya) veya İzmit YHT" },
            "yalova": { name: "Yalova", nearest: "İzmit YHT veya Pendik YHT" },
            "bursa": { name: "Bursa", nearest: "Bilecik YHT veya Bozüyük YHT (Bursa YHT hattı yapım aşamasındadır)" },
            "canakkale": { name: "Çanakkale", nearest: "Bandırma veya Balıkesir Gar" },
            "aksaray": { name: "Aksaray", nearest: "Konya Gar (YHT) veya Niğde Gar" },
            "nevsehir": { name: "Nevşehir (Kapadokya)", nearest: "Kayseri veya Niğde Gar" },
            "kapadokya": { name: "Kapadokya", nearest: "Kayseri veya Niğde Gar" },
            "gaziantep": { name: "Gaziantep", nearest: "Adana veya Osmaniye Gar" },
            "sanliurfa": { name: "Şanlıurfa", nearest: "Diyarbakır veya Malatya Gar" },
            "mardin": { name: "Mardin", nearest: "Diyarbakır veya Batman Gar" },
            "sirnak": { name: "Şırnak", nearest: "Kurtalan (Siirt) Gar" },
            "hakkari": { name: "Hakkari", nearest: "Tatvan (Bitlis) Gar" },
            "adiyaman": { name: "Adıyaman", nearest: "Malatya veya Elazığ Gar" },
            "kilis": { name: "Kilis", nearest: "Adana / Osmaniye Gar" },
            "agri": { name: "Ağrı", nearest: "Erzurum veya Kars Gar" },
            "igdir": { name: "Iğdır", nearest: "Kars Gar" },
            "ardahan": { name: "Ardahan", nearest: "Kars Gar" },
            "gumushane": { name: "Gümüşhane", nearest: "Erzincan Gar" },
            "bayburt": { name: "Bayburt", nearest: "Erzincan veya Erzurum Gar" },
            "tunceli": { name: "Tunceli", nearest: "Elazığ veya Erzincan Gar" },
            "bingol": { name: "Bingöl", nearest: "Muş veya Elazığ Gar" }
        };

        const inactiveInfo = TRAIN_INACTIVE_PROVINCES[clean];
        if (inactiveInfo) {
            window._lastTrainInactiveWarning = inactiveInfo;
            showFieldWarningNotice(inputEl, `⚠️ ${inactiveInfo.name} ilinde aktif demiryolu/YHT hattı bulunmamaktadır. En yakın istasyon: ${inactiveInfo.nearest}.`);
            return;
        } else {
            clearFieldWarningNotice(inputEl);
        }

        const TRAIN_STATION_MAP = {
            'istanbul': 'İstanbul - Söğütlüçeşme YHT',
            'sogutlucesme': 'İstanbul - Söğütlüçeşme YHT',
            'söğütlüçeşme': 'İstanbul - Söğütlüçeşme YHT',
            'pendik': 'İstanbul - Pendik YHT',
            'bostanci': 'İstanbul - Bostancı YHT',
            'bostancı': 'İstanbul - Bostancı YHT',
            'halkali': 'İstanbul - Halkalı Garı',
            'halkalı': 'İstanbul - Halkalı Garı',
            'bakirkoy': 'İstanbul - Bakırköy YHT',
            'bakırköy': 'İstanbul - Bakırköy YHT',
            'ankara': 'Ankara Gar (YHT)',
            'eryaman': 'Ankara - Eryaman YHT',
            'polatli': 'Ankara - Polatlı YHT',
            'eskisehir': 'Eskişehir Gar (YHT)',
            'eskişehir': 'Eskişehir Gar (YHT)',
            'konya': 'Konya Gar (YHT)',
            'selcuklu': 'Konya - Selçuklu YHT',
            'sivas': 'Sivas Gar (YHT)',
            'karaman': 'Karaman Gar (YHT)',
            'kocaeli': 'Kocaeli - İzmit YHT',
            'izmit': 'Kocaeli - İzmit YHT',
            'gebze': 'Kocaeli - Gebze Garı',
            'sakarya': 'Sakarya - Arifiye YHT',
            'adapazari': 'Sakarya - Arifiye YHT',
            'arifiye': 'Sakarya - Arifiye YHT',
            'bilecik': 'Bilecik YHT',
            'bozuyuk': 'Bilecik - Bozüyük YHT',
            'kirikkale': 'Kırıkkale YHT',
            'yozgat': 'Yozgat YHT',
            'kars': 'Kars Gar (Doğu Ekspresi)',
            'erzurum': 'Erzurum Gar',
            'erzincan': 'Erzincan Gar',
            'izmir': 'İzmir - Basmane Garı',
            'basmane': 'İzmir - Basmane Garı',
            'denizli': 'Denizli Gar (Pamukkale Ekspresi)',
            'aydin': 'Aydın Gar',
            'manisa': 'Manisa Gar',
            'usak': 'Uşak Gar',
            'kutahya': 'Kütahya Gar',
            'afyon': 'Afyonkarahisar Gar',
            'kayseri': 'Kayseri Gar',
            'malatya': 'Malatya Gar',
            'elazig': 'Elazığ Gar',
            'diyarbakir': 'Diyarbakır Gar',
            'batman': 'Batman Gar',
            'kurtalan': 'Siirt - Kurtalan Garı',
            'tatvan': 'Bitlis - Tatvan Garı (Van Gölü Ekspresi)',
            'amasya': 'Amasya Gar',
            'samsun': 'Samsun Gar',
            'adana': 'Adana Gar',
            'mersin': 'Mersin Gar',
            'zonguldak': 'Zonguldak Gar',
            'karabuk': 'Karabük Gar'
        };

        for (const [tk, tv] of Object.entries(TRAIN_STATION_MAP)) {
            if (clean === normalizeTurkish(tk) || (clean.length >= 4 && normalizeTurkish(tk).startsWith(clean))) {
                inputEl.value = tv;
                return;
            }
        }
    } else if (currentMode === 'ferry') {
        // GEMİ & FERİBOT MODU: İskele ve Liman Çözümleme + Karasal İller Kontrolü
        const FERRY_INLAND_CITIES = {
            'ankara': 'Ankara',
            'eskisehir': 'Eskişehir',
            'konya': 'Konya',
            'kayseri': 'Kayseri',
            'sivas': 'Sivas',
            'erzurum': 'Erzurum',
            'diyarbakir': 'Diyarbakır',
            'gaziantep': 'Gaziantep',
            'malatya': 'Malatya',
            'denizli': 'Denizli',
            'afyon': 'Afyonkarahisar',
            'isparta': 'Isparta',
            'burdur': 'Burdur',
            'bolu': 'Bolu',
            'karaman': 'Karaman',
            'kahramanmaras': 'Kahramanmaraş',
            'sanliurfa': 'Şanlıurfa',
            'elazig': 'Elazığ',
            'van': 'Van'
        };
        const inlandName = FERRY_INLAND_CITIES[clean];
        if (inlandName) {
            showFieldWarningNotice(inputEl, `⚠️ ${inlandName} karasal bir ildir ve feribot limanı bulunmamaktadır. Feribot hatları Marmara, Ege Adaları ve Kıbrıs limanları arasında çalışmaktadır.`);
            return;
        } else {
            clearFieldWarningNotice(inputEl);
        }

        const FERRY_PORT_MAP = {
            'yenikapi': 'Yenikapı (İstanbul)',
            'yenikapı': 'Yenikapı (İstanbul)',
            'eminonu': 'Eminönü (İstanbul)',
            'eminönü': 'Eminönü (İstanbul)',
            'pendik': 'Pendik (İstanbul)',
            'bursa': 'Bursa - Mudanya (BUDO)',
            'mudanya': 'Bursa - Mudanya (BUDO)',
            'guzelyali': 'Bursa - Güzelyalı (İDO)',
            'güzelyalı': 'Bursa - Güzelyalı (İDO)',
            'yalova': 'Yalova',
            'bandirma': 'Bandırma',
            'bandırma': 'Bandırma',
            'cesme': 'Çeşme',
            'çeşme': 'Çeşme',
            'sakiz': 'Sakız Adası (Chios)',
            'sakız': 'Sakız Adası (Chios)',
            'bodrum': 'Bodrum',
            'kos': 'Kos Adası',
            'midilli': 'Midilli Adası (Lesvos)',
            'ayvalik': 'Ayvalık',
            'ayvalık': 'Ayvalık',
            'kusadasi': 'Kuşadası',
            'kuşadası': 'Kuşadası',
            'samos': 'Samos Adası',
            'marmaris': 'Marmaris',
            'rodos': 'Rodos Adası',
            'kas': 'Kaş',
            'kaş': 'Kaş',
            'tasucu': 'Taşucu',
            'taşucu': 'Taşucu',
            'girne': 'Girne (Kıbrıs)',
            'canakkale': 'Çanakkale',
            'çanakkale': 'Çanakkale',
            'bozcaada': 'Bozcaada',
            'gokceada': 'Gökçeada',
            'gökçeada': 'Gökçeada'
        };
        for (const [fk, fv] of Object.entries(FERRY_PORT_MAP)) {
            if (clean === normalizeTurkish(fk) || (clean.length >= 4 && normalizeTurkish(fk).startsWith(clean))) {
                inputEl.value = fv;
                return;
            }
        }
    } else if (currentMode === 'car') {
        clearFieldWarningNotice(inputEl);
        // ARAÇ KİRALAMA: Havalimanı & Şehir İçi Ofis Çözümleme
        const CAR_RENTAL_MAP = {
            'istanbul': 'İstanbul Havalimanı (IST)',
            'sabiha': 'İstanbul Sabiha Gökçen (SAW)',
            'saw': 'İstanbul Sabiha Gökçen (SAW)',
            'ist': 'İstanbul Havalimanı (IST)',
            'ankara': 'Ankara Esenboğa (ESB)',
            'izmir': 'İzmir Adnan Menderes (ADB)',
            'antalya': 'Antalya Havalimanı (AYT)',
            'bodrum': 'Bodrum Milas (BJV)',
            'dalaman': 'Dalaman Havalimanı (DLM)',
            'trabzon': 'Trabzon Havalimanı (TZX)',
            'adana': 'Adana / Çukurova (COV)',
            'kayseri': 'Kayseri Havalimanı (ASR)',
            'gaziantep': 'Gaziantep Havalimanı (GZT)'
        };
        for (const [ck, cv] of Object.entries(CAR_RENTAL_MAP)) {
            if (clean === normalizeTurkish(ck) || (clean.length >= 3 && normalizeTurkish(ck).startsWith(clean))) {
                inputEl.value = cv;
                return;
            }
        }
    }
}
window.resolveLocationInput = resolveLocationInput;
window.resolveDistrictOrAirportInput = resolveLocationInput;
window.resolveDistrictOrAirportInput = resolveLocationInput;

function populateDatalists(transportMode, scope) {
    const originList = document.getElementById("originCitiesList");
    const destList = document.getElementById("destCitiesList");

    let prefix = "✈️";
    if (transportMode === "bus") prefix = "🚌";
    if (transportMode === "train") prefix = "🚆";
    if (transportMode === "ferry") prefix = "⛴️";
    if (transportMode === "car") prefix = "🚗";

    if (transportMode === 'flight') {
        // Kalkış & Varış Havalimanları: Hem Türkiye hem Yurtdışı (Zürih/Zurich vb.) seçenekler her iki kutuda da açık
        const specialOrigins = `
            <option value="İstanbul">✈️ İstanbul - Tüm Havalimanları (IST, SAW)</option>
            <option value="İstanbul Sabiha Gökçen (SAW)">✈️ Sabiha Gökçen Havalimanı (SAW) - Anadolu Yakası</option>
            <option value="İstanbul Havalimanı (IST)">✈️ İstanbul Havalimanı (IST) - Avrupa Yakası</option>
            <option value="Ankara (ESB)">✈️ Ankara Esenboğa Havalimanı (ESB)</option>
            <option value="İzmir (ADB)">✈️ İzmir Adnan Menderes (ADB) • Çeşme / Alaçatı / Urla</option>
            <option value="Antalya (AYT)">✈️ Antalya Havalimanı (AYT) • Kemer / Belek / Side / Kaş</option>
            <option value="Adana - Mersin / Çukurova (COV)">✈️ Adana - Mersin / Çukurova Uluslararası (COV)</option>
            <option value="Trabzon (TZX)">✈️ Trabzon Havalimanı (TZX)</option>
            <option value="Bodrum (BJV)">✈️ Muğla - Bodrum Milas Havalimanı (BJV) • Didim</option>
            <option value="Dalaman (DLM)">✈️ Muğla - Dalaman Havalimanı (DLM) • Marmaris / Fethiye / Göcek</option>
            <option value="Alanya (GZP)">✈️ Alanya - Gazipaşa Havalimanı (GZP)</option>
            <option value="Balıkesir - Edremit (EDO)">✈️ Balıkesir - Edremit Koca Seyit (EDO) • Ayvalık / Akçay</option>
        `;
        const restOrigins = verifiedCities.filter(c => !['istanbul', 'ankara', 'izmir', 'antalya', 'adana', 'mersin', 'trabzon', 'bodrum', 'dalaman', 'alanya', 'balikesir'].includes(c.slug)).map(c => {
            const iataStr = (c.iata && !c.name.includes(`(${c.iata}`)) ? ` (${c.iata})` : '';
            const enAlias = c.en_name ? ` / ${c.en_name}` : '';
            const countryStr = c.country ? ` • ${c.country}` : ' Havalimanı';
            const icon = (c.is_international || (c.country && c.country !== 'Türkiye')) ? '🌍' : prefix;
            return `<option value="${c.name}">${icon} ${c.name}${iataStr}${enAlias}${countryStr}</option>`;
        }).join("");
        if (originList) originList.innerHTML = specialOrigins + restOrigins;

        // Varış Havalimanları: Kapsama göre (Türkçe + İngilizce/ASCII arama destekli)
        const specialDests = `
            <option value="Dalaman (DLM)">✈️ Muğla - Dalaman Havalimanı (DLM) • Marmaris / Fethiye / Göcek</option>
            <option value="Bodrum (BJV)">✈️ Muğla - Bodrum Milas Havalimanı (BJV) • Didim</option>
            <option value="Antalya (AYT)">✈️ Antalya Havalimanı (AYT) • Kemer / Belek / Side / Kaş</option>
            <option value="İzmir (ADB)">✈️ İzmir Adnan Menderes (ADB) • Çeşme / Alaçatı / Urla</option>
            <option value="Adana - Mersin / Çukurova (COV)">✈️ Adana - Mersin / Çukurova Uluslararası Havalimanı (COV)</option>
            <option value="Alanya (GZP)">✈️ Alanya - Gazipaşa Havalimanı (GZP)</option>
            <option value="Balıkesir - Edremit (EDO)">✈️ Balıkesir - Edremit Koca Seyit (EDO) • Ayvalık / Akçay</option>
            <option value="Trabzon (TZX)">✈️ Trabzon Havalimanı (TZX)</option>
            <option value="İstanbul">✈️ İstanbul - Tüm Havalimanları (IST, SAW)</option>
            <option value="İstanbul Sabiha Gökçen (SAW)">✈️ Sabiha Gökçen Havalimanı (SAW) - Anadolu Yakası</option>
            <option value="İstanbul Havalimanı (IST)">✈️ İstanbul Havalimanı (IST) - Avrupa Yakası</option>
            <option value="Ankara (ESB)">✈️ Ankara Esenboğa Havalimanı (ESB)</option>
        `;
        const restDests = verifiedCities.filter(c => !['istanbul', 'ankara', 'antalya', 'izmir', 'adana', 'mersin', 'bodrum', 'dalaman', 'alanya', 'balikesir', 'trabzon'].includes(c.slug)).map(c => {
            const iataStr = (c.iata && !c.name.includes(`(${c.iata}`)) ? ` (${c.iata})` : '';
            const enAlias = c.en_name ? ` / ${c.en_name}` : '';
            const countryStr = c.country ? ` • ${c.country}` : '';
            const icon = (c.is_international || (c.country && c.country !== 'Türkiye')) ? '🌍' : '🇹🇷';
            return `<option value="${c.name}">${icon} ${c.name}${iataStr}${enAlias}${countryStr}</option>`;
        }).join("");
        if (destList) destList.innerHTML = specialDests + restDests;
    } else if (transportMode === 'train') {
        const trainStationsHtml = `
            <option value="İstanbul - Söğütlüçeşme YHT">🚆 İstanbul - Söğütlüçeşme / Bostancı / Halkalı YHT</option>
            <option value="Ankara Gar (YHT)">🚆 Ankara Gar (YHT / Anahat)</option>
            <option value="Eskişehir Gar (YHT)">🚆 Eskişehir Gar (YHT)</option>
            <option value="Konya Gar (YHT)">🚆 Konya Gar (YHT)</option>
            <option value="Sivas Gar (YHT)">🚆 Sivas Gar (YHT)</option>
            <option value="Karaman Gar (YHT)">🚆 Karaman Gar (YHT)</option>
            <option value="Kars Gar (Doğu Ekspresi)">🚆 Kars Gar (Doğu Ekspresi)</option>
            <option value="İzmir - Basmane Garı">🚆 İzmir Basmane (İzmir Mavi Treni)</option>
            <option value="Denizli">🚆 Denizli Gar (Pamukkale Ekspresi)</option>
            <option value="Adana">🚆 Adana Gar</option>
            <option value="Mersin">🚆 Mersin Gar</option>
            <option value="Kayseri">🚆 Kayseri Gar</option>
            <option value="Tatvan">🚆 Tatvan Gar (Van Gölü Ekspresi)</option>
            <option value="Kurtalan">🚆 Kurtalan Gar (Güney Kurtalan Ekspresi)</option>
            <option value="Sofya">🌍 Sofya - Merkez Gar (Bulgaristan)</option>
            <option value="Bükreş">🌍 Bükreş - Gara de Nord (Romanya)</option>
            <option value="Paris">🌍 Paris - Gare du Nord / de Lyon (Eurostar/TGV)</option>
            <option value="Londra">🌍 Londra - St Pancras Int. (Eurostar)</option>
            <option value="Roma">🌍 Roma - Termini (Frecciarossa)</option>
            <option value="Milano">🌍 Milano - Centrale (Frecciarossa)</option>
            <option value="Amsterdam">🌍 Amsterdam - Centraal (Eurostar)</option>
            <option value="Berlin">🌍 Berlin - Hbf (ICE)</option>
            <option value="Münih">🌍 Münih - Hbf (ICE)</option>
            <option value="Viyana">🌍 Viyana - Hbf (Railjet)</option>
            <option value="Zürih">🌍 Zürih - HB (Railjet)</option>
            <option value="Prag">🌍 Prag - Hlavni Nadrazi (EuroCity)</option>
        `;
        if (originList) originList.innerHTML = trainStationsHtml;
        if (destList) destList.innerHTML = trainStationsHtml;
    } else if (transportMode === 'bus') {
        const busScope = scope || currentBusScope;
        let busTerminalsHtml = '';
        if (busScope === 'intl') {
            busTerminalsHtml = `
                <option value="İstanbul">🚌 İstanbul - Esenler / Alibeyköy Otogarı</option>
                <option value="Edirne">🚌 Edirne - Şehirlerarası Otogarı</option>
                <option value="Bursa">🚌 Bursa - Uluslararası Otobüs Terminali</option>
                <option value="İzmir">🚌 İzmir - Şehirlerarası Otobüs Terminali</option>
                <option value="Selanik">🌍 Selanik - Makedonia Otobüs Terminali (Yunanistan)</option>
                <option value="Atina">🌍 Atina - Kifisou Otogarı (Yunanistan)</option>
                <option value="Sofya">🌍 Sofya - Central Bus Station (Bulgaristan)</option>
                <option value="Filibe">🌍 Filibe / Plovdiv - Yug Otogarı (Bulgaristan)</option>
                <option value="Varna">🌍 Varna - Şehirlerarası Otogarı (Bulgaristan)</option>
                <option value="Burgas">🌍 Burgas - Şehirlerarası Otogarı (Bulgaristan)</option>
                <option value="Bükreş">🌍 Bükreş - Filaret Otobüs Terminali (Romanya)</option>
                <option value="Berlin">🌍 Berlin - ZOB (Almanya - FlixBus)</option>
                <option value="Prag">🌍 Prag - Florenc Bus Station (Çekya - FlixBus)</option>
                <option value="Paris">🌍 Paris - Bercy Seine (Fransa - FlixBus)</option>
                <option value="Amsterdam">🌍 Amsterdam - Sloterdijk (Hollanda - FlixBus)</option>
                <option value="Münih">🌍 Münih - ZOB (Almanya - FlixBus)</option>
                <option value="Zürih">🌍 Zürih - Carpark Sihlquai (İsviçre - FlixBus)</option>
                <option value="Viyana">🌍 Viyana - Erdberg VIB (Avusturya - FlixBus)</option>
                <option value="Budapeşte">🌍 Budapeşte - Nepliget (Macaristan - FlixBus)</option>
                <option value="Roma">🌍 Roma - Tiburtina (İtalya - FlixBus)</option>
                <option value="Floransa">🌍 Floransa - Villa Costanza (İtalya - FlixBus)</option>
            `;
        } else {
            const popularHubs = [
                { val: "İstanbul", label: "🚌 İstanbul - Esenler / Alibeyköy / Harem Otogarı" },
                { val: "Ankara", label: "🚌 Ankara - AŞTİ Otobüs Terminali" },
                { val: "İzmir", label: "🚌 İzmir - Şehirlerarası Otobüs Terminali (İZOTAŞ)" },
                { val: "Antalya", label: "🚌 Antalya - Şehirlerarası Otobüs Terminali" },
                { val: "Bursa", label: "🚌 Bursa - Şehirlerarası Otobüs Terminali" },
                { val: "Eskişehir", label: "🚌 Eskişehir - Şehirlerarası Otobüs Terminali" },
                { val: "Adana", label: "🚌 Adana - Merkez Otogarı" },
                { val: "Trabzon", label: "🚌 Trabzon - Şehirlerarası Otogarı" },
                { val: "Gaziantep", label: "🚌 Gaziantep - Şehirlerarası Otogarı" },
                { val: "Konya", label: "🚌 Konya - Şehirlerarası Otobüs Terminali" },
                { val: "Kayseri", label: "🚌 Kayseri - Şehirlerarası Otobüs Terminali" },
                { val: "Mersin", label: "🚌 Mersin - Şehirlerarası Otobüs Terminali (MEŞOT)" },
                { val: "Bodrum", label: "🚌 Muğla - Bodrum Şehirlerarası Otogarı" },
                { val: "Fethiye", label: "🚌 Muğla - Fethiye Otogarı" },
                { val: "Marmaris", label: "🚌 Muğla - Marmaris Otogarı" },
                { val: "Denizli", label: "🚌 Denizli - Şehirlerarası Otobüs Terminali" },
                { val: "Diyarbakır", label: "🚌 Diyarbakır - Şehirlerarası Otobüs Terminali" },
                { val: "Samsun", label: "🚌 Samsun - Şehirlerarası Otobüs Terminali" },
                { val: "Balıkesir", label: "🚌 Balıkesir - Şehirlerarası Otogarı" },
                { val: "Çanakkale", label: "🚌 Çanakkale - Şehirlerarası Otogarı" },
                { val: "Edirne", label: "🚌 Edirne - Şehirlerarası Otogarı" }
            ];
            const popularSet = new Set(popularHubs.map(h => h.val.toLowerCase()));
            let items = popularHubs.map(h => `<option value="${h.val}">${h.label}</option>`);

            if (verifiedCities && verifiedCities.length > 0) {
                const rest = verifiedCities.filter(c => !popularSet.has((c.name || '').toLowerCase()));
                rest.forEach(c => {
                    const label = c.is_district ? `🚌 ${c.name} Otogarı` : `🚌 ${c.name} Şehirlerarası Otogarı`;
                    items.push(`<option value="${c.name}">${label}</option>`);
                });
            }
            busTerminalsHtml = items.join("");
        }
        if (originList) originList.innerHTML = busTerminalsHtml;
        if (destList) destList.innerHTML = busTerminalsHtml;
    } else if (transportMode === 'ferry') {
        const ferryPortsHtml = `
            <option value="İstanbul">⛴️ İstanbul - Yenikapı / Eminönü / Pendik / Galataport</option>
            <option value="Yenikapı">⛴️ İstanbul - Yenikapı İskelesi (İDO)</option>
            <option value="Eminönü">⛴️ İstanbul - Eminönü / Sirkeci İskelesi (BUDO)</option>
            <option value="Pendik">⛴️ İstanbul - Pendik İskelesi (İDO Hızlı Feribot)</option>
            <option value="Galataport">🛳️ İstanbul - Galataport Kruvaziyer Limanı</option>
            <option value="Bursa">⛴️ Bursa - Mudanya (BUDO) / Güzelyalı (İDO)</option>
            <option value="Yalova">⛴️ Yalova İskelesi (İDO Hızlı Arabalı Feribot)</option>
            <option value="Bandırma">⛴️ Bandırma Limanı (İDO Hızlı Deniz Otobüsü)</option>
            <option value="Avşa Adası">🏝️ Avşa Adası (Marmara)</option>
            <option value="Çeşme">🇬🇷 İzmir - Çeşme Uluslararası Limanı</option>
            <option value="Sakız Adası">🇬🇷 Sakız Adası (Chios - Kapıda Vize)</option>
            <option value="Bodrum">🇬🇷 Muğla - Bodrum Yolcu Limanı</option>
            <option value="Kos Adası">🇬🇷 Kos Adası (İstanköy - Kapıda Vize)</option>
            <option value="Simi Adası">🇬🇷 Simi Adası (Symi - Kapıda Vize)</option>
            <option value="Ayvalık">🇬🇷 Balıkesir - Ayvalık Limanı</option>
            <option value="Midilli Adası">🇬🇷 Midilli Adası (Lesvos - Kapıda Vize)</option>
            <option value="Kuşadası">🇬🇷 Aydın - Kuşadası Ege Port Limanı</option>
            <option value="Samos Adası">🇬🇷 Samos Adası (Sisam - Kapıda Vize)</option>
            <option value="Marmaris">🇬🇷 Muğla - Marmaris Cruise & Feribot Limanı</option>
            <option value="Fethiye">🇬🇷 Muğla - Fethiye Limanı</option>
            <option value="Rodos Adası">🇬🇷 Rodos Adası (Rhodes - Kapıda Vize)</option>
            <option value="Kaş">🇬🇷 Antalya - Kaş Limanı</option>
            <option value="Meis Adası">🇬🇷 Meis Adası (Kastellorizo - Kapıda Vize)</option>
            <option value="Çanakkale">⛴️ Çanakkale İskelesi (Gestaş)</option>
            <option value="Eceabat">⛴️ Eceabat / Gelibolu İskelesi (Gestaş)</option>
            <option value="Geyikli">⛴️ Geyikli İskelesi (Çanakkale - Bozcaada)</option>
            <option value="Bozcaada">🏝️ Bozcaada Limanı (Gestaş)</option>
            <option value="Kabatepe">⛴️ Kabatepe İskelesi (Çanakkale - Gökçeada)</option>
            <option value="Gökçeada">🏝️ Gökçeada (Kuzu Limanı - Gestaş)</option>
            <option value="Taşucu">⛴️ Mersin - Taşucu Limanı (KKTC Feribot)</option>
            <option value="Girne">🪪 KKTC - Girne Limanı (Kıbrıs)</option>
            <option value="Cruise">🛳️ Ege & Yunan Adaları & İtalya Kruvaziyer Turu</option>
        `;
        if (originList) originList.innerHTML = ferryPortsHtml;
        if (destList) destList.innerHTML = ferryPortsHtml;
    } else if (transportMode === 'car') {
        const carLocationsHtml = `
            <option value="Antalya Havalimanı (AYT)">🚗 Antalya Havalimanı (AYT) - İç/Dış Hatlar Ofisleri</option>
            <option value="İstanbul Sabiha Gökçen (SAW)">🚗 Sabiha Gökçen Havalimanı (SAW) - Anadolu Yakası</option>
            <option value="İstanbul Havalimanı (IST)">🚗 İstanbul Havalimanı (IST) - Avrupa Yakası</option>
            <option value="İzmir Adnan Menderes (ADB)">🚗 İzmir Adnan Menderes Havalimanı (ADB)</option>
            <option value="Bodrum Milas (BJV)">🚗 Muğla - Bodrum Milas Havalimanı (BJV)</option>
            <option value="Dalaman Havalimanı (DLM)">🚗 Muğla - Dalaman Havalimanı (DLM)</option>
            <option value="Ankara Esenboğa (ESB)">🚗 Ankara Esenboğa Havalimanı (ESB)</option>
            <option value="Trabzon Havalimanı (TZX)">🚗 Trabzon Havalimanı (TZX)</option>
            <option value="Adana / Çukurova (COV)">🚗 Adana / Çukurova Havalimanı (COV)</option>
            <option value="Kayseri Havalimanı (ASR)">🚗 Kayseri Erkilet Havalimanı (ASR)</option>
            <option value="Gaziantep Havalimanı (GZT)">🚗 Gaziantep Havalimanı (GZT)</option>
            <option value="İstanbul Kadıköy">🏙️ İstanbul Kadıköy - Şehir İçi Ofisleri</option>
            <option value="İstanbul Taksim">🏙️ İstanbul Taksim - Şehir İçi Ofisleri</option>
            <option value="İzmir Alsancak">🏙️ İzmir Alsancak - Şehir İçi Ofisleri</option>
            <option value="Ankara Çankaya">🏙️ Ankara Çankaya / Kızılay Ofisleri</option>
            <option value="Antalya Lara">🏙️ Antalya Lara / Muratpaşa Şehir İçi</option>
        `;
        if (originList) originList.innerHTML = carLocationsHtml;
        if (destList) destList.innerHTML = carLocationsHtml;
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
    window.currentTransportSubTab = subTab;

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

    updateTransportFieldLabels(subTab, window.currentAppLang || 'tr');

    // Uçuş Seçenekleri Barını (Yurtiçi/Yurtdışı & Tek Yön/Gidiş-Dönüş) sadece uçak modunda göster
    const flightBar = document.getElementById("flightOptionsBar");
    if (flightBar) {
        if (subTab === 'flight') {
            flightBar.classList.remove("hidden");
        } else {
            flightBar.classList.add("hidden");
        }
    }
    const trainBar = document.getElementById("trainOptionsBar");
    if (trainBar) {
        if (subTab === 'train') {
            trainBar.classList.remove("hidden");
            trainBar.classList.add("flex");
        } else {
            trainBar.classList.add("hidden");
            trainBar.classList.remove("flex");
        }
    }
    const busBar = document.getElementById("busOptionsBar");
    if (busBar) {
        if (subTab === 'bus') {
            busBar.classList.remove("hidden");
            busBar.classList.add("flex");
        } else {
            busBar.classList.add("hidden");
            busBar.classList.remove("flex");
        }
    }
    const ferryBar = document.getElementById("ferryOptionsBar");
    if (ferryBar) {
        if (subTab === 'ferry') {
            ferryBar.classList.remove("hidden");
            ferryBar.classList.add("flex");
        } else {
            ferryBar.classList.add("hidden");
            ferryBar.classList.remove("flex");
        }
    }
    const carBar = document.getElementById("carOptionsBar");
    if (carBar) {
        if (subTab === 'car') {
            carBar.classList.remove("hidden");
            carBar.classList.add("flex");
        } else {
            carBar.classList.add("hidden");
            carBar.classList.remove("flex");
        }
    }
    updateAirportHints();
}


function ensureObiletPriceSort(url) {
    if (!url || typeof url !== 'string' || !url.includes('obilet.com')) return url;
    if (url.includes('/ucuslar/') || url.includes('/feribot-seferleri/')) return url;
    if (url.includes('sorting=price') || url.includes('sort=price')) return url;
    const sep = url.includes('?') ? '&' : '?';
    return url + sep + 'sorting=price&sort=price';
}

// 4. ULAŞIM ARAMASI ÇALIŞTIRMA (Uçak Odaklı, Kusursuz Yolcu & Kapsam Desteği)
async function executeTransportSearch(e) {
    if (e) e.preventDefault();

    const oInp = document.getElementById("transOrigin");
    const dInp = document.getElementById("transDest");
    if (oInp) resolveLocationInput(oInp, currentTransportSubTab);
    if (dInp) resolveLocationInput(dInp, currentTransportSubTab);

    let origin = oInp ? oInp.value.trim() : "";
    let destination = dInp ? dInp.value.trim() : "";
    const depDate = document.getElementById("transDepDate").value;
    const retDate = document.getElementById("transRetDate").value;
    const isRound = (currentFlightTripType === 'round');
    const totalPax = flightPax.adults + flightPax.children + flightPax.infants;

    // Araç kiralamada varış boş bırakılmışsa otomatik olarak alış noktasıyla aynı kabul et (aynı yere iade)
    if (currentTransportSubTab === 'car' && !destination) {
        destination = origin;
        const dInput = document.getElementById("transDest");
        if (dInput) dInput.value = origin;
    }

    if (!origin || !destination || !depDate) {
        alert("Lütfen kalkış noktası, varış noktası ve seyahat tarihini seçiniz.");
        return;
    }
    if (currentTransportSubTab === 'flight' && isRound && !retDate) {
        alert("Lütfen dönüş tarihini seçiniz veya 'Tek Yön' seçeneğini işaretleyiniz.");
        return;
    }

    const resultsArea = document.getElementById("transportResultsArea");

    // Ulaşım türüne özel simge, etiket, açı ve tema renkleri
    let vehicleIcon = "fa-plane";
    let vehicleRotate = "rotate(15deg)";
    let vehicleBg = "from-amber-500 to-amber-300";
    let vehicleShadow = "shadow-amber-500/40";
    let loadingStep1 = "Canlı Uçak Seferleri & Hakiki Fiyatlar Taranıyor...";
    let loadingStep2 = "Trip.com, Booking/Kayak, Skyscanner, THY, Pegasus, AJet ve SunExpress resmi acente biletleri anlık taranıyor.";

    if (currentTransportSubTab === 'bus') {
        vehicleIcon = "fa-bus-simple";
        vehicleRotate = "rotate(0deg)";
        vehicleBg = "from-emerald-500 to-teal-300";
        vehicleShadow = "shadow-emerald-500/40";
        loadingStep1 = "Obilet & Kamil Koç Otobüs Seferleri Taranıyor...";
        loadingStep2 = "Kamil Koç / FlixBus resmi seferleri, Pamukkale, Varan, Metro ve 180+ firmanın canlı koltuk fiyatları doğrulanıyor.";
    } else if (currentTransportSubTab === 'train') {
        vehicleIcon = "fa-train-subway";
        vehicleRotate = "rotate(0deg)";
        vehicleBg = "from-sky-500 to-blue-300";
        vehicleShadow = "shadow-sky-500/40";
        loadingStep1 = "TCDD Yüksek Hızlı Tren (YHT) Seferleri Taranıyor...";
        loadingStep2 = "TCDD Taşımacılık resmi e-bilet portalı, 597 istasyonluk tren ağı ve YHT canlı tarife saatleri doğrulanıyor.";
    } else if (currentTransportSubTab === 'ferry') {
        vehicleIcon = "fa-ship";
        vehicleRotate = "rotate(0deg)";
        vehicleBg = "from-cyan-500 to-teal-300";
        vehicleShadow = "shadow-cyan-500/40";
        loadingStep1 = "İDO, BUDO & Gemi Seferleri Taranıyor...";
        loadingStep2 = "İç hat Marmara arabalı vapurları, Kapıda Vize Yunan Adaları hızlı katamaranları ve Cruise turları doğrulanıyor.";
    } else if (currentTransportSubTab === 'car') {
        vehicleIcon = "fa-car";
        vehicleRotate = "rotate(0deg)";
        vehicleBg = "from-violet-500 to-indigo-300";
        vehicleShadow = "shadow-violet-500/40";
        loadingStep1 = "Kiralık Araç Filoları Taranıyor...";
        loadingStep2 = "Yolcu360, Enuygun, Avis & Garenta müsait filoları, kasko ve depozito koşulları karşılaştırılıyor.";
    }

    resultsArea.innerHTML = `
        <style>
            @keyframes moveVehicleSingleWay {
                0% { left: 0%; opacity: 0; transform: translateY(0px) ${vehicleRotate} scale(0.9); }
                10% { opacity: 1; transform: translateY(-4px) ${vehicleRotate} scale(1.05); }
                85% { opacity: 1; transform: translateY(-2px) ${vehicleRotate} scale(1.02); }
                100% { left: calc(100% - 36px); opacity: 0; transform: translateY(0px) ${vehicleRotate} scale(0.9); }
            }
            @keyframes streamTrail {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            .hakiki-vehicle-mover {
                position: absolute;
                top: -16px;
                animation: moveVehicleSingleWay 2.4s cubic-bezier(0.4, 0, 0.2, 1) infinite;
            }
            .hakiki-route-trail {
                animation: streamTrail 1.8s linear infinite;
            }
        </style>
        <div class="p-6 sm:p-10 text-center bg-gradient-to-br from-slate-950 via-[#0B1728] to-slate-900 rounded-3xl border border-sky-500/30 shadow-2xl relative overflow-hidden my-6">
            <!-- Arka Plan Radar Ağı & Yumuşak Parıltı -->
            <div class="absolute inset-0 opacity-15 pointer-events-none" style="background-image: radial-gradient(#38bdf8 1px, transparent 1px); background-size: 28px 28px;"></div>
            <div class="absolute -top-12 -left-12 w-48 h-48 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-12 -right-12 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <!-- Ulaşım Yolu & Tek Yöne İlerleyen Simge -->
            <div class="relative max-w-md mx-auto my-4 px-4">
                <!-- Rota Çizgisi -->
                <div class="h-2 w-full bg-slate-800/90 rounded-full relative overflow-hidden border border-sky-900/50">
                    <div class="hakiki-route-trail h-full w-full bg-gradient-to-r from-transparent via-amber-400 to-sky-400"></div>
                </div>

                <!-- Tek Yönlü Hareket Eden Araç Simgesi -->
                <div class="hakiki-vehicle-mover">
                    <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr ${vehicleBg} text-slate-950 flex items-center justify-center shadow-lg ${vehicleShadow} ring-2 ring-white/30">
                        <i class="fa-solid ${vehicleIcon} text-lg text-slate-950"></i>
                    </div>
                </div>

                <!-- Kalkış & Varış Nokta Rozetleri -->
                <div class="flex items-center justify-between text-xs font-black mt-5 text-sky-200">
                    <span class="flex items-center gap-1.5 bg-slate-900/90 border border-sky-400/30 px-3.5 py-1.5 rounded-xl shadow-xs">
                        <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                        <span class="text-white">${escapeHtml(origin)}</span>
                    </span>
                    <span class="flex items-center gap-1.5 bg-slate-900/90 border border-amber-400/30 px-3.5 py-1.5 rounded-xl shadow-xs">
                        <i class="fa-solid fa-location-dot text-amber-400"></i>
                        <span class="text-amber-300">${escapeHtml(destination)}</span>
                    </span>
                </div>
            </div>

            <!-- İlerleme Çubuğu ve Yüzde Göstergesi -->
            <div class="max-w-md mx-auto mt-6 px-4">
                <div class="flex items-center justify-between text-xs font-bold text-slate-300 mb-1.5">
                    <span id="searchProgressStatus" class="flex items-center gap-1.5 text-sky-300">
                        <i class="fa-solid fa-circle-notch fa-spin text-sky-400 text-[11px]"></i>
                        <span>Canlı veriler sorgulanıyor...</span>
                    </span>
                    <span id="searchProgressPct" class="text-amber-400 font-extrabold text-sm">%18</span>
                </div>
                <div class="w-full bg-slate-800/90 h-2.5 rounded-full overflow-hidden border border-slate-700 p-0.5 shadow-inner">
                    <div id="searchProgressBar" class="h-full bg-gradient-to-r from-amber-500 via-sky-400 to-emerald-400 rounded-full transition-all duration-300 ease-out" style="width: 18%;"></div>
                </div>
            </div>

            <!-- Bilgilendirme Metinleri -->
            <div class="relative z-10 space-y-1.5 mt-5">
                <div class="text-lg sm:text-xl font-black text-white flex items-center justify-center gap-2">
                    <span>${escapeHtml(origin)}</span>
                    <i class="fa-solid fa-arrow-right-long text-amber-400 text-sm"></i>
                    <span>${escapeHtml(destination)}</span>
                </div>
                <div class="text-xs sm:text-sm text-amber-300 font-extrabold flex items-center justify-center gap-2">
                    <span class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                    <span>${loadingStep1}</span>
                </div>
                <div class="text-[11px] sm:text-xs text-slate-400 font-medium max-w-lg mx-auto">
                    ${loadingStep2}
                </div>
            </div>
        </div>

        <!-- Modern Skeleton Screen (İskelet Kartlar) -->
        <div class="mt-6 space-y-4 max-w-5xl mx-auto">
            <div class="flex items-center justify-between px-2">
                <div class="h-4 bg-slate-200 rounded-md w-48 animate-pulse"></div>
                <div class="h-4 bg-slate-200 rounded-md w-28 animate-pulse"></div>
            </div>
            <!-- İskelet Kart 1 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm animate-pulse flex flex-col md:flex-row items-center justify-between gap-5">
                <div class="flex items-center gap-3.5 w-full md:w-auto">
                    <div class="w-12 h-12 rounded-xl bg-slate-200 shrink-0"></div>
                    <div class="space-y-2 flex-1">
                        <div class="h-4 bg-slate-200 rounded w-32"></div>
                        <div class="h-3 bg-slate-100 rounded w-20"></div>
                    </div>
                </div>
                <div class="flex items-center gap-6 w-full md:w-auto justify-between md:justify-center">
                    <div class="space-y-1 text-center">
                        <div class="h-5 bg-slate-200 rounded w-16 mx-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-10 mx-auto"></div>
                    </div>
                    <div class="w-28 flex flex-col items-center gap-1.5">
                        <div class="h-2 bg-slate-200 rounded-full w-full"></div>
                        <div class="h-2.5 bg-slate-100 rounded w-14"></div>
                    </div>
                    <div class="space-y-1 text-center">
                        <div class="h-5 bg-slate-200 rounded w-16 mx-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-10 mx-auto"></div>
                    </div>
                </div>
                <div class="flex items-center justify-between md:justify-end gap-3 w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                    <div class="space-y-1 text-right">
                        <div class="h-6 bg-slate-200 rounded w-20 ml-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-14 ml-auto"></div>
                    </div>
                    <div class="w-32 h-10 bg-slate-200 rounded-xl shrink-0"></div>
                </div>
            </div>
            <!-- İskelet Kart 2 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm animate-pulse flex flex-col md:flex-row items-center justify-between gap-5">
                <div class="flex items-center gap-3.5 w-full md:w-auto">
                    <div class="w-12 h-12 rounded-xl bg-slate-200 shrink-0"></div>
                    <div class="space-y-2 flex-1">
                        <div class="h-4 bg-slate-200 rounded w-36"></div>
                        <div class="h-3 bg-slate-100 rounded w-24"></div>
                    </div>
                </div>
                <div class="flex items-center gap-6 w-full md:w-auto justify-between md:justify-center">
                    <div class="space-y-1 text-center">
                        <div class="h-5 bg-slate-200 rounded w-16 mx-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-10 mx-auto"></div>
                    </div>
                    <div class="w-28 flex flex-col items-center gap-1.5">
                        <div class="h-2 bg-slate-200 rounded-full w-full"></div>
                        <div class="h-2.5 bg-slate-100 rounded w-14"></div>
                    </div>
                    <div class="space-y-1 text-center">
                        <div class="h-5 bg-slate-200 rounded w-16 mx-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-10 mx-auto"></div>
                    </div>
                </div>
                <div class="flex items-center justify-between md:justify-end gap-3 w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                    <div class="space-y-1 text-right">
                        <div class="h-6 bg-slate-200 rounded w-20 ml-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-14 ml-auto"></div>
                    </div>
                    <div class="w-32 h-10 bg-slate-200 rounded-xl shrink-0"></div>
                </div>
            </div>
            <!-- İskelet Kart 3 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm animate-pulse flex flex-col md:flex-row items-center justify-between gap-5">
                <div class="flex items-center gap-3.5 w-full md:w-auto">
                    <div class="w-12 h-12 rounded-xl bg-slate-200 shrink-0"></div>
                    <div class="space-y-2 flex-1">
                        <div class="h-4 bg-slate-200 rounded w-28"></div>
                        <div class="h-3 bg-slate-100 rounded w-20"></div>
                    </div>
                </div>
                <div class="flex items-center gap-6 w-full md:w-auto justify-between md:justify-center">
                    <div class="space-y-1 text-center">
                        <div class="h-5 bg-slate-200 rounded w-16 mx-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-10 mx-auto"></div>
                    </div>
                    <div class="w-28 flex flex-col items-center gap-1.5">
                        <div class="h-2 bg-slate-200 rounded-full w-full"></div>
                        <div class="h-2.5 bg-slate-100 rounded w-14"></div>
                    </div>
                    <div class="space-y-1 text-center">
                        <div class="h-5 bg-slate-200 rounded w-16 mx-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-10 mx-auto"></div>
                    </div>
                </div>
                <div class="flex items-center justify-between md:justify-end gap-3 w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                    <div class="space-y-1 text-right">
                        <div class="h-6 bg-slate-200 rounded w-20 ml-auto"></div>
                        <div class="h-3 bg-slate-100 rounded w-14 ml-auto"></div>
                    </div>
                    <div class="w-32 h-10 bg-slate-200 rounded-xl shrink-0"></div>
                </div>
            </div>
        </div>
    `;
    resultsArea.classList.remove("hidden");
    resultsArea.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Dinamik Yüzde & Durum Simülatörü
    let progressVal = 18;
    const progressInterval = setInterval(() => {
        if (progressVal < 92) {
            progressVal += Math.floor(Math.random() * 8) + 4;
            if (progressVal > 92) progressVal = 92;
            const barEl = document.getElementById("searchProgressBar");
            const pctEl = document.getElementById("searchProgressPct");
            const statusEl = document.getElementById("searchProgressStatus");
            if (barEl) barEl.style.width = progressVal + "%";
            if (pctEl) pctEl.textContent = "%" + progressVal;
            if (statusEl) {
                if (progressVal > 70) {
                    statusEl.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-emerald-400 text-[11px]"></i><span>En uygun hakiki fiyatlar teyit ediliyor...</span>`;
                } else if (progressVal > 40) {
                    statusEl.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-amber-400 text-[11px]"></i><span>Canlı seferler ve koltuklar taranıyor...</span>`;
                }
            }
        }
    }, 240);

    try {
        if (window._activeTransportAbort) {
            try { window._activeTransportAbort.abort(); } catch (_) {}
        }
        const abortCtrl = new AbortController();
        window._activeTransportAbort = abortCtrl;
        const searchSeq = (window._activeTransportSearchSeq = (window._activeTransportSearchSeq || 0) + 1);

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
            ferry_vehicle_type: currentFerryVehicleType,
            trip_type: isRound ? 'round_trip' : 'one_way',
            include_hotel: false, // Kullanıcı talimatı: Şimdilik otel önerilerini kaldır
            currency: activeCurrency
        };

        const res = await fetch("/api/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: abortCtrl.signal
        });

        if (searchSeq !== window._activeTransportSearchSeq) return;
        if (!res.ok) throw new Error("Arama sunucusundan yanıt alınamadı.");
        const data = await res.json();
        if (searchSeq !== window._activeTransportSearchSeq) return;
        clearInterval(progressInterval);
        const finalBar = document.getElementById("searchProgressBar");
        const finalPct = document.getElementById("searchProgressPct");
        if (finalBar) finalBar.style.width = "100%";
        if (finalPct) finalPct.textContent = "%100";
        if (data.travel_context) {
            window.HakikiTravelContext = data.travel_context;
        }
        renderTransportResults(data, payload);
    } catch (err) {
        clearInterval(progressInterval);
        if (err && err.name === "AbortError") return;
        resultsArea.innerHTML = `
            <div class="p-8 text-center bg-rose-50 border border-rose-200 rounded-3xl text-rose-800 shadow-xs">
                <i class="fa-solid fa-circle-exclamation text-2xl mb-2 text-rose-500"></i>
                <div class="font-bold text-base">Arama sırasında bir bağlantı sorunu oluştu.</div>
                <div class="text-xs mt-1 text-rose-600 font-medium">${escapeHtml(err.message)}</div>
            </div>

        `;
    }
}

// Ulaşım Sonuçlarını Render Et (Google Flights & Skyscanner Standardı • Canlı Sefer Saatleri & Çift Bacak)
function renderTransportResults(data, searchReq) {
    const resultsArea = document.getElementById("transportResultsArea");
    if (data && (data.flexible_insights || data.destination_cross_sell || data.car_rental || data.notices || data.deep_links)) {
        window.lastTransportData = data;
    } else if (window.lastTransportData) {
        data = Object.assign({}, window.lastTransportData, data);
    }
    const tickets = data.tickets || [];
    window.lastTransportResults = tickets;
    window.lastSearchReq = searchReq;

    const cinDate = searchReq.departure_date;
    const coutDate = searchReq.return_date || getNextDaysDate(cinDate, 2);

    let html = '';

    const isEn = window.currentAppLang === 'en';
    const modeType = searchReq.transport_type || 'flight';
    // Ulaşım Bilgi ve Kriter Özeti Çubuğu
    const adultWord = isEn ? ((searchReq.adults || 1) > 1 ? "Adults" : "Adult") : "Yetişkin";
    const childWord = isEn ? (searchReq.children > 1 ? "Children" : "Child") : "Çocuk";
    const infantWord = isEn ? (searchReq.infants > 1 ? "Infants" : "Infant") : "Bebek";
    let modeExtraSuffix = '';
    if (modeType === 'flight') {
        modeExtraSuffix = ' • ' + (searchReq.cabin_class === 'business' ? 'Business' : (isEn ? 'Economy' : 'Ekonomi'));
    } else if (modeType === 'ferry') {
        const fVeh = searchReq.ferry_vehicle_type || currentFerryVehicleType || 'passenger';
        if (fVeh === 'car') {
            modeExtraSuffix = ' • 🚗 ' + (isEn ? 'Car / SUV' : 'Otomobil');
        } else if (fVeh === 'motorcycle') {
            modeExtraSuffix = ' • 🏍️ ' + (isEn ? 'Motorcycle' : 'Motosiklet');
        } else {
            modeExtraSuffix = ' • 🚶 ' + (isEn ? 'Foot Passenger' : 'Yaya');
        }
    }
    const paxSummaryText = `${searchReq.adults || 1} ${adultWord}${searchReq.children ? ', ' + searchReq.children + ' ' + childWord : ''}${searchReq.infants ? ', ' + searchReq.infants + ' ' + infantWord : ''}${modeExtraSuffix}`;
    const tripTypeText = searchReq.trip_type === 'round_trip' 
        ? `${isEn ? 'Round-Trip' : 'Gidiş - Dönüş'} (${searchReq.departure_date} ⇄ ${searchReq.return_date})` 
        : `${isEn ? 'One-Way' : 'Tek Yön'} (${searchReq.departure_date})`;
    
    const isIntlRoute = Boolean(data.travel_context && data.travel_context.is_international);
    let scopeLabel = '';
    let headerModeIcon = 'fa-plane-departure';
    if (modeType === 'bus') {
        scopeLabel = isIntlRoute ? (isEn ? '🌍 International Bus' : '🌍 Uluslararası Otobüs') : (isEn ? '🚌 Domestic Bus' : '🚌 Otobüs Seferleri');
        headerModeIcon = 'fa-bus';
    } else if (modeType === 'train') {
        scopeLabel = isIntlRoute ? (isEn ? '🌍 European Rail' : '🌍 Avrupa Tren Hattı') : (isEn ? '🚆 TCDD & High-Speed Rail' : '🚆 Tren & YHT Seferleri');
        headerModeIcon = 'fa-train';
    } else if (modeType === 'ferry') {
        scopeLabel = isIntlRoute ? (isEn ? '⛴️ Greek Islands & Cruise' : '⛴️ Yunan Adaları & Cruise') : (isEn ? '⛴️ Domestic Ferry' : '⛴️ Deniz & Feribot Seferleri');
        headerModeIcon = 'fa-ship';
    } else if (modeType === 'car') {
        scopeLabel = isEn ? '🚗 Car Rental Comparison' : '🚗 Kiralık Araç Karşılaştırma';
        headerModeIcon = 'fa-car-side';
    } else {
        scopeLabel = isIntlRoute
            ? (isEn ? '🌍 International Flight' : '🌍 Yurtdışı Uçuş')
            : (isEn ? '🇹🇷 Domestic Flight' : '🇹🇷 Yurtiçi Uçuş');
        headerModeIcon = 'fa-plane-departure';
    }

    html += `
        <div class="bg-slate-900 text-white rounded-2xl px-4 py-3 mb-3 flex flex-wrap items-center justify-between gap-3 shadow-sm border border-slate-800">
            <div class="flex flex-wrap items-center gap-2.5">
                <span class="px-2.5 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider bg-amber-400 text-slate-950">
                    ${scopeLabel}
                </span>
                <h3 class="text-base sm:text-lg font-black text-white flex items-center gap-2">
                    <span>${escapeHtml(searchReq.origin)}</span>
                    <i class="fa-solid ${headerModeIcon} text-amber-400 text-xs"></i>
                    <span>${escapeHtml(searchReq.destination)}</span>
                </h3>
                <span class="text-xs text-slate-300 font-semibold hidden sm:inline">• ${tripTypeText}</span>
            </div>
            <div class="flex items-center gap-2 text-xs font-bold text-amber-300">
                <i class="fa-solid fa-user-group text-[11px]"></i>
                <span>${paxSummaryText}</span>
            </div>
        </div>
    `;

    // Adana / Mersin Ortak Bölgesel Havalimanı (Çukurova - COV) Bilgilendirme Bandı
    const rawSearchCombo = `${searchReq.origin || ''} ${searchReq.destination || ''}`.toLowerCase();
    const hasCovFlight = modeType === 'flight' && (
        rawSearchCombo.includes('cov') ||
        rawSearchCombo.includes('çukurova') ||
        rawSearchCombo.includes('cukurova') ||
        rawSearchCombo.includes('adana') ||
        rawSearchCombo.includes('mersin') ||
        tickets.some(t => t.from_code === 'COV' || t.to_code === 'COV')
    );
    if (hasCovFlight) {
        html += `
            <div class="bg-sky-50 border border-sky-200 text-sky-900 rounded-xl px-3.5 py-2 mb-3 text-xs font-semibold flex items-center gap-2">
                <i class="fa-solid fa-circle-info text-sky-600 shrink-0"></i>
                <span>
                    ${isEn
                        ? '<strong>Regional Airport Info:</strong> All Adana and Mersin flights operate via the shared <strong>Çukurova International Airport (COV)</strong> (listed as <em>"Mersin (COV)"</em> on global portals like Trip.com).'
                        : '<strong>Bölgesel Havalimanı Bilgilendirmesi:</strong> Adana ve Mersin uçuşları ortak kullanılan <strong>Çukurova Uluslararası Havalimanı (COV)</strong> üzerinden icra edilmektedir (Trip.com gibi global sistemlerde <em>"Mersin (COV)"</em> olarak listelenir).'}
                </span>
            </div>
        `;
    }

    // Popüler İlçe / Bölge ➔ En Yakın Havalimanı Yönlendirme Bilgilendirmesi (Marmaris ➔ Dalaman vb.)
    if (modeType === 'flight' && window._lastDistrictNotice) {
        html += `
            <div class="bg-amber-50 border border-amber-200 text-amber-950 rounded-xl px-3.5 py-2 mb-3 text-xs font-semibold flex items-center gap-2">
                <i class="fa-solid fa-location-dot text-amber-600 shrink-0"></i>
                <span>${escapeHtml(window._lastDistrictNotice)}</span>
            </div>
        `;
    }

    // ==================== KOMPAKT 7 GÜNLÜK FİYAT ŞERİDİ + "HAKİKİ İPUCU" ====================
    const flexInsights = data.flexible_insights;
    const altBadges = data.alternative_badges || [];
    if (flexInsights && Array.isArray(flexInsights.days) && flexInsights.days.length > 0) {
        const tip = flexInsights.hakiki_tip;
        const fmtNum = (n) => Number(n).toLocaleString(isEn ? 'en-US' : 'tr-TR');

        html += `<div class="bg-white border border-slate-200 rounded-2xl p-3 mb-3 shadow-2xs">`;

        // 1. Üst "💡 Hakiki İpucu" Bandı (Tek Satır Kompakt)
        if (tip && tip.has_savings) {
            const selDayName = isEn ? tip.selected_weekday_en : tip.selected_weekday_tr;
            const bestDayName = isEn ? tip.best_weekday_en : tip.best_weekday_tr;
            const diffTxt = isEn ? tip.diff_text_en : tip.diff_text_tr;
            const bestLbl = isEn ? tip.best_label_en : tip.best_label_tr;
            html += `
                <div class="bg-emerald-950 text-white rounded-xl px-3 py-2 mb-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
                    <div class="flex items-center gap-2">
                        <span class="text-amber-400 font-black">💡 ${isEn ? 'Smart Tip:' : 'Hakiki İpucu:'}</span>
                        <span>
                            ${isEn
                                ? `Instead of <strong>${selDayName}</strong>, travel on <strong>${bestDayName} (${diffTxt})</strong> from <strong class="text-emerald-300">${fmtNum(tip.best_price)} ${tip.currency}</strong> (${fmtNum(tip.savings)} ${tip.currency} cheaper!)`
                                : `<strong>${selDayName}</strong> yerine <strong>${bestDayName} (${diffTxt})</strong> seçerseniz <strong class="text-emerald-300">${fmtNum(tip.best_price)} ${tip.currency}</strong> (${fmtNum(tip.savings)} ${tip.currency} daha ucuz!)`
                            }
                        </span>
                    </div>
                    <button type="button" onclick="switchSearchDate('${tip.best_date}')"
                            class="px-2.5 py-1 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-black text-[11px] whitespace-nowrap transition cursor-pointer shrink-0">
                        ${isEn ? `Switch (${bestLbl}) →` : `${bestLbl} Seç →`}
                    </button>
                </div>
            `;
        }

        // 2. 7 Günlük Yatay Fiyat Şeridi (İnce & Minimalist)
        html += `
            <div class="grid grid-cols-7 gap-1.5">
                ${flexInsights.days.map(d => {
                    const lbl = isEn ? d.label_en : d.label_tr;
                    const pText = d.min_price ? `${fmtNum(d.min_price)} ${d.currency}` : (isEn ? 'Check' : 'Sorgula');
                    if (d.is_selected) {
                        return `
                            <button type="button" onclick="switchSearchDate('${d.date}')"
                                    class="py-1.5 px-1 rounded-xl bg-slate-900 text-white border border-slate-900 text-center transition cursor-pointer flex flex-col items-center justify-center">
                                <span class="text-[10px] font-bold text-slate-300 truncate w-full">${lbl}</span>
                                <span class="text-xs font-black text-amber-400">${pText}</span>
                            </button>
                        `;
                    } else if (d.is_cheapest) {
                        return `
                            <button type="button" onclick="switchSearchDate('${d.date}')"
                                    class="py-1.5 px-1 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-slate-900 border border-emerald-500 text-center transition cursor-pointer flex flex-col items-center justify-center">
                                <span class="text-[10px] font-bold text-emerald-800 truncate w-full">🔥 ${lbl}</span>
                                <span class="text-xs font-black text-emerald-700">${pText}</span>
                            </button>
                        `;
                    } else {
                        return `
                            <button type="button" onclick="switchSearchDate('${d.date}')"
                                    class="py-1.5 px-1 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-center transition cursor-pointer flex flex-col items-center justify-center">
                                <span class="text-[10px] font-semibold text-slate-500 truncate w-full">${lbl}</span>
                                <span class="text-xs font-black text-slate-900">${pText}</span>
                            </button>
                        `;
                    }
                }).join('')}
            </div>
        `;

        // 3. Haftanın En Ucuz Otobüs & Tren Alternatif Rozetleri (Tek Satır)
        if (altBadges.length > 0) {
            html += `
                <div class="mt-2 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                    <span class="font-bold text-slate-500">⚡ ${isEn ? 'Alternative Modes:' : 'Alternatif Ulaşım:'}</span>
                    <div class="flex flex-wrap items-center gap-1.5">
                        ${altBadges.map(b => {
                            const bTitle = isEn ? b.title_en : b.title_tr;
                            const bPrice = b.min_price ? `${fmtNum(b.min_price)} ${b.currency}` : (isEn ? 'Live Fares' : 'Canlı');
                            return `
                                <button type="button" onclick="switchUnifiedTab('${b.mode}'); executeTransportSearch();"
                                        class="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-900 hover:text-white text-slate-800 border border-slate-200 text-[11px] font-bold transition cursor-pointer inline-flex items-center gap-1.5">
                                    <span>${b.icon} ${bTitle}:</span>
                                    <span class="font-black text-amber-700">${bPrice}</span>
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        html += `</div>`;
    }

    // Filtre & Hızlı Sıralama Çubuğu (Kompakt Tek Satır)
    if (['flight', 'bus', 'train', 'ferry'].includes(currentTransportSubTab) && tickets.length > 1) {
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
        const isMultiAirportCity = currentTransportSubTab === 'flight' && ((hasSaw && hasIst) || 
            (searchReq.origin && searchReq.origin.toLowerCase().includes('istanbul')) ||
            (searchReq.destination && searchReq.destination.toLowerCase().includes('istanbul')));
        const unitLabel = currentTransportSubTab === 'flight' ? 'uçuş' : 'sefer';

        html += `
            <div class="bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 mb-3 shadow-2xs flex flex-col gap-2">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div class="flex flex-wrap items-center gap-1.5">
                        <span class="text-[11px] font-black text-slate-600 mr-1">
                            <i class="fa-solid fa-arrow-down-wide-short text-amber-500"></i> Sırala:
                        </span>
                        <button type="button" onclick="setFlightSort('cheapest')" id="fltSort-cheapest" class="flt-sort-btn px-2.5 py-1 rounded-lg text-[11px] font-black bg-slate-900 text-white transition cursor-pointer">
                            💰 En Ucuz
                        </button>
                        <button type="button" onclick="setFlightSort('fastest')" id="fltSort-fastest" class="flt-sort-btn px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            ⚡ En Hızlı
                        </button>
                        <button type="button" onclick="setFlightSort('earliest')" id="fltSort-earliest" class="flt-sort-btn px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            🛫 En Erken
                        </button>
                        <button type="button" onclick="setFlightSort('latest')" id="fltSort-latest" class="flt-sort-btn px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            🛬 En Geç
                        </button>
                    </div>

                    <div class="flex flex-wrap items-center gap-1">
                        <button type="button" onclick="setFlightTimeFilter('all')" id="fltTime-all" class="flt-time-btn px-2 py-1 rounded-lg text-[11px] font-black bg-amber-500 text-white transition cursor-pointer">
                            Tümü
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('night')" id="fltTime-night" class="flt-time-btn px-2 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            🌙 00-06
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('morning')" id="fltTime-morning" class="flt-time-btn px-2 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            🌅 06-12
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('noon')" id="fltTime-noon" class="flt-time-btn px-2 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            ☀️ 12-18
                        </button>
                        <button type="button" onclick="setFlightTimeFilter('evening')" id="fltTime-evening" class="flt-time-btn px-2 py-1 rounded-lg text-[11px] font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer">
                            🌆 18+
                        </button>
                        <span id="fltCountBadge" class="ml-1 text-[11px] font-bold text-slate-400">
                            (${tickets.length} ${unitLabel})
                        </span>
                    </div>
                </div>

                ${isMultiAirportCity ? `
                    <div class="flex flex-wrap items-center gap-1.5 pt-1.5 border-t border-slate-100">
                        <span class="text-[11px] font-black text-slate-600 mr-1">Havalimanı:</span>
                        <button type="button" onclick="setFlightAirportFilter('all')" id="fltPort-all" class="flt-port-btn px-2.5 py-0.5 rounded-lg text-[11px] font-black bg-slate-900 text-white transition cursor-pointer">
                            Tümü (${tickets.length})
                        </button>
                        <button type="button" onclick="setFlightAirportFilter('SAW')" id="fltPort-SAW" class="flt-port-btn px-2.5 py-0.5 rounded-lg text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            SAW (Sabiha Gökçen)
                        </button>
                        <button type="button" onclick="setFlightAirportFilter('IST')" id="fltPort-IST" class="flt-port-btn px-2.5 py-0.5 rounded-lg text-[11px] font-bold text-slate-700 hover:bg-slate-100 transition cursor-pointer">
                            IST (İstanbul Havalimanı)
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }



    // A. SEFER VEYA KİRALIK ARAÇ KARTLARI
    if (searchReq.transport_type === 'car' && data.car_rental && Array.isArray(data.car_rental.vehicles) && data.car_rental.vehicles.length > 0) {
        const cr = data.car_rental;
        const cSym = data.currency || cr.currency || '₺';

        // Aktif filtreleri uygula (Segment ve Vites)
        let filteredVehicles = cr.vehicles || [];
        if (currentCarCategoryFilter && currentCarCategoryFilter !== 'all') {
            filteredVehicles = filteredVehicles.filter(v => (v.category || '').toLowerCase().includes(currentCarCategoryFilter.toLowerCase()));
        }
        if (currentCarTransmissionFilter && currentCarTransmissionFilter !== 'all') {
            filteredVehicles = filteredVehicles.filter(v => (v.transmission || '').toLowerCase().includes(currentCarTransmissionFilter.toLowerCase()));
        }

        // Kiralama Özet Bilgi Şeridi
        html += `
            <div class="bg-amber-50/90 border border-amber-200 rounded-3xl p-4 sm:p-5 mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                <div class="flex items-center gap-3.5">
                    <div class="w-10 h-10 rounded-2xl bg-amber-500 text-slate-950 flex items-center justify-center text-xl font-black shadow-xs">
                        🚗
                    </div>
                    <div>
                        <div class="text-sm sm:text-base font-black text-slate-900">
                            ${escapeHtml(cr.location)} • ${escapeHtml(cr.location_type_label || 'Havalimanı / Merkez Ofisleri')}
                        </div>
                        <div class="text-xs font-semibold text-slate-600 mt-0.5 flex flex-wrap items-center gap-2">
                            <span>📅 <strong>${escapeHtml(cr.pickup_date)}</strong> ➔ <strong>${escapeHtml(cr.dropoff_date)}</strong></span>
                            <span>•</span>
                            <span class="text-amber-900 font-black">⏱️ ${cr.days_count} Günlük Kiralama</span>
                            <span>•</span>
                            <span class="text-emerald-700 font-bold">⚡ Sınırsız Kilometre</span>
                        </div>
                    </div>
                </div>
                <div class="text-xs font-bold text-slate-600 flex items-center gap-2 border-t sm:border-t-0 pt-2 sm:pt-0 border-amber-200">
                    <i class="fa-solid fa-circle-check text-emerald-600"></i>
                    <span>Yolcu360, Enuygun, Avis & Garenta Karşılaştırmalı</span>
                </div>
            </div>
        `;

        if (filteredVehicles.length === 0) {
            html += `
                <div class="bg-white p-8 rounded-3xl border-2 border-slate-200 text-center shadow-xs mb-6">
                    <i class="fa-solid fa-filter-circle-xmark text-3xl text-amber-500 mb-2"></i>
                    <div class="font-black text-slate-800 text-base">Seçtiğiniz filtreye (${currentCarCategoryFilter !== 'all' ? currentCarCategoryFilter : ''} ${currentCarTransmissionFilter !== 'all' ? currentCarTransmissionFilter : ''}) uygun araç bulunamadı.</div>
                    <div class="text-xs text-slate-500 mt-1 font-medium">Lütfen filtreleri sıfırlayarak tüm araç filosunu görüntüleyin.</div>
                    <button type="button" onclick="setCarCategoryFilter('all'); setCarTransmissionFilter('all');" class="mt-4 px-4 py-2 bg-slate-900 text-white font-bold text-xs rounded-xl shadow-xs hover:bg-black transition">
                        Filtreleri Temizle
                    </button>
                </div>
            `;
        } else {
            html += `<div class="space-y-4 mb-6">`;
            html += filteredVehicles.map(v => `
                <div class="bg-white border-2 border-slate-200 hover:border-amber-400 rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-xl transition-all mb-4">
                    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-5">
                        
                        <!-- Sol / Araç & Segment Detayları -->
                        <div class="flex-1 min-w-0">
                            <!-- Üst Rozet Satırı -->
                            <div class="flex flex-wrap items-center gap-2 mb-2.5">
                                <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-amber-100 text-amber-900 border border-amber-200 uppercase">
                                    ${escapeHtml(v.category)}
                                </span>
                                ${v.badge ? `
                                    <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-orange-100 text-orange-900 border border-orange-200">
                                        ${escapeHtml(v.badge)}
                                    </span>
                                ` : ''}
                                <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-emerald-100 text-emerald-800">
                                    ⚡ Sınırsız Km
                                </span>
                                <span class="px-2 py-0.5 rounded-md text-[10.5px] font-bold bg-slate-100 text-slate-600">
                                    🛡️ ${escapeHtml(v.deposit || 'Depozito')}
                                </span>
                            </div>

                            <!-- Araç Modeli ve İkonu -->
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center text-2xl shadow-2xs">
                                    ${v.image_icon || '🚗'}
                                </div>
                                <div>
                                    <h4 class="text-lg sm:text-xl font-black text-slate-900 leading-snug">
                                        ${escapeHtml(v.car_model)}
                                    </h4>
                                    <div class="text-xs font-semibold text-slate-500 flex items-center gap-1.5 mt-0.5">
                                        <i class="fa-solid fa-location-dot text-amber-500"></i>
                                        <span>${escapeHtml(v.pickup_point || cr.location)}</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Donanım ve Kapasite Özellikleri -->
                            <div class="flex flex-wrap items-center gap-2 mt-3.5 text-xs font-bold text-slate-700">
                                <span class="px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-1">
                                    ⚙️ <strong>${escapeHtml(v.transmission)}</strong>
                                </span>
                                <span class="px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-1">
                                    ⛽ <strong>${escapeHtml(v.fuel)}</strong>
                                </span>
                                <span class="px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-1">
                                    👥 <strong>${v.seats} Koltuk</strong>
                                </span>
                                <span class="px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-1">
                                    🧳 <strong>${escapeHtml(v.luggage)}</strong>
                                </span>
                                <span class="px-2.5 py-1 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                                    ❄️ <strong>Klima Dahil</strong>
                                </span>
                            </div>

                            <!-- Sağlayıcı Fiyat Karşılaştırma Şeridi -->
                            <div class="mt-3.5 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-2">
                                <span class="text-[10px] font-black uppercase text-slate-400">Şeffaf Sağlayıcı Fiyatları:</span>
                                ${(v.providers || []).map(p => `
                                    <a href="${p.url}" target="_blank" rel="noopener noreferrer"
                                       class="px-2.5 py-1 rounded-xl text-xs font-bold border ${p.is_cheapest ? 'bg-amber-50 border-amber-400 text-amber-950 font-black shadow-2xs' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'} transition inline-flex items-center gap-1.5">
                                        ${getBrandLogoHtml(p.name, '🚗', 'w-4 h-4')}
                                        <span>${escapeHtml(p.name)}</span>
                                        <span class="font-black">${Number(p.daily_price).toLocaleString('tr-TR')} ${cSym}/gün</span>
                                        ${p.is_cheapest ? '<span class="text-[9px] px-1 py-0.2 rounded bg-amber-200 text-amber-900 font-black">🏆 EN UCUZ</span>' : ''}
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-60"></i>
                                    </a>
                                `).join('')}
                            </div>
                        </div>

                        <!-- Sağ / Günlük & Toplam Fiyat ve Doğrudan Rezervasyon Butonu -->
                        <div class="lg:w-64 flex flex-col justify-between items-end border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6">
                            <div class="text-right w-full">
                                <div class="text-[10px] font-black uppercase tracking-wider text-slate-400 flex items-center justify-end gap-1">
                                    <i class="fa-solid fa-circle-check text-emerald-500"></i>
                                    <span>Doğrulanmış Günlük Taban</span>
                                </div>
                                <div class="text-3xl font-black text-slate-950 mt-1">
                                    ${Number(v.daily_price).toLocaleString('tr-TR')} <span class="text-lg font-bold">${cSym}</span>
                                    <span class="text-xs font-medium text-slate-400">/ gün</span>
                                </div>
                                <div class="text-xs font-black text-emerald-700 mt-1">
                                    Toplam: ${Number(v.total_price).toLocaleString('tr-TR')} ${cSym} (${cr.days_count} Gün)
                                </div>
                            </div>

                            <div class="w-full mt-4">
                                <a href="${v.official_link || (v.providers && v.providers[0] ? v.providers[0].url : '#')}" target="_blank" rel="noopener noreferrer"
                                   class="w-full py-3 px-4 bg-gradient-to-r from-amber-500 via-amber-600 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-black text-xs sm:text-sm rounded-2xl shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 group">
                                    <span>${escapeHtml(v.cheapest_provider_name || 'Yolcu360')} ile Kirala</span>
                                    <i class="fa-solid fa-arrow-up-right-from-square text-xs group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"></i>
                                </a>
                                <div class="text-[10px] text-center text-slate-400 font-medium mt-1.5">
                                    Sıfır ek komisyon • Doğrudan güvenli filo rezervasyonu
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            `).join('');
            html += `</div>`;
        }
    } else if (tickets.length === 0) {
        const routeNotices = (data.notices || []).filter(n => !n.includes("Güven ve Şeffaflık İlkesi"));
        const primaryNotice = routeNotices.length > 0
            ? routeNotices[0]
            : (isEn ? "No direct scheduled service found on this route for the selected date." : "Bu güzergahta seçili tarihte doğrudan sefer bulunamadı.");
        const secondaryNotice = routeNotices.length > 1
            ? routeNotices.slice(1).join(" • ")
            : (modeType === 'ferry'
                ? (isEn ? "Please select a coastal port or use Smart Route for combined travel." : "Lütfen feribot iskelesi olan bir kıyı noktası seçiniz veya aşağıdaki resmi deniz acentelerinden güncel seferleri sorgulayınız.")
                : (modeType === 'train'
                    ? (isEn ? "Please check bus or flight options for this route." : "Bu güzergah için otobüs veya uçak alternatiflerini inceleyebilirsiniz.")
                    : (isEn ? "Please try a different date or transport mode." : "Lütfen farklı bir tarih veya alternatif ulaşım modunu seçiniz.")));
        const emptyIcon = modeType === 'ferry' ? 'fa-anchor-circle-xmark' : (modeType === 'train' ? 'fa-train' : (modeType === 'bus' ? 'fa-bus' : 'fa-plane-slash'));
        const deepLinksList = Array.isArray(data.deep_links) ? data.deep_links : [];
        html += `
            <div class="bg-white p-8 sm:p-10 rounded-3xl border-2 border-slate-200 text-center shadow-xs mb-6">
                <i class="fa-solid ${emptyIcon} text-3xl text-amber-500 mb-3"></i>
                <div class="font-black text-slate-800 text-base">${escapeHtml(primaryNotice)}</div>
                <div class="text-xs text-slate-500 mt-1.5 font-medium max-w-2xl mx-auto">${escapeHtml(secondaryNotice)}</div>
                ${deepLinksList.length > 0 ? `
                    <div class="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-center gap-2">
                        ${deepLinksList.map((dl, idx) => `
                            <a href="${dl.url}" target="_blank" rel="noopener noreferrer"
                               class="px-3.5 py-2 rounded-xl text-xs font-black transition inline-flex items-center gap-1.5 ${idx === 0 ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-sm' : 'bg-slate-100 hover:bg-slate-900 hover:text-white text-slate-800 border border-slate-200'}">
                                <span>${escapeHtml(dl.name)}</span>
                                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                            </a>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

 else {
        const ferryOperationalNotices = (modeType === 'ferry' && Array.isArray(data.notices))
            ? data.notices.filter(n => !n.includes("Güven ve Şeffaflık İlkesi"))
            : [];
        if (ferryOperationalNotices.length > 0) {
            html += `
                <div class="bg-sky-950 text-white rounded-2xl px-4 py-3 mb-3 border border-sky-800 shadow-xs space-y-1.5">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[11px] font-black uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                            <i class="fa-solid fa-shield-halved"></i> Deniz Ulaşımı Operasyonel Rehberi & Kalkanlar
                        </span>
                        <span class="text-[10px] font-bold text-sky-300">Sıfır Varsayım • Canlı Kanal Karşılaştırmalı</span>
                    </div>
                    <div class="space-y-1 text-xs text-sky-100 font-medium leading-relaxed">
                        ${ferryOperationalNotices.map(fn => `<div class="flex items-start gap-1.5"><span class="text-amber-400 shrink-0">•</span><span>${escapeHtml(fn)}</span></div>`).join('')}
                    </div>
                </div>
            `;
        }
                if (!tickets || tickets.length === 0) {
            let emptyIcon = "fa-route";
            let emptyTitle = "Bu Güzergahta Doğrudan Sefer Bulunamadı";
            let emptyDesc = `${escapeHtml(searchReq.origin)} ile ${escapeHtml(searchReq.destination)} arasında seçtiğiniz tarihte tarifeli sefer bulunamadı.`;
            let showAltButtons = true;

            if (modeType === 'train') {
                emptyIcon = "fa-train-subway";
                emptyTitle = "Seçilen Güzergahta Aktif Yolcu Treni / YHT Hattı Bulunmamaktadır";
                emptyDesc = `${escapeHtml(searchReq.origin)} ile ${escapeHtml(searchReq.destination)} arasında doğrudan tarifeli TCDD tren seferi bulunmamaktadır. Türkiye genelinde demiryolu yolcu hattı belirli koridorlarda (YHT ve anahat hatları) hizmet vermektedir. Kesintisiz seyahat için Otobüs veya Uçak alternatiflerini tek tıkla inceleyebilirsiniz.`;
            } else if (modeType === 'ferry') {
                emptyIcon = "fa-ship";
                emptyTitle = "Bu Güzergahta Tarifeli Feribot Seferi Bulunmamaktadır";
                emptyDesc = `${escapeHtml(searchReq.origin)} ile ${escapeHtml(searchReq.destination)} arasında doğrudan deniz yolu / feribot hattı yoktur. Deniz hatlarımız Marmara Denizi (İDO/BUDO), Ege Adaları (Kapıda Vize) ve KKTC limanlarında hizmet vermektedir.`;
            } else if (modeType === 'bus') {
                emptyIcon = "fa-bus";
                emptyTitle = "Bu Tarihte Doğrudan Otobüs Seferi Bulunamadı";
                emptyDesc = `${escapeHtml(searchReq.origin)} - ${escapeHtml(searchReq.destination)} rotasında seçilen tarihte doğrudan sefer bulunamamıştır. Lütfen seyahat tarihinizi değiştiriniz veya uçuş alternatiflerini kontrol ediniz.`;
            }

            html += `
                <div class="bg-gradient-to-br from-slate-900 via-slate-850 to-slate-950 text-white rounded-3xl p-6 sm:p-8 my-4 border border-amber-500/40 shadow-xl text-center max-w-3xl mx-auto">
                    <div class="w-14 h-14 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-400/40 flex items-center justify-center text-2xl mx-auto mb-3 shadow-inner">
                        <i class="fa-solid ${emptyIcon}"></i>
                    </div>
                    <h3 class="text-lg sm:text-xl font-black text-amber-300">
                        ${emptyTitle}
                    </h3>
                    <p class="text-xs sm:text-sm text-slate-300 mt-2 max-w-xl mx-auto leading-relaxed">
                        ${emptyDesc}
                    </p>
                    ${showAltButtons ? `
                        <div class="mt-6 pt-5 border-t border-slate-800 flex flex-wrap items-center justify-center gap-3">
                            <span class="w-full text-xs font-bold text-slate-400 mb-1">Kesintisiz Ulaşım İçin Önerilen Alternatifler:</span>
                            ${modeType !== 'bus' ? `
                                <button type="button" onclick="switchToTransportAndSearch('bus')" class="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs transition cursor-pointer flex items-center gap-2 shadow-lg shadow-emerald-500/20">
                                    <i class="fa-solid fa-bus"></i>
                                    <span>🚌 Otobüs Seferlerini Gör</span>
                                </button>
                            ` : ''}
                            ${modeType !== 'flight' ? `
                                <button type="button" onclick="switchToTransportAndSearch('flight')" class="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs transition cursor-pointer flex items-center gap-2 shadow-lg shadow-amber-500/20">
                                    <i class="fa-solid fa-plane"></i>
                                    <span>✈️ Uçak Biletlerini Gör</span>
                                </button>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            html += `<div id="ticketCardsContainer" class="space-y-2.5 mb-5">`;
            html += generateTicketCardsHtml(tickets, searchReq);
            html += `</div>`;
        }
    }

    // ==================== ADIM 2.3: UÇUŞ / SEFER ALTI "GİTTİĞİNİZ YERDE BUNLAR VAR!" (OTEL + ARAÇ + ETKİNLİK/KEŞİF KÖPRÜSÜ) ====================
    const crossSell = data.destination_cross_sell;
    if (crossSell && crossSell.city) {
        const cCity = escapeHtml(crossSell.city);
        const cOrig = escapeHtml(crossSell.origin || searchReq.origin);
        const hl = crossSell.highlights || {};
        const evt = crossSell.matched_event;

        html += `
            <div class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-3xl p-5 sm:p-6 border border-slate-700 shadow-xl mt-6">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 mb-4 border-b border-slate-700/80">
                    <div>
                        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-400 text-slate-950">
                            🧭 ${cCity} Seyahat Tamamlayıcıları & Yerel Rehber
                        </span>
                        <h4 class="text-base sm:text-lg font-black text-white mt-1">
                            🎉 Siz Oradayken ${cCity} Şehrinde Neler Var? (Konaklama • Araç • Etkinlik & Keşif)
                        </h4>
                    </div>
                    <button type="button" onclick="openEventInSmartRoute('${cCity}', '${evt ? escapeHtml(evt.title) : ''}', '${searchReq.transport_type || 'flight'}')"
                            class="px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs transition cursor-pointer flex items-center gap-1.5 shrink-0">
                        <i class="fa-solid fa-wand-magic-sparkles"></i>
                        <span>Bu Seyahati Akıllı Rota ile Planla →</span>
                    </button>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <!-- KUTU 1: ETKİNLİK VEYA "ORADAYKEN BUNU MUTLAKA GÖRÜN" TAVSİYESİ -->
                    <div class="bg-slate-800/90 border ${evt ? 'border-amber-400/60' : 'border-slate-700'} rounded-2xl p-4 flex flex-col justify-between">
                        <div>
                            <div class="text-[10px] font-black uppercase ${evt ? 'text-amber-400' : 'text-sky-400'} mb-1">
                                ${evt ? '🎟️ Şehirdeki Canlı Etkinlik Yakalandı!' : '🏛️ Oradayken Bunları Mutlaka Görün!'}
                            </div>
                            ${evt ? `
                                <div class="font-black text-sm text-white mb-1">${escapeHtml(evt.title)}</div>
                                <div class="text-[11px] text-amber-300 font-bold mb-1.5"><i class="fa-regular fa-calendar mr-1"></i>${escapeHtml(evt.dates || '')} • ${escapeHtml(evt.badge || '')}</div>
                                <p class="text-xs text-slate-300 leading-relaxed mb-2">${escapeHtml(evt.desc || '')}</p>
                            ` : `
                                <div class="font-black text-sm text-white mb-1.5">${escapeHtml(hl.title || (cCity + ' Keşif Rehberi'))}</div>
                                <ul class="text-xs text-slate-300 space-y-1 mb-2">
                                    ${(hl.spots || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                                </ul>
                                ${hl.taste ? `<div class="text-[11px] text-amber-300 font-semibold mt-1.5">${escapeHtml(hl.taste)}</div>` : ''}
                            `}
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-slate-700/70 flex items-center justify-between gap-2">
                            ${evt ? `
                                <a href="${evt.ticket_url || '#'}" target="_blank" rel="noopener noreferrer" class="w-full py-2 px-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs text-center transition block">
                                    🎟️ Resmi Etkinlik Biletini Gör ↗
                                </a>
                            ` : `
                                <a href="https://www.google.com/maps/search/${encodeURIComponent(crossSell.city + ' gezilecek yerler ve restoranlar')}" target="_blank" rel="noopener noreferrer" class="w-full py-2 px-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs text-center transition block">
                                    <i class="fa-solid fa-map-location-dot text-amber-400 mr-1"></i> ${cCity} Gezi & Lezzet Haritası ↗
                                </a>
                            `}
                        </div>
                    </div>

                    <!-- KUTU 2: KONAKLAMA KÖPRÜSÜ (OTEL / PANSİYON / AIRBNB TARZI EV) -->
                    <div class="bg-slate-800/90 border border-slate-700 rounded-2xl p-4 flex flex-col justify-between">
                        <div>
                            <div class="text-[10px] font-black uppercase text-emerald-400 mb-1">
                                🏨 2. Bölüm • ${cCity} Konaklama Fırsatları
                            </div>
                            <div class="font-black text-sm text-white mb-1">Otel, Butik Pansiyon & Günlük Villa</div>
                            <p class="text-xs text-slate-300 leading-relaxed">
                                ${escapeHtml(hl.stay_tip || (cCity + ' merkezinde otel, pansiyon ve günlük kiralık ev alternatifleri.'))}
                            </p>
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-slate-700/70 grid grid-cols-3 gap-1.5">
                            <button type="button" onclick="triggerCrossSellStay('${cCity}', 'hotel', '${crossSell.checkin_date}', '${crossSell.checkout_date}')"
                                    class="py-2 px-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-[11px] transition cursor-pointer">
                                🏨 Otel
                            </button>
                            <button type="button" onclick="triggerCrossSellStay('${cCity}', 'pension', '${crossSell.checkin_date}', '${crossSell.checkout_date}')"
                                    class="py-2 px-2 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold text-[11px] transition cursor-pointer">
                                🏡 Pansiyon
                            </button>
                            <button type="button" onclick="triggerCrossSellStay('${cCity}', 'airbnb', '${crossSell.checkin_date}', '${crossSell.checkout_date}')"
                                    class="py-2 px-2 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold text-[11px] transition cursor-pointer">
                                🏠 Ev/Villa
                            </button>
                        </div>
                    </div>

                    <!-- KUTU 3: HAVALİMANI ARAÇ KİRALAMA & TRANSFER KÖPRÜSÜ -->
                    <div class="bg-slate-800/90 border border-slate-700 rounded-2xl p-4 flex flex-col justify-between">
                        <div>
                            <div class="text-[10px] font-black uppercase text-amber-400 mb-1">
                                🚗 İnişte Ulaşım & Araç Kiralama
                            </div>
                            <div class="font-black text-sm text-white mb-1">${cCity} Havalimanı / Gar Teslim Araçlar</div>
                            <p class="text-xs text-slate-300 leading-relaxed">
                                ${cCity} varışınızda havalimanı veya şehir merkezinden hemen teslim alabileceğiniz kiralık araçları karşılaştırın.
                            </p>
                        </div>
                        <div class="mt-3 pt-2.5 border-t border-slate-700/70 flex flex-col gap-1.5">
                            <button type="button" onclick="triggerCrossSellCar('${cCity}', '${crossSell.checkin_date}', '${crossSell.checkout_date}')"
                                    class="w-full py-2 px-3 rounded-xl bg-amber-500/20 border border-amber-400/50 hover:bg-amber-500 hover:text-slate-950 text-amber-300 font-black text-xs transition cursor-pointer">
                                🚗 ${cCity} Kiralık Araç Fiyatlarını Gör →
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }



    resultsArea.innerHTML = html;
}

// Esnek Tarih Şeridinden veya "Hakiki İpucu" Butonundan Gün Değiştirme
function switchSearchDate(newDepDate) {
    if (!newDepDate) return;
    const depInput = document.getElementById("transDepDate");
    const retInput = document.getElementById("transRetDate");
    if (depInput) {
        const oldDep = depInput.value;
        depInput.value = newDepDate;
        // Eğer gidiş-dönüş seçiliyse dönüş tarihini aynı gün farkıyla kaydır
        if (currentFlightTripType === 'round' && retInput && retInput.value && oldDep) {
            try {
                const d1 = new Date(oldDep);
                const d2 = new Date(retInput.value);
                const diffDays = Math.max(1, Math.round((d2 - d1) / (1000 * 60 * 60 * 24)));
                retInput.value = getNextDaysDate(newDepDate, diffDays);
            } catch (e) {
                retInput.value = getNextDaysDate(newDepDate, 3);
            }
        }
    }
    executeTransportSearch();
}
window.switchSearchDate = switchSearchDate;

// Uçuş Altı Konaklama (Otel / Pansiyon / Ev-Villa) Hızlı Geçiş Köprüsü
function triggerCrossSellStay(city, staySubType, checkinDate, checkoutDate) {
    if (window.switchMainPillar) window.switchMainPillar('stay');
    if (window.switchStaySubTab) window.switchStaySubTab(staySubType || 'hotel');
    const cInput = document.getElementById("hotelCity");
    const cinInput = document.getElementById("hotelCheckin");
    const coutInput = document.getElementById("hotelCheckout");
    if (cInput && city) cInput.value = city;
    if (cinInput && checkinDate) cinInput.value = checkinDate;
    if (coutInput && checkoutDate) coutInput.value = checkoutDate;
    if (typeof executeHotelSearch === 'function') {
        executeHotelSearch();
    }
}
window.triggerCrossSellStay = triggerCrossSellStay;

// Uçuş Altı Araç Kiralama Hızlı Geçiş Köprüsü
function triggerCrossSellCar(city, pickupDate, dropoffDate) {
    if (window.switchMainPillar) window.switchMainPillar('travel');
    if (window.switchUnifiedTab) window.switchUnifiedTab('car');
    const oInput = document.getElementById("transOrigin");
    const dInput = document.getElementById("transDest");
    const depInput = document.getElementById("transDepDate");
    if (oInput && city) oInput.value = city;
    if (dInput && city) dInput.value = city;
    if (depInput && pickupDate) depInput.value = pickupDate;
    executeTransportSearch();
}
window.triggerCrossSellCar = triggerCrossSellCar;

// Bilet Kartlarını Minimalist & Kompakt Formatla Üret (v3 — Ekranda 3-4 Bilet Görünür, ~120px Yükseklik + Açılır Detay Çekmecesi)

// Tüm Havayolu, Otobüs, Tren, Feribot, Araç Kiralama ve Acente Markaları İçin Resmi Logo Çözümleyici
const OFFICIAL_BRAND_DOMAINS = {
    'google': 'google.com',
    'google flights': 'google.com',
    'trip.com': 'trip.com',
    'trip': 'trip.com',
    'kiwi': 'kiwi.com',
    'kiwi.com': 'kiwi.com',
    'skyscanner': 'skyscanner.com.tr',
    'booking': 'booking.com',
    'booking.com': 'booking.com',
    'kayak': 'kayak.com',
    'enuygun': 'enuygun.com',
    'obilet': 'obilet.com',
    'turna': 'turna.com',
    'bilet.com': 'bilet.com',
    'biletdukkani': 'biletdukkani.com',
    'kamil koç': 'kamilkoc.com.tr',
    'kamil koc': 'kamilkoc.com.tr',
    'flixbus': 'flixbus.com.tr',
    'pamukkale': 'pamukkale.com.tr',
    'metro': 'metroturizm.com.tr',
    'varan': 'varan.com.tr',
    'ali osman ulusoy': 'aliosmanulusoy.com.tr',
    'ulusoy': 'ulusoy.com.tr',
    'nilüfer': 'nilufer.com.tr',
    'nilufer': 'nilufer.com.tr',
    'efe tur': 'efetur.com.tr',
    'efetur': 'efetur.com.tr',
    'süha': 'suhaturizm.com.tr',
    'suha': 'suhaturizm.com.tr',
    'kontur': 'kontur.com.tr',
    'özkaymak': 'ozkaymak.com.tr',
    'ozkaymak': 'ozkaymak.com.tr',
    'seç': 'secturizm.com.tr',
    'sec': 'secturizm.com.tr',
    'has turizm': 'hasturizm.com.tr',
    'isparta petrol': 'ispartapetrol.com.tr',
    'buzlu': 'buzlu.com.tr',
    'kale': 'kaleseyahat.com.tr',
    'tcdd': 'tcddtasimacilik.gov.tr',
    'trainline': 'thetrainline.com',
    'eurostar': 'eurostar.com',
    'omio': 'omio.com',
    'ido': 'ido.com.tr',
    'i̇do': 'ido.com.tr',
    'budo': 'burulas.com.tr',
    'gestaş': 'gestasdenizulasim.com.tr',
    'gestas': 'gestasdenizulasim.com.tr',
    'turyol': 'turyol.com',
    'ertürk': 'erturklines.com',
    'erturk': 'erturklines.com',
    'feribotlines': 'feribotlines.com',
    'meander': 'meandertravel.com',
    'msc': 'msccruises.com.tr',
    'costa': 'costacruises.com',
    'yolcu360': 'yolcu360.com',
    'avis': 'avis.com.tr',
    'budget': 'budget.com.tr',
    'garenta': 'garenta.com.tr',
    'enterprise': 'enterprise.com.tr',
    'sixt': 'sixt.com.tr',
    'europcar': 'europcar.com.tr',
    'green motion': 'greenmotion.com',
    'goldcar': 'goldcar.es',
    'hertz': 'hertz.com.tr',
    'rentalcars': 'rentalcars.com'
};

function getBrandLogoHtml(name, fallbackEmoji = '🎫', sizeClass = 'w-4 h-4') {
    if (!name) return `<span>${fallbackEmoji}</span>`;
    const low = String(name).toLowerCase().trim();

    // 1. Önce Havayolu Kontrolü
    let iata = '';
    if (low.includes('pegasus')) iata = 'PC';
    else if (low.includes('ajet') || low.includes('anadolujet')) iata = 'VF';
    else if (low.includes('thy') || low.includes('türk hava') || low.includes('turkish airlines')) iata = 'TK';
    else if (low.includes('sunexpress')) iata = 'XQ';
    else if (low.includes('lufthansa')) iata = 'LH';
    else if (low.includes('swiss')) iata = 'LX';
    else if (low.includes('british')) iata = 'BA';
    else if (low.includes('air france')) iata = 'AF';
    else if (low.includes('klm')) iata = 'KL';
    else if (low.includes('qatar')) iata = 'QR';
    else if (low.includes('emirates')) iata = 'EK';
    else if (low.includes('aegean')) iata = 'A3';
    else if (low.includes('azal') || low.includes('azerbaijan')) iata = 'J2';

    if (iata) {
        return `<img src="https://www.gstatic.com/flights/airline_logos/70px/${iata}.png"
                     alt="${escapeHtml(name)}"
                     loading="lazy"
                     class="${sizeClass} object-contain inline-block shrink-0 rounded-xs"
                     onerror="if(!this.dataset.fb){this.dataset.fb='1';this.src='https://pics.avs.io/72/72/${iata}.png';}else{this.outerHTML='<span>${fallbackEmoji}</span>';}">`;
    }

    // 2. Domain Tabanlı Resmi Marka Logosu Kontrolü
    let domain = '';
    for (const [k, dom] of Object.entries(OFFICIAL_BRAND_DOMAINS)) {
        if (low.includes(k)) {
            domain = dom;
            break;
        }
    }
    if (domain) {
        return `<img src="https://www.google.com/s2/favicons?domain=${domain}&sz=64"
                     alt="${escapeHtml(name)}"
                     loading="lazy"
                     class="${sizeClass} object-contain inline-block shrink-0 rounded-xs"
                     onerror="this.outerHTML='<span>${fallbackEmoji}</span>';">`;
    }

    return `<span>${fallbackEmoji}</span>`;
}
window.getBrandLogoHtml = getBrandLogoHtml;

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
                    flightActionText = isEn ? `Trip.com ↗` : `Trip.com'dan Al ↗`;
                } else if (winnerChannel === 'booking') {
                    flightActionText = isEn ? `Booking.com ↗` : `Booking'den Al ↗`;
                } else if (winnerChannel === 'skyscanner') {
                    flightActionText = isEn ? `Skyscanner ↗` : `Skyscanner'dan Al ↗`;
                } else if (winnerChannel === 'kiwi') {
                    flightActionText = isEn ? `Kiwi.com ↗` : `Kiwi.com'dan Al ↗`;
                } else if (winnerChannel === 'agency') {
                    flightActionText = isEn ? `${winnerLabel} ↗` : `${winnerLabel}'dan Al ↗`;
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
                    flightActionText = isEn ? `Book (${carrierBrand}) ↗` : `${carrierBrand} Al ↗`;
                }
            } else {
                flightActionText = isEn ? 'Live Fares ↗' : 'Seferleri Gör ↗';
            }
        }

        const actionButtonText = isFlight
            ? flightActionText
            : (isEn
                ? 'Select ↗'
                : (ticket.transport_type === 'train'
                    ? `TCDD E-Bilet ↗`
                    : (ticket.transport_type === 'bus'
                        ? `Obilet'ten Al ↗`
                        : `Bileti Al ↗`)));

        // ==================== 1. TREN KARTI (KOMPAKT TEK SATIR + AÇILIR İNDİRİM ÇEKMECESİ) ====================
        if (ticket.transport_type === 'train') {
            const hasReturn = isRoundTrip && ticket.return_leg;
            const retLeg = ticket.return_leg;
            const discounts = ticket.discounts || {};
            const trainNo = ticket.flight_number || 'YHT';
            const badgeText = ticket.badge || 'YHT';
            const isIntlTrain = ticket.id && ticket.id.startsWith('tr-intl');
            const targetUrl = ticket.direct_link || ticket.official_link || 'https://ebilet.tcddtasimacilik.gov.tr/';
            const btnLabel = isIntlTrain ? (isEn ? 'Trainline ↗' : 'Trainline ile Al ↗') : (isEn ? 'TCDD Official ↗' : 'TCDD E-Bilet ↗');

            const hasDiscounts = Boolean(discounts.genc_ogrenci || discounts.yas_65_ustu || discounts.emekli);
            const drawerHtml = hasDiscounts ? `
                <details class="group mt-2 pt-2 border-t border-slate-100 text-[11px]">
                    <summary class="list-none cursor-pointer flex items-center justify-between text-slate-500 hover:text-indigo-700 font-bold select-none">
                        <span class="inline-flex flex-wrap items-center gap-1.5">
                            <i class="fa-solid fa-tags text-indigo-500 text-[10px]"></i>
                            <span>${isEn ? 'Legal Discounts (Student, Retiree, 65+)' : 'Kanuni İndirimler (Genç %15, Emekli %20, 65+ Yaş %50)'}</span>
                            ${discounts.genc_ogrenci ? `<span class="px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 font-black">🎓 ${Number(discounts.genc_ogrenci).toLocaleString('tr-TR')} ${currSym}</span>` : ''}
                            ${discounts.emekli ? `<span class="px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 font-black">🧓 ${Number(discounts.emekli).toLocaleString('tr-TR')} ${currSym}</span>` : ''}
                        </span>
                        <span class="text-[10.5px] font-black text-indigo-600">▾ Tüm İndirimler</span>
                    </summary>
                    <div class="mt-2 pt-2 border-t border-dashed border-slate-200 flex flex-wrap items-center gap-2 text-[11px]">
                        ${discounts.yas_65_ustu ? `<span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200">👴 65+ Yaş: <strong>${Number(discounts.yas_65_ustu).toLocaleString('tr-TR')} ${currSym}</strong></span>` : ''}
                        ${discounts.emekli ? `<span class="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">🧓 Emekli: <strong>${Number(discounts.emekli).toLocaleString('tr-TR')} ${currSym}</strong></span>` : ''}
                        ${discounts.genc_ogrenci ? `<span class="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">🎓 Genç/Öğrenci: <strong>${Number(discounts.genc_ogrenci).toLocaleString('tr-TR')} ${currSym}</strong></span>` : ''}
                        ${discounts.cocuk_7_12 ? `<span class="px-2 py-0.5 rounded-md bg-sky-50 text-sky-800 border border-sky-200">🧒 7-12 Yaş: <strong>${Number(discounts.cocuk_7_12).toLocaleString('tr-TR')} ${currSym}</strong></span>` : ''}
                        ${discounts.ogretmen ? `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">👩‍🏫 Öğretmen: <strong>${Number(discounts.ogretmen).toLocaleString('tr-TR')} ${currSym}</strong></span>` : ''}
                        <span class="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">👶 0-6 Yaş: <strong>Ücretsiz</strong></span>
                    </div>
                </details>
            ` : '';

            return `
                <div class="bg-white border border-slate-200/90 hover:border-indigo-400 rounded-2xl px-4 py-3 shadow-2xs hover:shadow-md transition-all">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <!-- Sol: Taşıyıcı & Rozetler -->
                        <div class="flex items-center gap-2.5 md:w-56 shrink-0">
                            <div class="w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-2xs text-indigo-700 flex items-center justify-center text-base shrink-0 overflow-hidden p-1.5">${getBrandLogoHtml(isIntlTrain ? (ticket.carrier || "Trainline") : "TCDD", "🚆", "w-7 h-7")}</div>
                            <div class="min-w-0">
                                <div class="font-black text-slate-900 text-sm truncate">${escapeHtml(ticket.carrier)}</div>
                                <div class="flex flex-wrap items-center gap-1 mt-0.5">
                                    <span class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700">${escapeHtml(trainNo)}</span>
                                    <span class="px-1.5 py-0.2 rounded text-[10px] font-black bg-amber-100 text-amber-900 truncate max-w-[130px]">${escapeHtml(badgeText)}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Orta: Kalkış ➔ Süre ➔ Varış -->
                        <div class="flex-1 flex items-center justify-between sm:justify-center gap-3 sm:gap-6 px-2">
                            <div class="text-left">
                                <div class="text-xl font-black text-slate-900 leading-none">${ticket.departure_time}</div>
                                <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[130px]">${escapeHtml(ticket.origin)}</div>
                            </div>
                            <div class="flex flex-col items-center justify-center min-w-[90px] sm:min-w-[120px]">
                                <span class="text-[10.5px] font-bold text-slate-500">${ticket.duration || '4 sa 15 dk'}</span>
                                <div class="w-full h-[2px] bg-indigo-200 my-1 relative flex items-center justify-center">
                                    <i class="fa-solid fa-train text-indigo-600 text-[9px] bg-white px-1"></i>
                                </div>
                                <span class="text-[10px] font-bold text-emerald-600">✓ Direkt</span>
                            </div>
                            <div class="text-right">
                                <div class="text-xl font-black text-slate-900 leading-none">${ticket.arrival_time}</div>
                                <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[130px]">${escapeHtml(ticket.destination)}</div>
                            </div>
                        </div>

                        <!-- Sağ: Fiyat + Tek Tık Buton -->
                        <div class="flex items-center justify-between md:justify-end gap-3 md:w-64 shrink-0 border-t md:border-t-0 md:border-l border-slate-100 pt-2.5 md:pt-0 md:pl-4">
                            <div class="text-left md:text-right">
                                <div class="text-xl sm:text-2xl font-black text-slate-950 leading-none">
                                    ${Number(ticket.price).toLocaleString('tr-TR')} <span class="text-sm font-bold">${currSym}</span>
                                </div>
                                <div class="text-[10px] font-semibold text-slate-400 mt-0.5">Resmi Taban Ücret</div>
                            </div>
                            <a href="${targetUrl}" target="_blank" rel="noopener noreferrer"
                               class="px-4 py-2.5 bg-indigo-900 hover:bg-black text-white font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 whitespace-nowrap">
                                <span>${btnLabel}</span>
                            </a>
                        </div>
                    </div>
                    ${hasReturn ? `<div class="mt-2 pt-2 border-t border-slate-100 text-[11px] font-bold text-indigo-800 flex items-center justify-between"><span>🔄 Dönüş: ${retLeg.departure_time} ${escapeHtml(retLeg.origin)} ➔ ${retLeg.arrival_time} ${escapeHtml(retLeg.destination)}</span><span>${retLeg.flight_number || 'YHT'}</span></div>` : ''}
                    ${drawerHtml}
                </div>
            `;
        }

        // ==================== 2. OTOBÜS KARTI (KOMPAKT TEK SATIR ~120px + AÇILIR ACENTE ÇEKMECESİ) ====================
        if (ticket.transport_type === 'bus') {
            const hasReturn = isRoundTrip && ticket.return_leg;
            const retLeg = ticket.return_leg;
            const busType = ticket.flight_number || '2+1 Rahat';
            const badgeText = ticket.badge || '';
            const isKamilOrFlix = Boolean(
                ticket.winner_channel === 'kamilkoc_official' ||
                (ticket.carrier && (ticket.carrier.toLowerCase().includes('kamil') || ticket.carrier.toLowerCase().includes('flix') || ticket.carrier.toLowerCase().includes('alpar')))
            );
            const targetUrl = isKamilOrFlix
                ? (ticket.kamilkoc_link || ticket.direct_link || ticket.official_link || 'https://www.kamilkoc.com.tr/')
                : (ensureObiletPriceSort(ticket.obilet_link) || ticket.direct_link || ticket.official_link || 'https://www.obilet.com/');

            const priceStr = ticket.price ? `${Number(ticket.price).toLocaleString('tr-TR')} ${currSym}` : '';
            const btnLabel = isKamilOrFlix
                ? (isEn ? `Kamil Koç ↗` : `Kamil Koç'tan Al ↗`)
                : (isEn ? `Obilet ↗` : `Obilet'ten Al ↗`);

            const discounts = ticket.discounts || {};
            const hasTimeDiscount = Boolean(discounts.has_time_discount && discounts.original_price && discounts.original_price > ticket.price);
            const rawFeatures = Array.isArray(ticket.features) && ticket.features.length > 0
                ? ticket.features
                : ['Wi-Fi', '220V Priz', 'İkram'];

            return `
                <div class="bg-white border ${isKamilOrFlix ? 'border-emerald-300/90 hover:border-emerald-600' : 'border-slate-200/90 hover:border-emerald-500'} rounded-2xl px-4 py-3 shadow-2xs hover:shadow-md transition-all">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <!-- Sol: Firma + Koltuk Tipi & Kompakt İkonlar -->
                        <div class="flex items-center gap-2.5 md:w-56 shrink-0">
                            <div class="w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-2xs text-emerald-700 flex items-center justify-center text-base shrink-0 overflow-hidden p-1.5">${getBrandLogoHtml(ticket.carrier, "🚌", "w-7 h-7")}</div>
                            <div class="min-w-0">
                                <div class="flex items-center gap-1.5">
                                    <span class="font-black text-slate-900 text-sm truncate">${escapeHtml(ticket.carrier)}</span>
                                </div>
                                <div class="flex flex-wrap items-center gap-1 mt-0.5 text-[10px]">
                                    <span class="px-1.5 py-0.2 rounded font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">💺 ${escapeHtml(busType)}</span>
                                    <span class="text-slate-400 font-bold" title="Wi-Fi, Priz & İkram">📶 🔌 ☕</span>
                                    ${badgeText ? `<span class="px-1.5 py-0.2 rounded font-black bg-amber-100 text-amber-900 truncate max-w-[130px]">${escapeHtml(badgeText)}</span>` : ''}
                                </div>
                            </div>
                        </div>

                        <!-- Orta: Kalkış ➔ Süre ➔ Varış -->
                        <div class="flex-1 flex items-center justify-between sm:justify-center gap-3 sm:gap-6 px-2">
                            <div class="text-left">
                                <div class="text-xl font-black text-slate-900 leading-none">${ticket.departure_time}</div>
                                <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[130px]">${escapeHtml(ticket.origin)}</div>
                            </div>
                            <div class="flex flex-col items-center justify-center min-w-[90px] sm:min-w-[120px]">
                                <span class="text-[10.5px] font-bold text-slate-500">${ticket.duration || '6 sa'}</span>
                                <div class="w-full h-[2px] bg-emerald-200 my-1 relative flex items-center justify-center">
                                    <i class="fa-solid fa-bus text-emerald-600 text-[9px] bg-white px-1"></i>
                                </div>
                                <span class="text-[10px] font-bold text-emerald-600">✓ Direkt</span>
                            </div>
                            <div class="text-right">
                                <div class="text-xl font-black text-slate-900 leading-none">${ticket.arrival_time}</div>
                                <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[130px]">${escapeHtml(ticket.destination)}</div>
                            </div>
                        </div>

                        <!-- Sağ: Fiyat + Tek Tık Buton -->
                        <div class="flex items-center justify-between md:justify-end gap-3 md:w-64 shrink-0 border-t md:border-t-0 md:border-l border-slate-100 pt-2.5 md:pt-0 md:pl-4">
                            <div class="text-left md:text-right">
                                ${hasTimeDiscount ? `<div class="text-[11px] font-bold text-rose-500 line-through leading-none mb-0.5">${Number(discounts.original_price).toLocaleString('tr-TR')} ${currSym}</div>` : ''}
                                <div class="text-xl sm:text-2xl font-black text-slate-950 leading-none">
                                    ${ticket.price ? `${Number(ticket.price).toLocaleString('tr-TR')} <span class="text-sm font-bold">${currSym}</span>` : 'Canlı Fiyat'}
                                </div>
                                <div class="text-[10px] font-semibold text-slate-400 mt-0.5">${isRoundTrip ? 'Gidiş-Dönüş' : 'Tek Yön Net'}</div>
                            </div>
                            <a href="${targetUrl}" target="_blank" rel="noopener noreferrer"
                               class="px-4 py-2.5 ${isKamilOrFlix ? 'bg-amber-500 hover:bg-amber-600 text-slate-950' : 'bg-emerald-800 hover:bg-emerald-950 text-white'} font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 whitespace-nowrap">
                                <span>${btnLabel}</span>
                            </a>
                        </div>
                    </div>

                    ${hasReturn ? `<div class="mt-2 pt-2 border-t border-slate-100 text-[11px] font-bold text-emerald-800 flex items-center justify-between"><span>🔄 Dönüş: ${retLeg.departure_time} ${escapeHtml(retLeg.origin)} ➔ ${retLeg.arrival_time} ${escapeHtml(retLeg.destination)}</span><span>${escapeHtml(retLeg.carrier || ticket.carrier)}</span></div>` : ''}

                    <!-- Açılır/Kapanır Diğer Acenteler & Donanım Çekmecesi -->
                    <details class="group mt-2 pt-1.5 border-t border-slate-100 text-[11px]">
                        <summary class="list-none cursor-pointer flex items-center justify-between text-slate-500 hover:text-slate-800 font-bold select-none">
                            <span class="inline-flex items-center gap-2">
                                <span>▾ ${isEn ? 'Other Agencies & Bus Features (Obilet, Enuygun...)' : 'Diğer Fiyatlar & Donanım (Obilet, Enuygun, Resmi Site)'}</span>
                            </span>
                            <span class="text-[10px] font-semibold text-slate-400">${escapeHtml(ticket.carrier)} • ${ticket.departure_time}</span>
                        </summary>
                        <div class="mt-2 pt-2 border-t border-dashed border-slate-200 flex flex-wrap items-center justify-between gap-2">
                            <div class="flex flex-wrap items-center gap-1.5">
                                ${isKamilOrFlix && ticket.kamilkoc_link ? `<a href="${ticket.kamilkoc_link}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-300 font-black inline-flex items-center gap-1.5">${getBrandLogoHtml('Kamil Koç', '🚌', 'w-4 h-4')}<span>Kamil Koç Resmi (${priceStr}) ↗</span></a>` : ''}
                                ${ticket.obilet_link ? `<a href="${ensureObiletPriceSort(ticket.obilet_link)}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-950 border border-rose-200 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml('Obilet', '🎟️', 'w-4 h-4')}<span>Obilet (${!isKamilOrFlix && priceStr ? priceStr : 'Koltuk Seç'}) ↗</span></a>` : ''}
                                ${ticket.enuygun_link ? `<a href="${ticket.enuygun_link}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-950 border border-emerald-200 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml('Enuygun', '💚', 'w-4 h-4')}<span>Enuygun Teklifleri ↗</span></a>` : ''}
                                ${!isKamilOrFlix && ticket.carrier_official_link ? `<a href="${ticket.carrier_official_link}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml(ticket.carrier, '🚌', 'w-4 h-4')}<span>${escapeHtml(ticket.carrier)} Resmi Site ↗</span></a>` : ''}
                            </div>
                            <div class="flex flex-wrap items-center gap-1 text-[10.5px] text-slate-600">
                                ${rawFeatures.slice(0, 4).map(f => `<span class="px-2 py-0.5 rounded bg-slate-100">✓ ${escapeHtml(String(f))}</span>`).join('')}
                            </div>
                        </div>
                    </details>
                </div>
            `;
        }

        // ==================== 3. FERİBOT & CRUISE KARTI (ÇOKLU DENİZ ACENTESİ & OPERASYONEL KALKANLI) ====================
        if (ticket.transport_type === 'ferry' || ticket.is_cruise) {
            const hasReturn = isRoundTrip && ticket.return_leg;
            const retLeg = ticket.return_leg;
            const isCruise = ticket.is_cruise || ticket.category === 'cruise';
            const isGreekIsland = ticket.is_greek_island || ticket.category === 'greek_islands';
            const hasVerifiedPrice = ticket.price !== null && ticket.price !== undefined && Number(ticket.price) > 0;
            const targetUrl = ticket.winner_url || ticket.direct_link || ticket.official_link || 'https://www.obilet.com/feribot-bileti';
            const btnLabel = (isEn ? ticket.winner_button_text_en : ticket.winner_button_text) || (hasVerifiedPrice ? `${ticket.winner_name || 'Obilet Feribot'}'tan Al ↗` : 'Canlı Fiyatı Gör ↗');
            const providers = Array.isArray(ticket.providers) ? ticket.providers : [];
            const cabinTiers = Array.isArray(ticket.cabin_tiers) ? ticket.cabin_tiers : [];
            const cardDomId = escapeHtml(ticket.id || `ferry-${Math.random().toString(36).slice(2, 7)}`);
            const breakdownText = ticket.price_breakdown_text || `${totalPaxText} • Doğrulanmış Canlı Fiyat`;

            const shieldItems = [];
            if (ticket.green_card_notice) shieldItems.push({ text: ticket.green_card_notice, cls: 'text-amber-950 bg-amber-50 border-amber-300 font-bold' });
            if (ticket.vehicle_pricing_note) shieldItems.push({ text: ticket.vehicle_pricing_note, cls: 'text-emerald-900 bg-emerald-50 border-emerald-200' });
            if (ticket.passport_notice) shieldItems.push({ text: ticket.passport_notice, cls: 'text-sky-900 bg-sky-50 border-sky-200' });
            if (ticket.seasonality_note) shieldItems.push({ text: ticket.seasonality_note, cls: 'text-amber-900 bg-amber-50 border-amber-200' });
            if (ticket.weather_assurance) shieldItems.push({ text: ticket.weather_assurance, cls: 'text-slate-700 bg-slate-50 border-slate-200' });

            return `
                <div id="card-${cardDomId}" class="bg-white border-2 border-slate-200/90 hover:border-sky-500 rounded-2xl px-4 py-3.5 shadow-2xs hover:shadow-md transition-all">
                    <!-- 1. Ana Sefer ve En Ucuz Kanal Satırı -->
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div class="flex items-center gap-2.5 md:w-64 shrink-0">
                            <div class="w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-2xs text-sky-700 flex items-center justify-center text-lg shrink-0 overflow-hidden p-1.5">${getBrandLogoHtml(ticket.carrier, isCruise ? "🛳️" : "⛴️", "w-7 h-7")}</div>
                            <div class="min-w-0">
                                <div class="font-black text-slate-900 text-sm truncate" title="${escapeHtml(ticket.carrier)}">${escapeHtml(ticket.carrier)}</div>
                                <div class="text-[10.5px] font-semibold text-slate-500 truncate">${escapeHtml(ticket.vessel_type || 'Tarifeli Deniz Hattı')}</div>
                                <div class="flex flex-wrap items-center gap-1 mt-1 text-[10px]">
                                    <span class="px-1.5 py-0.2 rounded font-black bg-amber-100 text-amber-900">${escapeHtml(ticket.badge || 'Tarifeli')}</span>
                                    ${isGreekIsland && !(ticket.badge || '').includes('Vize') ? `<span class="px-1.5 py-0.2 rounded font-bold bg-sky-100 text-sky-800">🇬🇷 Kapıda Vize</span>` : ''}
                                    ${ticket.requires_chip_id && !(ticket.badge || '').includes('Kimlik') ? `<span class="px-1.5 py-0.2 rounded font-bold bg-indigo-100 text-indigo-800">🪪 Çipli Kimlik</span>` : ''}
                                    ${isCruise
                                        ? `<span class="px-1.5 py-0.2 rounded font-bold bg-purple-100 text-purple-900">🍽️ Tam Pansiyon</span>`
                                        : (ticket.vehicle_allowed
                                            ? `<span class="px-1.5 py-0.2 rounded font-bold bg-emerald-100 text-emerald-800">🚗 Arabalı & Yaya</span>`
                                            : `<span class="px-1.5 py-0.2 rounded font-bold bg-slate-100 text-slate-700">🚶 Sadece Yaya (Katamaran)</span>`)}
                                </div>
                            </div>
                        </div>

                        <div class="flex-1 flex items-center justify-between sm:justify-center gap-3 sm:gap-6 px-2">
                            <div class="text-left">
                                <div class="text-xl font-black text-slate-900 leading-none">${ticket.departure_time}</div>
                                <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[135px]" title="${escapeHtml(ticket.origin)}">${escapeHtml(ticket.origin)}</div>
                            </div>
                            <div class="flex flex-col items-center justify-center min-w-[95px] sm:min-w-[125px]">
                                <span class="text-[10.5px] font-bold text-slate-500">${ticket.duration || '1 sa 30 dk'}</span>
                                <div class="w-full h-[2px] bg-sky-200 my-1 relative flex items-center justify-center">
                                    <i class="fa-solid fa-ship text-sky-600 text-[9px] bg-white px-1"></i>
                                </div>
                                <span class="text-[10px] font-bold text-emerald-600">${isCruise ? '✓ Kruvaziyer Rotası' : '✓ Direkt Deniz Hattı'}</span>
                            </div>
                            <div class="text-right">
                                <div class="text-xl font-black text-slate-900 leading-none">${ticket.arrival_time}</div>
                                <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[145px]" title="${escapeHtml(ticket.destination)}">${escapeHtml(ticket.destination)}</div>
                            </div>
                        </div>

                        <div class="flex items-center justify-between md:justify-end gap-3 md:w-80 shrink-0 border-t md:border-t-0 md:border-l border-slate-100 pt-2.5 md:pt-0 md:pl-4">
                            <div class="text-left md:text-right">
                                ${hasVerifiedPrice ? `
                                    <div class="inline-flex items-center gap-1 text-[10px] font-black text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded mb-0.5">
                                        <i class="fa-solid fa-circle-check text-[9px]"></i>
                                        <span>Canlı En Ucuz (${escapeHtml(ticket.winner_name || 'Acente')})</span>
                                    </div>
                                    <div class="text-xl sm:text-2xl font-black text-slate-950 leading-none">
                                        <span id="ferryPriceVal-${cardDomId}">${Number(ticket.price).toLocaleString('tr-TR')}</span> <span class="text-sm font-bold">${currSym}</span>
                                    </div>
                                    <div id="ferryBreakdown-${cardDomId}" class="text-[10px] font-bold text-sky-800 mt-0.5">${escapeHtml(breakdownText)}</div>
                                ` : `
                                    <div class="inline-flex items-center gap-1 text-[10px] font-black text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded mb-0.5">
                                        <i class="fa-solid fa-bolt text-[9px]"></i>
                                        <span>Canlı Sefer Sorgulama</span>
                                    </div>
                                    <div class="text-sm sm:text-base font-black text-slate-900 leading-tight">
                                        Güncel Gişe Fiyatı
                                    </div>
                                    <div class="text-[10px] font-semibold text-slate-400 mt-0.5">Seçili Tarih İçin Tıklayın</div>
                                `}
                            </div>
                            <a href="${targetUrl}" target="_blank" rel="noopener noreferrer"
                               class="px-4 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-black text-xs rounded-xl shadow-sm hover:shadow transition flex items-center gap-1.5 whitespace-nowrap">
                                <span>${escapeHtml(btnLabel)}</span>
                            </a>
                        </div>
                    </div>

                    ${hasReturn ? `<div class="mt-2 pt-2 border-t border-slate-100 text-[11px] font-bold text-sky-800 flex items-center justify-between"><span>🔄 Dönüş Seferi: ${retLeg.departure_time} ${escapeHtml(retLeg.origin)} ➔ ${retLeg.arrival_time} ${escapeHtml(retLeg.destination)}</span></div>` : ''}

                    <!-- 1.5. CRUISE KABİN TİPİ SEÇİCİ ŞERİDİ (Sadece Cruise Turlarında Görünür) -->
                    ${isCruise && cabinTiers.length > 0 ? `
                        <div class="mt-2.5 pt-2.5 border-t border-sky-100 bg-sky-50/60 rounded-xl px-3 py-2 flex flex-wrap items-center justify-between gap-2">
                            <span class="text-[11px] font-black text-sky-950 flex items-center gap-1.5">
                                <i class="fa-solid fa-bed text-sky-700"></i> Kabin Tipi Seçin (${totalPaxText}):
                            </span>
                            <div class="flex flex-wrap items-center gap-1.5">
                                ${cabinTiers.map((ct, cIdx) => `
                                    <button type="button"
                                            onclick="selectCruiseCabin('${cardDomId}', ${cIdx})"
                                            id="cabinBtn-${cardDomId}-${cIdx}"
                                            class="px-2.5 py-1 rounded-lg text-[11px] transition cursor-pointer inline-flex items-center gap-1.5 ${cIdx === 0
                                                ? 'bg-sky-900 text-white font-black shadow-2xs border border-sky-900'
                                                : 'bg-white hover:bg-sky-100 text-slate-700 font-bold border border-sky-200'}">
                                        <span>${escapeHtml(ct.name)}:</span>
                                        <span class="${cIdx === 0 ? 'text-amber-300 font-black' : 'text-sky-900 font-black'}">${Number(ct.price).toLocaleString('tr-TR')} ${ct.currency || currSym}</span>
                                        <span class="text-[9.5px] opacity-80">(${ct.per_person_eur}€/kişi)</span>
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- 2. Kritik Vize / Yeşil Sigorta / Katamaran Araç Uyarı Bantları -->
                    ${ticket.visa_urgent_warning ? `
                        <div class="mt-2.5 px-3 py-2 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-[11px] font-bold flex items-start gap-2">
                            <i class="fa-solid fa-triangle-exclamation text-rose-600 mt-0.5 shrink-0"></i>
                            <span>${escapeHtml(ticket.visa_urgent_warning)}</span>
                        </div>
                    ` : ''}
                    ${ticket.green_card_notice ? `
                        <div class="mt-2 px-3 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 text-[11px] font-bold flex items-start gap-2">
                            <i class="fa-solid fa-id-card-clip text-amber-600 mt-0.5 shrink-0"></i>
                            <span>${escapeHtml(ticket.green_card_notice)}</span>
                        </div>
                    ` : ''}
                    ${ticket.vehicle_warning ? `
                        <div class="mt-2 px-3 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 text-[11px] font-bold flex items-start gap-2">
                            <i class="fa-solid fa-car-burst text-amber-600 mt-0.5 shrink-0"></i>
                            <span>${escapeHtml(ticket.vehicle_warning)}</span>
                        </div>
                    ` : ''}

                    <!-- 3. Açık Tek Satır Deniz Acenteleri & Resmi Gişe Karşılaştırma Şeridi -->
                    ${providers.length > 0 ? `
                        <div class="mt-2.5 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                            <div class="flex flex-wrap items-center gap-1.5">
                                <span class="text-[10.5px] font-black text-slate-500 mr-1 flex items-center gap-1">
                                    <i class="fa-solid fa-scale-balanced text-sky-600"></i> Satış Kanalları:
                                </span>
                                ${providers.map((p, pIdx) => {
                                    const pHasPrice = p.price !== null && p.price !== undefined && Number(p.price) > 0;
                                    const pPriceTxt = pHasPrice ? `${Number(p.price).toLocaleString('tr-TR')} ${p.currency || currSym}` : (p.badge === 'Araç İçin Çağrı Merkezi' ? 'Çağrı M. (0850 885 00 97)' : 'Canlı Sorgula ↗');
                                    const isWin = Boolean(p.is_best || p.is_winner);
                                    return `
                                        <a href="${p.url}" target="_blank" rel="noopener noreferrer"
                                           class="px-2.5 py-1 rounded-lg text-[11px] transition inline-flex items-center gap-1.5 ${isWin
                                               ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-950 border border-emerald-400 font-black shadow-2xs'
                                               : 'bg-slate-50 hover:bg-slate-900 hover:text-white text-slate-700 border border-slate-200 font-bold'}">
                                            ${isWin ? `<span class="text-emerald-600 text-[10px]">★</span>` : ''}
                                            <span>${escapeHtml(p.name)}:</span>
                                            <span id="provPrice-${cardDomId}-${pIdx}" class="${isWin ? 'text-emerald-700 font-black' : (pHasPrice ? 'text-amber-700 font-black' : 'text-sky-700 font-semibold')}">${pPriceTxt}</span>
                                        </a>
                                    `;
                                }).join('')}
                            </div>

                            ${shieldItems.length > 0 ? `
                                <details class="text-[11px] group">
                                    <summary class="cursor-pointer font-bold text-sky-800 hover:text-sky-950 list-none inline-flex items-center gap-1 select-none">
                                        <i class="fa-solid fa-circle-info text-sky-600"></i>
                                        <span>Deniz & Vize Kuralları</span>
                                        <i class="fa-solid fa-chevron-down text-[9px] group-open:rotate-180 transition-transform"></i>
                                    </summary>
                                    <div class="mt-2 p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 text-[11px] font-medium text-slate-700 max-w-2xl">
                                        ${shieldItems.map(si => `
                                            <div class="px-2.5 py-1.5 rounded-lg border ${si.cls}">
                                                <span>${escapeHtml(si.text)}</span>
                                            </div>
                                        `).join('')}
                                    </div>
                                </details>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        if (!isFlight) {
            return `
                <div class="bg-white border border-slate-200 hover:border-amber-400 rounded-2xl px-4 py-3 shadow-2xs flex items-center justify-between gap-4">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-amber-50 text-amber-700 border border-amber-200 flex items-center justify-center text-lg">🚗</div>
                        <div>
                            <div class="font-black text-slate-900 text-sm">${escapeHtml(ticket.carrier)}</div>
                            <div class="text-xs text-slate-500">${ticket.departure_time || '09:00'} • ${escapeHtml(ticket.origin)} ➔ ${escapeHtml(ticket.destination)}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="text-xl font-black text-slate-950">${ticket.price ? `${Number(ticket.price).toLocaleString('tr-TR')} ${currSym}` : 'Canlı'}</div>
                        <a href="${directLink}" target="_blank" rel="noopener noreferrer" class="px-4 py-2 bg-slate-900 text-white font-black text-xs rounded-xl">${actionButtonText}</a>
                    </div>
                </div>
            `;
        }

        // ==================== 4. UÇUŞ KARTI (KOMPAKT TEK SATIR ~120px + AÇILIR ACENTE ÇEKMECESİ) ====================
        let fromCode = ticket.from_code || '';
        let fromCity = ticket.origin || searchReq.origin;
        const matchFrom = (ticket.origin || '').match(/(.*?)\s*\((.*?)\)/);
        if (matchFrom) { fromCity = matchFrom[1].trim(); fromCode = matchFrom[2].trim(); }

        let toCode = ticket.to_code || '';
        let toCity = ticket.destination || searchReq.destination;
        const matchTo = (ticket.destination || '').match(/(.*?)\s*\((.*?)\)/);
        if (matchTo) { toCity = matchTo[1].trim(); toCode = matchTo[2].trim(); }

        const carrierUpper = (ticket.carrier || '').toUpperCase();
        const bagLabel = (carrierUpper.includes('THY') || carrierUpper.includes('TÜRK') || carrierUpper.includes('AJET'))
            ? '🧳 15 kg Bagaj + Kabin'
            : '🎒 Kabin Çantası';

        let airlineIata = (ticket.carrier_code || '').trim().toUpperCase();
        if (!airlineIata && ticket.flight_number) {
            const fnMatch = String(ticket.flight_number).trim().match(/^([A-Z0-9]{2})\s*\d+/i);
            if (fnMatch) airlineIata = fnMatch[1].toUpperCase();
        }
        if (!airlineIata) {
            if (carrierUpper.includes('PEGASUS')) airlineIata = 'PC';
            else if (carrierUpper.includes('SUNEXPRESS')) airlineIata = 'XQ';
            else if (carrierUpper.includes('AJET') || carrierUpper.includes('ANADOLU')) airlineIata = 'VF';
            else if (carrierUpper.includes('THY') || carrierUpper.includes('TÜRK HAVA') || carrierUpper.includes('TURKISH')) airlineIata = 'TK';
            else if (carrierUpper.includes('LUFTHANSA')) airlineIata = 'LH';
            else if (carrierUpper.includes('SWISS')) airlineIata = 'LX';
            else if (carrierUpper.includes('AEGEAN')) airlineIata = 'A3';
            else if (carrierUpper.includes('BRITISH')) airlineIata = 'BA';
            else if (carrierUpper.includes('AIR FRANCE')) airlineIata = 'AF';
            else if (carrierUpper.includes('KLM')) airlineIata = 'KL';
            else if (carrierUpper.includes('QATAR')) airlineIata = 'QR';
            else if (carrierUpper.includes('EMIRATES')) airlineIata = 'EK';
            else if (carrierUpper.includes('AZAL') || carrierUpper.includes('AZERBAIJAN')) airlineIata = 'J2';
        }
        const airlineLogoHtml = airlineIata
            ? `<img src="https://www.gstatic.com/flights/airline_logos/70px/${escapeHtml(airlineIata)}.png"
                    alt="${escapeHtml(ticket.carrier)}"
                    loading="lazy"
                    class="w-7 h-7 object-contain"
                    onerror="if(!this.dataset.fb){this.dataset.fb='1';this.src='https://pics.avs.io/72/72/${escapeHtml(airlineIata)}.png';}else{this.style.display='none';this.parentElement.innerHTML='✈️';}">`
            : '✈️';

        const verifiedProviders = (ticket.providers || []).filter(p => p.price !== null && p.price !== undefined && Number(p.price) > 0);
        const hasTripPrice = verifiedProviders.some(p => p.channel === 'trip' || String(p.name || '').toLowerCase().includes('trip'));
        const hasBookingPrice = verifiedProviders.some(p => p.channel === 'booking' || String(p.name || '').toLowerCase().includes('booking') || String(p.name || '').toLowerCase().includes('kayak'));
        const tripFallbackLink = ticket.trip_link || ticket.travelpayouts_link || '';
        const bookingFallbackLink = ticket.kayak_link || '';
        const hasDrawer = verifiedProviders.length > 0 || tripFallbackLink || bookingFallbackLink || ticket.enuygun_link || ticket.obilet_link;

        return `
            <div class="bg-white border border-slate-200/90 hover:border-amber-400 rounded-2xl px-4 py-3 shadow-2xs hover:shadow-md transition-all">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <!-- Sol: Havayolu Logosu & Bagaj Özeti -->
                    <div class="flex items-center gap-2.5 md:w-56 shrink-0">
                        <div class="w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-2xs text-amber-600 flex items-center justify-center text-base shrink-0 overflow-hidden p-1">${airlineLogoHtml}</div>
                        <div class="min-w-0">
                            <div class="flex items-center gap-1.5">
                                <span class="font-black text-slate-900 text-sm truncate">${escapeHtml(ticket.carrier)}</span>
                                <span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 text-[10px] font-mono font-bold">${escapeHtml(ticket.flight_number || '')}</span>
                            </div>
                            <div class="flex flex-wrap items-center gap-1 mt-0.5 text-[10px]">
                                <span class="text-slate-500 font-bold">${bagLabel}</span>
                                ${ticket.badge ? `<span class="px-1.5 py-0.2 rounded font-black bg-amber-100 text-amber-900 truncate max-w-[120px]">${escapeHtml(ticket.badge)}</span>` : ''}
                            </div>
                        </div>
                    </div>

                    <!-- Orta: Kalkış ➔ Süre ➔ Varış -->
                    <div class="flex-1 flex items-center justify-between sm:justify-center gap-3 sm:gap-6 px-2">
                        <div class="text-left">
                            <div class="text-xl font-black text-slate-900 leading-none">${ticket.departure_time || '08:45'}</div>
                            <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[130px]"><span class="text-amber-600 font-black">${escapeHtml(fromCode)}</span> ${escapeHtml(fromCity)}</div>
                        </div>
                        <div class="flex flex-col items-center justify-center min-w-[90px] sm:min-w-[120px]">
                            <span class="text-[10.5px] font-bold text-slate-500">${ticket.duration || '1 sa 15 dk'}</span>
                            <div class="w-full h-[2px] bg-slate-300 my-1 relative flex items-center justify-center">
                                <i class="fa-solid fa-plane text-amber-500 text-[9px] bg-white px-1"></i>
                            </div>
                            <span class="text-[10px] font-bold ${ticket.is_direct !== false ? 'text-emerald-600' : 'text-amber-600'}">${ticket.is_direct !== false ? '✓ Direkt' : '1 Aktarma'}</span>
                        </div>
                        <div class="text-right">
                            <div class="text-xl font-black text-slate-900 leading-none">${ticket.arrival_time || '10:00'}</div>
                            <div class="text-[11px] font-bold text-slate-600 mt-1 truncate max-w-[130px]"><span class="text-amber-600 font-black">${escapeHtml(toCode)}</span> ${escapeHtml(toCity)}</div>
                        </div>
                    </div>

                    <!-- Sağ: Fiyat + Tek Tık Buton -->
                    <div class="flex items-center justify-between md:justify-end gap-3 md:w-64 shrink-0 border-t md:border-t-0 md:border-l border-slate-100 pt-2.5 md:pt-0 md:pl-4">
                        <div class="text-left md:text-right">
                            <div class="text-xl sm:text-2xl font-black text-slate-950 leading-none">
                                ${ticket.price ? `${Number(ticket.price).toLocaleString(isEn ? 'en-US' : 'tr-TR')} <span class="text-sm font-bold">${currSym}</span>` : 'Canlı Fiyat'}
                            </div>
                            <div class="text-[10px] font-semibold text-slate-400 mt-0.5">${totalPaxText} • ${isRoundTrip ? 'Gidiş-Dönüş' : 'Tek Yön'}</div>
                        </div>
                        <a href="${flightTargetUrl}" target="_blank" rel="noopener noreferrer"
                           class="px-4 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 whitespace-nowrap">
                            <span>${actionButtonText}</span>
                        </a>
                    </div>
                </div>

                ${isRoundTrip && ticket.return_leg ? `<div class="mt-2 pt-2 border-t border-slate-100 text-[11px] font-bold text-blue-800 flex items-center justify-between"><span>🛬 Dönüş: ${ticket.return_leg.departure_time} (${escapeHtml(ticket.return_leg.from_code || toCode)}) ➔ ${ticket.return_leg.arrival_time} (${escapeHtml(ticket.return_leg.to_code || fromCode)})</span><span>${escapeHtml(ticket.return_leg.flight_number || 'Dönüş')}</span></div>` : ''}

                ${hasDrawer ? `
                    <div class="mt-2 pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-[11px]">
                        <span class="text-[10.5px] font-black text-slate-500 mr-0.5 select-none">
                            ${isEn ? 'All Fares:' : 'Diğer Fiyatlar:'}
                        </span>
                        ${verifiedProviders.map(p => `
                            <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-0.5 rounded-lg ${p.is_best ? 'bg-amber-50 border-amber-300 text-amber-950 font-black' : 'bg-slate-50 border-slate-200 text-slate-700 font-bold'} border hover:bg-slate-100 transition inline-flex items-center gap-1.5">
                                ${getBrandLogoHtml(p.name, '🌐', 'w-3.5 h-3.5')}
                                <span>${escapeHtml(p.name)}</span>
                                <span class="font-black">${Number(p.price).toLocaleString('tr-TR')} ${currSym}</span>
                                <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] opacity-60"></i>
                            </a>
                        `).join('')}
                        ${!hasTripPrice && tripFallbackLink ? `<a href="${tripFallbackLink}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-0.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-950 border border-blue-200 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml('Trip.com', '🌐', 'w-3.5 h-3.5')}<span>Trip.com Teklifleri ↗</span></a>` : ''}
                        ${!hasBookingPrice && bookingFallbackLink ? `<a href="${bookingFallbackLink}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-0.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-200 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml('Booking / Kayak', '🌐', 'w-3.5 h-3.5')}<span>Booking / Kayak ↗</span></a>` : ''}
                        ${ticket.airline_direct_url ? `<a href="${ticket.airline_direct_url}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-0.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-950 border border-indigo-200 font-bold inline-flex items-center gap-1.5">${airlineIata ? `<img src="https://www.gstatic.com/flights/airline_logos/70px/${escapeHtml(airlineIata)}.png" alt="" class="w-4 h-4 object-contain inline-block shrink-0" onerror="if(!this.dataset.fb){this.dataset.fb='1';this.src='https://pics.avs.io/72/72/${escapeHtml(airlineIata)}.png';}else{this.style.display='none';}">` : getBrandLogoHtml(ticket.carrier, '✈️', 'w-4 h-4')}<span>${escapeHtml((isEn ? (ticket.airline_label_en || "Airline Site ↗") : (ticket.airline_label_tr || "Havayolunda Gör ↗")).replace(/^✈️\s*/, ''))}</span></a>` : ''}
                        ${ticket.enuygun_link ? `<a href="${ticket.enuygun_link}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-0.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-950 border border-emerald-200 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml('Enuygun', '💚', 'w-3.5 h-3.5')}<span>Enuygun Teklifleri ↗</span></a>` : ''}
                        ${ticket.obilet_link ? `<a href="${ensureObiletPriceSort(ticket.obilet_link)}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-0.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-950 border border-rose-200 font-bold inline-flex items-center gap-1.5">${getBrandLogoHtml('Obilet', '🎟️', 'w-3.5 h-3.5')}<span>Obilet Teklifleri ↗</span></a>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }

).join("");
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
        // Otobüs sekmesinde akıllı kürasyon sırasını (Vitrin Kamil Koç + En Ucuz Fırsat + Bölge Kahramanı & Ana Koridor) koru
        list.sort((a, b) => {
            if (currentTransportSubTab === 'bus' || (a.transport_type === 'bus' && b.transport_type === 'bus')) {
                const aRank = Number(a.smart_sort_rank) || 9999;
                const bRank = Number(b.smart_sort_rank) || 9999;
                if (aRank !== bRank) return aRank - bRank;
            }
            const ap = (a.price !== null && a.price !== undefined && Number(a.price) > 0) ? Number(a.price) : 999999999;
            const bp = (b.price !== null && b.price !== undefined && Number(b.price) > 0) ? Number(b.price) : 999999999;
            const pDiff = ap - bp;
            if (Math.abs(pDiff) > 0.01) return pDiff;
            const sDiff = (Number(b.carrier_score) || 0) - (Number(a.carrier_score) || 0);
            if (sDiff !== 0) return sDiff;
            return parseMins(a.departure_time) - parseMins(b.departure_time);
        });
    } else if (window.currentFlightSort === 'fastest') {
        list.sort((a, b) => {
            const dDiff = getDurMins(a.duration) - getDurMins(b.duration);
            if (dDiff !== 0) return dDiff;
            const sDiff = (Number(b.carrier_score) || 0) - (Number(a.carrier_score) || 0);
            if (sDiff !== 0) return sDiff;
            return (Number(a.price) || 0) - (Number(b.price) || 0);
        });
    } else if (window.currentFlightSort === 'earliest') {
        // En Erken Kalkış: 00:00'dan 23:59'a doğru artan sıra (aynı dakikada Bölge Kahramanı / Ulusal Marka üstte)
        list.sort((a, b) => {
            const tDiff = parseMins(a.departure_time) - parseMins(b.departure_time);
            if (tDiff !== 0) return tDiff;
            const sDiff = (Number(b.carrier_score) || 0) - (Number(a.carrier_score) || 0);
            if (sDiff !== 0) return sDiff;
            return (Number(a.price) || 0) - (Number(b.price) || 0);
        });
    } else if (window.currentFlightSort === 'latest') {
        // En Geç Kalkış: 23:59'dan 00:00'a doğru azalan sıra (aynı dakikada Bölge Kahramanı / Ulusal Marka üstte)
        list.sort((a, b) => {
            const tDiff = parseMins(b.departure_time) - parseMins(a.departure_time);
            if (tDiff !== 0) return tDiff;
            const sDiff = (Number(b.carrier_score) || 0) - (Number(a.carrier_score) || 0);
            if (sDiff !== 0) return sDiff;
            return (Number(a.price) || 0) - (Number(b.price) || 0);
        });
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
        const unitLabel = currentTransportSubTab === 'flight' ? 'uçuş' : 'sefer';
        countBadge.textContent = `(${list.length} ${unitLabel})`;
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

    const safeCity = escapeHtml(city);
    const resultsArea = document.getElementById("hotelResultsArea");
    resultsArea.innerHTML = `
        <div class="p-12 text-center bg-gradient-to-b from-amber-50/50 to-white rounded-3xl border border-amber-200/60 shadow-xs">
            <div class="inline-block w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <div class="text-lg font-black text-slate-800">${safeCity} Otelleri ve Ulaşım Seçenekleri Canlı Taranıyor...</div>
            <div class="text-xs text-slate-500 mt-1.5 font-medium">Uçak, tren, otobüs ve feribot alternatifleri ile canlı otel odaları sorgulanıyor.</div>
        </div>
    `;
    resultsArea.classList.remove("hidden");
    resultsArea.scrollIntoView({ behavior: "smooth", block: "nearest" });

    try {
        if (window._activeHotelAbort) {
            try { window._activeHotelAbort.abort(); } catch (_) {}
        }
        const abortCtrl = new AbortController();
        window._activeHotelAbort = abortCtrl;

        const dynamicOrigin = (window.HakikiTravelContext && window.HakikiTravelContext.origin_name)
            || (document.getElementById("transOrigin") && document.getElementById("transOrigin").value.trim())
            || "İstanbul";

        const payload = {
            origin: dynamicOrigin,
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
            body: JSON.stringify(payload),
            signal: abortCtrl.signal
        });

        const data = await res.json();
        renderHotelResults(data.hotel_info, city, cin, cout, guests, data);
    } catch (err) {
        if (err && err.name === "AbortError") return;
        resultsArea.innerHTML = `
            <div class="p-8 text-center bg-rose-50 border border-rose-200 rounded-3xl text-rose-800">
                <i class="fa-solid fa-circle-exclamation text-2xl mb-2 text-rose-500"></i>
                <div class="font-bold">Otel araması sırasında bir hata oluştu.</div>
                <div class="text-xs mt-1 text-rose-600">${escapeHtml(err.message)}</div>
            </div>
        `;
    }


}

// OTEL ARAMA SONUÇLARI: MULTI-MODAL ULAŞIM BANDI + KOMBİNE SEPET + CANLI OTELLER
function renderHotelResults(hotelInfo, city, cin, cout, guests, data) {
    const resultsArea = document.getElementById("hotelResultsArea");
    const safeCity = escapeHtml(city);
    const safeCityJs = String(city || "").replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    const activeOrigName = (data && data.origin) || (window.HakikiTravelContext && window.HakikiTravelContext.origin_name) || 'İstanbul';
    const safeOrigJs = String(activeOrigName).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    if (!hotelInfo) {
        resultsArea.innerHTML = `
            <div class="bg-white p-10 rounded-3xl border border-slate-200 text-center shadow-xs">
                <div class="font-black text-lg text-slate-800">${safeCity} için resmi arama linki hazırlandı.</div>
                <div class="mt-4">
                    <a href="https://www.booking.com/searchresults.tr.html?ss=${encodeURIComponent(city)}&checkin=${encodeURIComponent(cin)}&checkout=${encodeURIComponent(cout)}&aid=585474" target="_blank" class="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-black rounded-xl inline-flex items-center gap-2 shadow-md">
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
                        <span class="text-xs text-slate-400 font-bold">${safeCity} Seyahatiniz İçin Ulaşım Seçenekleri</span>
                    </div>
                    <h4 class="text-base sm:text-lg font-black text-white">${safeCity} Şehrine Nasıl Gidilir? (Doğrulanmış Taban Fiyatlar)</h4>
                </div>
                <button onclick="prefillTransportAndSwitch('${safeOrigJs}', '${safeCityJs}', '${escapeHtml(cin)}', '${escapeHtml(cout)}')" class="px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-amber-300 font-bold text-xs rounded-xl transition flex items-center gap-1.5 shrink-0">
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
                        <span class="text-xs text-slate-500 font-bold">${safeCity} Seyahati (${hotelInfo.nights || 2} Gece • ${escapeHtml(guests)} Kişi)</span>
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
                            ${safeCity} genelindeki tüm müsait otel, pansiyon ve butik konaklama seçeneklerini tarihleriniz ve ${escapeHtml(guests)} misafir için önceden doldurulmuş ekranda inceleyin.
                        </p>
                    </div>
                    <div class="mt-4 pt-3 border-t border-slate-100">
                        ${hotelInfo.is_international ? `
                            <a href="${hotelInfo.booking_url || bookingCityLink}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl shadow-md transition flex items-center justify-center gap-2">
                                <span>🏨 Tüm ${safeCity} Otellerini Listele (Booking.com)</span>
                                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                            </a>
                        ` : `
                            <a href="${hotelInfo.agoda_url || hotelInfo.enuygun_url || bookingCityLink}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow-md transition flex items-center justify-center gap-2">
                                <span>🏨 Tüm ${safeCity} Otellerini Listele (Agoda / Enuygun)</span>
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
                    <div class="flex items-center gap-2 mb-1">
                        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-900">
                            🏨 Resmi Partner Karşılaştırma Ağı
                        </span>
                        <span class="text-xs text-slate-400 font-bold">Sıfır Komisyon & Aracısız Fiyatlar</span>
                    </div>
                    <h3 class="font-black text-xl text-slate-900">${hotelInfo.destination} Otel & Konaklama Seçenekleri</h3>
                    <div class="text-xs text-slate-500 mt-1 font-medium">${cin} — ${cout} (${hotelInfo.nights} Gece) • ${guests} Misafir • Canlı Karşılaştırma Ağı</div>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <a href="${hotelInfo.trip_hotel_url || (hotelInfo.deep_links && hotelInfo.deep_links.trip) || `https://tr.trip.com/hotels/list?keyword=${encodeURIComponent(city)}&checkin=${cin}&checkout=${cout}&crn=1&adult=${guests}&Allianceid=11051531&SID=333747492`}" target="_blank" rel="noopener noreferrer" class="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5">
                        <i class="fa-solid fa-hotel"></i>
                        <span>Trip.com Otelleri ↗</span>
                    </a>
                    <a href="${bookingUrl}" target="_blank" rel="noopener noreferrer" class="px-4 py-2.5 bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5">
                        <i class="fa-solid fa-bed"></i>
                        <span>Booking.com ↗</span>
                    </a>
                    ${enuygunUrl ? `
                    <a href="${enuygunUrl}" target="_blank" rel="noopener noreferrer" class="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5">
                        <i class="fa-solid fa-building"></i>
                        <span>Enuygun Otel ↗</span>
                    </a>
                    ` : ''}
                    <a href="${hotelInfo.agoda_url || '#'}" target="_blank" rel="noopener noreferrer" class="px-4 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center gap-1.5">
                        <i class="fa-solid fa-suitcase"></i>
                        <span>Agoda ↗</span>
                    </a>
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
                                        ${h.provider || (hotelInfo.is_international ? 'Booking.com' : 'Trip.com')}
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
                    `).join('')}
                </div>
            ` : `
                <!-- SIFIR VARSAYIM ÇOKLU ACENTE OTEL VİTRİNİ -->
                <div class="p-6 sm:p-8 bg-slate-50/80 rounded-3xl border border-slate-200">
                    <div class="text-center max-w-xl mx-auto mb-6">
                        <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-amber-100 text-amber-900 mb-2">
                            <i class="fa-solid fa-shield-check text-amber-600"></i>
                            <span>Sıfır Varsayım: Doğrulanmış Canlı Müsaitlik</span>
                        </div>
                        <h4 class="text-lg font-black text-slate-900">${safeCity} için En Avantajlı Odaları Karşılaştırın</h4>
                        <p class="text-xs text-slate-500 mt-1">
                            ${cin} — ${cout} tarihleri ve ${escapeHtml(guests)} misafir için resmi partnerlerimizin doğrudan canlı oda arama sayfaları hazırlandı.
                        </p>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        <!-- Partner 1: Trip.com -->
                        <div class="p-5 rounded-2xl bg-white border border-slate-200 hover:border-blue-500 hover:shadow-md transition flex flex-col justify-between">
                            <div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs font-black text-blue-600 uppercase tracking-wide flex items-center gap-1.5">
                                        🏨 Trip.com Hotels
                                    </span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-800">Resmi Partner</span>
                                </div>
                                <div class="font-bold text-sm text-slate-900">${safeCity} Otelleri & Tatil Köyleri</div>
                                <div class="text-xs text-slate-500 mt-1 leading-relaxed">
                                    Geniş otel ağı, Türkçe arayüz ve ücretsiz iptal seçenekleri.
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100">
                                <a href="${hotelInfo.trip_hotel_url || (hotelInfo.deep_links && hotelInfo.deep_links.trip) || `https://tr.trip.com/hotels/list?keyword=${encodeURIComponent(city)}&checkin=${cin}&checkout=${cout}&crn=1&adult=${guests}&Allianceid=11051531&SID=333747492`}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-blue-600 hover:bg-blue-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                    <span>Trip.com'da Fiyatları Gör ↗</span>
                                </a>
                            </div>
                        </div>

                        <!-- Partner 2: Booking.com -->
                        <div class="p-5 rounded-2xl bg-white border border-slate-200 hover:border-[#003580] hover:shadow-md transition flex flex-col justify-between">
                            <div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs font-black text-[#003580] uppercase tracking-wide flex items-center gap-1.5">
                                        🏨 Booking.com
                                    </span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">Küresel Ağ</span>
                                </div>
                                <div class="font-bold text-sm text-slate-900">${safeCity} Tesisleri & Daireler</div>
                                <div class="text-xs text-slate-500 mt-1 leading-relaxed">
                                    Dünya çapında 28 milyon tesis, gerçek gezgin yorumları ve harita filtreleme.
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100">
                                <a href="${bookingUrl}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-[#003580] hover:bg-[#00224f] text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                    <span>Booking.com'da Canlı Odaları Aç ↗</span>
                                </a>
                            </div>
                        </div>

                        <!-- Partner 3: Enuygun Otel / Agoda -->
                        ${enuygunUrl ? `
                        <div class="p-5 rounded-2xl bg-white border border-slate-200 hover:border-emerald-500 hover:shadow-md transition flex flex-col justify-between">
                            <div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs font-black text-emerald-700 uppercase tracking-wide flex items-center gap-1.5">
                                        🏨 Enuygun Otel
                                    </span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800">Yurt İçi Karşılaştırma</span>
                                </div>
                                <div class="font-bold text-sm text-slate-900">${safeCity} Butik & Şehir Otelleri</div>
                                <div class="text-xs text-slate-500 mt-1 leading-relaxed">
                                    Türkiye geneli butik oteller, pansiyonlar ve taksit imkanları.
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100">
                                <a href="${enuygunUrl}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                    <span>Enuygun'da Odaları Listele ↗</span>
                                </a>
                            </div>
                        </div>
                        ` : `
                        <div class="p-5 rounded-2xl bg-white border border-slate-200 hover:border-slate-800 hover:shadow-md transition flex flex-col justify-between">
                            <div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs font-black text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
                                        🏨 Agoda
                                    </span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">Özel Teklifler</span>
                                </div>
                                <div class="font-bold text-sm text-slate-900">${safeCity} Tatil Evleri & Oteller</div>
                                <div class="text-xs text-slate-500 mt-1 leading-relaxed">
                                    Son dakika oda indirimleri ve tatil villaları.
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100">
                                <a href="${hotelInfo.agoda_url || '#'}" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 px-3 text-center bg-slate-800 hover:bg-slate-900 text-white font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5">
                                    <span>Agoda'da Odaları Aç ↗</span>
                                </a>
                            </div>
                        </div>
                        `}
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
    }

).join("");
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

    // Arama Kutularına tıklandığında içeriği otomatik seçme (Kullanıcının hemen rahatça yeni şehir/ilçe yazabilmesi için)
    const hotelCityInput = document.getElementById("hotelCity");
    [originInput, destInput, hotelCityInput].forEach(inp => {
        if (!inp) return;
        inp.addEventListener("focus", function() {
            setTimeout(() => {
                try { this.select(); } catch (_) {}
            }, 60);
        });
        inp.addEventListener("click", function() {
            if (!this.dataset.clickedOnce) {
                this.dataset.clickedOnce = '1';
                try { this.select(); } catch (_) {}
            }
        });
        inp.addEventListener("blur", function() {
            this.dataset.clickedOnce = '';
            resolveDistrictOrAirportInput(this);
        });
        inp.addEventListener("change", function() {
            resolveDistrictOrAirportInput(this);
        });
        inp.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                resolveDistrictOrAirportInput(this);
            }
        });
        let debounceTimer = null;
        inp.addEventListener("input", function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                resolveDistrictOrAirportInput(inp, true);
            }, 400);
        });
    });

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

// Etkinlik & Festival Habercisi Abonelik Yöneticisi (Gerçek Backend & Resend Entegreli)
async function handleRadarSubscribe(event) {
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

    let serverMsg = "Tebrikler! Yeni festival & yarış takvimleri açıldığında ilk sizin haberiniz olacak.";
    try {
        const res = await fetch("/api/erken-kayit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, kvkk_consent: true })
        });
        if (res.ok) {
            const data = await res.json();
            if (data && data.message) serverMsg = data.message;
        }
    } catch (e) {
        console.warn("Radar backend kayıt uyarısı:", e);
    }

    form.innerHTML = `
        <div class="px-4 py-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 font-bold text-xs flex items-center gap-2">
            <i class="fa-solid fa-circle-check text-emerald-400"></i>
            <span>${escapeHtml(serverMsg)}</span>
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
window.filterEvents = filterEvents;
window.filterCuratedEvents = filterEvents;
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
window.setFerryCategory = setFerryCategory;
window.toggleFerryVehicle = toggleFerryVehicle;
window.quickFillFerry = quickFillFerry;

// Cruise Kartı Üzerinde Dinamik Kabin Tipi Seçici (İç Kabin / Dış Kabin / Balkonlu Kabin)
function selectCruiseCabin(cardDomId, tierIdx) {
    const tickets = window.lastTransportResults || [];
    const ticket = tickets.find(t => String(t.id) === String(cardDomId));
    if (!ticket || !Array.isArray(ticket.cabin_tiers) || !ticket.cabin_tiers[tierIdx]) return;

    const selectedTier = ticket.cabin_tiers[tierIdx];
    const baseTier = ticket.cabin_tiers[0];
    const ratio = (baseTier && baseTier.price > 0) ? (selectedTier.price / baseTier.price) : 1.0;
    const paxCount = (window.lastSearchReq && window.lastSearchReq.passengers) ? window.lastSearchReq.passengers : 1;

    // 1. Ana fiyatı ve kırılım metnini güncelle
    const priceEl = document.getElementById(`ferryPriceVal-${cardDomId}`);
    if (priceEl && selectedTier.price) {
        priceEl.textContent = Number(selectedTier.price).toLocaleString('tr-TR');
    }
    const breakEl = document.getElementById(`ferryBreakdown-${cardDomId}`);
    if (breakEl) {
        breakEl.textContent = `${selectedTier.name} (${selectedTier.per_person_eur} € × ${paxCount} Kişi) • Her Şey Dahil`;
    }

    // 2. Kabin butonlarının aktif/pasif stillerini güncelle
    ticket.cabin_tiers.forEach((ct, idx) => {
        const btn = document.getElementById(`cabinBtn-${cardDomId}-${idx}`);
        if (!btn) return;
        const currSym = ct.currency || ticket.currency || '₺';
        const isSel = (idx === tierIdx);
        btn.className = `px-2.5 py-1 rounded-lg text-[11px] transition cursor-pointer inline-flex items-center gap-1.5 ${isSel
            ? 'bg-sky-900 text-white font-black shadow-2xs border border-sky-900'
            : 'bg-white hover:bg-sky-100 text-slate-700 font-bold border border-sky-200'}`;
        btn.innerHTML = `
            <span>${escapeHtml(ct.name)}:</span>
            <span class="${isSel ? 'text-amber-300 font-black' : 'text-sky-900 font-black'}">${Number(ct.price).toLocaleString('tr-TR')} ${currSym}</span>
            <span class="text-[9.5px] opacity-80">(${ct.per_person_eur}€/kişi)</span>
        `;
    });

    // 3. Alt şeritteki acente fiyatlarını seçilen kabin tipine göre güncelle
    if (Array.isArray(ticket.providers)) {
        ticket.providers.forEach((p, pIdx) => {
            const provEl = document.getElementById(`provPrice-${cardDomId}-${pIdx}`);
            if (provEl && p.price) {
                const updatedProvPrice = Math.round(p.price * ratio);
                provEl.textContent = `${Number(updatedProvPrice).toLocaleString('tr-TR')} ${p.currency || ticket.currency || '₺'}`;
            }
        });
    }
}
window.selectCruiseCabin = selectCruiseCabin;
window.setCarCategoryFilter = setCarCategoryFilter;
window.setCarTransmissionFilter = setCarTransmissionFilter;
window.toggleCarDropoffLocation = toggleCarDropoffLocation;
window.quickFillCar = quickFillCar;

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




function updateTransportFieldLabels(subTab, lang) {
    const isEn = (lang === 'en');
    const originLabel = document.getElementById("originFieldLabel");
    const destLabel = document.getElementById("destFieldLabel");
    const subHintBadge = document.getElementById("transportSubHint");
    const searchBtn = document.getElementById("searchSubmitBtnText");
    const paxTitle = document.getElementById("paxBoxTitleText");
    const paxCabinSec = document.getElementById("paxCabinSection");
    const paxFerryVehSec = document.getElementById("paxFerryVehicleSection");
    if (!subTab) subTab = window.currentTransportSubTab || 'flight';

    if (paxCabinSec) paxCabinSec.classList.toggle("hidden", subTab !== 'flight');
    if (paxFerryVehSec) paxFerryVehSec.classList.toggle("hidden", subTab !== 'ferry');

    if (subTab === 'car') {
        if (paxTitle) paxTitle.textContent = isEn ? "Driver & Pax" : "Yolcu Sayısı";
        if (originLabel) originLabel.innerHTML = isEn ? '🚗 Pick-up Location (Airport / City)' : '🚗 Alış Noktası (Havalimanı / Şehir)';
        if (destLabel) destLabel.innerHTML = (typeof currentCarDifferentDropoff !== 'undefined' && currentCarDifferentDropoff)
            ? (isEn ? '📍 Different Return Location' : '📍 Farklı İade Noktası') 
            : (isEn ? '📍 Return Location (Same Place)' : '📍 İade Noktası (Aynı Yer)');
        if (subHintBadge) subHintBadge.innerHTML = isEn 
            ? '🚗 Compare Airport Car Rentals: Enuygun, Yolcu360, Avis & Garenta' 
            : '🚗 Enuygun, Yolcu360, Avis & Garenta Havalimanı Araç Kiralama Karşılaştırması';
        if (searchBtn) searchBtn.textContent = isEn ? "Find Rental Cars →" : "Kiralık Araçları Bul →";
        if (typeof setFlightTripType === 'function') setFlightTripType('round');
    } else if (subTab === 'bus') {
        if (paxTitle) paxTitle.textContent = isEn ? "Passengers" : "Yolcu Sayısı";
        if (originLabel) originLabel.innerHTML = isEn ? '🚌 Departure City / Terminal' : '🚌 Kalkış Şehri / Otogarı';
        if (destLabel) destLabel.innerHTML = isEn ? '🎯 Destination City (Turkey & Balkans)' : '🎯 Varış Şehri (Türkiye & Balkanlar)';
        if (subHintBadge) subHintBadge.innerHTML = isEn 
            ? '🚌 Intercity & Balkan Bus Routes (Kamil Koç/FlixBus, Metro, Obilet)' 
            : '🚌 Türkiye Şehirlerarası & Balkan Hatları (Kamil Koç/FlixBus, Metro, Obilet)';
        if (searchBtn) searchBtn.textContent = isEn ? "Find Bus Routes →" : "Otobüs Seferlerini Bul →";
    } else if (subTab === 'train') {
        if (paxTitle) paxTitle.textContent = isEn ? "Passengers" : "Yolcu Sayısı";
        if (originLabel) originLabel.innerHTML = isEn ? '🚆 Departure Station' : '🚆 Kalkış İstasyonu / Garı';
        if (destLabel) destLabel.innerHTML = isEn ? '🏁 Arrival Station' : '🏁 Varış İstasyonu';
        if (subHintBadge) subHintBadge.innerHTML = isEn 
            ? '🚆 TCDD High-Speed Train (YHT) & Mainline Official Schedules' 
            : '🚆 TCDD Yüksek Hızlı Tren (YHT) & Doğu Ekspresi Hatları';
        if (searchBtn) searchBtn.textContent = isEn ? "Find Trains →" : "Tren Seferlerini Bul →";
    } else if (subTab === 'ferry') {
        if (paxTitle) paxTitle.textContent = isEn ? "Passengers & Vehicle" : "Yolcu & Araç";
        if (originLabel) originLabel.innerHTML = isEn ? '⛴️ Departure Port / Pier' : '⛴️ Kalkış Limanı / İskelesi';
        if (destLabel) destLabel.innerHTML = isEn ? '🏝️ Destination Island or Port' : '🏝️ Varış Adası veya İskelesi';
        if (subHintBadge) subHintBadge.innerHTML = isEn 
            ? '⛴️ Greek Islands Visa-on-Arrival Catamarans & Galataport Cruise Trips' 
            : '⛴️ Kapıda Vize Yunan Adaları (Sakız, Rodos, Kos) & Galataport Kruvaziyer Gemi Turları';
        if (searchBtn) searchBtn.textContent = isEn ? "Find Ferry & Cruise →" : "Gemi & Feribot Seferlerini Bul →";
    } else {
        if (paxTitle) paxTitle.textContent = isEn ? "Passengers & Class" : "Yolcu & Sınıf";
        if (originLabel) originLabel.innerHTML = isEn ? '✈️ Departure Airport' : '✈️ Kalkış Havalimanı';
        if (destLabel) destLabel.innerHTML = isEn ? '🛬 Arrival Airport' : '🛬 Varış Havalimanı';
        if (subHintBadge) subHintBadge.innerHTML = isEn 
            ? '✈️ Live Flight Price Comparison (THY, Pegasus, AJet & Global Airlines)' 
            : '✈️ THY, Pegasus, AJet & Dünya Havayolları Canlı Bilet Karşılaştırması';
        if (searchBtn) searchBtn.textContent = isEn ? "Find Flights →" : "Uçuşları Bul →";
    }
    if (typeof updatePaxSummaryDisplay === 'function') {
        updatePaxSummaryDisplay();
    }
}
window.updateTransportFieldLabels = updateTransportFieldLabels;

// ==================== HAKİKİ BİLET ANALİTİK & İSTATİSTİK MOTORU ====================
(function initHakikiAnalytics() {
    function getActiveLang() {
        try {
            return localStorage.getItem("hakiki_lang") || "tr";
        } catch (e) {
            return "tr";
        }
    }

    function trackHakikiEvent(payload) {
        if (!payload || !payload.event_type) return;
        const bodyObj = Object.assign({
            lang: getActiveLang(),
            referrer: document.referrer || ""
        }, payload);
        const bodyStr = JSON.stringify(bodyObj);
        try {
            if (navigator.sendBeacon) {
                const blob = new Blob([bodyStr], { type: "application/json" });
                navigator.sendBeacon("/api/analytics/event", blob);
                return;
            }
        } catch (e) {}
        try {
            fetch("/api/analytics/event", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: bodyStr,
                keepalive: true
            }).catch(() => {});
        } catch (e) {}
    }
    window.trackHakikiEvent = trackHakikiEvent;

    function detectProviderFromLink(href, text) {
        const h = (href || "").toLowerCase();
        const t = (text || "").toLowerCase();
        if (h.includes("trip.com") || t.includes("trip.com")) return "Trip.com";
        if (h.includes("skyscanner") || t.includes("skyscanner")) return "Skyscanner";
        if (h.includes("obilet") || t.includes("obilet")) return "Obilet";
        if (h.includes("enuygun") || t.includes("enuygun")) return "Enuygun";
        if (h.includes("kiwi.com") || t.includes("kiwi")) return "Kiwi.com";
        if (h.includes("kayak") || h.includes("booking.com") || t.includes("booking") || t.includes("kayak")) return "Booking / Kayak";
        if (h.includes("google.com/travel") || t.includes("google flights")) return "Google Flights";
        if (h.includes("turkishairlines") || t.includes("türk hava yolları") || t.includes("thy")) return "Türk Hava Yolları";
        if (h.includes("flypgs") || t.includes("pegasus")) return "Pegasus";
        if (h.includes("ajet.com") || t.includes("ajet")) return "AJet";
        if (h.includes("sunexpress") || t.includes("sunexpress")) return "SunExpress";
        if (h.includes("tcdd") || t.includes("tcdd")) return "TCDD E-Bilet";
        if (h.includes("kamilkoc") || h.includes("flixbus") || t.includes("kamil koç") || t.includes("flixbus")) return "Kamil Koç / FlixBus";
        if (h.includes("pamukkale") || t.includes("pamukkale")) return "Pamukkale Turizm";
        if (h.includes("metroturizm") || t.includes("metro turizm")) return "Metro Turizm";
        if (h.includes("yolcu360") || t.includes("yolcu360")) return "Yolcu360";
        if (h.includes("avis") || t.includes("avis")) return "Avis";
        if (h.includes("garenta") || t.includes("garenta")) return "Garenta";
        if (h.includes("feribotlines") || t.includes("feribotlines")) return "Feribotlines";
        if (h.includes("ido.com") || t.includes("ido")) return "İDO";
        if (h.includes("budo") || t.includes("budo")) return "BUDO";
        if (h.includes("turyol") || t.includes("turyol")) return "Turyol";
        return (text || "Resmi Acente").replace(/↗/g, "").trim().slice(0, 40) || "Resmi Acente";
    }

    function extractPriceFromCardOrLink(anchorEl) {
        const text = (anchorEl.innerText || anchorEl.textContent || "").replace(/\./g, "").replace(",", ".");
        const match = text.match(/(\d{3,6})\s*(?:₺|TL|EUR|€|\$)/i);
        if (match) return parseFloat(match[1]) || 0;
        const card = anchorEl.closest("[data-ticket-price], .bg-white, .rounded-2xl, .rounded-3xl");
        if (card) {
            const cardText = (card.innerText || "").replace(/\./g, "").replace(",", ".");
            const m2 = cardText.match(/(\d{3,6})\s*(?:₺|TL)/i);
            if (m2) return parseFloat(m2[1]) || 0;
        }
        return 0;
    }

    document.addEventListener("DOMContentLoaded", () => {
        try {
            const params = new URLSearchParams(window.location.search);
            const utmSource = (params.get("utm_source") || params.get("ref") || "").toLowerCase();
            const utmCampaign = (params.get("utm_campaign") || params.get("mail") || "").toLowerCase();

            trackHakikiEvent({
                event_type: "page_view",
                utm_source: utmSource,
                utm_campaign: utmCampaign
            });

            if (utmSource === "email" || utmSource === "mail" || utmSource === "bulten" || utmCampaign) {
                trackHakikiEvent({
                    event_type: "email_return",
                    utm_source: utmSource || "email",
                    utm_campaign: utmCampaign || "bulten_genel"
                });
            }
        } catch (e) {}
    });

    // Acente / Havayolu / Otobüs / Tren / Feribot / Araç Kiralama dış bağlantı tıklama yakalayıcı
    document.addEventListener("click", (ev) => {
        const anchor = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
        if (!anchor) return;
        const href = anchor.getAttribute("href") || "";
        if (!href.startsWith("http://") && !href.startsWith("https://")) return;
        if (href.includes(window.location.hostname) && !href.includes("utm_")) return;

        const provider = detectProviderFromLink(href, anchor.innerText || anchor.textContent || "");
        const price = extractPriceFromCardOrLink(anchor);
        const oInp = document.getElementById("transOrigin");
        const dInp = document.getElementById("transDest");
        const lastReq = window.lastSearchReq || {};

        trackHakikiEvent({
            event_type: "affiliate_click",
            provider_name: provider,
            transport_type: lastReq.transport_type || window.currentTransportSubTab || "flight",
            origin: lastReq.origin || (oInp ? oInp.value : "") || "",
            destination: lastReq.destination || (dInp ? dInp.value : "") || "",
            ticket_price: price
        });
    }, true);
})();

