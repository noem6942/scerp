# accounting/process.py
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext as _
from django.utils import timezone

import json
import logging

from scerp.admin import get_help_text
from scerp.mixins import get_admin     
from .api_cash_ctrl import API, FIELD_TYPE, CashCtrl
from .models import (
    APISetup, FiscalPeriod, Location, Currency, Unit, Tax, CostCenter)

logger = logging.getLogger(__name__)  # Using the app name for logging


class Process(object):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.api_setup = api_setup
        self.timezone = timezone.get_current_timezone()
        self.admin = get_admin()
    
    def make_timeaware(self, naive_datetime):
        return timezone.make_aware(naive_datetime, self.timezone)
      
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
        self.ctrl = CashCtrl(api_setup.org_name, api_setup.api_key)
        
        super().__init__(api_setup)

    def add_application_logging(self, data):
        print("***1")
        data.update({
            'c_id': data.pop('id'),
            'c_created': self.make_timeaware(data.pop('created')),
            'c_created_by': data.pop('created_by'),
            'c_last_updated': self.make_timeaware(data.pop('last_updated')),
            'c_last_updated_by': data.pop('last_updated_by')
        })
        print("***2")
        self.add_logging(data)

    def save_application_logging(self, obj, data):
        self.add_logging(data)
        obj.c_id = data['id']
        obj.c_created = data['created']
        obj.c_created_by = data['created_by']
        obj.c_last_updated = self.make_timeaware(data['last_updated'])
        obj.c_last_updated_by = self.make_timeaware(data['last_updated_by'])

    # APISetup
    def init_custom_groups(self):
        for field in self.api_setup.__dict__.keys():
            if field.startswith('custom_field_group_'):
                # Get elems
                data = json.loads(get_help_text(APISetup, field))
                name = data['name']
                type_ = data['type']

                group = self.ctrl.get_customfield_group(name, type_)
                if group:
                    msg = _('Group {name} of type {type} already existing.').format(
                        name=name, type=type_)
                    logger.warning(msg)
                else:
                    # Create group
                    group = self.ctrl.create_customfield_group(name, type_)

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
                customfield = self.ctrl.get_customfield(
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
                    customfield = self.ctrl.create_customfield(**data)

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

    def init_fiscal_periods(self):
        # Get Periods
        fiscal_periods = self.ctrl.list(API.fiscalperiod.value['url'])

        # Assign Periods
        for data in fiscal_periods:
            if not FiscalPeriod.objects.filter(c_id=data['id']).exists():
                # Create
                obj = FiscalPeriod(
                    name=data['name'],
                    start=data['start'].date(),
                    end=data['end'].date(),
                    is_closed=data['is_closed'],
                    is_current=data['is_current'])

                # Save
                self.save_application_logging(obj, data)
                obj.save()

                # Message
                msg = _('Saved Fiscal Period {name}.').format(name=obj.name)
                logger.info(msg)

    # FiscalPeriod
    def create_fiscal_period(self, obj):            
        # Create, we do is_custom=True, we don't assign type
        data = {
            'name': obj.name,
            'is_custom': True,
            'start': obj.start,
            'end': obj.end
        }        
        fp = self.ctrl.create(API.fiscalperiod.value['url'], data)
        if fp.get('success'):         
            # Get data
            fiscal_periods = self.ctrl.list(API.fiscalperiod.value['url'])
            period = next(
                (x for x in fiscal_periods if x['name'] == obj.name), None)
                
            # Save    
            if period:       
                self.save_application_logging(obj, period)
                obj.save()            
            else:
                raise Exception(f"Period '{obj.name}' not found.")

    def update_fiscal_period(self, obj):
        data = {
            'id': obj.c_id,
            'name': obj.name,
            'is_custom': True,
            'start': obj.start,
            'end': obj.end
        }
        fp = self.ctrl.update(API.fiscalperiod.value['url'], data)

    # Location
    def push_accounting_data(self, api_class, model):
        # Get data

        data_list = self.ctrl.list(api_class.url)
        print("*d", data_list)     
 
        # Init
        created, updated = 0, 0
        instance = model()
        model_keys = instance.__dict__.keys()  

        # Parse
        for data in data_list:
            # Clean basics
            data.update({
                'c_id': data.pop('id'),
                'c_created': self.make_timeaware(data.pop('created')),
                'c_created_by': data.pop('created_by'),
                'c_last_updated': self.make_timeaware(
                    data.pop('last_updated')),
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
 
    def get_locations(self):
        # Get and update all locations
        created, updated = self.push_accounting_data(API.Location, Location)
        
    def get_fiscal_periods(self):
        # Get and update all fiscal periods
        created, updated = self.push_accounting_data(
            API.FiscalPeriod, FiscalPeriod)
            
    def get_currencies(self):
        # Get and update all currencies
        created, updated = self.push_accounting_data(
            API.Currency, Currency)
            
    def get_units(self):
        # Get and update all units
        created, updated = self.push_accounting_data(
            API.Unit, Unit)
            
    def get_tax(self):
        # Get and update all tax rates
        created, updated = self.push_accounting_data(
            API.Tax, Tax)
            
    def get_cost_centere(self):
        # Get and update all cost centers
        created, updated = self.push_accounting_data(
            API.AccountCostCenter, CostCenter)
