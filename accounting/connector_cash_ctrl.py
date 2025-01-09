# accounting/connector_cash_ctrl.py
'''Interface to cashCtrl (and other accounting applications later)
'''
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext as _

from scerp.admin import get_help_text, format_big_number

from .api_cash_ctrl import STANDARD_ACCOUNT
from .connector import (
    DJANGO_KEYS, ConnectorBase, make_timeaware, extract_fields_to_dict)
from . import models
from . import api_cash_ctrl, init_cash_ctrl


logger = logging.getLogger(__name__)  # Using the app name for logging

CASH_CTRL_KEYS = [
    'c_id',
    'c_created',
    'c_created_by',
    'c_last_updated',
    'c_last_updated_by'
]


class Connector(ConnectorBase):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        # Init
        super().__init__(api_setup)

        # Ctrl
        cls = getattr(self, 'CLASS', None)
        self.ctrl = self.init_class(cls) if cls else None
        
    # Helpers
    def init_class(self, cash_ctrl_cls):
        # assign cash control class within api_cash_ctrl
        return cash_ctrl_cls(self.api_setup.org_name, self.api_setup.api_key)    

    def prepare_data(self, data):
        """
        Prepares data by renaming keys and transforming specific fields.

        Args:
            data (dict): The data dictionary to be modified.

        Raises:
            KeyError: If any of the required keys are missing.
        """
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
  
    def get(self):
        '''generic class, pull data from api_class, e.g. Unit
            and store it in the model
        '''
        # Get data
        data_list = self.ctrl.list()

        # Init
        created, updated = 0, 0
        instance = self.model()
        model_keys = instance.__dict__.keys()

        # Parse
        c_ids = []
        for data in data_list:
            # Load basics
            self.prepare_data(data)

            # Convert data, remove keys not needed
            for key in list(data.keys()):
                if key in ['start', 'end']:
                    data[key] = make_timeaware(data[key])
                elif key  not in model_keys:
                    data.pop(key)

            # Add logging info
            self.add_logging(data)

            # Maintenance
            setup = data.pop('setup')
            c_id = data.pop('c_id')
            c_ids.append(c_id)

            # Update or create
            _obj, created = self.model.objects.update_or_create(
                tenant=self.api_setup.tenant, setup=setup, c_id=c_id,
                defaults=data)
            if created:
                created += 1
            else:
                updated += 1

        # Update deleted
        queryset = self.model.objects.filter(
            setup=setup).exclude(c_id__in=c_ids)
        deleted_count, _deleted_objects = queryset.delete()

        # Message
        msg = _('{total} {verbose_name_plural}, updated {updated}, '
                'created {created}, deleted {deleted}')
        logger.info(msg.format(
            verbose_name_plural = self.model._meta.verbose_name_plural,
            total=created + updated + deleted_count,
            created=created, updated=updated, deleted=deleted_count))

        return {
            'created': created, 'updated': updated, 'deleted': deleted_count}


class CustomFieldGroupConn(Connector):
    CLASS = api_cash_ctrl.CustomFieldGroup

    def init(self):
        # Check and create groups
        for group_def in init_cash_ctrl.CUSTOM_FIELD_GROUPS:
            # Get group
            group = self.ctrl.get_from_name(
                group_def['name'], group_def['type'])
            if group:
                msg = _('Group {name} of type {type} already existing.').format(
                    name=group_def['name'], type=group_def['type'])
                logger.warning(msg)
            else:
                # Create group
                data = {
                    'name': dict(values=group_def['name']),
                    'type': group_def['type']
                }
                response = self.ctrl.create(data)

                # Register group
                if response.pop('success', False):
                    self.register(
                        models.MappingId.TYPE.CUSTOM_FIELD_GROUP,
                        group_def['key'], response['insert_id'])  
                else:
                    raise ValueError(
                        f"Could not register field {group_def['type']}.")           

                # Msg
                msg = _("Created group {name} of type {type}.").format(
                    name=group_def['name'], type=group_def['type'])
                logger.info(msg)


class CustomFieldConn(Connector):
    CLASS = api_cash_ctrl.CustomField

    def init(self):
        # Check and create fields
        for field_def in init_cash_ctrl.CUSTOM_FIELDS:
            # Init
            group_key = field_def.pop('group_key')

            # Get group id
            group_id = self.get_mapping_id(
                models.MappingId.TYPE.CUSTOM_FIELD_GROUP, group_key)
            if not group_id:
                raise ValueError(f"Not register group '{group_key}'")

            # Get group type
            type_c = next((
                x['type'] for x in init_cash_ctrl.CUSTOM_FIELD_GROUPS
                if x['key'] == group_key), None)
            if not type_c:
                raise Exception(f"No type for key {group_key} found.")

            # Prepare
            name = dict(values=field_def['name'])
            customfield = self.ctrl.get_from_name(name, type_c)

            if customfield:
                msg = _('Customfield {name} of type {type} in '
                        '{group_name} already existing.')
                msg = msg.format(
                    name=field_def['name'], type=type_c, group_name=name)
                logger.warning(msg)
            else:
                # Create field
                field_def.update({
                    'name': name,
                    'type': type_c,
                    'group_id': group_id
                })
                response = self.ctrl.create(field_def)

                # Register field
                if response.pop('success', False):
                    self.register(
                        models.MappingId.TYPE.CUSTOM_FIELD,
                        field_def['key'], response['insert_id']) 
                else:
                    raise ValueError(f"Could not register field '{name}'")

                # Msg
                msg = _('Created customfield {name} of type {type}')
                msg = msg.format(name=name, type=type_c)
                logger.info(msg)


class PersonConn(Connector):
    CLASS = api_cash_ctrl.Person
    # later MODEL = models.Person
    
    def init(self):
        # Init
        ctrl = self.init_class(api_cash_ctrl.PersonCategory)
        
        # Add new categories
        for category in init_cash_ctrl.PERSON_CATEGORIES:
            response = ctrl.create(category)
            if response.pop('success', False):
                self.register(
                    models.MappingId.TYPE.PERSON_CATEGORY,
                    category['key'], response['insert_id'])  
            else:
                raise ValueError(f"Could not register field '{key}'")                    


# reading classes
class CostCenterConn(Connector):
    CLASS = api_cash_ctrl.AccountCostCenter
    MODEL = models.CostCenter
    

class CurrencyConn(Connector):
    CLASS = api_cash_ctrl.Currency
    MODEL = models.Currency


class FiscalPeriodConn(Connector):
    CLASS = api_cash_ctrl.FiscalPeriod
    MODEL = models.FiscalPeriod


class LocationConn(Connector):
    CLASS = api_cash_ctrl.Location
    MODEL = models.Location


class TaxPeriodConn(Connector):
    CLASS = api_cash_ctrl.Tax
    MODEL = models.Tax


class ArticleConn(Connector):
    CLASS = api_cash_ctrl.Article
    MODEL = models.Article


class SettingConn(Connector):
    CLASS = api_cash_ctrl.Setting
    MODEL = models.Setting

    def get(self):
        '''override default get as settings does not return list
        '''
        # Get data
        data = self.add_logging({})
        data['data'] = self.ctrl.read()

        # Update or create   
        updated, created = 0, 0
        _obj, created = self.model.objects.update_or_create(
            tenant=self.api_setup.tenant,
            setup=data.pop('setup'),
            defaults=data)
        if created:
            created += 1
        else:
            updated += 1

        # Message
        msg = _('Settings updated {updated} or created {created}')
        logger.info(msg.format(created=created, updated=updated))

        return {'created': created, 'updated': updated}


class UnitConn(Connector):
    CLASS = api_cash_ctrl.Unit
    MODEL = models.Unit
    
    def init(self):
        units = self.ctrl.list()
        for data in init_cash_ctrl.UNITS:
            if not next((x for x in units if x['name'] == data['name']), None):
                response = self.ctrl.create(data)
                if response.pop('success', False):
                    logger.info(f"created {response}")        
    
def get_all(api_setup):
    CLASSES = [
        CostCenterConn,
        CurrencyConn,
        FiscalPeriodConn,
        TaxPeriodConn,
        SettingConn,
        UnitConn,
        LocationConn,
        ArticleConn
    ]
    
    for cls in CLASSES:
        ctrl = cls(api_setup)
        ctrl.get()


"""
class SettingsConn(Connector):
    CLASS = api_cash_ctrl.Settings
    
    def init(self):
        ''' work
        '''
        data = {
            # General
            'tax_accounting_method': 'AGREED',
            'csv_delimiter': ';',
            'thousand_separator': settings.THOUSAND_SEPARATOR,

            # Standardkonten, Allgemein
            'default_opening_account_id': 37,  # Eröffnungsbilanz
            'default_exchange_diff_account_id': 131,  # Kursdifferenzen
            'default_profit_allocation_account_id': 127,  # Jahresgewinn oder -verlust

            # Standardkonten, Inventar
            'default_inventory_article_revenue_account_id': 42,
            'default_inventory_article_expense_account_id': 45,
            'default_inventory_depreciation_account_id': 28,
            'default_inventory_disposal_account_id': 92,
            'default_inventory_asset_revenue_account_id': 164,

            # Standardkonten, Aufträge
            'default_creditor_account_id': 9,
            'default_debtor_account_id': 4,
            'default_input_tax_adjustment_account_id': 173,
            'default_sales_tax_adjustment_account_id': 174,

            # Sequence Number
            'default_sequence_number_inventory_article': 2,
            'default_sequence_number_inventory_asset': 4,
            'default_sequence_number_journal': 6,
            'default_sequence_number_person': 5,

            # First Steps, set all to True
            'first_steps_account': True,
            'first_steps_currency': True,
            'first_steps_logo': True,
            'first_steps_opening_entries': True,
            'first_steps_pro_demo': True,
            'first_steps_tax_rate': True,
            'first_steps_tax_type': True,
            'first_steps_two_factor_auth': True,

            # Others
            'journal_import_force_sequence_number': False,
            'order_mail_copy_to_me': False,
        }

        response = ctrl.update(data)
        if response.get('success', False):
            logger.info(f"{response['message']}")

    # Get
    def get_settings(self):
        # Get settings
        ctrl = self.init_class(api_cash_ctrl.Setting)
        data = ctrl.read()

        if data:
            obj, created = Setting.objects.update_or_create(
                tenant=self.api_setup.tenant,
                setup=self.api_setup,
                defaults={
                    'data': data,
                    'created_by': self.admin,
                    'modified_by': self.admin
                })
            return obj, created
        else:
            raise Exception("No settings found.")


class LocationCntr(Connector):
    def get(self):
        # Get and update all locations
        count = self._pull_accounting_data(
            api_cash_ctrl.Location, Location)
            
    def save(self, instance, created=False):
        '''not working:
        POST request failed for 'https://test167.cashctrl.com/api/v1/location/create.json': 500 - 500 CashCtrl - 500 Internal Server Error
        '''
        # Prepare
        fields = [
            x for x in instance.__dict__.keys()
            if x not in DJANGO_KEYS and x not in CASH_CTRL_KEYS]
        data = extract_fields_to_dict(instance, fields)
        print("*data", data)
        data.pop('logo_id')
        data.pop('logo_file_id')

        # Send to cashCtrl
        ctrl = self.init_class(api_cash_ctrl.Location)
        if created:
            print("*data**", data)
            item = ctrl.create(data)
        else:
            data['id'] = instance.c_id
            print("*data", data)
            item = ctrl.update(data)
          
        # Process
        if item.pop('success', None):
            logger.info(f"created {item}")            
"""


class Account(Connector):
    CLASS = api_cash_ctrl.Account
    
    # First digits account_number
    TOP_CATEGORY_MAP = {
        # First digits account_number, account_category in data
        1: 'ASSET',
        2: 'LIABILITY',
        3: 'p&l_expense',
        5: 'p&l_revenue',
        4: 'is_expense',
        6: 'is_revenue',
        9: 'BALANCE',
    }

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        # Init
        super().__init__(api_setup)

        # Cache fields
        self.hrm_id = self.get_mapping_id(
            models.MappingId.TYPE.CUSTOM_FIELD, 'account_hrm')
        self.function_id = self.get_mapping_id(
            models.MappingId.TYPE.CUSTOM_FIELD, 'account_function')

    # Make account ready to import accounts
    def init(self, overwrite=False):
        # Init Accounts
        _accounts = self.ctrl.list()
        standard_account = self.ctrl.standard_account

        # Register standard accounts
        for key, value in standard_account.items():
            self.register(models.MappingId.TYPE.ACCOUNT, key, value['id'])
        
        # Init Categories
        ctrl = self.init_class(api_cash_ctrl.AccountCategory)
        _categories = ctrl.list()
        top_category = ctrl.top_category

        # Register top categories
        for key, value in top_category.items():
            self.register(
                models.MappingId.TYPE.ACCOUNT_CATEGORY, key, value['id'])

        # Create top categories
        for number, category in enumerate(
                init_cash_ctrl.ACCOUNT_CATEGORIES, start=1):
            if self.get_mapping_id(
                    models.MappingId.TYPE.ACCOUNT, category['key']):
                logger.info(f"{category['key']} already existing")
                if not overwrite:
                    continue  # we don't overwrite categories

            # Prepare
            top = top_category[category['top']]
            data = {
                'name': dict(values=category['name']),
                'number': f'10000000000{number}',  # to categorize as hrm number
                'parent_id': top['id']
            }

            # Create
            response = ctrl.create(data)
            if response.get('success', False):
                # register top categories
                self.register(
                    models.MappingId.TYPE.ACCOUNT,
                    category['key'], response['insert_id'])                    
                logger.info(f"created {data['name']}")

    # Init Account Positions
    def _check_custom_fields(self):
        if not self.hrm_id:
            raise KeyError("No custom field 'account_hrm' found.")
        if not self.function_id:
            raise KeyError("No custom field 'account_function' found.")    
    
    def _check_top_categories(self):
        # init
        ctrl = self.init_class(api_cash_ctrl.AccountCategory)
        categories = ctrl.list()
        
        # Check
        for name in self.TOP_CATEGORY_MAP.values():
            id = self.get_mapping_id(
                models.MappingId.TYPE.ACCOUNT_CATEGORY, name)            
            if not id:
                raise KeyError(f"'{name}' not found")
            category = next(
                (x for x in categories if x['id'] == id), None)
            if not category:
                raise KeyError(f"category '{name}' {id} not found")       
    
    def _create_category(self, ctrl, position, field_name='c_id', c_id=None):
        # Get parent_id for cashCtrl
        parent_id = c_id if c_id else getattr(position.parent, field_name)

        # Create category
        
        if self.heading_w_numbers:
            name = f'{position.function} {position.name}'
        else:
            name = position.name
            
        data = {
            'name': dict(values={self.api_setup.language: name}),
            'number': float(position.number),
            'parent_id': parent_id
        }
        response = ctrl.create(data)
        if response.get('success', False):
            parent_id = response['insert_id']
            setattr(position, field_name, parent_id)
        else:
            raise DatabaseError (f"Couldn't save {data} in {field_name}")

    def _create_position(self, ctrl, position, field_name='c_id'):
        # Create hrm, e.g. 10010.1 --> 10010.10
        hrm = format_big_number(
            float(position.account_number), thousand_separator='')
        data = {
            'name': dict(values={self.api_setup.language: position.name}),
            'number': float(position.number),
            'category_id': getattr(position.parent, field_name),
            'notes': position.notes,
            'is_inactive': position.is_inactive,
            'currency': self.get_currency_c_id(position.currency),
            'custom': dict(values={
                    f"customField{self.hrm_id}": hrm,
                    f"customField{self.function_id}": position.function,
                })
        }
        response = ctrl.create(data)
        if response.get('success', False):
            parent_id = response['insert_id']
            setattr(position, field_name, parent_id)
        else:
            raise DatabaseError (f"Couldn't save {data} in {field_name}")

    def _check_position_parent(self, position):
        if not position.parent:
            raise KeyError(
                f"{position.get_account_type_display()}: "
                f"No parent found for '{position.account_number} {position.name}'.")

    def upload_accounts(self, ordered_positions, heading_w_numbers=True):
        # Check category definitions
        self._check_custom_fields()  
        self._check_top_categories()       
        self.heading_w_numbers = heading_w_numbers
        
        # Init
        ctrl_account = self.ctrl
        ctrl_category = self.init_class(api_cash_ctrl.AccountCategory)

        # Loop
        if ordered_positions[0].account_type == ACCOUNT_TYPE.BALANCE:
            parents = [None] * 99  # list for storing parents
            for position in ordered_positions:
                if position.is_category:
                    # Is category
                    if position.level == 1:
                        # Get top level
                        first_digit = int(position.account_number[0])
                        key = self.TOP_CATEGORY_MAP[first_digit]
                        position.c_id = self.get_mapping_id(
                            models.MappingId.TYPE.ACCOUNT, key)
                        position.parent = None
                    else:
                        # Parent
                        position.parent = parents[position.level - 1]
                        self._check_position_parent(position)
                        self._create_category(ctrl_category, position)

                    # Register parent
                    parents[position.level] = position

                else:
                    # Is position
                    position.parent = parents[position.level]
                    self._check_position_parent(position)
                    self._create_position(ctrl_account, position)

                # Update position, no need to do post/preprocessing with signals
                position.save_base(raw=True)

        # Upload income, invest
        else:  # (ACCOUNT_TYPE.INCOME, ACCOUNT_TYPE.INVEST)
            # Loop
            balance_scope = CATEGORY_HRM.get_scope(CATEGORY_HRM.BALANCE)
            parents = [None] * 99  # list for storing parents
            for position in ordered_positions:
                if position.is_category:
                    # Is category
                    if position.level == 1:
                        # Get top level
                        # currently we do not work with balance
                        # if int(position.account_number[0]) in balance_scope:
                        #    parent_id = account_category.get('BALANCE')
                        if position.account_type == ACCOUNT_TYPE.INCOME:
                            parent_id = account_category.get('p&l_expense')
                            parent_rev_id = account_category.get('p&l_revenue')
                        elif position.account_type == ACCOUNT_TYPE.INVEST:
                            parent_id = account_category.get('is_expense')
                            parent_rev_id = account_category.get('is_revenue')
                        position.parent = None
                        self._create_category(
                            ctrl_category, position, 'c_id', parent_id)
                        self._create_category(
                            ctrl_category, position, 'c_rev_id', parent_rev_id)
                    else:
                        # Parent
                        position.parent = parents[position.level - 1]
                        self._check_position_parent(position)

                        self._create_category(ctrl_category, position)
                        self._create_category(
                            ctrl_category, position, 'c_rev_id')

                    # Register parent
                    parents[position.level] = position

                else:
                    # Is position
                    position.parent = parents[position.level]
                    self._check_position_parent(position)

                    # Get cashCtrl parents
                    first_digit = int(position.account_number[0])
                    if first_digit in (3, 5):
                        self._create_position(
                            ctrl_account, position, 'c_id')
                    elif first_digit in (4, 6):
                        self._create_position(
                            ctrl_account, position, 'c_rev_id')

                # Update position, no need to do post/preprocessing with signals
                position.save_base(raw=True)

    def upload_balances(self, queryset, date):
        '''
        upload balances from django to cashCtrl, use opening account
        '''
        # Get opening account
        account_open_id =  self.get_mapping_id(
            models.MappingId.TYPE.ACCOUNT, STANDARD_ACCOUNT.OPENING_BALANCE)
        if not account_open_id:
            raise ValueError(_("Could not find opening account"))
        
        # Init
        if date is None:
            # Get the current date
            date = date.today()
        CREDIT, DEBIT = ACCOUNT_SIDE.CREDIT, ACCOUNT_SIDE.DEBIT
        
        # Make collective booking
        items = []
        for account in queryset:
            # Check if position
            if account.is_category:
                continue
                
            # Get amount    
            amount = account.balance or 0
            
            # Calc side
            if amount > 0:      
                side = DEBIT if account.c_id else ACCOUNT_SIDE.CREDIT
            else:
                # CashCtrl doesn't allow negative amounts
                amount = -amount
                side = CREDIT if account.c_id else DEBIT
            
            # Calc account_id
            account_id = account.c_id or account.c_rev_id
            if not account_id:
                logger.warning(f"No account c_id found for {account}.")
                continue
            
            if side == DEBIT:
                items += [{
                    'account_id': account_id,
                    'description': (
                        _('Liability') if account.type ==  ACCOUNT_TYPE.BALANCE
                        else _('Expense')),
                    'debit': amount
                }, {
                    'account_id': account_open_id,
                    'description': 'Opening',
                    'credit': amount
                }]
            else:
                # Credit
                items += [{
                    'account_id': account_id,
                    'description': (                      
                        _('Asset') if account.type ==  ACCOUNT_TYPE.BALANCE
                        else _('Revenue')),
                    'credit': amount
                }, {
                    'account_id': account_open_id,
                    'description': 'Opening',
                    'debit': amount
                }]
 
        # Convert
        items = [{
            api_cash_ctrl.snake_to_camel(key): value 
            for key, value in item.items()
        } for item in items]
 
        # Create data
        data = {
            'amount': None,  # gets ignored if items
            'credit_id': None,  # gets ignored
            'debit_id': None,  # gets ignored 
            'items': json.dumps(items),
            'notes': _('Items are imported opening bookings'),
            'date_added': date.strftime('%Y-%m-%d'),  # must be valid date in fiscal period
            'title': _('Opening booking')
        }
 
        # Book
        ctrl = self.init_class(api_cash_ctrl.Journal)
        response = ctrl.create(data)
        
        if response.get('success', False):
            logger.info(f'Collective booking: {response}')
        else:
            logger.error(f'Collective booking: {response}')
        
        return response

    def download_balances(self, queryset):
        """
        Download 'opening_amount' and 'end_amount' from cashCtrl.
        
        Args:
            queryset: A queryset of positions to update.

        Returns:
            int: The count of successfully updated positions.
        """
        accounts = self.ctrl.list()
        
        # Optimize lookup by converting to a dictionary
        account_map = {account['id']: account for account in accounts}
        
        count = 0
        for position in queryset:
            if not position.is_category:
                # Try expense
                account = (
                    account_map.get(position.c_id)
                        or account_map.get(position.c_rev_id))
                    
                # Save    
                if account:
                    self.prepare_data(account)
                    for key in (CASH_CTRL_KEYS
                            + ['opening_amount', 'end_amount']):
                        if key in account:
                            setattr(position, key, account[key])
                    position.save()
                    count += 1
                else:
                    logger.info(f'{position} not found.')
        
        return count

    def get_balances(self, queryset, date=None):
        """
        Download 'opening_amount' and 'end_amount' from cashCtrl.
        
        Args:
            queryset: A queryset of positions to update.

        Returns:
            int: The count of successfully updated positions.
        """
        # Prepare
        ctrl = self.init_class(api_cash_ctrl.Account)
        count = 0
        
        # Perform
        for position in queryset:
            if not position.is_category:
                id = position.c_id or position.c_rev_id
                position.balance = ctrl.get_balance(id, date=None)
                print("*save", id, position.account_number, position.name,
                    position.balance)
                position.save()
                count += 1
        
        return count

    def delete_system_accounts(self):
        # Prepare
        restricted_accounts = models.MappingId.objects.filter(
            setup=self.api_setup,
            type=models.MappingId.TYPE.ACCOUNT,
            name__gte='0000',
            name__lte='9999'
        ).exclude(c_id=None)
        exclude_numbers = [x.name for x in restricted_accounts.all()]
        
        # Perform
        ids = []
        accounts = self.ctrl.list() 
        for account in accounts:
            if not account['custom']:
                if str(account['number']) not in exclude_numbers:
                    ids.append(account['id'])

        # Delete
        self.ctrl.delete(*ids)
        return len(ids)

    def delete_hrm(self):
        # Prepare
        accounts = self.ctrl.list()
        if self.hrm_id:
            customfield = f'customField{self.hrm_id}'
        else:
            raise ValueError('hrm field not defined')
        
        # Perform
        ids = []
        for account in accounts:
            if account['custom']:
                if account['custom']['values'].get(customfield):
                    ids.append(account['id'])

        # Delete
        self.ctrl.delete(*ids)
        return len(ids)


class AccountCategory(Connector):
    CLASS = api_cash_ctrl.AccountCategory
  
    def delete(self, max_tries, min_length=None, max_length=None):
        # Perform
        count = 0
        for nr_try in range(max_tries):      
            # Prepare
            categories = self.ctrl.list()
            leaves = [
                x for x in self.ctrl.get_leaves()
                if (
                    (min_length and len(str(x['number'])) >= min_length
                        or max_length and len(str(x['number'])) <= max_length)
                )
            ]
            if leaves:
                ids = [x['id'] for x in leaves]
                for id in ids:
                    try:
                        self.ctrl.delete(id)
                        count += 1
                    except:
                        continue
            else:
                break
           
        return count    
  
    def delete_hrm(self, max_tries=10):
        return self.delete(max_tries, min_length=5)    
    
    def delete_system(self, max_tries=5):
        return self.delete(max_tries, max_length=4)
