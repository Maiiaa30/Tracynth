from django.apps import AppConfig


class ConfigConfig(AppConfig):
    name = "config"
    verbose_name = "Tracynth configuration"

    def ready(self):
        from . import checks  # noqa: F401
