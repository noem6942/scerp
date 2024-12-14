# accounting/process.py
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext as _
from django.utils import timezone

import json
import logging

from scerp.admin import get_help_text
from .api_cash_ctrl import API, FIELD_TYPE, CashCtrl
from .models import APISetup, FiscalPeriod, Location

logger = logging.getLogger(__name__)  # Using the app name for logging


class Process(object):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.api_setup = api_setup
        self.timezone = timezone.get_current_timezone()
    
    def make_timeaware(self, naive_datetime):
        timezone.make_aware(naive_datetime, self.timezone)
        
    def save_logging(self, obj):
        obj.tenant = self.api_setup.tenant
        if not obj.created_by:
            obj.created_by = self.api_setup.modified_by
        obj.modified_by = self.api_setup.modified_by


class ProcessGenericAppCtrl(Process):
    pass


class ProcessCashCtrl(Process):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.ctrl = CashCtrl(api_setup.org_name, api_setup.api_key)
        
        super().__init__(api_setup)

    def save_application_logging(self, obj, data):
        obj.c_id = data['id']
        obj.c_created = data['created']
        obj.c_created_by = data['created_by']
        obj.c_last_updated = make_timeaware(data['last_updated'])
        obj.c_last_updated_by = make_timeaware(data['last_updated_by'])
        save_logging(obj)

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
    def init_locations(self):
        # Create in api_setuping
        if not Location.objects.filter(tenant=self.api_setup.tenant).exists():
            loc = Location(name=_('VAT (1)'))
            self.save_logging(loc)
            loc.save()

        # Create in CashCtrl
        pass
