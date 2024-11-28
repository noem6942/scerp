from django.apps import AppConfig
from django.utils.translation import get_language, gettext_lazy as _

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = _('Admin')
    
    def ready(self):
        # Import signal handlers to register them
        import core.signals
