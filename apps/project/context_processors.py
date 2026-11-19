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


def brand(request):
    """Nombre del sitio, datos de contacto y redes sociales (los vacíos no se muestran)."""
    socials = [
        {'network': network, 'url': url, 'label': label}
        for network, url, label in (
            ('facebook', settings.SOCIAL_FACEBOOK, 'Facebook'),
            ('instagram', settings.SOCIAL_INSTAGRAM, 'Instagram'),
            ('x-twitter', settings.SOCIAL_X, 'X'),
        )
        if url
    ]
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_TAGLINE': settings.SITE_TAGLINE,
        'SITE_URL': settings.SITE_URL or request.build_absolute_uri('/').rstrip('/'),
        'CONTACT_EMAIL': settings.CONTACT_EMAIL,
        'CONTACT_PHONE': settings.CONTACT_PHONE,
        'CONTACT_ADDRESS': settings.CONTACT_ADDRESS,
        'SOCIAL_LINKS': socials,
    }
