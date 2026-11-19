// El appId se toma del atributo data-app-id del <script> (FACEBOOK_APP_ID en el servidor).
(function () {
    var script = document.currentScript;
    var appId = script && script.dataset.appId;
    if (!appId) return;

    window.fbAsyncInit = function () {
        FB.init({
            appId: appId,
            cookie: true,
            xfbml: true,
            version: 'v21.0'
        });
    };

    // Carga asíncrona del SDK
    (function (d, s, id) {
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) return;
        js = d.createElement(s); js.id = id;
        js.src = 'https://connect.facebook.net/es_LA/sdk.js';
        fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));
})();
