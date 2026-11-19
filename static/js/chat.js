// Chat en tiempo real (WebSocket vía Django Channels).
// Sólo se activa en páginas que tienen el widget de chat (#owner).
(function () {
    var owner = document.getElementById('owner');
    var body = document.querySelector('.chat-body');
    var input = document.querySelector('.chat-widget_input textarea');
    var button = document.querySelector('.chat-widget_input button');
    if (!owner || !body || !input || !button) return;

    var scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    var socket = new WebSocket(scheme + window.location.host + '/ws/message/' + encodeURIComponent(owner.value) + '/');

    socket.onmessage = function (e) {
        var data = JSON.parse(e.data);
        // El HTML llega renderizado y escapado por el servidor.
        body.insertAdjacentHTML('beforeend', data.message);
    };

    socket.onclose = function () {
        console.warn('Chat desconectado');
    };

    var send = function () {
        var message = input.value.trim();
        if (!message || socket.readyState !== WebSocket.OPEN) return;
        socket.send(JSON.stringify({ message: message }));
        input.value = '';
    };

    input.addEventListener('keyup', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) send();
    });
    button.addEventListener('click', function (e) {
        e.preventDefault();
        send();
    });
})();
