'''
accounting/resources.py
'''
from import_export import resources
from .models import LedgerBalance


class LedgerBalanceResource(resources.ModelResource):
    class Meta:
        model = LedgerBalance
        import_id_fields = ('id',)  # You can specify other unique fields here
        fields = (
            'function', 'hrm', 'name', 'opening_balance', 'increase', 
            'decrease', 'closing_balance', 'notes')  # Specify fields to be exported
        skip_unchanged = False  # Skip unchanged records during export
