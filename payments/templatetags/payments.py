from django import template
from ..models import PaypalPayment

register = template.Library()

@register.inclusion_tag('payments/payment_button.html')
def check_payment(property, user):        
    context = {'property': property}
    try:
        paypal = PaypalPayment.objects.get(property=property, user=user)
        paid = paypal.is_paid
    except:
        paid = False
    context.update({'is_paid': paid})
    return context
