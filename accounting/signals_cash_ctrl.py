'''
accounting/signals_cash_ctrl.py
'''
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

from . import connector_cash_ctrl_new as conn
from .models import CustomFieldGroup, CustomField


# Helpers
def handle_custom_field_signal(cls, sender, instance, action):
    '''
    Generic handler for CustomField-related signals.

    This function performs actions based on the specified signal type 
    (create, update, delete).
    
    :cls: connector_cash_ctrl cls
    :param sender: The model class sending the signal.
    :param instance: The model instance being affected by the signal.
    :param action: The action to perform - one of 'create', 'update', or 'delete'.
    '''
    handler = cls(sender, instance=instance)
    if action == "save":
        handler.create() if instance.pk else handler.update()
    elif action == "delete" and instance.c_id:
        handler.delete(instance.c_id)


def handle_custom_field_signal_save(cls, sender, instance):
    '''
    Determine the appropriate action (create or update) for save signals
    and delegate it to the generic signal handler.

    :param sender: The model class sending the signal.
    :param instance: The model instance being saved.
    '''    
    handle_custom_field_signal(cls, sender, instance, "save")


def handle_custom_field_signal_delete(cls, sender, instance):
    '''
    Handle delete signals by delegating to the generic signal handler.

    :param sender: The model class sending the signal.
    :param instance: The model instance being deleted.
    '''
    if instance.c_id:
        handle_custom_field_signal(cls, sender, instance, "delete")


# Signal Handlers
# These handlers connect the appropriate signals to the helper functions.

# APISetup

# cashCtrl classes
@receiver(pre_save, sender=CustomFieldGroup)
def custom_field_group_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre_save signals on CustomFieldGroup. '''    
    handle_custom_field_signal_save(conn.CustomFieldGroup, sender, instance)


@receiver(pre_delete, sender=CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    handle_custom_field_signal_delete(conn.CustomFieldGroup, sender, instance)


@receiver(pre_save, sender=CustomField)
def custom_field_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre_save signals on CustomField. '''
    handle_custom_field_signal_save(conn.CustomField, sender, instance)


@receiver(pre_delete, sender=CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    handle_custom_field_signal_delete(conn.CustomField, sender, instance)
