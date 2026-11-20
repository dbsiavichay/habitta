"""Pruebas del panel de publicaciones (fase 3): listas, asistente de publicación, fotos y favoritos.

    docker compose exec web python manage.py test apps.realty.tests
"""
import base64
import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from PIL import Image as PILImage

from apps.logs.models import Log
from apps.multimedia.models import Image
from apps.project.testing import create_category, create_listing, create_user
from apps.realty.models import Category, GroupCategory, Property, Specification

MEDIA_ROOT = tempfile.mkdtemp(prefix='habitta-tests-')


def tearDownModule():
    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)


class PanelPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('ana')
        cls.other = create_user('luis')
        cls.listing = create_listing(cls.owner)

    def setUp(self):
        self.client.force_login(self.owner)

    def assert_panel_page(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertTemplateUsed(response, 'layouts/app.html')
        self.assertNotIn('larbit', response.content.decode().lower(), url)
        return response

    def test_pages_use_panel_layout(self):
        for url in (
            reverse('properties'),
            reverse('favorite_properties'),
            reverse('choose_category'),
            reverse('choose_category') + '?kind=2',
            reverse('add_property', args=[self.listing.category_id]),
            reverse('update_property', args=[self.listing.pk]),
            reverse('property_photos', args=[self.listing.pk]) + '?nuevo=1',
        ):
            with self.subTest(url=url):
                self.assert_panel_page(url)

    def test_panel_pages_require_login(self):
        self.client.logout()
        for url in (reverse('properties'), reverse('favorite_properties'), reverse('choose_category'),
                    reverse('property_photos', args=[self.listing.pk])):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse('login') + '?next=' + url, fetch_redirect_response=False)

    def test_menu_marks_only_the_current_section(self):
        content = self.assert_panel_page(reverse('properties')).content.decode()
        self.assertIn(f'href="{reverse("properties")}" aria-current="page"', content)
        self.assertNotIn(f'href="{reverse("favorite_properties")}" aria-current="page"', content)
        # Las subpáginas (editar, fotos) marcan su sección
        content = self.assert_panel_page(reverse('update_property', args=[self.listing.pk])).content.decode()
        self.assertIn(f'href="{reverse("properties")}" aria-current="page"', content)

    def test_my_listings_only_shows_mine_with_likes(self):
        create_listing(self.other, name='Lotes', title='Lote ajeno')
        Log.objects.create(type=Log.LIKE, property=self.listing, user=self.other)
        response = self.assert_panel_page(reverse('properties'))
        self.assertEqual([p.pk for p in response.context['object_list']], [self.listing.pk])
        self.assertEqual(response.context['object_list'][0].likes, 1)
        self.assertNotContains(response, 'Lote ajeno')

    def test_my_listings_are_paginated(self):
        category = self.listing.category
        for i in range(12):
            create_listing(self.owner, category=category, title=f'Casa {i}')
        first = self.assert_panel_page(reverse('properties'))
        self.assertEqual(len(first.context['object_list']), 12)
        self.assertContains(first, 'aria-label="Paginación"')
        second = self.assert_panel_page(reverse('properties') + '?page=2')
        self.assertEqual(len(second.context['object_list']), 1)

    def test_other_users_listing_is_not_found(self):
        self.client.force_login(self.other)
        for url in (reverse('update_property', args=[self.listing.pk]), reverse('property_photos', args=[self.listing.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete_property', args=[self.listing.pk])).status_code, 404)
        self.assertTrue(Property.objects.filter(pk=self.listing.pk).exists())

    def test_delete_listing(self):
        response = self.client.post(reverse('delete_property', args=[self.listing.pk]), follow=True)
        self.assertRedirects(response, reverse('properties'))
        self.assertFalse(Property.objects.filter(pk=self.listing.pk).exists())
        self.assertContains(response, 'Eliminamos el anuncio')

    def test_favorites_list_and_htmx_removal(self):
        theirs = create_listing(self.other, name='Lotes', title='Lote con vista')
        like = Log.objects.create(type=Log.LIKE, property=theirs, user=self.owner)
        response = self.assert_panel_page(reverse('favorite_properties'))
        self.assertContains(response, 'Lote con vista')
        self.assertContains(response, reverse('delete_log', args=[like.pk]))

        response = self.client.post(reverse('delete_log', args=[like.pk]), HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Log.objects.filter(pk=like.pk).exists())

    def test_choose_category_groups_by_kind(self):
        create_category(kind=Category.SERVICE, name='Plomeros', require_location=False)
        response = self.assert_panel_page(reverse('choose_category') + '?kind=2')
        self.assertEqual(response.context['initial_kind'], Category.SERVICE)
        self.assertEqual([k['id'] for k in response.context['kinds']], [Category.REAL_STATE, Category.SERVICE])
        self.assertContains(response, 'Sin ubicación fija')


@override_settings(MEDIA_ROOT=MEDIA_ROOT, TINIFY_API_KEY='')
class PublishWizardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('ana')
        cls.other = create_user('luis')
        cls.category = create_category(name='Casas')
        cls.other_category = create_category(name='Terrenos', purposes=list(cls.category.purposes.all()))
        cls.price = Specification.objects.get(internal_name='precio')
        cls.purpose = cls.category.purposes.first()

    def setUp(self):
        self.client.force_login(self.owner)

    def data(self, **overrides):
        data = {
            'purpose': self.purpose.pk,
            'title': 'Casa en Cumbayá',
            'description': 'Con jardín.',
            str(self.price.pk): '95000',
            'address': 'Cumbayá, Quito, Ecuador',
            'latitude': '-0.2041',
            'longitude': '-78.4320',
            'radius': '0',
            'base64image': '',
        }
        data.update(overrides)
        return data

    def test_create_redirects_to_photos_step(self):
        url = reverse('add_property', args=[self.category.pk])
        response = self.client.post(url, self.data())
        listing = Property.objects.get(title='Casa en Cumbayá')
        self.assertRedirects(response, reverse('property_photos', args=[listing.pk]) + '?nuevo=1', fetch_redirect_response=False)
        self.assertEqual(listing.user, self.owner)
        self.assertEqual(listing.category, self.category)
        self.assertEqual(listing.details, {'purpose': self.purpose.pk, 'specifications': {str(self.price.pk): '95000'}})
        self.assertAlmostEqual(listing.geopoint.y, -0.2041)
        self.assertEqual(listing.address, 'Cumbayá, Quito, Ecuador')

    def test_category_comes_from_the_url_not_the_post(self):
        self.client.post(reverse('add_property', args=[self.category.pk]), self.data(category=self.other_category.pk))
        self.assertEqual(Property.objects.get(title='Casa en Cumbayá').category, self.category)

    def test_long_google_address_fits(self):
        address = 'Calle de los Naranjos E10-45 y Avenida Interoceánica, Cumbayá, Quito 170157, Pichincha, Ecuador'
        self.client.post(reverse('add_property', args=[self.category.pk]), self.data(address=address))
        self.assertEqual(Property.objects.get(title='Casa en Cumbayá').address, address)

    def test_disabled_category_is_not_found(self):
        Category.objects.filter(pk=self.category.pk).update(enabled=False)
        url = reverse('add_property', args=[self.category.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.data()).status_code, 404)
        self.assertFalse(Property.objects.exists())

    def test_errors_open_the_first_step_with_errors(self):
        url = reverse('add_property', args=[self.category.pk])
        response = self.client.post(url, self.data(latitude='', longitude=''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['initial_step'], 2)
        self.assertContains(response, 'Falta marcar el punto en el mapa')

        response = self.client.post(url, self.data(title='', latitude=''))
        self.assertEqual(response.context['initial_step'], 1)

        response = self.client.post(url, self.data(base64image='data:image/png;base64,nada'))
        self.assertEqual(response.context['initial_step'], 3)
        self.assertFalse(Property.objects.exists())

    def test_service_saves_operation_radius(self):
        service = create_category(kind=Category.SERVICE, name='Plomeros', require_location=False,
                                  purposes=list(self.category.purposes.all()))
        response = self.client.get(reverse('add_property', args=[service.pk]))
        self.assertContains(response, 'name="radius"')
        self.assertContains(response, 'type="range"')
        self.client.post(reverse('add_property', args=[service.pk]), self.data(radius='5000', title='Plomería'))
        self.assertEqual(Property.objects.get(title='Plomería').radius, 5000)

    def test_cover_is_saved_with_thumbnail(self):
        buffer = BytesIO()
        PILImage.new('RGB', (160, 90), (11, 110, 95)).save(buffer, format='JPEG')
        data_url = 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()
        self.client.post(reverse('add_property', args=[self.category.pk]), self.data(base64image=data_url))
        listing = Property.objects.get(title='Casa en Cumbayá')
        self.assertIsNotNone(listing.get_cover_instance())
        self.assertTrue(Image.objects.filter(object_id=listing.pk, code='thumbnail').exists())

    def test_update_keeps_address_and_values(self):
        listing = create_listing(self.owner, category=self.category)
        url = reverse('update_property', args=[listing.pk])
        response = self.client.get(url)
        self.assertContains(response, 'value="Av. Amazonas, Quito"')
        self.assertContains(response, 'value="120000"')
        self.assertEqual(response.context['initial_step'], 1)

        response = self.client.post(url, self.data(title='Casa renovada'))
        self.assertRedirects(response, listing.get_absolute_url(), fetch_redirect_response=False)
        listing.refresh_from_db()
        self.assertEqual(listing.title, 'Casa renovada')
        self.assertEqual(listing.category, self.category)

    def cover_data_url(self, color):
        buffer = BytesIO()
        PILImage.new('RGB', (160, 90), color).save(buffer, format='JPEG')
        return 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()

    def test_replacing_the_cover_keeps_a_single_one(self):
        self.client.post(reverse('add_property', args=[self.category.pk]), self.data(base64image=self.cover_data_url((200, 0, 0))))
        listing = Property.objects.get(title='Casa en Cumbayá')
        old_cover = listing.get_cover_instance()
        old_path = old_cover.img.path
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('update_property', args=[listing.pk]), self.data(base64image=self.cover_data_url((0, 0, 200))))
        covers = Image.objects.filter(object_id=listing.pk, is_cover=True)
        self.assertEqual(covers.count(), 1)
        self.assertNotEqual(covers.get().img.path, old_path)
        self.assertFalse(os.path.exists(old_path))
        self.assertEqual(Image.objects.filter(object_id=listing.pk, code='thumbnail').count(), 1)

    def test_attachments_are_kept_or_replaced_when_editing(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.realty.models import Group

        group = Group.objects.create(name='Documentos', internal_name='documentos')
        GroupCategory.objects.create(group=group, category=self.category, sequence=2)
        plans = Specification.objects.create(name='Planos', internal_name='planos', field_type='FileField')
        group.specifications.add(plans)
        key = str(plans.pk)

        def upload(name):
            return SimpleUploadedFile(name, b'%PDF-1.4', content_type='application/pdf')

        self.client.post(reverse('add_property', args=[self.category.pk]), self.data(**{key: upload('a.pdf')}))
        listing = Property.objects.get(title='Casa en Cumbayá')
        first = listing.details['specifications'][key]
        self.assertTrue(os.path.exists(first))

        # Editar sin volver a subir el archivo lo conserva
        self.client.post(reverse('update_property', args=[listing.pk]), self.data(title='Casa editada'))
        listing.refresh_from_db()
        self.assertEqual(listing.details['specifications'][key], first)

        # Reemplazarlo borra el anterior
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('update_property', args=[listing.pk]), self.data(**{key: upload('b.pdf')}))
        listing.refresh_from_db()
        second = listing.details['specifications'][key]
        self.assertNotEqual(second, first)
        self.assertFalse(os.path.exists(first))
        self.assertTrue(os.path.exists(second))

    def test_photos_step_lists_the_gallery(self):
        listing = create_listing(self.owner, category=self.category)
        response = self.client.get(reverse('property_photos', args=[listing.pk]) + '?nuevo=1')
        self.assertTrue(response.context['is_new'])
        self.assertEqual(response.context['photos'], [])
        self.assertContains(response, 'galleryManager(')
        # galleryManager se registra en property.js: sin él no se pueden subir fotos.
        self.assertContains(response, 'js/habitta/property.js')


def png_bytes(size=(160, 90), color=(11, 110, 95)):
    buffer = BytesIO()
    PILImage.new('RGB', size, color).save(buffer, format='PNG')
    return buffer.getvalue()


TILE_URL = 'https://tiles.test/{z}/{x}/{y}.png'


def gray_tile(*args):
    return PILImage.new('RGB', (256, 256), (230, 230, 230))


@override_settings(MEDIA_ROOT=MEDIA_ROOT, TINIFY_API_KEY='', MAP_TILE_URL='', SITE_URL='https://habitta.test')
class PropertyPdfTests(TestCase):
    """Afiche en PDF (apps/realty/report.py)."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('ana', last_name='Torres')
        cls.listing = create_listing(cls.owner)

    def get_pdf(self, listing=None):
        listing = listing or self.listing
        response = self.client.get(reverse('print_property', args=[listing.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        return response

    def test_pdf_without_cover_or_map(self):
        response = self.get_pdf()
        self.assertIn('filename="habitta-anuncio-%s.pdf"' % self.listing.pk, response['Content-Disposition'])

    def test_pdf_with_cover_avatar_socials_and_saved_map(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.authentication.models import SocialNetwork, SocialNetworkProfile

        cover = self.listing.add_image(PILImage.new('RGB', (1600, 900), (200, 80, 46)))
        cover.is_cover = True
        cover.save()
        self.listing.add_image(PILImage.new('RGB', (800, 680), (230, 230, 230)), 'map')
        profile = self.owner.profile
        profile.phone = '0991234567'
        profile.image = SimpleUploadedFile('ana.png', png_bytes((200, 200)), content_type='image/png')
        profile.save()
        network = SocialNetwork.objects.create(name='Instagram', icon='instagram', url='https://instagram.com/')
        SocialNetworkProfile.objects.create(social_network=network, profile=profile, username='ana.casas')

        with patch('apps.realty.report._fetch_tile') as fetch:
            self.get_pdf()
        fetch.assert_not_called()  # el mapa guardado ya tiene buena resolución

    @override_settings(MAP_TILE_URL=TILE_URL)
    def test_low_resolution_map_is_replaced(self):
        old = self.listing.add_image(PILImage.new('RGB', (274, 203)), 'map')
        with patch('apps.realty.report._fetch_tile', side_effect=gray_tile) as fetch:
            self.get_pdf()
        self.assertTrue(fetch.called)
        old.refresh_from_db()
        self.assertEqual(old.img.width, 800)

        # Ya guardado con buena resolución: no se vuelven a pedir tiles
        with patch('apps.realty.report._fetch_tile') as fetch:
            self.get_pdf()
        fetch.assert_not_called()

    @override_settings(MAP_TILE_URL=TILE_URL)
    def test_static_map_is_built_from_tiles_with_the_brand_pin(self):
        from apps.realty.report import _render_static_map

        with patch('apps.realty.report._fetch_tile', side_effect=gray_tile) as fetch:
            image = _render_static_map(self.listing)
        self.assertEqual(image.size, (800, 680))
        self.assertGreaterEqual(fetch.call_count, 4)  # 400×340 px lógicos cruzan al menos 2×2 tiles
        zooms = {call.args[3] for call in fetch.call_args_list}
        self.assertEqual(zooms, {16})
        # Cuerpo del pin (verde de la marca) sobre el punto; fondo gris alrededor
        r, g, b = image.getpixel((400, 302))
        self.assertTrue(abs(r - 11) < 20 and abs(g - 110) < 20 and abs(b - 95) < 20, (r, g, b))
        self.assertEqual(image.getpixel((40, 40)), (230, 230, 230))

    @override_settings(MAP_TILE_URL=TILE_URL)
    def test_map_is_skipped_when_tiles_fail(self):
        import requests

        with patch('apps.realty.report._fetch_tile', side_effect=requests.ConnectionError):
            self.get_pdf()
        self.assertIsNone(self.listing.get_last_image_by_code('map'))

    @override_settings(MAP_TILE_URL=TILE_URL)
    def test_service_without_location_does_not_ask_for_a_map(self):
        service = create_listing(self.owner, kind=Category.SERVICE, name='Plomeros', title='Plomería')
        Category.objects.filter(pk=service.category_id).update(require_location=False)
        with patch('apps.realty.report._fetch_tile') as fetch:
            self.get_pdf(Property.objects.get(pk=service.pk))
        fetch.assert_not_called()

    def test_features_skip_price_files_and_negative_values(self):
        from apps.realty.models import Group
        from apps.realty.report import _features, _title

        group = Group.objects.create(name='Interior', internal_name='interior')
        GroupCategory.objects.create(group=group, category=self.listing.category, sequence=2)
        rooms = Specification.objects.create(name='Habitaciones', internal_name='habitaciones', field_type='IntegerField')
        pool = Specification.objects.create(name='Piscina', internal_name='piscina', field_type='ChoiceField')
        garden = Specification.objects.create(name='Jardín', internal_name='jardin', field_type='ChoiceField')
        plans = Specification.objects.create(name='Planos', internal_name='planos', field_type='FileField')
        group.specifications.add(rooms, pool, garden, plans)
        self.listing.details['specifications'].update({
            str(rooms.pk): '3', str(pool.pk): 'no', str(garden.pk): 'si', str(plans.pk): '/tmp/planos.pdf',
        })
        self.listing.title = 'CASA CON JARDÍN'

        self.assertEqual(_features(self.listing), [('Habitaciones', '3'), ('Jardín', 'Sí')])
        self.assertEqual(_title(self.listing), 'Casa con jardín')

    def test_finder_by_purpose_was_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse('finder_by_purpose', args=[1, 'x'])
