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

    /* ---------- Carga perezosa de Google Maps (una sola vez por página) ---------- */
    var mapsPromise = null;
    habitta.loadMaps = function () {
        if (mapsPromise) return mapsPromise;
        mapsPromise = new Promise(function (resolve, reject) {
            if (window.google && window.google.maps && window.google.maps.places) {
                resolve(window.google.maps);
                return;
            }
            var meta = document.querySelector('meta[name="habitta:maps-key"]');
            var key = meta && meta.content;
            if (!key) {
                reject(new Error('Google Maps no está configurado'));
                return;
            }
            window.__habittaMapsReady = function () { resolve(window.google.maps); };
            var script = document.createElement('script');
            script.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(key) +
                '&libraries=places&language=es&region=EC&loading=async&callback=__habittaMapsReady';
            script.async = true;
            script.onerror = function () { reject(new Error('No se pudo cargar Google Maps')); };
            document.head.appendChild(script);
        });
        return mapsPromise;
    };

    /* Estilo de mapa atenuado para que los pines de la marca destaquen */
    habitta.mapStyles = [
        { elementType: 'geometry', stylers: [{ saturation: -35 }, { lightness: 8 }] },
        { featureType: 'poi', stylers: [{ visibility: 'off' }] },
        { featureType: 'poi.park', elementType: 'geometry', stylers: [{ visibility: 'on' }, { color: '#d9eadf' }] },
        { featureType: 'transit', stylers: [{ visibility: 'off' }] },
        { featureType: 'road', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
        { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#f3e3c3' }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#bfdcd6' }] },
        { featureType: 'administrative', elementType: 'labels.text.fill', stylers: [{ color: '#4b5a56' }] },
    ];

    /* Pin SVG con el color de la marca (data URI para google.maps.Marker) */
    habitta.pinIcon = function (maps, active) {
        var fill = active ? '#C8502E' : '#0B6E5F';
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="46" viewBox="0 0 36 46">' +
            '<path d="M18 45s15-15.2 15-27A15 15 0 0 0 3 18c0 11.8 15 27 15 27z" fill="' + fill + '" stroke="#fff" stroke-width="2.5"/>' +
            '<circle cx="18" cy="18" r="5.5" fill="#fff"/></svg>';
        return {
            url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
            scaledSize: new maps.Size(active ? 42 : 36, active ? 54 : 46),
            anchor: new maps.Point(active ? 21 : 18, active ? 54 : 46),
        };
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

        /* Chat en tiempo real con el anunciante (WebSocket de Django Channels) */
        Alpine.data('chatWidget', function (receiverId) {
            var socket = null;
            var pending = []; // mensajes escritos antes de que el WebSocket termine de abrir
            return {
                open: false,
                draft: '',
                status: 'idle', // idle | connecting | online | offline
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
                        self.$refs.messages.insertAdjacentHTML('beforeend', data.bubble || data.message);
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
         * Buscador del hero: pestañas por tipo (inmuebles/servicios/empleos), categorías filtradas
         * por tipo y propósito, y autocompletado de lugares con Google Places (si hay key).
         */
        Alpine.data('heroSearch', function (initial) {
            initial = initial || {};
            return {
                kind: initial.kind || '',
                purpose: initial.purpose || '',
                category: initial.category || '',
                categories: [],
                purposes: [],
                init: function () {
                    var data = habitta.readJson('search-data');
                    this.categories = data.categories || [];
                    this.purposes = data.purposes || [];
                    var input = this.$refs.address;
                    if (!input) return;
                    habitta.loadMaps().then(function (maps) {
                        if (!maps.places) return;
                        new maps.places.Autocomplete(input, {
                            componentRestrictions: { country: 'ec' },
                            fields: ['formatted_address', 'geometry', 'name'],
                        });
                    }).catch(function () {});
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
