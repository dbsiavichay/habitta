/*
 * Habitta: asistente de publicación (elegir categoría, datos, ubicación, portada y revisar).
 * Se carga sólo en esas páginas, en el bloque `scripts` (antes que Alpine).
 * Usa los mapas (habitta.loadMaps, createMap, pinElement…), habitta.places y habitta.formatPrice de app.js.
 */
(function () {
    'use strict';

    var STEP_SLUGS = { 1: 'datos', 2: 'ubicacion', 3: 'portada', 4: 'revisar' };
    var LAST_STEP = 4;

    function normalize(text) {
        return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
    }

    function toNumber(value) {
        var n = parseFloat(String(value === null || value === undefined ? '' : value).replace(',', '.'));
        return isFinite(n) ? n : null;
    }

    function cleanLabel(text) {
        return String(text || '').replace(/\*/g, '').replace(/Opcional/g, '').replace(/\s+/g, ' ').trim();
    }

    document.addEventListener('alpine:init', function () {
        var Alpine = window.Alpine;

        /* Paso 1: pestañas por tipo y buscador de categorías (sin tildes ni mayúsculas) */
        Alpine.data('categoryPicker', function (initialKind) {
            return {
                kind: initialKind,
                query: '',
                items: [],
                init: function () {
                    this.items = Array.prototype.map.call(this.$root.querySelectorAll('[data-name]'), function (el) {
                        return { name: el.dataset.name, kind: Number(el.dataset.kind) };
                    });
                },
                matches: function (name) {
                    return !this.query || normalize(name).indexOf(normalize(this.query)) !== -1;
                },
                visible: function (kind) {
                    var self = this;
                    if (!this.query) return this.kind === kind;
                    return this.items.some(function (item) { return item.kind === kind && self.matches(item.name); });
                },
                get empty() {
                    var self = this;
                    return !!this.query && !this.items.some(function (item) { return self.matches(item.name); });
                },
            };
        });

        /*
         * Asistente: muestra un paso a la vez, valida el paso antes de avanzar (validación nativa del
         * navegador + punto en el mapa) y arma el resumen del paso Revisar. Todo se envía en un solo POST.
         */
        Alpine.data('publishWizard', function (options) {
            options = options || {};
            return {
                step: 1,
                labels: ['Categoría', 'Datos', 'Ubicación', 'Portada', 'Revisar', 'Fotos'],
                dirty: !!options.errors,
                submitting: false,
                summary: [],
                card: { cover: '', title: '', address: '', price: '' },
                init: function () {
                    var self = this;
                    var fromHash = 0;
                    Object.keys(STEP_SLUGS).forEach(function (n) {
                        if (window.location.hash === '#' + STEP_SLUGS[n]) fromHash = Number(n);
                    });
                    // Tras un error del servidor manda el paso con errores; si no, el enlace (#portada…)
                    this.step = options.errors ? (options.initial || 1) : (fromHash || 1);
                    if (this.step === LAST_STEP) this.buildSummary();
                    this.attachCounters();
                    window.addEventListener('beforeunload', function (event) {
                        if (self.dirty && !self.submitting) {
                            event.preventDefault();
                            event.returnValue = '';
                        }
                    });
                },
                panel: function (n) {
                    return this.$root.querySelector('[data-step="' + n + '"]');
                },
                controls: function (n) {
                    var panel = this.panel(n);
                    if (!panel) return [];
                    return Array.prototype.filter.call(panel.querySelectorAll('input, select, textarea'), function (el) {
                        return !el.disabled && el.type !== 'hidden';
                    });
                },
                hasPoint: function () {
                    var lat = this.$root.querySelector('input[name="latitude"]');
                    var lng = this.$root.querySelector('input[name="longitude"]');
                    return !!(lat && lng && lat.value !== '' && lng.value !== '');
                },
                validate: function (n) {
                    var controls = this.controls(n);
                    for (var i = 0; i < controls.length; i++) {
                        var el = controls[i];
                        if (!el.checkValidity()) {
                            this.show(n);
                            this.$nextTick(function () {
                                el.scrollIntoView({ block: 'center', behavior: 'smooth' });
                                el.reportValidity();
                            });
                            return false;
                        }
                    }
                    if (n === 2 && !this.hasPoint()) {
                        this.show(2);
                        this.$dispatch('need-point');
                        return false;
                    }
                    return true;
                },
                next: function () {
                    if (this.validate(this.step)) this.goTo(this.step + 1);
                },
                back: function () {
                    this.goTo(this.step - 1);
                },
                goTo: function (n) {
                    n = Math.max(1, Math.min(LAST_STEP, n));
                    if (n === LAST_STEP) this.buildSummary();
                    this.show(n);
                    var self = this;
                    this.$nextTick(function () {
                        self.$root.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        var heading = self.$root.querySelector('#paso-' + n);
                        if (heading) heading.focus({ preventScroll: true });
                    });
                },
                show: function (n) {
                    this.step = n;
                    if (window.history && window.history.replaceState) {
                        window.history.replaceState(null, '', '#' + STEP_SLUGS[n]);
                    }
                },
                /* Enter en un campo de texto avanza de paso en lugar de enviar el formulario */
                enter: function (event) {
                    var el = event.target;
                    if (el.tagName === 'TEXTAREA' || el.tagName === 'BUTTON' || el.tagName === 'A') return;
                    event.preventDefault();
                    // En la dirección, Enter elige la sugerencia resaltada (placeSearch)
                    if (el.name === 'address') return;
                    if (this.step < LAST_STEP) this.next();
                },
                submit: function (event) {
                    for (var n = 1; n < LAST_STEP; n++) {
                        if (!this.validate(n)) {
                            event.preventDefault();
                            return;
                        }
                    }
                    this.submitting = true;
                },
                /* Contador de caracteres para el título */
                attachCounters: function () {
                    Array.prototype.forEach.call(this.$root.querySelectorAll('input[name="title"][maxlength]'), function (input) {
                        var counter = document.createElement('p');
                        counter.className = 'mt-1 text-right text-xs text-base-content/50';
                        counter.setAttribute('aria-live', 'polite');
                        var update = function () {
                            counter.textContent = input.value.length + '/' + input.maxLength;
                        };
                        input.addEventListener('input', update);
                        input.insertAdjacentElement('afterend', counter);
                        update();
                    });
                },
                /* Resumen del paso Revisar a partir de lo que hay en el formulario */
                buildSummary: function () {
                    var self = this;
                    var root = this.$root;
                    var sections = [];

                    Array.prototype.forEach.call(root.querySelectorAll('[data-summary]'), function (box) {
                        var stepEl = box.closest('[data-step]');
                        var section = { title: box.dataset.summary, step: Number(stepEl && stepEl.dataset.step), rows: [] };

                        if (box.hasAttribute('data-cover')) {
                            var output = box.querySelector('input[name="base64image"]');
                            var image = box.querySelector('[data-cover-preview]');
                            var src = image && image.getAttribute('src');
                            section.rows.push({
                                label: 'Foto de portada',
                                value: output && output.value ? 'Nueva portada lista' :
                                    (src ? 'Se mantiene la portada actual' : 'Sin portada: se mostrará una imagen genérica'),
                            });
                            self.card.cover = src || '';
                            sections.push(section);
                            return;
                        }

                        var seenRadios = {};
                        Array.prototype.forEach.call(box.querySelectorAll('input, select, textarea'), function (el) {
                            if (el.type === 'hidden' || el.disabled) return;
                            var label = '';
                            var value = '';
                            if (el.type === 'radio') {
                                if (seenRadios[el.name]) return;
                                seenRadios[el.name] = true;
                                var fieldset = el.closest('fieldset');
                                var legend = fieldset && fieldset.querySelector('legend');
                                label = cleanLabel(legend && legend.textContent);
                                var checked = box.querySelector('input[name="' + el.name + '"]:checked');
                                var text = checked && checked.closest('label') && checked.closest('label').querySelector('.sr-only');
                                value = text ? text.textContent.trim() : '';
                            } else {
                                var labelEl = el.id && root.querySelector('label[for="' + el.id + '"]');
                                var labelText = labelEl && (labelEl.querySelector('span') || labelEl);
                                label = cleanLabel(labelText ? labelText.textContent : el.name);
                                if (el.tagName === 'SELECT') {
                                    var option = el.selectedOptions[0];
                                    value = option && option.value ? option.textContent.trim() : '';
                                } else if (el.type === 'checkbox') {
                                    value = el.checked ? 'Sí' : '';
                                } else if (el.type === 'file') {
                                    value = el.files && el.files[0] ? el.files[0].name : '';
                                } else if (el.type === 'range' && el.name === 'radius') {
                                    value = (Number(el.value) / 1000).toLocaleString('es-EC', { maximumFractionDigits: 1 }) + ' km a la redonda';
                                } else {
                                    value = el.value.trim();
                                }
                            }
                            if (!value) return;
                            if (options.priceField && el.name === options.priceField) {
                                value = habitta.formatPrice(value) || value;
                                self.card.price = value;
                            }
                            if (el.name === 'title') self.card.title = value;
                            if (el.name === 'address') self.card.address = value;
                            var wide = el.tagName === 'TEXTAREA' || value.length > 60;
                            if (value.length > 400) value = value.slice(0, 400) + '…';
                            section.rows.push({ label: label, value: value, wide: wide });
                        });

                        if (section.step === 2 && self.hasPoint()) {
                            section.rows.push({ label: 'Punto en el mapa', value: 'Marcado' });
                        }
                        sections.push(section);
                    });
                    this.summary = sections;
                },
            };
        });

        /*
         * Paso 2: ubicación con MapLibre (búsqueda de lugares con placeSearch, pin arrastrable, dirección
         * del punto vía /api/places/reverse/ y radio de operación para los servicios).
         * Sin mapa se puede usar la geolocalización.
         */
        Alpine.data('locationPicker', function (options) {
            options = options || {};
            var maplibregl = null;
            var map = null;
            var marker = null;
            var updateCoverage = null;
            var reverseSeq = 0;
            return {
                lat: toNumber(options.lat),
                lng: toNumber(options.lng),
                radius: parseInt(options.radius, 10) || 3000,
                fixed: !!options.fixed,
                mapState: 'idle', // idle | loading | ready | error
                locating: false,
                geoError: '',
                needPoint: false,
                get hasPoint() {
                    return this.lat !== null && this.lng !== null;
                },
                get km() {
                    return (this.radius / 1000).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                },
                init: function () {
                    var self = this;
                    // El mapa se crea cuando el paso es visible (un mapa en un contenedor oculto queda en blanco)
                    this.$watch('step', function (value) { if (value === 2) self.ensureMap(); });
                    if (this.step === 2) this.$nextTick(function () { self.ensureMap(); });
                    this.$watch('radius', function () { self.drawCircle(true); });
                },
                ensureMap: function () {
                    var self = this;
                    if (this.mapState !== 'idle') return;
                    this.mapState = 'loading';
                    var fail = function (error) {
                        habitta.mapError(error);
                        self.mapState = 'error';
                    };
                    habitta.loadMaps().then(function (lib) {
                        maplibregl = lib;
                        self.buildMap();
                        habitta.whenMapReady(map, function () {
                            updateCoverage = habitta.addCoverageLayer(map);
                            self.mapState = 'ready';
                            if (self.hasPoint) {
                                self.placeMarker();
                                self.drawCircle(true);
                            }
                        }, fail);
                    }).catch(fail);
                },
                buildMap: function () {
                    var self = this;
                    map = habitta.createMap(maplibregl, this.$refs.map, {
                        center: this.hasPoint ? { lat: this.lat, lng: this.lng } : null,
                        zoom: this.hasPoint ? (this.fixed ? 16 : 11) : 6,
                        cooperative: true,
                        fullscreen: true,
                    });
                    map.on('click', function (event) {
                        self.setPoint(event.lngLat.lat, event.lngLat.lng, { geocode: true });
                    });
                },
                /* Lugar elegido en el buscador de la dirección (placeSearch) */
                pickPlace: function (place) {
                    this.setPoint(place.lat, place.lng, { geocode: false, zoom: true });
                    this.setAddress(place.label);
                },
                setPoint: function (lat, lng, opts) {
                    opts = opts || {};
                    this.lat = Math.round(lat * 1e6) / 1e6;
                    this.lng = Math.round(lng * 1e6) / 1e6;
                    this.needPoint = false;
                    this.geoError = '';
                    this.placeMarker();
                    if (map && opts.zoom) map.jumpTo({ center: [this.lng, this.lat], zoom: this.fixed ? 16 : 11 });
                    this.drawCircle(!!opts.zoom);
                    if (opts.geocode) this.reverseGeocode();
                    this.$dispatch('input'); // marca el formulario como modificado
                },
                placeMarker: function () {
                    if (!map || this.mapState !== 'ready' || !this.hasPoint) return;
                    var self = this;
                    if (marker) {
                        marker.setLngLat([this.lng, this.lat]);
                        return;
                    }
                    marker = new maplibregl.Marker({ element: habitta.pinElement(true), anchor: 'bottom', draggable: true });
                    marker.getElement().title = 'Arrastra para ajustar';
                    marker.on('dragend', function () {
                        var position = marker.getLngLat();
                        self.setPoint(position.lat, position.lng, { geocode: true });
                    });
                    marker.setLngLat([this.lng, this.lat]).addTo(map);
                },
                drawCircle: function (fit) {
                    if (this.fixed || !updateCoverage || !this.hasPoint) return;
                    var center = { lat: this.lat, lng: this.lng };
                    updateCoverage(center, this.radius);
                    if (fit) map.fitBounds(habitta.circleBounds(center, this.radius), { padding: 24, duration: 0 });
                },
                reverseGeocode: function () {
                    var self = this;
                    var current = ++reverseSeq;
                    // Para una zona de trabajo basta con la ciudad o el cantón
                    habitta.places.reverse(this.lat, this.lng, !this.fixed).then(function (label) {
                        if (current === reverseSeq && label) self.setAddress(label);
                    }).catch(function () { /* sin dirección: queda como la escribió */ });
                },
                setAddress: function (text) {
                    var input = this.$root.querySelector('input[name="address"]');
                    if (!input || !text) return;
                    input.value = String(text).slice(0, input.maxLength > 0 ? input.maxLength : 255);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                },
                locate: function () {
                    var self = this;
                    if (!navigator.geolocation) {
                        this.geoError = 'Tu navegador no permite usar tu ubicación.';
                        return;
                    }
                    this.locating = true;
                    this.geoError = '';
                    navigator.geolocation.getCurrentPosition(function (position) {
                        self.locating = false;
                        self.setPoint(position.coords.latitude, position.coords.longitude, { geocode: true, zoom: true });
                    }, function (error) {
                        self.locating = false;
                        self.geoError = error.code === 1 ? 'No diste permiso para usar tu ubicación.' : 'No pudimos obtener tu ubicación.';
                    }, { enableHighAccuracy: true, timeout: 10000 });
                },
            };
        });

        /* Paso 3: portada recortada a 16:9 con Cropper.js; se envía como JPEG en base64 */
        Alpine.data('coverCropper', function (options) {
            options = options || {};
            var cropper = null;
            var objectUrl = null;
            return {
                current: options.current || '',
                preview: '',
                hasNew: false,
                dragging: false,
                error: '',
                init: function () {
                    // Tras un error del servidor la portada recortada vuelve en el campo oculto
                    var output = this.output();
                    if (output && output.value) {
                        this.preview = output.value;
                        this.hasNew = true;
                    } else {
                        this.preview = this.current;
                    }
                },
                output: function () {
                    return this.$root.querySelector('input[name="base64image"]');
                },
                pick: function () {
                    this.$refs.file.click();
                },
                drop: function (event) {
                    this.dragging = false;
                    var files = event.dataTransfer && event.dataTransfer.files;
                    if (files && files[0]) this.load(files[0]);
                },
                load: function (file) {
                    this.error = '';
                    this.$refs.file.value = '';
                    if (!file) return;
                    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
                        this.error = 'Usa una foto en JPG, PNG o WEBP.';
                        return;
                    }
                    if (!window.Cropper) {
                        this.error = 'No se pudo cargar el editor de recorte. Recarga la página.';
                        return;
                    }
                    this.destroy();
                    objectUrl = URL.createObjectURL(file);
                    var image = this.$refs.image;
                    image.src = objectUrl;
                    this.$refs.dialog.showModal();
                    cropper = new window.Cropper(image, {
                        aspectRatio: 16 / 9,
                        viewMode: 1,
                        autoCropArea: 1,
                        dragMode: 'move',
                        background: false,
                        responsive: true,
                    });
                },
                crop: function () {
                    if (!cropper) return;
                    var canvas = cropper.getCroppedCanvas({
                        width: 1600, height: 900, fillColor: '#fff',
                        imageSmoothingEnabled: true, imageSmoothingQuality: 'high',
                    });
                    if (!canvas) return;
                    // JPEG: pesa una fracción del PNG y no supera el límite de subida
                    var data = canvas.toDataURL('image/jpeg', 0.85);
                    var output = this.output();
                    output.value = data;
                    output.dispatchEvent(new Event('input', { bubbles: true }));
                    this.preview = data;
                    this.hasNew = true;
                    this.$refs.dialog.close();
                },
                cancel: function () {
                    this.$refs.dialog.close();
                },
                destroy: function () {
                    if (cropper) {
                        cropper.destroy();
                        cropper = null;
                    }
                    if (objectUrl) {
                        URL.revokeObjectURL(objectUrl);
                        objectUrl = null;
                    }
                },
                discard: function () {
                    this.output().value = '';
                    this.preview = this.current;
                    this.hasNew = false;
                },
            };
        });
    });
})();
