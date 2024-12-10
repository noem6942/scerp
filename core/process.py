# core/process.py
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.utils.text import slugify
import logging
import os

from scerp.locales import APP
from scerp.mixins import get_admin 

from ._init_user_groups import USER_GROUPS
from ._init_markdown import MODULE_PAGE
from .models import App

logger = logging.getLogger(__name__)  # Using the app name for logging


class AppSetup(object):

    def update_or_create(self):                
        admin = get_admin()
        for app_name in APP.APP_MODEL_ORDER.keys():
            if not App.objects.filter(name=app_name):
                app = App(
                    name=app_name,
                    modified_by=admin,
                    created_by=admin)
                app.save()            


class UserGroupSetup(object):
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


class DocumentationSetup(object):
    '''
        Manage documentation
    '''
    def __init__(self, name):
        self.name = name
        
    def create_markdown(self):
        """Creates a markdown file with sections for description, features, data, functions, and notes."""
        # Define the filename
        name = self.name
        filename = f"{slugify(name)}.md"        

        # Gather information from the user
        data = dict(
            name=name,
            description=input(f"Enter description for {name}: "),
            features=input(f"Enter special features for {name}: "),
            data=input(f"Enter data details for {name}: "),
            functions=input(f"Enter functions for {name}: "),
            notes=input(f"Enter notes for {name}: ")
        )

        # Prepare the content for the Markdown file
        content = MODULE_PAGE.format(**data)

        # Write the content to the markdown file
        filepath = os.path.join(settings.DOCS_SOURCE, filename)

        with open(filepath, 'w') as file:
            file.write(content)
    