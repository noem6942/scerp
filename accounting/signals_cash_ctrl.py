'''
accounting/signals_cash_ctrl.py
'''
from decimal import Decimal
import logging
import time

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models.signals import post_save, pre_save
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from core.models import (
    Title as TitleCrm,
    PersonCategory as PersonCategoryCrm,
    Person as PersonCrm
)
from scerp.mixins import read_yaml_file
from . import connector_cash_ctrl_2 as conn2
from . import models, connector_cash_ctrl as conn
from .ledger import LedgerBalanceUpdate, LedgerPLUpdate, LedgerICUpdate


# Set up logging
logger = logging.getLogger(__name__)


# Helpers
def setup_data_add_logging(setup, data):
    ''' Add logging data to cashCtrl instances '''
    data.update({
        'tenant': setup.tenant,
        'created_by': setup.created_by,
        'sync_to_accounting': True,  # send to cashCtrl
    })


# Signal Handlers

# APISetup ----------------------------------------------------------------

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

        # Get request from init
        request = kwargs.get('request')

        # Get titles
        sync = conn2.Title()
        sync.get(TitleCrm, models.Title, instance, request.user, update=False)

        return

        # PersonCategory
        sync = conn.CashCtrlSync(sender, instance, conn.PersonCategory)
        sync.get(model=models.PersonCategory)

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

        return

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
        sync = conn.CashCtrlSync(sender, instance, conn.Location)
        sync.get(model=models.Location)

        # FiscalPeriod
        sync = conn.CashCtrlSync(sender, instance, conn.FiscalPeriod)
        sync.get(model=models.FiscalPeriod)

        # Currency
        sync = conn.CashCtrlSync(sender, instance, conn.Currency)
        sync.get(model=models.Currency)

        # SequenceNumber
        sync = conn.CashCtrlSync(sender, instance, conn.SequenceNumber)
        sync.get(model=models.SequenceNumber)

        # Unit
        sync = conn.CashCtrlSync(sender, instance, conn.Unit)
        sync.get(model=models.Unit)

        # CostCenterCategory
        sync = conn.CashCtrlSync(sender, instance, conn.CostCenterCategory)
        sync.get(model=models.CostCenterCategory)

        # CostCenter
        sync = conn.CashCtrlSync(sender, instance, conn.CostCenter)
        sync.get(model=models.CostCenter)

        # AccountCategory
        sync = conn.CashCtrlSync(sender, instance, conn.AccountCategory)
        sync.get(model=models.AccountCategory)

        # Account
        sync = conn.CashCtrlSync(sender, instance, conn.Account)
        sync.get(model=models.Account)

        # Setting
        sync = conn.CashCtrlSync(sender, instance, conn.Setting)
        sync.get(model=models.Setting)

        # Title
        sync = conn.CashCtrlSync(sender, instance, conn.Title)
        sync.get(model=models.Title)

        # PersonCategory
        sync = conn.CashCtrlSync(sender, instance, conn.PersonCategory)
        sync.get(model=models.PersonCategory)

        # Round 2 data -----------------------------------------------
        # Create Root Additional Top AccountCategories
        for data in init_data['AccountCategories']:
            # Find top account
            parent_number = data.pop('parent_number', None)
            category_number = next((
                x.value for x in models.TOP_LEVEL_ACCOUNT
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


        # Round 3: sync again -----------------------------------------------

        # Tax
        sync = conn.CashCtrlSync(sender, instance, conn.Tax)
        sync.get(model=models.Tax)


# accounting.models ----------------------------------------------------------
'''
Note that instances only get synced if saved in scerp (
    i.e. self.received_from_scerp() is True
'''
# CustomFieldGroup
@receiver(post_save, sender=models.CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''
    __ = sender
    if instance.sync_to_accounting:
        api = conn2.CustomFieldGroup()
        api.save(instance, created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    __ = sender
    if instance.c_id:
        api = conn2.CustomFieldGroup()
        api.delete(instance)


# CustomField
@receiver(pre_save, sender=models.CustomField)
def custom_field_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CustomFieldGroup. '''
    sync = conn.CashCtrlSync(sender, instance, conn.CustomField)
    if not instance.type:
        # Assign type from group
        if instance.group:
            instance.type = instance.group.type


# CustomField
@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    sync = conn.CashCtrlSync(sender, instance, conn.CustomField)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    sync = conn.CashCtrlSync(sender, instance, conn.CustomField)
    sync.delete()


# FiscalPeriod
@receiver(post_save, sender=models.FiscalPeriod)
def fiscal_period_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on FiscalPeriod. '''
    sync = conn.CashCtrlSync(sender, instance, conn.FiscalPeriod)
    sync.save(created=created)


# Currency
@receiver(post_save, sender=models.Currency)
def currency_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Currency. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Currency)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Currency)
def currency_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Currency. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Currency)
    sync.delete()


# CostCenterCategory
@receiver(post_save, sender=models.CostCenterCategory)
def cost_center_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenterCategory. '''
    sync = conn.CashCtrlSync(sender, instance, conn.CostCenterCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CostCenterCategory)
def cost_center_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenterCategory. '''
    # Handle the children (CostCenters) first
    related_cost_centers = models.CostCenter.objects.filter(category=instance)
    for cost_center in related_cost_centers:
        cost_center.delete()  # This will cascade the delete,

    # Send the external API request
    sync = conn.CashCtrlSync(sender, instance, conn.CostCenterCategory)
    sync.delete()


# CostCenter
@receiver(post_save, sender=models.CostCenter)
def cost_center_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenter. '''
    sync = conn.CashCtrlSync(sender, instance, conn.CostCenter)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CostCenter)
def cost_center_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenter. '''
    sync = conn.CashCtrlSync(sender, instance, conn.CostCenter)
    sync.delete()


# AccountCategory
@receiver(post_save, sender=models.AccountCategory)
def account_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on AccountCategory. '''
    sync = conn.CashCtrlSync(sender, instance, conn.AccountCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.AccountCategory)
def account_category_pre_delete(sender, instance, **kwargs):
    ''''Signal handler for pre_delete signals on AccountCategory. '''
    # Check protection
    if instance.is_top_level_account:
        raise ValueError(_("Deletion is not allowed for {instance.number}."))

    # Handle the children first
    related_accounts = models.Account.objects.filter(category=instance)
    for account in related_accounts:
        account.delete()  # This will cascade the delete

    # Send the external API request
    sync = conn.CashCtrlSync(sender, instance, conn.AccountCategory)
    sync.delete()


# Account
@receiver(post_save, sender=models.Account)
def account_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Account. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Account)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Account)
def account_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Account. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Account)
    sync.delete()


# Rounding
@receiver(post_save, sender=models.Rounding)
def rounding_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Rounding. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Rounding)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Rounding)
def rounding_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Rounding. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Rounding)
    sync.delete()


# Tax
@receiver(post_save, sender=models.Tax)
def tax_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Tax. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Tax)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Tax)
def tax_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Tax. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Tax)
    sync.delete()


# SequenceNumber
@receiver(post_save, sender=models.SequenceNumber)
def sequence_number_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on SequenceNumber. '''
    sync = conn.CashCtrlSync(sender, instance, conn.SequenceNumber)
    sync.save(created=created)


@receiver(pre_delete, sender=models.SequenceNumber)
def sequence_number_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on SequenceNumber. '''
    sync = conn.CashCtrlSync(sender, instance, conn.SequenceNumber)
    sync.delete()


# Unit
@receiver(post_save, sender=models.Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Unit)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Unit)
    sync.delete()


# ArticleCategory
@receiver(post_save, sender=models.ArticleCategory)
def article_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on ArticleCategory. '''
    sync = conn.CashCtrlSync(sender, instance, conn.ArticleCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.ArticleCategory)
def article_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on ArticleCategory. '''
    sync = conn.CashCtrlSync(sender, instance, conn.ArticleCategory)
    sync.delete()


# Article
@receiver(post_save, sender=models.Article)
def article_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Article. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Article)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Article)
def article_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Article. '''
    sync = conn.CashCtrlSync(sender, instance, conn.Article)
    sync.delete()


# OrderCategoryContract
@receiver(post_save, sender=models.OrderCategoryContract)
def order_category_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryContract. '''
    # Ensure related M2M relationships are saved
    sync = conn.CashCtrlSync(sender, instance, conn.OrderCategoryContract)
    sync.save(created=created)


@receiver(pre_delete, sender=models.OrderCategoryContract)
def order_category_contract_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryContract. '''
    sync = conn.CashCtrlSync(sender, instance, conn.OrderCategoryContract)
    sync.delete()


# OrderCategoryIncoming
@receiver(post_save, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryIncoming. '''
    sync = conn.CashCtrlSync(sender, instance, conn.OrderCategoryIncoming)
    sync.save(created=created)


@receiver(pre_delete, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryIncoming. '''
    sync = conn.CashCtrlSync(sender, instance, conn.OrderCategoryIncoming)
    sync.delete()


# ContractOrder
@receiver(post_save, sender=models.OrderContract)
def order_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderContract. '''
    sync = conn.CashCtrlSync(sender, instance, conn.OrderContract)
    sync.save(created=created)


@receiver(pre_delete, sender=models.OrderContract)
def order_contract_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderContract. '''
    sync = conn.CashCtrlSync(sender, instance, conn.OrderContract)
    sync.delete()


# IncomingOrder
@receiver(post_save, sender=models.IncomingOrder)
def incoming_order_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on IncomingOrder. '''
    sync = conn.CashCtrlSync(sender, instance, conn.IncomingOrder)
    sync.save(created=created)


@receiver(pre_delete, sender=models.IncomingOrder)
def incoming_order_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on IncomingOrder. '''
    sync = conn.CashCtrlSync(sender, instance, conn.IncomingOrder)
    sync.delete()


# Ledger ------------------------------------------------------------------
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


@receiver(post_save, sender=models.LedgerIC)
def ledger_ic_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    __ = created
    handler = LedgerICUpdate(sender, instance)
    if handler.needs_update:
        handler.save()


# core.models ----------------------------------------------------------
# Helpers
def get_or_create_accounting_instance(model, instance, created):
    # Init
    setup = models.APISetup.objects.filter(
        tenant=instance.tenant, is_default=True).first()
    create = created

    # Check if existing
    if not created:
        account_instance = model.objects.filter(
            core=instance, setup=setup).first()
        if not account_instance:
            create = True

    # Create
    if create:
        account_instance = model.objects.create(
            tenant=instance.tenant,
            setup=setup,
            core=instance,
            is_enabled_sync=True,
            sync_to_accounting=True,
            created_by=instance.created_by
        )

    return account_instance, create


# Title
@receiver(post_save, sender=TitleCrm)
def title_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Title. '''
    __ = sender
    if instance.sync_to_accounting:
        api = conn2.Title()
        api.save(instance, created)


@receiver(post_delete, sender=models.Title)
def title_pre_delete(sender, instance, **kwargs):
    '''Signal handler for post_delete signals on Title. '''
    if instance.c_id:
        api = conn2.Title()
        api.delete(instance)


# PersonCategory
@receiver(post_save, sender=PersonCategoryCrm)
def person_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on PersonCategory. '''
    model = models.PersonCategory
    accounting_instance, created = get_or_create_accounting_instance(
        model, instance, created)
    sync = conn.CashCtrlSync(
        model, instance, conn.PersonCategory,
        accounting_instance=accounting_instance)
    sync.save(created=created)


@receiver(pre_delete, sender=PersonCategoryCrm)
def person_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on PersonCategory. '''
    model = models.PersonCategory
    accounting_instance, created = get_or_create_accounting_instance(
        model, instance, created=False)
    sync = conn.CashCtrlSync(
        model, instance, conn.PersonCategory,
        accounting_instance=accounting_instance)
    sync.delete()


# Person
@receiver(post_save, sender=PersonCrm)
def person_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Person. '''
    model = models.Person
    accounting_instance, created = get_or_create_accounting_instance(
        model, instance, created)
    sync = conn.CashCtrlSync(
        model, instance, conn.Person, accounting_instance=accounting_instance)
    sync.save(created=created)


@receiver(pre_delete, sender=PersonCrm)
def person_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Person. '''
    model = models.Person
    accounting_instance, created = get_or_create_accounting_instance(
        model, instance, created=False)
    sync = conn.CashCtrlSync(
        model, instance, conn.Person, accounting_instance=accounting_instance)
    sync.delete()
