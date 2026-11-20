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
                'rocket', screens=('register', 'complete_register', 'login', 'password_reset')),
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
