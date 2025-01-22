''' core/process.py
Init and Update Jobs 
'''
import json
import logging
import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.text import slugify

from crm.models import Country
from scerp.locales import APP_CONFIG, APP_MODEL_ORDER, COUNTRY_CHOICES
from scerp.mixins import get_admin, generate_random_password

from .init_permissions import USER_GROUPS, USER_GROUP_TRUSTEE, PERMISSIONS
from .models import App, Message, Tenant, TenantSetup, UserProfile

logger = logging.getLogger(__name__)  # Using the app name for logging
User = get_user_model()


# helpers
def add_logging(data, user):
    '''add mandatory fields
    '''
    data.update({
        'created_by': user
    })
    return data


class GroupAdmin:
    
    def __init__(self, group=None):
        self.group = group
    
    def create(self, name):
        self.group, created = Group.objects.get_or_create(name=name)             
        if created:
            logger.info(
                f"Created `{self.group.name}`."
            )            
        else:
            logger.info(
                f"Allready existing `{self.group.name}`."
            )            
            
    def clean_permissions(self):
        # Clear all existing permissions from the group
        self.group.permissions.clear()
        logger.info(
            f"All permissions removed from group `{self.group.name}`."
        )

    def get_all_permissions(self):
        '''Get all permissions
        e.g. print(
                f"Model: {permission.content_type.model} "
                "Permission: {permission.codename}")
        '''        
        return Permission.objects.all()
        
    def assign_permission(self, permission=None, permission_codename=None):
        '''permission_codename, e.g.
            permission_codename = 'add_user'
        '''
        # Get the permission by its codename
        if not permission:
            permission = Permission.objects.get(codename=permission_codename)

        # Assign the permission to the group
        self.group.permissions.add(permission)

    def assign_permissions(self, permissions=[], cls=None):        
        permissions_all = [p for p in self.get_all_permissions()]                
        if cls and cls.get('exceptions'):            
            # Remove
            for permission in permissions:
                model = ('Model', permission.content_type.model) 
                if model in cls['exceptions']:
                    permissions.remove(permission)                    
                    continue
                
                codename = ('Permission', permission.codename)                
                if codename in cls['exceptions']:
                    permissions.remove(permission)                    
            
        # Assign
        self.clean_permissions()
        for permission in permissions:
            self.group.permissions.add(permission)

        logger.info(
            f"All permissions assigned to group `{self.group.name}`."
        )


class UserAdmin:
    
    def __init__(self, user=None):
        self.user = user
        
    def create(self, **kwargs):
        ''' kwargs must contains username '''
        if not kwargs.get('username'):
            raise ValueError("Username is required and cannot be empty.")
            
        self.password = kwargs.get('password', generate_random_password())
        
        # Create user
        if kwargs.get('is_superuser'):
            self.user = User.objects.create_superuser(**kwargs)
            logger.info(f"Superuser {kwargs['username']} created successfully!")
        else:
            self.user = User.objects.create_user(**kwargs)

        return self.user


class TenantAdmin:
    
    def __init__(self, admin):
        self.admin = admin

    def create(self, name, code, tenant_type=None, users=[]):
        '''Make tenant
        '''
        # Create Tenant, triggers Tenant Setup
        data = {'name': code}
        tenant, created = Tenant.objects.get_or_create(
            code=code,
            defaults=add_logging(data, self.admin)
        )
        if created:
            logger.info(f"Tenant '{code}' created.")
        else:
            logger.warning(f"Tenant '{code}' already exists.")

        # Modify Tenant Setup
        queryset = TenantSetup.objects.filter(tenant=tenant)
        queryset.update(type=tenant_type)
        tenant_setup = queryset.first()

        # Add users
        for user in users:
            add_user(tenant_setup, user)

        # Add profiles
        for user in users:
            obj, created = UserProfile.objects.update_or_create(user=user)
            logger.info(f"User profile '{user.username}' created.")

        return tenant


class AppAdmin:

    def __init__(self, admin):        
        self.admin = admin if admin else get_admin()

    def create_message(self):
        if not Message.objects.all().exists():
            # Prepare
            message = {
                'name': APP_CONFIG['index_title'],
                'text': APP_CONFIG['site_title']
            }

            # Save
            add_logging(message, self.admin)
            Message.objects.create(**message)
            logger.info(f"created {message['name']}")

    def update_apps(self):
        '''Get all apps
        '''        
        # get mandatory
        mandatories = [
            app_name for app_name, def_ in APP_MODEL_ORDER.items()
            if def_['is_mandatory']
        ]
        for app_config in apps.get_app_configs():
            # Init
            data = add_logging(
                {'verbose_name': app_config.verbose_name}, self.admin)
            data['is_mandatory'] = app_config.name in mandatories
            
            # Update or create
            obj, created = App.objects.update_or_create(
                name=app_config.name,
                defaults=data)

        # Register mandatory apps
        for app in App.objects.order_by('name'):
            if app.is_mandatory:
                for tenant in Tenant.objects.all():
                    tenant.apps.add(app)

        logger.info(f"Register apps.")

    def update_countries(self):
        """
        Initializes alpha3_dict by reading country data from JSON files
        for each language defined in settings.LANGUAGES.
        """
        # Initialize the dictionary
        alpha3_dict = {}        
        languages = [lang for lang, _language in settings.LANGUAGES]
        lang_dict = {
            'name': {lang: None for lang in languages},
            'is_default': False,            
            'created_by': self.admin
        }

        # Parse
        for lang in languages:
            # Construct the path to the JSON file for the current language
            path_to_file = os.path.join(
                settings.BASE_DIR, 'crm', 'fixtures', 'countries', lang,
                'countries.json'
            )
            try:
                # Open and read the JSON file
                with open(path_to_file, 'r', encoding='utf-8') as file:
                    countries = json.load(file)  # Load JSON data

                    # Build/update the dictionary using 'alpha3' as the key
                    for country in countries:
                        alpha3 = country['alpha3'].upper()

                        if alpha3 not in alpha3_dict:
                            # New country
                            alpha3_dict[alpha3] = dict(lang_dict)
                            if alpha3 == COUNTRY_DEFAULT:
                                alpha3_dict[alpha3]['is_default'] = True

                        # assign name
                        alpha3_dict[alpha3]['name'][lang] = country['name']

            except FileNotFoundError:
                print(f"File not found for language '{lang}': {path_to_file}")
            except json.JSONDecodeError:
                print(f"""Error decoding JSON for language '{lang}'.
                    Please check the file format.""")
            except Exception as e:
                print(f"An unexpected error occurred for language '{lang}': {e}")

        # Save Db
        # Begin a database transaction for better performance
        with transaction.atomic():
            for alpha3, country in alpha3_dict.items():
                # Use update_or_create to store data
                _obj, _created = Country.objects.update_or_create(
                    code=alpha3,  # Lookup field
                    defaults=country
                )

        # Info
        logger.info(
            f"Countries: '{ len(alpha3_dict) }' records created successfully."
        )

        # Return the final dictionary (optional, if needed elsewhere)
        return alpha3_dict

    def update_documentation(self, app_name=None):
        """Creates a markdown file with sections
        """
        # Load File
        file_path = os.path.join(settings.BASE_DIR, 'core/init_markdown.md')
        with open(file_path, 'r') as file:
            template = file.read()

        if app_name:
            # Define the filename
            names = [app_name]
        else:
            names = []
            for app_name in APP_MODEL_ORDER.keys():
                app_config = apps.get_app_config(app_name)
                names.append(app_config.verbose_name)

        # Create
        for name in names:
            # Prepare the content for the Markdown file
            content = template.format(name=name)
            filename = f'{slugify(name)}.md'

            # Write the content to the markdown file
            filepath = os.path.join(settings.DOCS_SOURCE, filename)
            with open(filepath, 'w') as file:
                file.write(content)

            logger.info(f'Created {filename}.md')

class Core:
    
    def init_first(self):        
        # User
        user = UserAdmin()
        admin = user.create(username='admin', is_superuser=True)

        # App
        app = AppAdmin(admin)
        app.update_apps()
        app.update_documentation()        
        app.update_countries()
        app.create_message()

        # Groups
        group = GroupAdmin()
        self.update_groups()
        
        # Group Trustee
        group = GroupAdmin()
        group.create(USER_GROUP_TRUSTEE)
        group.assign_permissions(cls=PERMISSIONS.TRUSTEE)

        # Tenant
        code = settings.TENANT_CODE
        name = code        
        tenant_type=TenantSetup.TYPE.TRUSTEE
        
        tenant = TenantAdmin(admin)
        tenant_obj = tenant.create(name, code, tenant_type=tenant_type)
        
        # Tenant Setup User
        tenant_setup = TenantSetup.objects.filter(tenant=tenant_obj).first()
        tenant_setup.users.add(admin)

    def update_groups(self):
        for group in USER_GROUPS:
            group_obj = GroupAdmin()
            group_obj.create(group['name'])
            group_obj.assign_permissions(group['permissions'])
