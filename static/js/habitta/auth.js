/*
 * Páginas de cuenta: entrar con Facebook (layouts/auth.html lo carga sólo si está configurado).
 * El SDK entrega un token que el servidor valida contra la app (apps/authentication/social.py).
 */
(function () {
    'use strict';

    var sdk = null;   // promesa de carga del SDK (una sola vez por página)
    var FB = null;    // fuera del estado de Alpine para no envolverlo en un proxy reactivo

    function loadFacebookSdk(appId) {
        if (sdk) return sdk;
        sdk = new Promise(function (resolve, reject) {
            if (window.FB) { resolve(window.FB); return; }
            window.fbAsyncInit = function () {
                window.FB.init({ appId: appId, cookie: false, xfbml: false, version: 'v21.0' });
                resolve(window.FB);
            };
            var script = document.createElement('script');
            script.src = 'https://connect.facebook.net/es_LA/sdk.js';
            script.async = true;
            script.crossOrigin = 'anonymous';
            script.onerror = function () { reject(new Error('No se pudo cargar el SDK de Facebook')); };
            document.head.appendChild(script);
        });
        return sdk;
    }

    document.addEventListener('alpine:init', function () {
        window.Alpine.data('facebookLogin', function (appId) {
            return {
                busy: false,
                failed: false,
                error: '',
                init: function () {
                    var self = this;
                    // Se carga al abrir la página: FB.login debe llamarse directo desde el clic
                    // o el navegador bloquea la ventana emergente.
                    loadFacebookSdk(appId)
                        .then(function (sdkFB) { FB = sdkFB; })
                        .catch(function () { self.failed = true; });
                },
                login: function () {
                    var self = this;
                    if (!FB) {
                        this.error = this.failed
                            ? 'No pudimos conectar con Facebook. Revisa tu conexión o entra con tu correo.'
                            : 'Facebook todavía está cargando. Inténtalo en un momento.';
                        return;
                    }
                    this.error = '';
                    this.busy = true;
                    FB.login(function (response) {
                        if (response && response.authResponse) {
                            self.$refs.token.value = response.authResponse.accessToken;
                            self.$root.submit();   // submit() no dispara @submit: no hay bucle
                        } else {
                            self.busy = false;
                        }
                    }, { scope: 'public_profile,email' });
                },
            };
        });
    });
})();
