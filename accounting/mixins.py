# accounting/mixins.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


def prepare_cash_ctrl(data):
    data.update({
        'c_id': data.pop('id'),
        'c_created': data.pop('created'),
        'c_created_by': data.pop('created_by'),
        'c_last_updated': data.pop('last_updated'),
        'c_last_updated_by': data.pop('updated_by')
    })


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


class AccountPositionAbstractValidate:
    '''make number, and do validations
        PATTERN = '{display_type_1}{function_4}{category_1}{account_5_2}'
    '''

    @staticmethod
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

    def update_related_data(
            self, digits_functional, comma_functional, digits_nr, comma_nr):
        # Code to update related models or fields
        # ff
        if self.account_4_plus_2 is None or 'ff' not in self.account_4_plus_2:
            self.ff = False
        else:
            self.ff = True
        
        # Account, category 
        account_number = self.account_number.strip()
        if account_number:
            self.is_category = True
            self.account = account_number
        else:
            self.is_category = False
            self.account = (
                self.account_4_plus_2.strip().replace('ff', '').strip())
            if self.account == '':
                self.account = 0

        # Fill in function
        if hasattr(self, 'function') and self.function:
            function_4 = int(self.function)
        else:
            function_4 = 0
        
        # Calc prafix, i.e.{type_1}{function_4}
        display_type_1 = self.display_type
        praefix = self.format_number_with_leading_digits(
            display_type_1, function_4, digits_functional, comma_functional)
 
        # Add category
        category_1 = '1' if self.is_category else '0'
        praefix += category_1
 
        # Fill in account
        if self.account:
            account = float(self.account)
        else:
            account = 0.0
 
        # Fill in number
        number = self.format_number_with_leading_digits(
            praefix, account, digits_nr, comma_nr)        
        number_str = number
        
        # Calc number
        self.number = Decimal(number)

    def validate_before_save(self, chart_type, max_account_nr):
        # Get row_nr
        row_nr = self.row_nr if hasattr(self, 'row_nr') else None
        if row_nr:
            del self.row_nr  # Delete the temporary field after use 

        # Perform checks here
        try:
            nr = float(self.account)
        except:
            nr = -1
        if 0 <= nr <= max_account_nr:
            pass
        else:                      
            msg = f"{_('row')} {row_nr}: {self.account} {_('not a number')}"
            raise ValidationError(msg)


class AccountPositionMunicipalityValidate:

    def clean_related_data(self, chart_type):
        if self.display_type == chart_type.FUNCTIONAL:
            msg = _("display_type cannot be set to Functional")
            raise ValidationError(msg)
