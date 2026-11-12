import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
from django.db.models import Q
from django.template.loader import render_to_string

from .models import Conversation, Message


class MessageConsumer(WebsocketConsumer):
    room_group_name = None
    conversation = None

    def connect(self):
        sender = self.scope['user']
        if not sender.is_authenticated:
            self.close()
            return

        receiver_id = self.scope['url_route']['kwargs']['receiver']
        self.conversation = self.load_conversation(sender, receiver_id)
        if self.conversation is None:
            self.close()
            return

        self.room_group_name = f'chat_{self.conversation.id}'
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        if self.room_group_name:
            async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

    def load_conversation(self, sender, receiver_id):
        try:
            receiver = User.objects.get(pk=int(receiver_id))
        except (User.DoesNotExist, ValueError):
            return None

        if receiver == sender:
            return None

        conversation = Conversation.objects.filter(
            Q(owner=sender, member=receiver) | Q(owner=receiver, member=sender)
        ).first()
        if conversation is None:
            conversation = Conversation.objects.create(owner=sender, member=receiver)
        return conversation

    def render_message(self, message):
        template = 'messenger/chat_message_receiver.html'
        return render_to_string(template, context={'message': message})

    # Mensaje recibido desde el WebSocket
    def receive(self, text_data=None, bytes_data=None):
        if not self.conversation or not text_data:
            return
        try:
            content = str(json.loads(text_data).get('message', '')).strip()
        except (ValueError, AttributeError):
            return
        if not content:
            return

        message = Message.objects.create(
            sender=self.scope['user'], content=content, conversation=self.conversation
        )
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {'type': 'chat.message', 'message': self.render_message(message)},
        )

    # Mensaje recibido desde el grupo
    def chat_message(self, event):
        self.send(text_data=json.dumps({'message': event['message']}))
