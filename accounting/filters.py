'''
accounting/filters.py
'''
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant, filter_query_for_tenant
from .models import APISetup, FiscalPeriod, Ledger


# Helpers
def filter_queryset(model_admin, request, queryset):
    """Filter queryset based on selected setup in admin filter."""
    if model_admin.value():
        return filter_query_for_tenant(request, queryset)
    return queryset  # No filter applied

"""
class TenantFilteredSetupListFilter(SimpleListFilter):
    '''Needed as admin.py filter shows all filters values also of foreign
        tenants
    '''
    title = _('Setup')  # Display title in admin
    parameter_name = 'setup'  # The query parameter name

    def lookups(self, request, model_admin):
        '''Return the available options, filtered by tenant.'''
        tenant_data = get_tenant(request)  # Get the current tenant

        # Get only the setups linked to this tenant
        queryset = APISetup.objects.filter(tenant__id=tenant_data['id'])

        # Return a list of tuples (ID, Display Name)
        return [(setup.id, str(setup)) for setup in queryset]

    def queryset(self, request, queryset):
        '''Filter queryset based on selected setup in admin filter.'''
        return filter_queryset(self, request, queryset)
"""

class LedgerFilteredSetupListFilter(SimpleListFilter):
    '''Needed as admin.py filter shows all filters values also of foreign
        tenants
    '''
    title = _('Ledger')  # Display title in admin
    parameter_name = 'ledger'  # The query parameter name

    def lookups(self, request, model_admin):
        """Return the available options, filtered by tenant."""
        tenant_data = get_tenant(request)  # Get the current tenant

        # Get only the setups linked to this tenant
        queryset = Ledger.objects.filter(
            setup__id=tenant_data['setup_id'])

        # Return a list of tuples (ID, Display Name)
        return [(ledger.id, str(ledger)) for ledger in queryset]

    def queryset(self, request, queryset):
        """Filter queryset based on selected setup in admin filter."""
        # Get the value from the query string
        ledger_id = self.value()        
        if ledger_id:
            # If a ledger is selected, filter the queryset based on that
            queryset = queryset.filter(ledger__id=ledger_id)        
        return filter_queryset(self, request, queryset)
