# chat/consumers.py
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json

from django.contrib.auth.models import User
from django.db.models import Q
from .models import Conversation, Message

from django.template.loader import render_to_string

class MessageConsumer(WebsocketConsumer):
    def connect(self):
        sender = self.scope['user']
        receiver_id = self.scope['url_route']['kwargs']['receiver']
        self.load_conversation(sender, receiver_id)
        self.join_group()
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def load_conversation(self, sender, receiver_id):
        try:
            receiver = User.objects.get(pk=receiver_id)
        except User.DoesNotExist:
            self.conversation = None
            return

        try:
            conversation = Conversation.objects.get(Q(owner=sender, member=receiver)|Q(owner=receiver, member=sender))
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(owner=sender, member=receiver)

        self.conversation = conversation

    def join_group(self):
        if not self.conversation: return        
        self.room_name = self.conversation.id
        self.room_group_name = f'chat_{self.room_name}'

        #Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

    def render_message(self, message):
        template =  'messenger/chat_message_receiver.html'
        return render_to_string(template, context={'message': message})


    # Receive message from WebSocket
    def receive(self, text_data):
        data = json.loads(text_data)
        sender = self.scope['user']
        message = data['message']
        message = Message.objects.create(sender=sender, content=message,conversation=self.conversation)
        
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'message',
                'message': self.render_message(message)
            }
        )

    # Receive message from room group
    def message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))