'''
accounting/resources.py
'''
from import_export import resources
from .models import LedgerBalance, LedgerPL, LedgerIC


class LedgerBalanceResource(resources.ModelResource):
    class Meta:
        model = LedgerBalance
        import_id_fields = ('id',)  # You can specify other unique fields here
        fields = (
            'function', 'hrm', 'name', 'opening_balance', 'increase',
            'decrease', 'closing_balance', 'notes')  # Specify fields to be exported
        skip_unchanged = False  # Skip unchanged records during export


class LedgerPLResource(resources.ModelResource):
    class Meta:
        model = LedgerPL
        import_id_fields = ('id',)  # You can specify other unique fields here
        fields = (
            'function', 'hrm', 'name', 'expense', 'revenue',
            'expense_budget', 'revenue_budget',
            'expense_previous', 'revenue_previous',
            'notes')  # Specify fields to be exported
        skip_unchanged = False  # Skip unchanged records during export


class LedgerICResource(LedgerPLResource):
    pass
