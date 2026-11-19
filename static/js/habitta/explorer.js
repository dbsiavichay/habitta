/*
 * Explorador de anuncios: filtros, resultados (tarjetas renderizadas por el servidor) y mapa.
 * Contrato: GET /api/properties/?lat&lng&radio&kind&category&purpose&address&min_price&max_price
 * Datos de la página: #search-data (categorías/propósitos) y #explorer-initial (filtros iniciales).
 */
(function () {
    'use strict';

    var habitta = window.habitta;
    var DEFAULT_CENTER = { lat: -1.8312, lng: -78.1834 }; // Ecuador

    document.addEventListener('alpine:init', function () {
        window.Alpine.data('explorer', function () {
            // Objetos de Google Maps fuera del estado reactivo de Alpine (no deben envolverse en proxies)
            var map = null;
            var maps = null;
            var markers = {};
            var clusterer = null;
            var centerMarker = null;
            var autocomplete = null;
            var userMoved = false;
            var requestId = 0;

            return {
                filters: { kind: '', purpose: '', category: '', address: '', minPrice: '', maxPrice: '', radius: '15' },
                center: null,
                placeLabel: '',
                categories: [],
                purposes: [],
                results: [],
                loading: true,
                error: false,
                view: 'map',
                mobileMap: false,
                filtersOpen: false,
                priceOpen: false,
                activeId: null,
                preview: null,
                mapStatus: 'idle', // idle | loading | ready | unavailable
                areaChanged: false,
                locating: false,

                init: function () {
                    var self = this;
                    var data = habitta.readJson('search-data');
                    var initial = habitta.readJson('explorer-initial');
                    this.categories = data.categories || [];
                    this.purposes = data.purposes || [];
                    ['kind', 'purpose', 'category', 'address', 'minPrice', 'maxPrice'].forEach(function (key) {
                        if (initial[key]) self.filters[key] = String(initial[key]);
                    });
                    if (initial.radius) this.filters.radius = String(initial.radius);
                    if (initial.lat && initial.lng) {
                        this.center = { lat: Number(initial.lat), lng: Number(initial.lng) };
                        this.placeLabel = this.filters.address || 'Zona seleccionada';
                        this.filters.address = '';
                    }
                    this.view = initial.view || 'map';

                    this.search();
                    var desktop = window.matchMedia('(min-width: 1024px)');
                    if (desktop.matches && this.view === 'map') this.ensureMap();
                    this.setupAutocomplete();

                    this.$watch('filters.kind', function () { self.normalizeSelects(); self.queueSearch(); });
                    this.$watch('filters.purpose', function () { self.normalizeSelects(); self.queueSearch(); });
                    this.$watch('filters.category', function () { self.queueSearch(); });
                    this.$watch('filters.radius', function () { if (self.center) self.queueSearch(); });
                },

                /* ---------- Filtros ---------- */
                get visibleCategories() {
                    return habitta.filterCategories(this.categories, this.filters.kind, this.filters.purpose);
                },
                get visiblePurposes() {
                    return habitta.filterPurposes(this.categories, this.purposes, this.filters.kind);
                },
                normalizeSelects: function () {
                    var f = this.filters;
                    if (f.purpose && !this.visiblePurposes.some(function (p) { return String(p.id) === f.purpose; })) f.purpose = '';
                    if (f.category && !this.visibleCategories.some(function (c) { return String(c.id) === f.category; })) f.category = '';
                },
                get activeCount() {
                    var f = this.filters;
                    return [f.kind, f.purpose, f.category, f.minPrice || f.maxPrice, this.center || f.address]
                        .filter(Boolean).length;
                },
                get priceLabel() {
                    var min = habitta.formatPrice(this.filters.minPrice);
                    var max = habitta.formatPrice(this.filters.maxPrice);
                    if (min && max) return min + ' – ' + max;
                    if (min) return 'Desde ' + min;
                    if (max) return 'Hasta ' + max;
                    return 'Precio';
                },
                nameOf: function (list, id) {
                    var item = list.find(function (x) { return String(x.id) === String(id); });
                    return item ? item.name : '';
                },
                clearPrice: function () {
                    this.filters.minPrice = '';
                    this.filters.maxPrice = '';
                    this.priceOpen = false;
                    this.search();
                },
                clearPlace: function () {
                    this.center = null;
                    this.placeLabel = '';
                    this.filters.address = '';
                    if (centerMarker) centerMarker.setMap(null);
                    this.search({ fit: true });
                },
                clearAll: function () {
                    this.filters.kind = '';
                    this.filters.purpose = '';
                    this.filters.category = '';
                    this.filters.minPrice = '';
                    this.filters.maxPrice = '';
                    this.clearPlace();
                },
                submitAddress: function () {
                    // Texto escrito sin elegir una sugerencia: se busca por dirección.
                    if (this.center && this.filters.address === '') return;
                    this.center = null;
                    this.placeLabel = '';
                    this.search({ fit: true });
                },

                /* ---------- Resultados ---------- */
                buildParams: function () {
                    var f = this.filters;
                    var params = new URLSearchParams();
                    if (f.kind) params.set('kind', f.kind);
                    if (f.purpose) params.set('purpose', f.purpose);
                    if (f.category) params.set('category', f.category);
                    if (f.minPrice) params.set('min_price', f.minPrice);
                    if (f.maxPrice) params.set('max_price', f.maxPrice);
                    if (this.center) {
                        params.set('lat', this.center.lat.toFixed(6));
                        params.set('lng', this.center.lng.toFixed(6));
                        params.set('radio', f.radius || '15');
                    } else if (f.address) {
                        params.set('address', f.address);
                    }
                    return params;
                },
                syncUrl: function () {
                    var f = this.filters;
                    var q = new URLSearchParams();
                    if (f.kind) q.set('kind', f.kind);
                    if (f.purpose) q.set('search_purpose', f.purpose);
                    if (f.category) q.set('search_category', f.category);
                    if (f.minPrice) q.set('min_price', f.minPrice);
                    if (f.maxPrice) q.set('max_price', f.maxPrice);
                    if (this.center) {
                        q.set('lat', this.center.lat.toFixed(5));
                        q.set('lng', this.center.lng.toFixed(5));
                        q.set('radius', f.radius);
                        if (this.placeLabel) q.set('search_address', this.placeLabel);
                    } else if (f.address) {
                        q.set('search_address', f.address);
                    }
                    if (this.view === 'list') q.set('view', 'list');
                    var url = window.location.pathname + (q.toString() ? '?' + q.toString() : '');
                    window.history.replaceState(null, '', url);
                },
                /* Agrupa cambios seguidos de filtros (p. ej. tipo + categoría que se limpia) en una sola petición */
                queueSearch: function () {
                    var self = this;
                    clearTimeout(this._searchTimer);
                    this._searchTimer = setTimeout(function () { self.search(); }, 150);
                },
                search: function (opts) {
                    opts = opts || {};
                    var self = this;
                    var current = ++requestId;
                    this.loading = true;
                    this.error = false;
                    this.preview = null;
                    this.syncUrl();
                    fetch('/api/properties/?' + this.buildParams().toString(), { headers: { Accept: 'application/json' } })
                        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
                        .then(function (data) {
                            if (current !== requestId) return; // respuesta vieja
                            self.results = data;
                            self.loading = false;
                            self.renderMarkers(opts.fit !== false && !opts.keepView);
                        })
                        .catch(function () {
                            if (current !== requestId) return;
                            self.loading = false;
                            self.error = true;
                        });
                },

                /* Resaltado tarjeta ↔ pin (las tarjetas vienen como HTML del servidor) */
                hoverCard: function (event) {
                    var card = event.target.closest('[data-property-id]');
                    this.setActive(card ? Number(card.dataset.propertyId) : null);
                },
                setActive: function (id) {
                    if (this.activeId === id) return;
                    var prev = this.activeId;
                    this.activeId = id;
                    if (!maps) return;
                    if (prev && markers[prev]) { markers[prev].setIcon(habitta.pinIcon(maps, false)); markers[prev].setZIndex(1); }
                    if (id && markers[id]) { markers[id].setIcon(habitta.pinIcon(maps, true)); markers[id].setZIndex(999); }
                },

                /* ---------- Vista ---------- */
                setView: function (view) {
                    this.view = view;
                    this.syncUrl();
                    if (view === 'map') this.$nextTick(this.ensureMap.bind(this));
                },
                openMobileMap: function () {
                    this.mobileMap = true;
                    var self = this;
                    this.$nextTick(function () {
                        self.ensureMap();
                        if (map) maps.event.trigger(map, 'resize');
                    });
                },

                /* ---------- Mapa ---------- */
                ensureMap: function () {
                    var self = this;
                    if (map || this.mapStatus === 'loading' || this.mapStatus === 'unavailable') return;
                    this.mapStatus = 'loading';
                    habitta.loadMaps().then(function (gmaps) {
                        maps = gmaps;
                        map = new maps.Map(self.$refs.map, {
                            center: self.center || DEFAULT_CENTER,
                            zoom: self.center ? 12 : 7,
                            styles: habitta.mapStyles,
                            disableDefaultUI: true,
                            zoomControl: true,
                            zoomControlOptions: { position: maps.ControlPosition.RIGHT_BOTTOM },
                            gestureHandling: 'greedy',
                            clickableIcons: false,
                        });
                        map.addListener('dragend', function () { userMoved = true; self.areaChanged = true; });
                        map.addListener('zoom_changed', function () { if (userMoved) self.areaChanged = true; });
                        map.addListener('click', function () { self.preview = null; self.setActive(null); });
                        self.mapStatus = 'ready';
                        self.renderMarkers(true);
                    }).catch(function () {
                        self.mapStatus = 'unavailable';
                    });
                },
                renderMarkers: function (fit) {
                    var self = this;
                    if (!map || !maps) return;
                    if (clusterer) clusterer.clearMarkers();
                    Object.keys(markers).forEach(function (id) { markers[id].setMap(null); });
                    markers = {};
                    var bounds = new maps.LatLngBounds();
                    var list = [];
                    this.results.forEach(function (item) {
                        if (!item.latitude || !item.longitude) return;
                        var position = { lat: item.latitude, lng: item.longitude };
                        var marker = new maps.Marker({ position: position, icon: habitta.pinIcon(maps, false), title: item.title || item.category, zIndex: 1 });
                        marker.addListener('click', function () {
                            self.preview = item;
                            self.setActive(item.id);
                            map.panTo(position);
                        });
                        markers[item.id] = marker;
                        list.push(marker);
                        // Coordenadas fuera de Ecuador suelen ser datos erróneos: se muestran pero no mueven el encuadre.
                        if (inEcuador(position)) bounds.extend(position);
                    });
                    if (window.markerClusterer && list.length) {
                        clusterer = new window.markerClusterer.MarkerClusterer({
                            map: map,
                            markers: list,
                            renderer: {
                                render: function (cluster) {
                                    var count = cluster.count;
                                    var size = count < 10 ? 44 : count < 50 ? 52 : 60;
                                    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size + '" viewBox="0 0 60 60">' +
                                        '<circle cx="30" cy="30" r="28" fill="#0B6E5F" fill-opacity=".22"/><circle cx="30" cy="30" r="21" fill="#0B6E5F" stroke="#fff" stroke-width="3"/></svg>';
                                    return new maps.Marker({
                                        position: cluster.position,
                                        icon: { url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg), scaledSize: new maps.Size(size, size), anchor: new maps.Point(size / 2, size / 2) },
                                        label: { text: String(count), color: '#fff', fontWeight: '800', fontSize: '13px', fontFamily: 'Plus Jakarta Sans, sans-serif' },
                                        zIndex: 1000 + count,
                                    });
                                },
                            },
                        });
                    } else {
                        list.forEach(function (m) { m.setMap(map); });
                    }
                    if (this.center) {
                        if (!centerMarker) {
                            centerMarker = new maps.Marker({
                                map: map,
                                clickable: false,
                                zIndex: 2000,
                                icon: { path: maps.SymbolPath.CIRCLE, scale: 8, fillColor: '#2F80ED', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 3 },
                            });
                        }
                        centerMarker.setPosition(this.center);
                        centerMarker.setMap(map);
                        bounds.extend(this.center);
                    }
                    if (fit && !bounds.isEmpty()) {
                        userMoved = false;
                        map.fitBounds(bounds, 64);
                        maps.event.addListenerOnce(map, 'idle', function () {
                            if (map.getZoom() > 15) map.setZoom(15);
                            self.areaChanged = false;
                        });
                    }
                },
                searchThisArea: function () {
                    if (!map) return;
                    var c = map.getCenter();
                    var ne = map.getBounds().getNorthEast();
                    this.center = { lat: c.lat(), lng: c.lng() };
                    this.placeLabel = 'Zona del mapa';
                    this.filters.address = '';
                    this.filters.radius = String(Math.max(1, Math.ceil(haversineKm(this.center, { lat: ne.lat(), lng: ne.lng() }))));
                    this.areaChanged = false;
                    this.search({ keepView: true });
                },
                locateMe: function () {
                    var self = this;
                    if (!navigator.geolocation) return;
                    this.locating = true;
                    navigator.geolocation.getCurrentPosition(function (pos) {
                        self.locating = false;
                        self.center = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                        self.placeLabel = 'Cerca de ti';
                        self.filters.address = '';
                        self.search({ fit: true });
                    }, function () {
                        self.locating = false;
                        window.alert('No pudimos obtener tu ubicación. Revisa los permisos del navegador.');
                    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
                },
                setupAutocomplete: function () {
                    var self = this;
                    var input = this.$refs.address;
                    if (!input) return;
                    habitta.loadMaps().then(function (gmaps) {
                        maps = gmaps;
                        if (!gmaps.places) return;
                        autocomplete = new gmaps.places.Autocomplete(input, {
                            componentRestrictions: { country: 'ec' },
                            fields: ['formatted_address', 'geometry', 'name'],
                        });
                        autocomplete.addListener('place_changed', function () {
                            var place = autocomplete.getPlace();
                            if (!place.geometry) return;
                            var loc = place.geometry.location;
                            self.center = { lat: loc.lat(), lng: loc.lng() };
                            self.placeLabel = place.name || place.formatted_address;
                            self.filters.address = '';
                            input.value = '';
                            self.search({ fit: true });
                        });
                    }).catch(function () {});
                },
            };
        });
    });

    function inEcuador(p) {
        return p.lat > -6 && p.lat < 2.5 && p.lng > -93 && p.lng < -74;
    }

    function haversineKm(a, b) {
        var R = 6371;
        var dLat = (b.lat - a.lat) * Math.PI / 180;
        var dLng = (b.lng - a.lng) * Math.PI / 180;
        var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return 2 * R * Math.asin(Math.sqrt(h));
    }
})();
