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
