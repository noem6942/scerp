# core/signals.py
from django.contrib import messages
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

import logging

from .models import Tenant #, TenantSetup

logger = logging.getLogger(__name__)  # Using the app name for logging


@receiver(post_save, sender=Tenant)
def tenant_post_create(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Tenant is created."""
    if created:
        # This code only runs the first time the tenant is created (not on updates)
        
        # Perform follow-up actions
        
        # TenantSetup
        tenant_admin, created = TenantSetup.objects.get_or_create(
            tenant=instance, 
            created_by=instance.created_by,
            modified_by=instance.modified_by)

        if created:
            logger.info(_('Tenant created.'))
        else:
            logger.info(_('Tenant already existing.'))        
