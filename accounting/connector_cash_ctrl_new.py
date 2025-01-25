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

    Params:
        :api_class: define class in api_cash_ctrl
        :json_fields: convert into cashCtrl values
        :ignore_keys: do not upload these key values to cashCtrl
        :type_filter(Enum): Needed to get type specific classes, .i.e.
            - api_cash_ctrl.FIELD_TYPE for CustomField and CustomFieldGroup
        :delete_not_existing
            the data is freshly loaded from cashCtrl, delete all non
            matching items in scerp; use with caution!

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
        self.handler = self.api_class(org_name, api_key)
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
        '''
        if hasattr(self, 'json_fields'):
            for field in self.json_fields:
                json_data = getattr(self.instance, field, None)
                # if json_data:
                #    self.data[field] = dict(values=json_data)
        '''
        
    def get_data(self, params={}, **filter_kwargs):
        """
        Load data from cashCtrl
        if self.type_filter by querying for each field type and aggregating
        the results.

        :param params: Optional dictionary of parameters to pass to the query.
        :type_filter(Enum): Needed to get type specific classes, .i.e.
            - api_cash_ctrl.FIELD_TYPE for CustomField and CustomFieldGroup
        :return: Aggregated list of data from all field types.
        """
        type_filter = getattr(self, 'type_filter', None)
        if type_filter:
            data_list = []
            # Iterate over each field type and fetch data
            for field_type in type_filter:
                # Ensure the original params remain unaffected
                type_params = {**params, 'type': field_type.value}  # Enum

                # Fetch data for the current field type and append it to the
                # list
                data_list += self.handler.list(type_params, **filter_kwargs)
        else:
            data_list = self.handler.list(params, **filter_kwargs)
        return data_list

    def load(self, params={}, delete_not_existing=False, **filter_kwargs):
        # Init
        created, updated, deleted = 0, 0, 0

        # Load data
        data_list = self.get_data(params, **filter_kwargs)
        c_ids = [x['id'] for x in data_list]
        tenant = self.get_tenant()

        # Delete instances not matching
        if delete_not_existing:
            deleted = queryset.filter(
                tenant=tenant).exclude(c_id__in=c_ids).delete()

        # Check
        if not data_list:
            return

        # Parse
        model_keys = self.model.__dict__.keys()
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
                value = data[key]                
                if isinstance(value, dict) and 'values' in value:
                    # remove "values"
                    data[key] = value['values']
                elif key in ['start', 'end']:
                    data[key] = make_timeaware(value)
                elif key not in model_keys:
                    data.pop(key)

        # Update
        queryset = self.model.objects.filter(tenant=tenant, c_id__in=c_ids)
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
        # Send to cashCtrl
        response = self.handler.create(self.data)
        if response.get('success', False):
            return response['insert_id']
        raise ValueError(response)

    def update(self):
        # Send to cashCtrl
        response = self.handler.create(self.data)
        if response.get('success', False):
            return response['insert_id']
        raise ValueError(response)

    def delete(self, c_id):
        response = self.handler.delete(c_id)
        if not response.get('success', False):
            raise ValueError(response)


class CustomFieldGroup(cashCtrl):
    api_class = api_cash_ctrl.CustomFieldGroup
    json_fields = ['name']
    type_filter = api_cash_ctrl.FIELD_TYPE

    def __init__(
            self, sender, org_name=None, api_key=None, instance=None,
            request=None):
        super().__init__(sender, org_name, api_key, instance, request)
        if instance:
            self.data.update({
                'name': instance.name,
                'type': instance.type
            })


class CustomField(cashCtrl):
    api_class = api_cash_ctrl.CustomField
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
