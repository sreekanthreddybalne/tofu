from django.apps import AppConfig


class appConfig(AppConfig):
    name = 'app'

    def ready(self):
        from . import signals
