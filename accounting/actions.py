'''
accounting/actions.py
'''
import importlib
import logging

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from core.safeguards import save_logging
from scerp.admin import action_check_nr_selected
from scerp.exceptions import APIRequestError

from .models import (
    APPLICATION, ACCOUNT_TYPE_TEMPLATE, APISetup,
    AccountPositionTemplate,
    ChartOfAccounts, AccountPosition, FiscalPeriod
)
from . import models
from . import connector_cash_ctrl, forms
from . import connector_cash_ctrl_new as conn
from . import signals, signals_cash_ctrl
from .import_accounts_canton import Import
from .mixins import AccountPositionCheck
from .connector import get_connector_module
from .signals_cash_ctrl import api_setup_post_save


ACTION_LOAD = _('Load actual data from Accounting System')

DONOT_COPY_FIELDS = [
    # General
    'pk', 'id', 'created_at', 'created_by_id', 'modified_at', 'modified_by_id',
    'version_id', 'protected', 'inactive',

    # Accounting
    'chart', 'chart_id', 'account_type', 'function',

    # CashCtrl
    'c_id', 'c_created', 'c_created_by', 'c_last_updated', 'c_last_updated_by'
]

# Set up a logger to capture the error details
logger = logging.getLogger(__name__)


class Handler:
    
    def __init__(self, modeladmin, request, queryset, api_class):
        # Check if at least one item is selected
        # error handling not working
        if action_check_nr_selected(request, queryset, min_count=1):
            # Get setup
            setup = queryset.first().setup
            
            # Proceed if application is CASH_CTRL
            if setup.application == APPLICATION.CASH_CTRL:            
                # Get handler
                self.handler = api_class(setup.org_name, setup.api_key)
                            
                # Init            
                self.model = modeladmin.model
                self.setup = setup
                self.user = request.user
            else:
                self.handler = None
                messages.error(request, _("No accounting system defined."))        
        
    def load(self, request):
        if self.handler:
            self.handler.load(self.model, self.setup, self.user)
            return
            try:
                self.handler.load(self.model, self.setup, self.user)
            except:
                messages.error(request, _("API Error: cannot retrieve data"))


# mixins
def get_api_setup(queryset):
    '''Get api.setup from queryset
    '''
    api_setup = queryset.first().setup
    if api_setup:
        _api_setup, module = get_connector_module(api_setup=api_setup)
        return api_setup, module
    messages.error(request, _("No account setup found"))
    

@admin.action(description=f"1. {_('Get data from account system')}")
def accounting_get_data(modeladmin, request, queryset):
    ''' load data '''    
    api_class = getattr(conn, modeladmin.model.__name__, None)
    if api_class:
        handler = Handler(modeladmin, request, queryset, api_class)
        handler.load(request)
    else:
        messages.warning(request, _("Cannot retrieve data for this list"))

@admin.action(description=('Admin: Init setup'))
def init_setup(modeladmin, request, queryset):
    # Check
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()

        # Only perform actions if there are no errors
        try:
            # Wrap the database operation in an atomic block
            with transaction.atomic():
                api_setup_post_save(
                    modeladmin.model, instance, created=True, request=request) 
        except IntegrityError as e:
            if "Duplicate entry" in str(e):
                msg = _("Unique constraints violated")    
                messages.error(request, f"{msg}: {e}")                
            else:
                messages.error(request, f"An error occurred: {str(e)}")  
        except APIRequestError as e:
            # Catch the custom exception and show a user-friendly message
            messages.error(request, f"APIRequestError: {str(e)}")        
        
        messages.success(request, _("Accounting API initialized"))
  

@admin.action(description=ACTION_LOAD)
def api_setup_get(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()
        api_setup, module = get_connector_module(api_setup=instance)
        module.get_all(api_setup)        


@action_with_form(
    forms.ConfirmForm, description="Admin: delete HRM accounting positions")
def api_setup_delete_hrm_accounts(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()
        api_setup, module = get_connector_module(api_setup=instance)
        acc = module.Account(api_setup) 

        try:
            count = acc.delete_hrm()
            msg = _("Deleted {count} accounts").format(count=count)
            messages.success(request, msg)
        except Exception as e:
            error_msg = _("An error occurred while deleting accounts: {error}").format(error=str(e))
            messages.error(request, error_msg)


@action_with_form(
    forms.ConfirmForm, description="Admin: delete system accounting positions")
def api_setup_delete_system_accounts(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()
        api_setup, module = get_connector_module(api_setup=instance)
        acc = module.Account(api_setup) 

        try:
            count = acc.delete_system_accounts()
            msg = _("Deleted {count} accounts").format(count=count)
            messages.success(request, msg)
        except Exception as e:
            error_msg = _("An error occurred while deleting accounts: {error}").format(error=str(e))
            messages.error(request, error_msg)


def api_setup_delete_categories(request, queryset, method):
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()
        api_setup, module = get_connector_module(api_setup=instance)
        acc = module.AccountCategory(api_setup) 

        try:
            count = getattr(acc, method)()
            msg = _("Deleted {count} categories").format(count=count)
            messages.success(request, msg)
        except Exception as e:
            error_msg = _("An error occurred while deleting accounts: {error}").format(error=str(e))
            messages.error(request, error_msg)   


@action_with_form(
    forms.ConfirmForm, description="Admin: delete HRM accounting categories")
def api_setup_delete_hrm_categories(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    method = 'delete_hrm'
    api_setup_delete_categories(request, queryset, method)


@action_with_form(
    forms.ConfirmForm, description="Admin: delete system categories")
def api_setup_delete_system_categories(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    method = 'delete_system'
    api_setup_delete_categories(request, queryset, method)


# Load actual data ----------------------------------------------------------
def api_get(modeladmin, request, queryset, cls):
    __, __ = modeladmin, request  # disable pylint warning    
    api_setup, module = get_api_setup(queryset)
    ctrl = getattr(module, cls)(api_setup)  # e.g. module.LocationConn(api_setup) 
    ctrl.get()
    
@admin.action(description=ACTION_LOAD)
def location_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'LocationConn')
    
@admin.action(description=ACTION_LOAD)
def fiscal_period_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'FiscalPeriodConn')

@admin.action(description=ACTION_LOAD)
def currency_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'CurrencyConn')

@admin.action(description=ACTION_LOAD)
def unit_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'UnitConn')

@admin.action(description=ACTION_LOAD)
def tax_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'TaxConn')

@admin.action(description=ACTION_LOAD)
def rounding_get(modeladmin, request, queryset):  # Corrected function name
    api_get(modeladmin, request, queryset, 'RoundingConn')  # Corrected 'RoundingyConn' to 'RoundingConn'

@admin.action(description=ACTION_LOAD)
def sequence_number_get(modeladmin, request, queryset):  # Corrected function name
    api_get(modeladmin, request, queryset, 'SequenceNumberConn')

@admin.action(description=ACTION_LOAD)
def order_category_get(modeladmin, request, queryset):  # Corrected function name
    api_get(modeladmin, request, queryset, 'OrderCategoryConn')

@admin.action(description=ACTION_LOAD)
def order_template_get(modeladmin, request, queryset):  # Corrected function name
    api_get(modeladmin, request, queryset, 'OrderTemplateConn')


@admin.action(description=ACTION_LOAD)
def cost_center_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'CostCenterConn')

@admin.action(description=ACTION_LOAD)
def article_get(modeladmin, request, queryset):
    api_get(modeladmin, request, queryset, 'ArticleConn')


# Mixins ----------------------------------------------------------
@admin.action(description=_('12 Check accounting positions'))
def check_accounts(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # Perform    
        try:
            apc = AccountPositionCheck(queryset)
            apc.check()
            messages.success(
                request, _("Accounting positons checked. No errors found."))
        except Exception as e:
            msg = _('Check result: {e}').format(e=e)
            messages.warning(request, msg)


@admin.action(description=_('13 Convert names from upper to title case'))
def account_names_convert_upper_case(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        apc = AccountPositionCheck(queryset)
        change_list = apc.convert_upper_case()
        if not change_list:
            messages.success(request, _("No changes. All good."))
        else:
            for position in change_list:
                msg = _("Converted '{number} {name}'.").format(
                    number=position.account_number, name=position.name)
                messages.info(request, msg)


@admin.action(description=_('14 Upload accounting positions'))
def upload_accounts(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # Check account_type
        account_types = set([x.account_type for x in queryset])
        if len(account_types) > 1:
            messages.error(request, _("Mixed account types found"))
        else:
            # Prepare
            api_setup, module = get_api_setup(queryset)
            ctrl = module.Account(api_setup)
     
            # Perform    
            headings_w_numbers = queryset.first().chart.headings_w_numbers
            ctrl.upload_accounts(queryset, headings_w_numbers) 
            messages.success(request, _("Accounting positons uploaded"))


@admin.action(description=_('15 Get balances from accounting system'))
def download_balances(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare
        api_setup, module = get_api_setup(queryset)
        ctrl = module.Account(api_setup)
 
        # Perform
        count = ctrl.download_balances(queryset) 
        msg = _("{count} balances downloaded.").format(count=count)
        messages.success(request, msg)
        

@action_with_form(
    forms.ChartOfAccountsDateForm,
    description=_(
        '16 Get current balances from accounting system')
)
def get_balances(modeladmin, request, queryset, data):
    """
    Custom admin action to get balances of selected records.
    """
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare
        api_setup, module = get_api_setup(queryset)
        ctrl = module.Account(api_setup)
 
        # Perform
        count = ctrl.get_balances(queryset, data.get('date'))
    
        # Perform
        msg =  _("{count} positions updated.").format(count=count)
        messages.success(request, msg)
        
        # Download balances to doublecheck
        download_balances(modeladmin, request, queryset)


@action_with_form(
    forms.ChartOfAccountsDateForm,
    description=_(
        '17 Upload opening balances to accounting system')
)
def upload_balances(modeladmin, request, queryset, data):
    """
    Custom admin action to upload balances of selected records.
    """
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare
        api_setup, module = get_api_setup(queryset)
        ctrl = module.Account(api_setup)
 
        # Perform
        response = ctrl.upload_balances(queryset, data.get('date'))
    
        # Perform
        msg =  _("Balances uploaded, {response}").format(response=response)
        messages.success(request, msg)
        
        # Download balances to doublecheck
        download_balances(modeladmin, request, queryset)


@admin.action(description=_('> Insert copy of record below'))
def position_insert(modeladmin, request, queryset):
    """
    Insert row of a model that has a field position
    """
    __ = modeladmin  # disable pylint warning
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
    except Exception as e:
        msg = _('Not allowed to copy this record. {e}').format(e=e)
        messages.warning(request, msg)
        return


# ChartOfAccountsTemplate (coac)
def coac_positions(request, queryset, overwrite):
    """
    Check Excel File of ChartOfAccountsTemplate
    """
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
        check_only = not overwrite
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
                    save_logging(account_instance, request, add_tenant)

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
    '''
    perform position check
    '''
    __ = modeladmin  # disable pylint warning
    coac_positions(request, queryset, overwrite=False)


@action_with_form(
    forms.ChartOfAccountsTemplateForm,
    description=_('> Create canton account positions'))
def coac_positions_create(modeladmin, request, queryset, data):
    """
    Check Excel File of ChartOfAccountsTemplate
    """
    __ = modeladmin  # disable pylint warning
    __ = data  # disable pylint warning

    # Check number selected
    if action_check_nr_selected(request, queryset, 1):
         # Load excel
        coac_positions(request, queryset, overwrite=True)


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
    setup = chart.period.setup
    count_created = 0
    count_updated = 0

    # Copy
    for obj in queryset.all():
        # Adjust function and accounting numbers
        if type_from == ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL:
            function = obj.account_number
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
            account_instance.setup=setup
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
        save_logging(account_instance, request, add_tenant=True)
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
    forms.ChartOfAccountsBalanceForm,
    description=_('> Export selected balance positions to own balance'))
def apc_export_balance(modeladmin, request, queryset, data):
    '''
    type checks are done in the form
    '''
    __ = modeladmin  # disable pylint warning
    chart_id = data.get('chart')
    if chart_id:
        apc_export(
            request, queryset, ACCOUNT_TYPE_TEMPLATE.BALANCE,
            ACCOUNT_TYPE_TEMPLATE.BALANCE, chart_id)

@action_with_form(
    forms.ChartOfAccountsFunctionForm,
    description=_('> Export selected function positions to own income'))
def apc_export_function_to_income(modeladmin, request, queryset, data):
    '''
    type checks are done in the form
    '''
    __ = modeladmin  # disable pylint warning
    chart_id = data.get('chart')
    if chart_id:
        apc_export(
            request, queryset, ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL,
            ACCOUNT_TYPE_TEMPLATE.INCOME, chart_id)

@action_with_form(
    forms.ChartOfAccountsFunctionForm,
    description=_('> Export selected function positions to own invest'))
def apc_export_function_to_invest(modeladmin, request, queryset, data):
    '''
    type checks are done in the form
    '''
    __ = modeladmin  # disable pylint warning
    chart_id = data.get('chart')
    if chart_id:
        apc_export(
            request, queryset, ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL,
            ACCOUNT_TYPE_TEMPLATE.INVEST, chart_id)


# AccountPosition (apm)
def apm_add(request, queryset, data, account_type):
    '''
    add income or invest
    '''
    # Check number selected
    if queryset.count() > 1:
        messages.warning(request, _('Select only one function.'))

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
            save_logging(account_instance, request, add_tenant=True)
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
    forms.AccountPositionAddIncomeForm,
    description=_('10. Add income positions to function')
)
def apm_add_income(modeladmin, request, queryset, data):
    '''
    add income to Account Positions
    '''
    __ = modeladmin  # disable pylint warning
    apm_add(request, queryset, data, ACCOUNT_TYPE_TEMPLATE.INCOME)


@action_with_form(
    forms.AccountPositionAddInvestForm,
    description=_('11 Add invest positions to function')
)
def apm_add_invest(modeladmin, request, queryset, data):
    '''
    add invest to Account Positions
    '''
    __ = modeladmin  # disable pylint warning
    apm_add(request, queryset, data, ACCOUNT_TYPE_TEMPLATE.INVEST)


@action_with_form(
    forms.AssignResponsibleForm,
    description=_(
        '17 Assign a responsible group to the selected account positions.')
)
def assign_responsible(modeladmin, request, queryset, data):
    """
    Custom admin action to assign a responsible group to selected records.
    """
    __ = modeladmin  # disable pylint warning
    # Update the `responsible` field for all selected records
    responsible = data.get('responsible')
    count_updated = queryset.update(responsible=responsible)
    msg = _("Successfully assigned '{group}' to {count} records.").format(
        group=responsible.name, count=count_updated)
    messages.success(request, msg)
