"""Menú del panel del usuario (layouts/app.html).

Una sola definición para el sidebar de escritorio y los chips de móvil. Cada ítem se marca activo
cuando la vista actual es su `url_name` o alguna de sus subpáginas (`also`).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PanelItem:
    label: str
    url_name: str
    icon: str
    also: tuple = field(default_factory=tuple)
    badge: str = ''  # nombre de la variable de contexto con el contador (p. ej. unread_messages)

    def matches(self, url_name):
        return url_name == self.url_name or url_name in self.also


PANEL_MENU = (
    ('Publicaciones', (
        PanelItem('Mis publicaciones', 'properties', 'layout-grid', also=('update_property', 'property_photos')),
        PanelItem('Publicar', 'choose_category', 'circle-plus', also=('add_property',)),
        PanelItem('Favoritos', 'favorite_properties', 'heart'),
    )),
    ('Actividad', (
        PanelItem('Mensajes', 'conversations', 'message-circle', also=('detail_conversation',), badge='unread_messages'),
        PanelItem('Subastas', 'auctions', 'gavel', also=('add_auction',)),
    )),
    ('Pagos', (
        PanelItem('Mis pagos', 'list_bank_payment', 'receipt-text',
                  also=('add_bank_payment', 'select_method_payment', 'execute_paypal_payment')),
        PanelItem('Descargas', 'downloads', 'download'),
    )),
    ('Cuenta', (
        PanelItem('Mi perfil', 'update_profile', 'user-round-cog'),
        PanelItem('Contraseña', 'change_password', 'key-round', also=('change_password_done',)),
    )),
)
