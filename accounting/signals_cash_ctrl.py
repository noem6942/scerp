'''
accounting/signals_cash_ctrl.py
'''
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from scerp.exceptions import APIRequestError
from scerp.mixins import read_yaml_file
from . import models, connector_cash_ctrl_new as conn


# Refresh Time:
#   if cashCtrl signals has received within this time assume no other update
#   necessary
MIN_REFRESH_TIME = 5  # seconds


# Helpers
def create_instance(setup_instance, api_class, data, **kwargs):
    # created_by
    request = kwargs.get('request')
    created_by = request.user if request else setup_instance.created_by

    # Create instance
    return api_class.objects.create(
        **data,
        setup=setup_instance,
        tenant=setup_instance.tenant,
        created_by=created_by)


def sent_to_cash_ctrl(instance):
    ''' check if sending is necessary '''
    if instance.last_received:
        diff = timezone.now() - instance.last_received
        return diff.seconds > MIN_REFRESH_TIME
    return True


def handle_cashctrl_signal(cls, instance, action, created=None):
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
@receiver(post_save, sender=models.APISetup)
def api_setup_post_save(sender, instance, created, **kwargs):
    '''Post action for APISetup:
        - init accounting instances
    '''
    # Init
    yaml_filename = 'init_setup.yaml'

    if created:
        # Open yaml
        init_data = read_yaml_file('accounting', yaml_filename)

        # Create CustomFieldGroups
        for data in init_data['CustomFieldGroup']:
            new_instance = create_instance(
                instance, models.CustomFieldGroup, data, **kwargs)
            handle_cashctrl_signal(
                conn.CustomFieldGroup, new_instance, 'save', created)

        # Create CustomFields
        for data in init_data['CustomField']:
            new_instance = create_instance(
                instance, models.CustomField, data, **kwargs)
            handle_cashctrl_signal(
                conn.CustomField, new_instance, 'save', created)


# cashCtrl classes
@receiver(post_save, sender=models.CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''
    if not instance.code and instance.c_id:
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
    handle_cashctrl_signal(
        conn.CustomFieldGroup, instance, 'save', created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    handle_cashctrl_signal(conn.CustomFieldGroup, instance, 'delete')


@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    if not instance.code and instance.c_id:
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
    handle_cashctrl_signal(
        conn.CustomField, instance, 'save', created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    handle_cashctrl_signal(conn.CustomField, instance, 'delete')
