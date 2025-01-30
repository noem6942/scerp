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
        'c_last_updated_by', 'setup_id', 'message', 'is_enabled_sync',
        'last_received'
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
        :setup: needed for get
        :user: needed for get
        :language: cashCtrl api language, use None (i.e. 'en' for most cases)

    Properties
        :api_class: define class in api_cash_ctrl
        :json_fields: convert into cashCtrl values
        :ignore_keys: do not **upload** these key values to cashCtrl
        :type_filter(Enum): Needed to get type specific classes, .i.e.
            - api_cash_ctrl.FIELD_TYPE for CustomField and CustomFieldGroup
        :delete_not_existing
            the data is freshly loaded from cashCtrl, delete all non
            matching items in scerp; use with caution!
    '''
    def __init__(self, setup, user=None, language=None):
        # Init data
        self.setup = setup
        self.user = user

        # Get data
        self.model = None
        self.model_keys = None

        # Assign handler
        self.handler = self.api_class(
            self.setup.org_name, self.setup.api_key, language)

    def upload_prepare(self, instance):
        '''
        Copy values from self.instance to data to be sent to cashCtrl
        do not send self.ignore_keys
        '''
        # Copy values
        data = {}
        for key, value in instance.__dict__.items():
            if key not in self.ignore_keys:
                data[key] = getattr(instance, key)

        # Clean
        if getattr(self, 'pre_upload', None):
            self.pre_upload(instance, data)

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

    def convert_source_data(self, data):
        # Handle cashCtrl specials
        try:
            data.update({
                'c_id': data.pop('id'),
                'c_created': make_timeaware(data.pop('created')),
                'c_created_by': data.pop('created_by'),
                'c_last_updated': make_timeaware(data.pop('last_updated')),
                'c_last_updated_by': data.pop('last_updated_by'),
                'last_received': timezone.now(),  # important for signals.py!
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
            elif key not in self.model_keys:
                data.pop(key)

    def update_or_create_instance(self, source, assign, instance=None):
        # What to do
        do_create = instance is None

        # Create or update instance
        if do_create:
            instance = self.model(
                setup=self.setup,
                tenant=self.setup.tenant,
                created_by=self.user,
                modified_at=timezone.now()  # set to check for trigger
            )
        else:
            instance.modified_by = self.user

        # Add data
        for key in instance.__dict__.keys():
            if key in assign:
                setattr(instance, key, assign[key])

        # Clean
        if getattr(self, 'post_get', None):
            self.post_get(instance, source, assign, created=do_create)

        return instance

    def load(
            self, model, params={}, delete_not_existing=False,
            **filter_kwargs):
        # Init
        self.model = model
        self.model_keys = [field.name for field in model._meta.get_fields()]
        created, updated, deleted = 0, 0, 0

        # Check init
        if not self.setup:
            raise ValueError("No Setup given.")
        elif not self.user:
            raise ValueError("No User given.")

        # Load data
        raw_data = self.get_data(params, **filter_kwargs)
        if not raw_data:
            return

        # Assign data
        data_list = {
            'source': {x['id']: dict(x) for x in raw_data},
            'assign': {x['id']: x for x in raw_data}
        }
        c_ids = list(data_list['source'].keys())

        # Delete instances not matching
        if delete_not_existing:
            deleted = model.objects.filter(
                setup=self.setup).exclude(c_id__in=c_ids).delete()

        # Parse
        for data in data_list['assign'].values():
            self.convert_source_data(data)

        # Update
        queryset = model.objects.filter(setup=self.setup, c_id__in=c_ids)
        for instance in queryset.all():
            # Update instance
            source = data_list['source'][instance.c_id]
            assign = data_list['assign'][instance.c_id]
            instance = self.update_or_create_instance(source, assign, instance)
            instance.save()

            # Maintenance
            c_ids.remove(source['id'])
            updated += 1

        # Create
        for c_id in c_ids:
            # Create instance
            source = data_list['source'][c_id]
            assign = data_list['assign'][c_id]
            instance = self.update_or_create_instance(source, assign)
            instance.save()

            # Maintenance
            created += 1

        # Message
        logger.info(
            f'{model}: updated {updated}, created {created}, deleted {deleted}')

    def update_category(
            self, instance, source, assign, created, field_name,
            foreign_key_model):
        ''' used for uploading categories from cashCtrl '''
        # init
        __ = assign, created
        category_id = source[f"{field_name}_id"]

        if not category_id:
            return  # no category to assign

        # check for change
        category = getattr(instance, field_name, None)
        if category and category.c_id == category_id:
            return

        # Get model of foreign key
        related_model = instance._meta.get_field(field_name).related_model

        # check for new
        for round in ['get from existing', 'load categories']:
            category = related_model.objects.filter(c_id=category_id).first()
            setattr(instance, field_name, category)
            if category:
                return

            # Load it
            handler = foreign_key_model(self.setup, self.user)
            handler.load(related_model)

        logger.warning("no category found")

    # C(R)UD
    def create(self, instance):
        # Send to cashCtrl
        data = self.upload_prepare(instance)
        print("*data", data)
        response = self.handler.create(data)
        if response.get('success', False):
            instance.c_id = response['insert_id']
            instance.save()
            return instance
        raise ValueError(response)

    def update(self, instance):
        # Send to cashCtrl
        data = self.upload_prepare(instance)
        response = self.handler.update(data)
        if response.get('success', False):
            return response['insert_id']
        raise ValueError(response)

    def delete(self, instance):
        response = self.handler.delete(instance.c_id)
        if not response.get('success', False):
            raise ValueError(response)


class CustomFieldGroup(cashCtrl):
    api_class = api_cash_ctrl.CustomFieldGroup
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)
    type_filter = api_cash_ctrl.FIELD_TYPE

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"


class CustomField(cashCtrl):
    api_class = api_cash_ctrl.CustomField
    ignore_keys = IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.CODE + [
        'group', 'group_ref']
    type_filter = api_cash_ctrl.FIELD_TYPE

    def pre_upload(self, instance, data):
        # Prepare group_id
        data['group_id'] = instance.group.c_id

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # code
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"

        # group
        foreign_key_model = CustomFieldGroup
        self.update_category(
            instance, source, assign, created, 'group', foreign_key_model)


class Location(cashCtrl):
    pass


class Currency(cashCtrl):
    api_class = api_cash_ctrl.Currency
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)


class SequenceNumber(cashCtrl):
    api_class = api_cash_ctrl.SequenceNumber
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)


class Unit(cashCtrl):
    api_class = api_cash_ctrl.Unit
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)


class CostCenterCategory(cashCtrl):
    api_class = api_cash_ctrl.AccountCostCenterCategory
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES)

    def pre_upload(self, instance, data):
        # Prepare parent_id
        if getattr(instance, 'parent', None):
            data['parent_id'] = instance.parent.c_id
        else:
            data.pop('parent_id')

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_model = CostCenterCategory
        self.update_category(
            instance, source, assign, created, 'parent', foreign_key_model)


class CostCenter(cashCtrl):
    api_class = api_cash_ctrl.AccountCostCenter
    ignore_keys = IGNORE.BASE

    def pre_upload(self, instance, data):
        # Prepare category_id
        data['category_id'] = instance.category.c_id

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_model = CostCenterCategory
        self.update_category(
            instance, source, assign, created, 'category', foreign_key_model)


class AccountCategory(cashCtrl):
    api_class = api_cash_ctrl.AccountCategory
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES)

    def pre_upload(self, instance, data):
        # Prepare parent_id
        if getattr(instance, 'parent', None):
            data['parent_id'] = instance.parent.c_id
        else:
            data.pop('parent_id')

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_model = AccountCategory
        self.update_category(
            instance, source, assign, created, 'parent', foreign_key_model)


class Account(cashCtrl):
    pass


class Tax(cashCtrl):
    pass


class Rounding(cashCtrl):
    api_class = api_cash_ctrl.Rounding
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE )

    def pre_upload(self, instance, data):
        # Prepare account_id
        if getattr(instance, 'account', None):
            data['account_id'] = instance.account.c_id
        else:
            data.pop('account_id')

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_model = Account
        self.update_category(
            instance, source, assign, created, 'account', foreign_key_model)



class Title(cashCtrl):
    api_class = api_cash_ctrl.PersonTitle
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"
