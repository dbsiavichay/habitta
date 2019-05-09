from django import template
from ..models import PaypalPayment

from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.inclusion_tag('payments/payment_button.html')
def check_payment(object, user):        
    context = {
    	'object': object,
    	'content_type': ContentType.objects.get_for_model(object)
    }
    try:
        paypal = PaypalPayment.objects.get(property=object, user=user)
        paid = paypal.is_paid
    except:
        paid = False
    context.update({'is_paid': paid})
    return context
