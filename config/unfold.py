"""
Configuración del admin (django-unfold): marca, colores, menú por tareas y dashboard.

`build_unfold(site_name)` se llama desde settings. Las rutas y los estáticos van en lambdas porque
Unfold los evalúa por petición (al importar settings todavía no hay URLconf ni storage).
Documentación: https://unfoldadmin.com/docs/configuration/settings/
"""
from django.templatetags.static import static
from django.urls import reverse_lazy

# Escalas OKLCH generadas desde la paleta "Bosque y Terracota" (assets/tailwind/source.css):
# primary-600 es el verde de la marca (#0b6e5f) y base va de los cremas del tema claro (50–300)
# a los verdes casi negros del oscuro (800–950). Contraste verificado (AA): blanco sobre
# primary-600 6.2:1, primary-500 sobre base-900 4.8:1, base-500 sobre base-50 4.7:1.
COLORS = {
    'primary': {
        '50': 'oklch(97.5% 0.015 178.6)',
        '100': 'oklch(94.5% 0.032 178.6)',
        '200': 'oklch(89.5% 0.058 178.6)',
        '300': 'oklch(82.0% 0.090 178.6)',
        '400': 'oklch(69.0% 0.118 178.6)',
        '500': 'oklch(62.5% 0.114 178.6)',
        '600': 'oklch(48.3% 0.086 178.6)',
        '700': 'oklch(42.0% 0.076 178.6)',
        '800': 'oklch(36.0% 0.064 178.6)',
        '900': 'oklch(30.0% 0.052 178.6)',
        '950': 'oklch(22.0% 0.038 178.6)',
    },
    'base': {
        '50': 'oklch(96.8% 0.007 80.7)',
        '100': 'oklch(94.5% 0.010 80.7)',
        '200': 'oklch(92.1% 0.015 80.7)',
        '300': 'oklch(87.0% 0.015 80.0)',
        '400': 'oklch(70.0% 0.012 170.0)',
        '500': 'oklch(53.5% 0.015 179.0)',
        '600': 'oklch(44.0% 0.018 179.0)',
        '700': 'oklch(36.0% 0.020 176.0)',
        '800': 'oklch(28.5% 0.023 173.2)',
        '900': 'oklch(24.3% 0.020 173.5)',
        '950': 'oklch(20.6% 0.016 182.1)',
    },
}

DASHBOARD = 'apps.project.admin_dashboard'


def _can_view(app_label, model_name):
    perm = f'{app_label}.view_{model_name}'
    return lambda request: request.user.has_perm(perm)


def _model(title, icon, app_label, model_name, **extra):
    """Ítem del menú que lleva a la lista de un modelo; se oculta sin permiso de lectura."""
    return {
        'title': title,
        'icon': icon,
        'link': reverse_lazy(f'admin:{app_label}_{model_name}_changelist'),
        'permission': _can_view(app_label, model_name),
        **extra,
    }


MANUAL_URL = reverse_lazy('manual_index', kwargs={'manual': 'administracion'})

SIDEBAR_NAVIGATION = [
    {
        'items': [
            {'title': 'Inicio', 'icon': 'space_dashboard', 'link': reverse_lazy('admin:index')},
        ],
    },
    {
        'title': 'Operación',
        'separator': True,
        'items': [
            _model('Transferencias', 'account_balance', 'payments', 'bankpayment',
                   badge=f'{DASHBOARD}.pending_bank_payments_badge', badge_variant='warning'),
            _model('Pagos PayPal', 'credit_card', 'payments', 'paypalpayment'),
            _model('Publicaciones', 'home_work', 'realty', 'property'),
            _model('Subastas', 'gavel', 'auctions', 'auction'),
        ],
    },
    {
        'title': 'Comunidad',
        'separator': True,
        'items': [
            _model('Usuarios', 'group', 'auth', 'user'),
            _model('Vistas y me gusta', 'visibility', 'logs', 'log'),
            _model('Comentarios', 'forum', 'comments', 'comment'),
            # Mensajes privados: sólo superusuarios (apps/messenger/admin.py).
            _model('Conversaciones', 'chat', 'messenger', 'conversation',
                   permission=lambda request: request.user.is_superuser),
        ],
    },
    {
        'title': 'Catálogo',
        'separator': True,
        'items': [
            _model('Categorías', 'category', 'realty', 'category'),
            _model('Formularios', 'dynamic_form', 'realty', 'group'),
            _model('Especificaciones', 'tune', 'realty', 'specification'),
            _model('Propósitos', 'flag', 'realty', 'purpose'),
        ],
    },
    {
        'title': 'Contenido del sitio',
        'separator': True,
        'items': [
            _model('Portada y fondos', 'wallpaper', 'project', 'settings'),
            _model('Términos', 'gavel', 'project', 'term'),
            _model('Ayuda', 'help', 'project', 'help'),
            _model('Redes sociales', 'share', 'authentication', 'socialnetwork'),
            _model('Íconos', 'interests', 'project', 'icons'),
        ],
    },
    {
        'title': 'Sistema',
        'separator': True,
        'items': [
            _model('Bancos', 'account_balance_wallet', 'payments', 'bank'),
            _model('Grupos y permisos', 'admin_panel_settings', 'auth', 'group'),
            _model('Imágenes', 'photo_library', 'multimedia', 'image'),
        ],
    },
    {
        # No se llama "Ayuda" para no confundirla con las preguntas frecuentes de "Contenido del sitio".
        'title': 'Manuales',
        'separator': True,
        'items': [
            # Página pública del sitio (apps/manual): la ve todo el staff.
            {'title': 'Manual de administración', 'icon': 'menu_book', 'link': MANUAL_URL},
        ],
    },
]


def build_unfold(site_name):
    return {
        'SITE_TITLE': f'Administración de {site_name}',
        'SITE_HEADER': site_name,
        'SITE_SUBHEADER': 'Administración',
        'SITE_URL': '/',
        'SITE_ICON': lambda request: static('brand/habitta-mark.svg'),
        'SITE_FAVICONS': [
            {'rel': 'icon', 'type': 'image/svg+xml', 'href': lambda request: static('brand/favicon.svg')},
            {'rel': 'alternate icon', 'sizes': '32x32', 'href': lambda request: static('brand/favicon.ico')},
        ],
        'SITE_DROPDOWN': [
            {'icon': 'public', 'title': 'Ver el sitio', 'link': '/'},
            {'icon': 'person', 'title': 'Mi panel', 'link': reverse_lazy('properties')},
            {'icon': 'menu_book', 'title': 'Manual de administración', 'link': MANUAL_URL},
        ],
        'ENVIRONMENT': f'{DASHBOARD}.environment_callback',
        'ENVIRONMENT_TITLE_PREFIX': f'{DASHBOARD}.environment_title_prefix',
        'DASHBOARD_CALLBACK': f'{DASHBOARD}.dashboard_callback',
        'LOGIN': {
            'image': lambda request: static('brand/admin-login.svg'),
        },
        'STYLES': [
            lambda request: 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap',
            lambda request: static('css/admin.css'),
        ],
        'SCRIPTS': [
            lambda request: static('js/admin.js'),
        ],
        'BORDER_RADIUS': '12px',  # igual a --radius-field del sitio
        'COLORS': COLORS,
        # ⌘K / Ctrl+K: además del menú, busca registros en estos modelos (respeta los permisos).
        'COMMAND': {
            'search_models': ['auth.user', 'realty.property', 'payments.bankpayment',
                              'realty.category', 'realty.specification'],
            'show_history': True,
        },
        'SIDEBAR': {
            'show_search': True,
            'show_all_applications': False,
            'navigation': SIDEBAR_NAVIGATION,
        },
    }
