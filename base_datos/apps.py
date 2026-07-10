from django.apps import AppConfig

class BaseDatosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'base_datos'

    def ready(self):
        from . import signals  # noqa: F401 — conecta la invalidación de caché
