# core/signals.py
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

import logging

from core.safeguards import save_logging
from scerp.mixins import get_admin
from ._init_user_groups import USER_GROUPS
from .models import Tenant, TenantSetup, TenantLocation, UserProfile


PASSWORD_LENGTH = 32
logger = logging.getLogger(__name__)  # Using the app name for logging
        

@receiver(post_save, sender=Tenant)
def tenant_create(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Tenant is created."""
    if created:        
        # Create empty TenantSetup
        tenant_setup, _created = TenantSetup.objects.get_or_create(
            tenant=instance, 
            created_by=instance.created_by, 
            modified_by=instance.modified_by
        )
        
        # Create empty TenantLocation
        _obj, _created = TenantLocation.objects.get_or_create(
            org_name=instance.name,
            tenant=instance, 
            created_by=instance.created_by, 
            modified_by=instance.modified_by
        )        
        
        # Add groups
        group_names = [x['name'] for x in USER_GROUPS]
        groups = Group.objects.filter(name__in=group_names)
        for group in groups:
            tenant_setup.groups.add(group)

        # Create user
        # Generate a random character password
        password = get_random_string(PASSWORD_LENGTH)
        
        # Create a new user
        user = User.objects.create_user(
            username=instance.initial_user_email,
            email=instance.initial_user_email,
            first_name=instance.initial_user_first_name,
            last_name=instance.initial_user_last_name,
            password=password,
            is_staff=True
        )

        # Add the user to the admin group
        admin_name = next(
            (x['name'] for x in USER_GROUPS if x['name'] == 'Admin'), None)
        admin_group = Group.objects.filter(name=admin_name).first()
        if admin_group:
            user.groups.add(admin_group)

        # Add user profile        
        user_profil = UserProfile.objects.create(
            user=user,
            created_by=instance.created_by, 
            modified_by=instance.modified_by)        

        msg = _("Created user '{username}' with password {password}").format(
            username=user.username, password=password)
        logger.info(msg)

    else:
        pass
        # logger.info(f"{len(currencies)} analyzed.") 
