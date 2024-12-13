# accounting/process.py
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext as _

import json
import logging

from core.safeguards import save_logging
from scerp.admin import get_help_text
from .api_cash_ctrl import API, FIELD_TYPE, CashCtrl
from .models import APISetup, FiscalPeriod, Location

logger = logging.getLogger(__name__)  # Using the app name for logging


class Process(object):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.api_setup = api_setup


class ProcessGenericAppCtrl(Process):
    pass


class ProcessCashCtrl(Process):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.ctrl = CashCtrl(api_setup.org_name, api_setup.api_key)
        super().__init__(api_setup)

    def save_logging(self, obj):
        obj.created_by = self.api_setup.created_by
        obj.modified_by = self.api_setup.modified_by
        obj.tenant = self.api_setup.tenant

    def save_application_logging(self, obj, data):
        obj.c_id = data['id']
        obj.c_created = data['created']
        obj.c_created_by = data['created_by']
        obj.c_last_updated = data['last_updated']
        obj.c_last_updated_by = data['last_updated_by']
        self.save_logging(obj)

    def init_custom_groups(self):
        model = APISetup
        for field in self.api_setup.__dict__.keys():
            if field.startswith('custom_field_group_'):
                # Get elems
                data = json.loads(get_help_text(model, field))
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
        model = APISetup
        for field in self.api_setup.__dict__.keys():
            if (not field.startswith('custom_field_group_')
                    and field.startswith('custom_field_')):
                # Get elems
                data = json.loads(get_help_text(model, field))
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

    def get_fiscal_period(self, name):
        fiscal_periods = self.ctrl.list(API.fiscalperiod.value['url'])
        return next(
            (x for x in fiscal_periods if x['name'] == name), None)
            
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
            fp = self.get_fiscal_period(obj.name)
            self.save_application_logging(obj, fp)
            obj.save()

    def update_fiscal_period(self, obj):
        data = self.get_fiscal_period(obj.name)
        fp = self.ctrl.update(API.fiscalperiod.value['url'], data)

    def init_locations(self):
        # Create in api_setuping
        if not Location.objects.filter(tenant=self.api_setup.tenant).exists():
            loc = Location(name=_('VAT (1)'))
            self.save_logging(loc)
            loc.save()

        # Create in CashCtrl
        pass