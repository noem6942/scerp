'''
accounting/signals_cash_ctrl.py
'''
from django.db import IntegrityError
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


def received_from_cash_ctrl(instance):
    ''' check if sending is necessary '''
    if instance.last_received:
        diff = timezone.now() - instance.last_received
        return diff.seconds > MIN_REFRESH_TIME
    return True


def handle_cash_ctrl_signal(
        api_class, instance, action, created=None, model=None):
    '''
    Generic handler for CustomField-related signals.

    This function performs actions based on the specified signal type
    (create, update, delete).

    :api_class: connector_cash_ctrl class
    :param instance: The model instance being affected by the signal.
    :param action: The action to perform - one of 
                    'create', 'update', 'delete', 'get'.
    '''
    if not instance.is_enabled_sync:
        return  # sync is turned off for this record

    handler = api_class(instance.setup.org_name, instance.setup.api_key)
    #try:
    if action == 'save':
        # If record has been updated
        if not received_from_cash_ctrl(instance):
            if created:
                instance.c_id = handler.create(instance)
                instance.save()
            else:
                handler.update(instance)
    elif action == 'delete' and instance.c_id:
        handler.delete(instance)
    elif action == 'get':
        user = (
            instance.modified_by if instance.modified_by
            else instance.created_by)
        handler.load(model, instance.tenant, self.user)
    #except:
    #    raise APIRequestError("Failed to send data to the API.")


def handle_cashctrl_check_category(
        api_class, model, instance, field_name='category'):
    ''' 
    assign category and reload if no category found 
    
    :api_class: api class of foreign key
    :model: model of foreign key
    :field_name: field_name of foreign key
    '''
    if not getattr(instance, field_name, None):
        # Fix category
        category = models.CostCenterCategory.objects.filter(
            c_id=instance.c_id).first()

        if not category:
            # Load categories from cashCtrl
            handle_cash_ctrl_signal(api_class, instance, 'get', model)
            category = model.objects.filter(
                setup=instance.setup, c_id=instance.c_id).first()

        if category:
            # Save
            instance.category = category
            instance.save()

# Signal Handlers
# These handlers connect the appropriate signals to the helper functions.

# APISetup
def assign_setup(instance):
    if not getattr(instance, 'setup', None):
        # Query the default value
        default_value = models.APISetup.objects.filter(
            tenant=instance.tenant, is_default=True).first()
        if not default_value:
            raise IntegrityError(f"No default_value for {self.org_name}")
        instance.setup = default_value


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

        # Create objects, that fire then signals to cashCtrl

        # Create CustomFieldGroups
        for data in init_data['CustomFieldGroup']:
            new_instance = create_instance(
                instance, models.CustomFieldGroup, data, **kwargs)

        # Create CustomFields
        for data in init_data['CustomField']:
            new_instance = create_instance(
                instance, models.CustomField, data, **kwargs)


# cashCtrl classes

# CustomFieldGroup
@receiver(pre_save, sender=models.CustomFieldGroup)
def custom_field_group_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CustomFieldGroup. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.CustomFieldGroup)
def custom_field_group_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomFieldGroup. '''
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
        instance.save()
    handle_cash_ctrl_signal(
        conn.CustomFieldGroup, instance, 'save', created)


@receiver(pre_delete, sender=models.CustomFieldGroup)
def custom_field_group_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomFieldGroup. '''
    handle_cash_ctrl_signal(conn.CustomFieldGroup, instance, 'delete')


# CustomField
@receiver(pre_save, sender=models.CustomField)
def custom_field_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CustomFieldGroup. '''
    # Assign setup if necessary
    assign_setup(instance)

    # Check group_ref
    if getattr(instance, 'group', None):
        # Assing type from group
        instance.type = instance.group.type
    else:
        # Get group from group_ref
        instance.group = models.CustomFieldGroup.objects.filter(
            setup=instance.setup, code=instance.group_ref).first()
        if instance.group:
            instance.type = self.instance.type
        else:
            raise IntegrityError(
                f"No CustomFieldGroup with code '{self.group_ref}'")


@receiver(post_save, sender=models.CustomField)
def custom_field_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CustomField. '''
    # Align category if necessary
    handle_cashctrl_check_category(
        conn.CustomFieldGroup, models.CustomFieldGroup, instance, 'group')    
    
    # Align code if necessary
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
        instance.save()    
    
    # Send to cashCtrl if necessary
    handle_cash_ctrl_signal(conn.CustomField, instance, 'save', created)


@receiver(pre_delete, sender=models.CustomField)
def custom_field_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CustomField. '''
    handle_cash_ctrl_signal(conn.CustomField, instance, 'delete')

"""
# Currency
@receiver(pre_save, sender=models.Currency)
def currency_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on Currency. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.Currency)
def currency_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Currency. '''
    handle_cash_ctrl_signal(conn.Currency, instance, 'save', created)


@receiver(pre_delete, sender=models.Currency)
def currency_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Currency. '''
    handle_cash_ctrl_signal(conn.Currency, instance, 'delete')


# CostCenterCategory
@receiver(pre_save, sender=models.CostCenterCategory)
def cost_center_category_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CostCenterCategory. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.CostCenterCategory)
def cost_center_category_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenterCategory. '''
    handle_cash_ctrl_signal(conn.CostCenterCategory, instance, 'save', created)


@receiver(pre_delete, sender=models.CostCenterCategory)
def cost_center_category_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenterCategory. '''
    handle_cash_ctrl_signal(conn.CostCenterCategory, instance, 'delete')


# CostCenter
@receiver(pre_save, sender=models.CostCenter)
def cost_center_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on CostCenterCategory. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.CostCenter)
def cost_center_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on CostCenter. '''
    # Align category if necessary
    handle_cashctrl_check_category(
        conn.CostCenterCategory, models.CostCenterCategory, instance)    
    
    # Align code if necessary
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = str(instance.c_id)
        instance.save()
    
    # Send to cashCtrl if necessary
    handle_cash_ctrl_signal(conn.CustomField, instance, 'save', created)


@receiver(pre_delete, sender=models.CostCenter)
def cost_center_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on CostCenter. '''
    handle_cash_ctrl_signal(conn.CostCenter, instance, 'delete')


# Tax
@receiver(pre_save, sender=models.Tax)
def tax_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on Tax. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.Tax)
def tax_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Tax. '''
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = f"{instance.c_id}, {instance.percentage}"
        instance.save()
    handle_cash_ctrl_signal(conn.Tax, instance, 'save', created)


@receiver(pre_delete, sender=models.Tax)
def tax_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Tax. '''
    handle_cash_ctrl_signal(conn.Tax, instance, 'delete')


# Rounding
@receiver(pre_save, sender=models.Rounding)
def rounding_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on Rounding. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.Rounding)
def rounding_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Rounding. '''
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = f"{self.c_id}, {self.mode}"
        instance.save()
    handle_cash_ctrl_signal(conn.Rounding, instance, 'save', created)


@receiver(pre_delete, sender=models.Rounding)
def rounding_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Rounding. '''
    handle_cash_ctrl_signal(conn.Rounding, instance, 'delete')


# SequenceNumber
@receiver(pre_save, sender=models.SequenceNumber)
def sequence_number_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on SequenceNumber. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.SequenceNumber)
def sequence_number_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on SequenceNumber. '''
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = f"{self.c_id}, {self.mode}"
        instance.save()
    handle_cash_ctrl_signal(conn.SequenceNumber, instance, 'save', created)


@receiver(pre_delete, sender=models.SequenceNumber)
def sequence_number_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on SequenceNumber. '''
    handle_cash_ctrl_signal(conn.SequenceNumber, instance, 'delete')


# Unit
@receiver(pre_save, sender=models.Unit)
def unit_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre signals on Unit. '''
    # Assign setup if necessary
    assign_setup(instance)


@receiver(post_save, sender=models.Unit)
def unit_post_save(sender, instance, created, **kwargs):
    '''Signal handler for post_save signals on Unit. '''
    if not getattr(instance, 'code', None):
        # Record has been created in cashCtrl but not scerp
        instance.code = f"{self.c_id}, {self.name.get('de')}"
        instance.save()
    handle_cash_ctrl_signal(conn.Unit, instance, 'save', created)


@receiver(pre_delete, sender=models.Unit)
def unit_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_delete signals on Unit. '''
    handle_cash_ctrl_signal(conn.Unit, instance, 'delete')
"""