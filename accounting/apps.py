from django.apps import AppConfig
from django.utils.translation import get_language, gettext_lazy as _


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'
    verbose_name = _('Accounting')

    def ready(self):
        # Import signal handlers to register them
        import accounting.signals
        import accounting.signals_cash_ctrl
