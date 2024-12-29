# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.utils import formats
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant

from scerp.admin import (
    admin_site, BaseAdmin, display_empty, display_verbose_name,
    display_datetime, display_big_number, display_json, display_name_w_levels)

from .actions import init_setup, upload_accounts
from .models import (
    APISetup, Setting, Location, FiscalPeriod, Currency, Unit, Tax,
    CostCenter, ChartOfAccountsTemplate,
    AccountPositionTemplate, ChartOfAccounts, AccountPosition,
    ACCOUNT_TYPE, CATEGORY_HRM
)

from . import actions as a
from scerp.admin import (
    format_name, verbose_name_field, set_inactive, set_protected)


class CASH_CTRL:
    FIELDS = [
        'c_id',
        'c_created',
        'c_created_by',
        'c_last_updated',
        'c_last_updated_by'
    ]
    WARNING_READ_ONLY = _("Read only model. <i>Use cashControl for edits!</i>")


@admin.register(APISetup, site=admin_site)
class APISetupAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('tenant', 'org_name', 'api_key_hidden')
    search_fields = ('tenant', 'org_name')
    readonly_fields = ('display_data',)
    actions = [init_setup]

    fieldsets = (
        (None, {
            'fields': (
                'org_name',
                'api_key',
                'language',
                'display_data'
            ),
            'classes': ('expand',),
        }),
        (_('Edit data'), {
            'fields': (
                'data',
            ),
            'classes': ('collapse',),
        })
    )

    @admin.display(description=_('settings'))
    def display_data(self, obj):
        return display_json(obj.data)


class CashCtrlAdmin(BaseAdmin):
    has_tenant_field = True

    def get_readonly_fields(self, request, obj=None):
        ''' Extend readonly fields
        '''
        # Get readonly fields from parent
        readonly_fields = super().get_readonly_fields(request, obj)
        readonly_fields = list(readonly_fields)  # Ensure it's mutable

        # Adjust readonly_fields
        if getattr(self, 'is_readonly'):
            all_fields = [
                field.name for field in self.model._meta.get_fields()]
            readonly_fields.extend(all_fields)
        else:
            readonly_fields.extend(CASH_CTRL.FIELDS)  # Add custom readonly fields

        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        # Add additional sections like Notes and Logging
        return super().get_fieldsets(request, obj) + (
            ('CashCtrl', {
                'fields': CASH_CTRL.FIELDS,
                'classes': ('collapse',),
            }),
        )

    @admin.display(description=_('last update'))
    def display_last_update(self, obj):
        return obj.modified_at


@admin.register(Setting, site=admin_site)
class Setting(BaseAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    list_display = ('display_settings', 'modified_at')
    search_fields = ('setup',)
    list_filter = ('setup',)
    readonly_fields = ['display_data']  # Corrected

    fieldsets = (
        (None, {
            'fields': ('setup', 'display_data'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('settings'))
    def display_settings(self, obj):
        return _('settings')

    @admin.display(description=_('settings'))
    def display_data(self, obj):
        return display_json(obj.data)


@admin.register(Location, site=admin_site)
class Location(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    list_display = ('name', 'type', 'vat_uid', 'display_last_update')
    search_fields = ('name', 'vat_uid')
    list_filter = ('setup', 'type')

    fieldsets = (
        # Organization Details
        (None, {
            'fields': (
                'name', 'type', 'address', 'zip', 'city',
                'country', 'logo'),
            'classes': ('expand',),
        }),

        # Accounting Information
        (_('Accounting Information'), {
            'fields': (
                'bic', 'iban', 'qr_first_digits', 'qr_iban', 'vat_uid'
            ),
            'classes': ('expand',),
        }),

        # Layout
        (_('Layout'), {
            'fields': ('logo_file_id', 'footer'),
            'classes': ('collapse',),
        }),
    )


@admin.register(FiscalPeriod, site=admin_site)
class FiscalPeriodAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    list_display = ('name', 'start', 'end', 'is_current', 'display_last_update')
    search_fields = ('name', 'start', 'end', 'is_current')
    list_filter = ('setup',)
    actions = [a.fiscal_period_set_current]

    fieldsets = (
        (None, {
            'fields': ('name', 'start', 'end', 'is_closed', 'is_current'),
            'classes': ('expand',),
        }),
    )


@admin.register(Currency, site=admin_site)
class CurrencyAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_description',)

    list_display = ('code', 'is_default', 'rate', 'display_last_update')
    search_fields = ('code',)
    list_filter = ('setup',)

    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_description', 'is_default', 'rate', 'index'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('description'))
    def display_description(self, obj):
        return obj.local_description


@admin.register(Unit, site=admin_site)
class UnitAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name',)

    list_display = ('display_name', 'is_default', 'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)

    fieldsets = (
        (None, {
            'fields': ('display_name', 'is_default'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return obj.local_name


@admin.register(Tax, site=admin_site)
class TaxAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name',)

    list_display = ('display_name', 'percentage', 'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)

    fieldsets = (
        (None, {
            'fields': ('display_name', 'percentage'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return obj.local_name


@admin.register(CostCenter, site=admin_site)
class CostCenterAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name',)

    list_display = ['display_name', 'number', 'display_last_update']
    search_fields = ['display_name', 'number']
    list_filter = ('setup',)

    fieldsets = (
        (None, {
            'fields': ('display_name', 'number'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return obj.local_name


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


@admin.register(AccountPositionTemplate, site=admin_site)
class AccountPositionTemplateAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = ('category_number', 'position_number', 'display_name', )
    list_filter = (
        'chart__account_type',
        'chart__canton', 'chart__chart_version', 'chart')
    list_display_links = ('display_name',)
    search_fields = ('account_number', 'name', 'notes', 'number')    
    readonly_fields = ('chart', 'number')
    
    actions = [a.apc_export_balance, a.apc_export_function_to_income,
               a.apc_export_function_to_invest, a.position_insert]

    fieldsets = (
        (None, {
            'fields': (
                'account_number', 'name', 'description', 'is_category',
                'parent'),
            'classes': ('expand',),
        }),
        (_('Others'), {
            'fields': ('number', 'chart'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Subject Nr.'))
    def category_number(self, obj):
        return obj.account_number if obj.is_category else display_empty()

    @admin.display(description=_('Position Nr.'))
    def position_number(self, obj):
        return display_empty() if obj.is_category else obj.account_number

    @admin.display(
        description=verbose_name_field(AccountPosition, 'name'))
    def display_name(self, obj):
        return display_name_w_levels(obj)


@admin.register(ChartOfAccounts, site=admin_site)
class ChartOfAccountsAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = (
        'display_name', 'chart_version', 'period', 'link_to_positions')
    search_fields = ('name',)
    # readonly_fields = ('period',)
    actions = [upload_accounts]

    fieldsets = (
        (None, {
            'fields': ('name', 'chart_version', 'period'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('Position Nr.'))
    def display_name(self, obj):
        return obj.full_name()

    @admin.display(description=_('Show positions'))
    def link_to_positions(self, obj):
        links = []
        for account_type in ACCOUNT_TYPE:
            url = (f'../accountposition/?chart__id__exact={obj.id}'
                   f'&account_type__exact={account_type}')
            name = account_type.label
            # Use format_html correctly
            links.append(format_html('<a href="{}">{}</a>', url, name))
        # Join the links with commas and return
        return format_html(', '.join(links))


@admin.register(AccountPosition, site=admin_site)
class AccountPositionAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = False

    list_display = (
        'display_function', 'position_number', 'display_name',
        'display_balance_credit', 'display_balance_debit',
        'display_budget', 'display_previous')
    list_display_links = ('display_name',)
    list_filter = ('account_type', 'chart', 'responsible')
    readonly_fields = ('balance', 'budget', 'previous')
    list_per_page = 500  # Show 500 results per page

    fieldsets = (
        (None, {
            'fields': ('account_type', 'account_number', 'function',
                       'is_category', 'name', 'description', 'chart',
                       'parent'),
            'classes': ('expand',),
        }),
        (_('Edit'), {
            'fields': ('balance', 'budget', 'previous',
                       'explanation', 'responsible'),
            'classes': ('collapse',),
        }),
    )
    actions = [
        a.apm_add_income, a.apm_add_invest, a.position_insert,
        a.check_accounts, set_inactive, set_protected
    ]

    @admin.display(
        description=verbose_name_field(AccountPosition, 'name'))
    def display_name(self, obj):
        return display_name_w_levels(obj)

    @admin.display(
        description=verbose_name_field(AccountPosition, 'function'))
    def display_function(self, obj):
        return obj.account_number if obj.is_category else display_empty()

    @admin.display(description=_('position nr.'))
    def position_number(self, obj):
        return display_empty() if obj.is_category else obj.account_number

    @admin.display(description=_('balance +'))
    def display_balance_credit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.EXPENSE, CATEGORY_HRM.ASSET):
            balance = 0 if obj.balance is None else obj.balance
            return display_big_number(balance)
        else:
            return display_empty()

    @admin.display(description=_('balance -'))
    def display_balance_debit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.REVENUE, CATEGORY_HRM.LIABILITY):
            balance = 0 if obj.balance is None else obj.balance
            return display_big_number(balance)
        else:
            return display_empty()

    @admin.display(description=_('balance'))
    def display_balance(self, obj):
        balance = 0 if obj.balance is None else obj.balance
        return display_big_number(balance)

    @admin.display(description=_('budget'))
    def display_budget(self, obj):
        return display_big_number(obj.budget)

    @admin.display(description=_('previous'))
    def display_previous(self, obj):
        return display_big_number(obj.previous)
