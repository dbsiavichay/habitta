"""Piezas compartidas por los ModelAdmin (Unfold): columnas de usuario, enlaces y vistas previas.

El HTML que se arma aquí lo pinta el CSS compilado de Unfold, no el nuestro: sólo se usan clases que
existen en `unfold/static/unfold/css/styles.css` y, para lo demás, estilos en línea.
"""
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django_htmx.http import HttpResponseClientRedirect

from apps.project.templatetags.habitta import initials

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')


def user_header(user):
    """Valor para `@display(header=True)`: nombre, correo y foto (o iniciales)."""
    name = user.get_full_name() or user.get_username()
    picture = None
    profile = getattr(user, 'profile', None)
    if profile is not None and profile.image:
        picture = {'path': profile.image.url}
    return [name, user.email, initials(user), picture]


def short_date(value):
    """Fecha corta para columnas ("5 Feb 2020"); la hora completa queda en el detalle."""
    return date_format(timezone.localtime(value), 'j M Y') if value else None


def short_datetime(value):
    """Fecha y hora cortas ("5 Feb 2020, 15:34") para campos de sólo lectura o columnas donde importa la hora."""
    return date_format(timezone.localtime(value), 'j M Y, H:i') if value else None


def label_html(text, variant=None):
    """Insignia de Unfold como HTML: `@display(label=…)` no se aplica a los campos de sólo lectura del detalle."""
    return render_to_string('unfold/helpers/label.html', {'text': text, 'type': variant})


class ReadOnlyChangeFormMixin:
    """Para fichas sin campos editables (todo se hace con acciones): oculta los botones de guardar."""

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = {
            'show_save': False, 'show_save_and_continue': False, 'show_save_and_add_another': False,
            **(extra_context or {}),
        }
        return super().changeform_view(request, object_id, form_url, extra_context)


def admin_url(obj, view='change'):
    opts = obj._meta
    return reverse(f'admin:{opts.app_label}_{opts.model_name}_{view}', args=[obj.pk])


def admin_link(obj, text=None):
    if obj is None:
        return '—'
    return format_html('<a href="{}" class="font-medium text-primary-600 dark:text-primary-500">{}</a>',
                       admin_url(obj), text or obj)


def site_link(obj, text='Ver en el sitio'):
    """Enlace a la página pública del objeto, en otra pestaña."""
    if obj is None or not hasattr(obj, 'get_absolute_url'):
        return '—'
    return format_html(
        '<a href="{}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 font-medium '
        'text-primary-600 dark:text-primary-500">{}<span class="material-symbols-outlined text-sm">open_in_new</span></a>',
        obj.get_absolute_url(), text,
    )


def is_image(fieldfile):
    return bool(fieldfile) and fieldfile.name.lower().endswith(IMAGE_EXTENSIONS)


def image_preview(fieldfile, height=160):
    """Miniatura que abre la imagen completa; '—' si no hay archivo."""
    if not fieldfile:
        return '—'
    return format_html(
        '<a href="{0}" target="_blank" rel="noopener"><img src="{0}" alt="" loading="lazy" '
        'style="max-height:{1}px;max-width:100%;border-radius:12px;object-fit:cover" '
        'class="border border-base-200 dark:border-base-700"></a>',
        fieldfile.url, height,
    )


def thumbnail(url, size=40):
    return format_html(
        '<img src="{}" alt="" loading="lazy" style="width:{}px;height:{}px;object-fit:cover;border-radius:8px" '
        'class="border border-base-200 dark:border-base-700">',
        url, size, size,
    )


def back_to_page(request, fallback):
    """Respuesta tras una acción: vuelve a la página donde se abrió (con sus filtros).

    Las acciones con diálogo llegan por htmx; ahí hace falta HX-Redirect para recargar la página entera
    (los mensajes de Django se ven al volver).
    """
    url = request.headers.get('HX-Current-URL') or request.META.get('HTTP_REFERER') or ''
    if not url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        url = fallback
    if request.headers.get('HX-Request'):
        return HttpResponseClientRedirect(url)
    return HttpResponseRedirect(url)


def message_count(request, count, singular, plural, level=messages.SUCCESS):
    if count:
        messages.add_message(request, level, singular if count == 1 else plural.format(count=count))
