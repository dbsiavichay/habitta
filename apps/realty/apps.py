from django.apps import AppConfig


class RealtyConfig(AppConfig):
    name = 'apps.realty'
    verbose_name = 'Bienes raíces'

    def ready(self):
        from . import signals  # noqa: F401
