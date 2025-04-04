# process_billing.py
'''usage:
    python manage.py process_billing gesoft --tenant_id=12 --route_id=1 --date=2024-09-30
    python manage.py process_billing gesoft_area --tenant_id=12
    python manage.py process_billing gesoft_archive --tenant_id=12
'''
import json
from django.core.management.base import BaseCommand
from django.core.management import CommandError


class Command(BaseCommand):
    help = 'Process accounting'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',  # Positional argument
            choices=['gesoft', 'gesoft_area', 'gesoft_archive'],
            help='Specify the action: gesoft'
        )
        parser.add_argument(
            '--tenant_id',  # Optional argument (use '--')
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
        tenant_id = options.get('tenant_id')
        route_id = options.get('route_id')
        date = options.get('date')

        if action == 'gesoft':
            # Import library
            from billing.gesoft_import import ImportAddress, ImportData

            # Load addresses
            file_name = 'Abonnenten Gebühren einzeilig.xlsx'
            handler = ImportAddress(tenant_id)
            address_data = handler.load(file_name)

            # Load subscribers + counters
            file_name = 'Abonnenten mit Zähler und Gebühren.xlsx'
            handler = ImportData(tenant_id, route_id, date)
            handler.load(file_name, address_data)

        elif action == 'gesoft_area':
            # Import library
            from billing.gesoft_import import AreaAssignment

            # Load subscribers + counters
            handler = AreaAssignment(tenant_id)
            handler.assign()

        elif action == 'gesoft_archive':
            # Import library
            from billing.gesoft_import import ImportArchive

            # Load subscribers + counters
            file_name = 'Abonnenten Archiv Gebühren einzeilig.xlsx'
            handler = ImportArchive(tenant_id)
            handler.load(file_name)

        else:
            raise ValueError("No valid action")
