# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant

from scerp.admin import (
    admin_site, BaseAdmin, display_empty, display_verbose_name,
    display_datetime)
    
from .models import (
    APISetup, Location, FiscalPeriod, Currency, ChartOfAccountsTemplate,
    AccountPositionTemplate, ChartOfAccounts, AccountPosition,
    CostCenter, TaxRate
)

from . import actions as a
from scerp.admin import verbose_name_field


@admin.register(APISetup, site=admin_site) 
class APISetupAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('tenant', 'org_name', 'api_key_hidden')
    search_fields = ('tenant', 'org_name')
    
    fieldsets = (
        (None, {
            'fields': ('org_name', 'api_key'),
            'classes': ('expand',),            
        }),     
    )


@admin.register(Location, site=admin_site) 
class Location(BaseAdmin):
    has_tenant_field = True
    list_display = ('tenant_location',)
    search_fields = ('tenant_location',)
    
    fieldsets = (
        (None, {
            'fields': ('tenant_location', ),
            'classes': ('expand',),            
        }),     
    )


@admin.register(FiscalPeriod, site=admin_site) 
class FiscalPeriodAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'start', 'end', 'is_current')
    search_fields = ('name', 'start', 'end', 'is_current')
    readonly_fields = ('is_current',)
    actions = [a.fiscal_period_set_current] 
    

@admin.register(Currency, site=admin_site) 
class CurrencyAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('code', 'is_default')
    search_fields = ('code',)        
    
    fieldsets = (
        (None, {
            'fields': ('code', 'description'),
            'classes': ('expand',),            
        }),
    )    


@admin.register(CostCenter, site=admin_site) 
class CostCenterAdmin(BaseAdmin):    
    has_tenant_field = True

    list_display = ['name', 'number']
    search_fields = ['number']

    fieldsets = (
        (None, {
            'fields': ('name',),
            'classes': ('expand',),            
        }),     
        (_('Details'), {
            'fields': ('number',),
            'classes': ('expand',),            
        })
    )


@admin.register(ChartOfAccountsTemplate, site=admin_site) 
class ChartOfAccountsTemplateAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = ('name', 'chart_version', 'link_to_positions')
    search_fields = ('name', 'account_type', 'canton', 'category')
    list_filter = ('account_type', 'category', 'canton', 'chart_version')    
    readonly_fields = ('exported_at',)
    actions = [a.coac_positions_check, a.coac_positions_create] 
    
    fieldsets = (
        (None, {
            'fields': ('name', 'account_type', 'canton', 'category', 'chart_version', 
                       'date'),
            'classes': ('expand',),            
        }),
        (_('Content'), {
            'fields': ('excel', 'exported_at'),
            'classes': ('expand',),            
        }),        
    )
    
    def custom_display_name(self, obj):
        # Return the modified display name for other contexts
        return f"Custom: {obj.name}"    

    @admin.display(description=_('Type - display positions'))
    def link_to_positions(self, obj):
        url = f"../accountpositiontemplate/?chart__id__exact={obj.id}"
        name = obj.get_account_type_display()
        return format_html(f'<a href="{url}">{name}</a>', url)



class AccountPositionAbstractAdmin(BaseAdmin):
    list_display_links = ('name',)
    search_fields = (
        'account_number', 'name', 'notes')    
    readonly_fields = ('chart', 'number')
    
    fieldsets = (
        (None, {
            'fields': ('account_number', 'name', 'description', 'is_category'),
            'classes': ('expand',),            
        }),
        (_('Others'), {
            'fields': ('number', 'chart'),
            'classes': ('collapse',),            
        }),        
    )

    @admin.display(description=_('Subject Nr.'))
    def category_number(self, obj):
        return obj.account_number if obj.is_category else ' '

    @admin.display(description=_('Position Nr.'))
    def position_number(self, obj):
        return ' ' if obj.is_category else obj.account_number

        
@admin.register(AccountPositionTemplate, site=admin_site) 
class AccountPositionTemplateAdmin(AccountPositionAbstractAdmin):
    has_tenant_field = False       
    list_display = ('category_number', 'position_number', 'name', )
    list_filter = (        
        'chart__account_type', 
        'chart__canton', 'chart__chart_version', 'chart')    
    actions = [a.apc_export_balance, a.apc_export_function_to_income,
               a.apc_export_function_to_invest, a.position_insert]


@admin.register(ChartOfAccounts, site=admin_site) 
class ChartOfAccountsAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'chart_version', 'link_to_positions')    
    search_fields = ('name',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'chart_version'),
            'classes': ('expand',),            
        }),
    )

    @admin.display(description=_('Type - display positions'))
    def link_to_positions(self, obj):
        url = f"../accountposition/?chart__id__exact={obj.id}"
        name = _('Positions')
        return format_html(f'<a href="{url}">{name}</a>', url)


@admin.register(AccountPosition, site=admin_site) 
class AccountPositionAdmin(AccountPositionAbstractAdmin):
    has_tenant_field = True
    list_display = (
        'display_function', 'account_number', 'name',)    
    list_filter = ('account_type', 'chart')
    fieldsets = (
        (None, {
            'fields': ('account_number', 'name', 'notes'),
            'classes': ('expand',),            
        }),
        (_('Others'), {
            'fields': ('function', 'number', 'hrm_1', 'description_hrm_1',  
                       'ff', 'is_category'),
            'classes': ('collapse',),            
        }),        
    )
    actions = [a.apm_add_income, a.apm_add_invest, a.position_insert]    
    
    @admin.display(
        description=verbose_name_field(AccountPosition, 'function'))
    def display_function(self, obj):
        return display_empty(obj.function)


@admin.register(TaxRate, site=admin_site) 
class TaxRateAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'percentage')
    search_fields = ('name', 'percentage')

    fieldsets = (
        (None, {
            'fields': ('name', 'percentage', 'account'),
            'classes': ('expand',),            
        }),       
    )