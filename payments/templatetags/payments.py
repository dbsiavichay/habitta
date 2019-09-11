from django import template
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
