/*
 * Habitta: utilidades globales y componentes Alpine reutilizables.
 * Se carga en todas las páginas (layouts/base.html) antes que Alpine.
 */
(function () {
    'use strict';

    var habitta = (window.habitta = window.habitta || {});

    /* ---------- Formato de precios (igual que el filtro |money de Django) ---------- */
    habitta.formatPrice = function (value) {
        if (value === null || value === undefined || value === '') return null;
        var n = Number(value);
        if (!isFinite(n)) return null;
        var hasCents = Math.round(n * 100) % 100 !== 0;
        return '$' + n.toLocaleString('es-EC', {
            minimumFractionDigits: hasCents ? 2 : 0,
            maximumFractionDigits: hasCents ? 2 : 0,
        });
    };

    habitta.escapeHtml = function (value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    };

    habitta.readJson = function (id) {
        var el = document.getElementById(id);
        try { return el ? JSON.parse(el.textContent) : {}; } catch (e) { return {}; }
    };

    /* Categorías visibles para un tipo (1 inmuebles, 2 servicios, 3 empleos) y un propósito */
    habitta.filterCategories = function (categories, kind, purpose) {
        return categories.filter(function (c) {
            return (!kind || String(c.kind) === String(kind)) &&
                (!purpose || c.purposes.indexOf(Number(purpose)) !== -1);
        });
    };

    /* Propósitos que usa al menos una categoría del tipo elegido */
    habitta.filterPurposes = function (categories, purposes, kind) {
        if (!kind) return purposes;
        var used = {};
        categories.forEach(function (c) {
            if (String(c.kind) === String(kind)) c.purposes.forEach(function (id) { used[id] = true; });
        });
        return purposes.filter(function (p) { return used[p.id]; });
    };

    /* ---------- Mapas: MapLibre con un estilo vectorial libre (OpenFreeMap), sin key ---------- */
    var BRAND = '#0B6E5F';
    var BRAND_ACTIVE = '#C8502E';
    habitta.DEFAULT_CENTER = { lat: -1.8312, lng: -78.1834 }; // Ecuador completo
    habitta.EMPTY_GEOJSON = { type: 'FeatureCollection', features: [] };

    function loadAsset(tag, attrs) {
        return new Promise(function (resolve, reject) {
            var el = document.createElement(tag);
            Object.keys(attrs).forEach(function (name) { el[name] = attrs[name]; });
            el.onload = resolve;
            el.onerror = function () { reject(new Error('No se pudo cargar ' + (attrs.src || attrs.href))); };
            document.head.appendChild(el);
        });
    }

    /* Carga perezosa de MapLibre (JS + CSS, una sola vez por página); resuelve `maplibregl` */
    var mapsPromise = null;
    habitta.loadMaps = function () {
        if (mapsPromise) return mapsPromise;
        var meta = document.querySelector('meta[name="habitta:maps"]');
        if (!meta) return Promise.reject(new Error('Los mapas no están configurados'));
        mapsPromise = Promise.all([
            window.maplibregl ? null : loadAsset('script', { src: meta.dataset.js, async: true }),
            loadAsset('link', { rel: 'stylesheet', href: meta.dataset.css }),
        ]).then(function () {
            if (!window.maplibregl) throw new Error('No se pudo cargar el mapa');
            return window.maplibregl;
        });
        mapsPromise.catch(function () { mapsPromise = null; }); // se puede reintentar
        return mapsPromise;
    };

    var MAP_LOCALE = {
        'NavigationControl.ZoomIn': 'Acercar',
        'NavigationControl.ZoomOut': 'Alejar',
        'NavigationControl.ResetBearing': 'Restablecer la orientación',
        'FullscreenControl.Enter': 'Pantalla completa',
        'FullscreenControl.Exit': 'Salir de pantalla completa',
        'AttributionControl.ToggleAttribution': 'Créditos del mapa',
        'AttributionControl.MapFeedback': 'Reportar un error en el mapa',
        'Map.Title': 'Mapa',
        'Marker.Title': 'Marcador',
        'Popup.Close': 'Cerrar',
        'CooperativeGesturesHandler.WindowsHelpText': 'Mantén Ctrl y usa la rueda para hacer zoom',
        'CooperativeGesturesHandler.MacHelpText': 'Mantén ⌘ y usa la rueda para hacer zoom',
        'CooperativeGesturesHandler.MobileHelpText': 'Usa dos dedos para mover el mapa',
    };

    /* Tintes de la marca sobre el estilo (ids de capa de OpenFreeMap; los que no existan se ignoran) */
    var MAP_TINTS = {
        water: { 'fill-color': '#bfdcd6' },
        waterway: { 'line-color': '#a9cfc8' },
        park: { 'fill-color': '#d9eadf' },
        landcover_wood: { 'fill-color': '#e1ebe3' },
        highway_motorway_inner: { 'line-color': '#f3e3c3' },
        highway_motorway_bridge_inner: { 'line-color': '#f3e3c3' },
    };

    function tintStyle(map) {
        var style = map.getStyle();
        (style.layers || []).forEach(function (layer) {
            var paint = MAP_TINTS[layer.id];
            if (paint) Object.keys(paint).forEach(function (prop) { map.setPaintProperty(layer.id, prop, paint[prop]); });
            // Sin puntos de interés: los pines de la marca deben destacar
            if (layer['source-layer'] === 'poi') map.setLayoutProperty(layer.id, 'visibility', 'none');
        });
        // Positron sólo pinta parques nacionales y reservas; los urbanos están en landcover (clase grass)
        if (style.sources && style.sources.openmaptiles && map.getLayer('park') && !map.getLayer('landcover_grass')) {
            map.addLayer({
                id: 'habitta-parks', type: 'fill', source: 'openmaptiles', 'source-layer': 'landcover',
                filter: ['all', ['==', ['get', 'class'], 'grass'],
                    ['in', ['get', 'subclass'], ['literal', ['park', 'garden', 'village_green', 'recreation_ground']]]],
                paint: { 'fill-color': MAP_TINTS.park['fill-color'] },
            }, map.getLayer('water') ? 'water' : undefined);
        }
    }

    /*
     * Mapa con el estilo de la marca, sin rotación y con controles en español.
     * opts: center {lat, lng}, zoom, cooperative (Ctrl + rueda / dos dedos), fullscreen.
     * Lanza un error si el navegador no tiene WebGL: quien lo llame muestra «mapa no disponible».
     */
    habitta.createMap = function (maplibregl, container, opts) {
        opts = opts || {};
        var center = opts.center || habitta.DEFAULT_CENTER;
        var map = new maplibregl.Map({
            container: container,
            style: document.querySelector('meta[name="habitta:maps"]').content,
            center: [center.lng, center.lat],
            zoom: opts.zoom || 6,
            attributionControl: {}, // créditos completos en mapas anchos; plegables (ⓘ) en los angostos
            cooperativeGestures: !!opts.cooperative,
            dragRotate: false,
            pitchWithRotate: false,
            touchPitch: false,
            locale: MAP_LOCALE,
        });
        map.touchZoomRotate.disableRotation();
        map.keyboard.disableRotation();
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
        if (opts.fullscreen) map.addControl(new maplibregl.FullscreenControl(), 'top-right');
        map.on('style.load', function () { tintStyle(map); });
        return map;
    };

    /* onReady cuando el mapa terminó de cargar; onError si el estilo no llega (sin conexión o servicio caído) */
    habitta.whenMapReady = function (map, onReady, onError) {
        var styleLoaded = false;
        var failed = false;
        map.once('style.load', function () { styleLoaded = true; });
        map.once('load', function () { if (!failed) onReady(); });
        map.on('error', function (event) {
            if (styleLoaded || failed) return; // un tile que falla no invalida el mapa
            failed = true;
            onError(event && event.error);
        });
    };

    /* Deja en la consola por qué no se pudo mostrar el mapa (sin WebGL, sin conexión, estilo caído…) */
    habitta.mapError = function (error) {
        if (window.console) console.warn('Habitta: el mapa no está disponible.', error || '');
    };

    /* Pin SVG con el color de la marca (normal: verde, activo: terracota y más grande) */
    function pinSvg(active, width, height) {
        return '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '" viewBox="0 0 36 46">' +
            '<path d="M18 45s15-15.2 15-27A15 15 0 0 0 3 18c0 11.8 15 27 15 27z" fill="' + (active ? BRAND_ACTIVE : BRAND) + '" stroke="#fff" stroke-width="2.5"/>' +
            '<circle cx="18" cy="18" r="5.5" fill="#fff"/></svg>';
    }

    function pinSize(active) {
        return active ? [42, 54] : [36, 46];
    }

    /* Pin como elemento DOM para maplibregl.Marker (anchor: 'bottom') */
    habitta.pinElement = function (active) {
        var size = pinSize(active);
        var el = document.createElement('div');
        el.style.width = size[0] + 'px';
        el.style.height = size[1] + 'px';
        el.innerHTML = pinSvg(active, size[0], size[1]);
        return el;
    };

    /* Imágenes 'pin' y 'pin-active' (a 2x) para capas de símbolos */
    habitta.addPinImages = function (map) {
        return Promise.all([false, true].map(function (active) {
            var name = active ? 'pin-active' : 'pin';
            var size = pinSize(active);
            var image = new Image(size[0] * 2, size[1] * 2);
            image.src = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(pinSvg(active, size[0] * 2, size[1] * 2));
            return image.decode().then(function () {
                var canvas = document.createElement('canvas');
                canvas.width = image.width;
                canvas.height = image.height;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
                if (!map.hasImage(name)) map.addImage(name, ctx.getImageData(0, 0, canvas.width, canvas.height), { pixelRatio: 2 });
            });
        }));
    };

    /* Círculo de `meters` alrededor de center {lat, lng} como polígono GeoJSON, y sus límites */
    function circleDeltas(center, meters) {
        var dLat = meters / 111320;
        return [dLat, dLat / Math.max(Math.cos(center.lat * Math.PI / 180), 0.01)];
    }

    habitta.circle = function (center, meters) {
        var d = circleDeltas(center, meters);
        var ring = [];
        for (var i = 0; i <= 64; i++) {
            var angle = (i / 64) * 2 * Math.PI;
            ring.push([center.lng + d[1] * Math.cos(angle), center.lat + d[0] * Math.sin(angle)]);
        }
        return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [ring] } };
    };

    habitta.circleBounds = function (center, meters) {
        var d = circleDeltas(center, meters);
        return [[center.lng - d[1], center.lat - d[0]], [center.lng + d[1], center.lat + d[0]]];
    };

    /* Capa del radio de cobertura (relleno + borde). Devuelve update(center, meters); sin center la vacía. */
    habitta.addCoverageLayer = function (map) {
        map.addSource('coverage', { type: 'geojson', data: habitta.EMPTY_GEOJSON });
        map.addLayer({ id: 'coverage-fill', type: 'fill', source: 'coverage', paint: { 'fill-color': BRAND, 'fill-opacity': 0.12 } });
        map.addLayer({ id: 'coverage-line', type: 'line', source: 'coverage', paint: { 'line-color': BRAND, 'line-opacity': 0.75, 'line-width': 2 } });
        return function (center, meters) {
            map.getSource('coverage').setData(center ? habitta.circle(center, meters) : habitta.EMPTY_GEOJSON);
        };
    };

    /* ---------- Lugares (OpenStreetMap vía /api/places/, ver api/geocoding.py) ---------- */
    function getJson(url) {
        return fetch(url, { headers: { Accept: 'application/json' } }).then(function (r) {
            if (!r.ok) throw new Error(r.status);
            return r.json();
        });
    }

    habitta.places = {
        /* [{name, detail, label, lat, lng}]; near {lat, lng} prioriza lo cercano */
        search: function (query, near) {
            var params = new URLSearchParams({ q: query });
            if (near) {
                params.set('lat', near.lat.toFixed(3));
                params.set('lng', near.lng.toFixed(3));
            }
            return getJson('/api/places/?' + params.toString());
        },
        /* Dirección del punto (o «ciudad, provincia» con zone); null si no se encuentra */
        reverse: function (lat, lng, zone) {
            var params = new URLSearchParams({ lat: lat.toFixed(6), lng: lng.toFixed(6) });
            if (zone) params.set('zone', '1');
            return getJson('/api/places/reverse/?' + params.toString()).then(function (data) { return data.label; });
        },
    };

    /* ---------- Componentes Alpine ---------- */
    document.addEventListener('alpine:init', function () {
        var Alpine = window.Alpine;

        /* Navbar: se vuelve sólida al hacer scroll (modo overlay en la home) */
        Alpine.data('navbar', function (overlay) {
            return {
                overlay: !!overlay,
                scrolled: false,
                init: function () {
                    var self = this;
                    var update = function () { self.scrolled = window.scrollY > 24; };
                    update();
                    window.addEventListener('scroll', update, { passive: true });
                },
                get solid() { return !this.overlay || this.scrolled; },
            };
        });

        /* Tema: sistema → claro → oscuro (se guarda en este navegador) */
        Alpine.data('themeToggle', function () {
            return {
                theme: document.documentElement.dataset.theme || 'system',
                get label() {
                    return { system: 'Tema del sistema', habitta: 'Tema claro', 'habitta-dark': 'Tema oscuro' }[this.theme];
                },
                cycle: function () {
                    var order = ['system', 'habitta', 'habitta-dark'];
                    this.theme = order[(order.indexOf(this.theme) + 1) % order.length];
                    try {
                        if (this.theme === 'system') {
                            delete document.documentElement.dataset.theme;
                            localStorage.removeItem('habitta-theme');
                        } else {
                            document.documentElement.dataset.theme = this.theme;
                            localStorage.setItem('habitta-theme', this.theme);
                        }
                    } catch (e) {}
                },
            };
        });

        /* Mostrar u ocultar una contraseña (plantilla hydra/forms/passwordinput.html) */
        Alpine.data('passwordToggle', function () {
            return {
                show: false,
                toggle: function () {
                    this.show = !this.show;
                    var input = this.$root.querySelector('input');
                    if (input) input.type = this.show ? 'text' : 'password';
                },
            };
        });

        /* Toast que se cierra solo */
        Alpine.data('toast', function (delay) {
            return {
                open: true,
                init: function () {
                    var self = this;
                    setTimeout(function () { self.open = false; }, delay || 6000);
                },
            };
        });

        /* Carrusel horizontal con scroll-snap y flechas */
        Alpine.data('carousel', function () {
            return {
                atStart: true,
                atEnd: false,
                init: function () {
                    var self = this;
                    this.$nextTick(function () { self.update(); });
                    this.$refs.track.addEventListener('scroll', function () { self.update(); }, { passive: true });
                    window.addEventListener('resize', function () { self.update(); }, { passive: true });
                },
                update: function () {
                    var t = this.$refs.track;
                    this.atStart = t.scrollLeft <= 4;
                    this.atEnd = t.scrollLeft + t.clientWidth >= t.scrollWidth - 4;
                },
                scroll: function (dir) {
                    var t = this.$refs.track;
                    t.scrollBy({ left: dir * t.clientWidth * 0.85, behavior: 'smooth' });
                },
            };
        });

        /* Cuenta regresiva (subastas) */
        Alpine.data('countdown', function (endIso) {
            return {
                end: new Date(endIso).getTime(),
                d: '00', h: '00', m: '00', s: '00',
                done: false,
                init: function () {
                    var self = this;
                    this.tick();
                    var timer = setInterval(function () {
                        self.tick();
                        if (self.done) clearInterval(timer);
                    }, 1000);
                },
                tick: function () {
                    var diff = Math.max(0, this.end - Date.now());
                    this.done = diff === 0;
                    var pad = function (n) { return String(n).padStart(2, '0'); };
                    this.d = pad(Math.floor(diff / 86400000));
                    this.h = pad(Math.floor(diff / 3600000) % 24);
                    this.m = pad(Math.floor(diff / 60000) % 60);
                    this.s = pad(Math.floor(diff / 1000) % 60);
                },
            };
        });

        /* Compartir: Web Share API nativa y, si no existe, copiar enlace */
        Alpine.data('share', function (title, url) {
            return {
                copied: false,
                url: url || window.location.href,
                get canShare() { return !!navigator.share; },
                get whatsappUrl() {
                    return 'https://wa.me/?text=' + encodeURIComponent(title + ' ' + this.url);
                },
                share: function () {
                    if (navigator.share) {
                        navigator.share({ title: title, url: this.url }).catch(function () {});
                    } else {
                        this.copy();
                    }
                },
                copy: function () {
                    var self = this;
                    navigator.clipboard.writeText(this.url).then(function () {
                        self.copied = true;
                        setTimeout(function () { self.copied = false; }, 2200);
                    });
                },
            };
        });

        /* Lector de códigos QR de los afiches: el script (1.5 MB) se carga sólo al abrirlo */
        Alpine.data('qrScanner', function (scriptUrl) {
            return {
                status: 'idle',
                scanner: null,
                open: function () {
                    this.$refs.dialog.showModal();
                    this.start();
                },
                close: function () {
                    if (this.scanner) this.scanner.stop();
                    this.$refs.dialog.close();
                },
                start: function () {
                    var self = this;
                    this.status = 'loading';
                    var run = function () {
                        self.scanner = new window.Instascan.Scanner({ video: self.$refs.video, mirror: false });
                        self.scanner.addListener('scan', function (content) {
                            // Sólo se siguen códigos que apunten a este mismo sitio.
                            try {
                                var target = new URL(content, window.location.origin);
                                if (target.origin === window.location.origin) window.location.href = target.href;
                            } catch (e) {}
                        });
                        window.Instascan.Camera.getCameras().then(function (cameras) {
                            if (!cameras.length) { self.status = 'nocamera'; return; }
                            self.scanner.start(cameras[cameras.length - 1]);
                            self.status = 'scanning';
                        }).catch(function () { self.status = 'denied'; });
                    };
                    if (window.Instascan) { run(); return; }
                    var s = document.createElement('script');
                    s.src = scriptUrl;
                    s.onload = run;
                    s.onerror = function () { self.status = 'error'; };
                    document.head.appendChild(s);
                },
            };
        });

        /* Diálogo de confirmación del panel (<c-confirm-dialog>): lo abre $dispatch('confirm', {...}) */
        Alpine.data('confirmDialog', function () {
            return {
                action: '',
                title: '',
                text: '',
                button: 'Eliminar',
                show: function (detail) {
                    detail = detail || {};
                    this.action = detail.action || '';
                    this.title = detail.title || '¿Seguro?';
                    this.text = detail.text || '';
                    this.button = detail.button || 'Eliminar';
                    if (this.action) this.$root.showModal();
                },
                close: function () { this.$root.close(); },
            };
        });

        /* Copiar un texto (número de cuenta, enlace) con confirmación visual */
        Alpine.data('copyText', function (text) {
            return {
                copied: false,
                copy: function () {
                    var self = this;
                    if (!navigator.clipboard) return;
                    navigator.clipboard.writeText(text).then(function () {
                        self.copied = true;
                        setTimeout(function () { self.copied = false; }, 1800);
                    });
                },
            };
        });

        /*
         * Chat en tiempo real con otro usuario (WebSocket de Django Channels).
         * En el widget flotante conecta al abrirse; en la página de conversación ({autoconnect: true}) al cargar.
         */
        Alpine.data('chatWidget', function (receiverId, options) {
            var socket = null;
            var pending = []; // mensajes escritos antes de que el WebSocket termine de abrir
            options = options || {};
            return {
                open: false,
                draft: '',
                status: 'idle', // idle | connecting | online | offline
                init: function () {
                    if (!options.autoconnect) return;
                    this.connect();
                    var self = this;
                    this.$nextTick(function () { self.scrollDown(); });
                },
                toggle: function () {
                    this.open = !this.open;
                    if (this.open) this.connect();
                    var self = this;
                    this.$nextTick(function () {
                        self.scrollDown();
                        if (self.$refs.input) self.$refs.input.focus();
                    });
                },
                connect: function () {
                    var self = this;
                    if (socket || !receiverId) return;
                    this.status = 'connecting';
                    var scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
                    socket = new WebSocket(scheme + window.location.host + '/ws/message/' + encodeURIComponent(receiverId) + '/');
                    socket.onopen = function () {
                        self.status = 'online';
                        while (pending.length) socket.send(JSON.stringify({ message: pending.shift() }));
                    };
                    socket.onclose = function () { self.status = 'offline'; socket = null; };
                    socket.onmessage = function (event) {
                        var data = JSON.parse(event.data);
                        // HTML renderizado y escapado por el servidor
                        self.$refs.messages.insertAdjacentHTML('beforeend', data.bubble);
                        var empty = self.$refs.messages.querySelector('[data-empty]');
                        if (empty) empty.remove();
                        self.scrollDown();
                    };
                },
                send: function () {
                    var text = this.draft.trim();
                    if (!text) return;
                    this.draft = '';
                    if (!socket || socket.readyState !== WebSocket.OPEN) {
                        pending.push(text);
                        this.connect();
                        return;
                    }
                    socket.send(JSON.stringify({ message: text }));
                },
                scrollDown: function () {
                    var box = this.$refs.messages;
                    if (box) box.scrollTop = box.scrollHeight;
                },
            };
        });
        /*
         * Autocompletado de lugares sobre el input que haya dentro del componente (o el de options.input).
         * La lista va en <c-place-suggestions /> dentro del mismo elemento (que debe ser `relative`).
         * Al elegir un lugar emite `place-selected` con {name, detail, label, lat, lng}.
         * options.near: función que devuelve {lat, lng} para priorizar resultados cercanos.
         * Los nombres llevan prefijo para no tapar datos ni métodos de los componentes que lo contienen.
         */
        Alpine.data('placeSearch', function (options) {
            options = options || {};
            var input = null;
            var timer = null;
            var requestSeq = 0;
            return {
                suggestOpen: false,
                suggestions: [],
                suggestIndex: -1,
                suggestId: '',
                suggestPicked: '',
                init: function () {
                    var self = this;
                    input = this.$root.querySelector(options.input || 'input:not([type="hidden"])');
                    if (!input) return;
                    this.suggestId = this.$id('lugares');
                    input.setAttribute('role', 'combobox');
                    input.setAttribute('aria-autocomplete', 'list');
                    input.setAttribute('aria-controls', this.suggestId);
                    input.setAttribute('aria-expanded', 'false');
                    input.setAttribute('autocomplete', 'off');
                    input.addEventListener('input', function () { self.suggestType(); });
                    input.addEventListener('keydown', function (event) { self.suggestKey(event); });
                    input.addEventListener('blur', function () { self.suggestClose(); });
                    input.addEventListener('focus', function () {
                        if (input.value.trim() !== self.suggestPicked) self.suggestShow();
                    });
                    this.$watch('suggestIndex', function (i) {
                        if (i >= 0) input.setAttribute('aria-activedescendant', self.suggestId + '-' + i);
                        else input.removeAttribute('aria-activedescendant');
                    });
                },
                suggestShow: function () {
                    this.suggestOpen = this.suggestions.length > 0;
                    input.setAttribute('aria-expanded', String(this.suggestOpen));
                },
                suggestClose: function () {
                    this.suggestOpen = false;
                    this.suggestIndex = -1;
                    if (input) input.setAttribute('aria-expanded', 'false');
                },
                suggestType: function () {
                    var self = this;
                    var query = input.value.trim();
                    clearTimeout(timer);
                    if (query === this.suggestPicked) return; // el valor lo puso choosePlace()
                    this.suggestPicked = '';
                    if (query.length < 3) {
                        requestSeq++;
                        this.suggestions = [];
                        this.suggestClose();
                        return;
                    }
                    timer = setTimeout(function () {
                        var current = ++requestSeq;
                        var near = typeof options.near === 'function' ? options.near() : null;
                        habitta.places.search(query, near).then(function (places) {
                            if (current !== requestSeq) return; // respuesta vieja
                            self.suggestions = places;
                            self.suggestIndex = -1;
                            if (document.activeElement === input) self.suggestShow();
                        }).catch(function () {});
                    }, 300);
                },
                suggestKey: function (event) {
                    var count = this.suggestions.length;
                    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                        if (!count) return;
                        event.preventDefault();
                        if (!this.suggestOpen) this.suggestShow();
                        // Recorre -1 (el texto escrito) y 0..count-1
                        var step = event.key === 'ArrowDown' ? 1 : -1;
                        this.suggestIndex = ((this.suggestIndex + 1 + step) % (count + 1) + count + 1) % (count + 1) - 1;
                    } else if (event.key === 'Enter') {
                        if (this.suggestOpen && this.suggestIndex >= 0) {
                            event.preventDefault();
                            this.choosePlace(this.suggestions[this.suggestIndex]);
                        } else {
                            this.suggestClose();
                        }
                    } else if (event.key === 'Escape' && this.suggestOpen) {
                        event.preventDefault();
                        this.suggestClose();
                    }
                },
                choosePlace: function (place) {
                    clearTimeout(timer);
                    requestSeq++;
                    this.suggestPicked = place.label;
                    input.value = place.label;
                    this.suggestClose();
                    this.$root.dispatchEvent(new CustomEvent('place-selected', { detail: place, bubbles: true }));
                },
            };
        });

        /*
         * Buscador del hero: pestañas por tipo (inmuebles/servicios/empleos), categorías filtradas
         * por tipo y propósito, y lugar con autocompletado (placeSearch): si se elige una sugerencia,
         * el explorador abre centrado en ella (lat/lng); si no, busca el texto en las direcciones.
         */
        Alpine.data('heroSearch', function (initial) {
            initial = initial || {};
            return {
                kind: initial.kind || '',
                purpose: initial.purpose || '',
                category: initial.category || '',
                categories: [],
                purposes: [],
                lat: '',
                lng: '',
                placeLabel: '',
                init: function () {
                    var data = habitta.readJson('search-data');
                    this.categories = data.categories || [];
                    this.purposes = data.purposes || [];
                },
                pickPlace: function (place) {
                    this.lat = place.lat;
                    this.lng = place.lng;
                    this.placeLabel = place.label;
                },
                typedPlace: function (event) {
                    if (event.target.value.trim() === this.placeLabel) return;
                    this.lat = '';
                    this.lng = '';
                    this.placeLabel = '';
                },
                get visibleCategories() {
                    return habitta.filterCategories(this.categories, this.kind, this.purpose);
                },
                get visiblePurposes() {
                    return habitta.filterPurposes(this.categories, this.purposes, this.kind);
                },
                setKind: function (kind) {
                    this.kind = kind;
                    var self = this;
                    if (this.purpose && !this.visiblePurposes.some(function (p) { return String(p.id) === String(self.purpose); })) {
                        this.purpose = '';
                    }
                    if (this.category && !this.visibleCategories.some(function (c) { return String(c.id) === String(self.category); })) {
                        this.category = '';
                    }
                },
            };
        });
    });
})();
