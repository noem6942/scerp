# accounting/init_accounting.py
'''usage:
    python manage.py process_api_cash_ctrl cmd
'''
from django.core.management.base import BaseCommand
from 

class Command(BaseCommand):
    help = 'Init accounting'

    def add_arguments(self, parser):
        # Required positional argument
        parser.add_argument('action', type=str, help='Specify the action: create')
        
        # Optional arguments
        parser.add_argument('--code', type=str, help='Optional code parameter')
        parser.add_argument('--name', type=str, help='Optional name parameter')
        parser.add_argument('--key', type=str, help='Optional key parameter')

    def handle(self, *args, **options):
        # Retrieve options
        action = options['action']
        code = options.get('code')
        name = options.get('name')
        key = options.get('key')

        # Perform actions based on the retrieved options
        self.stdout.write(self.style.SUCCESS(f'Action: {action}'))
        if code:
            self.stdout.write(self.style.SUCCESS(f'Code: {code}'))
        if name:
            self.stdout.write(self.style.SUCCESS(f'Name: {name}'))
        if key:
            self.stdout.write(self.style.SUCCESS(f'Key: {key}'))

        # Your core logic here
