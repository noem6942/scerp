# import_accounts.py
from scerp.mixins import get_admin
from .models import APISetup, AccountPosition, ChartOfAccounts


def save_accounts(accounts, tenant__code, org_name, chart_id):        
    # Init
    admin = get_admin()
    chart = ChartOfAccounts.objects.get(
        tenant__code=tenant__code, id=chart_id)
    
    tenant_setup = APISetup.objects.filter(
        org_name=org_name,
        tenant__code=tenant__code
    ).first()
    if tenant_setup:
        tenant = tenant_setup.tenant
    else:
        raise ValueError(f"No API Setup found for org_name: {org_name}")
        
    for account in accounts:
        # add mandatory fields
        account.update({
            'tenant': tenant,
            'setup': tenant_setup,
            'created_by': admin,
            'modified_by': admin
        })
        
        # Delete existing record (usually only one)
        AccountPosition.objects.filter(
            setup=tenant_setup,
            chart=chart,
            function=account['function'],
            account_number=account['account_number'],
            account_type=account['account_type'],
            is_category=account['is_category']
        ).delete()
        
        # Save
        account_position = AccountPosition(chart=chart, **account)      
        account_position.save()        
        '''
        try:
            
        except Exception as e:
            # Print the error to the console
            print(f"Record: {account}")
            print(f"Error occurred while saving account_position: {e}")
            break
        '''