const parkSearch = document.getElementById('park-search');
const parkDropdown = document.getElementById('park-dropdown');
const selectedParksListDiv = document.getElementById('selected-parks-list');
const selectedCampgroundsListDiv = document.getElementById('selected-campgrounds-list');
const campgroundSection = document.getElementById('campgrounds-section');
const campgroundDropdownBtn = document.getElementById('campground-dropdown-btn');
const campgroundDropdown = document.getElementById('campground-dropdown');

let selectedParks = {}; // {parkName: parkName} — NPS unit name is both key and id now (offline search, no RIDB RecAreaID needed)
let selectedCampgrounds = {}; // {cgId: cgName}
let parkResultsCache = [];
let campgroundResultsCache = []; // [{id, name, lat, lon, phone, reservationUrl}, ...] — flat, derived via point-in-polygon

function pill(label, onRemove) {
    const el = document.createElement('span');
    el.className = 'pill';
    const text = document.createElement('span');
    text.textContent = label;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'pill-remove';
    remove.setAttribute('aria-label', 'Remove');
    remove.textContent = '×';
    remove.onclick = onRemove;
    el.appendChild(text);
    el.appendChild(remove);
    return el;
}

// --- Park search: instant client-side search over the bundled 442 NPS
// unit names (nps_boundaries.geojson) — no per-keystroke network call.
// RIDB's recareas search only matches whole words ("sequo" returns nothing,
// "sequoia" returns 14), so a live API call can never be truly responsive
// to a partial word; searching the local bundle is both faster and correct.
let allParkNames = [];
CampsiteMap.getParkNames().then(names => { allParkNames = names; });

parkSearch.addEventListener('input', function () {
    const query = parkSearch.value.trim();
    if (query.length === 0) {
        parkDropdown.hidden = true;
        parkResultsCache = [];
        return;
    }
    const ql = query.toLowerCase();
    parkResultsCache = allParkNames
        .filter(name => name.toLowerCase().includes(ql))
        .sort((a, b) => fuzzyScore(b, query) - fuzzyScore(a, query))
        .slice(0, 25);
    renderParkDropdown();
});
parkSearch.addEventListener('keydown', e => { if (e.key === 'Enter') e.preventDefault(); });
parkSearch.addEventListener('focus', () => { if (parkResultsCache.length > 0) renderParkDropdown(); });
document.addEventListener('click', e => {
    if (!parkSearch.contains(e.target) && !parkDropdown.contains(e.target)) parkDropdown.hidden = true;
});

function fuzzyScore(name, q) {
    if (!q) return 0;
    const nameLower = name.toLowerCase();
    const ql = q.toLowerCase();
    if (nameLower === ql) return 1000;
    if (nameLower.startsWith(ql)) return 900;
    if (nameLower.includes(ql)) return 800;
    let score = 0, qi = 0;
    for (let ni = 0; ni < nameLower.length && qi < ql.length; ++ni) {
        if (nameLower[ni] === ql[qi]) { score += 10; qi++; }
    }
    return score;
}

function renderParkDropdown() {
    parkDropdown.innerHTML = '';
    if (parkResultsCache.length === 0) { parkDropdown.hidden = true; return; }
    parkResultsCache.forEach(parkName => {
        const item = document.createElement('div');
        item.className = 'combo-option';
        const label = document.createElement('label');
        label.style.display = 'flex';
        label.style.alignItems = 'center';
        label.style.gap = '8px';
        label.style.margin = '0';
        label.style.cursor = 'pointer';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = !!selectedParks[parkName];
        checkbox.addEventListener('change', function (e) {
            e.stopPropagation();
            if (this.checked) {
                selectedParks[parkName] = parkName;
            } else {
                delete selectedParks[parkName];
            }
            renderSelectedParks();
        });
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(parkName));
        item.appendChild(label);
        parkDropdown.appendChild(item);
    });
    parkDropdown.hidden = false;
}

function updateMapCampgrounds() {
    const selectedIds = new Set(Object.keys(selectedCampgrounds));
    CampsiteMap.setCampgrounds(campgroundResultsCache, selectedIds, onMapMarkerToggle);
}

function onMapMarkerToggle(cgId, cgName) {
    const nowSelected = !selectedCampgrounds[cgId];
    if (nowSelected) {
        selectedCampgrounds[cgId] = cgName;
    } else {
        delete selectedCampgrounds[cgId];
    }
    CampsiteMap.setSelected(cgId, nowSelected);
    renderSelectedCampgrounds();
    updateCampgroundBtnText();
    if (!campgroundDropdown.hidden) renderCampgroundDropdown();
}

function renderSelectedParks() {
    selectedParksListDiv.innerHTML = '';
    CampsiteMap.setParks(Object.values(selectedParks));
    Object.entries(selectedParks).forEach(([parkName]) => {
        selectedParksListDiv.appendChild(pill(parkName, () => {
            delete selectedParks[parkName];
            renderSelectedParks();
            refreshCampgroundsForSelectedParks();
        }));
    });

    campgroundSection.style.display = '';
    campgroundDropdownBtn.style.display = '';
    refreshCampgroundsForSelectedParks();
}

function renderSelectedCampgrounds() {
    selectedCampgroundsListDiv.innerHTML = '';
    Object.entries(selectedCampgrounds).forEach(([cgId, cgName]) => {
        const el = pill(cgName, () => {
            delete selectedCampgrounds[cgId];
            CampsiteMap.setSelected(cgId, false);
            renderSelectedCampgrounds();
            updateCampgroundBtnText();
        });
        el.addEventListener('mouseenter', () => CampsiteMap.highlight(cgId));
        el.addEventListener('mouseleave', () => CampsiteMap.unhighlight(cgId, true));
        selectedCampgroundsListDiv.appendChild(el);
    });
}

// Derives campgrounds for the currently selected parks entirely offline —
// point-in-polygon against the bundled park boundaries and campground
// bundle (CampsiteMap.campgroundsInParks) — no RIDB call.
function refreshCampgroundsForSelectedParks() {
    const parkNames = Object.values(selectedParks);
    if (parkNames.length === 0) {
        campgroundResultsCache = [];
        campgroundDropdownBtn.disabled = true;
        campgroundDropdown.hidden = true;
        updateMapCampgrounds();
        renderSelectedCampgrounds();
        return;
    }
    CampsiteMap.campgroundsInParks(parkNames).then(campgrounds => {
        campgroundResultsCache = campgrounds;
        // Deliberately does not prune selectedCampgrounds when a park pill
        // is removed or a campground falls just outside the (~200m
        // simplified) boundary polygon — an explicit campground selection
        // is the user's choice and shouldn't silently vanish because of
        // boundary-matching imprecision.
        campgroundDropdownBtn.disabled = campgrounds.length === 0;
        if (campgrounds.length === 0) campgroundDropdown.hidden = true;
        if (!campgroundDropdown.hidden) renderCampgroundDropdown();
        updateCampgroundBtnText();
        renderSelectedCampgrounds();
        updateMapCampgrounds();
    });
}

campgroundDropdownBtn.addEventListener('click', () => {
    renderCampgroundDropdown();
    campgroundDropdown.hidden = false;
});
document.addEventListener('click', e => {
    if (!campgroundDropdownBtn.contains(e.target) && !campgroundDropdown.contains(e.target)) campgroundDropdown.hidden = true;
});

function renderCampgroundDropdown() {
    campgroundDropdown.innerHTML = '';
    if (!campgroundResultsCache || campgroundResultsCache.length === 0) {
        campgroundDropdown.hidden = true;
        return;
    }
    campgroundResultsCache.forEach(cg => {
        const item = document.createElement('div');
        item.className = 'combo-option';
        const label = document.createElement('label');
        label.style.display = 'flex';
        label.style.alignItems = 'center';
        label.style.gap = '8px';
        label.style.margin = '0';
        label.style.cursor = 'pointer';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = !!selectedCampgrounds[String(cg.id)];
        checkbox.addEventListener('change', function (e) {
            e.stopPropagation();
            if (this.checked) {
                selectedCampgrounds[String(cg.id)] = cg.name;
            } else {
                delete selectedCampgrounds[String(cg.id)];
            }
            CampsiteMap.setSelected(String(cg.id), this.checked);
            updateCampgroundBtnText();
            renderSelectedCampgrounds();
        });
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(cg.name));
        label.addEventListener('mouseenter', () => CampsiteMap.highlight(String(cg.id)));
        label.addEventListener('mouseleave', () => CampsiteMap.unhighlight(String(cg.id), !!selectedCampgrounds[String(cg.id)]));
        item.appendChild(label);
        campgroundDropdown.appendChild(item);
    });
    campgroundDropdown.hidden = false;
    updateCampgroundBtnText();
}

function updateCampgroundBtnText() {
    const selected = Object.values(selectedCampgrounds);
    campgroundDropdownBtn.textContent = selected.length > 0 ? selected.join(', ') : 'Select campgrounds…';
}

// --- Email pillfield ---
let emailList = [];
const emailInput = document.getElementById('email-input');
const emailListDiv = document.getElementById('email-list');

emailInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        const val = emailInput.value.trim();
        if (val && isValidEmail(val) && !emailList.includes(val)) {
            emailList.push(val);
            renderEmailList();
            emailInput.value = '';
        }
    }
});
function renderEmailList() {
    emailListDiv.innerHTML = '';
    emailList.forEach((email, idx) => {
        emailListDiv.appendChild(pill(email, () => {
            emailList.splice(idx, 1);
            renderEmailList();
        }));
    });
}
function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// --- Segmented toggles (partial / tents-permitted) ---
function wireSegmented(id) {
    const el = document.getElementById(id);
    el.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
            el.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', 'false'));
            btn.setAttribute('aria-pressed', 'true');
            el.dataset.checked = btn.dataset.value;
        });
    });
}
wireSegmented('partial-toggle');
wireSegmented('tents-toggle');
function segmentedValue(id) {
    return document.getElementById(id).dataset.checked === 'true';
}

// --- Date range picker ---
let startDate = '';
let endDate = '';
const dateRangeInput = document.getElementById('date-range');
const picker = new Litepicker({
    element: dateRangeInput,
    singleMode: false,
    format: 'YYYY-MM-DD',
    tooltip: true,
    numberOfColumns: 2,
    numberOfMonths: 2,
    autoApply: true,
    tooltipText: totalDays => {
        if (!totalDays || totalDays <= 1) return '';
        const nights = totalDays - 1;
        return nights === 1 ? '1 night' : `${nights} nights`;
    },
    pluralize: (i, label) => {
        if (label === 'day') return i === 1 ? '1 night' : `${i} nights`;
        return `${i} ${label}${i > 1 ? 's' : ''}`;
    }
});
window.picker = picker;

function updateDateRangeInput(start, end) {
    startDate = start ? start.format('YYYY-MM-DD') : '';
    endDate = end ? end.format('YYYY-MM-DD') : '';
    if (start && end) {
        const nights = end.diff(start, 'days');
        dateRangeInput.value = `${startDate} to ${endDate} (${nights} night${nights === 1 ? '' : 's'})`;
    } else if (start) {
        dateRangeInput.value = startDate;
    } else {
        dateRangeInput.value = '';
    }
}
picker.on('selected', (start, end) => updateDateRangeInput(start, end));
picker.on('hide', () => updateDateRangeInput(picker.getDate(), picker.getEndDate()));
dateRangeInput.addEventListener('input', () => {
    if (!dateRangeInput.value) { startDate = ''; endDate = ''; }
});

function uuidv4() {
    return 'xxxxxxxx_xxxx_4xxx_yxxx_xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function showStatus(message, kind) {
    document.getElementById('submit-status').innerHTML = `<div class="alert alert-${kind}">${message}</div>`;
}

// --- Submit ---
document.getElementById('campsite-form').addEventListener('submit', function (e) {
    e.preventDefault();

    const currentEmail = emailInput.value.trim();
    if (currentEmail && isValidEmail(currentEmail) && !emailList.includes(currentEmail)) {
        emailList.push(currentEmail);
        renderEmailList();
        emailInput.value = '';
    }

    if (emailList.length === 0) {
        showStatus('Please enter at least one valid email.', 'danger');
        emailInput.focus();
        return;
    }
    if (Object.keys(selectedCampgrounds).length === 0) {
        showStatus('Please select at least one campground.', 'danger');
        return;
    }

    const userName = document.getElementById('user-name').value.trim();
    let key, endpoint;
    if (EDIT_MODE && typeof PREPOP_CONFIG !== 'undefined') {
        key = PREPOP_CONFIG.key || PREPOP_CONFIG.uuid || PREPOP_CONFIG.id;
        endpoint = UPDATE_ENDPOINT;
    } else {
        key = uuidv4();
        endpoint = API_ENDPOINTS.addConfig;
    }

    const nationalParksDict = {};
    Object.entries(selectedParks).forEach(([parkId, parkName]) => { nationalParksDict[parkName] = String(parkId); });

    const campgroundsDict = {};
    Object.keys(selectedCampgrounds).forEach(cgId => { campgroundsDict[selectedCampgrounds[cgId]] = String(cgId); });

    const configValue = {
        name: userName,
        start_date: startDate,
        end_date: endDate,
        national_parks: nationalParksDict,
        campgrounds: campgroundsDict,
        email_to: emailList,
        partial: segmentedValue('partial-toggle'),
        tents_permitted: segmentedValue('tents-toggle'),
        active: true
    };

    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: configValue, national_parks: nationalParksDict })
    })
        .then(response => { if (!response.ok) throw new Error('save failed'); return response.json(); })
        .then(() => showStatus('Submitted!', 'success'))
        .catch(() => showStatus('Error saving config.', 'danger'));
});

// --- Prepopulation (edit mode) ---
document.addEventListener('DOMContentLoaded', function () {
    CampsiteMap.init('campsite-map');
    campgroundSection.style.display = '';
    campgroundDropdownBtn.style.display = '';
    campgroundDropdownBtn.disabled = true;
    campgroundDropdownBtn.textContent = 'Select campgrounds…';

    if (!EDIT_MODE || typeof PREPOP_CONFIG === 'undefined') return;

    if (PREPOP_CONFIG.national_parks && typeof PREPOP_CONFIG.national_parks === 'object') {
        // Saved configs store {parkName: <old RIDB RecAreaID>} from before the
        // offline-search switch; only the name matters now (boundary/campground
        // matching is name-based), so the old id is simply ignored here.
        Object.keys(PREPOP_CONFIG.national_parks).forEach(parkName => {
            selectedParks[parkName] = parkName;
        });
        if (PREPOP_CONFIG.campgrounds) {
            Object.entries(PREPOP_CONFIG.campgrounds).forEach(([cgName, cgId]) => {
                selectedCampgrounds[String(cgId)] = cgName;
            });
            renderSelectedCampgrounds();
        }
        renderSelectedParks();
    }

    if (Array.isArray(PREPOP_CONFIG.email_to)) {
        emailList = PREPOP_CONFIG.email_to.slice();
        renderEmailList();
    }

    if (PREPOP_CONFIG.start_date && PREPOP_CONFIG.end_date) {
        setTimeout(() => {
            if (window.picker) {
                window.picker.setDateRange(PREPOP_CONFIG.start_date, PREPOP_CONFIG.end_date);
                updateDateRangeInput(dayjs(PREPOP_CONFIG.start_date), dayjs(PREPOP_CONFIG.end_date));
            }
        }, 200);
    }
});

// --- Delete (edit mode) ---
if (EDIT_MODE) {
    const deleteBtn = document.getElementById('deleteBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function () {
            if (!confirm('Are you sure you want to delete this configuration? This action cannot be undone.')) return;
            fetch(DELETE_ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
                .then(response => {
                    if (response.ok) {
                        showStatus('Configuration deleted.', 'success');
                        document.getElementById('campsite-form').querySelectorAll('input,button,textarea,select').forEach(el => el.disabled = true);
                        setTimeout(() => { window.location.href = MAIN_PAGE_URL; }, 1200);
                    } else {
                        showStatus('Error deleting configuration.', 'danger');
                    }
                })
                .catch(() => showStatus('Error deleting configuration.', 'danger'));
        });
    }
}
