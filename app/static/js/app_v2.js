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
let currentFlightScope = 'domestic'; // 'domestic' (Yurtiçi) or 'international' (Yurtdışı)
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
let currentFerryVehicleType = 'passenger'; // 'passenger', 'car'

function setFerryCategory(cat) {
    currentFerryCategory = cat;
    const allBtn = document.getElementById("ferryCat-all");
    const domBtn = document.getElementById("ferryCat-domestic");
    const islBtn = document.getElementById("ferryCat-islands");
    const cruBtn = document.getElementById("ferryCat-cruise");

    const activeCls = "px-2.5 py-1 rounded-lg text-[11px] font-black bg-sky-900 text-white transition";
    const inactiveCls = "px-2.5 py-1 rounded-lg text-[11px] font-bold text-slate-700 hover:text-sky-900 transition";

    if (allBtn) allBtn.className = cat === 'all' ? activeCls : inactiveCls;
    if (domBtn) domBtn.className = cat === 'domestic' ? activeCls : inactiveCls;
    if (islBtn) islBtn.className = cat === 'greek_islands' ? activeCls : inactiveCls;
    if (cruBtn) cruBtn.className = cat === 'cruise' ? activeCls : inactiveCls;

    const originInput = document.getElementById("transOrigin");
    const destInput = document.getElementById("transDest");
    if (cat === 'domestic') {
        originInput.placeholder = "";
        destInput.placeholder = "";
    } else if (cat === 'greek_islands') {
        originInput.placeholder = "";
        destInput.placeholder = "";
    } else if (cat === 'cruise') {
        originInput.placeholder = "";
        destInput.placeholder = "";
    }
}
window.setFerryCategory = setFerryCategory;

function toggleFerryVehicle() {
    const isCar = currentFerryVehicleType === 'car';
    currentFerryVehicleType = isCar ? 'passenger' : 'car';

    const btn = document.getElementById("ferryVehicleToggle");
    const label = document.getElementById("ferryVehicleLabel");
    const icon = document.getElementById("ferryVehicleIcon");

    if (currentFerryVehicleType === 'car') {
        if (btn) btn.className = "px-2.5 py-1 rounded-lg border border-sky-600 bg-sky-900 text-white font-black text-[11px] shadow-2xs transition flex items-center gap-1.5";
        if (label) label.innerText = "🚗 Arabalı Geçiş (Araç Dahil)";
        if (icon) icon.className = "fa-solid fa-car text-amber-300";
    } else {
        if (btn) btn.className = "px-2.5 py-1 rounded-lg border border-slate-300 bg-white text-slate-700 font-bold text-[11px] hover:border-sky-500 transition flex items-center gap-1.5";
        if (label) label.innerText = "🚶 Yaya (Araçsız)";
        if (icon) icon.className = "fa-solid fa-person-walking text-slate-500";
    }
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
    if (isVehicle && currentFerryVehicleType !== 'car') {
        toggleFerryVehicle();
    } else if (!isVehicle && currentFerryVehicleType === 'car') {
        toggleFerryVehicle();
    }
    const oInput = document.getElementById("transOrigin");
    const dInput = document.getElementById("transDest");
    if (oInput) oInput.value = origin;
    if (dInput) dInput.value = dest;
    executeTransportSearch();
}
window.quickFillFerry = quickFillFerry;

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
    if (currentFlightCabin === 'business') {
        str += " • Business";
    } else if (isEn) {
        str += " • Economy";
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
    } else if (transportMode === 'train') {
        const trainScope = scope || currentTrainScope;
        let trainStationsHtml = '';
        if (trainScope === 'intl') {
            trainStationsHtml = `
                <option value="İstanbul">🚆 İstanbul - Halkalı Garı (Balkan Ekspresi)</option>
                <option value="Sofya">🌍 Sofya - Merkez Gar (Bulgaristan)</option>
                <option value="Bükreş">🌍 Bükreş - Gara de Nord (Romanya)</option>
                <option value="Paris">🌍 Paris - Gare du Nord / de Lyon (Eurostar/TGV)</option>
                <option value="Londra">🌍 Londra - St Pancras Int. (Eurostar)</option>
                <option value="Roma">🌍 Roma - Termini (Frecciarossa)</option>
                <option value="Milano">🌍 Milano - Centrale (Frecciarossa)</option>
                <option value="Amsterdam">🌍 Amsterdam - Centraal (Eurostar)</option>
                <option value="Berlin">🌍 Berlin - Hbf (ICE)</option>
                <option value="Münih">🌍 Münih - Hbf (ICE)</option>
                <option value="Madrid">🌍 Madrid - Puerta de Atocha (AVE)</option>
                <option value="Barselona">🌍 Barselona - Sants (AVE)</option>
                <option value="Zürih">🌍 Zürih - HB (Railjet)</option>
                <option value="Viyana">🌍 Viyana - Hbf (Railjet)</option>
                <option value="Prag">🌍 Prag - Hlavni Nadrazi (EuroCity)</option>
            `;
        } else {
            trainStationsHtml = `
                <option value="İstanbul">🚆 İstanbul - Söğütlüçeşme / Bostancı / Halkalı YHT</option>
                <option value="Ankara">🚆 Ankara Gar (YHT / Anahat)</option>
                <option value="Eskişehir">🚆 Eskişehir Gar (YHT)</option>
                <option value="Konya">🚆 Konya Gar (YHT)</option>
                <option value="Sivas">🚆 Sivas Gar (YHT)</option>
                <option value="Karaman">🚆 Karaman Gar (YHT)</option>
                <option value="Kars">🚆 Kars Gar (Doğu Ekspresi)</option>
                <option value="İzmir">🚆 İzmir Basmane (İzmir Mavi Treni)</option>
                <option value="Denizli">🚆 Denizli Gar (Pamukkale Ekspresi)</option>
                <option value="Adana">🚆 Adana Gar</option>
                <option value="Mersin">🚆 Mersin Gar</option>
                <option value="Kayseri">🚆 Kayseri Gar</option>
                <option value="Tatvan">🚆 Tatvan Gar (Van Gölü Ekspresi)</option>
                <option value="Kurtalan">🚆 Kurtalan Gar (Güney Kurtalan Ekspresi)</option>
            `;
        }
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
            <option value="Bandırma">⛴️ Bandırma Limanı (İDO Arabalı Hızlı Feribot)</option>
            <option value="Avşa Adası">🏝️ Avşa Adası (Marmara)</option>
            <option value="Marmara Adası">🏝️ Marmara Adası</option>
            <option value="Çeşme">🇬🇷 İzmir - Çeşme Uluslararası Limanı</option>
            <option value="Sakız Adası">🇬🇷 Sakız Adası (Chios - Kapıda Vize)</option>
            <option value="Bodrum">🇬🇷 Muğla - Bodrum Yolcu Limanı</option>
            <option value="Kos Adası">🇬🇷 Kos Adası (İstanköy - Kapıda Vize)</option>
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
            <option value="Bozcaada">🏝️ Bozcaada Limanı (Gestaş)</option>
            <option value="Gökçeada">🏝️ Gökçeada (Kuzu Limanı - Gestaş)</option>
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
        if (destLabel) destLabel.innerHTML = currentCarDifferentDropoff ? '📍 Farklı İade Noktası' : '📍 İade Noktası (Aynı Yer)';
        originInput.placeholder = "";
        destInput.placeholder = "";
        if (subHintBadge) subHintBadge.innerHTML = '🚗 Enuygun, Yolcu360, Avis & Garenta Havalimanı Araç Kiralama Karşılaştırması';
        // Araç kiralamada alış ve iade tarihi gerektiğinden varsayılan olarak tarih aralığını aç
        setFlightTripType('round');
    } else if (subTab === 'bus') {
        if (originLabel) originLabel.innerHTML = '🚌 Kalkış Şehri / Otogarı';
        if (destLabel) destLabel.innerHTML = '🎯 Varış Şehri (Türkiye & Balkanlar)';
        originInput.placeholder = "";
        destInput.placeholder = "";
        if (subHintBadge) subHintBadge.innerHTML = '🚌 Türkiye Şehirlerarası & Balkan Hatları (Kamil Koç/FlixBus, Metro, Obilet)';
    } else if (subTab === 'train') {
        if (originLabel) originLabel.innerHTML = '🚆 Kalkış İstasyonu / Garı';
        if (destLabel) destLabel.innerHTML = '🏁 Varış İstasyonu';
        originInput.placeholder = "";
        destInput.placeholder = "";
        if (subHintBadge) subHintBadge.innerHTML = '🚆 TCDD Yüksek Hızlı Tren (YHT) & Doğu Ekspresi Hatları';
    } else if (subTab === 'ferry') {
        if (originLabel) originLabel.innerHTML = '⛴️ Kalkış Limanı / İskelesi';
        if (destLabel) destLabel.innerHTML = '🏝️ Varış Adası veya İskelesi';
        originInput.placeholder = "";
        destInput.placeholder = "";
        if (subHintBadge) subHintBadge.innerHTML = '⛴️ Kapıda Vize Yunan Adaları (Sakız, Rodos, Kos) & Galataport Kruvaziyer Gemi Turları';
    } else {
        if (originLabel) originLabel.innerHTML = '✈️ Kalkış Havalimanı';
        if (destLabel) destLabel.innerHTML = '🛬 Varış Havalimanı';
        originInput.placeholder = "";
        destInput.placeholder = "";
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
    if (url.includes('sorting=price') || url.includes('sort=price')) return url;
    const sep = url.includes('?') ? '&' : '?';
    return url + sep + 'sorting=price&sort=price';
}

// 4. ULAŞIM ARAMASI ÇALIŞTIRMA (Uçak Odaklı, Kusursuz Yolcu & Kapsam Desteği)
async function executeTransportSearch(e) {
    if (e) e.preventDefault();

    let origin = document.getElementById("transOrigin").value.trim();
    let destination = document.getElementById("transDest").value.trim();
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
    const paxSummaryText = `${searchReq.adults || 1} ${adultWord}${searchReq.children ? ', ' + searchReq.children + ' ' + childWord : ''}${searchReq.infants ? ', ' + searchReq.infants + ' ' + infantWord : ''}${modeType === 'flight' ? ' • ' + (searchReq.cabin_class === 'business' ? 'Business' : (isEn ? 'Economy' : 'Ekonomi')) : ''}`;
    const tripTypeText = searchReq.trip_type === 'round_trip' 
        ? `${isEn ? 'Round-Trip' : 'Gidiş - Dönüş'} (${searchReq.departure_date} ⇄ ${searchReq.return_date})` 
        : `${isEn ? 'One-Way' : 'Tek Yön'} (${searchReq.departure_date})`;
    
    const isIntlRoute = Boolean(data.travel_context && data.travel_context.is_international) || (modeType === 'flight' && currentFlightScope === 'international');
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
        <div class="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white rounded-3xl p-5 sm:p-6 mb-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl border border-slate-700">
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
                    <span>${escapeHtml(searchReq.origin)}</span>
                    <i class="fa-solid ${headerModeIcon} text-amber-400 text-base"></i>
                    <span>${escapeHtml(searchReq.destination)}</span>
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

    // ==================== ADIM 2.1 & 2.2: PEGASUS TARZI 7 GÜNLÜK FİYAT ŞERİDİ + "HAKİKİ İPUCU" + EN UCUZ OTOBÜS/TREN ROZETLERİ ====================
    const flexInsights = data.flexible_insights;
    const altBadges = data.alternative_badges || [];
    if (flexInsights && Array.isArray(flexInsights.days) && flexInsights.days.length > 0) {
        const tip = flexInsights.hakiki_tip;
        const fmtNum = (n) => Number(n).toLocaleString(isEn ? 'en-US' : 'tr-TR');

        html += `<div class="bg-white border-2 border-amber-300/80 rounded-3xl p-4 sm:p-5 mb-5 shadow-md">`;

        // 1. Üst "💡 Hakiki İpucu" Bandı
        if (tip && tip.has_savings) {
            const selDayName = isEn ? tip.selected_weekday_en : tip.selected_weekday_tr;
            const bestDayName = isEn ? tip.best_weekday_en : tip.best_weekday_tr;
            const diffTxt = isEn ? tip.diff_text_en : tip.diff_text_tr;
            const bestLbl = isEn ? tip.best_label_en : tip.best_label_tr;
            html += `
                <div class="bg-gradient-to-r from-emerald-950 via-slate-900 to-emerald-950 text-white rounded-2xl p-3.5 sm:p-4 mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border border-emerald-500/40 shadow-sm">
                    <div class="flex items-start sm:items-center gap-3">
                        <span class="w-9 h-9 rounded-xl bg-amber-400 text-slate-950 flex items-center justify-center font-black text-base shrink-0 shadow-xs">
                            💡
                        </span>
                        <div class="text-xs sm:text-sm leading-snug">
                            <span class="font-black text-amber-300 uppercase tracking-wide text-[11px] block mb-0.5">
                                ${isEn ? 'Hakiki Smart Fare Tip' : 'Hakiki Fiyat İpucu'}
                            </span>
                            ${isEn
                                ? `Instead of <strong>${selDayName}</strong> (${fmtNum(tip.selected_price)} ${tip.currency}), if you travel on <strong>${bestDayName} (${diffTxt})</strong>, the same route starts at <strong class="text-emerald-300 underline">${fmtNum(tip.best_price)} ${tip.currency}</strong> (<span class="bg-emerald-500/30 text-emerald-200 px-1.5 py-0.5 rounded font-black">${fmtNum(tip.savings)} ${tip.currency} cheaper!</span>)`
                                : `<strong>${selDayName}</strong> (${fmtNum(tip.selected_price)} ${tip.currency}) yerine <strong>${bestDayName} (${diffTxt})</strong> uçarsanız aynı rotada bilet <strong class="text-emerald-300 underline">${fmtNum(tip.best_price)} ${tip.currency}</strong> (<span class="bg-emerald-500/30 text-emerald-200 px-1.5 py-0.5 rounded font-black">${fmtNum(tip.savings)} ${tip.currency} daha ucuz!</span>)`
                            }
                        </div>
                    </div>
                    <button type="button" onclick="switchSearchDate('${tip.best_date}')"
                            class="w-full sm:w-auto px-4 py-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-black text-xs whitespace-nowrap shadow-sm transition cursor-pointer flex items-center justify-center gap-1.5 shrink-0">
                        <i class="fa-regular fa-calendar-check"></i>
                        <span>${isEn ? `Switch to ${bestLbl} →` : `Tarihi Değiştir (${bestLbl}) →`}</span>
                    </button>
                </div>
            `;
        } else if (tip && !tip.has_savings) {
            const selDayName = isEn ? tip.selected_weekday_en : tip.selected_weekday_tr;
            html += `
                <div class="bg-emerald-50 border border-emerald-200 rounded-2xl px-4 py-2.5 mb-3.5 flex items-center justify-between gap-2 text-xs text-emerald-950">
                    <div class="flex items-center gap-2 font-bold">
                        <i class="fa-solid fa-circle-check text-emerald-600 text-sm"></i>
                        <span>${isEn ? `<strong>Hakiki Fare Check:</strong> Your selected day (<strong>${selDayName}</strong>) is already the <strong>cheapest day</strong> of this 7-day period!` : `<strong>Hakiki İpucu:</strong> Seçtiğiniz gün (<strong>${selDayName}</strong>) bu 7 günlük dönemin <strong>en ucuz günü!</strong>`}</span>
                    </div>
                    <span class="px-2.5 py-0.5 rounded-full bg-emerald-600 text-white font-black text-[10px] uppercase shrink-0">${isEn ? 'Best Day' : 'En Uygun Gün'}</span>
                </div>
            `;
        }

        // 2. Pegasus Tarzı 7 Günlük Yatay Fiyat Şeridi
        html += `
            <div class="flex items-center justify-between mb-2 px-0.5">
                <div class="text-[11px] font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <i class="fa-solid fa-calendar-week text-amber-500"></i>
                    <span>${isEn ? 'Flexible 7-Day Lowest Fare Strip (Click any day to switch)' : 'Esnek 7 Günlük En Ucuz Fiyat Şeridi (Güne tıklayarak anında geçiş yapın)'}</span>
                </div>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                ${flexInsights.days.map(d => {
                    const lbl = isEn ? d.label_en : d.label_tr;
                    const pText = d.min_price ? `${fmtNum(d.min_price)} ${d.currency}` : (isEn ? 'Check' : 'Sorgula');
                    if (d.is_selected) {
                        return `
                            <button type="button" onclick="switchSearchDate('${d.date}')"
                                    class="p-2.5 rounded-2xl bg-slate-900 text-white border-2 border-slate-900 shadow-md text-center transition cursor-pointer flex flex-col items-center justify-between">
                                <span class="text-[10px] font-bold text-amber-300 uppercase tracking-tight">${isEn ? 'Selected' : 'Seçili Gün'}</span>
                                <span class="text-xs font-bold text-white my-0.5">${lbl}</span>
                                <span class="text-sm font-black text-amber-400">${pText}</span>
                            </button>
                        `;
                    } else if (d.is_cheapest) {
                        return `
                            <button type="button" onclick="switchSearchDate('${d.date}')"
                                    class="p-2.5 rounded-2xl bg-emerald-50/90 hover:bg-emerald-100 text-slate-900 border-2 border-emerald-500 shadow-2xs text-center transition cursor-pointer flex flex-col items-center justify-between">
                                <span class="text-[9.5px] font-black bg-emerald-600 text-white px-2 py-0.2 rounded-full uppercase">${isEn ? '🔥 Cheapest' : '🔥 En Ucuz'}</span>
                                <span class="text-xs font-bold text-slate-800 my-0.5">${lbl}</span>
                                <span class="text-sm font-black text-emerald-700">${pText}</span>
                            </button>
                        `;
                    } else {
                        return `
                            <button type="button" onclick="switchSearchDate('${d.date}')"
                                    class="p-2.5 rounded-2xl bg-slate-50 hover:bg-amber-50/60 text-slate-700 border border-slate-200 hover:border-amber-400 text-center transition cursor-pointer flex flex-col items-center justify-between">
                                <span class="text-[10px] font-semibold text-slate-400">${d.day_diff > 0 ? '+' + d.day_diff : d.day_diff} ${isEn ? 'd' : 'gün'}</span>
                                <span class="text-xs font-bold text-slate-800 my-0.5">${lbl}</span>
                                <span class="text-xs sm:text-sm font-black text-slate-900">${pText}</span>
                            </button>
                        `;
                    }
                }).join('')}
            </div>
        `;

        // 3. Haftanın En Ucuz Otobüs & Tren Alternatif Rozetleri
        if (altBadges.length > 0) {
            html += `
                <div class="mt-3.5 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                    <div class="text-[11px] font-black text-slate-600 flex items-center gap-1.5">
                        <i class="fa-solid fa-tags text-amber-500"></i>
                        <span>${isEn ? 'Cheapest Ground / Alternative Transport on This Route:' : 'Bu Güzergahta Haftanın En Ucuz Alternatif Ulaşım Rozetleri:'}</span>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        ${altBadges.map(b => {
                            const bTitle = isEn ? b.title_en : b.title_tr;
                            const bPrice = b.min_price ? `${fmtNum(b.min_price)} ${b.currency}` : (isEn ? 'Live Fares' : 'Canlı Seferler');
                            return `
                                <button type="button" onclick="switchUnifiedTab('${b.mode}'); executeTransportSearch();"
                                        class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-900 hover:text-white text-slate-800 border border-slate-200 text-xs font-bold transition cursor-pointer flex items-center gap-2 shadow-2xs group">
                                    <span>${b.icon} <strong>${bTitle}:</strong></span>
                                    <span class="px-2 py-0.5 rounded-lg bg-amber-400 text-slate-950 font-black text-xs">${bPrice}</span>
                                    ${b.duration ? `<span class="text-[10.5px] opacity-75">(${b.duration})</span>` : ''}
                                    <span class="text-[10px] font-black text-amber-600 group-hover:text-amber-300">${isEn ? 'Switch →' : 'Gör →'}</span>
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        html += `</div>`;
    }

    // Filtre & Hızlı Sıralama Çubuğu (En Erken / En Geç & 12-18 Öğle Slotu Dahil)
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
                            (${tickets.length} ${unitLabel})
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
                ? (isEn ? "Please select a coastal port or use Smart Route for combined travel." : "Lütfen feribot iskelesi olan bir kıyı noktası seçiniz veya Akıllı Rota Sihirbazı'nı kullanınız.")
                : (modeType === 'train'
                    ? (isEn ? "Please check bus or flight options for this route." : "Bu güzergah için otobüs veya uçak alternatiflerini inceleyebilirsiniz.")
                    : (isEn ? "Please try a different date or transport mode." : "Lütfen farklı bir tarih veya alternatif ulaşım modunu seçiniz.")));
        const emptyIcon = modeType === 'ferry' ? 'fa-anchor-circle-xmark' : (modeType === 'train' ? 'fa-train' : (modeType === 'bus' ? 'fa-bus' : 'fa-plane-slash'));
        html += `
            <div class="bg-white p-10 rounded-3xl border-2 border-slate-200 text-center shadow-xs mb-6">
                <i class="fa-solid ${emptyIcon} text-3xl text-amber-500 mb-3"></i>
                <div class="font-black text-slate-800 text-base">${escapeHtml(primaryNotice)}</div>
                <div class="text-xs text-slate-500 mt-1.5 font-medium">${escapeHtml(secondaryNotice)}</div>
            </div>
        `;
    } else {
        html += `<div id="ticketCardsContainer" class="space-y-4 mb-6">`;
        html += generateTicketCardsHtml(tickets, searchReq);
        html += `</div>`;
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

        if (ticket.transport_type === 'train') {
            const hasReturn = isRoundTrip && ticket.return_leg;
            const retLeg = ticket.return_leg;
            const discounts = ticket.discounts || {};
            const trainNo = ticket.flight_number || 'YHT';
            const badgeText = ticket.badge || 'Yüksek Hızlı Tren (YHT)';
            const isIntlTrain = ticket.id && ticket.id.startsWith('tr-intl');
            const targetUrl = ticket.direct_link || ticket.official_link || 'https://ebilet.tcddtasimacilik.gov.tr/';
            const btnLabel = isIntlTrain ? (isEn ? 'Book on Trainline ↗' : 'Trainline ile Al ↗') : (isEn ? 'TCDD Official E-Ticket ↗' : 'TCDD E-Bilet Resmi Portalı ↗');

            let discountsHtml = '';
            if (discounts.genc_ogrenci || discounts.yas_65_ustu) {
                discountsHtml = `
                    <div class="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-bold text-slate-600">
                        <span class="text-indigo-800 font-extrabold flex items-center gap-1">
                            <i class="fa-solid fa-tags text-indigo-600"></i> ${isEn ? 'Legal Discounts:' : 'Kanuni İndirimler:'}
                        </span>
                        ${discounts.genc_ogrenci ? `<span class="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">🎓 ${isEn ? 'Youth/Student:' : 'Genç/Öğrenci:'} <strong>${Number(discounts.genc_ogrenci).toLocaleString('tr-TR')} ${ticket.currency || '₺'}</strong></span>` : ''}
                        ${discounts.yas_65_ustu ? `<span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200">👴 65+ Yaş: <strong>${Number(discounts.yas_65_ustu).toLocaleString('tr-TR')} ${ticket.currency || '₺'}</strong></span>` : ''}
                        ${discounts.ogretmen ? `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">Öğretmen: <strong>${Number(discounts.ogretmen).toLocaleString('tr-TR')} ${ticket.currency || '₺'}</strong></span>` : ''}
                        <span class="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">👶 0-6 Yaş: <strong>${isEn ? 'Free' : 'Ücretsiz'}</strong></span>
                    </div>
                `;
            }

            let returnLegHtml = '';
            if (hasReturn) {
                returnLegHtml = `
                    <div class="mt-3 bg-slate-50/90 p-3 sm:p-3.5 rounded-2xl border border-slate-200">
                        <div class="text-[11px] font-black text-slate-700 mb-2 flex items-center justify-between">
                            <span class="flex items-center gap-1.5 text-indigo-700 font-black">
                                <i class="fa-solid fa-train"></i> 🚆 ${isEn ? 'RETURN TRAIN' : 'DÖNÜŞ TRENİ'} • ${retLeg.departure_date_formatted || searchReq.return_date}
                            </span>
                            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                                ${retLeg.flight_number || 'YHT Dönüş'}
                            </span>
                        </div>
                        <div class="grid grid-cols-12 items-center gap-2">
                            <div class="col-span-4 sm:col-span-3 text-left">
                                <div class="text-xl font-black text-slate-900 leading-none">${retLeg.departure_time}</div>
                                <div class="text-xs font-bold text-slate-700 mt-1 truncate">${retLeg.origin}</div>
                            </div>
                            <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                <div class="text-xs font-bold text-slate-600 mb-1">${retLeg.duration || ticket.duration}</div>
                                <div class="relative flex items-center justify-center h-6 my-1">
                                    <div class="absolute inset-x-0 h-[2px] bg-indigo-200"></div>
                                    <div class="relative z-10 bg-white px-2 py-0.5 rounded-full border border-indigo-200 shadow-2xs flex items-center justify-center">
                                        <i class="fa-solid fa-train text-indigo-600 text-[10px] transform rotate-180"></i>
                                    </div>
                                </div>
                                <div class="text-[10.5px] font-bold text-emerald-600 mt-1">✓ ${isEn ? 'Direct' : 'Direkt • Aktarmasız'}</div>
                            </div>
                            <div class="col-span-4 sm:col-span-3 text-right">
                                <div class="text-xl font-black text-slate-900 leading-none">${retLeg.arrival_time}</div>
                                <div class="text-xs font-bold text-slate-700 mt-1 truncate">${retLeg.destination}</div>
                            </div>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="bg-white border-2 border-slate-200 hover:border-indigo-400 rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-xl transition-all mb-4">
                    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-5">
                        
                        <!-- Sol / Sefer Detayları -->
                        <div class="flex-1 min-w-0">
                            <!-- Üst Rozet Satırı -->
                            <div class="flex flex-wrap items-center gap-2 mb-3">
                                <div class="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 flex items-center justify-center text-base shadow-2xs">
                                    🚆
                                </div>
                                <span class="font-black text-slate-900 text-sm sm:text-base">${ticket.carrier}</span>
                                <span class="px-2 py-0.5 rounded-md font-mono text-[11px] font-black bg-slate-100 text-slate-800 border border-slate-200">
                                    ${trainNo}
                                </span>
                                <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-amber-100 text-amber-900 border border-amber-200">
                                    ${badgeText}
                                </span>
                                ${ticket.platform ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-indigo-100 text-indigo-800 border border-indigo-200">🚏 ${escapeHtml(ticket.platform)}</span>` : ''}
                                ${ticket.live_status ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">${escapeHtml(ticket.live_status)}</span>` : ''}
                                ${isIntlTrain
                                    ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-sky-100 text-sky-800">${isEn ? 'European Rail' : 'Avrupa Hızlı Tren'}</span>`
                                    : (ticket.train_category === 'anahat'
                                        ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-purple-100 text-purple-800">🌙 ${isEn ? 'Sleeper / Couchette & Pullman' : 'Pulman / Kuşetli & Yataklı'}</span>`
                                        : (ticket.train_category === 'bolgesel'
                                            ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-teal-100 text-teal-800">🚆 ${isEn ? 'Regional Express' : 'TCDD Bölgesel Hat'}</span>`
                                            : `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-emerald-100 text-emerald-800">⚡ ${isEn ? 'Station-to-Station 250+ km/h' : 'Gardan Gara 250+ km/s'}</span>`))}
                            </div>

                            <!-- Gidiş Seferi Zaman Çizelgesi -->
                            <div class="bg-slate-50/60 p-3.5 sm:p-4 rounded-2xl border border-slate-200">
                                ${hasReturn ? `<div class="text-[11px] font-black text-indigo-700 mb-2 flex items-center gap-1.5"><i class="fa-solid fa-train"></i> ${isEn ? 'OUTBOUND TRAIN' : 'GİDİŞ TRENİ'} • ${ticket.departure_date_formatted}</div>` : ''}
                                <div class="grid grid-cols-12 items-center gap-2">
                                    <div class="col-span-4 sm:col-span-3 text-left">
                                        <div class="text-2xl font-black text-slate-900 leading-none">${ticket.departure_time}</div>
                                        <div class="text-xs font-bold text-slate-700 mt-1.5 truncate">${ticket.origin}</div>
                                        <div class="text-[11px] text-slate-400 font-medium">${ticket.departure_date_formatted}</div>
                                    </div>
                                    <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                        <div class="text-xs font-bold text-slate-600 mb-1">${ticket.duration || '4 sa 20 dk'}</div>
                                        <div class="relative flex items-center justify-center h-6 my-1">
                                            <div class="absolute inset-x-0 h-[2px] bg-indigo-300"></div>
                                            <div class="relative z-10 bg-white px-2.5 py-0.5 rounded-full border border-indigo-300 shadow-2xs flex items-center justify-center">
                                                <i class="fa-solid fa-train text-indigo-600 text-xs"></i>
                                            </div>
                                        </div>
                                        <div class="text-[10.5px] font-bold text-emerald-600 mt-1">✓ ${isEn ? 'Direct' : 'Direkt • Aktarmasız'}${ticket.full_route ? ` <span class="text-slate-500 font-semibold">(${escapeHtml(ticket.full_route)})</span>` : ''}</div>
                                    </div>
                                    <div class="col-span-4 sm:col-span-3 text-right">
                                        <div class="text-2xl font-black text-slate-900 leading-none">${ticket.arrival_time}</div>
                                        <div class="text-xs font-bold text-slate-700 mt-1.5 truncate">${ticket.destination}</div>
                                        <div class="text-[11px] text-slate-400 font-medium">${ticket.arrival_date_formatted || ticket.departure_date_formatted}</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Varsa Dönüş Seferi -->
                            ${returnLegHtml}

                            <!-- İndirimler Şeridi -->
                            ${discountsHtml}
                        </div>

                        <!-- Sağ / Fiyat ve Doğrudan Biletleme Butonu -->
                        <div class="lg:w-64 flex flex-col justify-between items-end border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6">
                            <div class="text-right w-full">
                                <div class="text-[10px] font-black uppercase tracking-wider text-slate-400 flex items-center justify-end gap-1">
                                    <i class="fa-solid fa-circle-check text-emerald-500"></i>
                                    <span>${isEn ? 'Verified Official Fare' : 'Doğrulanmış Taban Fiyat'}</span>
                                </div>
                                <div class="text-3xl font-black text-slate-950 mt-1">
                                    ${Number(ticket.price).toLocaleString('tr-TR')} <span class="text-lg font-bold">${ticket.currency || '₺'}</span>
                                </div>
                                <div class="text-[11px] font-semibold text-slate-500 mt-0.5">
                                    ${isRoundTrip ? (isEn ? 'Round-trip Total' : 'Gidiş - Dönüş Toplam') : (isEn ? 'One-way Base Fare' : 'Tek Yön Taban Ücret')}
                                </div>
                            </div>

                            <div class="w-full mt-4">
                                <a href="${targetUrl}" target="_blank" rel="noopener noreferrer"
                                   class="w-full py-3 px-4 bg-gradient-to-r from-indigo-900 via-indigo-800 to-indigo-700 hover:from-black hover:to-indigo-950 text-white font-black text-xs sm:text-sm rounded-2xl shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 group">
                                    <span>${btnLabel}</span>
                                    <i class="fa-solid fa-arrow-up-right-from-square text-xs group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"></i>
                                </a>
                                <div class="text-[10px] text-center text-slate-400 font-medium mt-1.5">
                                    ${isIntlTrain ? 'Trainline resmi acente rezervasyonu' : 'Resmi TCDD Taşımacılık E-Bilet Sistemi'}
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            `;
        }

        if (ticket.transport_type === 'bus') {
            const hasReturn = isRoundTrip && ticket.return_leg;
            const retLeg = ticket.return_leg;
            const busType = ticket.flight_number || '2+1 Rahat';
            const badgeText = ticket.badge || 'Sefer';
            const isKamilOrFlix = Boolean(
                ticket.winner_channel === 'kamilkoc_official' ||
                (ticket.carrier && (ticket.carrier.toLowerCase().includes('kamil') || ticket.carrier.toLowerCase().includes('flix') || ticket.carrier.toLowerCase().includes('alpar')))
            );
            const targetUrl = isKamilOrFlix
                ? (ticket.kamilkoc_link || ticket.direct_link || ticket.official_link || 'https://www.kamilkoc.com.tr/')
                : (ensureObiletPriceSort(ticket.obilet_link) || ticket.direct_link || ticket.official_link || 'https://www.obilet.com/');

            const priceStr = ticket.price ? `${Number(ticket.price).toLocaleString('tr-TR')} ${ticket.currency || '₺'}` : '';
            const btnLabel = isKamilOrFlix
                ? (isEn
                    ? `Book on Kamil Koç / FlixBus ${priceStr ? `(${priceStr})` : ''} ↗`
                    : `Kamil Koç'tan Al ${priceStr ? `(${priceStr})` : ''} ↗`)
                : (isEn
                    ? `Select Seat on Obilet ${priceStr ? `(${priceStr})` : ''} ↗`
                    : `Obilet'te Koltuk Seç ${priceStr ? `(${priceStr})` : ''} ↗`);

            const discounts = ticket.discounts || {};
            const hasTimeDiscount = Boolean(discounts.has_time_discount && discounts.original_price && discounts.original_price > ticket.price);

            const rawFeatures = Array.isArray(ticket.features) && ticket.features.length > 0
                ? ticket.features
                : ['Ücretsiz Wi-Fi', '220V Priz & USB', 'İkram Servisi'];
            const featuresHtml = `
                <div class="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-bold text-slate-600">
                    <span class="text-emerald-800 font-extrabold flex items-center gap-1">
                        <i class="fa-solid fa-couch text-emerald-600"></i> ${isEn ? 'Features:' : 'Donanım:'}
                    </span>
                    <span class="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">💺 ${escapeHtml(busType)}</span>
                    ${rawFeatures.slice(0, 4).map(f => `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">✓ ${escapeHtml(String(f))}</span>`).join('')}
                </div>
            `;

            const localAgenciesHtml = `
                <div class="mt-2.5 pt-2.5 border-t border-dashed border-slate-200 flex flex-wrap items-center gap-2 text-[11px]">
                    <span class="text-slate-400 font-bold text-[10px] uppercase flex items-center gap-1">
                        <i class="fa-solid fa-store text-emerald-600"></i> ${isEn ? 'Booking Channels:' : 'Biletleme & Acenteler:'}
                    </span>
                    ${isKamilOrFlix && ticket.kamilkoc_link ? `
                        <a href="${ticket.kamilkoc_link}" target="_blank" rel="noopener noreferrer"
                           class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-400 font-black shadow-2xs transition"
                           title="Kamil Koç / FlixBus Resmi Bilet ve Koltuk Seçim Ekranı">
                            <span>🏆 Kamil Koç Resmi</span>
                            ${priceStr ? `<span class="font-black text-emerald-800 bg-white px-1.5 py-0.5 rounded text-[10px] border border-amber-300">${priceStr}</span>` : ''}
                            <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] text-amber-700"></i>
                        </a>
                    ` : ''}
                    ${ticket.obilet_link ? `
                        <a href="${ensureObiletPriceSort(ticket.obilet_link)}" target="_blank" rel="noopener noreferrer"
                           class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl ${!isKamilOrFlix ? 'bg-rose-50 hover:bg-rose-100 text-rose-950 border border-rose-300 font-black' : 'bg-rose-50/80 hover:bg-rose-100 text-rose-950 border border-rose-300/80 font-bold'} shadow-2xs transition"
                           title="Obilet canlı sefer ve koltuk seçimi ekranında aç">
                            <span class="flex items-center gap-1"><i class="fa-solid fa-ticket-simple text-rose-600 text-[10px]"></i> Obilet</span>
                            <span class="font-extrabold text-rose-700 bg-white/90 px-1.5 py-0.5 rounded text-[9.5px] border border-rose-200">${!isKamilOrFlix && priceStr ? priceStr : (isEn ? 'Select Seat' : 'Koltuk Seç')}</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] text-rose-600 opacity-70"></i>
                        </a>
                    ` : ''}
                    ${ticket.enuygun_link ? `
                        <a href="${ticket.enuygun_link}" target="_blank" rel="noopener noreferrer"
                           class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-50/80 hover:bg-emerald-100 text-emerald-950 border border-emerald-300/80 font-bold shadow-2xs transition"
                           title="Enuygun otobüs bileti tekliflerini karşılaştırın">
                            <span class="flex items-center gap-1"><i class="fa-solid fa-ticket text-emerald-600 text-[10px]"></i> Enuygun</span>
                            <span class="font-extrabold text-emerald-700 bg-white/90 px-1.5 py-0.5 rounded text-[9.5px] border border-emerald-200">${isEn ? 'See Offers' : 'Teklifleri Gör'}</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] text-emerald-600 opacity-70"></i>
                        </a>
                    ` : ''}
                    ${!isKamilOrFlix && ticket.carrier_official_link ? `
                        <a href="${ticket.carrier_official_link}" target="_blank" rel="noopener noreferrer"
                           class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 font-bold shadow-2xs transition"
                           title="${escapeHtml(ticket.carrier)} resmi web sitesi">
                            <span>🚌 ${escapeHtml(ticket.carrier)} Resmi Site</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] opacity-70"></i>
                        </a>
                    ` : ''}
                </div>
            `;

            let returnLegHtml = '';
            if (hasReturn) {
                returnLegHtml = `
                    <div class="mt-3 bg-slate-50/90 p-3 sm:p-3.5 rounded-2xl border border-slate-200">
                        <div class="text-[11px] font-black text-slate-700 mb-2 flex items-center justify-between">
                            <span class="flex items-center gap-1.5 text-emerald-700 font-black">
                                <i class="fa-solid fa-bus"></i> 🚌 ${isEn ? 'RETURN BUS' : 'DÖNÜŞ OTOBÜSÜ'} • ${retLeg.departure_date_formatted || searchReq.return_date}
                            </span>
                            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                                ${retLeg.carrier || ticket.carrier} • ${retLeg.flight_number || 'Dönüş'}
                            </span>
                        </div>
                        <div class="grid grid-cols-12 items-center gap-2">
                            <div class="col-span-4 sm:col-span-3 text-left">
                                <div class="text-xl font-black text-slate-900 leading-none">${retLeg.departure_time}</div>
                                <div class="text-xs font-bold text-slate-700 mt-1 truncate">${retLeg.origin}</div>
                            </div>
                            <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                <div class="text-xs font-bold text-slate-600 mb-1">${retLeg.duration || ticket.duration}</div>
                                <div class="relative flex items-center justify-center h-6 my-1">
                                    <div class="absolute inset-x-0 h-[2px] bg-emerald-200"></div>
                                    <div class="relative z-10 bg-white px-2 py-0.5 rounded-full border border-emerald-200 shadow-2xs flex items-center justify-center">
                                        <i class="fa-solid fa-bus text-emerald-600 text-[10px] transform rotate-180"></i>
                                    </div>
                                </div>
                                <div class="text-[10.5px] font-bold text-emerald-600 mt-1">✓ ${isEn ? 'Direct' : 'Direkt • Mola Dahil'}</div>
                            </div>
                            <div class="col-span-4 sm:col-span-3 text-right">
                                <div class="text-xl font-black text-slate-900 leading-none">${retLeg.arrival_time}</div>
                                <div class="text-xs font-bold text-slate-700 mt-1 truncate">${retLeg.destination}</div>
                            </div>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="bg-white border-2 ${isKamilOrFlix ? 'border-emerald-300/90 hover:border-emerald-600' : 'border-slate-200 hover:border-emerald-500'} rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-xl transition-all mb-4">
                    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-5">
                        
                        <!-- Sol / Sefer Detayları -->
                        <div class="flex-1 min-w-0">
                            <!-- Üst Rozet Satırı -->
                            <div class="flex flex-wrap items-center gap-2 mb-3">
                                <div class="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center text-base shadow-2xs">
                                    🚌
                                </div>
                                <span class="font-black text-slate-900 text-sm sm:text-base">${escapeHtml(ticket.carrier)}</span>
                                <span class="px-2 py-0.5 rounded-md font-mono text-[11px] font-black bg-slate-100 text-slate-800 border border-slate-200">
                                    ${escapeHtml(busType)}
                                </span>
                                <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-amber-100 text-amber-900 border border-amber-200">
                                    ${escapeHtml(badgeText)}
                                </span>
                                <span class="px-2 py-0.5 rounded-full text-[10.5px] font-black ${isKamilOrFlix ? 'bg-sky-100 text-sky-900 border border-sky-200' : 'bg-emerald-100 text-emerald-800'}">
                                    🛡️ ${isKamilOrFlix ? 'Kamil Koç / FlixBus Resmi' : 'Obilet Canlı Sefer'}
                                </span>
                            </div>

                            <!-- Gidiş Seferi Zaman Çizelgesi -->
                            <div class="bg-slate-50/60 p-3.5 sm:p-4 rounded-2xl border border-slate-200">
                                ${hasReturn ? `<div class="text-[11px] font-black text-emerald-700 mb-2 flex items-center gap-1.5"><i class="fa-solid fa-bus"></i> ${isEn ? 'OUTBOUND BUS' : 'GİDİŞ OTOBÜSÜ'} • ${ticket.departure_date_formatted}</div>` : ''}
                                <div class="grid grid-cols-12 items-center gap-2">
                                    <div class="col-span-4 sm:col-span-3 text-left">
                                        <div class="text-2xl font-black text-slate-900 leading-none">${ticket.departure_time}</div>
                                        <div class="text-xs font-bold text-slate-700 mt-1.5 truncate">${escapeHtml(ticket.origin)}</div>
                                        <div class="text-[11px] text-slate-400 font-medium">${ticket.departure_date_formatted}</div>
                                    </div>
                                    <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                        <div class="text-xs font-bold text-slate-600 mb-1">${ticket.duration || '6 sa'}</div>
                                        <div class="relative flex items-center justify-center h-6 my-1">
                                            <div class="absolute inset-x-0 h-[2px] bg-emerald-300"></div>
                                            <div class="relative z-10 bg-white px-2.5 py-0.5 rounded-full border border-emerald-300 shadow-2xs flex items-center justify-center">
                                                <i class="fa-solid fa-bus text-emerald-600 text-xs"></i>
                                            </div>
                                        </div>
                                        <div class="text-[10.5px] font-bold text-emerald-600 mt-1">✓ ${isEn ? 'Direct' : 'Direkt • Mola Dahil'}</div>
                                    </div>
                                    <div class="col-span-4 sm:col-span-3 text-right">
                                        <div class="text-2xl font-black text-slate-900 leading-none">${ticket.arrival_time}</div>
                                        <div class="text-xs font-bold text-slate-700 mt-1.5 truncate">${escapeHtml(ticket.destination)}</div>
                                        <div class="text-[11px] text-slate-400 font-medium">${ticket.arrival_date_formatted || ticket.departure_date_formatted}</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Varsa Dönüş Seferi -->
                            ${returnLegHtml}

                            <!-- Donanım Şeridi -->
                            ${featuresHtml}



                            <!-- Yerli Acenteler & Alternatif Kanallar (Kamil Koç Resmi, Obilet, Enuygun) -->
                            ${localAgenciesHtml}
                        </div>

                        <!-- Sağ / Fiyat ve Doğrudan Biletleme Butonu -->
                        <div class="lg:w-64 flex flex-col justify-between items-end border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6">
                            <div class="text-right w-full">
                                <div class="text-[10px] font-black uppercase tracking-wider text-slate-400 flex items-center justify-end gap-1">
                                    <i class="fa-solid fa-circle-check text-emerald-500"></i>
                                    <span>${escapeHtml(ticket.price_status_text || (isEn ? 'Live Official Fare' : 'Canlı Resmi Fiyat'))}</span>
                                </div>
                                ${hasTimeDiscount ? `
                                    <div class="text-xs font-bold text-rose-500 line-through mt-0.5">
                                        ${Number(discounts.original_price).toLocaleString('tr-TR')} ${ticket.currency || '₺'}
                                    </div>
                                ` : ''}
                                <div class="text-3xl font-black text-slate-950 mt-0.5">
                                    ${ticket.price ? `${Number(ticket.price).toLocaleString('tr-TR')} <span class="text-lg font-bold">${ticket.currency || '₺'}</span>` : `<span class="text-xl">${isEn ? 'Live Fares' : 'Canlı Seferler'}</span>`}
                                </div>
                                <div class="text-[11px] font-semibold text-slate-500 mt-0.5">
                                    ${isRoundTrip ? (isEn ? 'Round-trip Total' : 'Gidiş - Dönüş Toplam') : (isEn ? 'One-way Live Fare' : 'Tek Yön Canlı Bilet Ücreti')}
                                </div>
                                <div class="text-[10.5px] font-bold text-amber-700 bg-amber-50 rounded-lg px-2 py-1 mt-1.5 border border-amber-200/80 text-center">
                                    📍 ${escapeHtml(ticket.carrier)} • ${ticket.departure_time} (${escapeHtml(ticket.origin)})
                                </div>
                            </div>

                            <div class="w-full mt-3">
                                <a href="${targetUrl}" target="_blank" rel="noopener noreferrer"
                                   class="w-full py-3 px-4 ${isKamilOrFlix ? 'bg-gradient-to-r from-amber-500 via-amber-600 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950' : 'bg-gradient-to-r from-emerald-800 via-emerald-700 to-teal-800 hover:from-black hover:to-emerald-950 text-white'} font-black text-xs sm:text-sm rounded-2xl shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 group">
                                    <span>${btnLabel}</span>
                                    <i class="fa-solid fa-arrow-up-right-from-square text-xs group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"></i>
                                </a>
                                <div class="text-[10px] text-center text-slate-500 font-medium mt-1.5">
                                    ${isKamilOrFlix 
                                        ? `Kamil Koç resmi ekranında <strong>${ticket.departure_time}</strong> seferini seçip YolKart/Genç indirimiyle alabilirsiniz` 
                                        : `Obilet'te saat <strong>${ticket.departure_time}</strong> seferini seçerek koltuğunuzu alabilirsiniz`}
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            `;
        }

        if (ticket.transport_type === 'ferry' || ticket.is_cruise) {
            const hasReturn = isRoundTrip && ticket.return_leg;
            const retLeg = ticket.return_leg;
            const isCruise = ticket.is_cruise || ticket.category === 'cruise';
            const isGreekIsland = ticket.is_greek_island || ticket.category === 'greek_islands';
            const targetUrl = ticket.direct_link || ticket.official_link || 'https://www.ido.com.tr/';
            
            let btnLabel = isEn ? 'Book Official Ferry ↗' : 'Resmi Bileti Al ↗';
            if (isCruise) {
                btnLabel = isEn ? 'View Cruise Details & Book ↗' : 'Kruvaziyer Rezervasyonu ↗';
            } else if (ticket.carrier && ticket.carrier.includes('İDO')) {
                btnLabel = 'İDO Resmi Portalı ↗';
            } else if (ticket.carrier && ticket.carrier.includes('BUDO')) {
                btnLabel = 'BUDO Resmi Satış ↗';
            } else if (ticket.carrier && ticket.carrier.includes('Ertürk')) {
                btnLabel = 'Ertürk Lines ile Al ↗';
            } else if (ticket.carrier && ticket.carrier.includes('Feribotlines')) {
                btnLabel = 'Feribotlines ile Al ↗';
            } else if (ticket.carrier && ticket.carrier.includes('Turyol')) {
                btnLabel = 'Turyol Resmi Satış ↗';
            }

            let featuresHtml = '';
            if (isCruise) {
                featuresHtml = `
                    <div class="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-bold text-slate-600">
                        <span class="text-sky-900 font-extrabold flex items-center gap-1">
                            <i class="fa-solid fa-ship text-sky-600"></i> ${isEn ? 'Cruise Amenities:' : 'Tur Detayları:'}
                        </span>
                        <span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-900 border border-amber-200">⭐ Her Şey Dahil (Tam Pansiyon)</span>
                        <span class="px-2 py-0.5 rounded-md bg-sky-50 text-sky-800 border border-sky-200">🛏️ Kabin Konaklama</span>
                        <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">🎭 Canlı Şovlar & Müzik</span>
                        <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">🏊 Havuz & Güverte Keyfi</span>
                    </div>
                `;
            } else if (isGreekIsland) {
                featuresHtml = `
                    <div class="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-bold text-slate-600">
                        <span class="text-sky-900 font-extrabold flex items-center gap-1">
                            <i class="fa-solid fa-anchor text-sky-600"></i> ${isEn ? 'Services:' : 'Hizmetler:'}
                        </span>
                        <span class="px-2 py-0.5 rounded-md bg-sky-50 text-sky-800 border border-sky-200">🇬🇷 Kapıda Vizeye Uygun</span>
                        <span class="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">⚡ Hızlı Katamaran</span>
                        <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">☕ Kafeterya & Bar</span>
                        <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">🧳 Serbest Bagaj</span>
                    </div>
                `;
            } else {
                featuresHtml = `
                    <div class="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-bold text-slate-600">
                        <span class="text-sky-900 font-extrabold flex items-center gap-1">
                            <i class="fa-solid fa-water text-sky-600"></i> ${isEn ? 'Services:' : 'Hizmetler:'}
                        </span>
                        ${ticket.vehicle_allowed ? '<span class="px-2 py-0.5 rounded-md bg-sky-50 text-sky-800 border border-sky-200">🚗 Arabalı Feribot</span>' : '<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">🚶 Yaya Deniz Otobüsü</span>'}
                        <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">🛋️ Konforlu Salon</span>
                        <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">☕ Büfe / İkram</span>
                        <span class="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">🌊 Marmara Güvenli Hat</span>
                    </div>
                `;
            }

            let returnLegHtml = '';
            if (hasReturn) {
                returnLegHtml = `
                    <div class="mt-3 bg-slate-50/90 p-3 sm:p-3.5 rounded-2xl border border-slate-200">
                        <div class="text-[11px] font-black text-slate-700 mb-2 flex items-center justify-between">
                            <span class="flex items-center gap-1.5 text-sky-700 font-black">
                                <i class="fa-solid fa-ship"></i> ⛴️ ${isEn ? 'RETURN VOYAGE' : 'DÖNÜŞ SEFERİ'} • ${retLeg.departure_date_formatted || searchReq.return_date}
                            </span>
                            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                                ${retLeg.carrier || ticket.carrier} • ${retLeg.flight_number || 'Dönüş'}
                            </span>
                        </div>
                        <div class="grid grid-cols-12 items-center gap-2">
                            <div class="col-span-4 sm:col-span-3 text-left">
                                <div class="text-xl font-black text-slate-900 leading-none">${retLeg.departure_time}</div>
                                <div class="text-xs font-bold text-slate-700 mt-1 truncate">${retLeg.origin}</div>
                            </div>
                            <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                <div class="text-xs font-bold text-slate-600 mb-1">${retLeg.duration || ticket.duration}</div>
                                <div class="relative flex items-center justify-center h-6 my-1">
                                    <div class="absolute inset-x-0 h-[2px] bg-sky-300"></div>
                                    <div class="relative z-10 bg-white px-2 py-0.5 rounded-full border border-sky-300 shadow-2xs flex items-center justify-center">
                                        <i class="fa-solid fa-ship text-sky-600 text-[10px] transform rotate-180"></i>
                                    </div>
                                </div>
                                <div class="text-[10.5px] font-bold text-emerald-600 mt-1">✓ ${isEn ? 'Direct' : 'Direkt • Tarifeli Hat'}</div>
                            </div>
                            <div class="col-span-4 sm:col-span-3 text-right">
                                <div class="text-xl font-black text-slate-900 leading-none">${retLeg.arrival_time}</div>
                                <div class="text-xs font-bold text-slate-700 mt-1 truncate">${retLeg.destination}</div>
                            </div>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="bg-white border-2 border-slate-200 hover:border-sky-500 rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-xl transition-all mb-4">
                    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-5">
                        
                        <!-- Sol / Sefer Detayları -->
                        <div class="flex-1 min-w-0">
                            <!-- Üst Rozet Satırı -->
                            <div class="flex flex-wrap items-center gap-2 mb-3">
                                <div class="w-8 h-8 rounded-xl bg-sky-50 border border-sky-200 text-sky-700 flex items-center justify-center text-base shadow-2xs">
                                    ${ticket.carrier_logo || (isCruise ? '🛳️' : '⛴️')}
                                </div>
                                <span class="font-black text-slate-900 text-sm sm:text-base">${ticket.carrier}</span>
                                <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-black bg-amber-100 text-amber-900 border border-amber-200">
                                    ${ticket.badge || 'Tarifeli Sefer'}
                                </span>
                                ${isCruise ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-purple-100 text-purple-900">🛳️ Kruvaziyer Gemi Turu</span>` : ''}
                                ${isGreekIsland ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-sky-100 text-sky-800">🇬🇷 Kapıda Vize</span>` : ''}
                                ${ticket.vehicle_allowed ? `<span class="px-2 py-0.5 rounded-full text-[10.5px] font-black bg-emerald-100 text-emerald-800">🚗 Arabalı Feribot</span>` : ''}
                            </div>

                            <!-- Gidiş Seferi Zaman Çizelgesi -->
                            <div class="bg-slate-50/60 p-3.5 sm:p-4 rounded-2xl border border-slate-200">
                                ${hasReturn ? `<div class="text-[11px] font-black text-sky-700 mb-2 flex items-center gap-1.5"><i class="fa-solid fa-ship"></i> ${isEn ? 'OUTBOUND VOYAGE' : 'GİDİŞ SEFERİ'} • ${ticket.departure_date_formatted}</div>` : ''}
                                <div class="grid grid-cols-12 items-center gap-2">
                                    <div class="col-span-4 sm:col-span-3 text-left">
                                        <div class="text-2xl font-black text-slate-900 leading-none">${ticket.departure_time}</div>
                                        <div class="text-xs font-bold text-slate-700 mt-1.5 truncate">${ticket.origin}</div>
                                        <div class="text-[11px] text-slate-400 font-medium">${ticket.departure_date_formatted}</div>
                                    </div>
                                    <div class="col-span-4 sm:col-span-6 px-1 text-center">
                                        <div class="text-xs font-bold text-slate-600 mb-1">${ticket.duration || '1 sa 30 dk'}</div>
                                        <div class="relative flex items-center justify-center h-6 my-1">
                                            <div class="absolute inset-x-0 h-[2px] bg-sky-300"></div>
                                            <div class="relative z-10 bg-white px-2.5 py-0.5 rounded-full border border-sky-300 shadow-2xs flex items-center justify-center">
                                                <i class="fa-solid fa-ship text-sky-600 text-xs"></i>
                                            </div>
                                        </div>
                                        <div class="text-[10.5px] font-bold text-emerald-600 mt-1">✓ ${isEn ? 'Direct' : 'Direkt • Tarifeli Hat'}</div>
                                    </div>
                                    <div class="col-span-4 sm:col-span-3 text-right">
                                        <div class="text-2xl font-black text-slate-900 leading-none">${ticket.arrival_time}</div>
                                        <div class="text-xs font-bold text-slate-700 mt-1.5 truncate">${ticket.destination}</div>
                                        <div class="text-[11px] text-slate-400 font-medium">${ticket.arrival_date_formatted || ticket.departure_date_formatted}</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Varsa Dönüş Seferi -->
                            ${returnLegHtml}

                            <!-- Hizmet / Donanım Şeridi -->
                            ${featuresHtml}
                        </div>

                        <!-- Sağ / Fiyat ve Doğrudan Biletleme Butonu -->
                        <div class="lg:w-64 flex flex-col justify-between items-end border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6">
                            <div class="text-right w-full">
                                <div class="text-[10px] font-black uppercase tracking-wider text-slate-400 flex items-center justify-end gap-1">
                                    <i class="fa-solid fa-circle-check text-sky-500"></i>
                                    <span>${isCruise ? (isEn ? 'Verified Cruise Fare' : 'Doğrulanmış Tur Fiyatı') : (isEn ? 'Verified Base Fare' : 'Doğrulanmış Taban Fiyat')}</span>
                                </div>
                                <div class="text-3xl font-black text-slate-950 mt-1">
                                    ${Number(ticket.price).toLocaleString('tr-TR')} <span class="text-lg font-bold">${ticket.currency || '₺'}</span>
                                </div>
                                <div class="text-[11px] font-semibold text-slate-500 mt-0.5">
                                    ${isCruise ? 'Her Şey Dahil Kişi Başı' : (isRoundTrip ? (isEn ? 'Round-trip Total' : 'Gidiş - Dönüş Toplam') : (isEn ? 'One-way Base Fare' : 'Tek Yön Taban Ücret'))}
                                </div>
                            </div>

                            <div class="w-full mt-4">
                                <a href="${targetUrl}" target="_blank" rel="noopener noreferrer"
                                   class="w-full py-3 px-4 bg-gradient-to-r from-sky-900 via-sky-800 to-cyan-800 hover:from-black hover:to-sky-950 text-white font-black text-xs sm:text-sm rounded-2xl shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 group">
                                    <span>${btnLabel}</span>
                                    <i class="fa-solid fa-arrow-up-right-from-square text-xs group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"></i>
                                </a>
                                <div class="text-[10px] text-center text-slate-400 font-medium mt-1.5">
                                    ${(ticket.carrier && ticket.carrier.includes('İDO')) ? 'İDO resmi satış altyapısı' : ((ticket.carrier && ticket.carrier.includes('BUDO')) ? 'BURULAŞ resmi biletleme portali' : 'Doğrudan yetkili deniz yolu rezervasyonu')}
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            `;
        }

        if (!isFlight) {
            // Araç Kiralama veya Diğer Taşıt Kartı
            const typeIcon = '🚗';
            const typeColor = 'bg-amber-50 text-amber-700 border-amber-200';

            return `
                <div class="bg-white border-2 border-slate-200 hover:border-amber-400 rounded-3xl p-5 sm:p-6 shadow-xs hover:shadow-lg transition-all flex flex-col md:flex-row items-center justify-between gap-4">
                    <div class="flex items-center gap-4 w-full md:w-auto">
                        <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl ${typeColor} border shadow-2xs flex-shrink-0">
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
                            <div class="relative flex items-center justify-center h-6 my-1">
                                <div class="absolute inset-x-0 h-[2px] bg-slate-300"></div>
                                <div class="relative z-10 bg-white px-2 py-0.5 rounded-full border border-slate-300 shadow-2xs flex items-center justify-center">
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
                                    <div class="relative flex items-center justify-center h-6 my-1">
                                        <div class="absolute inset-x-0 h-[2px] bg-slate-300"></div>
                                        <div class="relative z-10 bg-white px-2.5 py-0.5 rounded-full border border-slate-300 shadow-2xs flex items-center justify-center">
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
                                ${(ticket.providers || []).filter(p => p.price !== null && p.price !== undefined && Number(p.price) > 0).map(p => {
                                    const hasVerifiedPrice = true;
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

                        <!-- Yerli Acenteler: Enuygun & Obilet 'Teklifleri Gör' Karşılaştırma Kutusu -->
                        ${ticket.enuygun_link || ticket.obilet_link ? `
                            <div class="pt-2 border-t border-dashed border-slate-200 flex flex-wrap items-center gap-2 text-[11px]">
                                <span class="text-slate-400 font-bold text-[10px] uppercase flex items-center gap-1">
                                    <i class="fa-solid fa-store text-emerald-600"></i> ${isEn ? 'Local OTAs:' : 'Yerli Acenteler:'}
                                </span>
                                ${ticket.enuygun_link ? `
                                    <a href="${ticket.enuygun_link}" target="_blank" rel="noopener noreferrer" 
                                       class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-50/80 hover:bg-emerald-100 text-emerald-950 border border-emerald-300/80 font-bold shadow-2xs transition" 
                                       title="${isEn ? 'Compare live offers on Enuygun' : 'Enuygun canlı sefer ve kampanya tekliflerini inceleyin'}">
                                        <span class="flex items-center gap-1"><i class="fa-solid fa-ticket text-emerald-600 text-[10px]"></i> Enuygun</span>
                                        <span class="font-extrabold text-emerald-700 bg-white/90 px-1.5 py-0.5 rounded text-[9.5px] border border-emerald-200">${isEn ? 'See Offers' : 'Teklifleri Gör'}</span>
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] text-emerald-600 opacity-70"></i>
                                    </a>
                                ` : ''}
                                ${ticket.obilet_link ? `
                                    <a href="${ensureObiletPriceSort(ticket.obilet_link)}" target="_blank" rel="noopener noreferrer" 
                                       class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-rose-50/80 hover:bg-rose-100 text-rose-950 border border-rose-300/80 font-bold shadow-2xs transition" 
                                       title="${isEn ? 'Compare live offers on Obilet' : 'Obilet canlı bilet ve acente tekliflerini inceleyin'}">
                                        <span class="flex items-center gap-1"><i class="fa-solid fa-ticket-simple text-rose-600 text-[10px]"></i> Obilet</span>
                                        <span class="font-extrabold text-rose-700 bg-white/90 px-1.5 py-0.5 rounded text-[9.5px] border border-rose-200">${isEn ? 'See Offers' : 'Teklifleri Gör'}</span>
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[8.5px] text-rose-600 opacity-70"></i>
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
                                ${totalPaxText} ${isEn ? 'total' : 'için toplam'}${isRoundTrip && ticket.price ? ` <span class="text-amber-700 font-semibold">(${isEn ? 'One-way avg.' : 'Tek yön ort.'} ~${Math.round(ticket.price / (searchReq.passengers || 1) / 2).toLocaleString(isEn ? 'en-US' : 'tr-TR')} ${ticket.currency || '₺'})</span>` : ''}
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
                            <span class="italic text-slate-400">${isEn ? `*Direct checkout via ${escapeHtml(winnerLabel)}.` : `*${escapeHtml(winnerLabel)} güvencesiyle doğrudan rezervasyon.`}</span>
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
        // Otobüs sekmesinde vitrindeki ilk 3 Kamil Koç Resmi seferini en üstte tut, ardından en ucuz biletleri sırala
        list.sort((a, b) => {
            if (currentTransportSubTab === 'bus') {
                const aFeat = a.is_featured_partner ? (Number(a.featured_rank) || 1) : 999;
                const bFeat = b.is_featured_partner ? (Number(b.featured_rank) || 1) : 999;
                if (aFeat !== bFeat) return aFeat - bFeat;
            }
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

    // Arama Kutularına tıklandığında içeriği sıfırlama (Kullanıcının hemen rahatça yeni şehir/ilçe yazabilmesi için)
    const hotelCityInput = document.getElementById("hotelCity");
    [originInput, destInput, hotelCityInput].forEach(inp => {
        if (!inp) return;
        inp.addEventListener("focus", function() {
            try { this.select(); } catch (_) {}
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


