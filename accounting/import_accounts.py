# import_accounts.py
from .models import AccountPosition, ChartOfAccounts, FiscalPeriod
from core.models import Tenant
from scerp.mixins import get_admin


def save_accounts(accounts, tenant_code, chart_id, fiscal_period_name=None):        
    # Init
    admin = get_admin()
    chart = ChartOfAccounts.objects.get(id=chart_id)
    tenant = Tenant.objects.get(code=tenant_code)
    
    # FiscalPeriod
    if fiscal_period_name:
        period = FiscalPeriod.objects.get(
            tenant=tenant, name=fiscal_period_name)
    else:
        period = FiscalPeriod.objects.get(
            tenant=tenant, is_current=True)
        
    for account in accounts:
        # add mandatory fields
        account.update({
            'tenant': tenant,
            'created_by': admin,
            'modified_by': admin
        })
        
        # Delete existings
        AccountPosition.objects.filter(
            tenant=tenant,
            chart=chart,
            function=account['function'],
            account_number=account['account_number'],
            account_type=account['account_type'],
            is_category=account['is_category']
        ).delete()
        
        # Save
        account_position = AccountPosition(chart=chart, **account)        
        try:
            account_position.save()
            account_position.periods.add(period)
        except Exception as e:
            # Print the error to the console
            print(f"Record: {account}")
            print(f"Error occurred while saving account_position: {e}")
            break
