# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.safeguards import get_tenant

from scerp.admin import (
    admin_site, App, AppConfig, BaseAdmin, display_empty, display_verbose_name,
    display_datetime)
    
from .models import (
    APISetup, Location, FiscalPeriod, Currency, ChartOfAccountsCanton,
    AccountPositionCanton, AccountChartMunicipality, 
    AccountPositionMunicipality,
    CostCenter, TaxRate
)

from .locales import (
    APP, FIELDSET, ACCOUNT_POSITION, CHART_OF_ACCOUNTS, 
    ACCOUNT_POSITION_MUNICIPALITY)
from . import actions as a

# init admin
app = App(APP)


class CashCtrlDescription(ModelAdmin):    
    '''Abstract class for name, description field 
    '''    
    @admin.display(
        description=display_verbose_name(CHART_OF_ACCOUNTS, 'name'))
    def description(self, obj):
        return obj.description


class CashCtrlName(ModelAdmin):    
    '''Abstract class for name, description field 
    '''    
    @admin.display(
        description=display_verbose_name(CHART_OF_ACCOUNTS, 'name'))
    def name(self, obj):
        return obj.name


@admin.register(APISetup, site=admin_site) 
class APISetupAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('tenant', 'org_name', 'api_key_hidden')
    search_fields = ('tenant', 'org_name')
    actions = [a.api_init] 
    
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
class CurrencyAdmin(BaseAdmin, CashCtrlDescription):
    has_tenant_field = True
    list_display = ('code', 'is_default')
    search_fields = ('code',)        
    
    fieldsets = (
        (None, {
            'fields': ('description_de', 'code'),
            'classes': ('expand',),            
        }),     
        ('International', {
            'fields': ('description_fr', 'description_it', 'description_en'),
            'classes': ('collapse',),            
        })
    )    


@admin.register(CostCenter, site=admin_site) 
class CostCenterAdmin(BaseAdmin, CashCtrlName):    
    has_tenant_field = True

    list_display = ['name', 'number'] + ['name_de']
    search_fields = ['number'] + ['name_de']

    fieldsets = (
        (None, {
            'fields': ('name_de',),
            'classes': ('expand',),            
        }),     
        ('International', {
            'fields': ('name_fr', 'name_it', 'name_en'),
            'classes': ('collapse',),            
        }),     
        ('Details', {
            'fields': ('number',),
            'classes': ('expand',),            
        })
    )


@admin.register(ChartOfAccountsCanton, site=admin_site) 
class ChartOfAccountsCantonAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = (
        'name', 'type', 'canton', 'category', 'chart_version', 
        'display_exported_at')
    search_fields = ('name', 'type', 'canton', 'category')
    list_filter = ('type', 'category', 'canton', 'chart_version')    
    readonly_fields = ('exported_at',)
    actions = [a.coac_positions_check, a.coac_positions_create] 
    
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'canton', 'category', 'chart_version', 
                       'date'),
            'classes': ('expand',),            
        }),
        (FIELDSET.content, {
            'fields': ('excel', 'exported_at'),
            'classes': ('expand',),            
        }),        
    )
    
    def custom_display_name(self, obj):
        # Return the modified display name for other contexts
        return f"Custom: {obj.name}"    
 
    @admin.display(
        description=display_verbose_name(CHART_OF_ACCOUNTS, 'exported_at'))
    def display_exported_at(self, obj):
        return display_datetime(obj.exported_at)        


class AccountPositionAbstractAdmin(BaseAdmin):
    list_display_links = ('name',)
    search_fields = (
        'account_number', 'account_4_plus_2', 'name', 'notes')    
    #readonly_fields = (
    #    'chart_of_accounts', 'hrm_1', 'hrm_2')    
    
    fieldsets = (
        (None, {
            'fields': ('account_number', 'account_4_plus_2', 'name', 'notes'),
            'classes': ('expand',),            
        }),
        (FIELDSET.others, {
            'fields': ('number', 'hrm_1', 'description_hrm_1',  
                       'ff', 'is_category'),
            'classes': ('collapse',),            
        }),        
    )

        
@admin.register(AccountPositionCanton, site=admin_site) 
class AccountPositionCantonAdmin(AccountPositionAbstractAdmin):
    has_tenant_field = False       
    list_display = (
        'account_number', 'account_4_plus_2', 
        'name', )    # 'chart_of_accounts', 
    list_filter = (        
        'chart_of_accounts__type', 'chart_of_accounts__category', 
        'chart_of_accounts__canton', 'chart_of_accounts__chart_version')    
    actions = [a.apc_export_balance, a.apc_export_function_to_income,
               a.apc_export_function_to_invest, a.position_insert]


@admin.register(AccountChartMunicipality, site=admin_site) 
class AccountChartMunicipalityAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'period')
    list_filter = ('period',)
    search_fields = ('name', 'period')


@admin.register(AccountPositionMunicipality, site=admin_site) 
class AccountPositionMunicipalityAdmin(AccountPositionAbstractAdmin):
    has_tenant_field = True
    list_display = (
        'display_function', 'account_number', 'account_4_plus_2', 'name',)    
    list_filter = ('display_type', 'chart')
    fieldsets = (
        (None, {
            'fields': ('account_number', 'account_4_plus_2', 'name', 'notes'),
            'classes': ('expand',),            
        }),
        (FIELDSET.others, {
            'fields': ('function', 'number', 'hrm_1', 'description_hrm_1',  
                       'ff', 'is_category'),
            'classes': ('collapse',),            
        }),        
    )
    actions = [a.apm_add_income, a.apm_add_invest, a.position_insert]    
    
    @admin.display(
        description=(
            ACCOUNT_POSITION_MUNICIPALITY.Field.function['verbose_name']))
    def display_function(self, obj):
        if obj.account_4_plus_2:
            return ''
        else:
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