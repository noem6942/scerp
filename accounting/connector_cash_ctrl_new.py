'''
accounting/connector_cash_ctrl_new.py
'''
import logging
from django.utils import timezone

from scerp.mixins import make_timeaware
from . import api_cash_ctrl


logger = logging.getLogger(__name__)  # Using the app name for logging

# Helpers
class IGNORE:
    ''' keys not be sent to cashCtrl '''
    BASE =  [
        '_state', 'id',
        'created_at', 'created_by_id', 'modified_at', 'modified_by_id',
        'attachment', 'version_id', 'is_protected', 'tenant_id',
        'c_id', 'c_created', 'c_created_by', 'c_last_updated',
        'c_last_updated_by', 'setup_id', 'message', 'is_enabled_sync'
    ]
    IS_INACTIVE = ['is_inactive']
    NOTES = ['notes']
    CODE = ['code']


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
        :org_name: cashCtrl org_name
        :api_key: cashCtrl api_key

    Properties
        :api_class: define class in api_cash_ctrl
        :json_fields: convert into cashCtrl values
        :ignore_keys_post: do not upload these key values to cashCtrl
        :ignore_keys_get: do not download these key from cashCtrl as they are
            used differently in cashCtrl (foreign keys)
        :type_filter(Enum): Needed to get type specific classes, .i.e.
            - api_cash_ctrl.FIELD_TYPE for CustomField and CustomFieldGroup
        :delete_not_existing
            the data is freshly loaded from cashCtrl, delete all non
            matching items in scerp; use with caution!
    '''
    def __init__(self, org_name, api_key):
        # Assign handler
        self.handler = self.api_class(org_name, api_key)

    def prepare_data(self, instance):
        '''
        Copy values from self.instance to data to be sent to cashCtrl
        self.ignore_keys_post:
        if ignore_keys_post are given we copy all values of the data
        except self.ignore_keys_post
        '''
        # Copy values
        data = {}
        for key, value in instance.__dict__.items():
            if key not in self.ignore_keys_post:
                data[key] = value

        # Add id if existing
        if instance.c_id:
            data['id'] = instance.c_id

        return data

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

    def load(
            self, model, tenant, user, params={}, delete_not_existing=False,
            **filter_kwargs):
        # Init
        created, updated, deleted = 0, 0, 0

        # Load data
        data_list = self.get_data(params, **filter_kwargs)
        c_ids = [x['id'] for x in data_list]

        # Delete instances not matching
        if delete_not_existing:
            deleted = model.objects.filter(
                tenant=tenant).exclude(c_id__in=c_ids).delete()

        # Check
        if not data_list:
            return

        # Parse
        model_keys = model.__dict__.keys()
        for data in data_list:
            # Handle cashCtrl specials
            try:
                data.update({
                    'c_id': data.pop('id'),
                    'c_created': make_timeaware(data.pop('created')),
                    'c_created_by': data.pop('created_by'),
                    'c_last_updated': make_timeaware(data.pop('last_updated')),
                    'c_last_updated_by': data.pop('last_updated_by'),
                    'last_received': timezone.now(),
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
        queryset = model.objects.filter(tenant=tenant, c_id__in=c_ids)
        for instance in queryset.all():
            # prepare
            data = next(x for x in data_list if x['c_id'] == instance.c_id)
            data['modified_by'] = user

            # save
            for key, value in data.items():
                # copy data to instance but skip foreign key typically ending
                # with _id
                if key == 'c_id' or not key.string.endswith('_id'):
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
                'created_by': user,
                'modified_at': timezone.now()  # set to check for trigger
            })
            _instance = model.objects.create(**data)
            created += 1

        # Message
        logger.info(
            f'{model}: updated {updated}, created {created}, deleted {deleted}')

    def create(self, instance):
        # Send to cashCtrl
        response = self.handler.create(self.prepare_data(instance))
        if response.get('success', False):
            return response['insert_id']
        raise ValueError(response)

    def update(self, instance):
        # Send to cashCtrl
        response = self.handler.update(self.prepare_data(instance))
        if response.get('success', False):
            return response['insert_id']
        raise ValueError(response)

    def delete(self, instance):
        response = self.handler.delete(instance.c_id)
        if not response.get('success', False):
            raise ValueError(response)


class CustomFieldGroup(cashCtrl):
    api_class = api_cash_ctrl.CustomFieldGroup
    ignore_keys_post = IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE
    type_filter = api_cash_ctrl.FIELD_TYPE


class CustomField(cashCtrl):
    api_class = api_cash_ctrl.CustomField
    ignore_keys_post = IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.CODE + [
        'group', 'group_ref', 'group_id']
    ignore_keys_get = ['group_id']
    type_filter = api_cash_ctrl.FIELD_TYPE
