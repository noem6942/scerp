'''
accounting/connector_cash_ctrl_new.py
'''
import logging
from django.utils import timezone

from crm.models import AddressPerson, ContactPerson
from scerp.exceptions import APIRequestError
from scerp.mixins import make_timeaware
from . import api_cash_ctrl
from .models import (
    APISetup, TOP_LEVEL_ACCOUNT, Allocation,
    CustomField as model_CustomField,
    Account as model_Account,
    Title as model_Titel
)

logger = logging.getLogger(__name__)  # Using the app name for logging

# Helpers
TOP_LEVEL_NUMBERS = [x.value for x in TOP_LEVEL_ACCOUNT]

class IGNORE:
    ''' keys not be sent to cashCtrl '''
    BASE =  [
        'id', 'created_at', 'created_by_id', 'modified_at', 'modified_by_id',
        'attachment', 'version_id', 'is_protected', 'tenant_id',
        'c_id', 'c_created', 'c_created_by', 'c_last_updated',
        'c_last_updated_by', 'setup_id', 'message', 'is_enabled_sync',
        'last_received', 'sync_to_accounting'
    ]
    IS_INACTIVE = ['is_inactive']
    NOTES = ['notes']
    CODE = ['code']


# Handle synchronization with cashCtrl, overall class ------------------------
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

    def init_custom_fields(self, model):
        # Init
        custom_fields = getattr(model, 'CUSTOM', [])
        custom = {}

        # Parse fields
        for field_name, custom_field__code in custom_fields:
            # Get field instance
            custom_field = model_CustomField.objects.filter(
                tenant=self.setup.tenant, code=custom_field__code).first()

            # Assign
            if custom_field:
                custom[field_name] = custom_field.custom_field_key
            else:
                msg = f"custom field {custom_field__code} not existing."
                raise ValueError(msg)

        return custom

    def upload_prepare(self, instance):
        '''
        Copy values from self.instance to data to be sent to cashCtrl
        do not send self.ignore_keys
        '''
        # Init customfields
        self.custom = self.init_custom_fields(instance)

        # Copy values
        data = {}
        for key, value in instance.__dict__.items():
            # skip django internal keys and ignore_keys
            if key[0] != '_' and key not in self.ignore_keys:
                data[key] = getattr(instance, key)

        # Convert CustomFields
        if self.custom:
            data['custom'] = {
                key_cash_ctrl: data.pop(field_name, None)
                for field_name, key_cash_ctrl in self.custom.items()
            }

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
            if key in ['start', 'end']:
                data[key] = make_timeaware(value)
            elif key == 'custom' and data['custom']:
                custom = data.pop('custom')
                for field_name, key_cash_ctrl in self.custom.items():
                    data[field_name] = custom.pop(key_cash_ctrl)
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

        # Prevent triggering any signals
        instance.sync_to_accounting = False

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
        self.custom = self.init_custom_fields(model)
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
            try:
                instance.save()
            except:
                raise ValueError(f"cannot save {instance}")

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
            foreign_key_class):
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
        return
        for round in ['get from existing', 'load categories']:
            category = related_model.objects.filter(c_id=category_id).first()
            setattr(instance, field_name, category)
            if category:
                return

            # Load it
            handler = foreign_key_class(self.setup, self.user)
            handler.load(related_model, round=round + 1)

            if category:  # If it was created, stop looping
                return

        logger.warning("no category found")

    # C(R)UD
    def close_transaction(self, instance, response):
        # Close the transaction

        # Prevent further signals
        instance.sync_to_accounting = False

        # Save
        if response.get('success', False):
            instance.c_id = response['insert_id']
        instance.save()

        # Raise Error if cashCtrl error
        if not instance.c_id:
            raise ValueError(response)

    def create(self, instance):
        # Send to cashCtrl
        data = self.upload_prepare(instance)
        response = self.handler.create(data)
        self.close_transaction(instance, response)

    def update(self, instance):
        # Send to cashCtrl
        data = self.upload_prepare(instance)
        response = self.handler.update(data)
        self.close_transaction(instance, response)

    def delete(self, instance):
        response = self.handler.delete(instance.c_id)

        # Prevent further signals
        instance.sync_to_accounting = False
        instance.save()

        if not response.get('success', False):
            raise ValueError(response)


# Handle synchronization with cashCtrl, individual classes -------------------
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
    ignore_keys = IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.CODE + ['group']
    type_filter = api_cash_ctrl.FIELD_TYPE

    def pre_upload(self, instance, data):
        # Prepare group_id
        if not getattr(instance, 'group'):
            raise ValueError(f"{data}: no group given")
        data['group_id'] = instance.group.c_id

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # code
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"

        # group
        foreign_key_class = CustomFieldGroup
        self.update_category(
            instance, source, assign, created, 'group', foreign_key_class)


class Location(cashCtrl):
    api_class = api_cash_ctrl.Location
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)


class FiscalPeriod(cashCtrl):
    api_class = api_cash_ctrl.FiscalPeriod
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)


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
        foreign_key_class = CostCenterCategory
        self.update_category(
            instance, source, assign, created, 'parent', foreign_key_class)


class CostCenter(cashCtrl):
    api_class = api_cash_ctrl.AccountCostCenter
    ignore_keys = IGNORE.BASE

    def pre_upload(self, instance, data):
        # Prepare category_id
        if getattr(instance, 'category', None):
            data['category_id'] = instance.category.c_id

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_class = CostCenterCategory
        self.update_category(
            instance, source, assign, created, 'category', foreign_key_class)


class AccountCategory(cashCtrl):
    api_class = api_cash_ctrl.AccountCategory
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + ['top'])

    @staticmethod
    def add_numbers(name, number):
        if number:
            return f"{int(number)} {name}"
        return name

    @staticmethod
    def skip_numbers(name):
        if name and ' ' in name:
            number, text = name.split(' ', 1)
            if number.isnumeric():
                return text
        return name

    def pre_upload(self, instance, data):
        # Prepare parent_id
        if getattr(instance, 'parent', None):
            data['parent_id'] = instance.parent.c_id
        else:
            data.pop('parent_id')

        # Encode numbers in headings
        if self.setup.encode_numbers and not instance.is_top_level_account:
            # Add numbers
            data['name'] = {
                language: self.add_numbers(value, data['number'])
                for language, value in data['name'].items()
            }

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # Decode numbers in headings
        if self.setup.encode_numbers:
            # Skip numbers
            if type(instance.name) == dict:
                name_dict = {
                    language: self.skip_numbers(value)
                    for language, value in instance.name.items()
                }
                instance.name = name_dict

        # parent
        foreign_key_class = AccountCategory
        self.update_category(
            instance, source, assign, created, 'parent', foreign_key_class)


class Account(cashCtrl):
    api_class = api_cash_ctrl.Account
    ignore_keys = IGNORE.BASE + ['top']

    def pre_upload(self, instance, data):
        # Prepare category_id
        data['category_id'] = instance.category.c_id

        # Currency
        if instance.currency.is_default:
            data.pop('currency_id')  # otherwise account has multi currencies
        else:
            data['currency_id'] = instance.currency.c_id

        # Allocations
        allocations = Allocation.objects.filter(account__id=instance.id)
        data['allocations'] = [{
            'share': float(allocation.share),
            'toCostCenterId': allocation.to_cost_center.c_id,
        } for allocation in allocations.all()]

        # Tax
        data.pop('tax_c_id', None)

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_class = AccountCategory
        self.update_category(
            instance, source, assign, created, 'category', foreign_key_class)


class Tax(cashCtrl):
    api_class = api_cash_ctrl.Tax
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)

    def pre_upload(self, instance, data):
        # account
        if getattr(instance, 'account', None):
            data['account_id'] = instance.account.c_id
        else:
            raise ValueError("No account given.")

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # code
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"

        # account
        foreign_key_class = Account
        self.update_category(
            instance, source, assign, created, 'account', foreign_key_class)


class Rounding(cashCtrl):
    api_class = api_cash_ctrl.Rounding
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)

    def pre_upload(self, instance, data):
        # Prepare account_id
        if getattr(instance, 'account', None):
            data['account_id'] = instance.account.c_id
        else:
            data.pop('account_id')

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # parent
        foreign_key_class = Account
        self.update_category(
            instance, source, assign, created, 'account', foreign_key_class)


class Setting(cashCtrl):
    api_class = api_cash_ctrl.Setting
    ignore_keys = IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES

    def create(self, instance=None):
        raise ValueError("Can't create new instances for settings")

    def load(
            self, model, params={}, delete_not_existing=False,
            **filter_kwargs):
        # Fetch data directly
        round = filter_kwargs.pop('round', 1)
        if round > 2:
            return  # prevent recursion

        data = self.handler.read()
        data.update({
            'c_id': 1,  # always
            'setup': self.setup,
            'tenant': self.setup.tenant,
            'created_by': self.user,
            'modified_at': timezone.now(),
            'modified_by': self.user
        })

        # Add Accounts
        model_keys = [field.name for field in model._meta.get_fields()]
        for key, value in data.items():
            if key not in model_keys:
                continue
            if key.endswith('_account_id'):
                data[key] = model_Account.objects.filter(
                    setup=self.setup, c_id=value).first()

        # Save Settings
        instance, _created = model.objects.update_or_create(
            setup=self.setup, c_id=data.pop('c_id'), defaults=data)


class Title(cashCtrl):
    api_class = api_cash_ctrl.PersonTitle
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES + IGNORE.CODE)

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"


class PersonCategory(cashCtrl):
    api_class = api_cash_ctrl.PersonCategory
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
        # code
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"

        # parent
        foreign_key_class = PersonCategory
        self.update_category(
            instance, source, assign, created, 'parent', foreign_key_class)


class Person(cashCtrl):
    api_class = api_cash_ctrl.Person
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES)

    @staticmethod
    def make_address(addr):
        value = addr.address.street
        
        if addr.address.house_number:
            value += ' ' + addr.address.house_number
        if addr.address.dwelling_number:
            value += ', ' + addr.address.dwelling_number
            
        if addr.post_office_box:
            value += '\n' + addr.post_office_box
        if addr.additional_information:
            value += '\n' + addr.additional_information            
                    
        return value

    def pre_upload(self, instance, data):
        # Prepare catgory_id
        if getattr(instance, 'category', None):
            data['category_id'] = instance.category.c_id
        else:
            raise ValueError("No catgory given.")

        # Prepare title_id
        if getattr(instance, 'title', None):
            title_id = data.pop('title_id')
            data['title_id'] = model_Titel.objects.get(id=title_id).c_id
        else:
            data.pop('title_id')

        # Prepare superior_id
        if getattr(instance, 'superior', None):
            data['superior_id'] = instance.superior.c_id
        else:
            data.pop('superior_id')

        # Make contacts
        person_id = data.pop('person_ptr_id')
        contacts = ContactPerson.objects.filter(person__id=person_id)
        data['contacts'] = [{
            'type': contact.type,
            'address': contact.address
        } for contact in contacts.order_by('id')]

        # Make addresses, map ech --> cashCtrl
        addresses = AddressPerson.objects.filter(person__id=person_id)
        data['addresses'] = [{
            'type': addr.type,
            'address': self.make_address(addr),
            'city': addr.address.town,
            'country': addr.address.country.alpha3,
            'zip': addr.address.zip
        } for addr in addresses.order_by('id')]

        print("*data", data)

    def load(self, model, **kwargs):
        raise ValueError("Load not defined for Person")


class OrderCategory(cashCtrl):
    api_class = api_cash_ctrl.OrderCategory
    ignore_keys = (
        IGNORE.BASE + IGNORE.IS_INACTIVE + IGNORE.NOTES)

    def pre_upload(self, instance, data):
        # account
        if getattr(instance, 'account', None):
            data['account_id'] = instance.account.c_id
        else:
            raise ValueError("No account given.")

    def post_get(self, instance, source, assign, created):
        __ = instance, created
        # code
        if created:
            # Fill out empty code
            instance.code = f"custom {source['id']}"

        # account
        foreign_key_class = Account
        self.update_category(
            instance, source, assign, created, 'account', foreign_key_class)


# Handler for signals_cash_ctrl ---------------------------------------------
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
        self.setup = instance if model == APISetup else instance.setup
        self.api_class = api_class
        self.language = language
        self.handler = self.api_class(self.setup, language=self.language)
        # time.sleep(5)

    def save(self, created=False):
        """
        Handles the 'save' action (create or update).

        :param created: Boolean indicating if this is a new instance.
        """
        if self.instance.is_enabled_sync and self.instance.sync_to_accounting:
            # We only sync it this is True !!!
            if created:
                logger.info(f"Creating record {self.instance} in CashCtrl")
                self.handler.create(self.instance)
            else:
                logger.info(f"Updating record {self.instance} in CashCtrl")
                self.handler.update(self.instance)
            return
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
            return  # nothing to sync

        if getattr(self.instance, 'self.instance.stop_delete', False):
            return

        try:
            self.instance.stop_delete = True
            self.instance.save()
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
        logger.info(f"Fetching data for {self.instance} from CashCtrl")
        self.handler.load(model, params, delete_not_existing, **filter_kwargs)
        return
        try:

            self.handler.load(model, params, delete_not_existing, **filter_kwargs)
        except Exception as e:
            logger.error(
                f"Failed to fetch {self.instance} from CashCtrl: {e}")
            raise APIRequestError(
                f"Failed to fetch data from CashCtrl API: {e}")
