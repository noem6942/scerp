# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import gettext_lazy as _

import logging

from .models import Tenant


logger = logging.getLogger(__name__)  # Using the app name for logging
        
        
TENANT_SETUP_FORMAT = {
    'admin': {
        'text_area_default': {
            'rows': 1,
            'cols': 80,
        }
    }
}        
        

@receiver(post_save, sender=Tenant)
def tenant_create(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Tenant is created."""
    if created:
        # This code only runs the first time the tenant is created (not on updates)
        pass
    else:
        pass
        # logger.info(f"{len(currencies)} analyzed.") 
