# vault/admin.py
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.translation import gettext as _

from core.safeguards import get_tenant

from scerp.admin import (
    admin_site, BaseAdmin, display_empty, display_verbose_name,
    display_datetime, verbose_name_field)
    
from .models import (
    RegistrationPlanCanton, RegistrationPosition,
    LeadAgency, RetentionPeriod, LegalBasis, ArchivalEvaluation)

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


@admin.register(LeadAgency, site=admin_site) 
class LeadAgencyAdmin(BaseAdmin):
    list_display = ('name',)     


@admin.register(RetentionPeriod, site=admin_site) 
class RetentionPeriodAdmin(BaseAdmin):
    list_display = ('name',)          


@admin.register(LegalBasis, site=admin_site) 
class LegalBasisAdmin(BaseAdmin):
    list_display = ('name',)          


@admin.register(ArchivalEvaluation, site=admin_site) 
class ArchivalEvaluationAdmin(BaseAdmin):
    list_display = ('name',)          


@admin.register(RegistrationPosition, site=admin_site) 
class RegistrationPositionAdmin(BaseAdmin):
    list_display = (
        'number', 'position', 'display_lead_agency', 
        'display_retention_period', 'remarks')      
    list_display_links = ('position',)
    list_filter = (
        'registration_plan', 'lead_agency', 'retention_period',
        'legal_basis', 'archival_evaluation')
    search_fields = (
        'number', 'position', 'lead_agency__name', 'retention_period__name',
        'legal_basis__name', 'archival_evaluation__name')
    
    fieldsets = (
        (None, {
            'fields': (
                'number', 'position', 'lead_agency', 'retention_period'),
            'classes': ('expand',),            
        }),
        (_('Others'), {
            'fields': (
                'legal_basis', 'archival_evaluation', 'remarks', 
                'is_category'),
            'classes': ('collapse',),            
        }),        
    )

    @admin.display(        
        description=verbose_name_field(RegistrationPosition, 'lead_agency'))
    def display_lead_agency(self, obj):
        return display_empty(obj.lead_agency)

    @admin.display(
        description=verbose_name_field(RegistrationPosition, 'retention_period'))
    def display_retention_period(self, obj):
        return display_empty(obj.retention_period)
