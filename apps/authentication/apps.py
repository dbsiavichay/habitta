from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name = 'apps.authentication'
    verbose_name = 'Autenticación'

    def ready(self):
    	from . import signals