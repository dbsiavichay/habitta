"""Pruebas de humo del frontend de Habitta (fases 0 y 1).

Recorren las páginas públicas como visitante y como usuario, y verifican que rendericen sin errores
y sin rastros de la marca anterior.

    docker compose exec web python manage.py test apps.project.tests
"""
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.logs.models import Log
from apps.project.models import Help, Term
from apps.project.templatetags.habitta import money, spec_text, whatsapp_url
from apps.realty.models import Category, Property, Purpose, Specification

IN_MEMORY_LAYER = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


def create_listing(owner, kind=Category.REAL_STATE, name='Casas', price='120000'):
    purpose = Purpose.objects.create(for_owner='Vender', for_user='Comprar', activity='En Venta', participle='Vendido')
    spec, _ = Specification.objects.get_or_create(
        internal_name='precio', defaults={'name': 'Precio', 'field_type': 'DecimalField'}
    )
    category = Category.objects.create(
        kind=kind, name=name, singular_name=name[:-1], price_area='precio', order=1, for_card='precio'
    )
    category.purposes.add(purpose)
    return Property.objects.create(
        title='Casa con jardín',
        description='Amplia y luminosa.',
        address='Av. Amazonas, Quito',
        geopoint=Point(-78.4867, -0.1807),
        status=Property.PUBLISHED,
        details={'purpose': purpose.id, 'specifications': {str(spec.id): price}},
        category=category,
        user=owner,
    )


class PublicPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('anunciante', 'owner@example.com', 'x', first_name='Ana', last_name='Pérez')
        cls.owner.profile.phone = '0991234567'
        cls.owner.profile.save()
        cls.visitor = User.objects.create_user('visitante', 'visit@example.com', 'x', first_name='Luis')
        cls.listing = create_listing(cls.owner)
        Term.objects.create(title='Uso del sitio', description='Reglas.', order=1)
        Help.objects.create(title='¿Cómo publico?', description='Así.', sequence=1, user=cls.owner)

    def public_urls(self):
        return [
            reverse('home'),
            reverse('finder'),
            reverse('finder_without_map') + '?kind=1&search_purpose=1',
            reverse('detail_property', args=[self.listing.pk]),
            reverse('detail_profile', args=[self.owner.username]),
            reverse('help'),
            reverse('terms'),
            '/api/properties/',
            '/api/properties/?kind=1&lat=-0.18&lng=-78.48&radio=15&min_price=1&max_price=500000',
        ]

    def assert_page_ok(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertNotIn('larbit', response.content.decode().lower(), f'Marca anterior en {url}')
        return response

    def test_pages_render_for_visitors(self):
        for url in self.public_urls():
            with self.subTest(url=url):
                self.assert_page_ok(url)

    def test_pages_render_for_logged_users(self):
        for user in (self.owner, self.visitor):
            self.client.force_login(user)
            for url in self.public_urls():
                with self.subTest(user=user.username, url=url):
                    self.assert_page_ok(url)

    def test_home_shows_brand_and_real_stats(self):
        html = self.assert_page_ok(reverse('home')).content.decode()
        self.assertIn('Habitta', html)
        self.assertIn('1 anuncios publicados', html)
        self.assertIn('id="search-data"', html)

    def test_detail_shows_price_contact_and_whatsapp(self):
        self.client.force_login(self.visitor)
        html = self.assert_page_ok(reverse('detail_property', args=[self.listing.pk])).content.decode()
        self.assertIn('$120.000', html)
        self.assertIn('https://wa.me/593991234567', html)
        self.assertIn('chatWidget(%d)' % self.owner.id, html)

    def test_owner_sees_photo_manager_instead_of_chat(self):
        self.client.force_login(self.owner)
        html = self.assert_page_ok(reverse('detail_property', args=[self.listing.pk])).content.decode()
        self.assertIn('galleryManager(', html)
        self.assertNotIn('chatWidget(', html)

    def test_api_filters_by_kind_and_ignores_bad_numbers(self):
        self.assertEqual(len(self.client.get('/api/properties/?kind=1').json()), 1)
        self.assertEqual(len(self.client.get('/api/properties/?kind=2').json()), 0)
        self.assertEqual(self.client.get('/api/properties/?lat=abc&radio=x').status_code, 200)
        item = self.client.get('/api/properties/').json()[0]
        self.assertEqual(item['title'], 'Casa con jardín')
        self.assertIn('data-property-id', item['list_card'])

    def test_finder_reads_filters_from_url_and_legacy_post(self):
        response = self.client.get(reverse('finder') + '?kind=2&search_category=7&lat=-0.2&lng=-78.5&radius=5')
        initial = response.context['initial_filters']
        self.assertEqual((initial['kind'], initial['category'], initial['radius']), ('2', '7', '5'))
        response = self.client.post(reverse('finder'), {'search_purpose': '3', 'search_address': 'Quito'})
        self.assertEqual(response.context['initial_filters']['purpose'], '3')

    def test_like_with_htmx_returns_partial(self):
        self.client.force_login(self.visitor)
        response = self.client.post(
            reverse('add_log'), {'type': Log.LIKE, 'property': self.listing.pk}, HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Guardado', response.content.decode())
        log = Log.objects.get(user=self.visitor, property=self.listing)
        response = self.client.post(reverse('delete_log', args=[log.pk]), HTTP_HX_REQUEST='true')
        self.assertIn('Guardar', response.content.decode())
        self.assertFalse(Log.objects.filter(pk=log.pk).exists())

    @override_settings(DEBUG=False)
    def test_friendly_404(self):
        response = self.client.get('/no-existe/')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Esta puerta no lleva a ningún lado', response.content.decode())


class TemplateFilterTests(TestCase):
    def test_money(self):
        self.assertEqual(money(120000.0), '$120.000')
        self.assertEqual(money('45.5'), '$45,50')
        self.assertEqual(money('precio'), '')

    def test_whatsapp_url(self):
        self.assertEqual(whatsapp_url('0991234567'), 'https://wa.me/593991234567')
        self.assertEqual(whatsapp_url('+593 99 123 4567'), 'https://wa.me/593991234567')
        self.assertEqual(whatsapp_url('2249241'), '')

    def test_spec_text(self):
        self.assertEqual(spec_text({'key': 'Garaje', 'value': 'si'}), 'Garaje')
        self.assertEqual(spec_text({'key': 'Habitaciones', 'value': '3'}), '3 habitaciones')
        self.assertEqual(spec_text({'key': 'Whatsapp', 'value': '0991234567'}), 'Whatsapp 0991234567')
        self.assertEqual(spec_text({'key': 'Piscina', 'value': 'No Disponible'}), '')


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ChatConsumerTests(TransactionTestCase):
    """El chat entrega a cada participante la burbuja renderizada para él (propia a la derecha)."""

    def test_each_side_gets_its_own_bubble(self):
        from config.asgi import application

        alice = User.objects.create_user('alice', password='x', first_name='Alice')
        bob = User.objects.create_user('bob', password='x', first_name='Bob')

        async def scenario():
            from channels.db import database_sync_to_async

            # AuthMiddlewareStack resuelve el usuario desde la sesión: se usa una sesión real.
            a_client = await database_sync_to_async(self._session_cookie)(alice)
            b_client = await database_sync_to_async(self._session_cookie)(bob)
            a = WebsocketCommunicator(application, f'/ws/message/{bob.id}/', headers=[(b'origin', b'http://localhost'), (b'cookie', a_client)])
            b = WebsocketCommunicator(application, f'/ws/message/{alice.id}/', headers=[(b'origin', b'http://localhost'), (b'cookie', b_client)])
            self.assertTrue((await a.connect())[0])
            self.assertTrue((await b.connect())[0])
            await a.send_json_to({'message': 'Hola Bob'})
            mine = await a.receive_json_from(timeout=5)
            theirs = await b.receive_json_from(timeout=5)
            await a.disconnect()
            await b.disconnect()
            return mine, theirs

        mine, theirs = async_to_sync(scenario)()
        self.assertTrue(mine['own'])
        self.assertIn('chat-end', mine['bubble'])
        self.assertFalse(theirs['own'])
        self.assertIn('chat-start', theirs['bubble'])
        self.assertIn('Hola Bob', theirs['bubble'])

    def _session_cookie(self, user):
        from django.test import Client

        client = Client()
        client.force_login(user)
        return f"sessionid={client.cookies['sessionid'].value}".encode()
