'''
accounting/signals_cash_ctrl.py
'''
from decimal import Decimal
import logging
import time

from django.conf import settings
from django.db import IntegrityError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from scerp.exceptions import APIRequestError
from scerp.mixins import read_yaml_file
from . import models, connector_cash_ctrl as conn
from .models import TOP_LEVEL_ACCOUNT


# Set up logging
logger = logging.getLogger(__name__)


# Helpers
class CashCtrlSync:
    """
    Handles synchronization between Django models and CashCtrl API.
    """
    def __init__(self, model, instance, api_class, language=None):
        """
        Initializes the sync handler with the instance and API connector.

        :model: model of instance
        :param instance: The model instance being processed.
        :param api_class: Connector class for CashCtrl API.
        :language: language for cashCtrl queries, use None for almost all cases
        """
        self.model = model
        self.instance = instance
        self.setup = instance if model == models.APISetup else instance.setup
        self.api_class = api_class
        self.language = language
        self.handler = self.api_class(self.setup, language=self.language)
        # time.sleep(5)

    def save(self, created=False):
        """
        Handles the 'save' action (create or update).

        :param created: Boolean indicating if this is a new instance.
        """
        if self.instance.is_enabled_sync and self.instance.sync_to_accounting:
            # We only sync it this is True !!!
            if created:
                logger.info(f"Creating record {self.instance} in CashCtrl")
                self.handler.create(self.instance)
            else:
                logger.info(f"Updating record {self.instance} in CashCtrl")
                self.handler.update(self.instance)
            return
            try:
                if created:
                    logger.info(f"Creating record {self.instance} in CashCtrl")
                    self.handler.create(self.instance)
                else:
                    logger.info(f"Updating record {self.instance} in CashCtrl")
                    self.handler.update(self.instance)
            except Exception as e:
                logger.error(
                    f"Failed to sync {self.instance} with CashCtrl: {e}")
                raise APIRequestError(
                    f"Failed to send data to CashCtrl API: {e}")

    def delete(self):
        """
        Handles the 'delete' action.
        """
        if not self.instance.is_enabled_sync or not self.instance.c_id:
            return  # nothing to sync

        if getattr(self.instance, 'self.instance.stop_delete', False):
            return

        try:
            self.instance.stop_delete = True
            self.instance.save()
            logger.info(f"Deleting record {self.instance} from CashCtrl")
            self.handler.delete(self.instance)
        except Exception as e:
            logger.error(
                f"Failed to delete {self.instance} from CashCtrl: {e}")
            raise APIRequestError(
                f"Failed to delete data from CashCtrl API: {e}")

    def get(
            self, params={}, delete_not_existing=False, model=None,
            **filter_kwargs):
        """
        Handles the 'get' action (fetching data from CashCtrl).

        :params: query params
        :delete_not_existing:
            delete a record in scerp if it was delete in cashCtrl
        :model: use different model than in __init__ (esp. for APISetup)
        :filter_kwargs: filter_kwargs for cashCtrl

        The model class to retrieve.
        """
        # Init
        model = model if model else self.model
        user = self.instance.modified_by or self.instance.created_by

        # Reassign handler with actual user
        self.handler = self.api_class(
            self.setup, user=user, language=self.language)

        # Load data
        logger.info(f"Fetching data for {self.instance} from CashCtrl")
        self.handler.load(model, params, delete_not_existing, **filter_kwargs)
        return
        try:

            self.handler.load(model, params, delete_not_existing, **filter_kwargs)
        except Exception as e:
            logger.error(
                f"Failed to fetch {self.instance} from CashCtrl: {e}")
            raise APIRequestError(
                f"Failed to fetch data from CashCtrl API: {e}")


def setup_data_add_logging(setup, data):
    ''' Add logging data to cashCtrl instances '''
    data.update({
        'tenant': setup.tenant,
        'created_by': setup.created_by,
        'sync_to_accounting': True,  # send to cashCtrl
    })


# Signal Handlers
# These handlers connect the appropriate signals to the helper functions.

'''
APISetup


Creation triggers many create events
'''
@receiver(post_save, sender=models.APISetup)
def api_setup_post_save(sender, instance, created=False, **kwargs):
    '''Post action for APISetup:
        - init accounting instances

    params
    :kwargs: request for getting user
    '''
    # Init
    YAML_FILENAME = 'init_setup.yaml'

    if created or kwargs.get('init', False):
        # Make data -----------------------------------------------
        setup = instance

        # Open yaml
        init_data = read_yaml_file('accounting', YAML_FILENAME)

        """

        # Round 1 data -----------------------------------------------
        # Create CustomFieldGroups
        for data in init_data['CustomFieldGroup']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.CustomFieldGroup.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)

        # Create CustomFields
        for data in init_data['CustomField']:
            data['group'] = models.CustomFieldGroup.objects.filter(
                setup=setup, code=data.get('group_ref')).first()
            if not data['group']:
                raise ValueError(f"{data}: no group given")
            setup_data_add_logging(setup, data)
            _obj, _created = models.CustomField.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)

        # Create Location, upload not working in cashCtrl
        for data in init_data['Location']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.Location.objects.update_or_create(
                setup=setup, name=data.pop('name'), defaults=data)

        # Create Units
        for data in init_data['Unit']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.Unit.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)

        # Create Texts
        for data in init_data['Text']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.Text.objects.update_or_create(
                setup=setup, name=data.pop('name'), defaults=data)

        # Read data -----------------------------------------------
        # Location
        sync = CashCtrlSync(sender, instance, conn.Location)
        sync.get(model=models.Location)

        # FiscalPeriod
        sync = CashCtrlSync(sender, instance, conn.FiscalPeriod)
        sync.get(model=models.FiscalPeriod)

        # Currency
        sync = CashCtrlSync(sender, instance, conn.Currency)
        sync.get(model=models.Currency)

        # SequenceNumber
        sync = CashCtrlSync(sender, instance, conn.SequenceNumber)
        sync.get(model=models.SequenceNumber)

        # Unit
        sync = CashCtrlSync(sender, instance, conn.Unit)
        sync.get(model=models.Unit)

        # CostCenterCategory
        sync = CashCtrlSync(sender, instance, conn.CostCenterCategory)
        sync.get(model=models.CostCenterCategory)

        # CostCenter
        sync = CashCtrlSync(sender, instance, conn.CostCenter)
        sync.get(model=models.CostCenter)

        # AccountCategory
        sync = CashCtrlSync(sender, instance, conn.AccountCategory)
        sync.get(model=models.AccountCategory)

        # Account
        sync = CashCtrlSync(sender, instance, conn.Account)
        sync.get(model=models.Account)

        # Setting
        sync = CashCtrlSync(sender, instance, conn.Setting)
        sync.get(model=models.Setting)
        """


        # Round 2 data -----------------------------------------------
        # Create Root Additional Top AccountCategories
        for data in init_data['AccountCategories']:
            # Find top account
            parent_number = data.pop('parent_number', None)
            category_number = next((
                x.value for x in TOP_LEVEL_ACCOUNT
                if x.name == parent_number
            ), None)

            # Parent
            data['parent'] = models.AccountCategory.objects.filter(
                setup=setup, number=category_number).first()
            if not data['parent']:
                raise ValueError(f"{data}: no top category found")

            # Save
            setup_data_add_logging(setup, data)
            _obj, _created = models.AccountCategory.objects.update_or_create(
                setup=setup, number=data.pop('number'), defaults=data)

        return

        # Create Tax
        for data in init_data['Tax']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.Tax.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)
        print("*dreate", data)


'''
cashCtrl models

Note that instances only get synced if saved in scerp (
    i.e. self.received_from_scerp() is True
'''
# CustomFieldGroup
@receiver(post_save, sender=models.CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''
    sync = CashCtrlSync(sender,instance, conn.CustomFieldGroup)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    sync = CashCtrlSync(sender,instance, conn.CustomFieldGroup)
    sync.delete()


# CustomField
@receiver(pre_save, sender=models.CustomField)
def custom_field_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CustomFieldGroup. '''
    sync = CashCtrlSync(sender,instance, conn.CustomField)
    if not instance.type:
        # Assign type from group
        if instance.group:
            instance.type = instance.group.type


# CustomField
@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    sync = CashCtrlSync(sender,instance, conn.CustomField)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    sync = CashCtrlSync(sender,instance, conn.CustomField)
    sync.delete()


# FiscalPeriod
@receiver(post_save, sender=models.FiscalPeriod)
def fiscal_period_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on FiscalPeriod. '''
    sync = CashCtrlSync(sender,instance, conn.FiscalPeriod)
    sync.save(created=created)


# Currency
@receiver(post_save, sender=models.Currency)
def currency_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Currency. '''
    sync = CashCtrlSync(sender,instance, conn.Currency)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Currency)
def currency_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Currency. '''
    sync = CashCtrlSync(sender,instance, conn.Currency)
    sync.delete()


# CostCenterCategory
@receiver(post_save, sender=models.CostCenterCategory)
def cost_center_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenterCategory. '''
    sync = CashCtrlSync(sender,instance, conn.CostCenterCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CostCenterCategory)
def cost_center_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenterCategory. '''
    # Handle the children (CostCenters) first
    related_cost_centers = models.CostCenter.objects.filter(category=instance)
    for cost_center in related_cost_centers:
        cost_center.delete()  # This will cascade the delete,

    # Send the external API request
    sync = CashCtrlSync(sender,instance, conn.CostCenterCategory)
    sync.delete()


# CostCenter
@receiver(post_save, sender=models.CostCenter)
def cost_center_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenter. '''
    sync = CashCtrlSync(sender,instance, conn.CostCenter)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CostCenter)
def cost_center_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenter. '''
    sync = CashCtrlSync(sender,instance, conn.CostCenter)
    sync.delete()


# AccountCategory
@receiver(post_save, sender=models.AccountCategory)
def account_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on AccountCategory. '''
    sync = CashCtrlSync(sender,instance, conn.AccountCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.AccountCategory)
def account_category_pre_delete(sender, instance, **kwargs):
    ''''Signal handler for pre_delete signals on AccountCategory. '''
    # Check protection
    if instance.number in models.PROTECTED_ACCOUNTS:
        return

    # Handle the children (CostCenters) first
    related_accounts = models.Account.objects.filter(category=instance)
    for account in related_accounts:
        account.delete()  # This will cascade the delete

    # Send the external API request
    sync = CashCtrlSync(sender,instance, conn.AccountCategory)
    sync.delete()


# Account
@receiver(post_save, sender=models.Account)
def account_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Account. '''
    sync = CashCtrlSync(sender,instance, conn.Account)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Account)
def account_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Account. '''
    sync = CashCtrlSync(sender,instance, conn.Account)
    sync.delete()


# Rounding
@receiver(post_save, sender=models.Rounding)
def rounding_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Rounding. '''
    sync = CashCtrlSync(sender,instance, conn.Rounding)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Rounding)
def rounding_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Rounding. '''
    sync = CashCtrlSync(sender,instance, conn.Rounding)
    sync.delete()


# Title
@receiver(post_save, sender=models.Title)
def title_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Title. '''
    sync = CashCtrlSync(sender,instance, conn.Title)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Title)
def title_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Title. '''
    sync = CashCtrlSync(sender,instance, conn.Title)
    sync.delete()


# Tax
@receiver(post_save, sender=models.Tax)
def tax_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Tax. '''
    print("*tax_post_save")
    sync = CashCtrlSync(sender,instance, conn.Tax)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Tax)
def tax_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Tax. '''
    sync = CashCtrlSync(sender,instance, conn.Tax)
    sync.delete()


# SequenceNumber
@receiver(post_save, sender=models.SequenceNumber)
def sequence_number_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on SequenceNumber. '''
    sync = CashCtrlSync(sender,instance, conn.SequenceNumber)
    sync.save(created=created)


@receiver(pre_delete, sender=models.SequenceNumber)
def sequence_number_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on SequenceNumber. '''
    sync = CashCtrlSync(sender,instance, conn.SequenceNumber)
    sync.delete()


# Unit
@receiver(post_save, sender=models.Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    sync = CashCtrlSync(sender,instance, conn.Unit)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    sync = CashCtrlSync(sender,instance, conn.Unit)
    sync.delete()


# Ledger ------------------------------------------------------------------
class LedgeUpdate:

    def __init__(self, model, instance):
        self.model = model
        self.instance = instance

    @property
    def needs_update(self):
        return (self.instance.is_enabled_sync and
            self.instance.sync_to_accounting)

    def update_or_create_category(self):
        ''' update or create AccountCategory '''
        for field_name in self.category_fields:
            category = getattr(self.instance, field_name)
            if category:
                if self.instance.parent:
                    # Update my category - top  don't get updated
                    category = category
                    category.name=self.instance.name
                    category.number=self.number
                    category.sync_to_accounting = True
                    category.save()
            else:
                # Create
                if self.instance.parent:
                    category = models.AccountCategory.objects.create(
                        tenant=self.instance.tenant,
                        setup=self.instance.setup,
                        number=self.number,
                        name=self.instance.name,
                        parent=self.instance.parent.category,
                        created_by=self.instance.created_by,
                        sync_to_accounting = True
                    )
                else:
                    category = self.get_top_category(field_name)

                # Ensure `pre_save` and `post_save` run and assign `c_id`
                category.refresh_from_db()  # Fetch updated values, including c_id

        # Save
        self.instance.category = category
        self.instance.sync_to_accounting = False
        self.instance.save()

    def update_or_create_account(self):
        ''' update or create Account '''
        account = self.instance.account
        if account:
            # Update, note: we do not re-arrange groups, needs new creation
            account.name=self.instance.name
            account.number=self.number
            account.hrm=instance.hrm
            account.function=self.instance.function
            account.sync_to_accounting=True
            account.save()
        else:
            # Update or create new
            account, created = models.Account.objects.update_or_create(
                tenant=instance.tenant,
                setup=instance.setup,
                number=number,
                defaults=dict(
                    name=self.instance.name,
                    hrm=self.instance.hrm,
                    function=self.instance.function,
                    category=self.get_account_category(),
                    created_by=self.instance.created_by,
                    sync_to_accounting=True
                )
            )

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

    def __init__(self, model, instance):
        self.number = Decimal(instance.hrm)
        super().__init__(model, instance)

    def get_top_category(self, field_name=None):
        __ = field_name
        return models.AccountCategory.objects.get(
            setup=self.instance.setup, number=self.number)

    def get_account_category(self):
        return instance.parent.category


class LedgerPLUpdate(LedgeUpdate):
    category_fields = ['category_expense', 'category_revenue']

    def __init__(self, model, instance):
        if '.' in instance.hrm:
            self.number = Decimal(f"{instance.function}{instance.hrm}")
        else:
            self.number = int(instance.hrm)
        super().__init__(model, instance)

    def get_top_category(self, field_name):
        queryset = models.AccountCategory.objects.filter(
            setup=self.instance.setup)
        if field_name == 'category_expense':
            return queryset.filter(
                number=TOP_LEVEL_ACCOUNT.PL_EXPENSE.value).first()
        return queryset.filter(
            number=TOP_LEVEL_ACCOUNT.PL_EXPENSE.value).first()

    def get_account_category(self):
        if str(self.instance.hrm).startswith(TOP_LEVEL_ACCOUNT.EXPENSE.value):
            return instance.parent.category_expense
        return instance.parent.category_revenue


@receiver(post_save, sender=models.LedgerBalance)
def ledger_balance_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    __ = created
    handler = LedgerBalanceUpdate(sender, instance)
    if handler.needs_update:
        handler.save()


@receiver(post_save, sender=models.LedgerPL)
def ledger_pl_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    __ = created
    handler = LedgerPLUpdate(sender, instance)
    if handler.needs_update:
        handler.save()
