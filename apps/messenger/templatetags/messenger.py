from django import template
from django.db.models import Q

from ..models import Conversation

register = template.Library()


@register.simple_tag
def get_conversation_receiver(conversation, sender):
    """El otro participante de una conversación."""
    return conversation.other(sender)


@register.simple_tag
def get_conversation_messages(sender, receiver):
    """Historial entre dos usuarios (lo usa el chat flotante del anuncio y del perfil)."""
    conversation = Conversation.objects.filter(
        Q(owner=sender, member=receiver) | Q(owner=receiver, member=sender)
    ).first()
    if conversation is None:
        return []
    return conversation.messages.select_related('sender__profile').order_by('create_date', 'pk')
