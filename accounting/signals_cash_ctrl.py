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
    Title as CoreTitle,
    PersonCategory as CorePersonCategory,
    Person as CorePerson
)
from scerp.mixins import read_yaml_file
from . import connector_cash_ctrl as conn
from . import models
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
        # Get request from init
        request = kwargs.get('request')

        # Make data -----------------------------------------------
        setup = instance

        # PersonCategory
        obj, created = CorePersonCategory.objects.get_or_create(
            tenant=setup.tenant,
            code='subscriber',
            defaults=dict(
                name={'de': 'Abonnenten', 'en': 'Subscribers'},
                created_by=request.user,
                sync_to_accounting=True
            )
        )
        
        # ArticleCategory
        obj, created = models.ArticleCategory.objects.get_or_create(
            tenant=setup.tenant,
            setup=setup,
            code='water',
            defaults=dict(
                name={'de': 'Wassergebühren', 'en': 'Water Billing'},
                created_by=request.user
            )
        )
        
        return
        # Order Template
        api = conn.OrderTemplate(models.OrderTemplate)
        api.get(instance, request.user, overwrite_data=True)        

        # Get settings
        api = conn.Setting(models.Setting)
        api.get(instance, request.user, update=True)
        return

        # Open yaml
        init_data = read_yaml_file('accounting', YAML_FILENAME)

        # Get titles
        sync = conn.Title()
        sync.get(CoreTitle, models.Title, instance, request.user, update=False)
        return

        # Get Person Categories
        sync = conn.PersonCategory()
        sync.get(
            CorePersonCategory, models.PersonCategory, instance, request.user,
            update=False)

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
    if instance.sync_to_accounting:
        api = conn.CustomFieldGroup(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    if instance.c_id:
        api = conn.CustomFieldGroup(sender)
        api.delete(instance)


# CustomField
@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    if instance.sync_to_accounting:
        api = conn.CustomField(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    if instance.c_id:
        api = conn.CustomField(sender)
        api.delete(instance)


# FiscalPeriod
@receiver(post_save, sender=models.FiscalPeriod)
def fiscal_period_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on FiscalPeriod. '''
    if instance.sync_to_accounting:
        api = conn.FiscalPeriod(sender)
        api.save(instance, created)



# Currency
@receiver(post_save, sender=models.Currency)
def currency_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Currency. '''
    if instance.sync_to_accounting:
        api = conn.Currency(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Currency)
def currency_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Currency. '''
    if instance.c_id:
        api = conn.Currency(sender)
        api.delete(instance)


# CostCenterCategory
@receiver(post_save, sender=models.CostCenterCategory)
def cost_center_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenterCategory. '''
    if instance.sync_to_accounting:
        api = conn.CostCenterCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CostCenterCategory)
def cost_center_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenterCategory. '''
    # Handle the children (CostCenters) first
    related_cost_centers = models.CostCenter.objects.filter(category=instance)
    for cost_center in related_cost_centers:
        cost_center.delete()  # This will cascade the delete,

    # Send the external API request
    if instance.c_id:
        api = conn.CostCenterCategory(sender)
        api.delete(instance)


# CostCenter
@receiver(post_save, sender=models.CostCenter)
def cost_center_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenter. '''
    if instance.sync_to_accounting:
        api = conn.CostCenter(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CostCenter)
def cost_center_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenter. '''
    if instance.c_id:
        api = conn.CostCenter(sender)
        api.delete(instance)


# AccountCategory
@receiver(post_save, sender=models.AccountCategory)
def account_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on AccountCategory. '''
    if instance.sync_to_accounting:
        api = conn.AccountCategory(sender)
        api.save(instance, created)


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
    if instance.c_id:
        api = conn.AccountCategory(sender)
        api.delete(instance)


# Account
@receiver(post_save, sender=models.Account)
def account_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Account. '''
    if instance.sync_to_accounting:
        api = conn.Account(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Account)
def account_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Account. '''
    if instance.c_id:
        api = conn.Account(sender)
        api.delete(instance)


# BankAccount
@receiver(post_save, sender=models.BankAccount)
def bank_account_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Bank Account. '''
    if instance.sync_to_accounting:
        api = conn.BankAccount(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.BankAccount)
def bank_account_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Bank Account. '''
    if instance.c_id:
        api = conn.BankAccount(sender)
        api.delete(instance)


# Rounding
@receiver(post_save, sender=models.Rounding)
def rounding_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Rounding. '''
    if instance.sync_to_accounting:
        api = conn.Rounding(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Rounding)
def rounding_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Rounding. '''
    if instance.c_id:
        api = conn.Rounding(sender)
        api.delete(instance)


# Tax
@receiver(post_save, sender=models.Tax)
def tax_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Tax. '''
    if instance.sync_to_accounting:
        api = conn.Tax(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Tax)
def tax_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Tax. '''
    if instance.c_id:
        api = conn.Tax(sender)
        api.delete(instance)


# SequenceNumber
@receiver(post_save, sender=models.SequenceNumber)
def sequence_number_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on SequenceNumber. '''
    if instance.sync_to_accounting:
        api = conn.SequenceNumber(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.SequenceNumber)
def sequence_number_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on SequenceNumber. '''
    if instance.c_id:
        api = conn.SequenceNumber(sender)
        api.delete(instance)


# Unit
@receiver(post_save, sender=models.Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    if instance.sync_to_accounting:
        api = conn.Unit(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    if instance.c_id:
        api = conn.Unit(sender)
        api.delete(instance)


# ArticleCategory
@receiver(post_save, sender=models.ArticleCategory)
def article_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on ArticleCategory. '''
    if instance.sync_to_accounting:
        api = conn.ArticleCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.ArticleCategory)
def article_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on ArticleCategory. '''
    if instance.c_id:
        api = conn.ArticleCategory(sender)
        api.delete(instance)


# Article
@receiver(post_save, sender=models.Article)
def article_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Article. '''
    if instance.sync_to_accounting:
        api = conn.Article(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Article)
def article_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Article. '''
    if instance.c_id:
        api = conn.Article(sender)
        api.delete(instance)


# OrderTemplate
@receiver(post_save, sender=models.OrderTemplate)
def order_template_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderTemplate. '''
    if instance.sync_to_accounting:
        api = conn.OrderTemplate(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderTemplate)
def order_template_contract_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderTemplate. '''
    if instance.c_id:
        api = conn.OrderTemplate(sender)
        api.delete(instance)
        

# OrderCategoryContract
@receiver(post_save, sender=models.OrderCategoryContract)
def order_category_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryContract. '''
    if instance.sync_to_accounting:
        api = conn.OrderCategoryContract(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryContract)
def order_category_contract_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryContract. '''
    if instance.c_id:
        api = conn.OrderCategoryContract(sender)
        api.delete(instance)


# OrderCategoryIncoming
@receiver(post_save, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryIncoming. '''
    if instance.sync_to_accounting:
        api = conn.OrderCategoryIncoming(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryIncoming. '''
    if instance.c_id:
        api = conn.OrderCategoryIncoming(sender)
        api.delete(instance)


# ContractOrder
@receiver(post_save, sender=models.OrderContract)
def order_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderContract. '''
    if instance.sync_to_accounting:
        api = conn.OrderContract(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderContract)
def order_contract_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderContract. '''
    if instance.c_id:
        api = conn.OrderContract(sender)
        api.delete(instance)


# IncomingOrder
@receiver(post_save, sender=models.IncomingOrder)
def incoming_order_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on IncomingOrder. '''
    if instance.sync_to_accounting:
        api = conn.IncomingOrder(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.IncomingOrder)
def incoming_order_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on IncomingOrder. '''
    if instance.c_id:
        api = conn.IncomingOrder(sender)
        api.delete(instance)


@receiver(post_save, sender=models.IncomingBookEntry)
def incoming_book_entry_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on IncomingBookEntry. '''
    if instance.sync_to_accounting:
        api = conn.IncomingBookEntry(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.IncomingBookEntry)
def incoming_book_entry_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on IncomingBookEntry. '''
    if instance.c_id:
        api = conn.IncomingBookEntry(sender)
        api.delete(instance)


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
@receiver(post_save, sender=CoreTitle)
def title_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Title. '''
    if instance.sync_to_accounting:
        api = conn.Title(sender)
        api.save(instance, created)


@receiver(post_delete, sender=models.Title)
def title_post_delete(sender, instance, **kwargs):
    '''Signal handler for post_delete signals on Title. '''
    if instance.c_id:
        api = conn.Title()
        api.delete(instance)


# PersonCategory
@receiver(post_save, sender=CorePersonCategory)
def person_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CorePersonCategory. '''
    if instance.sync_to_accounting:
        api = conn.PersonCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.PersonCategory)
def person_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on PersonCategory. '''
    if instance.c_id:
        api = conn.PersonCategory()
        api.delete(instance)


# Person
@receiver(post_save, sender=CorePerson)
def person_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CorePerson. '''
    if instance.sync_to_accounting:
        api = conn.Person(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Person)
def person_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Person. '''
    if instance.c_id:
        api = conn.Person()
        api.delete(instance)
