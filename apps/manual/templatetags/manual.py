"""Etiquetas de los manuales de uso.

    {% load manual %}
    {% figura 'usuarios/registro.webp' 'Formulario de registro' %}          captura a todo el ancho
    {% figura 'usuarios/ingresar.webp' 'En el celular' 'angosta' %}         captura de celular o recorte, más angosta
    {% manual_help_for_view as help %}                                    capítulo de la pantalla actual
"""
from functools import lru_cache

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import format_html

from apps.manual.content import SCREENS

register = template.Library()


@lru_cache(maxsize=256)
def image_size(path):
    """Ancho y alto de una imagen estática, para reservar su espacio antes de que cargue."""
    from PIL import Image

    found = finders.find(path)
    if not found:
        return None
    with Image.open(found) as image:
        return image.size


@register.simple_tag
def figura(path, caption, variant=''):
    """Captura de pantalla de `static/manual/<path>` con pie de foto; se amplía con PhotoSwipe.

    Va sola en su párrafo (con líneas en blanco antes y después) para que Markdown la deje tal cual.
    """
    static_path = f'manual/{path}'
    url = static(static_path)
    size = image_size(static_path)
    width, height = size if size else ('', '')
    css_class = 'manual-figure manual-figure--narrow' if variant == 'angosta' else 'manual-figure'
    return format_html(
        '<figure class="{}"><a href="{}" data-pswp-width="{}" data-pswp-height="{}" target="_blank" rel="noopener">'
        '<img src="{}" alt="{}" width="{}" height="{}" loading="lazy" decoding="async"></a>'
        '<figcaption>{}</figcaption></figure>',
        css_class, url, width, height, url, caption, width, height, caption,
    )


@register.simple_tag(takes_context=True)
def manual_help_for_view(context):
    """Capítulo del manual que explica la pantalla actual: {'url': …, 'title': …} o None."""
    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    found = SCREENS.get(match.url_name) if match else None
    if not found:
        return None
    manual, chapter = found
    return {'url': manual.chapter_url(chapter), 'title': chapter.title}
