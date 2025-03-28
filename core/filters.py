'''
core/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant_data
from .models import Area


# Custom Filter for Area
class AreaFilter(admin.SimpleListFilter):
    title = _('Areas')
    parameter_name = 'areas'

    def lookups(self, request, model_admin): 
        '''Return all categories '''
        return [
            (area.id, area.name) 
            for area in Area.objects.all()  # Fetch all categories
        ]

    def queryset(self, request, queryset):
        # Fetch tenant info
        tenant_data = get_tenant_data(request)  
        tenant_id = tenant_data.get('id')            
        
        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,
                area=self.value()
            )
        return queryset

