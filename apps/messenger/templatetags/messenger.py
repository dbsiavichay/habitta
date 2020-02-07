from django import template
from django.template.loader import render_to_string
from django.db.models import Q
#from django.contrib.contenttypes.models import ContentType
from ..models import Message, Conversation
from ..forms import MessageForm

register = template.Library()       

class MessageFormNode(template.Node):
    def __init__(self, receiver, template_name, success_url):       
        self.receiver = template.Variable(receiver)
        self.template_name = template_name
        self.success_url = template.Variable(success_url)        

    def render(self, context):
        receiver = self.receiver.resolve(context)        
        success_url = self.success_url.resolve(context)        
        form = MessageForm(initial={'receiver':receiver.id, 'success_url':success_url})

        context_dict = context.flatten()        
        context_dict['form'] = form
        formstr = render_to_string([self.template_name], context_dict)
        return formstr        


@register.tag(name='message_form')
def message_form(parser, token):
    """
    Syntax:
        {% message_form [object] template %}
    """
    try:        
        tag_name, obj, template_name, success_url = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a 3 or 4 arguments" % token.contents.split()[0])

    return MessageFormNode(obj, template_name[1:-1], success_url)

@register.simple_tag
def get_conversation_receiver(conversation, sender):
    user = conversation.member if sender == conversation.owner else conversation.owner
    return user

@register.simple_tag
def get_conversation_messages(sender, receiver):
    try:
        conversation = Conversation.objects.get(Q(owner=sender, member=receiver)|Q(owner=receiver, member=sender))
        messages = conversation.messages.all()
    except Conversation.DoesNotExist:
        messages = []
    return messages

@register.simple_tag
def get_conversations_count(user):
    count = Conversation.objects.filter(Q(owner=user)|Q(member=user)).exclude(messages__isnull=True).count()
    return count