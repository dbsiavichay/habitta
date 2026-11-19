"""
Cliente mínimo para la API REST de PayPal Orders v2.

Reemplaza a ``paypalrestsdk`` (archivado, usaba la API v1 de Payments).
Flujo: create_order() -> el usuario aprueba en PayPal -> capture_order().
Documentación: https://developer.paypal.com/docs/api/orders/v2/
"""
from decimal import Decimal

import requests
from django.conf import settings

SANDBOX_URL = 'https://api-m.sandbox.paypal.com'
LIVE_URL = 'https://api-m.paypal.com'


class PayPalError(Exception):
    pass


def is_configured():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def _base_url():
    return LIVE_URL if settings.PAYPAL_MODE == 'live' else SANDBOX_URL


def _request(method, path, **kwargs):
    kwargs.setdefault('timeout', settings.EXTERNAL_HTTP_TIMEOUT)
    try:
        response = requests.request(method, _base_url() + path, **kwargs)
    except requests.RequestException as exc:
        raise PayPalError(f'Error de conexión con PayPal: {exc}') from exc
    if response.status_code >= 400:
        raise PayPalError(f'PayPal respondió {response.status_code}: {response.text[:500]}')
    return response.json()


def _auth_headers():
    data = _request(
        'POST', '/v1/oauth2/token',
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={'grant_type': 'client_credentials'},
    )
    return {'Authorization': f"Bearer {data['access_token']}", 'Content-Type': 'application/json'}


def create_order(amount, description, reference_id, return_url, cancel_url, currency='USD'):
    """Crea una orden y devuelve ``(order_id, approve_url)``."""
    if not is_configured():
        raise PayPalError('PayPal no está configurado')

    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': str(reference_id),
            'description': str(description)[:127],
            'amount': {'currency_code': currency, 'value': f'{Decimal(amount):.2f}'},
        }],
        'payment_source': {
            'paypal': {
                'experience_context': {
                    'return_url': return_url,
                    'cancel_url': cancel_url,
                    'user_action': 'PAY_NOW',
                    'shipping_preference': 'NO_SHIPPING',
                },
            },
        },
    }
    order = _request('POST', '/v2/checkout/orders', json=payload, headers=_auth_headers())
    approve_url = next(
        (link['href'] for link in order.get('links', []) if link.get('rel') in ('payer-action', 'approve')),
        None,
    )
    if not approve_url:
        raise PayPalError('PayPal no devolvió la URL de aprobación')
    return order['id'], approve_url


def capture_order(order_id):
    """Captura una orden aprobada y devuelve la respuesta de PayPal."""
    return _request('POST', f'/v2/checkout/orders/{order_id}/capture', json={}, headers=_auth_headers())


def captured_amount(order):
    """Suma de los montos capturados en una orden (Decimal)."""
    total = Decimal('0')
    for unit in order.get('purchase_units', []):
        for capture in unit.get('payments', {}).get('captures', []):
            if capture.get('status') == 'COMPLETED':
                total += Decimal(capture['amount']['value'])
    return total
