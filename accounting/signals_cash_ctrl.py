'''
accounting/signals_cash_ctrl.py
'''
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from scerp.exceptions import APIRequestError
from . import connector_cash_ctrl_new as conn
from .models import CustomFieldGroup, CustomField

'''
Refresh Time:
if cashCtrl signals has received within this time assume no other update
necessary
'''
MIN_REFRESH_TIME = 5  # seconds

# Helpers
def sent_to_cash_ctrl(instance):    
    ''' check if sending is necessary '''
    if instance.last_received:
        diff = timezone.now() - instance.last_received
        return diff.seconds > MIN_REFRESH_TIME
    return True
        

def handle_custom_field_signal(cls, instance, action, created=None):
    '''
    Generic handler for CustomField-related signals.

    This function performs actions based on the specified signal type 
    (create, update, delete).
    
    :cls: connector_cash_ctrl cls    
    :param instance: The model instance being affected by the signal.
    :param action: The action to perform - one of 'create', 'update', or 'delete'.
    '''
    if not instance.is_enabled_sync:
        return  # sync is turned off for this record
        
    handler = cls(instance.setup.org_name, instance.setup.api_key)    
    try:
        None.list()
        if action == "save":
            # If record has been updated 
            if sent_to_cash_ctrl(instance):
                if created:  
                    instance.c_id = handler.create(instance)                      
                    instance.save()
                else:
                    handler.update(instance)
        elif action == "delete" and instance.c_id:
            handler.delete(instance)
    except:
        raise APIRequestError("Failed to send data to the API.")

# Signal Handlers
# These handlers connect the appropriate signals to the helper functions.

# APISetup

# cashCtrl classes
@receiver(post_save, sender=CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''
    if not instance.code and instance.c_id:
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
    handle_custom_field_signal(
        conn.CustomFieldGroup, instance, 'save', created)


@receiver(pre_delete, sender=CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    handle_custom_field_signal(conn.CustomFieldGroup, instance, 'delete')


@receiver(post_save, sender=CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    if not instance.code and instance.c_id:
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
    handle_custom_field_signal(
        conn.CustomField, instance, 'save', created)


@receiver(pre_delete, sender=CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    handle_custom_field_signal(conn.CustomField, instance, 'delete')
