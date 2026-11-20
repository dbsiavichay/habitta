/*
 * Explorador de anuncios: filtros, resultados (tarjetas renderizadas por el servidor) y mapa.
 * Contrato: GET /api/properties/?lat&lng&radio&kind&category&purpose&address&min_price&max_price
 * Datos de la página: #search-data (categorías/propósitos) y #explorer-initial (filtros iniciales).
 */
(function () {
    'use strict';

    var habitta = window.habitta;
    var BRAND = '#0B6E5F';

    document.addEventListener('alpine:init', function () {
        window.Alpine.data('explorer', function () {
            // Objetos de MapLibre fuera del estado reactivo de Alpine (no deben envolverse en proxies)
            var map = null;
            var maplibregl = null;
            var centerMarker = null;
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
                    if (centerMarker) centerMarker.remove();
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
                            self.renderResults(opts.fit !== false && !opts.keepView);
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
                    this.activeId = id;
                    this.drawActive();
                },
                /* El pin activo va en su propia fuente (sin agrupar): se ve aunque su anuncio esté en un grupo */
                drawActive: function () {
                    if (!map || this.mapStatus !== 'ready') return;
                    var id = this.activeId;
                    var item = id && this.results.find(function (r) { return r.id === id; });
                    map.getSource('active').setData(item && hasPoint(item)
                        ? { type: 'FeatureCollection', features: [toFeature(item)] }
                        : habitta.EMPTY_GEOJSON);
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
                        if (map) map.resize();
                    });
                },

                /* ---------- Mapa ---------- */
                ensureMap: function () {
                    var self = this;
                    if (map || this.mapStatus === 'loading' || this.mapStatus === 'unavailable') return;
                    this.mapStatus = 'loading';
                    var fail = function (error) {
                        habitta.mapError(error);
                        self.mapStatus = 'unavailable';
                    };
                    habitta.loadMaps().then(function (lib) {
                        maplibregl = lib;
                        map = habitta.createMap(lib, self.$refs.map, { center: self.center, zoom: self.center ? 12 : 6 });
                        habitta.whenMapReady(map, function () {
                            habitta.addPinImages(map).then(function () {
                                self.addLayers();
                                self.mapStatus = 'ready';
                                self.renderResults(true);
                            }).catch(fail);
                        }, fail);
                    }).catch(fail);
                },
                addLayers: function () {
                    var self = this;
                    var symbol = { 'icon-anchor': 'bottom', 'icon-allow-overlap': true, 'icon-ignore-placement': true };
                    var isCluster = ['has', 'point_count'];
                    map.addSource('results', { type: 'geojson', data: habitta.EMPTY_GEOJSON, cluster: true, clusterRadius: 50, clusterMaxZoom: 14 });
                    map.addSource('active', { type: 'geojson', data: habitta.EMPTY_GEOJSON });
                    map.addLayer({
                        id: 'cluster-halo', type: 'circle', source: 'results', filter: isCluster,
                        paint: { 'circle-color': BRAND, 'circle-opacity': 0.22, 'circle-radius': ['step', ['get', 'point_count'], 22, 10, 26, 50, 30] },
                    });
                    map.addLayer({
                        id: 'clusters', type: 'circle', source: 'results', filter: isCluster,
                        paint: {
                            'circle-color': BRAND, 'circle-stroke-color': '#fff', 'circle-stroke-width': 3,
                            'circle-radius': ['step', ['get', 'point_count'], 16, 10, 19, 50, 22],
                        },
                    });
                    // La fuente del conteo tiene que existir en los glifos del estilo (OpenFreeMap: Noto Sans)
                    map.addLayer({
                        id: 'cluster-count', type: 'symbol', source: 'results', filter: isCluster,
                        layout: {
                            'text-field': ['get', 'point_count_abbreviated'], 'text-font': ['Noto Sans Bold'], 'text-size': 13,
                            'text-allow-overlap': true, 'text-ignore-placement': true,
                        },
                        paint: { 'text-color': '#fff' },
                    });
                    map.addLayer({ id: 'pins', type: 'symbol', source: 'results', filter: ['!', isCluster], layout: Object.assign({ 'icon-image': 'pin' }, symbol) });
                    map.addLayer({ id: 'pin-active', type: 'symbol', source: 'active', layout: Object.assign({ 'icon-image': 'pin-active' }, symbol) });

                    map.on('click', function (event) {
                        var hit = map.queryRenderedFeatures(event.point, { layers: ['pin-active', 'pins', 'clusters'] })[0];
                        if (!hit) {
                            self.preview = null;
                            self.setActive(null);
                        } else if (hit.layer.id === 'clusters') {
                            map.getSource('results').getClusterExpansionZoom(hit.properties.cluster_id).then(function (zoom) {
                                map.easeTo({ center: hit.geometry.coordinates, zoom: zoom });
                            });
                        } else {
                            var id = hit.properties.id;
                            var item = self.results.find(function (r) { return r.id === id; });
                            if (!item) return;
                            self.preview = item;
                            self.setActive(id);
                            map.panTo([item.longitude, item.latitude]);
                        }
                    });
                    ['clusters', 'pins', 'pin-active'].forEach(function (layer) {
                        map.on('mouseenter', layer, function () { map.getCanvas().style.cursor = 'pointer'; });
                        map.on('mouseleave', layer, function () { map.getCanvas().style.cursor = ''; });
                    });
                    // Sólo los movimientos del usuario (no los de fitBounds/easeTo) ofrecen «Buscar en esta zona»
                    map.on('dragend', function () { self.areaChanged = true; });
                    map.on('zoomend', function (event) { if (event.originalEvent) self.areaChanged = true; });
                },
                renderResults: function (fit) {
                    if (!map || this.mapStatus !== 'ready') return;
                    var bounds = new maplibregl.LngLatBounds();
                    var features = [];
                    this.results.forEach(function (item) {
                        if (!hasPoint(item)) return;
                        features.push(toFeature(item));
                        // Coordenadas fuera de Ecuador suelen ser datos erróneos: se muestran pero no mueven el encuadre.
                        if (inEcuador(item)) bounds.extend([item.longitude, item.latitude]);
                    });
                    map.getSource('results').setData({ type: 'FeatureCollection', features: features });
                    this.drawActive();
                    if (this.center) {
                        if (!centerMarker) centerMarker = new maplibregl.Marker({ element: centerDot() });
                        centerMarker.setLngLat([this.center.lng, this.center.lat]).addTo(map);
                        bounds.extend([this.center.lng, this.center.lat]);
                    } else if (centerMarker) {
                        centerMarker.remove();
                    }
                    if (fit && !bounds.isEmpty()) {
                        map.fitBounds(bounds, { padding: 64, maxZoom: 15 });
                        this.areaChanged = false;
                    }
                },
                searchThisArea: function () {
                    if (!map) return;
                    var c = map.getCenter();
                    var ne = map.getBounds().getNorthEast();
                    this.center = { lat: c.lat, lng: c.lng };
                    this.placeLabel = 'Zona del mapa';
                    this.filters.address = '';
                    this.filters.radius = String(Math.max(1, Math.ceil(haversineKm(this.center, { lat: ne.lat, lng: ne.lng }))));
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

                /* ---------- Buscador de lugares (placeSearch) ---------- */
                pickPlace: function (place) {
                    this.center = { lat: place.lat, lng: place.lng };
                    this.placeLabel = place.name;
                    this.filters.address = '';
                    document.getElementById('explorer-address').value = '';
                    this.search({ fit: true });
                },
                /* Prioriza lugares cerca de lo que se está viendo (sólo con el mapa acercado: el centro de Ecuador no dice nada) */
                nearCenter: function () {
                    if (map && this.mapStatus === 'ready' && map.getZoom() >= 9) {
                        var c = map.getCenter();
                        return { lat: c.lat, lng: c.lng };
                    }
                    return this.center;
                },
            };
        });
    });

    function hasPoint(item) {
        return !!(item.latitude && item.longitude);
    }

    function toFeature(item) {
        return { type: 'Feature', properties: { id: item.id }, geometry: { type: 'Point', coordinates: [item.longitude, item.latitude] } };
    }

    /* Punto azul de «aquí buscas» (centro de la búsqueda por zona) */
    function centerDot() {
        var el = document.createElement('div');
        el.setAttribute('aria-hidden', 'true');
        el.style.cssText = 'width:18px;height:18px;border-radius:9999px;background:#2F80ED;border:3px solid #fff;' +
            'box-shadow:0 0 0 6px rgba(47,128,237,.2);pointer-events:none';
        return el;
    }

    function inEcuador(item) {
        return item.latitude > -6 && item.latitude < 2.5 && item.longitude > -93 && item.longitude < -74;
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
