# vault/admin.py
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.safeguards import get_tenant

from scerp.admin import (
    admin_site, App, AppConfig, BaseAdmin, display_empty, display_verbose_name,
    display_datetime)
    
from .models import (
    RegistrationPlanCanton
)

from .locales import (
    APP, FIELDSET, REGISTRATION_PLAN)
# from . import actions as a

# init admin
app = App(APP)


@admin.register(RegistrationPlanCanton, site=admin_site) 
class RegistrationPlanCantonAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = (
        'name', 'canton', 'category', 'plan_version', 
        'display_exported_at')
    search_fields = ('name', 'canton', 'category')
    list_filter = ('category', 'canton', 'plan_version')    
    readonly_fields = ('exported_at',)
    # actions = [a.coac_positions_check, a.coac_positions_create] 
    
    fieldsets = (
        (None, {
            'fields': ('name', 'canton', 'category', 'plan_version', 'date'),
            'classes': ('expand',),            
        }),
        (FIELDSET.content, {
            'fields': ('excel', 'exported_at'),
            'classes': ('expand',),            
        }),        
    )
 
    @admin.display(
        description=display_verbose_name(REGISTRATION_PLAN, 'exported_at'))
    def display_exported_at(self, obj):
        return display_datetime(obj.exported_at)        
