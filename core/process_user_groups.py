from django.contrib.auth.models import Group, Permission
import logging

logger = logging.getLogger(__name__)  # Using the app name for logging

USER_GROUPS = [
    {
        'name': 'local_user',
        'permissions': [
            'core.add_person',
            'core.change_person',
            'core.delete_person',
            'core.view_person',
        ]
    },
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
]


class UserGroup:
    """
    Manage user groups with specific permissions.
    """

    def update_or_create(self):
        """
        Create or update user groups with defined permissions.
        """
        for group_info in USER_GROUPS:
            # Create the group if it doesn't exist
            group, created = Group.objects.get_or_create(
                name=group_info['name']
            )
            if created:
                logger.info(
                    'Group "%s" created successfully.', group_info['name']
                )
            else:
                logger.warning(
                    'Group "%s" already exists.', group_info['name']
                )

            # Clear all existing permissions from the group
            group.permissions.clear()
            logger.info(
                'All permissions removed from group "%s".', group_info['name']
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
                        'Permission "%s" added to group "%s".',
                        perm, group_info['name']
                    )
                except Permission.DoesNotExist:
                    logger.error(
                        'Permission "%s" does not exist.', perm
                    )

        logger.info('User group setup complete.')
        return True
