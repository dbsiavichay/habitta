from django import template
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string

from ..forms import PaymentForm
from ..models import Payment

register = template.Library()


def _user_payment(obj, user):
    """Último pago no rechazado del usuario para ``obj`` (o None)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    return (
        Payment.objects.filter(
            user=user,
            object_id=obj.pk,
            content_type=ContentType.objects.get_for_model(obj),
        )
        .exclude(status=Payment.REJECTED)
        .order_by('-status', '-date')
        .first()
    )


@register.inclusion_tag('payments/payment_button.html', takes_context=True)
def check_payment(context, object, user, label='Pagar'):
    """Botón de pago, de descarga o de pago pendiente, según el estado.

    Pasa el `request` a la plantilla: sin él, {% payment_form %} no pone el token CSRF y el pago
    responde 403.
    """
    return {
        'request': context.get('request'),
        'object': object,
        'payment': _user_payment(object, user),
        'price': object.get_price_area(),
        'label': label,
    }


@register.simple_tag(takes_context=True)
def payment_form(context, **kwargs):
    request = context.get('request')
    label = kwargs.get('label', 'Pagar')
    obj = kwargs.get('obj')
    # El monto es sólo informativo: el servidor recalcula el precio al pagar.
    amount = kwargs.get('amount')
    content_type = ContentType.objects.get_for_model(obj)
    form = PaymentForm(initial={'object_id': obj.id, 'content_type': content_type, 'amount': amount})
    return render_to_string(
        ['payments/payment_form.html'], {'form': form, 'label': label}, request=request
    )


@register.filter
def is_pay(obj, user):
    """True sólo si el usuario tiene un pago CONFIRMADO para ``obj``."""
    payment = _user_payment(obj, user)
    return bool(payment and payment.is_confirmed())
