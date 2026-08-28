// Campsite location map: park boundaries + campground pins, synced with the
// campground picker in config_form.js via the CampsiteMap interface below.
// Amenity flags are best-effort (keyword-matched from RIDB's free-text
// FacilityDescription — RIDB has no structured toilet/water field).

var CampsiteMap = (function () {
    var map = null;
    var parkLayer = null;
    var markers = {}; // facilityId -> L.CircleMarker
    var parkFeatures = [];
    var parkFeaturesPromise = null;
    var campgroundBundlePromise = null;
    var amenitiesCache = {}; // facilityId -> promise of amenity flags

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    function loadParkFeatures() {
        if (!parkFeaturesPromise) {
            parkFeaturesPromise = fetch(API_ENDPOINTS.parkBoundaries)
                .then(r => { if (!r.ok) throw new Error('boundary bundle ' + r.status); return r.json(); })
                .then(gj => { parkFeatures = gj.features || []; return parkFeatures; });
        }
        return parkFeaturesPromise;
    }

    function loadCampgroundBundle() {
        if (!campgroundBundlePromise) {
            campgroundBundlePromise = fetch(API_ENDPOINTS.campgroundsBundle)
                .then(r => { if (!r.ok) throw new Error('campground bundle ' + r.status); return r.json(); })
                .then(list => list.filter(f => f.FacilityLatitude && f.FacilityLongitude));
        }
        return campgroundBundlePromise;
    }

    // All 442 NPS unit names, for instant client-side search — no per-
    // keystroke network call, unlike RIDB's recareas search (which also
    // only matches whole words, not prefixes — "sequo" returns nothing).
    function getParkNames() {
        return loadParkFeatures().then(function (features) {
            var names = new Set();
            features.forEach(f => { if (f.properties && f.properties.UNIT_NAME) names.add(f.properties.UNIT_NAME); });
            return Array.from(names).sort();
        });
    }

    // Even-odd ray casting. ring = array of [lon,lat] pairs (GeoJSON order).
    function pointInRing(lat, lon, ring) {
        var inside = false;
        for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            var xi = ring[i][0], yi = ring[i][1];
            var xj = ring[j][0], yj = ring[j][1];
            var intersects = ((yi > lat) !== (yj > lat)) &&
                (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi);
            if (intersects) inside = !inside;
        }
        return inside;
    }

    function pointInPolygonCoords(lat, lon, rings) {
        if (!pointInRing(lat, lon, rings[0])) return false;
        for (var i = 1; i < rings.length; i++) {
            if (pointInRing(lat, lon, rings[i])) return false; // inside a hole
        }
        return true;
    }

    function pointInFeature(lat, lon, feature) {
        var geom = feature.geometry;
        if (!geom) return false;
        if (geom.type === 'Polygon') return pointInPolygonCoords(lat, lon, geom.coordinates);
        if (geom.type === 'MultiPolygon') return geom.coordinates.some(poly => pointInPolygonCoords(lat, lon, poly));
        return false;
    }

    // Campgrounds from the nationwide bundle that fall inside any of the
    // given parks' boundary polygons — fully offline, no RIDB call.
    function campgroundsInParks(parkNames) {
        return Promise.all([loadParkFeatures(), loadCampgroundBundle()]).then(function (results) {
            var matchedParks = matchParkFeatures(results[0], parkNames);
            var campgrounds = results[1];
            if (matchedParks.length === 0) return [];
            return campgrounds
                .filter(cg => matchedParks.some(f => pointInFeature(cg.FacilityLatitude, cg.FacilityLongitude, f)))
                .map(cg => ({
                    id: String(cg.FacilityID),
                    name: cg.FacilityName,
                    lat: cg.FacilityLatitude,
                    lon: cg.FacilityLongitude,
                    phone: cg.FacilityPhone,
                    reservationUrl: cg.FacilityReservationURL,
                }));
        });
    }

    function markerStyle(state) {
        // state: 'default' | 'selected' | 'highlighted'
        if (state === 'selected') {
            return { radius: 10, weight: 2, color: '#fff', fillColor: cssVar('--lg-gold'), fillOpacity: 1 };
        }
        if (state === 'highlighted') {
            return { radius: 10, weight: 2, color: cssVar('--lg-highlight'), fillColor: cssVar('--lg-highlight'), fillOpacity: 1 };
        }
        return { radius: 7, weight: 1.5, color: cssVar('--lg-gold'), fillColor: '#fff', fillOpacity: 1 };
    }

    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#1976d2';
    }

    function amenitiesFor(facilityId) {
        if (!amenitiesCache[facilityId]) {
            amenitiesCache[facilityId] = fetch(API_ENDPOINTS.amenitiesTemplate.replace('__ID__', facilityId))
                .then(r => r.ok ? r.json() : null)
                .catch(() => null);
        }
        return amenitiesCache[facilityId];
    }

    function amenitiesHtml(flags) {
        if (!flags || !flags.description_source) return '<div class="section-note">No amenity info available.</div>';
        var labels = { toilets: 'Toilets', potable_water: 'Potable water', showers: 'Showers', dump_station: 'Dump station', hookups: 'Hookups' };
        return '<ul class="camp-amenities">' + Object.keys(labels).map(key =>
            '<li>' + (flags[key] ? '✓' : '✕') + ' ' + labels[key] + '</li>'
        ).join('') + '</ul>';
    }

    function tooltipHtml(cg) {
        var bits = [];
        if (cg.phone) bits.push('☎ ' + escapeHtml(cg.phone));
        return '<div class="camp-tip"><b>' + escapeHtml(cg.name) + '</b>' +
            (bits.length ? '<div class="section-note">' + bits.join(' · ') + '</div>' : '') +
            (cg.reservationUrl ? '<a href="' + escapeHtml(cg.reservationUrl) + '" target="_blank" rel="noopener">Reserve →</a>' : '') +
            '<div class="camp-amenities-slot" data-facility="' + cg.id + '">Loading amenities…</div></div>';
    }

    function init(elementId) {
        map = L.map(elementId, { zoomControl: true, attributionControl: false });
        map.setView([39.5, -98.35], 4); // CONUS default
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 16, attribution: 'Tiles &copy; Esri'
        }).addTo(map);
        loadParkFeatures().catch(err => console.error('park boundary preload failed', err));
    }

    // Strips "national park(s)" and normalizes punctuation/whitespace so
    // "Sequoia & Kings Canyon National Parks" and the NPS boundary dataset's
    // separate "Sequoia National Park" / "Kings Canyon National Park" units
    // both reduce to space-joined core name tokens, letting a combined RIDB
    // park name match multiple individual boundary units.
    function coreName(s) {
        return (s || '')
            .toLowerCase()
            .replace(/national parks?/g, ' ')
            .replace(/&/g, ' ')
            .replace(/\band\b/g, ' ')
            .replace(/[^a-z0-9 ]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function matchParkFeatures(features, parkNames) {
        var selectedCores = parkNames.map(coreName).filter(Boolean);
        return features.filter(function (f) {
            var unitCore = coreName(f.properties && f.properties.UNIT_NAME);
            if (!unitCore) return false;
            return selectedCores.some(function (sel) {
                // word-boundary containment either direction, so a combined
                // selection ("Sequoia & Kings Canyon National Parks") matches
                // boundary units the NPS dataset lists separately, and vice versa
                return (' ' + sel + ' ').indexOf(' ' + unitCore + ' ') !== -1 ||
                    unitCore.indexOf(sel) !== -1;
            });
        });
    }

    function setParks(parkNames) {
        if (parkLayer) { map.removeLayer(parkLayer); parkLayer = null; }
        loadParkFeatures().then(function (features) {
            var matched = matchParkFeatures(features, parkNames);
            if (matched.length === 0) return;
            parkLayer = L.geoJSON({ type: 'FeatureCollection', features: matched }, {
                interactive: false,
                style: { color: cssVar('--lg-highlight'), weight: 2, dashArray: '6,4', fillColor: cssVar('--lg-highlight'), fillOpacity: 0.05 }
            }).addTo(map);
            var bounds = parkLayer.getBounds();
            if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20] });
        });
    }

    function setCampgrounds(campgrounds, selectedIds, onToggle) {
        Object.values(markers).forEach(m => map.removeLayer(m));
        markers = {};
        var latlngs = [];
        campgrounds.forEach(function (cg) {
            if (!cg.lat || !cg.lon) return;
            var isSelected = selectedIds.has(String(cg.id));
            var marker = L.circleMarker([cg.lat, cg.lon], markerStyle(isSelected ? 'selected' : 'default')).addTo(map);
            marker.bindTooltip(tooltipHtml(cg), { direction: 'top', opacity: 0.97, className: 'camptip' });
            marker.on('tooltipopen', function () {
                amenitiesFor(cg.id).then(function (flags) {
                    var slot = document.querySelector('.camp-amenities-slot[data-facility="' + cg.id + '"]');
                    if (slot) slot.outerHTML = amenitiesHtml(flags);
                });
            });
            marker.on('click', function () { onToggle(String(cg.id), cg.name); });
            markers[cg.id] = marker;
            latlngs.push([cg.lat, cg.lon]);
        });
        if (latlngs.length && !parkLayer) map.fitBounds(latlngs, { padding: [40, 40], maxZoom: 12 });
    }

    function setSelected(id, isSelected) {
        var marker = markers[id];
        if (marker) marker.setStyle(markerStyle(isSelected ? 'selected' : 'default'));
    }

    var openTooltipId = null;

    function highlight(id) {
        if (openTooltipId && openTooltipId !== id) {
            var prev = markers[openTooltipId];
            if (prev) prev.closeTooltip();
        }
        var marker = markers[id];
        if (marker) {
            marker.setStyle(markerStyle('highlighted'));
            marker.openTooltip();
            openTooltipId = id;
        }
    }

    function unhighlight(id, isSelected) {
        var marker = markers[id];
        if (marker) {
            marker.setStyle(markerStyle(isSelected ? 'selected' : 'default'));
            marker.closeTooltip();
        }
        if (openTooltipId === id) openTooltipId = null;
    }

    return { init, setParks, setCampgrounds, setSelected, highlight, unhighlight, getParkNames, campgroundsInParks };
})();
