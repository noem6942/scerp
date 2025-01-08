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

from ._init_user_groups import ADMIN_GROUP_NAME, USER_GROUPS
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
    if created:        
        # Create empty TenantSetup
        tenant_setup, created = TenantSetup.objects.get_or_create(
            tenant=instance,
            defaults={
                'created_by': instance.modified_by,
                'modified_by': instance.modified_by,
            }
        )
                    
        # Add groups
        group_names = [x['name'] for x in USER_GROUPS]
        groups = Group.objects.filter(name__in=group_names)
        for group in groups:
            tenant_setup.groups.add(group)   
        
        # Create a new user if necessary
        user = User.objects.filter(
            username=instance.initial_user_email).first()
        if not user:
            # Generate a random character password and save it (temp)
            password = get_random_string(PASSWORD_LENGTH)        
            instance.initial_user_password = password
            instance.save()
            
            # Create a new user
            user = User.objects.create_user(
                username=instance.initial_user_email,
                email=instance.initial_user_email,
                first_name=instance.initial_user_first_name,
                last_name=instance.initial_user_last_name,
                password=password,
                is_staff=True
            )

            # Add user profile        
            user_profil = UserProfile.objects.create(
                user=user,            
                created_by=instance.created_by, 
                modified_by=instance.modified_by)  

        # Add the user to the admin group
        admin_name = next(
            (x['name'] 
                for x in USER_GROUPS 
                if x['name'] == ADMIN_GROUP_NAME
            ), None)
        admin_group = Group.objects.filter(name=admin_name).first()
        if admin_group:
            user.groups.add(admin_group)     

        # message
        logger.info(f"created tenant '{instance.name}'") 

    else:
        pass
        # logger.info(f"{len(currencies)} analyzed.") 


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
        