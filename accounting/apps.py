from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):
        # Import signal handlers to register them
        import accounting.signals
