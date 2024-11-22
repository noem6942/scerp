# core/process.py
from django.contrib.auth.models import Group, Permission
import logging

logger = logging.getLogger(__name__)  # Using the app name for logging

USER_GROUPS = [
    # Testing
    {'name': 'local_user', 'permissions': []},
    
    # Funktionen
    {'name': 'Funktion Zweckverband', 'permissions': []},
    
    # Gemeinderat    
    {'name': 'Gemeinderat', 'permissions': []},
    {'name': 'Gemeinderat - Präsidiales', 'permissions': []},
    {'name': 'Gemeinderat - Finanzen', 'permissions': []},
    {'name': 'Gemeinderat - Sicherheit', 'permissions': []},
    {'name': 'Gemeinderat - Soziales', 'permissions': []},
    {'name': 'Gemeinderat - Planung/Wirtschaft/Tourismus', 'permissions': []},
    {'name': 'Gemeinderat - Hoch-/Tiefbau', 'permissions': []},
    {'name': 'Gemeinderat - Bildung/Kultur', 'permissions': []},
    
    # Intern
    {'name': 'Admin', 'permissions': []},
    {
        'name': 'Intern Leitung',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Kanzlei',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Einwohnerdienste',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Personalwesen',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Gesundheit-/Sozialwesen',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Finanzen',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Steuern',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Liegenschaftsverwaltung',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Bauwesen',
        'permissions': [
        ]
    },
    {
        'name': 'Intern Bildung',
        'permissions': [
        ]
    },
]
'''    
    {
        'name': 'local_admin',
        'permissions': [
            'core.add_person',
            'core.change_person',
            'core.delete_person',
            'core.view_person',
            
            'core.add_userprofile',
            'core.change_userprofile',
            'core.delete_userprofile',
            'core.view_userprofile',
            
            'auth.add_user',
            'auth.change_user',
            'auth.delete_user',
            'auth.view_user',
        ]
    },
'''


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

        logger.info('User group setup complete.')
        return True
