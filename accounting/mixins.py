# accounting/mixins.py
'''helpers for models.py and signals.py
'''
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# FiscalPeriod
def fiscal_period_validate(obj):
    if not obj.start or not obj.end:
        raise ValidationError(
            _("Custom periods require both a start and an end date."))
    if obj.start > obj.end:
        raise ValidationError(_("Start date cannot be after end date."))



# AccountPositionAbstract
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


def account_position_calc_number(
        account_type, function, account_number, is_category):
    '''calc number with pattern:
        AFFFFCNNNNN.NN
        A .. ACCOUNT_TYPE
        FFFF .. function with leading zeros
        C .. 1 if is_category else 0
        NNNNN.NN .. unique number with leading zeros and 2 commas
        
        ff in account_number is ignored (replace by '')
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
