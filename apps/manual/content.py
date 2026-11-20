"""Manuales de uso (/manual/): qué manuales hay, sus capítulos y en qué orden.

Cada capítulo es un archivo Markdown en `apps/manual/templates/manual/<manual>/<capitulo>.md`. Antes de
pasar por Markdown se renderiza como plantilla de Django, así que admite `{% url %}`, `{% static %}`,
`{% figura %}` y las variables de los context processors (`SITE_NAME`, `PAYPAL_ENABLED`…).
Ojo: `{#` abre un comentario de Django; para darle un id a un título usa `{: #id }`.

`screens` son los nombres de URL de las pantallas que explica el capítulo: el panel del usuario
muestra el enlace "¿Cómo funciona?" hacia el capítulo de la pantalla actual.
"""
from dataclasses import dataclass, field

import markdown
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe


@dataclass(frozen=True)
class Chapter:
    slug: str
    title: str
    summary: str
    icon: str
    screens: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class Manual:
    slug: str
    title: str
    audience: str
    lead: str
    icon: str
    chapters: tuple

    def get_absolute_url(self):
        return reverse('manual_index', kwargs={'manual': self.slug})

    def chapter(self, slug):
        return next((chapter for chapter in self.chapters if chapter.slug == slug), None)

    def chapter_url(self, chapter):
        return reverse('manual_chapter', kwargs={'manual': self.slug, 'chapter': chapter.slug})

    def template_name(self, chapter):
        return f'manual/{self.slug}/{chapter.slug}.md'

    def neighbors(self, chapter):
        """Capítulos anterior y siguiente (None en los extremos)."""
        index = self.chapters.index(chapter)
        previous = self.chapters[index - 1] if index > 0 else None
        following = self.chapters[index + 1] if index + 1 < len(self.chapters) else None
        return previous, following


USER_MANUAL = Manual(
    slug='usuarios',
    title='Manual del usuario',
    audience='Para quienes buscan, publican y conversan',
    lead='Todo lo que puedes hacer en el sitio: crear tu cuenta, buscar, publicar anuncios, conversar y pagar.',
    icon='book-open',
    chapters=(
        Chapter('primeros-pasos', 'Primeros pasos', 'Crea tu cuenta, completa tu perfil e inicia sesión.',
                'rocket', screens=('register', 'complete_register', 'login', 'password_reset', 'password_reset_done',
                                   'password_reset_confirm', 'password_reset_complete')),
        Chapter('buscar', 'Buscar y explorar', 'Encuentra inmuebles, servicios y empleos con el buscador y el explorador.',
                'search', screens=('finder', 'finder_without_map')),
        Chapter('ver-anuncio', 'Ver un anuncio', 'Fotos, detalles, contacto con quien publica y tus favoritos.',
                'house', screens=('detail_property', 'detail_profile', 'favorite_properties')),
        Chapter('publicar', 'Publicar un anuncio', 'El asistente paso a paso: categoría, datos, ubicación, portada y fotos.',
                'circle-plus', screens=('choose_category', 'add_property', 'property_photos')),
        Chapter('mis-publicaciones', 'Mis publicaciones', 'Edita, cambia las fotos, descarga el afiche o elimina tus anuncios.',
                'layout-grid', screens=('properties', 'update_property')),
        Chapter('mensajes', 'Mensajes', 'Conversa en tiempo real con quienes publican y con tus interesados.',
                'message-circle', screens=('conversations', 'detail_conversation')),
        Chapter('subastas', 'Subastas', 'Pon un anuncio en subasta y sigue las ofertas hasta que termine.',
                'gavel', screens=('auctions', 'add_auction')),
        Chapter('pagos', 'Pagos y descargas', 'Compra los archivos de un anuncio, registra tu pago y descárgalos.',
                'receipt-text', screens=('select_method_payment', 'add_bank_payment', 'list_bank_payment', 'downloads',
                                         'execute_paypal_payment')),
        Chapter('mi-cuenta', 'Mi cuenta', 'Tus datos, tu foto, tus redes y tu contraseña.',
                'user-round-cog', screens=('update_profile', 'change_password', 'change_password_done')),
    ),
)

ADMIN_MANUAL = Manual(
    slug='administracion',
    title='Manual de administración',
    audience='Para el equipo que opera el sitio',
    lead='Cómo usar la administración: confirmar pagos, revisar publicaciones, atender usuarios y mantener el catálogo.',
    icon='shield-check',
    chapters=(
        Chapter('acceso', 'Acceso y recorrido', 'Quién puede entrar, cómo está organizado el menú y cómo encontrar cualquier cosa.',
                'log-in'),
        Chapter('inicio', 'Inicio', 'El resumen del sitio: pagos pendientes, publicaciones, usuarios y subastas.',
                'layout-dashboard'),
        Chapter('pagos', 'Transferencias y pagos', 'Confirma o rechaza transferencias, consulta PayPal y administra las cuentas bancarias.',
                'landmark'),
        Chapter('publicaciones', 'Publicaciones', 'Busca anuncios, corrige su texto o su ubicación y elimínalos si hace falta.',
                'building-2'),
        Chapter('subastas', 'Subastas', 'Sigue las subastas y sus ofertas, y cancélalas si es necesario.',
                'gavel'),
        Chapter('usuarios', 'Usuarios y permisos', 'Atiende cuentas y decide quién entra a la administración y qué puede hacer.',
                'users'),
        Chapter('comunidad', 'Comunidad', 'Vistas y me gusta, comentarios antiguos y conversaciones privadas.',
                'messages-square'),
        Chapter('catalogo', 'Catálogo', 'Categorías, formularios, especificaciones y propósitos de los anuncios.',
                'tags'),
        Chapter('contenido', 'Contenido del sitio', 'Fondos, términos, preguntas frecuentes, redes sociales e íconos.',
                'file-text'),
    ),
)

MANUALS = {manual.slug: manual for manual in (USER_MANUAL, ADMIN_MANUAL)}

# Pantalla del sitio (nombre de URL) → (manual, capítulo) que la explica.
SCREENS = {
    screen: (manual, chapter)
    for manual in MANUALS.values()
    for chapter in manual.chapters
    for screen in chapter.screens
}

MARKDOWN_EXTENSIONS = ['toc', 'tables', 'attr_list', 'admonition', 'sane_lists', 'md_in_html']


def render_markdown(template_name, request, context=None):
    """Renderiza un .md como plantilla de Django y luego como Markdown.

    Devuelve el HTML y el índice de los títulos de segundo nivel: [{'id': …, 'name': …}].
    """
    context = {'EMAIL_ENABLED': bool(settings.EMAIL_HOST), **(context or {})}
    source = render_to_string(template_name, context, request=request)
    md = markdown.Markdown(extensions=MARKDOWN_EXTENSIONS, extension_configs={'toc': {'toc_depth': '2'}})
    html = md.convert(source)
    toc = [{'id': token['id'], 'name': token['name']} for token in md.toc_tokens]
    return mark_safe(html), toc
