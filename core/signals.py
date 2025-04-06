# core/signals.py
import logging
import os
from datetime import date
from PIL import Image

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from asset.models import Unit, AssetCategory
from billing.models import Period
from core.models import Title, PersonCategory

from .models import App, Tenant, TenantSetup, TenantLogo, UserProfile, Country
from scerp.mixins import is_url_friendly, read_yaml_file

logger = logging.getLogger(__name__)  # Using the app name for logging


YAML_FILENAME = 'init_tenant.yaml'


@receiver(pre_save, sender=Tenant)
def tenant_pre_save(sender, instance, **kwargs):
    """Check before new Tenant is created."""
    __ = sender  # not used
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
    if not created and not kwargs.get('init'):
        return  # No action

    # Intro ---------------------------------------------------------------

    # Add default apps
    for app in App.objects.order_by('name'):
        if app.is_mandatory:
            instance.apps.add(app)

    # Create TenantSetup
    tenant_setup, _created = TenantSetup.objects.get_or_create(
        tenant=instance,
        created_by=instance.created_by)
    logger.info(f"Tenant Setup '{instance.code}' created.")

    # Core ---------------------------------------------------------------
    init_data = read_yaml_file('core', YAML_FILENAME)

    # Title
    '''
    for data in init_data['Title']:
        data.update({
            'created_by': instance.created_by,
            'is_enabled_sync': False  # do not synchronize            
        })
        obj, _created = Title.objects.get_or_create(
            tenant=instance,            
            code=data.pop('code'),
            defaults=data)
        logger.info(f"created {obj}")
    '''
    # PersonCategory
    for data in init_data['PersonCategory']:
        data.update({
            'created_by': instance.created_by,
            'is_enabled_sync': False  # do not synchronize
        })
        obj, _created = PersonCategory.objects.get_or_create(
            tenant=instance,
            code=data.pop('code'),
            defaults=data)
        logger.info(f"created {obj}")

    # Asset ---------------------------------------------------------------
    units = []
    for data in init_data['Unit']:
        data.update({
            'created_by': instance.created_by,
            'is_enabled_sync': False  # do not synchronize
        })
        obj, _created = Unit.objects.get_or_create(
            tenant=instance,
            code=data.pop('code'),
            defaults=data)
        units.append(obj)
        logger.info(f"created {obj}")    
        
    for data in init_data['AssetCategory']:
        # Get unit
        unit = next(
            (x for x in units if x.code == data['unit']), None)
        if not unit:
            raise ValidationError(_(f"{data} has no valid unit."))
            
        # Assign    
        data.update({
            'unit': unit,
            'created_by': instance.created_by,
            'is_enabled_sync': False  # do not synchronize
        })
        obj, _created = AssetCategory.objects.update_or_create(
            tenant=instance,
            code=data.pop('code'),
            defaults=data)
        logger.info(f"created {obj}")                  


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
