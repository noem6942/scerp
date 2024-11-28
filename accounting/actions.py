# accounting/actions.py
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from core.models import Tenant
from core.safeguards import save_logging, get_tenant
from scerp.actions import action_check_nr_selected

from .api_cash_ctrl import (
    CustomFieldGroup, CustomField, SequenceNumber, Tax,
    AccountCategory)    
from .forms import (
    AccountChartCantonForm, 
    AccountChartMunicipalityBalanceForm, 
    AccountChartMunicipalityFunctionForm,
    AccountPositionMunicipalityAddIncomeForm,
    AccountPositionMunicipalityAddInvestForm
)
from .models import (
    CHART_TYPE, DISPLAY_TYPE, FiscalPeriod,
    ChartOfAccountsCanton, AccountPositionCanton,
    AccountChartMunicipality, AccountPositionMunicipality
)
from .process_chart_of_accounts import Account

import json


DONOT_COPY_FIELDS = [
    # General
    'pk', 'id', 'created_at', 'created_by_id', 'modified_at', 'modified_by_id',
    'version_id', 'protected', 'inactive',
    
    # Accounting
    'chart', 'display_type', 'function',
    
    # CashCtrl
    'c_id', 'c_created', 'c_created_by', 'c_last_updated', 'c_last_updated_by'
]


# api
@admin.action(description=_('1. Init Cash API'))
def api_init(modeladmin, request, queryset):
    # Check number selected
    if action_check_nr_selected(request, queryset, 1):
        tenant = queryset.first()
    else:
        return False

    # Check API
    if not tenant.api_key:
        messages.error(request, _('api key missing'))
    '''
    # First test
    a = CustomFieldGroup(tenant.org_name, tenant.api_key)
    data = a.list()
    print("*data", len(data))

    with open("data_cash_ctrl.json", "w") as json_file:
        json.dump(data, json_file, indent=4)

    '''
    a = AccountCategory(tenant.org_name, tenant.api_key)
    filter = json.dumps([{"field": "parentId", "value": "53", "comparison": "eq"}])
    data = a.list(filter=filter)
    with open("data_cash_ctrl.json", "w") as json_file:
        json.dump(data, json_file, indent=4)
    '''
    prime_categories = {
        x['accountClass']: x['id']
        for x in data if not x['parentId']
    }
    '''

    messages.success(request, "good")


# mixins
@admin.action(description=_('2. Insert copy of record below'))
def position_insert(self, request, queryset):
    ''' Insert row of a model that has a field position '''
    # Check
    if action_check_nr_selected(request, queryset, 1):
        obj = queryset.first()    
    else:
        return

    # Create a copy of the instance with a new position
    obj.pk = None  # Clear the primary key for duplication
    obj.name += ' <copy>'
    try:
        if obj.account_number:
            obj.account_number = str(int(obj.account_number) + 1)
        elif obj.account_4_plus_2:
            obj.account_4_plus_2 = str(float(obj.account_4_plus_2) + 0.01)
        obj.save()
        messages.success(request, _('Copied record.'))
    except:
        messages.warning(request, _('Not allowed to copy this record.'))
        return
        
        
# FiscalPeriod        
@admin.action(description=_('3. Set selected period as current'))
def fiscal_period_set_current(self, request, queryset):
    ''' Insert row of a model that has a field position '''
    # Check
    if action_check_nr_selected(request, queryset, 1):
        obj = queryset.first()    
    else:
        return

    # Deselect all objects, make sure only `is_current=False` on others
    FiscalPeriod.objects.all().update(is_current=False)

    # Set selected object as the current one
    obj.is_current = True
    obj.save()
    
    msg = _('Set {obj.name} as current.').format(obj=obj)
    messages.success(request, msg)   
        

# ChartOfAccountsCanton (coac)
def coac_positions(modeladmin, request, queryset, overwrite):
    """Check Excel File of ChartOfAccountsCanton"""
    for chart in queryset:
        # Load excel
        try:
            a = Account(chart.excel.path, chart.type, None)
            accounts = a.get_accounts()
        except ValueError as e:
            # Catching the specific ValueError
            messages.error(request, f'{_("Error Message:")} {str(e)}')
            return

        # Set tenant
        add_tenant = False

        # Delete existing
        check_only = True if not overwrite else False
        if overwrite:
            AccountPositionCanton.objects.filter(
                chart_of_accounts=chart).delete()
            chart.exported_at = None
            chart.save() 

        # Create Positions
        try:
            with transaction.atomic():
                for account in accounts:
                    # Save base
                    account_instance = AccountPositionCanton(chart_of_accounts=chart)
                    for key, value in account.items():
                        setattr(account_instance, key, value)

                    # Add Logging
                    save_logging(request, account_instance, add_tenant)
                    
                    # Try to save (here the validity checks get performed
                    account_instance.save(check_only=check_only)

            # Message
            msg = _("successfully checked {count} accounts.").format(
                count=len(accounts))
            messages.success(request, msg)    

            # Log
            if overwrite:
                chart.exported_at = timezone.now()
                chart.save()

        except Exception as e:
            # If any error occurs, the transaction is rolled back
            # Display an error message in the admin
            messages.error(request, f'{_("Error Message:")} {str(e)}')
            return

        
@admin.action(description=_('4. Check Excel file for validity'))
def coac_positions_check(modeladmin, request, queryset):
    coac_positions(modeladmin, request, queryset, overwrite=False)


@action_with_form(
    AccountChartCantonForm,
    description=_('5. Create canton account positions')
)
def coac_positions_create(modeladmin, request, queryset, data):
    """Check Excel File of ChartOfAccountsCanton"""
    # Check number selected
    if action_check_nr_selected(request, queryset, 1):
        chart = queryset.first()
    else:
        return False

    # Load excel
    coac_positions(modeladmin, request, queryset, overwrite=True)

 
# AccountPositionCanton (apc)
def apc_export(request, queryset, type_from, display_type, chart_id):
    '''two cases:
    1. Copy bilance to bilance:
        add chart
        function = None
        copy account_number and account_4_plus_2
        copy display_type
    2. Copy function to income:
        add chart 
        function gets account_number (if existing), otherwise account
        display_type gets income   
    '''

    # Init
    chart = AccountChartMunicipality.objects.get(id=chart_id)
    count_created = 0
    count_updated = 0
    
    # Copy
    for obj in queryset.all():
        # Adjust function and accounting numbers
        if type_from == CHART_TYPE.FUNCTIONAL:
            # Function
            if obj.account_number:
                function = obj.account_number
            else:
                function = obj.account
                
            # Accounting numbers
            obj.account_number = ''
            obj.account_4_plus_2 = ''               
               
        else:
            function = None 
    
        # Check existing        
        account_instance = AccountPositionMunicipality.objects.filter(
            chart=chart, 
            function=function,
            account_number=obj.account_number, 
            account_4_plus_2=obj.account_4_plus_2,
            display_type=display_type
        ).first()
        
        # Create new
        if account_instance:
            count_updated += 1
        else:
            count_created += 1
            account_instance = AccountPositionMunicipality()
            account_instance.chart = chart 
            account_instance.function = function  
            account_instance.display_type = display_type  

        # Copy values
        for key, value in obj.__dict__.items():
            if key not in DONOT_COPY_FIELDS and key[0] != '_':                
                setattr(account_instance, key, value)

        # As we create an AbstractTenant instance from a non tenant obj we
        # do the update of tenant and logging ourselves instead of using
        # save_logging
        save_logging(request, account_instance, add_tenant=True)
        account_instance.save()

    # Message
    if count_created:
        msg = _("successfully created {count} accounts. ").format(
            count=count_created)
        messages.success(request, msg)
    if count_updated:
        msg = _("successfully updated {count} accounts. ").format(
            count=count_updated)
        messages.success(request, msg)
    if count_created or count_updated:
        msg = _("Go to '{verbose}' to see the results.").format(
            verbose=ACCOUNT_POSITION_MUNICIPALITY.verbose_name)
        messages.success(request, msg)   


@action_with_form(
    AccountChartMunicipalityBalanceForm,
    description=_('7. Export selected balance positions to municipality balance'))
def apc_export_balance(modeladmin, request, queryset, data):
    # type checks are done in the form
    chart_id = data.get('chart')
    if chart_id:        
        apc_export(
            request, queryset, CHART_TYPE.BALANCE, DISPLAY_TYPE.BALANCE, 
            chart_id)

@action_with_form(
    AccountChartMunicipalityFunctionForm,
    description=_('8. Export selected function positions to municipality income'))
def apc_export_function_to_income(modeladmin, request, queryset, data):
    # type checks are done in the form
    chart_id = data.get('chart')
    if chart_id:
        apc_export(
            request, queryset, CHART_TYPE.FUNCTIONAL, DISPLAY_TYPE.INCOME, 
            chart_id)

@action_with_form(
    AccountChartMunicipalityFunctionForm,
    description=_('Export selected function positions to municipality invest'))
def apc_export_function_to_invest(modeladmin, request, queryset, data):
    # type checks are done in the form
    chart_id = data.get('chart')
    if chart_id:        
        apc_export(
            request, queryset, CHART_TYPE.FUNCTIONAL, DISPLAY_TYPE.INVEST, 
            chart_id)


# AccountPositionMunicipality (apm)
def apm_add(modeladmin, request, queryset, data, display_type):
    # Check number selected
    if queryset.count() > 1:
         messages.warning(request, MESSAGE.multiple_functions)
    
    # Init
    chart = queryset.first().chart
    count_created = 0
    count_updated = 0

    # Get positions
    positions = data.get('positions')
    if not positions:
        return

    # Assign
    for function_obj in queryset.all():
        # Copy objects
        for obj in positions:
            # Check if existing
            function = function_obj.function
            account_instance = AccountPositionMunicipality.objects.filter(
                chart=chart, 
                account_number=obj.account_number,
                account_4_plus_2=obj.account_4_plus_2,
                function=function,
                display_type=display_type).first()
                
            # Create new 
            if account_instance:
                count_updated += 1
            else:
                # We create a new instance
                count_created += 1
                account_instance = AccountPositionMunicipality()                            
                account_instance.chart = chart
                account_instance.display_type = display_type
                account_instance.function = function

            # Copy values
            for key, value in obj.__dict__.items():
                if key not in DONOT_COPY_FIELDS and key[0] != '_':
                    setattr(account_instance, key, value)        

            # Save
            save_logging(request, account_instance, add_tenant=True)
            account_instance.save()    
    
    # Message
    if count_created:
        msg = _("successfully created {count} accounts. ").format(
            count=count_created)
        messages.success(request, msg)
    if count_updated:
        msg = _("successfully updated {count} accounts. ").format(
            count=count_updated)
        messages.success(request, msg)


@action_with_form(
    AccountPositionMunicipalityAddIncomeForm,
    description=_('10. Add income positions to function')
)
def apm_add_income(modeladmin, request, queryset, data):
    apm_add(modeladmin, request, queryset, data, DISPLAY_TYPE.INCOME)


@action_with_form(
    AccountPositionMunicipalityAddInvestForm,
    description=_('11 Add invest positions to function')
)
def apm_add_invest(modeladmin, request, queryset, data):
    apm_add(modeladmin, request, queryset, data, DISPLAY_TYPE.INVEST)
