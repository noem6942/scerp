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
        tenant_id = get_tenant_data(request).get('id') 
        
        return [
            (category.id, primary_language(category.name)) 
            for category in AssetCategory.objects.filter(
                tenant__id=tenant_id)  # Fetch all categories by tenant
        ]

    def queryset(self, request, queryset):
        # Fetch tenant info
        if self.value():
            return queryset.filter(
                category=self.value()
            )
        return queryset

