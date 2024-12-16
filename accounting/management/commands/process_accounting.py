# accounting/process_accounting.py
'''usage:
    python manage.py process_accounting cmd
    
    gesoft:
        python manage.py process_accounting import --import=gesoft --tenant_code=test167 --org_name=test167 --chart_id=1 --filepath="./accounting/fixtures/transfer ge_soft/Bilanz 2023 AGEM.xlsx" --account_type 1
        python manage.py process_accounting import --import=gesoft --tenant_code=test167 --org_name=test167 --chart_id=1 --filepath="./accounting/fixtures/transfer ge_soft/Erfolgsrechnung 2023 AGEM.xlsx" --account_type 3
        python manage.py process_accounting import --import=gesoft --tenant_code=test167 --org_name=test167 --chart_id=1 --filepath="./accounting/fixtures/transfer ge_soft/IR-F JR Detail  (Q) SO_BE HRM2 DLIHB.SO.IR15.xlsx" --account_type 5
'''
from django.core.management.base import BaseCommand
from accounting.import_accounts import save_accounts
from accounting.import_accounts_gesoft import (
    ACCOUNT_TYPE, ACCOUNT_SIDE, Import)


class Command(BaseCommand):
    help = 'Init accounting'

    def add_arguments(self, parser):
        # Required positional argument
        parser.add_argument(
            'action', type=str, 
            choices=['import'],
            help='Specify the action: create')
        
        # Optional arguments
        parser.add_argument(
            '--import', type=str, 
            choices=['gesoft'],
            help='Optional code, ')        
        parser.add_argument(
            '--tenant_code', type=str, help='Optional code tenant')
        parser.add_argument(
            '--org_name', type=str, help='Optional org_name')
        parser.add_argument(
            '--chart_id', type=int, help='Chart id')
        parser.add_argument(
            '--filepath', type=str, 
            help='file, e.g. ./accounting/fixtures/transfer ge_soft/Bilanz 2023 AGEM.xlsx')
        choices = [f'{x.value}: {x.label}' for x in ACCOUNT_TYPE]
        parser.add_argument(
            '--account_type', type=int, 
            choices=[x.value for x in ACCOUNT_TYPE],
            help=f'file, e.g. {choices}')

    def handle(self, *args, **options):
        # Retrieve options
        action = options['action']
        import_ = options.get('import')
        tenant_code = options.get('tenant_code')
        org_name = options.get('org_name')
        chart_id = options.get('chart_id')
        file_path = options.get('filepath')
        account_type = options.get('account_type')

        # Perform actions based on the retrieved options
        if action == 'import':
            # Init
            accounts = []
            
            if import_ == 'gesoft':
                if account_type == ACCOUNT_TYPE.BALANCE:
                    i = Import(file_path, account_type)
                    accounts = i.get_accounts()
                    save_accounts(accounts, tenant_code, org_name, chart_id)
                elif account_type == ACCOUNT_TYPE.INCOME:
                    i = Import(file_path, account_type, ACCOUNT_SIDE.INCOME)
                    accounts = i.get_accounts()
                    i = Import(file_path, account_type, ACCOUNT_SIDE.EXPENSE)
                    accounts += i.get_accounts()
                    i = Import(file_path, account_type, ACCOUNT_SIDE.CLOSING)
                    accounts += i.get_accounts()
                    save_accounts(accounts, tenant_code, org_name, chart_id)
                elif account_type == ACCOUNT_TYPE.INVEST:
                    i = Import(file_path, account_type, ACCOUNT_SIDE.INCOME)
                    accounts = i.get_accounts()
                    i = Import(file_path, account_type, ACCOUNT_SIDE.EXPENSE)
                    accounts += i.get_accounts()
                    save_accounts(accounts, tenant_code, org_name, chart_id)
                    
            # Output        
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created {len(accounts)} accounts.'))
