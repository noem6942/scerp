# process_billing.py
'''usage:
    python manage.py process_billing cmd
    e.g python manage.py process_billing gesoft --setup_id=12 --route_id=1 --date=2024-09-30
'''
import json
from django.core.management.base import BaseCommand
from django.core.management import CommandError


class Command(BaseCommand):
    help = 'Process accounting'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',  # Positional argument
            choices=['gesoft', 'gesoft_area'],  # Restrict valid values
            help='Specify the action: gesoft'
        )
        parser.add_argument(
            '--setup_id',  # Optional argument (use '--')
            type=int,
            required=False,
            help='Setup ID for the operation'
        )
        parser.add_argument(
            '--route_id',
            type=int,
            required=False,
            help='Route ID for the operation'
        )
        parser.add_argument(
            '--date',
            type=str,
            required=False,
            help='Date default for counter data'
        )

    def handle(self, *args, **options):
        action = options['action']
        setup_id = options.get('setup_id')
        route_id = options.get('route_id')
        date = options.get('date')

        if action == 'gesoft':
            # Import library
            from billing.gesoft_import import ImportAddress, ImportData

            # Load addresses
            file_name = 'Abonnenten Gebühren einzeilig.xlsx'
            handler = ImportAddress(setup_id)
            address_data = handler.load(file_name)

            # Load subscribers + counters
            file_name = 'Abonnenten mit Zähler und Gebühren.xlsx'
            handler = ImportData(setup_id, route_id, date)
            handler.load(file_name, address_data)

        elif action == 'gesoft_area':
            # Import library
            from billing.gesoft_import import AreaAssignment

            # Load subscribers + counters
            handler = AreaAssignment(setup_id)
            handler.assign()
            
        else:
            raise ValueError("No valid action")
