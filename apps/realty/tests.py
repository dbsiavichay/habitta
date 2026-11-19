"""Pruebas del panel de publicaciones (fase 3): listas, asistente de publicación, fotos y favoritos.

    docker compose exec web python manage.py test apps.realty.tests
"""
import base64
import shutil
import tempfile
from io import BytesIO

from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image as PILImage

from apps.logs.models import Log
from apps.multimedia.models import Image
from apps.project.testing import create_category, create_listing, create_user
from apps.realty.models import Category, Property, Specification

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

    def test_photos_step_lists_the_gallery(self):
        listing = create_listing(self.owner, category=self.category)
        response = self.client.get(reverse('property_photos', args=[listing.pk]) + '?nuevo=1')
        self.assertTrue(response.context['is_new'])
        self.assertEqual(response.context['photos'], [])
        self.assertContains(response, 'galleryManager(')
