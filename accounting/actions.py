# accounting/actions.py
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

import json

from core.models import Tenant
from core.safeguards import save_logging, get_tenant
from scerp.actions import action_check_nr_selected
from scerp.admin import get_help_text

from .api_cash_ctrl import API, FIELD_TYPE, CashCtrl
from .forms import (
    ChartOfAccountsTemplateForm, 
    ChartOfAccountsBalanceForm, 
    ChartOfAccountsFunctionForm,
    AccountPositionAddIncomeForm,
    AccountPositionAddInvestForm
)
from .models import (
    APISetup, ACCOUNT_TYPE_TEMPLATE, FiscalPeriod,
    ChartOfAccountsTemplate, AccountPositionTemplate,
    ChartOfAccounts, AccountPosition
)
from .import_accounts_canton import Import

import json


DONOT_COPY_FIELDS = [
    # General
    'pk', 'id', 'created_at', 'created_by_id', 'modified_at', 'modified_by_id',
    'version_id', 'protected', 'inactive',
    
    # Accounting
    'chart', 'chart_id', 'account_type', 'function',
    
    # CashCtrl
    'c_id', 'c_created', 'c_created_by', 'c_last_updated', 'c_last_updated_by'
]


# mixins
@admin.action(description=_('A1. Init Account Setup'))
def api_setup_init(self, request, queryset):
    ''' Init API Settings in cashCtrl '''
    # Check
    if action_check_nr_selected(request, queryset, 1):
        account = queryset.first()    
    else:
        return
    
    # Init
    ctrl = CashCtrl(account.org_name, account.api_key)
    
    # Create Custom Groups
    model = APISetup
    for field in account.__dict__.keys():
        if field.startswith('custom_field_group_'):
            # Get elems    
            data = json.loads(get_help_text(model, field))
            name = data['name'] 
            type_ = data['type'] 
            
            group = ctrl.get_customfield_group(name, type_)
            if group:
                msg = _('Group {name} of type {type} already existing.').format(
                    name=name, type=type_)
                messages.warning(request, msg)              
            else:
                # Create group
                group = ctrl.create_customfield_group(name, type_)
                
                # Register group
                setattr(account, field, group['insert_id'])
                account.save()
            
                # Msg
                msg = _('Created group {name} of type {type}.').format(
                    name=name, type=type_)
                messages.success(request, msg)  
            
            

    # Create Custom Fields, currently only for simple types with no defaults
    model = APISetup
    for field in account.__dict__.keys():
        if (not field.startswith('custom_field_group_')
                and field.startswith('custom_field_')):
            # Get elems    
            data = json.loads(get_help_text(model, field))     
            data['group'] = json.loads(data['group'])
                        
            # Get customfield    
            customfield = ctrl.get_customfield(
                data['name'], data['group']['type'])

            if customfield:
                msg = _('Customfield {name} of type {type} in '
                        '{group_name} already existing.')
                msg = msg.format(
                    name=data['name'], type=data['group']['type'], 
                    group_name=data['group']['name'])
                messages.warning(request, msg)                
            else: 
                # Create field
                customfield = ctrl.create_customfield(**data)
                
                # Register field
                setattr(account, field, customfield['insert_id'])
                account.save()
            
                # Msg
                msg = _('Created customfield {name} of type {type} in '
                        '{group_name}.')
                msg = msg.format(
                    name=data['name'], type=data['group']['type'], 
                    group_name=data['group']['name'])
                messages.success(request, msg)              


@admin.action(description=_('> Insert copy of record below'))
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
        if obj.is_category:
            obj.account_number = str(int(obj.account_number) + 1)
        else:
            obj.account_number = str(float(obj.account_number) + 0.01)
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
        

# ChartOfAccountsTemplate (coac)
def coac_positions(modeladmin, request, queryset, overwrite):
    """Check Excel File of ChartOfAccountsTemplate"""
    for chart in queryset:
        # Load excel
        try:
            a = Import(chart.excel.path, chart.account_type, None)
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
            AccountPositionTemplate.objects.filter(chart=chart).delete()
            chart.exported_at = None
            chart.save() 

        # Create Positions
        try:
            with transaction.atomic():
                for account in accounts:
                    # Save base
                    account_instance = AccountPositionTemplate(chart=chart)
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

        
@admin.action(description=_('> Check Excel file for validity'))
def coac_positions_check(modeladmin, request, queryset):
    coac_positions(modeladmin, request, queryset, overwrite=False)


@action_with_form(
    ChartOfAccountsTemplateForm,
    description=_('> Create canton account positions'))
def coac_positions_create(modeladmin, request, queryset, data):
    """Check Excel File of ChartOfAccountsTemplate"""
    # Check number selected
    if action_check_nr_selected(request, queryset, 1):
        chart = queryset.first()
    else:
        return False

    # Load excel
    coac_positions(modeladmin, request, queryset, overwrite=True)

 
# AccountPositionCanton (apc)
def apc_export(request, queryset, type_from, account_type, chart_id):
    '''two cases:
    1. Copy balance to balance:
        add chart
        function = None
        copy account_number
        copy account_type
    2. Copy function to income:
        add chart 
        function gets account_number (if existing), otherwise account
        account_type gets income   
    '''

    # Init
    chart = ChartOfAccounts.objects.get(id=chart_id)
    count_created = 0
    count_updated = 0
    
    # Copy
    for obj in queryset.all():
        # Adjust function and accounting numbers
        if type_from == ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL:
            function = obj.account_number
            obj.account_number = ''              
        else:
            function = None 
    
        # Check existing    
        account_instance = AccountPosition.objects.filter(
            chart=chart, 
            function=function,
            account_number=obj.account_number, 
            is_category=obj.is_category,
            account_type=account_type
        ).first()
        
        # Create new
        if account_instance:
            count_updated += 1
        else:
            count_created += 1
            account_instance = AccountPosition()
            account_instance.chart = chart 
            account_instance.function = function  
            account_instance.is_category=obj.is_category
            account_instance.account_type = account_type  

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
            verbose=AccountPosition._meta.verbose_name)
        messages.success(request, msg)   


@action_with_form(
    ChartOfAccountsBalanceForm,
    description=_('> Export selected balance positions to own balance'))
def apc_export_balance(modeladmin, request, queryset, data):
    # type checks are done in the form
    chart_id = data.get('chart')
    if chart_id:        
        apc_export(
            request, queryset, ACCOUNT_TYPE_TEMPLATE.BALANCE, 
            ACCOUNT_TYPE_TEMPLATE.BALANCE, chart_id)

@action_with_form(
    ChartOfAccountsFunctionForm,
    description=_('> Export selected function positions to own income'))
def apc_export_function_to_income(modeladmin, request, queryset, data):
    # type checks are done in the form
    chart_id = data.get('chart')
    if chart_id:
        apc_export(
            request, queryset, ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL, 
            ACCOUNT_TYPE_TEMPLATE.INCOME, chart_id)

@action_with_form(
    ChartOfAccountsFunctionForm,
    description=_('> Export selected function positions to own invest'))
def apc_export_function_to_invest(modeladmin, request, queryset, data):
    # type checks are done in the form
    chart_id = data.get('chart')
    if chart_id:        
        apc_export(
            request, queryset, ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL, 
            ACCOUNT_TYPE_TEMPLATE.INVEST, chart_id)


# AccountPosition (apm)
def apm_add(modeladmin, request, queryset, data, account_type):
    
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
            account_instance = AccountPosition.objects.filter(
                chart=chart, 
                account_number=obj.account_number,
                is_category=obj.is_category,
                function=function,
                account_type=account_type
            ).first()
                
            # Create new 
            if account_instance:
                count_updated += 1
            else:
                # We create a new instance
                count_created += 1
                account_instance = AccountPosition()                            
                account_instance.chart = chart
                account_instance.account_type = account_type
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
    AccountPositionAddIncomeForm,
    description=_('10. Add income positions to function')
)
def apm_add_income(modeladmin, request, queryset, data):
    apm_add(modeladmin, request, queryset, data, ACCOUNT_TYPE_TEMPLATE.INCOME)


@action_with_form(
    AccountPositionAddInvestForm,
    description=_('11 Add invest positions to function')
)
def apm_add_invest(modeladmin, request, queryset, data):
    apm_add(modeladmin, request, queryset, data, ACCOUNT_TYPE_TEMPLATE.INVEST)
