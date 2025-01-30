'''
accounting/signals_cash_ctrl.py
'''
import logging

from django.conf import settings
from django.db import IntegrityError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from scerp.exceptions import APIRequestError
from scerp.mixins import read_yaml_file
from . import models, connector_cash_ctrl as conn

# Set up logging
logger = logging.getLogger(__name__)

# Refresh Time:
#   if cashCtrl signals has received within this time assume no other update
#   necessary
MIN_REFRESH_TIME = 5  # seconds


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

    def received_from_scerp(self):
        """
        Checks if data retrieval from SCERP is necessary.

        :return: Boolean indicating if a refresh is needed.
        """
        if self.instance.last_received:
            diff = timezone.now() - self.instance.last_received
            return diff.total_seconds() > MIN_REFRESH_TIME
        return True

    def save(self, created=False):
        """
        Handles the 'save' action (create or update).

        :param created: Boolean indicating if this is a new instance.
        """
        if self.received_from_scerp():
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
            return

        try:
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
        self.handler.load(model, params, delete_not_existing, **filter_kwargs)
        return
        
        try:
            logger.info(f"Fetching data for {self.instance} from CashCtrl")

        except Exception as e:
            logger.error(
                f"Failed to fetch {self.instance} from CashCtrl: {e}")
            raise APIRequestError(
                f"Failed to fetch data from CashCtrl API: {e}")


# Signal Handlers
# These handlers connect the appropriate signals to the helper functions.

'''
APISetup

Creation triggers many create events
'''
@receiver(post_save, sender=models.APISetup)
def api_setup_post_save(sender, instance, created, **kwargs):
    '''Post action for APISetup:
        - init accounting instances
        
    params
    :kwargs: request for getting user 
    '''
    # Init
    yaml_filename = 'init_setup.yaml'

    if created:
        # Read data
        sync = CashCtrlSync(sender, instance, conn.AccountCategory)
        sync.get(model=models.AccountCategory)
        return
        
        # Open yaml
        init_data = read_yaml_file('accounting', yaml_filename)
        
        # Create objects, that fire then signals to cashCtrl

        # Create CustomFieldGroups
        for data in init_data['CustomFieldGroup']:
            new_instance = create_instance(
                instance, models.CustomFieldGroup, data, **kwargs)

        # Create CustomFields
        for data in init_data['CustomField']:
            new_instance = create_instance(
                instance, models.CustomField, data, **kwargs)

'''
cashCtrl models

Note that instances only get synced if saved in scerp (
    i.e. self.received_from_scerp() is True
'''
# CustomFieldGroup
@receiver(post_save, sender=models.CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''    
    sync = CashCtrlSync(sender, instance, conn.CustomFieldGroup)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    sync = CashCtrlSync(sender, instance, conn.CustomFieldGroup)
    sync.delete()


# CustomField
@receiver(pre_save, sender=models.CustomField)
def custom_field_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CustomFieldGroup. ''' 
    sync = CashCtrlSync(sender, instance, conn.CustomField)
    if sync.received_from_scerp():
        # Assign type from group
        if instance.group:
            instance.type = instance.group.type


# CustomField
@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    sync = CashCtrlSync(sender, instance, conn.CustomField)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    sync = CashCtrlSync(sender, instance, conn.CustomField)
    sync.delete()


# Currency
@receiver(post_save, sender=models.Currency)
def currency_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Currency. '''
    sync = CashCtrlSync(sender, instance, conn.Currency)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Currency)
def currency_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Currency. '''
    sync = CashCtrlSync(sender, instance, conn.Currency)
    sync.delete()


# CostCenterCategory
@receiver(post_save, sender=models.CostCenterCategory)
def cost_center_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenterCategory. '''
    sync = CashCtrlSync(sender, instance, conn.CostCenterCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CostCenterCategory)
def cost_center_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenterCategory. '''
    sync = CashCtrlSync(sender, instance, conn.CostCenterCategory)
    sync.delete()


# CostCenter
@receiver(post_save, sender=models.CostCenter)
def cost_center_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenter. '''
    sync = CashCtrlSync(sender, instance, conn.CostCenter)
    sync.save(created=created)


@receiver(pre_delete, sender=models.CostCenter)
def cost_center_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenter. '''
    sync = CashCtrlSync(sender, instance, conn.CostCenter)
    sync.delete()


# AccountCategory
@receiver(post_save, sender=models.AccountCategory)
def account_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on AccountCategory. '''
    sync = CashCtrlSync(sender, instance, conn.AccountCategory)
    sync.save(created=created)


@receiver(pre_delete, sender=models.AccountCategory)
def account_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on AccountCategory. '''
    return
    sync = CashCtrlSync(sender, instance, conn.AccountCategory)
    sync.delete()


# Rounding
@receiver(post_save, sender=models.Rounding)
def rounding_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Rounding. '''
    sync = CashCtrlSync(sender, instance, conn.Rounding)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Rounding)
def rounding_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Rounding. '''
    sync = CashCtrlSync(sender, instance, conn.Rounding)
    sync.delete()


# Title
@receiver(post_save, sender=models.Title)
def title_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Title. '''
    sync = CashCtrlSync(sender, instance, conn.Title)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Title)
def title_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Title. '''
    sync = CashCtrlSync(sender, instance, conn.Title)
    sync.delete()


# Tax
@receiver(post_save, sender=models.Tax)
def tax_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Tax. '''
    sync = CashCtrlSync(sender, instance, conn.Tax)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Tax)
def tax_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Tax. '''
    sync = CashCtrlSync(sender, instance, conn.Tax)
    sync.delete()


# SequenceNumber
@receiver(post_save, sender=models.SequenceNumber)
def sequence_number_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on SequenceNumber. '''
    sync = CashCtrlSync(sender, instance, conn.SequenceNumber)
    sync.save(created=created)


@receiver(pre_delete, sender=models.SequenceNumber)
def sequence_number_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on SequenceNumber. '''
    sync = CashCtrlSync(sender, instance, conn.SequenceNumber)
    sync.delete()


# Unit
@receiver(post_save, sender=models.Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    sync = CashCtrlSync(sender, instance, conn.Unit)
    sync.save(created=created)


@receiver(pre_delete, sender=models.Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    sync = CashCtrlSync(sender, instance, conn.Unit)
    sync.delete()
