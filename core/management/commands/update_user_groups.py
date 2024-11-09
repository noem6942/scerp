# core/management/commands/udpate_user_groups.py
'''usage:
    python manage.py udpate_user_groups update-or-create
'''
from django.core.management.base import BaseCommand
from django.core.management import CommandError

from core.run_user_groups import UserGroup


class Command(BaseCommand):
    help = 'Create a user group with specific permissions'

    def add_arguments(self, parser):
        parser.add_argument('action', type=str, help='Specify the action: create')

    def handle(self, *args, **options):
        action = options['action']

        if action == 'update-or-create':
            # Confirm action before proceeding
            confirmation = input(
                f'Are you sure you want to delete existing permissions and '
                f'set new user_groups? (y/N)')
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
