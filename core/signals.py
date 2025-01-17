# core/signals.py
import logging
from PIL import Image

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .models import App, Tenant, TenantSetup, TenantLogo, UserProfile
from scerp.mixins import is_url_friendly


PASSWORD_LENGTH = 32
logger = logging.getLogger(__name__)  # Using the app name for logging



@receiver(pre_save, sender=Tenant)
def tenant_pre_save(sender, instance, **kwargs):
    """Check before new Tenant is created."""
    if not is_url_friendly(instance.code):
        msg = _("Code cannot be displayed in an url.")
        raise ValidationError(msg)
    elif instance.code != instance.code.lower():
        msg = _("Code contains upper letters")
        raise ValidationError(msg)


@receiver(post_save, sender=Tenant)
def tenant_post_save(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Tenant is created."""
    __ = sender  # not used
    if created:
        # Create TenantSetup
        setup = TenantSetup.objects.create(
            tenant=instance,
            created_by=instance.created_by)

        # Add default apps
        for app in App.objects.order_by('name'):
            if app.is_mandatory:
                tenant_setup.apps.add(app)

        logger.info(f"Tenant Setup '{tenant.code}' created.")


@receiver(pre_save, sender=TenantSetup)
def tenant_setup_pre_save(sender, instance, **kwargs):
    """Check before new TenantSetup is saved"""
    MAX_SIZE_KB = 400  # unit: KB
    MAX_RESOLUTION = (2500, 2500)

    # Logo
    if instance.logo:  # Ensure a logo is uploaded before validation
        # Validate that the uploaded file is of an allowed type.
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if instance.logo.file.content_type not in allowed_types:
            msg = _("Unsupported file type. Only JPG, GIF, and PNG are allowed.")
            raise ValidationError(msg)

        # Validate that the file size does not exceed MAX_SIZE_KB.
        if instance.logo.size > MAX_SIZE_KB * 1024:
            raise ValidationError(_(f"File size exceeds {MAX_SIZE_KB}KB."))

        # Validate that the image resolution does not exceed 2500x2500 pixels.
        try:
            img = Image.open(instance.logo)
            if img.width > MAX_RESOLUTION[0] or img.height > MAX_RESOLUTION[1]:
                raise ValidationError(
                    _("Image resolution exceeds "
                      f"{MAX_RESOLUTION[0]} * {MAX_RESOLUTION[1]} pixels."))
        except Exception:
            raise ValidationError(_("Invalid image file."))


@receiver(post_save, sender=TenantLogo)
def tenant_logo(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Logo is created."""
    __ = created  # always perform check
    LOGO_TYPE = TenantLogo.Type
    if instance.type == LOGO_TYPE.MAIN:
        # Ensure only only one Main
        TenantLogo.objects.exclude(id=instance.id).filter(
            tenant=instance.tenant, type=LOGO_TYPE.MAIN
        ).update(type=LOGO_TYPE.OTHER)
