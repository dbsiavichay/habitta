"""Pruebas de humo del frontend de Habitta (fases 0 y 1).

Recorren las páginas públicas como visitante y como usuario, y verifican que rendericen sin errores
y sin rastros de la marca anterior.

    docker compose exec web python manage.py test apps.project.tests
"""
import shutil
import tempfile
from io import StringIO

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.logs.models import Log
from apps.project.models import Help, Icons, Settings, Term
from apps.project.templatetags.habitta import money, spec_text, whatsapp_url
from apps.project.testing import IN_MEMORY_LAYER, create_listing, create_user


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


ICONS_MEDIA = tempfile.mkdtemp(prefix='habitta-icons-')
ICONS_CSS = (
    "@font-face {\n  font-family: 'larbit';\n  src: url('fonts/larbit.eot?h1x3xy');\n"
    "  src: url('fonts/larbit.woff?h1x3xy') format('woff'), url('fonts/larbit.svg?h1x3xy#larbit') format('svg');\n}\n"
    "[class^=\"lb-\"] { font-family: 'larbit' !important; }\n"
    ".lb-bed:before { content: \"\\e900\"; }\n.lb-bath-tub:before { content: \"\\e901\"; }\n"
)


def tearDownModule():
    shutil.rmtree(ICONS_MEDIA, ignore_errors=True)


@override_settings(MEDIA_ROOT=ICONS_MEDIA, SITE_NAME='Habitta', LEGAL_NAME='Habitta S.A.', SITE_URL='https://habitta.ec')
class RebrandContentTests(TestCase):
    """manage.py rebrand_content"""

    @classmethod
    def setUpTestData(cls):
        cls.settings_row = Settings.objects.create(
            title='Bienvenidos  a LARBIT', subtitle='Tu tienda de servicios online',
            cover='covers/a.jpg', subcover='covers/a.jpg', term_cover='covers/a.jpg',
            help_cover='covers/a.jpg', service_cover='covers/a.jpg', is_active=True,
        )
        cls.term = Term.objects.create(title='1. ACEPTACIÓN', order=1, description=(
            'Términos de Larbit Company S.A., con domicilio en Macas (el “www.larbit.com”).\n'
            'Larbit company S.A y sus empresas. Propiedad de Larbit Company S.A. El Usuario acepta.\n'
            'Escríbenos a larbitecuador@gmail.com o visita Larbit.'
        ))

    def setUp(self):
        shutil.rmtree(ICONS_MEDIA, ignore_errors=True)

    def run_command(self, *args):
        out = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command('rebrand_content', *args, stdout=out)
        return out.getvalue()

    def create_icons(self):
        def stored(name, content):
            return default_storage.save(name, ContentFile(content))

        return Icons.objects.create(
            name='LarbitFonts', is_active=True,
            eot=stored('larbitfonts/fonts/larbit.eot', b'eot'), svg=stored('larbitfonts/fonts/larbit.svg', b'<font id="larbit">'),
            ttf=stored('larbitfonts/fonts/larbit.ttf', b'ttf'), woff=stored('larbitfonts/fonts/larbit.woff', b'woff'),
            css=stored('larbitfonts/style.css', ICONS_CSS.encode()),
        )

    def test_dry_run_saves_nothing(self):
        icons = self.create_icons()
        output = self.run_command('--dry-run')
        self.assertIn('Se cambiarían', output)
        self.term.refresh_from_db()
        self.assertIn('Larbit Company S.A.', self.term.description)
        icons.refresh_from_db()
        self.assertEqual(icons.css.name, 'larbitfonts/style.css')
        self.assertFalse(default_storage.exists('spec_icons/spec-icons.css'))

    def test_replaces_brand_legal_name_and_domain(self):
        self.run_command()
        self.settings_row.refresh_from_db()
        self.term.refresh_from_db()
        self.assertEqual(self.settings_row.title, 'Bienvenidos a Habitta')
        self.assertEqual(self.term.description, (
            'Términos de Habitta S.A., con domicilio en Macas (el “habitta.ec”).\n'
            'Habitta S.A. y sus empresas. Propiedad de Habitta S.A. El Usuario acepta.\n'
            # Los correos no se tocan: se reportan para revisarlos a mano
            'Escríbenos a larbitecuador@gmail.com o visita Habitta.'
        ))

    @override_settings(LEGAL_NAME='Habitta')
    def test_keeps_the_period_only_at_the_end_of_a_sentence(self):
        output = self.run_command()
        self.term.refresh_from_db()
        self.assertIn('Términos de Habitta, con domicilio', self.term.description)
        self.assertIn('Habitta y sus empresas. Propiedad de Habitta. El Usuario', self.term.description)
        self.assertIn('Aún mencionan «larbit»', output)

    def test_is_idempotent(self):
        self.run_command()
        self.assertIn('Se cambiaron 0 fragmentos', self.run_command())

    def test_moves_the_icon_font(self):
        from apps.project.context_processors import brand
        from apps.realty.utils import get_spec_icons

        icons = self.create_icons()
        self.run_command()
        icons.refresh_from_db()
        self.assertEqual(icons.name, 'Íconos de especificaciones')
        self.assertEqual(icons.eot.name, 'spec_icons/fonts/spec-icons.eot')
        self.assertEqual(icons.css.name, 'spec_icons/spec-icons.css')
        css = icons.css.read().decode()
        self.assertNotIn('larbit', css)
        self.assertIn("url('fonts/spec-icons.svg?h1x3xy#spec-icons')", css)
        self.assertEqual(icons.svg.read(), b'<font id="spec-icons">')
        self.assertFalse(default_storage.exists('larbitfonts/style.css'))
        self.assertEqual(get_spec_icons(), [('bath-tub', 'Bath tub'), ('bed', 'Bed')])
        self.assertTrue(brand(RequestFactory().get('/'))['icons_url'].endswith('/spec_icons/spec-icons.css'))


class AdminTests(TestCase):
    """Admin con Unfold (config/unfold.py): pantallas, dashboard, menú y acceso."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.contenttypes.models import ContentType

        from apps.payments.models import Bank, BankPayment, Payment
        from apps.realty.models import Property

        cls.superuser = create_user('jefa', is_staff=True, is_superuser=True)
        cls.owner = create_user('dueno')
        cls.listing = create_listing(cls.owner)
        bank = Bank.objects.create(name='Banco Andino', account_number='123', account_type=1,
                                   recipient_name='Habitta', recipient_charter='0999999999')
        content_type = ContentType.objects.get_for_model(Property)
        payments = [
            BankPayment.objects.create(user=cls.owner, object_id=cls.listing.pk, content_type=content_type,
                                       amount='12.50', status=status, bank=bank, voucher='payments/bankvouchers/v.png')
            for status in (Payment.REGISTRY, Payment.CONFIRMED, Payment.REJECTED)
        ]
        cls.pending = payments[0]

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_every_registered_model_lists_and_adds(self):
        from django.contrib import admin

        request = RequestFactory().get('/')
        request.user = self.superuser
        for model, model_admin in admin.site._registry.items():
            opts = model._meta
            with self.subTest(model=opts.label):
                views = ['changelist']
                # Pagos, publicaciones, subastas y lo que sólo se consulta no se crean desde el admin.
                if model_admin.has_add_permission(request):
                    views.append('add')
                for view in views:
                    response = self.client.get(reverse(f'admin:{opts.app_label}_{opts.model_name}_{view}'))
                    self.assertEqual(response.status_code, 200, view)

    def test_change_views(self):
        for obj in (self.listing, self.owner, self.pending, self.listing.category):
            opts = obj._meta
            with self.subTest(model=opts.label):
                response = self.client.get(reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[obj.pk]))
                self.assertEqual(response.status_code, 200)

    def test_dashboard(self):
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Hola, Jefa')
        kpis = {kpi['title']: kpi for kpi in response.context['kpis']}
        self.assertEqual(kpis['Pagos pendientes']['value'], 1)
        self.assertTrue(kpis['Pagos pendientes']['alert'])
        self.assertEqual(kpis['Publicaciones']['footer'], '+1 nueva en 30 días')
        self.assertEqual(len(response.context['pending_payments']['rows']), 1)
        self.assertEqual(len(response.context['latest_properties']['rows']), 1)
        self.assertEqual(response.context['top_categories'][0]['name'], 'Casas')
        # La publicación y los dos usuarios de hoy caen en el último mes del gráfico.
        totals = {serie['label']: serie['total'] for serie in response.context['activity']['legend']}
        self.assertEqual(totals, {'Publicaciones': 1, 'Usuarios nuevos': 2})
        self.assertFalse(response.context['activity']['empty'])

    def test_sidebar_badge_counts_only_pending_transfers(self):
        from apps.payments.models import Payment
        from apps.project.admin_dashboard import pending_bank_payments_badge

        self.assertEqual(pending_bank_payments_badge(None), 1)
        self.pending.status = Payment.CONFIRMED
        self.pending.save()
        self.assertIsNone(pending_bank_payments_badge(None))

    def test_staff_without_permissions_sees_nothing_sensitive(self):
        staff = create_user('ayudante', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpis'], [])
        self.assertIsNone(response.context['pending_payments'])
        self.assertNotContains(response, reverse('admin:payments_bankpayment_changelist'))

    def test_non_staff_is_sent_to_login(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('admin:index'))
        self.assertRedirects(response, f"{reverse('admin:login')}?next={reverse('admin:index')}")

    def test_spanish_strings_for_unfold(self):
        self.client.logout()
        response = self.client.get(reverse('admin:login'))
        self.assertContains(response, 'Te damos la bienvenida a')
        self.assertContains(response, 'Volver al sitio')

    def test_environment_label(self):
        from apps.project.admin_dashboard import environment_callback

        with override_settings(DEBUG=True):
            self.assertEqual(environment_callback(None), ['Desarrollo', 'warning'])
        with override_settings(DEBUG=False):
            self.assertIsNone(environment_callback(None))

    def test_navbar_links_admin_only_for_staff(self):
        admin_url = reverse('admin:index')
        self.assertContains(self.client.get(reverse('home')), f'href="{admin_url}"')
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(reverse('home')), f'href="{admin_url}"')

    # ---------- Fase B: pantallas por módulo ----------

    def test_conversations_only_for_superusers(self):
        from apps.messenger.models import Conversation, Message

        conversation = Conversation.objects.create(owner=self.owner, member=self.superuser)
        Message.objects.create(sender=self.owner, content='Hola, ¿sigue disponible?', conversation=conversation)
        changelist = reverse('admin:messenger_conversation_changelist')
        change = reverse('admin:messenger_conversation_change', args=[conversation.pk])

        response = self.client.get(change)
        self.assertContains(response, 'Hola, ¿sigue disponible?')
        self.assertContains(response, 'Mensajes privados entre usuarios')
        self.assertNotContains(response, 'name="_save"')
        self.assertEqual(self.client.get(changelist).context['cl'].result_list[0].messages_count, 1)

        staff = create_user('ayudante', is_staff=True)
        from django.contrib.auth.models import Permission
        staff.user_permissions.add(*Permission.objects.filter(codename__in=['view_conversation', 'view_message']))
        self.client.force_login(staff)
        self.assertEqual(self.client.get(changelist).status_code, 403)
        self.assertNotContains(self.client.get(reverse('admin:index')), changelist)

    def test_group_form_saves_specifications(self):
        from apps.realty.models import Group, Specification

        spec = Specification.objects.create(name='Piscina', internal_name='piscina', field_type='BooleanField')
        response = self.client.post(reverse('admin:realty_group_add'), {
            'name': 'Extras', 'internal_name': 'extras', 'columns': 'col-xs-6', 'specifications': [spec.pk],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(Group.objects.get(internal_name='extras').specifications.all()), [spec])

    def test_specification_choices_only_for_selectors(self):
        from apps.realty.models import Specification

        spec = Specification.objects.get(internal_name='precio')
        response = self.client.get(reverse('admin:realty_specification_change', args=[spec.pk]))
        self.assertContains(response, "x-show=\"field_type &amp;&amp; field_type.startsWith(&#x27;ChoiceField&#x27;)\"")

    def test_new_terms_go_to_the_end(self):
        Term.objects.create(title='Uso', description='x', order=1)
        Term.objects.create(title='Pagos', description='x', order=5)
        response = self.client.post(reverse('admin:project_term_add'), {'title': 'Cookies', 'description': 'Texto.'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Term.objects.get(title='Cookies').order, 6)
        self.assertEqual(Term.objects.last().title, 'Cookies')

    def test_cancel_open_auction(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.auctions.models import Auction

        auction = Auction.objects.create(property=self.listing, start_date=timezone.now(),
                                         ending_date=timezone.now() + timedelta(days=3), base_amount='100.00')
        url = reverse('admin:auctions_auction_cancel_auction', args=[auction.pk])
        self.assertContains(self.client.get(reverse('admin:auctions_auction_change', args=[auction.pk])), url)
        self.client.post(url, {'_form_submitted': 'on'})
        auction.refresh_from_db()
        self.assertEqual(auction.stage, Auction.CANCELED)
        self.assertNotContains(self.client.get(reverse('admin:auctions_auction_change', args=[auction.pk])), url)

    def test_user_change_shows_profile_inline(self):
        response = self.client.get(reverse('admin:auth_user_change', args=[self.owner.pk]))
        self.assertContains(response, 'name="profile-0-phone"')
        # Al crear no hay inline: el perfil lo hace la señal de post_save.
        response = self.client.post(reverse('admin:auth_user_add'), {
            'username': 'nueva', 'password1': 'Clave-muy-segura-123', 'password2': 'Clave-muy-segura-123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(username='nueva').profile)

    def test_category_list_shows_kind_badge(self):
        response = self.client.get(reverse('admin:realty_category_changelist'))
        self.assertContains(response, 'Inmuebles')


class HealthzTests(TestCase):
    @override_settings(APP_VERSION='abc1234')
    def test_reports_ok_and_commit(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'sha': 'abc1234'})
        self.assertIn('no-cache', response['Cache-Control'])

    def test_answers_plain_http_behind_ssl_redirect(self):
        # En producción SECURE_SSL_REDIRECT está activo, pero el HEALTHCHECK llama por HTTP.
        with override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r'^healthz$']):
            self.assertEqual(self.client.get('/healthz').status_code, 200)
            self.assertEqual(self.client.get(reverse('home')).status_code, 301)

    def test_only_get(self):
        self.assertEqual(self.client.post('/healthz').status_code, 405)
