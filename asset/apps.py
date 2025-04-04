from django.apps import AppConfig


class AssetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'asset'

    def ready(self):
        # Import signal handlers to handel Unit, AssetCategory, Device
        import accounting.signals_cash_ctrl
