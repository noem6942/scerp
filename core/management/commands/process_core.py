# core/management/commands/process_core.py
'''usage:
    python manage.py process_core core__init_first
'''
from django.core.management.base import BaseCommand
from django.core.management import CommandError

from core.process import AppAdmin, GroupAdmin, Core

class Command(BaseCommand):
    help = 'Create or update user groups, or create a markdown file with specific details'

    # Define an array of possible values for the action
    ACTION_CHOICES = {
        'test': None,
        'core__init_first': 'Core (first usage): add admin, setup tenant',
        'core__update_apps': 'Update Apps',
        'core__update_countries': 'Update country names',
        'core__update_documentation': 'Update apps for documentation',
        'core__update_groups': 'Update or create user groups',
        'update_group_trustee': 'Update or create trustee group',
    }

    def add_arguments(self, parser):
        # Add options for different actions
        parser.add_argument(
            'action', type=str,
            choices=self.ACTION_CHOICES.keys(),
            help=f'Specify the action: {self.ACTION_CHOICES}'
        )
        parser.add_argument(
            '--name', type=str, help='The name of the item for Markdown creation (required for create-markdown action)'
        )

    def handle(self, *args, **options):
        action = options['action']

        # Core
        if action == 'test':
            return

        if action == 'core__init_first':
            c = Core()
            c.init_first()
        elif action == 'core__update_apps':
            c = AppAdmin()
            c.update_apps()
        elif action == 'core__update_countries':
            c = AppAdmin()
            c.update_countries()
        elif action == 'core__update_documentation':
            name = options.get('name')
            c = AppAdmin()
            c.update_documentation(name)
        elif action == 'core__update_groups':
            c = Core()
            c.update_groups()
        elif action == 'update_group_trustee':
            c = Core()
            c.update_group_trustee()
