'''
process_asset.py

usage:
    python manage.py process_billing cmd
    e.g python manage.py process_asset gesoft --tenant_id=3

'''
from django.core.management.base import BaseCommand
from django.core.management import CommandError


class Command(BaseCommand):
    help = 'Process asset'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',  # Positional argument
            choices=['gesoft'],  # Restrict valid values
            help='Specify the action: gesoft'
        )
        parser.add_argument(
            '--tenant_id',  # Optional argument (use '--')
            type=int,
            required=False, 
            help='Setup ID for the operation'
        )

    def handle(self, *args, **options):
        action = options['action']
        tenant_id = options.get('tenant_id')
        
        if action == 'gesoft':
            # Import library
            from asset.gesoft_import import ImportDevice
                        
            # Loadcounters
            file_name = 'Zähler-Bestandesliste.xlsx'
            handler = ImportDevice(tenant_id)                        
            handler.load(file_name)
        else:
            raise ValueError("No valid action")
