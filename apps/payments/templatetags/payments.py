from django import template
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.core.exceptions import ImproperlyConfigured
from ..forms import PaymentForm
from ..models import Payment

from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.inclusion_tag('payments/payment_button.html')
def check_payment(object, user):        
    context = {
    	'object_id': object.id,
    	'content_type': ContentType.objects.get_for_model(object).id,        
    }
    try:
        payment = Payment.objects.filter(user=user).exclude(status=Payment.REJECTED).get(**context)        
        context.update({'payment': payment})
    except:
        context.update({'price': object.get_price_area()})    
    return context

@register.simple_tag(takes_context=True)
def payment_form(context, **kwargs):
    request = context.get('request')
    obj = kwargs.get('obj')
    amount = kwargs.get('amount')
    content_type = ContentType.objects.get_for_model(obj)
    form = PaymentForm(initial={'object_id': obj.id, 'content_type': content_type, 'amount': amount})
    context =  {        
        'form': form
    }
    liststr = render_to_string(['payments/payment_form.html',], context, request=request)
    return liststr

@register.filter(takes_context=True)
def is_pay(obj, user):    
    kwargs = {
        'object_id': obj.id,
        'content_type': ContentType.objects.get_for_model(obj).id,        
    }
    try:
        payment = Payment.objects.filter(user=user).exclude(status=Payment.REJECTED).get(**kwargs)        
        return True
    except:
        return False



