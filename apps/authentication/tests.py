"""Pruebas de las páginas de cuenta de Habitta (fase 2): login, registro y contraseñas.

    docker compose exec web python manage.py test apps.authentication.tests
"""
import base64
import re
import shutil
import tempfile
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.authentication.models import SocialNetwork, SocialNetworkProfile

PASSWORD = 'Casa-con-jardin-2026'
NEW_PASSWORD = 'Terraza-y-patio-77'
NO_SOCIAL = dict(FACEBOOK_APP_ID='', FACEBOOK_APP_SECRET='', TWITTER_API_KEY='', TWITTER_API_SECRET='')


class AuthPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('ana', 'ana@example.com', PASSWORD, first_name='Ana')

    def assert_auth_page(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertTemplateUsed(response, 'layouts/auth.html')
        self.assertNotIn('larbit', response.content.decode().lower(), f'Marca anterior en {url}')
        return response

    def test_public_pages_use_auth_layout(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        for url in (
            reverse('login'), reverse('register'), reverse('password_reset'), reverse('password_reset_done'),
            reverse('password_reset_complete'), reverse('password_reset_confirm', args=[uid, 'token-malo']),
        ):
            with self.subTest(url=url):
                self.assert_auth_page(url)

    def test_account_pages_use_auth_layout(self):
        self.client.force_login(self.user)
        self.assert_auth_page(reverse('complete_register', args=[self.user.profile.pk]))

    def test_password_pages_live_in_the_panel(self):
        self.client.force_login(self.user)
        for url in (reverse('change_password'), reverse('change_password_done')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'layouts/app.html')
                self.assertContains(response, f'href="{reverse("change_password")}" aria-current="page"')

    def test_register_with_open_session_offers_logout(self):
        self.client.force_login(self.user)
        response = self.assert_auth_page(reverse('register'))
        self.assertTemplateUsed(response, 'authentication/register_yet.html')
        self.assertContains(response, 'action="%s"' % reverse('logout'))
        self.assertContains(response, 'name="next" value="%s"' % reverse('register'))

    def test_only_login_and_register_are_indexable(self):
        self.assertNotContains(self.client.get(reverse('login')), 'noindex')
        self.assertNotContains(self.client.get(reverse('register')), 'noindex')
        self.assertContains(self.client.get(reverse('password_reset')), 'name="robots" content="noindex"')

    def test_password_fields_can_be_revealed(self):
        self.assertContains(self.client.get(reverse('login')), 'x-data="passwordToggle"')


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('ana', 'ana@example.com', PASSWORD, first_name='Ana')

    def test_login_with_email_greets_user(self):
        response = self.client.post(reverse('login'), {'username': 'ANA@example.com', 'password': PASSWORD}, follow=True)
        self.assertEqual(response.context['user'], self.user)
        self.assertContains(response, '¡Hola, Ana! Qué bueno verte.')

    def test_wrong_password_shows_alert(self):
        response = self.client.post(reverse('login'), {'username': 'ana', 'password': 'otra-cosa'})
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'El usuario o la contraseña no son correctos.')

    def test_login_links_to_register_keeping_next(self):
        response = self.client.get(reverse('login') + '?next=/explorador/')
        self.assertContains(response, 'href="%s?next=/explorador/"' % reverse('register'))

    @override_settings(FACEBOOK_APP_ID='123', FACEBOOK_APP_SECRET='s', TWITTER_API_KEY='k', TWITTER_API_SECRET='t')
    def test_social_buttons_when_configured(self):
        response = self.client.get(reverse('login') + '?next=/explorador/')
        self.assertContains(response, "facebookLogin('123')")
        self.assertContains(response, 'name="provider" value="twitter"')
        self.assertContains(response, 'js/habitta/auth.js')
        # Facebook, X y el formulario de correo conservan el destino
        self.assertContains(response, 'name="next" value="/explorador/"', count=3)

    @override_settings(**NO_SOCIAL)
    def test_no_social_buttons_without_credentials(self):
        response = self.client.get(reverse('login'))
        self.assertNotContains(response, reverse('social_login'))
        self.assertNotContains(response, 'js/habitta/auth.js')


class RegisterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('ana', 'ana@example.com', PASSWORD, first_name='Ana')

    def test_requires_email_and_strong_password(self):
        response = self.client.post(reverse('register'), {'username': 'luis', 'email': '', 'password': '12345678'})
        errors = response.context['form'].errors
        self.assertIn('email', errors)
        self.assertIn('password', errors)
        self.assertContains(response, 'aria-invalid="true"')
        self.assertFalse(User.objects.filter(username='luis').exists())

    def test_rejects_registered_email_ignoring_case(self):
        response = self.client.post(reverse('register'), {'username': 'luis', 'email': 'ANA@example.com', 'password': PASSWORD})
        self.assertIn('email', response.context['form'].errors)

    def test_register_and_complete_keep_next(self):
        response = self.client.post(reverse('register'), {
            'username': 'luis', 'email': 'luis@example.com', 'password': PASSWORD, 'next': '/explorador/',
        })
        luis = User.objects.get(username='luis')
        complete_url = reverse('complete_register', args=[luis.profile.pk])
        self.assertRedirects(response, complete_url + '?next=%2Fexplorador%2F', fetch_redirect_response=False)

        page = self.client.get(complete_url + '?next=%2Fexplorador%2F')
        self.assertContains(page, 'name="next" value="/explorador/"')

        response = self.client.post(complete_url, {'first_name': 'Luis', 'last_name': 'Mora', 'phone': '', 'next': '/explorador/'})
        self.assertRedirects(response, '/explorador/', fetch_redirect_response=False)
        luis.refresh_from_db()
        self.assertEqual(luis.get_full_name(), 'Luis Mora')

    def test_complete_ignores_external_next(self):
        self.client.force_login(self.user)
        url = reverse('complete_register', args=[self.user.profile.pk])
        response = self.client.post(url, {'first_name': 'Ana', 'last_name': 'Pérez', 'next': 'https://malo.example.com/'}, follow=True)
        self.assertRedirects(response, reverse('home'))
        self.assertContains(response, '¡Listo, Ana! Tu cuenta ya está completa.')

    def test_complete_prefills_name(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('complete_register', args=[self.user.profile.pk]))
        self.assertEqual(response.context['form']['first_name'].value(), 'Ana')
        self.assertContains(response, 'type="tel"')


class PasswordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('ana', 'ana@example.com', PASSWORD, first_name='Ana')

    @override_settings(SITE_URL='https://habitta.example')
    def test_reset_sends_branded_email_and_link_works(self):
        response = self.client.post(reverse('password_reset'), {'email': 'ana@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Recupera tu contraseña de %s' % settings.SITE_NAME)
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        link = re.search(r'https://habitta\.example/authentication/reset-password/confirm/\S+/\S+/', message.body).group(0)
        self.assertIn(link, html)
        self.assertIn('https://habitta.example/static/brand/habitta-logo.png', html)
        self.assertIn('Hola, Ana', html)
        self.assertNotIn('larbit', (message.body + html).lower())

        response = self.client.get(urlparse(link).path, follow=True)
        self.assertTrue(response.context['validlink'])
        self.assertContains(response, 'Crea una contraseña nueva')

        set_password_url = response.redirect_chain[-1][0]
        response = self.client.post(set_password_url, {'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD})
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.assertTrue(self.client.login(username='ana', password=NEW_PASSWORD))

    def test_unknown_email_sends_nothing_but_looks_the_same(self):
        response = self.client.post(reverse('password_reset'), {'email': 'nadie@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_link_offers_a_new_one(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('password_reset_confirm', args=[uid, 'token-malo']))
        self.assertFalse(response.context['validlink'])
        self.assertContains(response, 'Este enlace ya no sirve')
        self.assertContains(response, 'href="%s"' % reverse('password_reset'))

    def test_change_password_requires_login(self):
        response = self.client.get(reverse('change_password'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('change_password'), fetch_redirect_response=False)

    def test_change_password_flow(self):
        self.client.force_login(self.user)
        data = {'old_password': 'no-es-esta', 'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD}
        self.assertContains(self.client.post(reverse('change_password'), data), 'Tu contraseña actual no es correcta.')

        data['old_password'] = PASSWORD
        response = self.client.post(reverse('change_password'), data, follow=True)
        self.assertRedirects(response, reverse('change_password_done'))
        self.assertContains(response, 'Tu contraseña se cambió')
        self.assertEqual(response.context['user'], self.user)  # la sesión sigue abierta


class ProfilePanelTests(TestCase):
    """Mi perfil (fase 3): datos, celular, redes sociales y foto."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('ana', 'ana@example.com', PASSWORD, first_name='Ana', last_name='Pérez')
        cls.facebook = SocialNetwork.objects.create(name='Facebook', icon='facebook', url='https://www.facebook.com/')
        cls.youtube = SocialNetwork.objects.create(name='Youtube', icon='youtube', url='https://www.youtube.com/')

    def setUp(self):
        self.client.force_login(self.user)
        self.media = tempfile.mkdtemp(prefix='habitta-tests-')
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def data(self, **overrides):
        data = {
            'first_name': 'Ana', 'last_name': 'Pérez', 'email': 'ana@example.com', 'username': 'ana', 'phone': '0991234567',
            'socialnetworkprofile_set-TOTAL_FORMS': '2', 'socialnetworkprofile_set-INITIAL_FORMS': '0',
            'socialnetworkprofile_set-MIN_NUM_FORMS': '0', 'socialnetworkprofile_set-MAX_NUM_FORMS': '1000',
            'socialnetworkprofile_set-0-social_network': self.facebook.pk, 'socialnetworkprofile_set-0-username': '',
            'socialnetworkprofile_set-1-social_network': self.youtube.pk, 'socialnetworkprofile_set-1-username': '',
        }
        data.update(overrides)
        return data

    def test_profile_page(self):
        response = self.client.get(reverse('update_profile'))
        self.assertTemplateUsed(response, 'layouts/app.html')
        self.assertContains(response, 'Redes sociales')
        self.assertContains(response, 'facebook.com/')
        self.assertContains(response, reverse('upload_avatar_profile'))

    def test_save_profile_and_social_network(self):
        response = self.client.post(reverse('update_profile'), self.data(**{
            'first_name': 'Ana María',
            'socialnetworkprofile_set-0-username': 'https://www.facebook.com/ana.perez/',
        }), follow=True)
        self.assertRedirects(response, reverse('update_profile'))
        self.assertContains(response, 'Guardamos los cambios de tu perfil')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana María')
        self.assertEqual(self.user.profile.phone, '0991234567')
        # Se guarda sólo el usuario aunque se pegue el enlace completo
        self.assertEqual(SocialNetworkProfile.objects.get(profile=self.user.profile).username, 'ana.perez')

    def test_clearing_a_social_network_removes_it(self):
        SocialNetworkProfile.objects.create(profile=self.user.profile, social_network=self.facebook, username='ana')
        existing = SocialNetworkProfile.objects.get()
        data = self.data(**{
            'socialnetworkprofile_set-TOTAL_FORMS': '2', 'socialnetworkprofile_set-INITIAL_FORMS': '1',
            'socialnetworkprofile_set-0-id': existing.pk, 'socialnetworkprofile_set-0-username': '',
        })
        self.assertEqual(self.client.post(reverse('update_profile'), data).status_code, 302)
        self.assertFalse(SocialNetworkProfile.objects.exists())

    def test_names_and_email_are_required(self):
        response = self.client.post(reverse('update_profile'), self.data(first_name='', email=''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['user_form'].errors), {'first_name', 'email'})

    def test_upload_avatar(self):
        with override_settings(MEDIA_ROOT=self.media):
            image = SimpleUploadedFile('yo.png', base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='), 'image/png')
            response = self.client.post(reverse('upload_avatar_profile'), {'image': image}, follow=True)
            self.assertRedirects(response, reverse('update_profile'))
            self.assertContains(response, 'Actualizamos tu foto de perfil')
            self.user.profile.refresh_from_db()
            self.assertTrue(self.user.profile.image.name.startswith('users/profiles/'))

            previous = self.user.profile.image.name
            fake = SimpleUploadedFile('yo.png', b'no soy una imagen', 'image/png')
            response = self.client.post(reverse('upload_avatar_profile'), {'image': fake}, follow=True)
            self.assertRedirects(response, reverse('update_profile'))
            self.assertEqual([m.level_tag for m in response.context['messages']], ['error'])
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.image.name, previous)
