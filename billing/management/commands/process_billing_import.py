# process_billing_import.py
'''usage:
    python manage.py process_billing_import load_counters --city=gunzgen --filename=Zähler-Bestandesliste.xls
'''
import json
from django.core.management.base import BaseCommand
from django.core.management import CommandError

import billing.import_data as import_data
from billing.gesoft_counter_data_import import Address, Product, Counter

PATH = 'billing/fixtures/'

class Command(BaseCommand):
    help = 'Process accounting'

    def add_arguments(self, parser):
        # Positional argument
        parser.add_argument(
            'action', type=str, choices=[
                'load_counters', 'load_subscriptions'], 
            help='Specify the action: create or load_counters'
        )
        
        # Optional arguments with flags
        parser.add_argument(
            '--city', type=str, required=True, 
            help='Specify the city'
        )
        parser.add_argument(
            '--filename', type=str, required=True,
            help=f'Filename within {PATH}'
        )

    def handle(self, *args, **options):
        action = options['action']
        city_cls = getattr(import_data, options['city'].title())

        if action == 'load_counters':
            imp = city_cls(f"{PATH}{options['filename']}")
            count = imp.load_counters()
            print(f"*{count} records loaded")

        if action == 'load_subscriptions':
            imp = city_cls(f"{PATH}{options['filename']}")
            count = imp.load_subscriptions()
            print(f"*{count} records loaded")
