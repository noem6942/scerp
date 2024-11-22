# accounting/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import gettext_lazy as _

import logging

from scerp.mixins import dict_camel_to_snake
from . import api_cash_ctrl as api

from .models import APISetup, FiscalPeriod, Currency

logger = logging.getLogger(__name__)  # Using the app name for logging

from datetime import datetime   
def adopt_cash_ctrl_record(data):
    print("*", data)
    data.update({
        'c_id': data.pop('id'),
        'c_created': data.pop('created'),
        'c_created_by': data.pop('created_by'),
        'c_last_updated': data.pop('last_updated'),
        'c_last_updated_by': data.pop('last_updated_by')
    })    
        
        
def cash_ctrl_str_to_date(datetime_str):
    # Given datetime object
    start_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')

    # Assign just the date part to the DateField
    return start_datetime.date()
        

@receiver(post_save, sender=APISetup)
def api_create(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new APISetup is created."""
    if created:
        # This code only runs the first time the tenant is created (not on updates)
        pass
    else:
        # Perform follow-up actions  
        # a = api_FiscalPeriod(instance.tenant.org_name, tenant.api_key)
        a = api.FiscalPeriod(
            getattr(settings, 'ORG_CASH_CTRL_DEBUG'),
            getattr(settings, 'API_KEY_CASH_CTRL_DEBUG'))
        '''
        # Get fiscal periods      
        periods = a.list()     
        for period in periods:
            data = dict_camel_to_snake(period)        
            adopt_cash_ctrl_record(data)
                        
            obj, created = FiscalPeriod.objects.get_or_create(
                tenant=instance.tenant,
                name=data.pop('name'),
                defaults={
                    'start': cash_ctrl_str_to_date(data.pop('start')), 
                    'end': cash_ctrl_str_to_date(data.pop('end')),
                    'created_by': instance.created_by,
                    'modified_by': instance.modified_by
                })

        logger.info(f"{len(periods)} analyzed.") 
        '''
        # Get currencies
        a = api.Currency(
            getattr(settings, 'ORG_CASH_CTRL_DEBUG'),
            getattr(settings, 'API_KEY_CASH_CTRL_DEBUG'))        
        currencies = a.list()     
        for currency in currencies:            
            data = dict_camel_to_snake(currency)                    
            print("*currencies", data)
            adopt_cash_ctrl_record(data)            
                        
            obj, created = Currency.objects.get_or_create(
                tenant=instance.tenant,
                code=data.pop('code'),
                defaults={                    
                    'is_default': data.pop('is_default'),
                    'created_by': instance.created_by,
                    'modified_by': instance.modified_by
                })

        logger.info(f"{len(currencies)} analyzed.") 
