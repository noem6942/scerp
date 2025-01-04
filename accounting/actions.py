'''
accounting/actions.py
'''
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from core.safeguards import save_logging
from scerp.admin import action_check_nr_selected

from .forms import (
    ChartOfAccountsTemplateForm,
    ChartOfAccountsBalanceForm,
    ChartOfAccountsFunctionForm,
    AccountPositionAddIncomeForm,
    AccountPositionAddInvestForm,
    AssignResponsibleForm
)
from .models import (
    ACCOUNT_TYPE_TEMPLATE, APISetup,
    AccountPositionTemplate,
    ChartOfAccounts, AccountPosition, FiscalPeriod
)
from .import_accounts_canton import Import
from .mixins import AccountPositionCheck
from .connector import get_connector_module
from .signals import api_setup


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
def get_api_setup(queryset):
    '''Get api.setup from queryset
    '''
    api_setup = queryset.first().setup
    if api_setup:
        _api_setup, module = get_connector_module(api_setup=api_setup)
        return api_setup, module
    messages.error(request, _("No account setup found"))


@admin.action(description=_('Init setup'))
def init_setup(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    # Check
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()
        api_setup(type(instance), instance, created=False, init=True) 
        messages.success(request, _("Accounting API initialized"))
    else:
        return


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


@admin.action(description=_('15 Upload budgets'))
def upload_balances(modeladmin, request, queryset):
    __ = modeladmin  # disable pylint warning
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare
        api_setup, module = get_api_setup(queryset)
        ctrl = module.Account(api_setup)
 
        # Perform
        ctrl.upload_balances(queryset) 
        messages.success(request, _("Balances uploaded"))


@admin.action(description=_('16 Get balances from accounting system'))
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


# FiscalPeriod
@admin.action(description=_('3. Set selected period as current'))
def fiscal_period_set_current(modeladmin, request, queryset):
    """
    Insert row of a model that has a field position
    """
    __ = modeladmin  # disable pylint warning
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
    '''
    perform position check
    '''
    __ = modeladmin  # disable pylint warning
    coac_positions(request, queryset, overwrite=False)


@action_with_form(
    ChartOfAccountsTemplateForm,
    description=_('> Create canton account positions'))
def coac_positions_create(modeladmin, request, queryset, data):
    """
    Check Excel File of ChartOfAccountsTemplate
    """
    __ = modeladmin  # disable pylint warning
    _ = data  # disable pylint warning

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
    ChartOfAccountsFunctionForm,
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
    ChartOfAccountsFunctionForm,
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
    '''
    add income to Account Positions
    '''
    __ = modeladmin  # disable pylint warning
    apm_add(request, queryset, data, ACCOUNT_TYPE_TEMPLATE.INCOME)


@action_with_form(
    AccountPositionAddInvestForm,
    description=_('11 Add invest positions to function')
)
def apm_add_invest(modeladmin, request, queryset, data):
    '''
    add invest to Account Positions
    '''
    __ = modeladmin  # disable pylint warning
    apm_add(request, queryset, data, ACCOUNT_TYPE_TEMPLATE.INVEST)


@action_with_form(
    AssignResponsibleForm,
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
