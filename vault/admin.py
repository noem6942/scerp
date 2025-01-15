# vault/admin.py
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.translation import gettext as _

from core.safeguards import get_tenant

from scerp.admin import admin_site, BaseAdmin, Display, verbose_name_field
    
from .models import (
    RegistrationPlanCanton, RegistrationPositionCanton,
    LeadAgencyCanton, RetentionPeriodCanton, LegalBasisCanton, 
    ArchivalEvaluationCanton)

from . import actions as a


@admin.register(RegistrationPlanCanton, site=admin_site) 
class RegistrationPlanCantonAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = (
        'name', 'canton', 'category', 'plan_version', 
        'display_exported_at')
    search_fields = ('name', 'canton', 'category')
    list_filter = ('category', 'canton', 'plan_version')    
    readonly_fields = ('exported_at',)
    actions = [a.canton_positions_check, a.canton_positions_create]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'canton', 'category', 'plan_version', 'date'),
            'classes': ('expand',),            
        }),
        (_('content'), {
            'fields': ('excel', 'exported_at', 'website_url'),
            'classes': ('expand',),            
        }),        
    )
 
    @admin.display(
        description=verbose_name_field(RegistrationPlanCanton, 'exported_at'))        
    def display_exported_at(self, obj):
        return Display.datetime(obj.exported_at)        


@admin.register(LeadAgencyCanton, site=admin_site) 
class LeadAgencyCantonAdmin(BaseAdmin):
    list_display = ('name',)     


@admin.register(RetentionPeriodCanton, site=admin_site) 
class RetentionPeriodCantonAdmin(BaseAdmin):
    list_display = ('name',)          


@admin.register(LegalBasisCanton, site=admin_site) 
class LegalBasisCantonAdmin(BaseAdmin):
    list_display = ('name',)          


@admin.register(ArchivalEvaluationCanton, site=admin_site) 
class ArchivalCantonEvaluationAdmin(BaseAdmin):
    list_display = ('name',)          


@admin.register(RegistrationPositionCanton, site=admin_site) 
class RegistrationPositionCantonAdmin(BaseAdmin):
    list_display = (
        'heading_number', 'position_number', 'hierarchy_name', 'lead_agency', 
        'retention_period', 'remarks')      
    list_display_links = ('indent_name',)
    list_filter = (
        'registration_plan', 'lead_agency', 'retention_period',
        'legal_basis', 'archival_evaluation')
    search_fields = (
        'number', 'name', 'lead_agency__name', 'retention_period__name',
        'legal_basis__name', 'archival_evaluation__name')
    
    fieldsets = (
        (None, {
            'fields': (
                'number', 'name', 'lead_agency', 'retention_period'),
            'classes': ('expand',),            
        }),
        (_('Others'), {
            'fields': (
                'legal_basis', 'archival_evaluation', 'remarks', 
                'is_category', 'level'),
            'classes': ('collapse',),            
        }),        
    )
 
    @admin.display(description=_('#cat'))
    def heading_number(self, obj):     
        if obj.is_category:
            return Display.hierarchy(obj.level, obj.number)    
        else:
            return ' '
 
    @admin.display(description=_('#pos'))
    def position_number(self, obj):     
        if obj.is_category:
            return ' '
        else:
            return obj.number
 
    @admin.display(        
        description=verbose_name_field(RegistrationPositionCanton, 'name'))
    def hierarchy_name(self, obj):    
        if obj.is_category:    
            return Display.hierarchy(obj.level, obj.name)    
        else:
            return obj.name
