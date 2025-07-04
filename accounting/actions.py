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

from core.models import PersonBankAccount
from core.safeguards import save_logging
from scerp.actions import action_check_nr_selected
from scerp.exceptions import APIRequestError

from .import_export import (
    LedgerBalanceImportExport, LedgerPLImportExport, LedgerICImportExport
)
from .models import (
    FiscalPeriod, LedgerAccount, LedgerBalance, LedgerPL, LedgerIC
)

from . import forms, models
from . import api_cash_ctrl, connector_cash_ctrl as conn
from .ledger import LoadLedgerBalance

#from .signals_cash_ctrl import api_setup_post_save


@admin.action(description=('Admin: Init setup'))
def init_setup(modeladmin, request, queryset):
    pass
    '''
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
    '''


@action_with_form(
    forms.ChartOfAccountsDateForm, description=_('Get balances'))
def get_balances(modeladmin, request, queryset, data):
    """
    Custom admin action to get balances of selected records.
    """
    # Check
    if action_check_nr_selected(request, queryset, min_count=1):
        # init
        date =  data['date']

        # Load balances of underlying accounts
        if modeladmin.model == LedgerBalance:
            # load LedgerBalance
            ledger = LoadLedgerBalance(modeladmin.model, request, queryset)
            ledger.load(date)
        elif modeladmin.model == LedgerPL:
            # load LedgerPL
            balance = {
                'expense': {},
                'revenue': {}
            }
            for item in queryset.exclude(account=None):
                for key in balance.keys():
                    category = (
                        item.category_expense if key == 'expense'
                        else item.category_revenue)
                    if category and item.account.c_id:
                        balance[key][item.hrm] = conn.get_balance(
                            item.account.c_id, data['date'])
                        item.closing_balance = balance[key][item.hrm]
                        item.balance_updated = timezone.now()
                        item.save()
                    else:
                        msg = _("{item} has no cashCtrl id.").format(item=item)
                        messages.warning(request, msg)

            # Calc balances for categories
            for item in queryset.filter(account=None):
                balance_sum = sum([
                    value or 0
                    for hrm, value in balance.items()
                    if hrm.startswith(item.function)
                ])
                item.closing_balance = balance_sum
                item.balance_updated = timezone.now()
                item.save()
        else:
            print("*", modeladmin)

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
        tenant = queryset.first().tenant
        handler.get(tenant, request.user, update, delete_not_existing)
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
        tenant = queryset.first().tenant
        handler.get(
            tenant, request.user,
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
                instance.sync_accounting = True
                instance.save()


@admin.action(description=_("De-sync from Accounting"))
def de_sync_accounting(modeladmin, request, queryset):
    ''' update is_enabled_sync to False '''
    if action_check_nr_selected(request, queryset, min_count=1):
        queryset = queryset.update(
            is_enabled_sync=False,
            c_id=None, # we also deconnect c_id --> create a new object if needed
        )


@admin.action(description=_("Approve"))
def incoming_order_approve(modeladmin, request, queryset):
    ''' update is_enabled_sync to False '''
    if action_check_nr_selected(request, queryset, count=1):
        invoice = queryset.first()
        invoice.status = invoice.category.STATUS.APPROVED_1
        invoice.save()


@action_with_form(
    forms.OrderUpdateForm, description=_("Status Update")
)
def order_status_update(modeladmin, request, queryset, data):
    ''' update order status '''
    status = data['status']
    for order in queryset.all():
        order.status = status
        order.sync_to_accounting = True
        order.save()


@admin.action(description=_("Submit for booking"))
def incoming_order_approve(modeladmin, request, queryset):
    ''' update is_enabled_sync to False '''
    if action_check_nr_selected(request, queryset, count=1):
        invoice = queryset.first()
        invoice.status = invoice.category.STATUS.SUBMITTED
        invoice.save()


@admin.action(description=_("Get Order Status"))
def order_get_status(modeladmin, request, queryset):
    ''' filtering not working so we must read all orders
    '''
    if action_check_nr_selected(request, queryset, min_count=1):
        # prepare
        item = queryset.first()
        status_list = [x for x in item.category.STATUS]
        status_ids = [x['id'] for x in item.category.status_data]

        # get from cashCtrl
        api = api_cash_ctrl.Order(
            item.tenant.cash_ctrl_org_name,
            item.tenant.cash_ctrl_api_key)
        for order in queryset.all():
            invoice = api.read(order.c_id)
            index = status_ids.index(invoice['status_id'])
            order.status = status_list[index]
            order.save()


@action_with_form(
    forms.IncomingOrderForm, description=_('Scan data from invoice')
)
def get_bank_data(modeladmin, request, queryset, data):
    ''' update is_enabled_sync to False '''
    if action_check_nr_selected(request, queryset, count=1):
        invoice = queryset.first()

        changed = False
        if data['price_incl_vat']:
            invoice.price_incl_vat = data.pop('price_incl_vat')
            changed = True

        data = {k: v.replace(' ', '') for k, v in data.items()}
        bank_account = invoice.supplier_bank_account

        if bank_account:
            if data['iban'] != bank_account.iban:
                bank_account.iban = data['iban']
                changed = True
            if data['qr_iban'] != bank_account.qr_iban:
                bank_account.qr_iban = data['qr_iban']
                changed = True
            if data['bic'] != bank_account.bic:
                bank_account.bic = data['bic']
                changed = True

        if changed:
            bank_account.save()
