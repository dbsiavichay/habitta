from django.apps import AppConfig


class MultimediaConfig(AppConfig):
    name = 'apps.multimedia'
    verbose_name = 'Multimedia'

    def ready(self):
        from . import signals  # noqa: F401
