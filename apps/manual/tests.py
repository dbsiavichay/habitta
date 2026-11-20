"""Pruebas de los manuales de uso (/manual/).

    docker compose exec web python manage.py test apps.manual.tests
"""
import re
from pathlib import Path
from unittest import mock

from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.manual.content import MANUALS, SCREENS, render_markdown
from apps.project.testing import create_user

FIGURE_RE = re.compile(r"{%\s*figura\s+'([^']+)'")


class ManualPagesTests(TestCase):
    def test_hub_and_indexes_are_public(self):
        response = self.client.get(reverse('manual'))
        self.assertEqual(response.status_code, 200)
        for manual in MANUALS.values():
            self.assertContains(response, manual.get_absolute_url())
            with self.subTest(manual=manual.slug):
                response = self.client.get(manual.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                for chapter in manual.chapters:
                    self.assertContains(response, manual.chapter_url(chapter))

    def test_every_chapter_renders_for_visitors(self):
        """También valida los {% url %} de cada capítulo (un nombre roto da NoReverseMatch)."""
        for manual in MANUALS.values():
            for chapter in manual.chapters:
                with self.subTest(chapter=f'{manual.slug}/{chapter.slug}'):
                    response = self.client.get(manual.chapter_url(chapter))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, chapter.title)
                    self.assertContains(response, 'prose-manual')
                    self.assertNotIn('larbit', response.content.decode().lower())

    def test_unknown_manual_or_chapter_is_404(self):
        self.assertEqual(self.client.get('/manual/inexistente/').status_code, 404)
        self.assertEqual(self.client.get('/manual/usuarios/inexistente/').status_code, 404)

    def test_neighbors(self):
        for manual in MANUALS.values():
            first, last = manual.chapters[0], manual.chapters[-1]
            self.assertIsNone(manual.neighbors(first)[0])
            self.assertIsNone(manual.neighbors(last)[1])
            for previous, following in zip(manual.chapters, manual.chapters[1:]):
                self.assertEqual(manual.neighbors(following)[0], previous)
                self.assertEqual(manual.neighbors(previous)[1], following)

    def test_chapter_shows_table_of_contents(self):
        manual = MANUALS['usuarios']
        response = self.client.get(manual.chapter_url(manual.chapters[0]))
        self.assertContains(response, 'En esta página')
        self.assertContains(response, 'href="#crea-tu-cuenta"')

    def test_admin_manual_offers_admin_link_only_to_staff(self):
        manual = MANUALS['administracion']
        url = manual.chapter_url(manual.chapters[0])
        admin_url = reverse('admin:index')
        self.assertNotContains(self.client.get(url), 'Ir a la administración')
        self.client.force_login(create_user('equipo', is_staff=True))
        response = self.client.get(url)
        self.assertContains(response, 'Ir a la administración')
        self.assertContains(response, f'href="{admin_url}"')


class ManualContentTests(TestCase):
    def chapter_sources(self):
        for manual in MANUALS.values():
            for chapter in manual.chapters:
                path = Path(get_template(manual.template_name(chapter)).origin.name)
                yield f'{manual.slug}/{chapter.slug}', path.read_text()

    def test_figures_exist(self):
        for name, source in self.chapter_sources():
            for path in FIGURE_RE.findall(source):
                with self.subTest(chapter=name, figure=path):
                    self.assertTrue(finders.find(f'manual/{path}'), f'Falta static/manual/{path}')

    def test_figure_has_size_and_zoom(self):
        request = RequestFactory().get('/')
        manual = MANUALS['usuarios']
        html, _ = render_markdown(manual.template_name(manual.chapters[0]), request)
        self.assertRegex(str(html), r'<figure class="manual-figure"><a href="[^"]+\.webp" data-pswp-width="\d+" data-pswp-height="\d+"')

    def test_demo_notes_follow_integrations(self):
        request = RequestFactory().get('/')
        with self.settings(EMAIL_HOST=''):
            html, _ = render_markdown('manual/demo.md', request)
            self.assertIn('no envía correos', html)
        with self.settings(EMAIL_HOST='smtp.ejemplo.com'):
            html, _ = render_markdown('manual/demo.md', request)
            self.assertNotIn('no envía correos', html)

    def test_screens_point_to_existing_urls(self):
        from django.urls import get_resolver

        names = {name for name in get_resolver().reverse_dict.keys() if isinstance(name, str)}
        for screen in SCREENS:
            self.assertIn(screen, names, f'"{screen}" no es un nombre de URL')


class ManualLinksTests(TestCase):
    def test_footer_and_help_link_to_manuals(self):
        self.assertContains(self.client.get(reverse('home')), f'href="{reverse("manual")}"')
        response = self.client.get(reverse('help'))
        for manual in MANUALS.values():
            self.assertContains(response, manual.get_absolute_url())

    def test_auth_pages_link_to_their_chapter(self):
        manual, chapter = SCREENS['login']
        self.assertContains(self.client.get(reverse('login')), f'href="{manual.chapter_url(chapter)}"')
        with mock.patch.dict(SCREENS, clear=True):
            self.assertContains(self.client.get(reverse('login')), f'href="{reverse("manual")}"')

    def test_panel_links_to_user_manual(self):
        self.client.force_login(create_user('ana'))
        response = self.client.get(reverse('properties'))
        self.assertContains(response, MANUALS['usuarios'].get_absolute_url())
        self.assertContains(response, f'href="{reverse("manual")}"')  # menú de la cuenta

    def test_contextual_help_link(self):
        """Las pantallas del panel listadas en `screens` muestran "¿Cómo funciona?" hacia su capítulo."""
        self.client.force_login(create_user('ana'))
        manual = MANUALS['usuarios']
        chapter = manual.chapters[-1]
        with mock.patch.dict(SCREENS, {'choose_category': (manual, chapter)}):
            response = self.client.get(reverse('choose_category'))
            self.assertContains(response, '¿Cómo funciona?')
            self.assertContains(response, f'href="{manual.chapter_url(chapter)}"')
        with mock.patch.dict(SCREENS, clear=True):
            self.assertNotContains(self.client.get(reverse('choose_category')), '¿Cómo funciona?')

    def test_admin_menu_links_to_admin_manual(self):
        from django.conf import settings

        url = str(MANUALS['administracion'].get_absolute_url())
        sidebar = settings.UNFOLD['SIDEBAR']['navigation']
        links = [str(item['link']) for section in sidebar for item in section['items']]
        self.assertIn(url, links)
        self.assertIn(url, [str(item['link']) for item in settings.UNFOLD['SITE_DROPDOWN']])

        self.client.force_login(create_user('equipo', is_staff=True, is_superuser=True))
        self.assertContains(self.client.get(reverse('admin:index')), url)
