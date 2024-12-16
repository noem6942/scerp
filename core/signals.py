# core/signals.py
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

import logging

from ._init_user_groups import ADMIN_GROUP_NAME, USER_GROUPS
from .models import App, Tenant, TenantSetup, UserProfile


PASSWORD_LENGTH = 32
logger = logging.getLogger(__name__)  # Using the app name for logging
        

@receiver(post_save, sender=Tenant)
def tenant_create(sender, instance, created, **kwargs):
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
