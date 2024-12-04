# core/process.py
from django.contrib.auth.models import Group, Permission
import logging

from ._init_user_groups import USER_GROUPS

logger = logging.getLogger(__name__)  # Using the app name for logging


class UserGroup:
    '''
    Manage user groups with specific permissions.
    '''

    def update_or_create(self):
        '''
        Create or update user groups with defined permissions.
        '''
        for group_info in USER_GROUPS:
            # Create the group if it doesn't exist
            group, created = Group.objects.get_or_create(
                name=group_info['name']
            )
            if created:
                logger.info(
                    f"Group '{ group_info['name']}' created successfully."
                )
            else:
                logger.warning(
                    f"Group '{group_info['name']}' already exists."
                )

            # Clear all existing permissions from the group
            group.permissions.clear()
            logger.info(
                f"All permissions removed from group `{group_info['name']}`."
            )

            # Assign new permissions to the group
            for perm in group_info['permissions']:
                app_label, codename = perm.split('.')
                try:
                    # Filter by app label and codename to ensure the correct permission
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    group.permissions.add(permission)
                    logger.info(
                        f"Permission '{perm}' added to "
                        f"group '{group_info['name']}'."                        
                    )
                except Permission.DoesNotExist:
                    logger.error(
                        f"Permission '{perm}' does not exist.")            
            
            # Assign all permissions to admin  # TEMP!!!
            if group_info['name'] == 'Admin':
                admin_group = Group.objects.filter(name='Admin').first()  
                all_permissions = Permission.objects.all()
                for permission in all_permissions:
                    admin_group.permissions.add(permission)                

        logger.info('User group setup complete.')
        return True
