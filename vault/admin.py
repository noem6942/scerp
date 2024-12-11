# vault/admin.py
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.translation import gettext as _

from core.safeguards import get_tenant

from scerp.admin import (
    admin_site, BaseAdmin, display_empty, display_verbose_name,
    display_datetime, verbose_name_field, format_hierarchy)
    
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
        return display_datetime(obj.exported_at)        


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
        'heading_number', 'position_number', 'hierarchy_name', 'display_lead_agency', 
        'display_retention_period', 'display_remarks')      
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
            return format_hierarchy(obj.level, obj.number)    
        else:
            return display_empty()
 
    @admin.display(description=_('#pos'))
    def position_number(self, obj):     
        if obj.is_category:
            return display_empty()
        else:
            return obj.number
 
    @admin.display(        
        description=verbose_name_field(RegistrationPositionCanton, 'name'))
    def hierarchy_name(self, obj):    
        if obj.is_category:    
            return format_hierarchy(obj.level, obj.name)    
        else:
            return obj.name

    @admin.display(        
        description=verbose_name_field(
            RegistrationPositionCanton, 'lead_agency'))
    def display_lead_agency(self, obj):
        return display_empty(obj.lead_agency)

    @admin.display(
        description=verbose_name_field(
            RegistrationPositionCanton, 'retention_period'))
    def display_retention_period(self, obj):
        return display_empty(obj.retention_period)

    @admin.display(
        description=verbose_name_field(RegistrationPositionCanton, 'remarks'))
    def display_remarks(self, obj):
        return display_empty(obj.remarks)
