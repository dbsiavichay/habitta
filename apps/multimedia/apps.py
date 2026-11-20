from django.apps import AppConfig


class MultimediaConfig(AppConfig):
    name = 'apps.multimedia'

    def ready(self):
        from . import signals  # noqa: F401
