"""
Configuración de Django para Habitta.

Todos los valores sensibles o dependientes del entorno se leen de variables
de entorno (ver .env.example). Documentación:
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os

import environ
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CSRF_TRUSTED_ORIGINS=(list, []),
    SECURE_SSL=(bool, False),
)

# Permite desarrollo local fuera de Docker con un archivo .env.local en la raíz.
environ.Env.read_env(os.path.join(BASE_DIR, '.env.local'))

DEBUG = env('DEBUG')

# En producción SECRET_KEY es obligatoria; en desarrollo se usa una clave insegura fija.
SECRET_KEY = env('SECRET_KEY', default='')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Define la variable de entorno SECRET_KEY (obligatoria con DEBUG=False).')
    SECRET_KEY = 'insecure-dev-key-only-for-local-development'

ALLOWED_HOSTS = env('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880


# Application definition
DJANGO_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'hydra',
    'channels',
    'django_cotton',
    'django_htmx',
    'django_tailwind_cli',
]

MY_APPS = [
    'apps.auctions',
    'apps.payments',
    'apps.project',
    'apps.authentication',
    'apps.comments',
    'apps.messenger',
    'apps.realty',
    'apps.multimedia',
    'apps.logs',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + MY_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

# django_cotton reemplaza APP_DIRS por sus loaders (cotton + filesystem + app_directories, cacheados)
# y registra {% cotton %} como builtin. Los componentes viven en templates/cotton/.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'builtins': ['lucide.templatetags.lucide'],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.project.context_processors.integrations',
                'apps.project.context_processors.brand',
                'apps.messenger.context_processors.unread_messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgis://habitta:habitta@localhost:5432/habitta'),
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'es-EC'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True
# Mantiene el punto decimal (comportamiento previo con USE_L10N=False):
# coordenadas y precios se usan en atributos HTML y JavaScript.
FORMAT_MODULE_PATH = ['config.formats']


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'
        if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Tailwind CSS v4 + daisyUI 5 con el binario standalone (sin Node).
#   python manage.py tailwind watch   -> recompila en desarrollo
#   python manage.py tailwind build   -> CSS minificado (lo ejecuta el Dockerfile)
# tailwindcss-extra es el CLI oficial con daisyUI incluido (github.com/dobicinaitis/tailwind-cli-extra).
TAILWIND_CLI_USE_DAISY_UI = True
TAILWIND_CLI_VERSION = '2.10.34'
TAILWIND_CLI_PATH = env('TAILWIND_CLI_PATH', default='.django_tailwind_cli')
TAILWIND_CLI_SRC_CSS = 'assets/tailwind/source.css'
TAILWIND_CLI_DIST_CSS = 'css/habitta.css'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
SERVE_MEDIA = env.bool('SERVE_MEDIA', default=DEBUG)

# Login config
LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('home')

FORMS_URLFIELD_ASSUME_HTTPS = True


# Marca y datos de contacto que se muestran en el sitio (vacíos = no se muestran)
SITE_NAME = env('SITE_NAME', default='Habitta')
SITE_TAGLINE = env('SITE_TAGLINE', default='Inmuebles, servicios y empleos cerca de ti')
# Razón social que aparece en los términos y condiciones (la aplica `manage.py rebrand_content`).
LEGAL_NAME = env('LEGAL_NAME', default='') or SITE_NAME
# URL pública sin barra final; se usa en enlaces absolutos (PDF, QR, OpenGraph).
SITE_URL = env('SITE_URL', default='').rstrip('/')
CONTACT_EMAIL = env('CONTACT_EMAIL', default='')
CONTACT_PHONE = env('CONTACT_PHONE', default='')
CONTACT_ADDRESS = env('CONTACT_ADDRESS', default='')
SOCIAL_FACEBOOK = env('SOCIAL_FACEBOOK', default='')
SOCIAL_INSTAGRAM = env('SOCIAL_INSTAGRAM', default='')
SOCIAL_X = env('SOCIAL_X', default='')


# Integraciones externas (todas opcionales: vacías = deshabilitadas)
TWITTER_API_KEY = env('TWITTER_API_KEY', default='')
TWITTER_API_SECRET = env('TWITTER_API_SECRET', default='')

FACEBOOK_APP_ID = env('FACEBOOK_APP_ID', default='')
FACEBOOK_APP_SECRET = env('FACEBOOK_APP_SECRET', default='')

PAYPAL_MODE = env('PAYPAL_MODE', default='sandbox')
PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')

TINIFY_API_KEY = env('TINIFY_API_KEY', default='')

GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')

# Timeout (segundos) para llamadas HTTP a servicios externos
EXTERNAL_HTTP_TIMEOUT = env.int('EXTERNAL_HTTP_TIMEOUT', default=10)


# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [{
                'address': env('REDIS_URL', default='redis://localhost:6379/0'),
                # redis-py 8 trae socket_timeout=5 por defecto y channels_redis espera mensajes con
                # BZPOPMIN durante 5 s: la lectura vencía justo antes y cerraba los WebSocket del chat.
                'socket_timeout': 15,
            }],
        },
    },
}


# Email
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_USER = env('EMAIL_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_PASSWORD', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
# `or` y no `default=`: .env.example trae la variable vacía y env() devolvería '' (correo sin remitente).
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='') or EMAIL_HOST_USER or 'webmaster@localhost'
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST
    else 'django.core.mail.backends.console.EmailBackend',
)


# Seguridad detrás de un proxy HTTPS (producción)
if env('SECURE_SSL'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=3600)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')},
}
