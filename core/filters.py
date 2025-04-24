'''
core/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant_data
from scerp.mixins import primary_language
from .models import Area, PersonCategory


# Custom Filter for Area
class AreaFilter(admin.SimpleListFilter):
    title = _('Areas')
    parameter_name = 'areas'

    def lookups(self, request, model_admin): 
        '''Return all categories '''
        tenant_id = get_tenant_data(request).get('id') 
        
        return [
            (area.id, area.name) 
            for area in Area.objects.filter(
                tenant__id=tenant_id)  # Fetch all categories by tenant
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                area=self.value()
            )
        return queryset


# Custom Filter for PersonCategory
class PersonCategoryFilter(admin.SimpleListFilter):
    title = _('Category')
    parameter_name = 'categories'

    def lookups(self, request, model_admin): 
        '''Return all categories '''
        tenant_id = get_tenant_data(request).get('id') 
        
        return [
            (category.id, primary_language(category.name))
            for category in PersonCategory.objects.filter(
                tenant__id=tenant_id)  # Fetch all categories by tenant
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                category=self.value()
            )
        return queryset
