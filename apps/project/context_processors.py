from django.conf import settings


def integrations(request):
    """Expone a las plantillas qué integraciones externas están configuradas."""
    return {
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'GOOGLE_GEOCODING_API_KEY': settings.GOOGLE_GEOCODING_API_KEY,
        'FACEBOOK_APP_ID': settings.FACEBOOK_APP_ID,
        'FACEBOOK_LOGIN_ENABLED': bool(settings.FACEBOOK_APP_ID and settings.FACEBOOK_APP_SECRET),
        'TWITTER_LOGIN_ENABLED': bool(settings.TWITTER_API_KEY and settings.TWITTER_API_SECRET),
        'PAYPAL_ENABLED': bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET),
    }
