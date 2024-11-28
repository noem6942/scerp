from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class VaultConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vault'
    verbose_name = 'Vault'
