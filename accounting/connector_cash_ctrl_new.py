'''
accounting/connector_cash_ctrl_new.py
'''
import logging
from django.utils import timezone

from core.models import Tenant
from core.safeguards import get_tenant
from scerp.mixins import get_admin, make_timeaware

from . import api_cash_ctrl

logger = logging.getLogger(__name__)  # Using the app name for logging

# Helpers
class IGNORE_KEYS:
    BASE =  [
        '_state', 'id', 'created_at', 'created_by_id', 'modified_at',
        'modified_by_id', 'attachment', 'version_id',
        'is_protected', 'tenant_id', 'c_id', 'c_created', 'c_created_by',
        'c_last_updated', 'c_last_updated_by', 'setup_id'
    ]
    IS_INACTIVE = BASE + ['is_inactive']
    ALL = IS_INACTIVE + ['notes']


class cashCtrl:
    '''Handle synchronization with cashCtrl
    
    Principle:
    - scerp is master:
        * cashCtrl is informed by signals
        * no load after initial load
    - scerp is reader:
        * data is retrieved from cashCtrl
        * not matching data is deleted
        * updates are done if existing        
    '''
    def __init__(self, sender, org_name, api_key, instance, request):
        # From kwargs
        self.model = sender
        self.instance = instance
        self.request = request

        # From instance
        if not org_name or not api_key and instance:
            org_name = instance.setup.org_name
            api_key = instance.setup.api_key

        # Assign handler
        self.handler = self.ctrl(org_name, api_key)
        self.data = {}
        if instance:
            self.tenant = self.instance.setup
            self.init_data()
        else:
            self.tenant = None

    def get_tenant(self):
        # Tenant
        if not self.tenant and self.request:
            self.tenant = Tenant.objects.filter(
                id=get_tenant(self.request).get('id')).first()
        if self.tenant:
            return self.tenant
        raise ValueError('Cannot find tenant')

    def get_user(self):
        if self.request:
            return self.request.user
        else:
            return get_admin()

    def init_data(self):
        # c_id
        if self.instance.c_id:
            self.data['id'] = self.instance.c_id

        # ignore_keys
        if hasattr(self, 'ignore_keys'):
            for key, value in self.instance.__dict__.items():
                if key not in self.ignore_keys:
                    self.data['key'] = value

        # json_fields
        if hasattr(self, 'json_fields'):
            for field in self.json_fields:
                json_data = getattr(self.instance, field, None)
                if json_data:
                    self.data[field] = dict(values=json_data)

    def load(self, delete_not_existing=True):
        # Get from cashCtrl
        created, updated, deleted = 0, 0, 0
        data_list = self.handler.list()
        c_ids = [x['id'] for x in data_list]        
        
        tenant = self.get_tenant()
        queryset = self.model.objects.filter(tenant=tenant)
        
        # Delete instances not matching       
        if delete_not_existing:        
            deleted = queryset.exclude(c_id__in=c_ids).delete()
                    
        # Prepare data
        model_keys = self.model.__dict__.keys()

        # Parse
        for data in data_list:
            # Handle cashCtrl specials
            try:
                data.update({
                    'c_id': data.pop('id'),
                    'c_created': make_timeaware(data.pop('created')),
                    'c_created_by': data.pop('created_by'),
                    'c_last_updated': make_timeaware(data.pop('last_updated')),
                    'c_last_updated_by': data.pop('last_updated_by'),
                })
            except KeyError as e:
                # Log or handle the missing key error
                raise KeyError(f"Missing required field in data: {e}")

            # Convert data, remove keys not needed
            for key in list(data.keys()):
                if key in ['start', 'end']:
                    data[key] = make_timeaware(data[key])
                elif key not in model_keys:
                    data.pop(key)

        # Update
        queryset = queryset.filter(c_id__in=c_ids)
        for instance in queryset.all():
            # prepare
            data = next(x for x in data_list if x['c_id'] == instance.c_id)
            data.update({
                'modified_by': self.get_user(),
                'modified_at': timezone.now()
            })
            
            # save
            for key, value in data.items():
                setattr(instance, key, value)
            instance.save()
            c_ids.remove(data['c_id'])
            updated += 1
    
        # Create
        for c_id in c_ids:
            # prepare
            data = next(x for x in data_list if x['c_id'] == c_id)
            data.update({
                'tenant': tenant,
                'created_by': self.get_user(),
                'created_at': timezone.now()
            })
            _instance = self.model.objects.create(**data)
            created += 1

        # Message                
        logger.info(
            f'{self.model}: updated {updated}, created {created}, '
            f'deleted {deleted}')

    def create(self):
        print("*++++++++++++++")
        # Send to cashCtrl
        response = self.handler.create(self.data)
        if response.get('success', False):
            self.instance.c_id = response['insert_id']
        else:
            raise ValueError(response)

    def update(self):
        # Send to cashCtrl
        response = self.handler.create(self.data)
        if not response.get('success', False):
            raise ValueError(response)

    def delete(self, c_id):
        response = self.handler.delete(c_id)
        if not response.get('success', False):
            raise ValueError(response)


class CustomFieldGroup(cashCtrl):
    ctrl = api_cash_ctrl.CustomFieldGroup
    json_fields = ['name']

    def __init__(
            self, sender, org_name=None, api_key=None, instance=None,
            request=None):
        super().__init__(sender, org_name, api_key, instance, request)
        if instance:
            self.data.update({
                'type': instance.type
            })


class CustomField(cashCtrl):
    ctrl = api_cash_ctrl.CustomField
    ignore_keys = IGNORE_KEYS.IS_INACTIVE + ['code', 'group_ref', 'group_id']
    json_fields = ['name', 'description']

    def __init__(
            self, sender, org_name=None, api_key=None, instance=None,
            request=None):
        super().__init__(sender, org_name, api_key, instance, request)
        if instance:
            self.data.update({
                'group_id': instance.group.c_id,
                'type': instance.group.type,
                'data_type': instance.type,
            })
