'''
accounting/ledger.py

Ledger utilities
'''
import logging
import time
from decimal import Decimal

from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from scerp.mixins import find_first_match_in_nested_dict
from . import api_cash_ctrl
from .connector_cash_ctrl import Element as ConnElement
from .models import (
    TOP_LEVEL_ACCOUNT, Account, AccountCategory, LedgerAccount, LedgerBalance,
    Element
)

# Set up logging
logger = logging.getLogger(__name__)


# Ledger to cashCtrl Mapper, called by signals ----------------------------
class Ledger:
    '''
        Gets called before Ledger is saved
        updates category, parent and function

        model: LedgerBalance, LedgerPL, LedgerIC

        use function for functions
        use hrm for accounts

    '''
    def __init__(self, model, instance, **kwargs):
        self.model = model
        self.instance = instance

        # validate hrm
        try:
            __ = float(instance.hrm) if instance.hrm else None
        except:
            msg = _("{hrm} not a valid hrm").format(hrm=instance.hrm)
            raise ValueError(msg)

        # validate name
        if isinstance(instance.name, dict):
            for language, value in instance.name.items():
                if value and len(value) > 100:
                    msg = _("{name} more than 100 chars").format(
                        name=instance.name)
                    raise ValueError(msg)

    @staticmethod
    def make_function(value_str):
        if '.' in value_str:
            return str(int(float(value_str)))
        return value_str

    def update_account(self, instance):
        # type
        instance.type = self.model.TYPE.ACCOUNT

        # parent
        if not instance.parent:
            # derive from function
            instance.parent = self.model.objects.filter(
                ledger=instance.ledger,
                function=instance.function,
                type=self.model.TYPE.CATEGORY
            ).order_by('id').last()

    def update_category(self, instance):
        # type
        instance.type = self.model.TYPE.CATEGORY

        # parent
        function_parent = instance.function[:-1]  # Removes the last character
        if not instance.parent:
            instance.parent = self.model.objects.filter(
                ledger=instance.ledger,
                type=self.model.TYPE.CATEGORY,
                function=function_parent
            ).order_by('hrm').last()

        # function
        instance.hrm = instance.function

    def update(self):
        # Init
        instance = self.instance
        instance.hrm = instance.hrm.strip() if instance.hrm else instance.hrm

        if self.model == LedgerBalance:
            try:
                instance.side = int(instance.hrm[0])
            except:
                instance.side = None

        # Calc
        if instance.type == self.model.TYPE.ACCOUNT:
            self.update_account(instance)
        elif instance.type == self.model.TYPE.CATEGORY:
            self.update_category(instance)
        elif instance.hrm and '.' in instance.hrm:
            self.update_account(instance)
        else:
            self.update_category(instance)

        # Check name
        for label in instance.name.values():
            if label and label.isupper():
                instance.message =  _("Title in upper letters")
                break

        return instance


# Ledger to cashCtrl Mapper, called by signals_cash_ctrl -------------------
class LedgeUpdate:

    def __init__(self, model, instance):
        self.model = model
        self.instance = instance

    @property
    def needs_update(self):
        return (self.instance.is_enabled_sync and
            self.instance.sync_to_accounting)

    def update_or_create_category(self):
        ''' Update or create AccountCategory '''
        category = None  # Initialize category to avoid reference before assignment

        for field_name in self.category_fields:
            # Check if category already exists
            category = getattr(self.instance, field_name, None)
            if category:  # Update if category exists
                if self.instance.parent:
                    category.name = self.instance.name
                    category.number = self.get_number(field_name)
                    category.sync_to_accounting = True
                    category.save()
            else:
                # Step 1: Find parent AccountCategory and check if new
                #   AccountCategory for current ledger positions needs to be
                #   created
                if self.instance.parent:
                    # Get AccountCategory from parent
                    create = True
                    category = getattr(
                        self.instance.parent, field_name, None)
                else:
                    # Top level, get AccountCategory from get_top_category
                    create, category = self.get_top_category(field_name)

                # Step 2: Create AccountCategory if necessary
                #   If tenant, number is already existing we reuse the
                #   category (most probably from the previous year)
                if create and category:
                    # Create new category
                    category, _created = (
                        AccountCategory.objects.update_or_create(
                            tenant=self.instance.tenant,
                            number=self.get_number(field_name),
                            defaults=dict(
                                tenant=self.instance.tenant,
                                name=self.instance.name,
                                parent=category,  # Assign the parent properly
                                created_by=self.instance.created_by,
                                sync_to_accounting=True,
                                is_scerp=True
                            )
                        ))

                    # Ensure `pre_save` and `post_save` run and assign `c_id`
                    category.refresh_from_db()

            # Ensure instance category is updated and saved
            if category:
                # Assign the last valid category
                setattr(self.instance, field_name, category)

        self.instance.sync_to_accounting = False
        self.instance.save()

    def update_or_create_account(self):
        ''' update or create Account '''
        account = self.instance.account
        if account:
            # Update, note: we do not re-arrange groups, needs new creation
            account.name=self.instance.name
            account.number = self.get_number()
            account.hrm=self.instance.hrm
            account.function=self.instance.function
            account.sync_to_accounting=True
            account.save()
        else:
            # Update or create new
            account, created = Account.objects.update_or_create(
                tenant=self.instance.tenant,
                number=self.get_number(),
                defaults=dict(
                    tenant=self.instance.tenant,
                    name=self.instance.name,
                    hrm=self.instance.hrm,
                    function=self.instance.function,
                    category=self.get_account_category(),
                    created_by=self.instance.created_by,
                    sync_to_accounting=True
                )
            )
            x = dict(
                number=self.get_number(),
                defaults=dict(
                    tenant=self.instance.tenant,
                    name=self.instance.name,
                    hrm=self.instance.hrm,
                    function=self.instance.function,
                    category=self.get_account_category(),
                    created_by=self.instance.created_by,
                    sync_to_accounting=True
                ))

            # Ensure `pre_save` and `post_save` run and assign `c_id`
            account.refresh_from_db()  # Fetch updated values, including c_id

            # After save handling
            self.instance.account = account
            self.instance.sync_to_accounting = False
            self.instance.save()

    def save(self):
        if self.instance.type == self.model.TYPE.CATEGORY:
            self.update_or_create_category()
        else:
            self.update_or_create_account()


class LedgerBalanceUpdate(LedgeUpdate):
    category_fields = ['category']

    def get_number(self, category_name=None):
        '''
        numbering:
            category: e.g. 20000.1 for assets
            account: e.g. 20000
        '''
        if category_name:
            # We need comma to create unique number
            comma = self.instance.hrm[0]
            return Decimal(f"{self.instance.function}.{comma}")

        # Account
        return Decimal(self.instance.hrm)

    def get_top_category(self, field_name=None):
        # ASSET, LIABILITY already exists
        create = False

        # top level is a cashCtrl entity -> no comma
        number = int(self.get_number(field_name))

        parent = AccountCategory.objects.filter(
            tenant=self.instance.tenant, number=number).first()
        return create, parent

    def get_account_category(self):
        return self.instance.parent.category


class LedgerFunctionalUpdate(LedgeUpdate):
    category_fields = ['category_expense', 'category_revenue']
    accounts_expense  = [
        TOP_LEVEL_ACCOUNT.EXPENSE.value,
        TOP_LEVEL_ACCOUNT.BALANCE.value
    ]

    def get_number(self, category_name=None):
        '''
        numbering:
            category: e.g. 26.31 for expense, function 26
            account: e.g. 263000.01 for function 26, account 3000.01
        '''
        if category_name:
            # We need comma to create unique number
            if category_name == 'category_expense':
                number_str = self.top_level_expense
            else:
                number_str = self.top_level_revenue

            number_str = number_str.replace('.', '')  # remove .
            return Decimal(f"{self.instance.function}.{number_str}")

        # Account
        return Decimal(f"{self.instance.function}{self.instance.hrm}")

    def get_top_category(self, field_name):
        # create
        create = True  # Functional categories do not exist

        # parent
        queryset = AccountCategory.objects.filter(tenant=self.instance.tenant)

        if field_name == 'category_expense':
            parent = queryset.filter(
                number=self.top_level_expense).first()
        elif field_name == 'category_revenue':
            parent = queryset.filter(
                number=self.top_level_revenue).first()
        else:
            raise ValueError(f"{field_name}: not a valid field name")

        if not parent:
            raise ValueError(
                f"No top category found for {self.instance} / {field_name}. "
                f"Did you run the account setup?")

        return create, parent

    def get_account_category(self):
        if (self.instance.hrm[0] in self.accounts_expense
                or '9000.' in self.instance.hrm):
            return self.instance.parent.category_expense
        return self.instance.parent.category_revenue


class LedgerPLUpdate(LedgerFunctionalUpdate):
    top_level_expense = TOP_LEVEL_ACCOUNT.PL_EXPENSE.value  # '3.1'
    top_level_revenue = TOP_LEVEL_ACCOUNT.PL_REVENUE.value  # '4.1'


class LedgerICUpdate(LedgerFunctionalUpdate):
    top_level_expense = TOP_LEVEL_ACCOUNT.IS_EXPENSE.value  # '3.2'
    top_level_revenue = TOP_LEVEL_ACCOUNT.IS_REVENUE.value  # '4.2'


# helpers for load balances
class LoadBalanceFromAccount:
    '''Load balances from cashCtrl
    params:
        model: LedgerBalance, LedgerPL,
        queryset: items of model to be updated
    '''

    def __init__(self, model, request, queryset):
        self.model = model
        self.request = request
        self.queryset = queryset

        # Init conn
        tenant = queryset.first().tenant
        self.conn = api_cash_ctrl.Account(
            tenant.cash_ctrl_org_name, tenant.cash_ctrl_api_key)

    def load_balance(self, date=None):
        '''Load LedgerBalance
        '''
        balance = {}
        for item in self.queryset.exclude(account=None):
            if item.account.c_id:
                balance[item.hrm] = self.conn.get_balance(
                    item.account.c_id, date)
                item.closing_balance = balance[item.hrm]
                item.balance_updated = timezone.now()
                item.save()
            else:
                msg = _("{item} has no cashCtrl id.").format(item=item)
                messages.warning(self.request, msg)

        # Calc balances for categories
        for item in self.queryset.filter(account=None):
            balance_sum = sum([
                value or 0
                for hrm, value in balance.items()
                if hrm.startswith(item.function)
            ])
            item.closing_balance = balance_sum
            item.balance_updated = timezone.now()
            item.save()

    def load_pl_or_ic(self, date=None):
        # Load balance from cashCtrl
        balance = {
            'expense': {},
            'revenue': {}
        }
        for item in self.queryset.exclude(account=None):
            for key in balance.keys():
                if item.account.c_id:
                    balance[key][item.function] = self.conn.get_balance(
                        item.account.c_id, date)
                    setattr(item, key, balance[key][item.function])
                else:
                    msg = _("{item} has no cashCtrl id.").format(item=item)
                    print("*item.account.c_id", category, item.account.c_id)
                    messages.warning(self.request, msg)

                item.balance_updated = timezone.now()
                item.save()

        # Calc balances for categories
        for item in self.queryset.filter(account=None):
            for key in balance.keys():
                balance_sum = sum([
                    value or 0
                    for function, value in balance[key].items()
                    if function.startswith(item.function)
                ])
                setattr(item, key,balance_sum)
            item.balance_updated = timezone.now()
            item.save()

    def load(self, date=None):
        if self.model == LedgerBalance:
            return self.load_balance(date)
        else:
            return self.load_pl_or_ic(date)


class LoadBalance:
    '''Load balances from cashCtrl
    params:
        model: LedgerBalance, LedgerPL,
        queryset: items of model to be updated
    '''

    def __init__(self, model, request, queryset):
        self.model = model
        self.request = request
        self.queryset = queryset

    def _get_data(self, element_code):
        # Init
        tenant = self.queryset.first().tenant
        period = self.queryset.first().ledger.period
        conn = ConnElement(Element)

        # Balance
        element = Element.objects.filter(
            tenant=tenant, code=element_code).first()
        if not element:
            raise ValueError("No report element found for balance.")

        data = conn.get_element_data(element, period)
        return data

    def _update_positions(self, updated_objects, field_names):
        # Update balance
        self.model.objects.bulk_update(updated_objects, field_names)


class LoadLedgerBalance(LoadBalance):

    def load(self, _date=None):
        updated_objects = []
        data = self._get_data('balance')

        # Update accounts
        for ledger_position in self.queryset:
            if ledger_position.type == self.model.TYPE.ACCOUNT:
                key = 'accountId'
                value = ledger_position.account.c_id
            elif getattr(ledger_position, 'category', None):
                # Make key, value as cashCtrl report is e.g. id: 'category-985'
                key = 'id'
                value = f'category-{ledger_position.category.c_id}'
            else:
                msg = _("no category for {category}.").format(
                    category=ledger_position)
                messages.warning(self.request, msg)
                continue

            # Get result
            result = find_first_match_in_nested_dict(data, key, value)
            if not result:
                msg = _("no result for {position}.").format(
                    position=ledger_position)
                messages.warning(self.request, msg)
                continue

            # Assign result
            ledger_position.closing_balance = result.get('endAmount')
            ledger_position.balance_updated=timezone.now()
            updated_objects.append(ledger_position)

        # Update balance
        self._update_positions(
            updated_objects, ['closing_balance', 'balance_updated'])


class LoadFunctionalLedger(LoadBalance):

    HRM_CATEGORY_MAPPING = {
        # e.g. 5031.01 -> expense as starting with 5
        'expense': LedgerAccount.HRM_CATEGORY.EXPENSE,
        'revenue': LedgerAccount.HRM_CATEGORY.REVENUE
    }

    def load(self, _date=None):
        updated_objects = []
        data = self._get_data('pls')

        # Update expense accounts
        for update_field in ('expense', 'revenue'):
            # Init
            category_field = f'category_{update_field}'
            hrm_category = self.HRM_CATEGORY_MAPPING[update_field]

            # Parse
            for ledger_position in self.queryset:
                if ledger_position.type == self.model.TYPE.ACCOUNT:
                    if ledger_position.hrm_category != hrm_category:
                        continue
                    key = 'accountId'
                    value = ledger_position.account.c_id
                elif getattr(ledger_position, category_field, None):
                    # Make key, value as cashCtrl report is e.g. id: 'category-985'
                    key = 'id'
                    category = getattr(ledger_position, category_field)
                    value = f'category-{category.c_id}'
                else:
                    msg = _("no category for {category}.").format(
                        category=ledger_position)
                    messages.warning(self.request, msg)
                    continue

                # Get result
                result = find_first_match_in_nested_dict(data, key, value)
                if not result:
                    msg = _("no result for {position}.").format(
                        position=ledger_position)
                    messages.warning(self.request, msg)
                    continue

                # Assign result
                setattr(ledger_position, update_field, result.get('endAmount'))
                ledger_position.balance_updated=timezone.now()

                updated_objects.append(ledger_position)

        # Update balance
        self._update_positions(
            updated_objects, ['expense', 'revenue', 'balance_updated'])
