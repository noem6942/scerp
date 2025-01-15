from django.apps import AppConfig


class TimeAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'time_app'

    def ready(self):
        import time_app.signals  # Import signals