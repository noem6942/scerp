'''
asset/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant_data
from scerp.mixins import primary_language
from .models import AssetCategory


# Custom Filter for Category
class CategoryFilter(admin.SimpleListFilter):
    title = _('Categories')
    parameter_name = 'categories'

    def lookups(self, request, model_admin): 
        '''Return all categories '''
        return [
            (category.id, primary_language(category.name)) 
            for category in AssetCategory.objects.all()  # Fetch all categories
        ]

    def queryset(self, request, queryset):
        # Fetch tenant info
        tenant_data = get_tenant_data(request)  
        tenant_id = tenant_data.get('id')            
        
        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,
                category=self.value()
            )
        return queryset

