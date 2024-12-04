# accounting/mixins.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime   
import logging

from scerp.mixins import dict_camel_to_snake
from . import api_cash_ctrl as api

logger = logging.getLogger(__name__)  # Using the app name for logging


def adopt_cash_ctrl_record(data):
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


class APISetupProcessing:

    def api_create(sender, instance, created, **kwargs):
        """Perform follow-up actions when a new APISetup is created.
        """        
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


class FiscalPeriodValidate:

    def clean(self):
        if self.is_custom:
            if not self.start or not self.end:
                raise ValidationError(
                    _("Custom periods require both a start and an end date."))
            if self.start > self.end:
                raise ValidationError(
                    _("Start date cannot be after end date."))
        else:
            if self.start or self.end:
                raise ValidationError(
                    _("Automatic periods cannot have start or end dates."))


# Helpers
def format_number_with_leading_digits(praefix_digits, num, length, comma):
    # Format the number with the required decimal places
    formatted_num = f"{num:.{comma}f}"
    
    # Remove the decimal point and pad the number with leading zeros if necessary
    if comma:
        int_part, dec_part = formatted_num.split(".")
    else:
        int_part, dec_part = formatted_num, None

    # assemble
    int_str = int_part.zfill(length)
    dec_str = '' if dec_part is None else f".{dec_part}" 
    
    # Combine the prefix digit with the integer and decimal parts    
    return f"{praefix_digits}{int_str}{dec_str}"


# Account Position
def account_position_calc_number(
        account_type, function, account_number, is_category):
    '''calc number with pattern:
        AFFFFCNNNNN.NN
        A .. ACCOUNT_TYPE
        FFFF .. function with leading zeros
        C .. 1 if is_category else 0
        NNNNN.NN .. unique number with leading zeros and 2 commas
        
        ff is ignored (replace by '')
    '''
    DIGITS_FUNCTIONAL = 4, 0
    DIGITS_ACCOUNT = 5, 2

    # clean function
    try:
        function = int(function)
    except:    
        function = 0

    # eliminate ff
    if account_number:
        account_number = account_number.replace('ff', '').strip()

    # Calc prafix, i.e.{type_1}{function_4}
    praefix = format_number_with_leading_digits(
        account_type, function, *DIGITS_FUNCTIONAL)
    
    # Add category
    category_1 = '1' if is_category else '0'
    praefix += category_1

    # clean account_number
    try:
        account_number = float(account_number)
    except:    
        account_number = 0

    # Fill in number
    number = format_number_with_leading_digits(
        praefix, account_number, *DIGITS_ACCOUNT)
    
    return float(number)
