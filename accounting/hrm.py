# accounting/hrm
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _


class ACCOUNT_TYPE(models.IntegerChoices):
    # Used for Cantonal Charts
    BALANCE = (1, _('Bilanz'))
    FUNCTIONAL = (2, _('Funktionale Gliederung'))  # use only if canton chart
    INCOME = (3, _('Erfolgsrechnung'))
    INVEST = (5, _('Investitionsrechnung'))


class Position(object):
    
    def __init__(
            self, account_type, account_category_number=None,
            account_number=None, function=None):
        # Input
        self.account_type = self.get_account_type(account_type) 
        self.account_category_number = account_category_number
        self.account_number = self.get_account_number(account_number)
        self.function = function
        
        # Calc
        self.category = self.get_category(self.account_number)
        self.ff = self.get_ff(account_number)
        
    def get_account_number(self, value):
        if type(value) == str:
            value = value.strip()
        if value is None or value == '':
            return None
        return value
    
    def get_account_type(self, value):
        # Check if account_type is a valid account_type
        if value in ACCOUNT_TYPE.values:
            return value
        else:
            raise ValueError(f"Invalid account type: {value}")
            
    def get_ff(self, value):
        return False if (value is None or 'ff' not in value) else True
 
    def get_category(self, value):
        return True if account_number else False
        
        