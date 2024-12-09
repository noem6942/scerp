# core/management/commands/process_core.py
'''usage:
    python manage.py process_core
'''
from django.core.management.base import BaseCommand
from django.core.management import CommandError

from core.process import UserGroup, Documentation


class Command(BaseCommand):
    help = 'Create or update user groups, or create a markdown file with specific details'

    def add_arguments(self, parser):
        # Add options for different actions
        parser.add_argument(
            'action', type=str, help='Specify the action: update-or-create-groups or create-markdown'
        )
        parser.add_argument(
            '--name', type=str, help='The name of the item for Markdown creation (required for create-markdown action)'
        )

    def handle(self, *args, **options):
        action = options['action']

        # Handling the action of creating/updating user groups
        if action == 'update-or-create-groups':
            confirmation = input(
                f'Are you sure you want to delete existing permissions and '
                f'set new user_groups? (y/N)'
            )
            if confirmation.lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation canceled.'))
                return
            
            g = UserGroup()
            if g.update_or_create():
                self.stdout.write(self.style.SUCCESS(
                    'User group setup complete.'))
            else:
                self.stdout.write(self.style.ERROR(
                    'Invalid action specified. Use "create".'))

        # Handling the action of creating a markdown file
        elif action == 'create-markdown':
            # Ensure the 'name' argument is provided for Markdown file creation
            name = options.get('name')
            d = Documentation(name)
            
            if not name:
                self.stdout.write(self.style.ERROR(
                    'The --name argument is required for create-markdown action.'))
                return
            
            # Create the markdown file
            d.create_markdown()
            self.stdout.write(self.style.SUCCESS(
                f'Markdown file for {name} created successfully.'))

        else:
            raise CommandError('Invalid action. Use "update-or-create-groups" or "create-markdown".')
