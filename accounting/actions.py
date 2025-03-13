'''
accounting/actions.py
'''
import logging

from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import CharField
from django.db.models.functions import Cast
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from core.safeguards import save_logging
from scerp.actions import action_check_nr_selected
from scerp.exceptions import APIRequestError

from .import_export import (
    LedgerBalanceImportExport, LedgerPLImportExport, LedgerICImportExport
)
from .models import (
    APISetup, FiscalPeriod,
    LedgerAccount, LedgerBalance, LedgerPL, LedgerIC
)

from . import forms, models
from . import connector_cash_ctrl as conn
from .signals_cash_ctrl import api_setup_post_save


@admin.action(description=('Admin: Init setup'))
def init_setup(modeladmin, request, queryset):
    # Check
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()

        # Only perform actions if there are no errors
        with transaction.atomic():
            api_setup_post_save(
                modeladmin.model, instance, init=True, request=request)        
        return 
        try:
            # Wrap the database operation in an atomic block
            with transaction.atomic():
                api_setup_post_save(
                    modeladmin.model, instance, init=True, request=request)
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


def add_excel_to_ledger(model, request, queryset, data):
    """
    Custom admin action to assign a responsible group to selected records.
    """
    MAPPING = {
        LedgerBalance: LedgerBalanceImportExport,
        LedgerPL: LedgerPLImportExport,
        LedgerIC: LedgerICImportExport
    }

    # Update the `responsible` field for all selected records
    excel_file = data.get('excel_file')
    if not excel_file:
        messages.error(request, _("No file uploaded."))
        return

    # Init
    ledger = queryset.first()
    handler = MAPPING[model]

    #try:
    process = handler(ledger, request)
    process.update_or_get(excel_file)

    messages.success(request, _("Excel file processed successfully."))

    #except Exception as e:
    #    messages.error(request, _("Error processing Excel file: ") + str(e))


@action_with_form(
    forms.LedgerBalanceUploadForm, description=_('20 Insert or update into Balance')
)
def add_balance(modeladmin, request, queryset, data):
    """
    Custom admin action to assign a responsible group to selected records.
    """
    add_excel_to_ledger(LedgerBalance, request, queryset, data)


@action_with_form(
    forms.LedgerPLUploadForm, description=_('21 Insert or update into P&L')
)
def add_pl(modeladmin, request, queryset, data):
    """
    Custom admin action to assign a responsible group to selected records.
    """
    add_excel_to_ledger(LedgerPL, request, queryset, data)


@action_with_form(
    forms.LedgerICUploadForm, description=_('22 Insert or update into IC')
)
def add_ic(modeladmin, request, queryset, data):
    """
    Custom admin action to assign a responsible group to selected records.
    """
    add_excel_to_ledger(LedgerIC, request, queryset, data)


# Account
def get_data(modeladmin, request, queryset, update, delete_not_existing):
    api = getattr(conn, modeladmin.model.__name__, None)
    language = None  # i.e. English
    if api:
        handler = api(modeladmin.model)        
        setup = queryset.first().setup
        tenant = setup.tenant
        handler.get(setup, request.user, update, delete_not_existing)
    else:
        messages.warning(request, _("Cannot retrieve data for this list"))    

@action_with_form(
    forms.AccountingUpdateForm, description=_('Get data from account system')
)
def accounting_get_data(modeladmin, request, queryset, data):
    ''' load data '''
    model = modeladmin.model.__name__
    api = getattr(conn, model, None)
    language = None  # i.e. English
    if api:
        handler = api(modeladmin.model, language=language)
        setup = queryset.first().setup
        tenant = setup.tenant
        handler.get(
            setup, request.user, 
            overwrite_data=data['overwrite_data'], 
            delete_not_existing=data['delete_not_existing']
        )        
    else:
        messages.warning(request, _("Cannot retrieve data for this list"))


@admin.action(description=f"{_('Get data from account system')}")
def accounting_get_data_update_delete_not_existing(
        modeladmin, request, queryset):
    ''' load data '''
    get_data(
        modeladmin, request, queryset, update=True, delete_not_existing=True)


@admin.action(description=f"{_('Get data from account system')}")
def accounting_get_data_update(modeladmin, request, queryset, data):
    ''' load data '''
    get_data(
        modeladmin, request, queryset, update=True, delete_not_existing=True)





# Default row actions, accounting
@admin.action(description=_("Sync with Accounting"))
def sync_accounting(modeladmin, request, queryset):
    ''' set is_enabled_sync to True and save to trigger post_save '''
    if action_check_nr_selected(request, queryset, min_count=1):
        for instance in queryset.all():
            if not instance.is_enabled_sync:
                instance.is_enabled_sync = True
                instance.save()


@admin.action(description=_("De-sync from Accounting"))
def de_sync_accounting(modeladmin, request, queryset):
    ''' update is_enabled_sync to False '''
    if action_check_nr_selected(request, queryset, min_count=1):
        queryset = queryset.update(is_enabled_sync=False)
