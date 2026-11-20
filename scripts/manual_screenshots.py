#!/usr/bin/env python3
"""Toma las capturas de los manuales de uso (static/manual/) con Chrome headless.

Corre en la Mac, fuera de Docker, contra el servidor de capturas: una copia anonimizada de la base
(ver "Capturas de los manuales" en el README). Necesita Google Chrome, websocket-client y Pillow:

    python3 -m venv /tmp/capturas && /tmp/capturas/bin/pip install websocket-client pillow
    /tmp/capturas/bin/python scripts/manual_screenshots.py --sesiones sesiones.json
    /tmp/capturas/bin/python scripts/manual_screenshots.py --sesiones sesiones.json --solo usuarios/registro

Cada toma es un dict de SHOTS:
    name      archivo de salida, sin extensión, relativo a static/manual/
    path      ruta del sitio; admite los ids del JSON de sesiones, p. ej. /admin/…/{pago_pendiente}/change/
    user      'ana', 'carlos' o 'sofia' (claves del JSON de sesiones); None = visitante
    viewport  DESKTOP, ADMIN o PHONE
    js        JavaScript que se ejecuta antes de capturar (puede devolver una promesa)
    type      texto que se escribe en el campo con el foco, después de `js`
    selector  recorta la captura a ese elemento (con `pad` px de margen)
    clip      recorta la captura a (x, y, ancho, alto) en px CSS de la ventana
    full      True = toda la página, no sólo la ventana
    dark      True = tema oscuro
    wait      segundos extra antes de capturar
"""
import argparse
import base64
import io
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'static' / 'manual'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PORT = 9333

DESKTOP = {'width': 1280, 'height': 800, 'scale': 1.5, 'mobile': False}
ADMIN = {'width': 1440, 'height': 900, 'scale': 4 / 3, 'mobile': False}  # Unfold muestra el menú lateral desde 1440
PHONE = {'width': 390, 'height': 844, 'scale': 2, 'mobile': True}
MAX_WIDTH = 1920  # px de la imagen final

# Abre el menú de la cuenta del navbar (los dropdown de daisyUI se abren con el foco).
OPEN_ACCOUNT_MENU = "document.querySelector('[aria-label=\"Menú de tu cuenta\"]').focus()"
# El servidor de capturas corre con DEBUG: se quita la etiqueta "Desarrollo" que Unfold muestra sólo en local.
HIDE_ENVIRONMENT = (
    "[...document.querySelectorAll('span, div')]"
    ".filter(e => !e.children.length && e.textContent.trim().toLowerCase() === 'desarrollo')"
    ".forEach(e => e.remove())"
)
OPEN_COMMAND = "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'k', metaKey: true, ctrlKey: true, bubbles: true}))"


OPEN_CHAT = "window.dispatchEvent(new CustomEvent('open-chat'))"
# Baja al final de la página y de los contenedores con scroll propio (el contenido de Unfold).
SCROLL_BOTTOM = (
    "window.scrollTo(0, document.body.scrollHeight);"
    "[...document.querySelectorAll('*')].filter(e => e.scrollHeight > e.clientHeight + 20"
    " && ['auto', 'scroll'].includes(getComputedStyle(e).overflowY)).forEach(e => e.scrollTop = e.scrollHeight)"
)


def click_alpine(handler):
    """JS que hace clic en el elemento de Unfold cuyo x-on:click contiene `handler`."""
    return (f"[...document.querySelectorAll('[x-on\\\\:click]')]"
            f".find(e => e.getAttribute('x-on:click').includes({json.dumps(handler)})).click()")


def click_text(text, selector='a, button'):
    """JS que hace clic en el primer elemento visible de `selector` cuyo texto es `text` (o termina en él:
    los íconos de Unfold son ligaduras de texto, como "check_circle Confirmar")."""
    return (f"[...document.querySelectorAll({json.dumps(selector)})].find(e => {{"
            f" const t = e.textContent.replace(/\\s+/g, ' ').trim();"
            f" return (t === {json.dumps(text)} || t.endsWith(' ' + {json.dumps(text)})) && e.offsetParent !== null;"
            f" }}).click()")


def scroll_to_text(text, selector='h2, h3, legend'):
    """JS que lleva a la vista el primer `selector` que contiene `text`."""
    return (f"[...document.querySelectorAll({json.dumps(selector)})]"
            f".find(e => e.textContent.includes({json.dumps(text)})).scrollIntoView({{block: 'start'}})")


# Las rutas pueden usar los ids de `manage.py manual_capture_data --sesiones` ({anuncio}, {pago_pendiente}…).
U, A = 'usuarios/', 'administracion/'
SHOTS = [
    # ---------------------------------------------------------------- Manual del usuario
    # 1. Primeros pasos
    {'name': U + 'registro', 'path': '/authentication/register/', 'viewport': DESKTOP},
    {'name': U + 'completar-perfil', 'path': '/authentication/user/0/complete/', 'user': 'carlos', 'viewport': DESKTOP},
    {'name': U + 'ingresar', 'path': '/authentication/login/', 'viewport': PHONE},
    {'name': U + 'menu-cuenta', 'path': '/realty/publicationes/', 'user': 'ana', 'viewport': DESKTOP,
     'js': OPEN_ACCOUNT_MENU},
    # 2. Buscar y explorar
    {'name': U + 'portada', 'path': '/', 'viewport': DESKTOP, 'wait': 1},
    # Vista de lista: la clave de Google Maps del demo muestra un aviso de error sobre el mapa.
    {'name': U + 'explorador', 'path': '/realty/explorador/lista/?kind=1', 'viewport': DESKTOP, 'wait': 2},
    {'name': U + 'explorador-filtros', 'path': '/realty/explorador/mapa/?kind=1', 'viewport': PHONE, 'wait': 1,
     'js': "document.querySelector('[aria-label=\"Abrir filtros\"]').click()"},
    # 3. Ver un anuncio
    {'name': U + 'anuncio', 'path': '/realty/property/{anuncio}/detail/', 'user': 'carlos', 'viewport': DESKTOP, 'wait': 1},
    {'name': U + 'anuncio-contacto', 'path': '/realty/property/{anuncio}/detail/', 'user': 'carlos', 'viewport': DESKTOP,
     'selector': 'article aside', 'pad': 12},
    {'name': U + 'perfil-publico', 'path': '/authentication/profile/ana.torres/', 'user': 'carlos', 'viewport': DESKTOP},
    {'name': U + 'favoritos', 'path': '/realty/favorite/properties/', 'user': 'ana', 'viewport': DESKTOP},
    # 4. Publicar un anuncio
    {'name': U + 'publicar-categoria', 'path': '/realty/property/add/', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'publicar-datos', 'path': '/realty/property/add/category/{categoria}/', 'user': 'ana', 'viewport': DESKTOP},
    # Sin el mapa: con la clave del demo, Google muestra un aviso de error encima.
    {'name': U + 'publicar-ubicacion', 'path': '/realty/property/{anuncio}/update/#ubicacion', 'user': 'ana',
     'viewport': DESKTOP, 'clip': (300, 100, 980, 470)},
    {'name': U + 'publicar-portada', 'path': '/realty/property/{anuncio}/update/#portada', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'publicar-revisar', 'path': '/realty/property/{anuncio}/update/#revisar', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'publicar-fotos', 'path': '/realty/property/{anuncio}/fotos/', 'user': 'ana', 'viewport': DESKTOP},
    # 5. Mis publicaciones
    {'name': U + 'mis-publicaciones', 'path': '/realty/publicationes/', 'user': 'ana', 'viewport': DESKTOP,
     'js': "document.querySelector('[aria-label^=\"Más acciones\"]').focus()"},
    # 6. Mensajes (la lista antes que la conversación: abrirla marca los mensajes como leídos)
    {'name': U + 'mensajes', 'path': '/messenger/conversations/', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'chat-flotante', 'path': '/realty/property/{anuncio}/detail/', 'user': 'carlos', 'viewport': DESKTOP,
     'js': OPEN_CHAT, 'wait': 2},
    {'name': U + 'conversacion', 'path': '/messenger/conversation/{conversacion}/detail/', 'user': 'ana',
     'viewport': DESKTOP, 'wait': 2},
    # 7. Subastas
    {'name': U + 'subastas', 'path': '/auctions/auctions/', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'nueva-subasta', 'path': '/auctions/auction/add/', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'subasta-anuncio', 'path': '/realty/property/{anuncio_subasta}/detail/', 'user': 'carlos',
     'viewport': DESKTOP, 'selector': 'section.bg-neutral', 'pad': 12},
    # 8. Pagos y descargas (elegir-pago deja el pago en curso que usa registrar-pago)
    {'name': U + 'comprar', 'path': '/realty/property/{planos}/detail/', 'user': 'ana', 'viewport': DESKTOP,
     'selector': 'article aside', 'pad': 12},
    {'name': U + 'elegir-pago', 'path': '/realty/property/{planos}/detail/', 'user': 'ana', 'viewport': DESKTOP,
     'js': "document.querySelector('form[action$=\"/payments/method/select/\"]').submit()", 'wait': 2.5},
    {'name': U + 'registrar-pago', 'path': '/payments/bank/payment/add/', 'user': 'ana', 'viewport': DESKTOP},
    {'name': U + 'mis-pagos', 'path': '/payments/bank/payment/list/', 'user': 'carlos', 'viewport': DESKTOP},
    {'name': U + 'descargas', 'path': '/payments/downloads/', 'user': 'carlos', 'viewport': DESKTOP},
    # 9. Mi cuenta
    {'name': U + 'mi-perfil', 'path': '/authentication/profile/update/', 'user': 'ana', 'viewport': DESKTOP},

    # ---------------------------------------------------------------- Manual de administración
    # 1. Acceso y recorrido
    {'name': A + 'ingreso', 'path': '/admin/login/', 'viewport': ADMIN},
    {'name': A + 'inicio', 'path': '/admin/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'buscador', 'path': '/admin/', 'user': 'sofia', 'viewport': ADMIN,
     'js': OPEN_COMMAND, 'type': 'lote', 'wait': 1.5},
    {'name': A + 'menu-sitio', 'path': '/admin/', 'user': 'sofia', 'viewport': ADMIN,
     'js': click_alpine('siteDropdownOpen'), 'clip': (0, 0, 400, 330)},
    {'name': A + 'menu-usuario', 'path': '/admin/', 'user': 'sofia', 'viewport': ADMIN,
     'js': click_alpine('openUserLinks'), 'clip': (0, 680, 400, 220)},
    # 2. Inicio
    {'name': A + 'inicio-tablas', 'path': '/admin/', 'user': 'sofia', 'viewport': ADMIN, 'js': SCROLL_BOTTOM},
    # 3. Transferencias y pagos
    {'name': A + 'transferencias', 'path': '/admin/payments/bankpayment/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'transferencia-ficha', 'path': '/admin/payments/bankpayment/{pago_pendiente}/change/', 'user': 'sofia',
     'viewport': ADMIN},
    {'name': A + 'transferencia-confirmar', 'path': '/admin/payments/bankpayment/{pago_pendiente}/change/',
     'user': 'sofia', 'viewport': ADMIN, 'js': click_text('Confirmar'), 'wait': 1.5},
    {'name': A + 'transferencia-rechazar', 'path': '/admin/payments/bankpayment/{pago_pendiente}/change/',
     'user': 'sofia', 'viewport': ADMIN, 'js': click_text('Rechazar'), 'wait': 1.5},
    # 4. Publicaciones
    {'name': A + 'publicaciones', 'path': '/admin/realty/property/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'publicacion-ficha', 'path': '/admin/realty/property/{anuncio}/change/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'publicacion-especificaciones', 'path': '/admin/realty/property/{anuncio}/change/', 'user': 'sofia',
     'viewport': ADMIN, 'js': click_text('Especificaciones'), 'wait': 0.5},
    # 5. Subastas
    {'name': A + 'subastas', 'path': '/admin/auctions/auction/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'subasta-ofertas', 'path': '/admin/auctions/auction/{subasta}/change/', 'user': 'sofia',
     'viewport': ADMIN, 'js': click_text('Ofertas'), 'wait': 0.5},
    # 6. Usuarios y permisos
    {'name': A + 'usuarios', 'path': '/admin/auth/user/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'usuario-permisos', 'path': '/admin/auth/user/{ana}/change/', 'user': 'sofia', 'viewport': ADMIN,
     'js': scroll_to_text('Permisos')},
    {'name': A + 'grupo', 'path': '/admin/auth/group/add/', 'user': 'sofia', 'viewport': ADMIN},
    # 7. Comunidad
    {'name': A + 'vistas', 'path': '/admin/logs/log/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'conversaciones', 'path': '/admin/messenger/conversation/', 'user': 'sofia', 'viewport': ADMIN},
    # 8. Catálogo
    {'name': A + 'categorias', 'path': '/admin/realty/category/', 'user': 'sofia', 'viewport': ADMIN},
    {'name': A + 'categoria-publicacion', 'path': '/admin/realty/category/{categoria}/change/', 'user': 'sofia',
     'viewport': ADMIN, 'js': click_text('Publicación'), 'wait': 0.5},
    {'name': A + 'especificacion', 'path': '/admin/realty/specification/{especificacion}/change/', 'user': 'sofia',
     'viewport': ADMIN},
    # 9. Contenido del sitio
    # Sin las vistas previas que no cargan (en la copia local faltan algunas imágenes de media/).
    {'name': A + 'portada-fondos', 'path': '/admin/project/settings/{portada}/change/', 'user': 'sofia', 'viewport': ADMIN,
     'js': "document.querySelectorAll('img').forEach(i => { if (!i.naturalWidth) i.remove() })"},
    {'name': A + 'terminos', 'path': '/admin/project/term/', 'user': 'sofia', 'viewport': ADMIN},
]


class Chrome:
    """Chrome headless controlado por el protocolo de DevTools (una sola pestaña)."""

    def __init__(self):
        self.profile = tempfile.mkdtemp(prefix='habitta-capturas-')
        self.process = subprocess.Popen(
            [CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={self.profile}',
             '--hide-scrollbars', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
             '--lang=es-EC', 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version', timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        request = urllib.request.Request(f'http://127.0.0.1:{PORT}/json/new?about:blank', method='PUT')
        target = json.load(urllib.request.urlopen(request))
        self.ws = websocket.create_connection(target['webSocketDebuggerUrl'], timeout=60)
        self.counter = 0
        self.loaded = False
        self.call('Page.enable')
        self.call('Network.enable')

    def call(self, method, **params):
        self.counter += 1
        self.ws.send(json.dumps({'id': self.counter, 'method': method, 'params': params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get('method') == 'Page.loadEventFired':
                self.loaded = True
            if message.get('id') == self.counter:
                if 'error' in message:
                    raise RuntimeError(f'{method}: {message["error"]}')
                return message.get('result', {})

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', expression=expression, awaitPromise=True, returnByValue=True)
        if 'exceptionDetails' in result:
            raise RuntimeError(f'JS: {result["exceptionDetails"].get("text")} en {expression[:80]}')
        return result.get('result', {}).get('value')

    def navigate(self, url):
        if '#' in url:  # si sólo cambia el hash no hay evento de carga: se pasa antes por una página en blanco
            self.loaded = False
            self.call('Page.navigate', url='about:blank')
        self.loaded = False
        self.call('Page.navigate', url=url)
        deadline = time.time() + 30
        while not self.loaded and time.time() < deadline:
            message = json.loads(self.ws.recv())
            if message.get('method') == 'Page.loadEventFired':
                self.loaded = True
        self.evaluate('document.fonts.ready.then(() => true)')

    def close(self):
        self.ws.close()
        self.process.terminate()


def take(chrome, base_url, sessions, shot):
    viewport = shot['viewport']
    chrome.call('Network.clearBrowserCookies')
    if shot.get('user'):
        chrome.call('Network.setCookie', name='sessionid', value=sessions[shot['user']], domain='localhost', path='/')
    chrome.call('Emulation.setDeviceMetricsOverride', width=viewport['width'], height=viewport['height'],
                deviceScaleFactor=viewport['scale'], mobile=viewport['mobile'])
    chrome.call('Emulation.setTouchEmulationEnabled', enabled=viewport['mobile'])
    chrome.call('Emulation.setEmulatedMedia', features=[
        {'name': 'prefers-color-scheme', 'value': 'dark' if shot.get('dark') else 'light'},
        {'name': 'prefers-reduced-motion', 'value': 'reduce'},
    ])
    chrome.navigate(base_url + shot['path'].format(**sessions.get('ids', {})))
    time.sleep(0.8)
    if shot['path'].startswith('/admin/'):
        chrome.evaluate(HIDE_ENVIRONMENT)
    if shot.get('js'):
        chrome.evaluate(shot['js'])
        time.sleep(0.6)
    for char in shot.get('type', ''):  # tecla por tecla: hay buscadores que escuchan keyup
        chrome.call('Input.dispatchKeyEvent', type='keyDown', key=char, text=char)
        chrome.call('Input.dispatchKeyEvent', type='keyUp', key=char)
    time.sleep(shot.get('wait', 0))

    params = {'format': 'png'}
    if shot.get('clip'):
        x, y, width, height = shot['clip']
        params['clip'] = {'x': x, 'y': y, 'width': width, 'height': height, 'scale': 1}
    elif shot.get('selector'):
        pad = shot.get('pad', 16)
        rect = chrome.evaluate(
            f"(() => {{ const r = document.querySelector({json.dumps(shot['selector'])}).getBoundingClientRect();"
            " return {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}; })()"
        )
        params.update(captureBeyondViewport=True, clip={
            'x': max(rect['x'] - pad, 0), 'y': max(rect['y'] - pad, 0),
            'width': rect['width'] + 2 * pad, 'height': rect['height'] + 2 * pad, 'scale': 1,
        })
    elif shot.get('full'):
        height = chrome.evaluate('document.documentElement.scrollHeight')
        params.update(captureBeyondViewport=True,
                      clip={'x': 0, 'y': 0, 'width': viewport['width'], 'height': height, 'scale': 1})
    data = base64.b64decode(chrome.call('Page.captureScreenshot', **params)['data'])

    image = Image.open(io.BytesIO(data)).convert('RGB')
    if image.width > MAX_WIDTH:
        image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)), Image.LANCZOS)
    target = OUT / f'{shot["name"]}.webp'
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, 'WEBP', quality=80, method=6)
    print(f'{target.relative_to(ROOT)}  {image.width}×{image.height}  {target.stat().st_size // 1024} KB')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--sesiones', required=True, help='JSON de `manage.py manual_capture_data --sesiones`')
    parser.add_argument('--url', default='http://localhost:8001', help='servidor de capturas')
    parser.add_argument('--solo', nargs='*', default=[], help='nombres (o prefijos) de las tomas a repetir')
    args = parser.parse_args()

    sessions = json.loads(Path(args.sesiones).read_text())
    shots = [shot for shot in SHOTS if not args.solo or any(shot['name'].startswith(only) for only in args.solo)]
    chrome = Chrome()
    failed = []
    try:
        for shot in shots:
            try:
                take(chrome, args.url.rstrip('/'), sessions, shot)
            except Exception as error:  # una toma rota no detiene las demás
                failed.append(shot['name'])
                print(f'ERROR {shot["name"]}: {error}')
    finally:
        chrome.close()
    if failed:
        raise SystemExit(f'Fallaron {len(failed)} tomas: {", ".join(failed)}')


if __name__ == '__main__':
    main()
