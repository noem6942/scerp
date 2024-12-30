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

from .connector import ConnectorBase
from .models import (
    APISetup, FiscalPeriod, Setting, Location, Currency, Unit, Tax, CostCenter,
    ACCOUNT_TYPE, CATEGORY_HRM, AccountPosition)
from . import api_cash_ctrl, init_cash_ctrl


logger = logging.getLogger(__name__)  # Using the app name for logging


class Connector(ConnectorBase):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        # Init
        super().__init__(api_setup)

        # Custom Fields
        custom_field = self.api_setup.data.get('custom_field')
        if custom_field:
            self.hrm_id = custom_field.get('account_hrm')
            self.function_id = custom_field.get('account_function')
        else:
            self.hrm_id = None
            self.function_id = None

    # Handle cashCtrl pull
    def _pull_accounting_data(self, api_class, model):
        '''generic class, pull data from api_class, e.g. Unit
            and store it in the model
        '''
        # Init
        ctrl = self.init_class(api_class)

        # Get data
        data_list = ctrl.list(api_class.url)

        # Init
        created, updated = 0, 0
        instance = model()
        model_keys = instance.__dict__.keys()

        # Parse
        for data in data_list:
            # Clean basics
            data.update({
                'c_id': data.pop('id'),
                'c_created': make_timeaware(data.pop('created')),
                'c_created_by': data.pop('created_by'),
                'c_last_updated': make_timeaware(data.pop('last_updated')),
                'c_last_updated_by': data.pop('last_updated_by')
            })

            # Convert data, remove keys not needed
            for key in list(data.keys()):
                if key in ['start', 'end']:
                    data[key] = make_timeaware(data[key])
                elif key  not in model_keys:
                    data.pop(key)

            # Add logging info
            self.add_logging(data)

            # Update or create
            _obj, created = model.objects.update_or_create(
                tenant=self.api_setup.tenant,
                setup=data.pop('setup'),
                c_id=data.pop('c_id'),
                defaults=data)
            if created:
                created += 1
            else:
                updated += 1

        # Message
        msg = _('{total} {verbose_name_plural}, updated {updated}, '
                'created {created}')
        logger.info(msg.format(
            verbose_name_plural = model._meta.verbose_name_plural,
            total=created + updated,
            created=created,
            updated=updated))

        return created, updated

    # Init
    def init_class(self, cls):
        return cls(self.api_setup.org_name, self.api_setup.api_key)

    def init_persons(self):
        # Register top categories
        DATA_KEY = 'person_category'
        ctrl = self.init_class(api_cash_ctrl.PersonCategory)
        categories = ctrl.list()
        top_category = ctrl.top_category()

        # Register top categories
        for key, value in top_category.items():
            print("*key", key)
            self.api_setup.set_data(DATA_KEY, key, value['id'])

        # Create top classes
        # currently we don't create any person categories

    def init_units(self):
        ''' add m³, call before units load
        '''
        # Init
        ctrl = self.init_class(api_cash_ctrl.Unit)

        # List existing
        units = ctrl.list()

        # Create new
        for data in UNITS:
            if not next((x for x in units if x['name'] == data['name']), None):
                unit = ctrl.create(data)
                if unit.pop('success', None):
                    logger.info(f"created {unit}")

    def init_settings(self):
        ''' do this at the end
        '''
        ctrl = self.init_class(api_cash_ctrl.AccountCategory)

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

    def get_locations(self):
        # Get and update all locations
        created, updated = self._pull_accounting_data(
            api_cash_ctrl.Location, Location)

    def get_fiscal_periods(self):
        # Get and update all fiscal periods
        created, updated = self._pull_accounting_data(
            api_cash_ctrl.FiscalPeriod, FiscalPeriod)

    def get_currencies(self):
        # Get and update all currencies
        created, updated = self._pull_accounting_data(
            api_cash_ctrl.Currency, Currency)

    def get_units(self):
        # Get and update all units
        created, updated = self._pull_accounting_data(
            api_cash_ctrl.Unit, Unit)

    def get_tax(self):
        # Get and update all tax rates
        created, updated = self._pull_accounting_data(
            api_cash_ctrl.Tax, Tax)

    def get_cost_centere(self):
        # Get and update all cost centers
        created, updated = self._pull_accounting_data(
            api_cash_ctrl.AccountCostCenter, CostCenter)


class CustomField(Connector):

    def init_custom_groups(self):
        # Init
        ctrl = self.init_class(api_cash_ctrl.CustomFieldGroup)

        # Check and create groups
        for group_def in init_cash_ctrl.CUSTOM_FIELD_GROUPS:
            # Get group
            group = ctrl.get_from_name(group_def['name'], group_def['type'])
            if group:
                msg = _('Group {name} of type {type} already existing.').format(
                    name=name, type=type_)
                logger.warning(msg)
            else:
                # Create group
                data = {
                    'name': dict(values=group_def['name']),
                    'type': group_def['type']
                }
                group = ctrl.create(data)

                # Register group
                self.api_setup.set_data(
                    'custom_field_group', group_def['key'], group['insert_id'])

                # Msg
                msg = _("Created group {name} of type {type}.").format(
                    name=group_def['name'], type=group_def['type'])
                logger.info(msg)

    def init_custom_fields(self):
        # Init
        ctrl = self.init_class(api_cash_ctrl.CustomField)
        ctrl_group = self.init_class(api_cash_ctrl.CustomFieldGroup)

        # Check and create fields
        for field_def in init_cash_ctrl.CUSTOM_FIELDS:
            # Init
            key = field_def.pop('key')
            group_key = field_def.pop('group_key')

            # Get group id
            group_id = self.api_setup.get_data('custom_field_group', group_key)
            if not group_id:
                raise Exception(f"No group with {group_key} found.")

            # Get group type
            type_c = next((
                x['type'] for x in init_cash_ctrl.CUSTOM_FIELD_GROUPS
                if x['key'] == group_key), None)
            if not type_c:
                raise Exception(f"No type for key {group_key} found.")

            # Prepare
            name = dict(values=field_def['name'])
            customfield = ctrl.get_from_name(name, type_c)

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
                customfield = ctrl.create(field_def)

                # Register field
                self.api_setup.set_data(
                    'custom_field', key, customfield['insert_id'])

                # Msg
                msg = _('Created customfield {name} of type {type}')
                msg = msg.format(name=name, type=type_c)
                logger.info(msg)


class Account(Connector):

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

    # Make account ready to import accounts
    def init_accounts(self, overwrite=False):
        # Init Accounts
        DATA_KEY = 'account'
        ctrl = self.init_class(api_cash_ctrl.Account)
        _accounts = ctrl.list()
        standard_account = ctrl.standard_account

        # Register standard accounts
        for key, value in standard_account.items():
            self.api_setup.set_data(DATA_KEY, key, value['id'])        
        
        # Init Categories
        DATA_KEY = 'account_category'
        ctrl = self.init_class(api_cash_ctrl.AccountCategory)
        _categories = ctrl.list()
        top_category = ctrl.top_category

        # Register top categories
        for key, value in top_category.items():
            self.api_setup.set_data(DATA_KEY, key, value['id'])

        # Create top classes
        for number, category in enumerate(
                init_cash_ctrl.ACCOUNT_CATEGORIES, start=1):
            if self.api_setup.get_data(DATA_KEY, category['key']):
                logger.info(f"{category['key']} already existing")
                if not overwrite:
                    continue  # we don't overwrite categories

            # Prepare
            top = top_category[category['top']]
            data = {
                'name': dict(values=category['name']),
                'number': number,
                'parent_id': top['id']
            }

            # Create
            response = ctrl.create(data)
            if response.get('success', False):
                # register top categories
                self.api_setup.set_data(
                    DATA_KEY, category['key'], response['insert_id'])
                logger.info(f"created {data['name']}")

    # Init Account Positions
    def _check_custom_fields(self):
        if not self.hrm_id:
            raise KeyError("No custom field 'account_hrm' found.")
        if not self.function_id:
            raise KeyError("No custom field 'account_function' found.")    
    
    def _check_top_categories(self):
        # init
        DATA_KEY = 'account_category'
        ctrl = self.init_class(api_cash_ctrl.AccountCategory)
        categories = ctrl.list()
        
        # Check
        for name in self.TOP_CATEGORY_MAP.values():
            id = self.api_setup.get_data(DATA_KEY, name)
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
        ctrl_account = self.init_class(api_cash_ctrl.Account)
        ctrl_category = self.init_class(api_cash_ctrl.AccountCategory)
        account_category = self.api_setup.data['account_category']

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
                        position.c_id = account_category.get(key)
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
