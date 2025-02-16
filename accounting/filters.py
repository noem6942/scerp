'''
accounting/filters.py
'''
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant, filter_query_for_tenant
from .models import (
    APISetup, PersonCategory, ArticleCategory, FiscalPeriod, Ledger
)

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
        tenants; currently: don't allow to switch ledger
    '''
    title = _('Ledger')  # Display title in admin
    parameter_name = 'ledger'  # The query parameter name

    def lookups(self, request, model_admin):
        """Return the available options, filtered by tenant."""
        '''
        # allow to select
        tenant_data = get_tenant(request)  # Get the current tenant
        print("*tenant_data", tenant_data)

        # Get only the ledgers linked to this tenant
        queryset = Ledger.objects.filter(
            tenant__id=tenant_data['id']).order_by('name')
        '''

        # don't allow to select
        ledger_id = self.value()  # Get the selected ledger from URL params
        queryset = Ledger.objects.filter(id=ledger_id)

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


class CategoryFilter(SimpleListFilter):
    title = 'Category'  # The filter title
    parameter_name = 'category'  # The query parameter name in the URL
    
    def lookups(self, request, model_admin):
        """
        Return available filter options for the 'category' field,
        excluding categories with codes starting with "_".
        """
        # Get all categories excluding those whose code starts with "_"
        categories = self.model.objects.exclude(code__startswith='_')

        # Return the list of categories to be displayed in the filter dropdown
        return [(category.id, str(category)) for category in categories]

    def queryset(self, request, queryset):
        """
        Filter the queryset based on the selected category in the admin filter.
        """
        if self.value():
            # Apply filtering to the queryset based on the selected category
            return queryset.filter(category_id=self.value())
        return queryset  # Return the original queryset if no filter is applied

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PersonCategoryFilter(CategoryFilter):
    model = PersonCategory
    
 
class ArticleCategoryFilter(CategoryFilter):
    model = ArticleCategory 
