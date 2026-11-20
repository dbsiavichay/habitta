"""Callbacks del admin (config/unfold.py): dashboard de inicio, insignias del menú y entorno.

Cada bloque del dashboard se arma sólo si el usuario puede ver ese modelo, así un staff con
permisos parciales no ve números de lo que no administra.
"""
import json
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import format_html

from apps.auctions.models import Auction
from apps.payments.models import BankPayment, Payment
from apps.realty.models import Category, Property

from .templatetags.habitta import money

RECENT_DAYS = 30
CHART_MONTHS = 12
TABLE_ROWS = 5


# ---------- Entorno y menú ----------

def environment_callback(request):
    """Etiqueta junto al título del admin para no confundir el entorno local con producción."""
    if settings.DEBUG:
        return ['Desarrollo', 'warning']
    return None


def environment_title_prefix(request):
    return '[Desarrollo]' if settings.DEBUG else None


def pending_bank_payments_badge(request):
    """Transferencias que esperan revisión (insignia del menú). None oculta la insignia."""
    return BankPayment.objects.filter(status=Payment.REGISTRY).count() or None


# ---------- Dashboard ----------

def dashboard_callback(request, context):
    user = request.user
    since = timezone.now() - timedelta(days=RECENT_DAYS)
    can = lambda perm: user.has_perm(perm)  # noqa: E731

    context.update({
        'greeting_name': user.first_name or user.get_username(),
        'kpis': _kpis(can, since),
        'activity': _activity_chart(can),
        'pending_payments': _pending_payments_table() if can('payments.view_bankpayment') else None,
        'latest_properties': _latest_properties_table() if can('realty.view_property') else None,
        'top_categories': _top_categories() if can('realty.view_category') else None,
    })
    return context


def _changelist(model, query=''):
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
    return f'{url}?{query}' if query else url


def _change(obj):
    return reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])


def _when(value):
    """Celda de fecha corta que no se parte en varias líneas (la hora completa está en el detalle)."""
    return {'content': date_format(timezone.localtime(value), 'j M Y'), 'class': 'whitespace-nowrap'}


def _kpis(can, since):
    kpis = []
    if can('payments.view_bankpayment'):
        pending = BankPayment.objects.filter(status=Payment.REGISTRY).count()
        kpis.append({
            'title': 'Pagos pendientes',
            'value': pending,
            'footer': 'Transferencias por confirmar' if pending else 'Ninguna transferencia por confirmar',
            'icon': 'account_balance',
            'href': _changelist(BankPayment, f'status__exact={Payment.REGISTRY}'),
            'alert': bool(pending),
        })
    if can('realty.view_property'):
        kpis.append({
            'title': 'Publicaciones',
            'value': Property.objects.count(),
            'footer': _recent_text(Property.objects.filter(pub_date__gte=since).count(), 'nueva', 'nuevas'),
            'icon': 'home_work',
            'href': _changelist(Property),
        })
    if can('auth.view_user'):
        kpis.append({
            'title': 'Usuarios',
            'value': User.objects.count(),
            'footer': _recent_text(User.objects.filter(date_joined__gte=since).count(), 'registro', 'registros'),
            'icon': 'group',
            'href': _changelist(User),
        })
    if can('auctions.view_auction'):
        # El cierre de subastas es perezoso: se cierran las vencidas antes de contar (igual que el sitio).
        Auction.objects.close_expired()
        open_auctions = Auction.objects.filter(stage=Auction.OPEN).count()
        kpis.append({
            'title': 'Subastas abiertas',
            'value': open_auctions,
            'footer': 'Con fecha de cierre por delante' if open_auctions else 'Ninguna en curso',
            'icon': 'gavel',
            'href': None,  # el admin de subastas llega en la fase B
        })
    return kpis


def _recent_text(count, singular, plural):
    if not count:
        return f'Sin {plural} en {RECENT_DAYS} días'
    return f'+{count} {singular if count == 1 else plural} en {RECENT_DAYS} días'


def _month_starts(months):
    today = timezone.localdate()
    year, month = today.year, today.month
    starts = []
    for _ in range(months):
        starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(starts))


def _monthly_counts(queryset, field, starts):
    rows = (
        queryset.filter(**{f'{field}__date__gte': starts[0]})
        .annotate(month=TruncMonth(field)).values('month').annotate(n=Count('id')).order_by()
    )
    # Con USE_TZ, TruncMonth devuelve el inicio de mes como datetime consciente en la zona actual.
    by_month = {timezone.localtime(row['month']).date(): row['n'] for row in rows}
    return [by_month.get(start, 0) for start in starts]


def _activity_chart(can):
    """Publicaciones y registros por mes (últimos 12 meses), para el gráfico de líneas de Unfold."""
    series = []
    starts = _month_starts(CHART_MONTHS)
    if can('realty.view_property'):
        series.append(('Publicaciones', _monthly_counts(Property.objects, 'pub_date', starts), 'var(--color-primary-600)'))
    if can('auth.view_user'):
        series.append(('Usuarios nuevos', _monthly_counts(User.objects, 'date_joined', starts), '#c8502e'))
    if not series:
        return None

    datasets = [
        {'label': label, 'data': data, 'borderColor': color, 'backgroundColor': color}
        for label, data, color in series
    ]
    return {
        'data': json.dumps({
            # El año sólo en el primer mes y en enero, para que las etiquetas no se roten.
            'labels': [date_format(start, 'M Y' if i == 0 or start.month == 1 else 'M')
                       for i, start in enumerate(starts)],
            'datasets': datasets,
        }),
        'legend': [{'label': label, 'color': color, 'total': sum(data)} for label, data, color in series],
        'empty': not any(sum(data) for _, data, _ in series),
    }


def _pending_payments_table():
    payments = (
        BankPayment.objects.filter(status=Payment.REGISTRY)
        .select_related('user', 'bank').order_by('-date')[:TABLE_ROWS]
    )
    return {
        'headers': ['Usuario', 'Monto', 'Banco', 'Fecha'],
        'rows': [
            [
                format_html('<a href="{}" class="font-medium text-primary-600 dark:text-primary-500">{}</a>',
                            _change(payment), payment.user.get_full_name() or payment.user.get_username()),
                money(payment.amount),
                payment.bank.name,
                _when(payment.date),
            ]
            for payment in payments
        ],
    }


def _latest_properties_table():
    properties = Property.objects.select_related('category', 'user').order_by('-pub_date')[:TABLE_ROWS]
    return {
        'headers': ['Publicación', 'Categoría', 'Propietario', 'Fecha'],
        'rows': [
            [
                format_html('<a href="{}" class="font-medium text-primary-600 dark:text-primary-500">{}</a>',
                            _change(prop), prop),
                prop.category.name,
                prop.user.get_full_name() or prop.user.get_username(),
                _when(prop.pub_date),
            ]
            for prop in properties
        ],
    }


def _top_categories():
    categories = list(
        Category.objects.annotate(total=Count('property')).filter(total__gt=0)
        .order_by('-total', 'name')[:TABLE_ROWS]
    )
    if not categories:
        return []
    top = categories[0].total
    return [
        {
            'name': category.name,
            'total': category.total,
            'percent': round(category.total * 100 / top),
            'href': _changelist(Property, f'category__id__exact={category.pk}'),
        }
        for category in categories
    ]
