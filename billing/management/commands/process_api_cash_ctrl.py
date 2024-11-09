# process_api_cash_ctrl.py
'''usage:
    python manage.py process_api_cash_ctrl cmd
'''
import json
from django.core.management.base import BaseCommand
from django.core.management import CommandError

from accounting.process import Account, TYPE
# from accounting.api_cash_ctrl import Core


class Command(BaseCommand):
    help = 'Process accounting'

    def add_arguments(self, parser):
        parser.add_argument('action', type=str, help='Specify the action: create')

    def handle(self, *args, **options):
        action = options['action']
        if action == 'load_accounts':
            function = 8200
        
            # file_path = "./accounting/fixtures/kontenpläne/Kontenplan_SO_Bürgergemeinden_Funktionale Gliederung.xlsx"
            # a = Account(file_path, TYPE.FUNCTIONAL)        
        
            # file_path = "./accounting/fixtures/kontenpläne/Kontenplan_SO_Bürgergemeinden_Bilanz.xlsx"
            # a = Account(file_path, TYPE.BALANCE)
 
            # file_path = "./accounting/fixtures/kontenpläne/Kontenplan_SO_Bürgergemeinden_Erfolgsrechnung.xlsx"
            # a = Account(file_path, TYPE.INCOME, function)
 
            file_path = "./accounting/fixtures/kontenpläne/Kontenplan_SO_Bürgergemeinden_Investitionsrechnung.xlsx"
            a = Account(file_path, TYPE.INCOME, function)

            accounts = a.load_accounts()
            if accounts:
                with open("accounts.json", "w") as json_file:
                    json.dump(accounts, json_file, indent=4)
                print(f"*successfully loaded {len(accounts)} accounts")
            else:
                print(f"*completed with errors")            
