"""Correo al usuario cuando el equipo confirma o rechaza su transferencia desde el admin."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.project.templatetags.habitta import money

from .models import Payment

logger = logging.getLogger(__name__)

SUBJECTS = {
    Payment.CONFIRMED: 'Confirmamos tu pago en {site_name}',
    Payment.REJECTED: 'No pudimos confirmar tu pago en {site_name}',
}


def notify_payment_status(payment, request=None, reason=''):
    """Envía el correo del estado actual del pago. Devuelve False si no se pudo (sin correo o error SMTP).

    Un fallo al enviar no debe deshacer el cambio de estado: se registra y el admin avisa al staff.
    """
    user = payment.user
    if payment.status not in SUBJECTS or not user.email:
        return False

    site_url = settings.SITE_URL or (request.build_absolute_uri('/').rstrip('/') if request else '')
    context = {
        'site_name': settings.SITE_NAME,
        'site_url': site_url,
        'user': user,
        'payment': payment,
        'amount': money(payment.amount),
        'paid_for': payment.get_object_or_none(),
        'confirmed': payment.status == Payment.CONFIRMED,
        'reason': reason.strip(),
    }
    message = EmailMultiAlternatives(
        SUBJECTS[payment.status].format(site_name=settings.SITE_NAME),
        render_to_string('payments/emails/payment_status.txt', context),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    message.attach_alternative(render_to_string('payments/emails/payment_status.html', context), 'text/html')
    try:
        message.send()
    except Exception:
        logger.exception('No se pudo enviar el aviso del pago %s', payment.pk)
        return False
    return True
