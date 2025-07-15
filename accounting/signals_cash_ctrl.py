'''
accounting/signals_cash_ctrl.py
'''
from decimal import Decimal
import logging
import time

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models.signals import pre_save, post_save
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from asset.models import Unit, AssetCategory, Device
from core.models import Tenant
from core.models import (
    # we sync them here
    Title, PersonCategory, Person, PersonAddress, PersonContact,
    PersonBankAccount
)

from scerp.mixins import read_yaml_file
from . import connector_cash_ctrl as conn
from . import models
from .ledger import LedgerBalanceUpdate, LedgerPLUpdate, LedgerICUpdate


# Set up logging
logger = logging.getLogger(__name__)


ACCOUNT_SETUP_YAML = 'init_tenant.yaml'

# Helpers
def setup_data_add_logging(tenant, data):
    ''' Add logging data to cashCtrl instances '''
    data.update({
        'created_by': tenant.created_by,
        'sync_to_accounting': True,  # send to cashCtrl
    })


def sync(instance):
    return (
        instance.is_enabled_sync and instance.sync_to_accounting
        and instance.tenant.cash_ctrl_org_name
    )


def sync_delete(instance):
    return (
        instance.is_enabled_sync and instance.c_id
        and instance.tenant.cash_ctrl_org_name
    )


# Signal Handlers

# Tenant Setup --------------------------------------------------------------

@receiver(post_save, sender=Tenant)
def tenant_accounting_post_save(sender, instance, created=False, **kwargs):
    '''Post action for Tenant
    '''
    # Check no action
    __ = sender  # not used
    if created:
        return  # no action, first we want the user to select the tenant
    elif instance.is_initialized_accounting:    
        return  # no action, already initialized
    elif not kwargs.get('init'):
        return  # no action, if tenant setup not manually set    
    elif not instance.cash_ctrl_org_name:
        raise ValueError("Tenant has no cashCtrl org_name")
        return 
    elif not instance.cash_ctrl_api_key:
        raise ValueError("Tenant has no cashCtrl api key")
        return 

    # Intro ---------------------------------------------------------------
    tenant = instance
    
    # shift core data to accounting
    core_models = (
        Title,
        PersonCategory,
        #Person,
        Unit,
        AssetCategory,
        #Device
    )
    for model in core_models:
        queryset = model.objects.filter(tenant=tenant, is_enabled_sync=False)
        for obj in queryset.all():
            obj.is_enabled_sync = True
            obj.sync_to_accounting = True
            obj.save()
            logger.info(f"saved {obj}")

    # Open yaml
    init_data = read_yaml_file('accounting', ACCOUNT_SETUP_YAML)

    # Create CustomFieldGroups
    for data in init_data['CustomFieldGroup']:
        setup_data_add_logging(tenant, data)
        _obj, _created = models.CustomFieldGroup.objects.update_or_create(
            tenant=tenant, code=data.pop('code'), defaults=data)
    logger.info(f"saved CustomFieldGroups")

    # Create CustomFields
    for data in init_data['CustomField']:
        data['group'] = models.CustomFieldGroup.objects.filter(
            tenant=tenant, code=data.get('group_ref')).first()
        if not data['group']:
            raise ValueError(f"{data}: no group given")
        setup_data_add_logging(tenant, data)
        _obj, _created = models.CustomField.objects.update_or_create(
            tenant=tenant, code=data.pop('code'), defaults=data)
    logger.info(f"saved CustomFieldGroups")

    # Create ArticleCategory
    for data in init_data['ArticleCategory']:
        setup_data_add_logging(tenant, data)
        _obj, _created = models.ArticleCategory.objects.update_or_create(
            tenant=tenant, code=data.pop('code'), defaults=data)
    logger.info(f"saved CustomFieldGroups")

    # Create FileCategory
    for data in init_data['FileCategory']:
        setup_data_add_logging(tenant, data)
        _obj, _created = models.FileCategory.objects.update_or_create(
            tenant=tenant, code=data.pop('code'), defaults=data)
    logger.info(f"saved FileCategory")

    # Create Order Layout
    for data in init_data['OrderLayout']:
        setup_data_add_logging(tenant, data)
        _obj, _created = models.OrderLayout.objects.update_or_create(
            tenant=tenant, name=data.pop('name'), defaults=data)
    logger.info(f"saved OrderLayout")

    # Get Location
    api = conn.Location(models.Location)
    api.get(tenant, tenant.created_by)

    # Get FiscalPeriod
    api = conn.FiscalPeriod(models.FiscalPeriod)
    api.get(tenant, tenant.created_by)

    # Get Currency
    api = conn.Currency(models.Currency)
    api.get(tenant, tenant.created_by)

    # Get SequenceNumber
    api = conn.SequenceNumber(models.SequenceNumber)
    api.get(tenant, tenant.created_by)

    # Get CostCenterCategory
    api = conn.CostCenterCategory(models.CostCenterCategory)
    api.get(tenant, tenant.created_by)

    # Get CostCenter
    api = conn.CostCenter(models.CostCenter)
    api.get(tenant, tenant.created_by)

    # Get AccountCategory
    api = conn.AccountCategory(models.AccountCategory)
    api.get(tenant, tenant.created_by)

    # Get Account
    api = conn.Account(models.Account)
    api.get(tenant, tenant.created_by)

    # Get Rounding
    api = conn.Rounding(models.Rounding)
    api.get(tenant, tenant.created_by)

    # Get Setting
    api = conn.Setting(models.Setting)
    api.get(tenant, tenant.created_by)

    # Get Tax
    api = conn.Tax(models.Tax)
    api.get(tenant, tenant.created_by)

    # Get BankAccount
    api = conn.BankAccount(models.BankAccount)
    api.get(tenant, tenant.created_by)

    # Create AccountCategory, ER / IR categories like 3.1, 4.1 etc.
    for data in init_data['AccountCategory']:
        setup_data_add_logging(tenant, data)
        data['parent'] = models.AccountCategory.objects.filter(
            number=data.pop('parent_number')).first()
        _obj, _created = models.AccountCategory.objects.update_or_create(
            tenant=tenant, number=data.pop('number'), defaults=data)
    logger.info(f"saved AccountCategory")

    # Update tenant
    instance.is_initialized = True
    instance.save()


# core.models ----------------------------------------------------------

# Title
@receiver(post_save, sender=Title)
def title_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Title. '''
    if sync(instance):
        api = conn.Title(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=Title)
def title_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Title. '''
    if sync_delete(instance):
        api = conn.Title()
        api.delete(instance)


# PersonCategory
@receiver(post_save, sender=PersonCategory)
def person_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on PersonCategory. '''
    # BUG: seems not be synced !!!
    if sync(instance):
        api = conn.PersonCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=PersonCategory)
def person_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on PersonCategory. '''
    if sync_delete(instance):
        api = conn.PersonCategory()
        api.delete(instance)


# Person
@receiver(post_save, sender=Person)
def person_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Person.

    We need handle_sync because we want to delay that the add operations to
    manytomany fields are done
    '''
    if sync(instance):
        api = conn.Person(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=Person)
def person_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Person. '''
    if sync_delete(instance):
        api = conn.Person()
        api.delete(instance)
        instance._predeleted = True


# Person-related entities
def person_save(instance, created=None):
    # Gets called whenever something changes with person
    instance.sync_to_accounting = True
    if sync(instance):
        api = conn.Person(instance)
        api.save(instance, created)


def person_related_delete(instance):
    # Gets called whenever some deletes are in action
    person_id = instance.person_id  # still valid

    def sync_if_person_exists():
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return  # Person was deleted, do nothing
        person.sync_to_accounting = True
        if sync(person):
            api = conn.Person(person)
            api.save(person)

    transaction.on_commit(sync_if_person_exists)


@receiver(post_save, sender=PersonAddress)
def person_address_post_save(sender, instance, created, **kwargs):
    person_save(instance.person)


@receiver(post_delete, sender=PersonAddress)
def person_address_post_delete(sender, instance, **kwargs):
    person_related_delete(instance)


@receiver(post_save, sender=PersonContact)
def person_contact_post_save(sender, instance, created, **kwargs):
    person_save(instance.person)


@receiver(post_delete, sender=PersonContact)
def person_contact_post_delete(sender, instance, **kwargs):
    person_related_delete(instance)



@receiver(post_save, sender=PersonBankAccount)
def person_bank_account_post_save(sender, instance, created, **kwargs):
    person_save(instance.person)


@receiver(post_delete, sender=PersonBankAccount)
def person_bank_account_post_delete(sender, instance, **kwargs):
    person_related_delete(instance)


# asset.models ----------------------------------------------------------

# Unit
@receiver(post_save, sender=Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    if sync(instance):
        api = conn.Unit(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    if sync_delete(instance):
        api = conn.Unit(sender)
        api.delete(instance)


# AssetCategory
@receiver(post_save, sender=AssetCategory)
def asset_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on AssetCategory. '''
    if sync(instance):
        api = conn.AssetCategory(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=AssetCategory)
def asset_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on AssetCategory. '''
    if sync_delete(instance):
        api = conn.AssetCategory(sender)
        api.delete(instance)


# Device
@receiver(post_save, sender=Device)
def device_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Device. '''
    return
    # disabeld for now
    if sync(instance):
        api = conn.Asset(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=Device)
def device_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Device. '''
    if sync_delete(instance):
        api = conn.Asset(sender)
        api.delete(instance)


# accounting.models ----------------------------------------------------------
'''
Note that instances only get synced if saved in scerp (
    i.e. self.received_from_scerp() is True
'''
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
        api = conn.SequenceNumber(sender)
        api.delete(instance)


# Journal
@receiver(post_save, sender=models.Journal)
def journal_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Journal. '''
    if sync(instance):
        api = conn.Journal(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.Journal)
def journal_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Journal. '''
    if sync_delete(instance):
        api = conn.Journal(sender)
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
    if sync_delete(instance):
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
    if sync_delete(instance):
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
    if sync_delete(instance):
        api = conn.OrderLayout(sender)
        api.delete(instance)


# OrderCategoryContract
@receiver(post_save, sender=models.OrderCategoryContract)
def order_category_contract_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryContract. '''
    if instance.block_update:
        # do not update
        instance.sync_to_accounting = False
        instance.block_update = False  # reset
        instance.save()
    elif sync(instance):
        api = conn.OrderCategoryContract(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryContract)
def order_category_contract_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryContract. '''
    if sync_delete(instance):
        api = conn.OrderCategoryContract(sender)
        api.delete(instance)


# OrderCategoryIncoming
@receiver(post_save, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryIncoming. '''
    if instance.block_update:
        # do not update
        instance.sync_to_accounting = False
        instance.block_update = False  # reset
        instance.save()
    elif sync(instance):
        api = conn.OrderCategoryIncoming(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryIncoming)
def order_category_incoming_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryIncoming. '''
    if sync_delete(instance):
        api = conn.OrderCategoryIncoming(sender)
        api.delete(instance)


# OrderCategoryOutgoing
@receiver(post_save, sender=models.OrderCategoryOutgoing)
def order_category_outgoing_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on OrderCategoryOutgoing. '''
    if instance.block_update:
        # do not update
        instance.sync_to_accounting = False
        instance.block_update = False  # reset
        instance.save()
    elif sync(instance):
        api = conn.OrderCategoryOutgoing(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OrderCategoryOutgoing)
def order_category_outgoing_post_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OrderCategoryOutgoing. '''
    if sync_delete(instance):
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
    if sync_delete(instance):
        api = conn.OrderContract(sender)
        api.delete(instance)


# Incomingitem, related to IncomingOrder
def incoming_order_save(instance, created=None):
    # Gets called whenever something changes with IncomingOrder
    instance.sync_to_accounting = True
    if sync(instance):
        api = conn.IncomingOrder(instance)
        api.save(instance, created)


def incoming_order_related_delete(instance):
    # Gets called whenever some deletes are in action
    order_id = instance.order_id  # still valid

    def sync_if_order_exists():
        try:
            order = models.IncomingOrder.objects.get(pk=order_id)
        except models.IncomingOrder.DoesNotExist:
            return  # IncomingOrder was deleted, do nothing
        order.sync_to_accounting = True
        if sync(order):
            api = conn.IncomingOrder(order)
            api.save(order)

    transaction.on_commit(sync_if_order_exists)


@receiver(post_save, sender=models.IncomingItem)
def incoming_item_post_save(sender, instance, created, **kwargs):
    incoming_order_save(instance.order)


@receiver(post_delete, sender=models.IncomingItem)
def incoming_item_post_delete(sender, instance, **kwargs):
    incoming_order_related_delete(instance)


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
    if sync_delete(instance):
        api = conn.IncomingOrder(sender)
        api.delete(instance)


# OutgoingOrder
@receiver(post_save, sender=models.OutgoingOrder)
def outgoing_order_post_save(sender, instance, created, **kwargs):
    '''
    Signal handler for post_save signals on OutgoingOrder.
    OutgoingItem gets own signal (see below)
    '''
    if sync(instance):
        api = conn.OutgoingOrder(sender)
        api.save(instance, created)


@receiver(pre_delete, sender=models.OutgoingOrder)
def outgoing_order_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on OutgoingOrder. '''
    if sync_delete(instance):
        api = conn.OutgoingOrder(sender)
        api.delete(instance)


# OutgoingItem, related to OutgoingOrder
def outgoing_order_save(instance, created=None):
    # Gets called whenever something changes with OutgoingOrder
    instance.sync_to_accounting = True
    if sync(instance):
        api = conn.OutgoingOrder(instance)
        api.save(instance, created)


def outgoing_order_related_delete(instance):
    # Gets called whenever some deletes are in action
    order_id = instance.order_id  # still valid

    def sync_if_order_exists():
        try:
            order = models.OutgoingOrder.objects.get(pk=order_id)
        except models.OutgoingOrder.DoesNotExist:
            return  # OutgoingOrder was deleted, do nothing
        order.sync_to_accounting = True
        if sync(order):
            api = conn.OutgoingOrder(order)
            api.save(order)

    transaction.on_commit(sync_if_order_exists)


@receiver(post_save, sender=models.OutgoingItem)
def outgoing_item_post_save(sender, instance, created, **kwargs):
    outgoing_order_save(instance.order)


@receiver(post_delete, sender=models.OutgoingItem)
def outgoing_item_post_delete(sender, instance, **kwargs):
    outgoing_order_related_delete(instance)


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
        # creates or updates an Account in cashCtrl
        handler.save()


@receiver(post_save, sender=models.LedgerIC)
def ledger_ic_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    __ = created
    handler = LedgerICUpdate(sender, instance)
    if handler.needs_update:
        handler.save()
