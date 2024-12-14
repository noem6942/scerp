# core/management/commands/process_core.py
'''usage:
    python manage.py process_core update-or-create-apps
    python manage.py process_core update-or-create-groups
    python manage.py process_core create-markdown
'''
from django.core.management.base import BaseCommand
from django.core.management import CommandError

from core.process import AppSetup, UserGroupSetup, DocumentationSetup


class Command(BaseCommand):
    help = 'Create or update user groups, or create a markdown file with specific details'

    # Define an array of possible values for the action
    ACTION_CHOICES = {
        'update-or-create-apps': 'Update or create apps',
        'update-or-create-groups': 'Update or create user groups',
        'create-markdown': 'Create markdown file',
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

        # Handling the action of creating/updating apps
        if action == 'update-or-create-apps':
            a = AppSetup()
            a.update_or_create()
            self.stdout.write(self.style.SUCCESS('Apps setup complete.'))
        
        elif action == 'update-or-create-groups':
            confirmation = input(
                f'Are you sure you want to delete existing permissions and '
                f'set new user_groups? (y/N)'
            )
            if confirmation.lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation canceled.'))
                return
            
            g = UserGroupSetup()
            if g.update_or_create():
                self.stdout.write(self.style.SUCCESS(
                    'User group setup complete.'))
            else:
                self.stdout.write(self.style.ERROR(
                    'Invalid action specified. Use "create".'))

        # Handling the action of creating a markdown file
        elif action == 'create-markdown':            
            name = options.get('name')
            d = DocumentationSetup(name)            
            d.create_markdown()
            self.stdout.write(self.style.SUCCESS(
                f'Markdown file for {name} created successfully.'))

        else:
            raise CommandError('Invalid action. Use "update-or-create-groups" or "create-markdown".')
