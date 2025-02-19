'''
accounting/management/commands/process_accounting.py

usage:
   python manage.py process_accounting sync --org_name=test167 --ledger_id=1 --category=ic --max_count=100

'''
from django.core.management.base import BaseCommand

from accounting.import_export import SyncLedger


class Command(BaseCommand):
    help = 'Init accounting'

    def add_arguments(self, parser):
        # Required positional argument
        parser.add_argument(
            'action', type=str, 
            choices=['sync'],
            help='Sync ledger')
        
        # Optional arguments
        parser.add_argument(
            '--category', type=str, 
            choices=['balance', 'pl', 'ic'],
            help='Optional code, ')        
        parser.add_argument(
            '--org_name', type=str, help='org_name')
        parser.add_argument(
            '--ledger_id', type=int, help='ledger_id')        
        parser.add_argument(
            '--max_count', type=int, help='max number of records (< 100)')     
            
    def handle(self, *args, **options):
        # Retrieve action
        action = options['action']

        # Perform actions based on the retrieved options
        if action == 'sync':
            sync = SyncLedger(options.get('category'))
            org_name = options.get('org_name')
            ledger_id = options.get('ledger_id')
            max_count = options.get('max_count', 100)
            sync.load(org_name, ledger_id, max_count)
