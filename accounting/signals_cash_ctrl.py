'''
accounting/signals_cash_ctrl.py
'''
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from . import api_cash_ctrl
from .models import CustomFieldGroup, CustomField


# Helpers
class IGNORE_KEYS:
    BASE =  [
        '_state', 'id', 'created_at', 'created_by_id', 'modified_at', 
        'modified_by_id', 'attachment', 'version_id', 
        'is_protected', 'tenant_id', 'c_id', 'c_created', 'c_created_by', 
        'c_last_updated', 'c_last_updated_by', 'setup_id'
    ]
    ALL = BASE + ['notes', 'is_inactive']


class cashCtrl:
    
    def __init__(self, sender, **kwargs):
        # from kwargs
        self.model = sender
        org_name = kwargs.get('org_name')  
        api_key = kwargs.get('api_key')
        
        # from instance
         self.instance = kwargs.get('instance')
         if self.instance:            
            org_name = instance.setup.org_name
            api_key = instance.setup.api_key
                
        self.cls = self.ctrl(org_name, api_key)
        self.data = {}   
        
        # c_id
        if self.instance.c_id:
            data['id'] = c_id
            
        # ignore_keys
        if hasattr(self, 'ignore_keys'):
            self.data = {
                key: value 
                for key, value in instance.__dict__.items()
                if key not in self.ignore_keys
            }
        
        # json_fields
        if hasattr(self, 'json_fields'):
            for field in self.json_fields:
                if isinstance(self.data[field]):
                    value = self.data.pop(field)
                    if value:
                        self.data[field] = dict(values=value)

    def create(self):
        # Send to cashCtrl
        response = group.create(self.data)
        if response.get('success', False):
            self.instance.c_id = response['insert_id']
        else:
            raise ValidationError(response)   

    def update(self):
        # Send to cashCtrl
        response = group.create(self.data)
        if not response.get('success', False):            
            raise ValidationError(response)  


class CustomFieldGroup(cashCtrl):
    ctrl = api_cash_ctrl.CustomFieldGroup
    json_fields = ['name']

    def __init__(self, sender, instance):
        super().__init__(self, sender, instance)
        self.data.update({
            'type': instance.type
        })


class CustomField(cashCtrl):
    ctrl = api_cash_ctrl.CustomField
    ignore_keys = IGNORE_KEYS.ALL + ['code', 'group_ref', 'group_id']
    json_fields = ['name', 'description']
    
    def __init__(self, sender, instance):
        super().__init__(self, sender, instance)    
        data.update({            
            'group_id': instance.group.c_id,
            'type': instance.group.type,
            'data_type': instance.type,
        })


@receiver(pre_save, sender=CustomFieldGroup)       
def custom_field_group_pre_save(sender, instance, **kwargs):
    cls = CustomFieldGroup(sender, instance)
    cls.update() if cls.pk else cls.create()

        
@receiver(pre_save, sender=CustomField)
def custom_field_pre_save(sender, instance, **kwargs):    
    cls = CustomField(sender, instance)
    cls.update() if cls.pk else cls.create()
