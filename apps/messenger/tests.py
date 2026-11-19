"""Pruebas de mensajes (fase 3): lista con no leídos, conversación en página completa y marcado de leídos.

    docker compose exec web python manage.py test apps.messenger.tests
"""
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.messenger.models import Conversation, Message
from apps.project.testing import IN_MEMORY_LAYER, create_user, session_cookie


class ConversationPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = create_user('ana')
        cls.luis = create_user('luis')
        cls.eva = create_user('eva')
        cls.conversation = Conversation.objects.create(owner=cls.luis, member=cls.ana)
        Message.objects.create(conversation=cls.conversation, sender=cls.luis, content='¿Sigue disponible?')
        Message.objects.create(conversation=cls.conversation, sender=cls.luis, content='¿Puedo visitarla el sábado?')
        # Conversación vacía (el chat la crea al abrirse): no se lista
        Conversation.objects.create(owner=cls.eva, member=cls.ana)

    def setUp(self):
        self.client.force_login(self.ana)

    def test_list_shows_last_message_and_unread(self):
        response = self.client.get(reverse('conversations'))
        self.assertTemplateUsed(response, 'layouts/app.html')
        conversations = list(response.context['object_list'])
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].unread, 2)
        self.assertEqual(conversations[0].last_content, '¿Puedo visitarla el sábado?')
        self.assertContains(response, '2 sin leer')

    def test_unread_badge_in_navbar(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Mensajes, 2 sin leer')
        self.client.force_login(self.luis)
        self.assertNotContains(self.client.get(reverse('home')), 'sin leer')

    def test_opening_the_conversation_marks_it_read(self):
        response = self.client.get(reverse('detail_conversation', args=[self.conversation.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['receiver'], self.luis)
        self.assertContains(response, 'chatWidget(%d, { autoconnect: true })' % self.luis.pk)
        self.assertContains(response, '¿Sigue disponible?')
        self.assertEqual(Message.objects.unread_for(self.ana).count(), 0)
        # Lo que envió el otro participante sigue sin leer para él (aquí no hay nada pendiente)
        self.assertEqual(Message.objects.unread_for(self.luis).count(), 0)
        self.assertNotContains(response, 'sin leer')

    def test_someone_elses_conversation_is_not_found(self):
        self.client.force_login(self.eva)
        self.assertEqual(self.client.get(reverse('detail_conversation', args=[self.conversation.pk])).status_code, 404)
        self.assertEqual(Message.objects.unread_for(self.ana).count(), 2)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ChatReadReceiptsTests(TransactionTestCase):
    """Con el chat abierto los mensajes recibidos quedan leídos (al conectar y al llegar)."""

    def test_connecting_and_receiving_marks_messages_read(self):
        from config.asgi import application

        ana = create_user('ana')
        luis = create_user('luis')
        conversation = Conversation.objects.create(owner=luis, member=ana)
        Message.objects.create(conversation=conversation, sender=luis, content='Hola')

        async def scenario():
            from channels.db import database_sync_to_async

            ana_cookie = await database_sync_to_async(session_cookie)(ana)
            luis_cookie = await database_sync_to_async(session_cookie)(luis)
            a = WebsocketCommunicator(application, f'/ws/message/{luis.id}/', headers=[(b'origin', b'http://localhost'), (b'cookie', ana_cookie)])
            self.assertTrue((await a.connect())[0])
            unread_after_connect = await database_sync_to_async(Message.objects.unread_for(ana).count)()

            b = WebsocketCommunicator(application, f'/ws/message/{ana.id}/', headers=[(b'origin', b'http://localhost'), (b'cookie', luis_cookie)])
            self.assertTrue((await b.connect())[0])
            await b.send_json_to({'message': '¿La vemos mañana?'})
            received = await a.receive_json_from(timeout=5)
            await b.receive_json_from(timeout=5)
            await a.disconnect()
            await b.disconnect()
            unread_after_message = await database_sync_to_async(Message.objects.unread_for(ana).count)()
            return unread_after_connect, received, unread_after_message

        unread_after_connect, received, unread_after_message = async_to_sync(scenario)()
        self.assertEqual(unread_after_connect, 0)
        self.assertEqual(set(received), {'bubble', 'own'})  # ya no se envía el HTML viejo (`message`)
        self.assertEqual(unread_after_message, 0)
