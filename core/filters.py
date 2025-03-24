'''
core/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant_data


# Custom Filter for Existing Categories
class PersonAddressCategoryFilter(admin.SimpleListFilter):
    title = _('Categories')
    parameter_name = 'categories'

    def lookups(self, request, model_admin): 
        '''Return all categories '''
        return [
            (cat.id, cat.name) 
            for cat in AddressCategory.objects.all()  # Fetch all categories
        ]

    def queryset(self, request, queryset):
        # Fetch tenant info
        tenant_data = get_tenant_data(request)  
        tenant_id = tenant_data.get('id')            
        
        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,
                address__categories__id=self.value()
            )
        return queryset
