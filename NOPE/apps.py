from django.apps import AppConfig


class NopeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'NOPE'
    
    def ready(self):
        """Import signals when Django starts."""
        import NOPE.signals

