# accounting/process.py
'''Interface to cashCtrl (and other accounting applications later)
'''
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext as _

from scerp.admin import get_help_text
from scerp.mixins import get_admin, make_timeaware

from . import api_cash_ctrl
from .init_cash_ctrl import ACCOUNT_CATEGORIES, UNITS
from .models import (
    APISetup, FiscalPeriod, Setting, Location, Currency, Unit, Tax, CostCenter)

logger = logging.getLogger(__name__)  # Using the app name for logging


class Process(object):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.api_setup = api_setup
        self.admin = get_admin()

    def add_logging(self, data):
        data['setup'] = self.api_setup

        if not data.get('tenant'):
            data['tenant'] = self.api_setup.tenant

        if not data.get('created_by'):
            data['created_by'] = self.admin

        if not data.get('modified_by'):
            data['modified_by'] = self.admin


class ProcessGenericAppCtrl(Process):
    pass


class ProcessCashCtrl(Process):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        super().__init__(api_setup)

    def init_class(self, cls):
        return cls(self.api_setup.org_name, self.api_setup.api_key)

    # APISetup
    def init_custom_groups(self):
        for field in self.api_setup.__dict__.keys():
            if field.startswith('custom_field_group_'):
                # Get elems
                data = json.loads(get_help_text(APISetup, field))
                name = data['name']
                c_type = data['type']

                # Get group
                ctrl = self.init_class(api_cash_ctrl.CustomFieldGroup)
                group = ctrl.get_from_name(name, c_type)
                if group:
                    msg = _('Group {name} of type {type} already existing.').format(
                        name=name, type=type_)
                    logger.warning(msg)
                else:
                    # Create group
                    data = {'name': name, 'type': c_type}
                    group = ctrl.create(data)

                    # Register group
                    setattr(api_setup, field, group['insert_id'])
                    api_setup.save()

                    # Msg
                    msg = _('Created group {name} of type {type}.').format(
                        name=name, type=type_)
                    logger.info(msg)

    def init_custom_fields(self):
        for field in self.api_setup.__dict__.keys():
            if (not field.startswith('custom_field_group_')
                    and field.startswith('custom_field_')):
                # Get elems
                data = json.loads(get_help_text(APISetup, field))
                data['group'] = json.loads(data['group'])

                # Get customfield
                ctrl = self.init_class(api_cash_ctrl.CustomField)
                customfield = ctrl.get_from_name(
                    data['name'], data['group']['type'])

                if customfield:
                    msg = _('Customfield {name} of type {type} in '
                            '{group_name} already existing.')
                    msg = msg.format(
                        name=data['name'], type=data['group']['type'],
                        group_name=data['group']['name'])
                    logger.warning(msg)
                else:
                    # Create field
                    customfield = ctrl.create_from_group(**data)

                    # Register field
                    setattr(api_setup, field, customfield['insert_id'])
                    api_setup.save()

                    # Msg
                    msg = _('Created customfield {name} of type {type} in '
                            '{group_name}.')
                    msg = msg.format(
                        name=data['name'], type=data['group']['type'],
                        group_name=data['group']['name'])
                    logger.info(msg)

    def init_accounts(self):
        # init
        ctrl = self.init_class(api_cash_ctrl.AccountCategory)
        categories = ctrl.list()
        top_categories = ctrl.top_categories()

        # create top classes
        category_id = {}
        for number, category in enumerate(ACCOUNT_CATEGORIES, start=1):
            key = category['key']
            category_id[key] = {}
            for side in ['EXPENSE', 'REVENUE']:
                data = {
                    'name': {'values': category['name']},
                    'number': number,
                    'parent_id': top_categories[side]['id']
                }
                response = ctrl.create(data)
                if response.get('success', False):
                    category_id[key][side] = response['insert_id']
                    logger.info(f"created {data['name']}")

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

    # Handle cashCtrl pull
    def pull_accounting_data(self, api_class, model):
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

            # Remove keys not needed
            for key in list(data.keys()):
                if key  not in model_keys:
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
        created, updated = self.pull_accounting_data(
            api_cash_ctrl.Location, Location)

    def get_fiscal_periods(self):
        # Get and update all fiscal periods
        created, updated = self.pull_accounting_data(
            api_cash_ctrl.FiscalPeriod, FiscalPeriod)

    def get_currencies(self):
        # Get and update all currencies
        created, updated = self.pull_accounting_data(
            api_cash_ctrl.Currency, Currency)

    def get_units(self):
        # Get and update all units
        created, updated = self.pull_accounting_data(
            api_cash_ctrl.Unit, Unit)

    def get_tax(self):
        # Get and update all tax rates
        created, updated = self.pull_accounting_data(
            api_cash_ctrl.Tax, Tax)

    def get_cost_centere(self):
        # Get and update all cost centers
        created, updated = self.pull_accounting_data(
            api_cash_ctrl.AccountCostCenter, CostCenter)
