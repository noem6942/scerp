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

        # Open yaml
        init_data = read_yaml_file('accounting', YAML_FILENAME)

        # Make data -----------------------------------------------
        setup = instance

        # update_or_create data ------------------------------------
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

        # Create FileCategory
        for data in init_data['FileCategory']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.FileCategory.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)

        # Unit
        for data in init_data['Unit']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.Unit.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)

        # Order Layout
        for data in init_data['OrderLayout']:
            setup_data_add_logging(setup, data)
            _obj, _created = models.OrderLayout.objects.update_or_create(
                setup=setup, name=data.pop('name'), defaults=data)

        # get core data ----------------------------------------------

        # Get titles
        sync = conn.Title(CoreTitle)
        sync.get(models.Title, setup, request.user, update=False)

        # Get Person Categories
        sync = conn.PersonCategory(CorePersonCategory)
        sync.get(models.PersonCategory, setup, request.user, update=False)

        # Read data -----------------------------------------------
        # we use default params, currently:
        #   overwrite_data=True,
        #   delete_not_existing=True

        # Location
        sync = conn.Location(models.Location)
        sync.get(setup, request.user)

        # FiscalPeriod
        sync = conn.FiscalPeriod(models.FiscalPeriod)
        sync.get(setup, request.user)

        # Currency
        sync = conn.Currency(models.Currency)
        sync.get(setup, request.user)

        # SequenceNumber
        sync = conn.SequenceNumber(models.SequenceNumber)
        sync.get(setup, request.user)

        # Unit
        sync = conn.Unit(models.Unit)
        sync.get(setup, request.user)

        # CostCenterCategory
        sync = conn.CostCenterCategory(models.CostCenterCategory)
        sync.get(setup, request.user)

        # CostCenter
        sync = conn.CostCenter(models.CostCenter)
        sync.get(setup, request.user)

        # AccountCategory
        sync = conn.AccountCategory(models.AccountCategory)
        sync.get(setup, request.user)

        # Account
        sync = conn.Account(models.Account)
        sync.get(setup, request.user)

        # Setting
        sync = conn.Setting(models.Setting)
        sync.get(setup, request.user)

        # Tax
        sync = conn.Tax(models.Tax)
        sync.get(setup, request.user)

        # Create data -----------------------------------------------

        # AccountCategory, ER / IR categories like 3.1, 4.1 etc.
        for data in init_data['AccountCategory']:
            setup_data_add_logging(setup, data)
            data['parent'] = models.AccountCategory.objects.filter(
                number=data.pop('parent_number')).first()
            _obj, _created = models.AccountCategory.objects.update_or_create(
                setup=setup, number=data.pop('number'), defaults=data)

        # Tax
        # Take first 2000 account
        account = models.Account.objects.filter(
            number__startswith='2'
        ).first()
        print("*account", account)

        # Add
        for data in init_data['Tax']:
            data['account'] = account
            setup_data_add_logging(setup, data)
            _obj, _created = models.Tax.objects.update_or_create(
                setup=setup, code=data.pop('code'), defaults=data)


# accounting.models ----------------------------------------------------------
'''
Note that instances only get synced if saved in scerp (
    i.e. self.received_from_scerp() is True
'''
# Helper
def sync(instance):
    return instance.is_enabled_sync and instance.sync_to_accounting


# CustomFieldGroup
@receiver(post_save, sender=models.CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''
    if sync(instance):
        api = conn.CustomFieldGroup(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    if sync(instance) and instance.c_id:
        api = conn.CustomFieldGroup(sender)
        api.delete(instance)


# CustomField
@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    if sync(instance):
        api = conn.CustomField(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    if sync(instance) and instance.c_id:
        api = conn.CustomField(sender)
        api.delete(instance)


# FileCategory
@receiver(post_save, sender=models.FileCategory)
def file_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on FileCategory. '''
    if sync(instance):
        api = conn.FileCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.FileCategory)
def file_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on FileCategory. '''
    if sync(instance) and instance.c_id:
        api = conn.FileCategory(sender)
        api.delete(instance)


# FiscalPeriod
@receiver(post_save, sender=models.FiscalPeriod)
def fiscal_period_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on FiscalPeriod. '''
    if sync(instance):
        api = conn.FiscalPeriod(sender)
        api.save(instance, created)



# Currency
@receiver(post_save, sender=models.Currency)
def currency_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Currency. '''
    if sync(instance):
        api = conn.Currency(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Currency)
def currency_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Currency. '''
    if sync(instance) and instance.c_id:
        api = conn.Currency(sender)
        api.delete(instance)


# CostCenterCategory
@receiver(post_save, sender=models.CostCenterCategory)
def cost_center_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenterCategory. '''
    if sync(instance):
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
    if sync(instance) and instance.c_id:
        api = conn.CostCenterCategory(sender)
        api.delete(instance)


# CostCenter
@receiver(post_save, sender=models.CostCenter)
def cost_center_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenter. '''
    if sync(instance):
        api = conn.CostCenter(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.CostCenter)
def cost_center_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenter. '''
    if sync(instance) and instance.c_id:
        api = conn.CostCenter(sender)
        api.delete(instance)


# AccountCategory
@receiver(post_save, sender=models.AccountCategory)
def account_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on AccountCategory. '''
    if sync(instance):
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
    if sync(instance) and instance.c_id:
        api = conn.AccountCategory(sender)
        api.delete(instance)


# Account
@receiver(post_save, sender=models.Account)
def account_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Account. '''
    if sync(instance):
        api = conn.Account(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Account)
def account_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Account. '''
    if sync(instance) and instance.c_id:
        api = conn.Account(sender)
        api.delete(instance)


# BankAccount
@receiver(post_save, sender=models.BankAccount)
def bank_account_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Bank Account. '''
    if sync(instance):
        api = conn.BankAccount(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.BankAccount)
def bank_account_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Bank Account. '''
    if sync(instance) and instance.c_id:
        api = conn.BankAccount(sender)
        api.delete(instance)


# Rounding
@receiver(post_save, sender=models.Rounding)
def rounding_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Rounding. '''
    if sync(instance):
        api = conn.Rounding(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Rounding)
def rounding_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Rounding. '''
    if sync(instance) and instance.c_id:
        api = conn.Rounding(sender)
        api.delete(instance)


# Tax
@receiver(post_save, sender=models.Tax)
def tax_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Tax. '''
    if sync(instance):
        api = conn.Tax(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Tax)
def tax_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Tax. '''
    if sync(instance) and instance.c_id:
        api = conn.Tax(sender)
        api.delete(instance)


# SequenceNumber
@receiver(post_save, sender=models.SequenceNumber)
def sequence_number_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on SequenceNumber. '''
    if sync(instance):
        api = conn.SequenceNumber(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.SequenceNumber)
def sequence_number_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on SequenceNumber. '''
    if sync(instance) and instance.c_id:
        api = conn.SequenceNumber(sender)
        api.delete(instance)


# Unit
@receiver(post_save, sender=models.Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    if sync(instance):
        api = conn.Unit(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    if sync(instance) and instance.c_id:
        api = conn.Unit(sender)
        api.delete(instance)


# ArticleCategory
@receiver(post_save, sender=models.ArticleCategory)
def article_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on ArticleCategory. '''
    if sync(instance):
        api = conn.ArticleCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.ArticleCategory)
def article_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on ArticleCategory. '''
    if sync(instance) and instance.c_id:
        api = conn.ArticleCategory(sender)
        api.delete(instance)


# Article
@receiver(post_save, sender=models.Article)
def article_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Article. '''
    if sync(instance):
        api = conn.Article(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Article)
def article_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Article. '''
    if sync(instance) and instance.c_id:
        api = conn.Article(sender)
        api.delete(instance)


# OrderLayout
@receiver(post_save, sender=models.OrderLayout)
def order_layout_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderLayout. '''
    if sync(instance):
        api = conn.OrderLayout(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderLayout)
def order_layout_contract_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderLayout. '''
    if sync(instance) and instance.c_id:
        api = conn.OrderLayout(sender)
        api.delete(instance)


# OrderCategoryContract
@receiver(post_save, sender=models.OrderCategoryContract)
def order_category_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryContract. '''
    if sync(instance):
        api = conn.OrderCategoryContract(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryContract)
def order_category_contract_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryContract. '''
    if sync(instance) and instance.c_id:
        api = conn.OrderCategoryContract(sender)
        api.delete(instance)


# OrderCategoryIncoming
@receiver(post_save, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryIncoming. '''
    if sync(instance):
        api = conn.OrderCategoryIncoming(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryIncoming. '''
    if sync(instance) and instance.c_id:
        api = conn.OrderCategoryIncoming(sender)
        api.delete(instance)


# OrderCategoryOutgoing
@receiver(post_save, sender=models.OrderCategoryOutgoing)
def order_category_outgoing_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryOutgoing. '''
    if sync(instance):
        api = conn.OrderCategoryOutgoing(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryOutgoing)
def order_category_outgoing_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryOutgoing. '''
    if sync(instance) and instance.c_id:
        api = conn.OrderCategoryOutgoing(sender)
        api.delete(instance)


# ContractOrder
@receiver(post_save, sender=models.OrderContract)
def order_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderContract. '''
    if sync(instance):
        api = conn.OrderContract(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderContract)
def order_contract_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderContract. '''
    if sync(instance) and instance.c_id:
        api = conn.OrderContract(sender)
        api.delete(instance)


# IncomingOrder
@receiver(post_save, sender=models.IncomingOrder)
def incoming_order_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on IncomingOrder. '''
    if sync(instance):
        api = conn.IncomingOrder(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.IncomingOrder)
def incoming_order_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on IncomingOrder. '''
    if sync(instance) and instance.c_id:
        api = conn.IncomingOrder(sender)
        api.delete(instance)


# OutgoingOrder
@receiver(post_save, sender=models.OutgoingOrder)
def outgoing_order_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OutgoingOrder. '''
    if sync(instance):
        api = conn.OutgoingOrder(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OutgoingOrder)
def outgoing_order_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OutgoingOrder. '''
    if sync(instance) and instance.c_id:
        api = conn.OutgoingOrder(sender)
        api.delete(instance)


""" do not use
@receiver(post_save, sender=models.IncomingBookEntry)
def incoming_book_entry_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on IncomingBookEntry. '''
    if sync(instance):
        api = conn.IncomingBookEntry(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.IncomingBookEntry)
def incoming_book_entry_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on IncomingBookEntry. '''
    if sync(instance) and instance.c_id:
        api = conn.IncomingBookEntry(sender)
        api.delete(instance)
"""

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
    if sync(instance):
        api = conn.Title(sender)
        api.save(instance, created)


@receiver(post_delete, sender=models.Title)
def title_post_delete(sender, instance, **kwargs):
    '''Signal handler for post_delete signals on Title. '''
    if sync(instance) and instance.c_id:
        api = conn.Title()
        api.delete(instance)


# PersonCategory
@receiver(post_save, sender=CorePersonCategory)
def person_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CorePersonCategory. '''
    if sync(instance):
        api = conn.PersonCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.PersonCategory)
def person_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on PersonCategory. '''
    if sync(instance) and instance.c_id:
        api = conn.PersonCategory()
        api.delete(instance)


# Person
@receiver(post_save, sender=CorePerson)
def person_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CorePerson. '''
    if sync(instance):
        api = conn.Person(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Person)
def person_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Person. '''
    if sync(instance) and instance.c_id:
        api = conn.Person()
        api.delete(instance)
