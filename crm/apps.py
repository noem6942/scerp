from django.apps import AppConfig
from django.utils.translation import get_language, gettext_lazy as _


class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    verbose_name = _('CRM')
    
    def ready(self):
        # Import signal handlers to register them
        import crm.signals  # inform CRM about changes
        # import accounting.signals  # inform accounting about changes
