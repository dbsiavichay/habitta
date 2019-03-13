from django import template
from ..models import PaypalPayment

register = template.Library()

@register.inclusion_tag('payments/payment_button.html')
def check_payment(property, user):    
    res = {'render': False}
    if not property.get_path_files: return res
    res['render'] = True
    res['property'] = property
    try:
        paypal = PaypalPayment.objects.get(property=property, user=user)
        res['is_paid'] = paypal.is_paid
    except PaypalPayment.DoesNotExist:
        res['is_paid'] = False

    return res
