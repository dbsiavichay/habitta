/*
 * Detalle de un anuncio: mapa de ubicación y fotos del propietario (el chat vive en app.js).
 */
(function () {
    'use strict';

    var habitta = window.habitta;

    function csrfToken() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    document.addEventListener('alpine:init', function () {
        var Alpine = window.Alpine;

        /* Mapa de la ubicación (o del área de cobertura de un servicio). Se carga al entrar en pantalla. */
        Alpine.data('singleMap', function (lat, lng, radiusMeters) {
            return {
                status: 'idle',
                init: function () {
                    var self = this;
                    var observer = new IntersectionObserver(function (entries) {
                        if (!entries[0].isIntersecting) return;
                        observer.disconnect();
                        self.load();
                    }, { rootMargin: '200px' });
                    observer.observe(this.$el);
                },
                load: function () {
                    var self = this;
                    var center = { lat: lat, lng: lng };
                    var fail = function (error) {
                        habitta.mapError(error);
                        self.status = 'unavailable';
                    };
                    this.status = 'loading';
                    habitta.loadMaps().then(function (maplibregl) {
                        var map = habitta.createMap(maplibregl, self.$refs.canvas, {
                            center: center, zoom: radiusMeters ? 13 : 15, cooperative: true,
                        });
                        habitta.whenMapReady(map, function () {
                            if (radiusMeters) {
                                habitta.addCoverageLayer(map)(center, radiusMeters);
                                map.fitBounds(habitta.circleBounds(center, radiusMeters), { padding: 24, duration: 0 });
                            } else {
                                new maplibregl.Marker({ element: habitta.pinElement(false), anchor: 'bottom' })
                                    .setLngLat([lng, lat]).addTo(map);
                            }
                            self.status = 'ready';
                        }, fail);
                    }).catch(fail);
                },
            };
        });

        /* Fotos del propietario: subir (arrastrar o elegir, varias a la vez) y borrar */
        Alpine.data('galleryManager', function (uploadUrl, objectId, contentType) {
            return {
                dragging: false,
                uploading: 0,
                errors: [],
                pick: function () { this.$refs.input.click(); },
                drop: function (event) {
                    this.dragging = false;
                    this.upload(event.dataTransfer.files);
                },
                upload: function (fileList) {
                    var self = this;
                    var files = Array.prototype.filter.call(fileList || [], function (f) { return f.type.indexOf('image/') === 0; });
                    if (!files.length) return;
                    this.errors = [];
                    this.uploading = files.length;
                    var chain = Promise.resolve();
                    files.forEach(function (file) {
                        chain = chain.then(function () {
                            var data = new FormData();
                            data.append('img', file);
                            data.append('object_id', objectId);
                            data.append('content_type', contentType);
                            return fetch(uploadUrl, {
                                method: 'POST', body: data,
                                headers: { 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
                            }).then(function (r) {
                                if (!r.ok) self.errors.push(file.name);
                            }).catch(function () { self.errors.push(file.name); })
                              .finally(function () { self.uploading -= 1; });
                        });
                    });
                    chain.then(function () {
                        if (!self.errors.length) window.location.reload();
                    });
                },
                remove: function (url) {
                    if (!window.confirm('¿Eliminar esta foto? No se puede deshacer.')) return;
                    fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' } })
                        .then(function (r) { if (r.ok) window.location.reload(); else window.alert('No se pudo eliminar la foto.'); });
                },
            };
        });

    });
})();
