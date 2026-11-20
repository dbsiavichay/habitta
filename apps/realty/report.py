"""Afiche en PDF de un anuncio (A4) con la marca del sitio.

Todo se dibuja con reportlab, sin plantillas de imagen: cabecera con el logo, portada, título y
precio, descripción y características, y una fila con el mapa, el anunciante y un código QR que
lleva al anuncio. Los colores son los del tema `habitta` (assets/tailwind/source.css).
El mapa se arma con tiles raster de OpenStreetMap (MAP_TILE_URL) y se guarda como imagen del anuncio.
"""
import math
import os
from io import BytesIO
from urllib.parse import urlsplit

import qrcode
import requests
from django.conf import settings
from django.utils import timezone
from PIL import Image as PilImage, ImageDraw, ImageFont, ImageOps
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from apps.project.templatetags.habitta import NO_VALUES, initials, money, spec_value

PRIMARY = HexColor('#0B6E5F')
PRIMARY_SOFT = HexColor('#E7F1EF')   # primary al 10 % sobre blanco
SECONDARY = HexColor('#C8502E')
NEUTRAL = HexColor('#13211E')
MUTED = HexColor('#5B6764')          # neutral al ~65 %
FOOTER_MUTED = HexColor('#A7B3AF')
BASE_200 = HexColor('#F7F4EF')
BASE_300 = HexColor('#EAE4DA')

PAGE_W, PAGE_H = A4
MARGIN = 36
CONTENT_W = PAGE_W - 2 * MARGIN
FOOTER_H = 30
ROW_H = 176          # alto de la fila de tarjetas (mapa, anunciante, QR)
GAP = 12

LOGO_PATH = os.path.join(settings.BASE_DIR, 'static', 'brand', 'habitta-logo.png')
LOGO_RATIO = 1200 / 297
FONT_DIR = os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'plus-jakarta-sans')
FONT_STYLES = {'regular': 'Regular', 'semibold': 'SemiBold', 'bold': 'Bold', 'extrabold': 'ExtraBold'}
FALLBACK_FONTS = {'regular': 'Helvetica', 'semibold': 'Helvetica-Bold', 'bold': 'Helvetica-Bold', 'extrabold': 'Helvetica-Bold'}
MAP_ZOOM = 16
MAP_VIEW = (400, 340)   # área del mapa en px lógicos (como el antiguo mapa estático de 400×340 a escala 2)
MAP_SIZE = (800, 680)   # imagen guardada: suficiente para imprimir la tarjeta de 196 pt
MAP_MIN_WIDTH = 800     # los mapas guardados por la versión anterior (274 px) se vuelven a pedir
TILE_SIZE = 256

_fonts = {}


def _font(weight='regular'):
    """Plus Jakarta Sans registrada una sola vez; si faltan los TTF se usa Helvetica."""
    if not _fonts:
        for key, style in FONT_STYLES.items():
            name = 'PlusJakartaSans-%s' % style
            try:
                pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, name + '.ttf')))
                _fonts[key] = name
            except Exception:  # reportlab lanza TTFError u OSError según el caso
                _fonts[key] = FALLBACK_FONTS[key]
    return _fonts[weight]


# ----------------------------------------------------------------------------- texto

def _fit(text, font, size, width):
    """Recorta el texto con «…» para que quepa en una línea."""
    text = text or ''
    if stringWidth(text, font, size) <= width:
        return text
    while text and stringWidth(text + '…', font, size) > width:
        text = text[:-1]
    return text.rstrip() + '…'


def _lines(text, font, size, width, max_lines):
    """Parte el texto por palabras; si sobra, la última línea termina en «…»."""
    if max_lines <= 0:
        return []
    lines = simpleSplit(' '.join((text or '').split()), font, size, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(' .,;:') + '…'
    return [_fit(line, font, size, width) for line in lines]


def _char_lines(text, font, size, width, max_lines):
    """Parte el texto letra por letra (para URLs, que no tienen espacios)."""
    lines, current = [], ''
    for char in text:
        if current and stringWidth(current + char, font, size) > width:
            lines.append(current)
            current = char
        else:
            current += char
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _fit(lines[-1] + '…', font, size, width)
    return lines


def _label(c, text, x, y):
    """Rótulo pequeño en mayúsculas (como los `text-xs uppercase tracking-wide` del sitio)."""
    c.setFillColor(MUTED)
    c.setFont(_font('bold'), 7.5)
    c.drawString(x, y, text.upper(), charSpace=0.8)


def _pill(c, text, right, y, fg, bg, size=9):
    """Pastilla alineada a la derecha en `right`; devuelve su borde izquierdo."""
    font = _font('bold')
    pad, height = 9, size + 10
    width = stringWidth(text, font, size) + 2 * pad
    left = right - width
    c.setFillColor(bg)
    c.roundRect(left, y, width, height, height / 2, stroke=0, fill=1)
    c.setFillColor(fg)
    c.setFont(font, size)
    c.drawString(left + pad, y + (height - size) / 2 + 1.6, text)
    return left


# ----------------------------------------------------------------------------- imágenes

def _clip(c, x, y, w, h, radius=0, circle=False):
    path = c.beginPath()
    if circle:
        path.circle(x + w / 2, y + h / 2, min(w, h) / 2)
    elif radius:
        path.roundRect(x, y, w, h, radius)
    else:
        path.rect(x, y, w, h)
    c.clipPath(path, stroke=0, fill=0)


def _draw_image_cover(c, source, x, y, w, h, radius=0, circle=False):
    """Dibuja la imagen recortada al centro para llenar el marco (como `object-fit: cover`).

    `source` es una ruta o una imagen de Pillow. Devuelve False si no se pudo abrir.
    """
    try:
        image = source if isinstance(source, PilImage.Image) else PilImage.open(source)
        image = ImageOps.exif_transpose(image).convert('RGB')
    except (OSError, ValueError):
        return False

    ratio = w / h
    iw, ih = image.size
    if iw / ih > ratio:
        nw = max(1, round(ih * ratio))
        left = (iw - nw) // 2
        image = image.crop((left, 0, left + nw, ih))
    else:
        nh = max(1, round(iw / ratio))
        top = (ih - nh) // 2
        image = image.crop((0, top, iw, top + nh))
    max_width = int(w * 3)  # ~216 ppp: suficiente para imprimir sin inflar el PDF
    if image.width > max_width:
        image = image.resize((max_width, max(1, round(max_width / ratio))), PilImage.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, 'JPEG', quality=85)
    buffer.seek(0)
    c.saveState()
    _clip(c, x, y, w, h, radius=radius, circle=circle)
    c.drawImage(ImageReader(buffer), x, y, w, h)
    c.restoreState()
    return True


def _image_width(path):
    try:
        with PilImage.open(path) as image:
            return image.width
    except (OSError, ValueError):
        return 0


def _fetch_tile(session, x, y, zoom):
    url = settings.MAP_TILE_URL.format(z=zoom, x=x, y=y)
    response = session.get(url, timeout=settings.EXTERNAL_HTTP_TIMEOUT)
    response.raise_for_status()
    tile = PilImage.open(BytesIO(response.content))
    tile.load()
    return tile.convert('RGB')


def _world_pixel(lat, lng, zoom, tile_size):
    """Coordenadas en píxeles del mundo (Web Mercator) del punto, al zoom dado."""
    scale = tile_size * 2 ** zoom
    sin_lat = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    x = (lng + 180) / 360 * scale
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def _draw_pin(image, x, y, height):
    """Pin de la marca con la punta en (x, y), suavizado dibujándolo a 4x y reduciéndolo."""
    ss = 4
    width = height * 36 / 46
    layer = PilImage.new('RGBA', (round(width * ss), round(height * ss)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    unit = height * ss / 46  # el pin del sitio mide 36×46 (static/js/habitta/app.js)

    def drop(radius, tip, color):
        cx, cy, tip = 18 * unit, 18 * unit, tip * unit
        reach = math.acos(min(radius / (tip - cy), 1))  # ángulo de las tangentes desde la punta
        points = [
            (cx + radius * math.cos(math.pi / 2 + reach + i * (2 * math.pi - 2 * reach) / 48),
             cy + radius * math.sin(math.pi / 2 + reach + i * (2 * math.pi - 2 * reach) / 48))
            for i in range(49)
        ]
        draw.polygon(points + [(cx, tip)], fill=color)

    drop(16.25 * unit, 45.5, '#ffffff')  # borde blanco
    drop(13.75 * unit, 42.5, '#0B6E5F')
    dot = 5.5 * unit
    draw.ellipse((18 * unit - dot, 18 * unit - dot, 18 * unit + dot, 18 * unit + dot), fill='#ffffff')
    layer = layer.resize((round(width), round(height)), PilImage.LANCZOS)
    image.paste(layer, (round(x - width / 2), round(y - height)), layer)


def _draw_attribution(image, text):
    if not text:
        return
    size = max(14, image.width // 44)
    try:
        font = ImageFont.truetype(os.path.join(FONT_DIR, 'PlusJakartaSans-SemiBold.ttf'), size)
    except OSError:
        font = ImageFont.load_default(size=size)
    draw = ImageDraw.Draw(image, 'RGBA')
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    pad = size // 2
    box = (image.width - (right - left) - 2 * pad, image.height - (bottom - top) - 2 * pad, image.width, image.height)
    draw.rectangle(box, fill=(255, 255, 255, 200))
    draw.text((box[0] + pad - left, box[1] + pad - top), text, font=font, fill=(60, 72, 68, 255))


def _render_static_map(obj):
    """Mapa del punto del anuncio armado con tiles raster (OpenStreetMap por defecto), o None si falla."""
    if not settings.MAP_TILE_URL:
        return None
    scale = 2 if settings.MAP_TILE_SCALE == 2 else 1
    tile_size = TILE_SIZE * scale
    width, height = MAP_VIEW[0] * scale, MAP_VIEW[1] * scale
    cx, cy = _world_pixel(obj.geopoint.y, obj.geopoint.x, MAP_ZOOM, tile_size)
    left, top = cx - width / 2, cy - height / 2
    count = 2 ** MAP_ZOOM

    image = PilImage.new('RGB', (width, height), '#F7F4EF')
    session = requests.Session()
    session.headers['User-Agent'] = settings.GEO_USER_AGENT
    try:
        for tx in range(math.floor(left / tile_size), math.floor((left + width - 1) / tile_size) + 1):
            for ty in range(math.floor(top / tile_size), math.floor((top + height - 1) / tile_size) + 1):
                if not 0 <= ty < count:
                    continue
                tile = _fetch_tile(session, tx % count, ty, MAP_ZOOM)
                if tile.size != (tile_size, tile_size):
                    tile = tile.resize((tile_size, tile_size), PilImage.LANCZOS)
                image.paste(tile, (round(tx * tile_size - left), round(ty * tile_size - top)))
    except (requests.RequestException, OSError, ValueError):
        return None
    finally:
        session.close()

    if image.size != MAP_SIZE:
        image = image.resize(MAP_SIZE, PilImage.LANCZOS)
    _draw_pin(image, MAP_SIZE[0] / 2, MAP_SIZE[1] / 2, MAP_SIZE[1] * 0.135)
    _draw_attribution(image, settings.MAP_TILE_ATTRIBUTION)
    return image


def _map_source(obj):
    """Ruta del mapa estático del anuncio (se guarda como imagen `map` para no pedirlo cada vez)."""
    if not obj.category.require_location or not obj.geopoint:
        return None
    saved = obj.get_last_image_by_code('map')
    cached = saved.img.path if saved and saved.img and os.path.isfile(saved.img.path) else None
    if cached and _image_width(cached) >= MAP_MIN_WIDTH:
        return cached
    fresh = _render_static_map(obj)
    if fresh is not None:
        return obj.update_image(fresh, 'map').img.path
    return cached


# ----------------------------------------------------------------------------- datos

def _title(obj):
    title = ' '.join((obj.title or '').split())
    return title.lower().capitalize() if title else obj.category.singular_name


def _activity(obj):
    activity = getattr(obj.get_purpose(), 'activity', '')
    return activity if activity and activity != 'No definido' else ''


def _where(obj):
    address = ' '.join((obj.address or '').split())
    if obj.category.require_location:
        return address
    return 'Atiende en tu zona' + (' · %s' % address if address else '')


def _features(obj):
    """(nombre, valor) de las especificaciones llenas, sin archivos ni el precio, en el orden de los grupos."""
    values = (obj.details or {}).get('specifications') or {}
    price_name = (obj.category.price_area or '').strip().lower()
    items, seen = [], set()
    for group in obj.category.groups.all().order_by('groupcategory__sequence'):
        for spc in group.specifications.all():
            if spc.pk in seen or 'FileField' in spc.field_type:
                continue
            seen.add(spc.pk)
            if price_name and (spc.internal_name or '').strip().lower() == price_name:
                continue
            value = values.get(str(spc.pk))
            text = ' '.join(str(value).split()) if value is not None else ''
            if text.lower() in NO_VALUES:
                continue
            items.append((spc.name, spec_value(text)))
    return items


# ----------------------------------------------------------------------------- secciones

def _header(c, obj):
    top = PAGE_H - MARGIN
    logo_h = 28
    if os.path.isfile(LOGO_PATH):
        c.drawImage(LOGO_PATH, MARGIN, top - logo_h, logo_h * LOGO_RATIO, logo_h, mask='auto')
    else:
        c.setFillColor(PRIMARY)
        c.setFont(_font('extrabold'), 22)
        c.drawString(MARGIN, top - logo_h + 6, settings.SITE_NAME)

    pill_y = top - logo_h + (logo_h - 19) / 2
    right = PAGE_W - MARGIN
    activity = _activity(obj)
    if activity:
        right = _pill(c, activity, right, pill_y, white, SECONDARY) - 6
    _pill(c, obj.category.singular_name, right, pill_y, PRIMARY, PRIMARY_SOFT)

    line_y = top - logo_h - 12
    c.setStrokeColor(BASE_300)
    c.setLineWidth(1)
    c.line(MARGIN, line_y, PAGE_W - MARGIN, line_y)
    return line_y


def _cover(c, obj, x, y, w, h):
    path = obj.get_cover_path()
    if path and os.path.isfile(path) and _draw_image_cover(c, path, x, y, w, h, radius=14):
        return
    c.setFillColor(BASE_200)
    c.roundRect(x, y, w, h, 14, stroke=0, fill=1)
    c.setFillColor(MUTED)
    c.setFont(_font('semibold'), 11)
    c.drawCentredString(x + w / 2, y + h / 2 - 4, 'Sin foto de portada')


def _title_block(c, obj, top):
    """Título y ubicación a la izquierda, precio a la derecha. Devuelve dónde termina."""
    price = obj.get_price_value()
    price_text, price_size = (money(price), 22) if price is not None else ('A convenir', 16)
    price_w = stringWidth(price_text, _font('extrabold'), price_size)
    text_w = CONTENT_W - max(price_w, 70) - 24

    right = PAGE_W - MARGIN
    c.setFillColor(MUTED)
    c.setFont(_font('bold'), 7.5)
    c.drawRightString(right, top - 8, 'PRECIO', charSpace=0.8)
    c.setFillColor(PRIMARY)
    c.setFont(_font('extrabold'), price_size)
    c.drawRightString(right, top - 8 - price_size - 4, price_text)

    y = top - 18
    c.setFillColor(NEUTRAL)
    c.setFont(_font('extrabold'), 19)
    for line in _lines(_title(obj), _font('extrabold'), 19, text_w, 2):
        c.drawString(MARGIN, y, line)
        y -= 23

    where = _where(obj)
    if where:
        c.setFillColor(MUTED)
        c.setFont(_font('regular'), 10)
        c.drawString(MARGIN, y + 5, _fit(where, _font('regular'), 10, text_w))
        y -= 12
    return min(y, top - 44)


def _body(c, obj, top, bottom):
    """Descripción (izquierda) y características (derecha, o a todo el ancho si no hay descripción)."""
    description = ' '.join((obj.description or '').split())
    features = _features(obj)
    if not description and not features:
        return

    feat_w = 205 if description else CONTENT_W
    desc_w = CONTENT_W - (feat_w + 28 if features else 0)

    if description:
        _label(c, 'Descripción', MARGIN, top)
        size, leading = 9.5, 13.5
        max_lines = int((top - 14 - bottom) // leading)
        c.setFillColor(NEUTRAL)
        c.setFont(_font('regular'), size)
        y = top - 16
        for line in _lines(description, _font('regular'), size, desc_w, max_lines):
            c.drawString(MARGIN, y, line)
            y -= leading

    if features:
        left = PAGE_W - MARGIN - feat_w
        _label(c, 'Características', left, top)
        columns = 1 if description else 2
        col_gap = 24
        col_w = (feat_w - col_gap * (columns - 1)) / columns
        row_h = 17
        rows = max(0, int((top - 12 - bottom) // row_h))
        for index, (name, value) in enumerate(features[:rows * columns]):
            col, row = index // rows, index % rows
            x = left + col * (col_w + col_gap)
            y = top - 18 - row * row_h
            value_w = stringWidth(value, _font('semibold'), 9)
            value_w = min(value_w, col_w * 0.55)
            c.setFillColor(MUTED)
            c.setFont(_font('regular'), 9)
            c.drawString(x, y, _fit(name, _font('regular'), 9, col_w - value_w - 8))
            c.setFillColor(NEUTRAL)
            c.setFont(_font('semibold'), 9)
            c.drawRightString(x + col_w, y, _fit(value, _font('semibold'), 9, col_w * 0.55))
            c.setStrokeColor(BASE_300)
            c.setLineWidth(0.6)
            c.line(x, y - 6, x + col_w, y - 6)


def _card(c, x, y, w, h):
    c.setFillColor(BASE_200)
    c.roundRect(x, y, w, h, 12, stroke=0, fill=1)


def _contact_card(c, user, x, y, w, h):
    _card(c, x, y, w, h)
    pad = 14
    inner_w = w - 2 * pad
    top = y + h - pad
    _label(c, 'Anunciante', x + pad, top - 7)

    profile = getattr(user, 'profile', None)
    size = 40
    ax, ay = x + pad, top - 16 - size
    image = profile.image if profile and profile.image else None
    if not (image and os.path.isfile(image.path) and _draw_image_cover(c, image.path, ax, ay, size, size, circle=True)):
        c.setFillColor(PRIMARY)
        c.circle(ax + size / 2, ay + size / 2, size / 2, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont(_font('bold'), 14)
        c.drawCentredString(ax + size / 2, ay + size / 2 - 5, initials(user))

    name_x = ax + size + 10
    name_w = x + w - pad - name_x
    lines = _lines(user.get_full_name() or user.username, _font('bold'), 11.5, name_w, 2)
    c.setFillColor(NEUTRAL)
    c.setFont(_font('bold'), 11.5)
    y_name = ay + size / 2 + (len(lines) - 1) * 7 - 4
    for line in lines:
        c.drawString(name_x, y_name, line)
        y_name -= 14

    rows = []
    if profile and profile.phone:
        rows.append(('Teléfono', profile.phone))
    if user.email:
        rows.append(('Correo', user.email))
    if profile:
        socials = profile.socialnetworkprofile_set.select_related('social_network')
        for social in [s for s in socials if s.username.strip().lower() not in NO_VALUES][:3]:
            rows.append((social.social_network.name, social.username.strip()))

    # Con espacio suficiente, rótulo y valor en la misma línea; si no, uno sobre otro
    inline = inner_w >= 230
    row_h = 17 if inline else 24
    yy = ay - 18
    for label, value in rows:
        if yy - (0 if inline else 10) < y + pad - 2:
            break
        c.setFillColor(MUTED)
        c.setFont(_font('regular'), 8)
        if inline:
            c.drawString(x + pad, yy, label)
            c.setFillColor(NEUTRAL)
            c.setFont(_font('semibold'), 9.5)
            c.drawString(x + pad + 70, yy, _fit(value, _font('semibold'), 9.5, inner_w - 70))
        else:
            c.drawString(x + pad, yy, label)
            c.setFillColor(NEUTRAL)
            c.setFont(_font('semibold'), 9.5)
            c.drawString(x + pad, yy - 11, _fit(value, _font('semibold'), 9.5, inner_w))
        yy -= row_h


def _qr_card(c, url, x, y, w, h):
    _card(c, x, y, w, h)
    pad = 14
    qr_size = 84
    box = qr_size + 12
    bx = x + (w - box) / 2
    by = y + h - pad - box
    c.setFillColor(white)
    c.roundRect(bx, by, box, box, 8, stroke=0, fill=1)

    qr = qrcode.QRCode(border=0, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = BytesIO()
    qr.make_image(fill_color='#13211E', back_color='white').save(buffer)
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), bx + 6, by + 6, qr_size, qr_size)

    inner_w = w - 2 * pad
    yy = by - 14
    c.setFillColor(NEUTRAL)
    c.setFont(_font('bold'), 8.5)
    for line in _lines('Escanea para ver el anuncio', _font('bold'), 8.5, inner_w, 2):
        c.drawCentredString(x + w / 2, yy, line)
        yy -= 11
    short = url.split('://', 1)[-1]
    c.setFillColor(MUTED)
    c.setFont(_font('regular'), 7)
    for line in _char_lines(short, _font('regular'), 7, inner_w, 2):
        c.drawCentredString(x + w / 2, yy - 1, line)
        yy -= 9


def _bottom_row(c, obj, url, y):
    map_path = _map_source(obj)
    qr_w = 128
    map_w = 196 if map_path else 0
    contact_w = CONTENT_W - qr_w - GAP - (map_w + GAP if map_w else 0)
    x = MARGIN
    if map_path:
        if _draw_image_cover(c, map_path, x, y, map_w, ROW_H, radius=12):
            x += map_w + GAP
        else:
            contact_w += map_w + GAP
    _contact_card(c, obj.user, x, y, contact_w, ROW_H)
    _qr_card(c, url, x + contact_w + GAP, y, qr_w, ROW_H)


def _footer(c, base_url):
    c.setFillColor(NEUTRAL)
    c.rect(0, 0, PAGE_W, FOOTER_H, stroke=0, fill=1)
    domain = urlsplit(base_url).netloc or base_url.split('://', 1)[-1]
    parts = [domain, settings.CONTACT_PHONE, settings.CONTACT_EMAIL]
    y = FOOTER_H / 2 - 3
    c.setFillColor(BASE_200)
    c.setFont(_font('extrabold'), 9.5)
    c.drawString(MARGIN, y, settings.SITE_NAME)
    name_w = stringWidth(settings.SITE_NAME, _font('extrabold'), 9.5)
    details = '  ·  '.join(part for part in parts if part)
    if details:
        c.setFillColor(FOOTER_MUTED)
        c.setFont(_font('regular'), 8)
        c.drawString(MARGIN + name_w + 10, y, _fit(details, _font('regular'), 8, CONTENT_W - name_w - 130))
    c.setFillColor(FOOTER_MUTED)
    c.setFont(_font('regular'), 8)
    c.drawRightString(PAGE_W - MARGIN, y, 'Generado el %s' % timezone.localdate().strftime('%d/%m/%Y'))


def get_pdf(obj, base_url=''):
    """PDF (bytes) del anuncio `obj`; `base_url` es la URL pública del sitio, sin barra final."""
    base_url = (base_url or settings.SITE_URL or '').rstrip('/')
    url = '%s%s' % (base_url, obj.get_absolute_url())

    buffer = BytesIO()
    c = Canvas(buffer, pagesize=A4)
    c.setTitle('%s · %s' % (_title(obj), settings.SITE_NAME))
    c.setAuthor(settings.SITE_NAME)
    c.setSubject(url)
    # Fondo blanco explícito: sin él, algunos visores y conversores muestran la página transparente
    c.setFillColor(white)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    line_y = _header(c, obj)
    cover_h = CONTENT_W * 9 / 16
    cover_y = line_y - 14 - cover_h
    _cover(c, obj, MARGIN, cover_y, CONTENT_W, cover_h)
    body_top = _title_block(c, obj, cover_y - 14)
    row_y = FOOTER_H + 16
    _body(c, obj, body_top - 14, row_y + ROW_H + 14)
    _bottom_row(c, obj, url, row_y)
    _footer(c, base_url)
    c.save()
    return buffer.getvalue()
