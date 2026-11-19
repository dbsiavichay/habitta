"""Filtros y etiquetas de presentación del frontend de Habitta.

Uso: ``{% load habitta %}``
"""
import re

from django import template

register = template.Library()

# Ícono Lucide por tipo de categoría (Category.kind)
KIND_ICONS = {1: 'house', 2: 'wrench', 3: 'briefcase-business'}
KIND_LABELS = {1: 'Inmuebles', 2: 'Servicios', 3: 'Empleos'}


@register.filter
def money(value):
    """Formatea un precio en dólares al estilo de Ecuador: $120.000 o $45,50.

    Si el valor no es numérico (p. ej. la categoría no tiene precio) devuelve ''.
    Debe coincidir con habitta.formatPrice() de static/js/habitta/app.js.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ''
    if round(number * 100) % 100 == 0:
        text = f'{number:,.0f}'.replace(',', '.')
    else:
        text = f'{number:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    return f'${text}'


@register.filter
def initials(user):
    """Iniciales para el avatar de un usuario sin foto."""
    name = (user.get_full_name() or user.username or '?').strip()
    parts = [p for p in name.split() if p]
    letters = ''.join(p[0] for p in parts[:2]) or name[:1]
    return letters.upper()


@register.filter
def whatsapp_url(phone):
    """Enlace wa.me para un número de Ecuador (09xxxxxxxx → 5939xxxxxxxx). '' si no es válido."""
    digits = re.sub(r'\D', '', str(phone or ''))
    if digits.startswith('0') and len(digits) == 10:
        digits = '593' + digits[1:]
    elif len(digits) == 9 and digits.startswith('9'):
        digits = '593' + digits
    if len(digits) < 11:
        return ''
    return f'https://wa.me/{digits}'


@register.filter
def kind_icon(kind):
    return KIND_ICONS.get(kind, 'tag')


@register.filter
def kind_label(kind):
    return KIND_LABELS.get(kind, '')


@register.filter
def has_avatar(user):
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.image)


YES_VALUES = {'si', 'sí', 'yes', 'true', 'disponible'}
NO_VALUES = {'no', 'false', 'no disponible', 'ninguno', 'ninguna', '0', ''}


@register.filter
def spec_text(item):
    """Texto corto de una especificación para tarjetas: 'si' → nombre, número → '3 Habitación'.

    Devuelve '' si la especificación es negativa o vacía (para no mostrar 'No Disponible').
    """
    key = str(item.get('key', '')).strip()
    value = str(item.get('value', '')).strip()
    lowered = value.lower()
    if lowered in NO_VALUES:
        return ''
    if lowered in YES_VALUES:
        return key
    try:
        float(value.replace(',', '.'))
    except ValueError:
        return value
    # Cantidades cortas se leen "3 habitaciones"; números largos (teléfonos, códigos) "Whatsapp 0991…"
    if len(re.sub(r'\D', '', value)) >= 6:
        return f'{key} {value}'
    return f'{value} {key.lower()}'


@register.filter
def ago(value):
    """'hace 3 días' (sólo la unidad mayor)."""
    from django.utils.timesince import timesince

    if not value:
        return ''
    return f'hace {timesince(value, depth=1)}'


@register.filter
def spec_value(value):
    """Valor legible de una especificación: True/si → Sí, False/no → No."""
    text = str(value).strip()
    lowered = text.lower()
    if lowered in ('true', 'si', 'sí', 'yes'):
        return 'Sí'
    if lowered in ('false', 'no'):
        return 'No'
    return text


# Íconos propios de <c-icon> para redes sociales; el resto usa un globo genérico
SOCIAL_ICONS = {'facebook', 'instagram', 'twitter', 'x-twitter', 'whatsapp'}


@register.filter
def social_icon(network):
    """Ícono de <c-icon> para una SocialNetwork (su campo `icon` venía de Font Awesome 4)."""
    name = str(getattr(network, 'icon', network) or '').strip().lower().removeprefix('fa-')
    return name if name in SOCIAL_ICONS else 'globe'


@register.filter
def badge_count(value):
    """Contador corto para insignias: 0 → '', 12 → '9+'."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ''
    if number <= 0:
        return ''
    return '9+' if number > 9 else str(number)


@register.filter
def page_range(page_obj):
    """Números de página con elipsis (1 … 4 5 6 … 20) para <c-pagination>."""
    return page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)


WIZARD_STEPS = ('Categoría', 'Datos', 'Ubicación', 'Portada', 'Revisar', 'Fotos')


@register.simple_tag
def wizard_steps():
    """Pasos del asistente de publicación como [(1, 'Categoría'), …] para <c-panel.steps>."""
    return list(enumerate(WIZARD_STEPS, start=1))


@register.simple_tag(takes_context=True)
def panel_menu(context):
    """Secciones del menú del panel con la URL resuelta, el ítem activo y su contador."""
    from django.urls import reverse

    from apps.project.panel import PANEL_MENU

    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    current = match.url_name if match else ''
    sections = []
    for title, items in PANEL_MENU:
        sections.append({
            'title': title,
            'items': [
                {
                    'label': item.label,
                    'url': reverse(item.url_name),
                    'icon': item.icon,
                    'active': item.matches(current),
                    'badge': context.get(item.badge, 0) if item.badge else 0,
                }
                for item in items
            ],
        })
    return sections
