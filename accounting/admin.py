from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.utils import formats
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ExportMixin, ImportExportModelAdmin

from core.safeguards import get_tenant
from scerp.admin import (
     BaseAdmin, Display, verbose_name_field, set_inactive, set_protected)
from scerp.admin_site import admin_site     
from scerp.mixins import multi_language
from . import actions as a
from .models import (
    APISetup, Setting, CustomFieldGroup, CustomField,
    MappingId, Location, FiscalPeriod, Currency, Unit, Tax,
    Rounding, SequenceNumber, OrderCategory, OrderTemplate,
    CostCenter, Article, ChartOfAccountsTemplate,
    AccountPositionTemplate, ChartOfAccounts, AccountPosition,
    ACCOUNT_TYPE, CATEGORY_HRM
)


class CASH_CTRL:
    SUPER_USER_EDITABLE_FIELDS = [
        'message',
        'is_enabled_sync',
    ]
    FIELDS = [
        'c_id',
        'c_created',
        'c_created_by',
        'c_last_updated',
        'c_last_updated_by'
    ]
    REVENUE_FIELDS = [
        'c_rev_id',
        'c_rev_created',
        'c_rev_created_by',
        'c_rev_last_updated',
        'c_rev_last_updated_by'
    ]
    WARNING_READ_ONLY = _("Read only model. <i>Use cashControl for edits!</i>")


class MappingIdInline(admin.TabularInline):
    model = MappingId
    extra = 0  # Number of empty forms to display for new inlines
    fields = ('type', 'name', 'c_id', 'description')
    # readonly_fields = ('type', 'name', 'c_id', 'description')
    # can_delete = False  # Prevent deletion of inline objects

    def has_add_permission(self, request, obj=None):
        # Disable add permission for this inline
        return False

@admin.register(APISetup, site=admin_site)
class APISetupAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('tenant', 'org_name', 'api_key_hidden')
    search_fields = ('tenant', 'org_name')
    readonly_fields = ('display_data',)
    actions = [
        a.api_setup_get,
        a.init_setup,        
        a.api_setup_delete_hrm_accounts,
        a.api_setup_delete_system_accounts,
        a.api_setup_delete_hrm_categories,
        a.api_setup_delete_system_categories
    ]

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
    )

    inlines = [MappingIdInline]

    @admin.display(description=_('settings'))
    def display_data(self, obj):
        return Display.json(obj.data)


class CashCtrlAdmin(BaseAdmin):
    has_tenant_field = True

    def get_cash_ctrl_fields(self):        
        fields = CASH_CTRL.FIELDS + CASH_CTRL.SUPER_USER_EDITABLE_FIELDS
        if getattr(self, 'has_revenue_id', False):
            for field in CASH_CTRL.REVENUE_FIELDS:
                if field not in fields:
                    fields.append(field)
        return fields

    def get_readonly_fields(self, request, obj=None):
        ''' Extend readonly fields '''
        # Get readonly fields from parent
        readonly_fields = super().get_readonly_fields(request, obj)
        readonly_fields = list(readonly_fields)  # Ensure it's mutable

        # Adjust readonly_fields
        if getattr(self, 'is_readonly', None):
            all_fields = [
                field.name for field in self.model._meta.get_fields()]
            readonly_fields.extend(all_fields)
        else:
            # Add custom readonly fields
            readonly_fields.extend(self.get_cash_ctrl_fields())

        # Make sure 'disable_sync' is not in readonly_fields
        if request.user.is_superuser:
            for field in CASH_CTRL.SUPER_USER_EDITABLE_FIELDS:
                if field in readonly_fields:
                    readonly_fields.remove(field)

        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        # Add additional sections like Notes and Logging
        return super().get_fieldsets(request, obj) + (
            ('CashCtrl', {
                'fields': self.get_cash_ctrl_fields(),
                'classes': ('collapse',),
            }),
        )

    @admin.display(description=_('last update'))
    def display_last_update(self, obj):
        return obj.modified_at


@admin.register(Setting, site=admin_site)
class Setting(BaseAdmin):
    related_tenant_fields = ['setup']
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
        return Display.json(obj.data)


@admin.register(CustomFieldGroup, site=admin_site)
class CustomFieldGroupAdmin(CashCtrlAdmin):    
    has_tenant_field = True
    related_tenant_fields = ['setup']
    list_display = (
        'code', 'name', 'type', 'c_id', 'message', 'is_enabled_sync')
    search_fields = ('code', 'name')
    actions = [a.custom_group_field_get]

    fieldsets = (
        # Organization Details
        (None, {
            'fields': ('code', 'name', 'type'),
            'classes': ('expand',),
        }),
    )

@admin.register(CustomField, site=admin_site)
class CustomFieldAdmin(CashCtrlAdmin):    
    has_tenant_field = True
    list_display = ('code', 'group', 'name', 'data_type', 'c_id', 'message')
    search_fields = ('code', 'name')
    actions = [a.custom_field_get]

    fieldsets = (
        # Organization Details
        (None, {
            'fields': (
                'code', 'group', 'name', 'data_type', 'description',
                'is_multi', 'values'),
            'classes': ('expand',),
        }),
    )


class LocationResource(resources.ModelResource):
    class Meta:
        model = Location
        fields = ('id', 'name', 'type', 'address', 'zip', 'city')


@admin.register(Location, site=admin_site)
class Location(ImportExportModelAdmin, CashCtrlAdmin):
    related_tenant_fields = ['logo']
    resource_class = LocationResource
    has_tenant_field = True
    is_readonly = False
    # warning = CASH_CTRL.WARNING_READ_ONLY

    list_display = (
        'name', 'type', 'vat_uid', 'logo', 'address', 'display_last_update',
        'url')
    search_fields = ('name', 'vat_uid')
    list_filter = ('setup', 'type')
    actions = [a.location_get]

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

    @admin.display(description=_('Applikation link'))
    def url(self, obj):
        if obj.type == obj.TYPE.MAIN:
            link = obj.setup.url
            return Display.link(link, link)


@admin.register(FiscalPeriod, site=admin_site)
class FiscalPeriodAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    list_display = ('name', 'start', 'end', 'is_current', 'display_last_update')
    search_fields = ('name', 'start', 'end', 'is_current')
    list_filter = ('setup',)
    actions = [a.fiscal_period_get]

    fieldsets = (
        (None, {
            'fields': ('name', 'start', 'end', 'is_closed', 'is_current'),
            'classes': ('expand',),
        }),
    )


@admin.register(Currency, site=admin_site)
class CurrencyAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = False
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_description',)

    list_display = ('code', 'is_default', 'rate', 'display_last_update')
    search_fields = ('code',)
    list_filter = ('setup',)
    actions = [a.currency_get]

    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_description', 'is_default', 'rate', 'index',
                'description'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('description'))
    def display_description(self, obj):
        return multi_language(obj.description)


@admin.register(Unit, site=admin_site)
class UnitAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name',)

    list_display = ('display_name', 'is_default', 'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)

    actions = [a.unit_get]

    fieldsets = (
        (None, {
            'fields': ('display_name', 'is_default'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return multi_language(obj.name)


@admin.register(Tax, site=admin_site)
class TaxAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('local_name', 'local_document_name')

    list_display = (
        'local_name', 'local_document_name', 'display_percentage',
        'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)
    actions = [a.tax_get]

    fieldsets = (
        (None, {
            'fields': (
                'local_name', 'local_document_name', 'percentage',
                'calc_type', 'percentage_flat', 'account_id'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def local_name(self, obj):
        return multi_language(obj.name)

    @admin.display(description=_('show as'))
    def local_document_name(self, obj):
        return multi_language(obj.document_name)

    @admin.display(description=_("Percentage"))
    def display_percentage(self, obj):
        return Display.percentage(obj.percentage, 1)


@admin.register(Rounding, site=admin_site)
class RoundingAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('local_name',)

    list_display = (
        'local_name', 'rounding', 'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)
    actions = [a.rounding_get]

    fieldsets = (
        (None, {
            'fields': (
                'local_name', 'rounding', 'mode', 'account_id'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def local_name(self, obj):
        return multi_language(obj.name)


@admin.register(SequenceNumber, site=admin_site)
class SequenceNumberAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('local_name',)

    list_display = ('local_name', 'pattern', 'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)
    actions = [a.sequence_number_get]

    fieldsets = (
        (None, {
            'fields': (
                'local_name', 'pattern'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def local_name(self, obj):
        return multi_language(obj.name)


@admin.register(OrderCategory, site=admin_site)
class OrderCategoryAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name', 'display_status')

    list_display = ['display_name', 'due_days', 'display_last_update']
    search_fields = ['display_name', 'number']
    list_filter = ('setup',)
    actions = [a.order_category_get]

    fieldsets = (
        (None, {
            'fields': (
                'display_name', 'account_id', 'display_status', 'address_type',
                'due_days'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return multi_language(obj.name_plural)

    @admin.display(description=_('Stati'))
    def display_status(self, obj):
        stati = [multi_language(x['name']) for x in obj.status]
        return Display.list(stati)


@admin.register(OrderTemplate, site=admin_site)
class OrderTemplateAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    list_display = ('name', 'is_default', 'display_last_update')
    search_fields = ('name',)
    list_filter = ('setup',)
    actions = [a.order_template_get]

    fieldsets = (
        (None, {
            'fields': ('name', 'is_default'),
            'classes': ('expand',),
        }),
    )


@admin.register(CostCenter, site=admin_site)
class CostCenterAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name',)

    list_display = ('display_name', 'number', 'display_last_update')
    search_fields = ('name', 'number')
    list_filter = ('setup',)
    actions = [a.cost_center_get]

    fieldsets = (
        (None, {
            'fields': ('display_name', 'number'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return multi_language(obj.name)


@admin.register(Article, site=admin_site)
class ArticleAdmin(CashCtrlAdmin):
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY
    readonly_fields = ('display_name', 'display_sales_price')

    list_display = (
        'nr', 'display_name', 'display_sales_price', 'display_last_update')
    search_fields = ('name', 'nr')
    list_filter = ('is_stock_article', 'category_id')
    actions = [a.article_get]

    fieldsets = (
        (None, {
            'fields': (
                'name', 'description', 'nr', 'category_id', 'currency_id',
                'display_sales_price', 'last_purchase_price', 'is_stock_article',
                'min_stock', 'max_stock', 'stock', 'bin_location', 'location_id'
            ),
            'classes': ('expand',),
        }),
        (_('Advanced'), {
            'fields': ('is_purchase_price_gross', 'is_sales_price_gross',
                'sequence_number_id', 'custom'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('name'))
    def display_name(self, obj):
        return multi_language(obj.name)

    @admin.display(description=_('price in CHF'))
    def display_sales_price(self, obj):
        return Display.big_number(obj.sales_price)


@admin.register(ChartOfAccountsTemplate, site=admin_site)
class ChartOfAccountsTemplateAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = ('name', 'chart_version', 'link_to_positions')
    search_fields = ('name', 'account_type', 'canton', 'type')
    list_filter = ('account_type', 'type', 'canton', 'chart_version')
    readonly_fields = ('exported_at',)
    actions = [a.coac_positions_check, a.coac_positions_create]

    fieldsets = (
        (None, {
            'fields': ('name', 'account_type', 'canton', 'type', 'chart_version',
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
    related_tenant_fields = ['parent']
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
        return obj.account_number if obj.is_category else ''

    @admin.display(description=_('Position Nr.'))
    def position_number(self, obj):
        return '' if obj.is_category else obj.account_number

    @admin.display(
        description=verbose_name_field(AccountPosition, 'name'))
    def display_name(self, obj):
        return Display.name_w_levels(obj)


@admin.register(ChartOfAccounts, site=admin_site)
class ChartOfAccountsAdmin(BaseAdmin):
    related_tenant_fields = ['period']
    has_tenant_field = True
    list_display = (
        'display_name', 'chart_version', 'period', 'link_to_positions')
    search_fields = ('name',)
    # readonly_fields = ('period',)

    fieldsets = (
        (None, {
            'fields': (
                'name', 'chart_version', 'period', 'headings_w_numbers'),
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
    related_tenant_fields = [
        'setup', 'parent', 'chart', 'allocations', 'currency' ]
    has_tenant_field = True
    has_revenue_id = True
    is_readonly = False

    list_display = (
        'display_function', 'position_number', 'display_name',
        'display_end_amount_credit', 'display_end_amount_debit',
        'display_balance_credit', 'display_balance_debit',
        'display_budget', 'display_previous', 'display_cashctrl', 'responsible')
    list_display_links = ('display_name',)
    list_filter = ('account_type', 'chart', 'responsible')
    search_fields = ('function', 'account_number', 'number', 'name')
    readonly_fields = ('balance', 'budget', 'previous', 'number')
    list_per_page = 1000  # Show 1000 (i.e. all most probably) results per page

    fieldsets = (
        (None, {
            'fields': (
                'setup', 'chart', 'account_type', 'account_number', 'name', 
                'function', 'is_category', 'description', 
                'parent', 'number'),
            'classes': ('expand',),
        }),
        (_('Edit'), {
            'fields': ('balance', 'budget', 'previous',
                       'explanation', 'responsible', 'currency'),
            'classes': ('collapse',),
        }),
    )
    actions = [
        a.apm_add_income, a.apm_add_invest,
        a.check_accounts, a.account_names_convert_upper_case,
        a.upload_accounts, a.download_balances, a.get_balances,
        a.upload_balances,
        a.assign_responsible,
        set_inactive, set_protected, a.position_insert
    ]

    @admin.display(
        description=verbose_name_field(AccountPosition, 'name'))
    def display_name(self, obj):
        return Display.name_w_levels(obj)

    @admin.display(
        description=verbose_name_field(AccountPosition, 'function'))
    def display_function(self, obj):
        return obj.account_number if obj.is_category else ' '

    @admin.display(description=_('position nr.'))
    def position_number(self, obj):
        return ' ' if obj.is_category else obj.account_number

    @admin.display(description=_('actual +'))
    def display_end_amount_credit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.EXPENSE, CATEGORY_HRM.ASSET):
            balance = 0 if obj.end_amount is None else obj.end_amount
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('actual -'))
    def display_end_amount_debit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.REVENUE, CATEGORY_HRM.LIABILITY):
            balance = 0 if obj.end_amount is None else obj.end_amount
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('balance +'))
    def display_balance_credit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.EXPENSE, CATEGORY_HRM.ASSET):
            balance = 0 if obj.balance is None else obj.balance
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('balance -'))
    def display_balance_debit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.REVENUE, CATEGORY_HRM.LIABILITY):
            balance = 0 if obj.balance is None else obj.balance
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('balance'))
    def display_balance(self, obj):
        balance = 0 if obj.balance is None else obj.balance
        return Display.big_number(balance)

    @admin.display(description=_('budget'))
    def display_budget(self, obj):
        return Display.big_number(obj.budget)

    @admin.display(description=_('previous'))
    def display_previous(self, obj):
        return Display.big_number(obj.previous)

    @admin.display(description=_(''))
    def display_cashctrl(self, obj):
        if obj.c_id or obj.c_rev_id:
            return '🪙'  # (Coin): \U0001FA99
        return ' '
