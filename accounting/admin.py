from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import CharField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import formats
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportActionMixin

from core.admin import AttachmentInline, FIELDS as CORE_FIELDS
from core.models import Country, Address, Contact
from core.safeguards import get_tenant, save_logging
from scerp.actions import set_inactive, set_protected
from scerp.admin import (
     BaseAdmin, BaseAdminNew, BaseTabularInline, ReadOnlyAdmin, Display,
     verbose_name_field, make_language_fields)
from scerp.admin_base import (
    TenantFilteringAdmin, FIELDS as BASE_FIELDS, FIELDSET as BASE_FIELDSET)
from scerp.admin_site import admin_site
from scerp.mixins import primary_language, show_hidden

from . import forms, models, actions as a
from .admin_base import FIELDS, FIELDSET, CashCtrlAdmin
from .api_cash_ctrl import URL_ROOT as cashControl_URL_ROOT
from .resources import (
    LedgerBalanceResource, LedgerPLResource, LedgerICResource
)


@admin.register(models.APISetup, site=admin_site)
class APISetupAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']

    # Display these fields in the list view
    list_display = ('tenant', 'org_name', 'display_link', 'display_api_key')
    readonly_fields = ('display_name',) + BASE_FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('tenant', 'org_name')

    # Actions
    actions = [
        a.init_setup,
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'org_name',
                'api_key',
                'language',
                'is_default'
            ),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT
    )

    @admin.display(description=_('API Key'))
    def display_api_key(self, obj):
        return show_hidden(obj.api_key)

    @admin.display(description=_('Link'))
    def display_link(self, obj):
        url = cashControl_URL_ROOT.format(org=obj.org_name)
        return format_html(f'<a href="{url}" target="new">{url}</a>', url)


@admin.register(models.CustomFieldGroup, site=admin_site)
class CustomFieldGroupAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['setup', 'tenant']

    # Display these fields in the list view
    list_display = ('code', 'display_name', 'type') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'type'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.CustomField, site=admin_site)
class CustomFieldAdmin(TenantFilteringAdmin, BaseAdminNew):
    protected_foreigns = ['tenant', 'setup', 'group']

    # Display these fields in the list view
    list_display = (
        'code', 'group', 'display_name', 'data_type') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type','data_type',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'group', 'name', 'data_type', 'description',
                'is_multi', 'values'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Setting, site=admin_site)
class SettingAdmin(TenantFilteringAdmin, BaseAdminNew, ReadOnlyAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']
    help_text = _("Read only model. Use cashControl for edits.")

    # Display these fields in the list view
    list_display = FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'csv_delimiter',
                'thousand_separator',
                'first_steps_logo',
                'first_steps_account',
                'first_steps_currency',
                'first_steps_pro_demo',
                'first_steps_tax_rate',
                'first_steps_tax_type',
                'order_mail_copy_to_me',
                'tax_accounting_method',
                'journal_import_force_sequence_number'
            ),
            'classes': ('expand',),
        }),
        (_("Account Settings"), {
            'fields': (
                'default_debtor_account',
                'default_opening_account',
                'default_creditor_account',
                'default_exchange_diff_account',
                'default_profit_allocation_account',
                'default_inventory_disposal_account',
                'default_input_tax_adjustment_account',
                'default_sales_tax_adjustment_account',
                'default_inventory_depreciation_account',
                'default_inventory_asset_revenue_account',
                'default_inventory_article_expense_account',
                'default_inventory_article_revenue_account',
            ),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Location, site=admin_site)
class Location(TenantFilteringAdmin, BaseAdminNew, ReadOnlyAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']
    help_text = _("Read only model. Use cashControl for edits.")

    # Display these fields in the list view
    list_display = ('name', 'type', 'address', ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name', 'vat_uid')
    list_filter = ('type',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
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
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Applikation link'))
    def url(self, obj):
        if obj.type == obj.TYPE.MAIN:
            link = obj.setup.url
            return Display.link(link, link)


@admin.register(models.FiscalPeriod, site=admin_site)
class FiscalPeriodAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']

    # Display these fields in the list view
    list_display = ('name', 'start', 'end', 'is_current', 'display_last_update')
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    
    # Search, filter
    search_fields = ('name', 'start', 'end', 'is_current')
    list_filter = ('is_current',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('name', 'start', 'end', 'is_closed', 'is_current'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Unit, site=admin_site)
class UnitAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']

    # Helpers
    form = forms.UnitAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name') + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('code', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Display these fields in the list view
    search_fields = ('code', 'name')
    # list_filter = ('code',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', *make_language_fields('name')),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Tax, site=admin_site)
class TaxAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']

    # Helpers
    form = forms.TaxAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'display_percentage') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = (
        'display_name', 'display_document_name', 'display_percentage_flat'
    ) + FIELDS.C_READ_ONLY
    list_display_links = ('code', 'display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('percentage',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'display_name', 'code', 'percentage', 'calc_type',
                'percentage_flat', 'account'
            ),
            'classes': ('expand',),
        }),
        (_('Text'), {
            'fields': (
                *make_language_fields('name'),
                *make_language_fields('document_name'),
            ),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Rounding, site=admin_site)
class RoundingAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']

    # Helpers
    form = forms.RoundingAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'rounding') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Display these fields in the list view
    search_fields = ('code', 'name')
    list_filter = ('mode',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'account', 'rounding', 'mode',
                *make_language_fields('name'),),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        return primary_language(obj.name)


@admin.register(models.SequenceNumber, site=admin_site)
class SequenceNumberAdmin(TenantFilteringAdmin, BaseAdminNew, ReadOnlyAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']
    help_text = _("Read only model. Use cashControl for edits.")    

    # Display these fields in the list view
    list_display = ('display_name', 'pattern') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name',)
    list_filter = ('setup',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'pattern', 'name'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.CostCenterCategory, site=admin_site)
class CostCenterCategoryAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'parent']

    # Helpers
    form = forms.CostCenterCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'display_name', 'number', 'display_parent') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name', 'number')
    list_filter = ('setup',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'parent', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.CostCenter, site=admin_site)
class CostCenterAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'category']

    # Helpers
    form = forms.CostCenterAdminForm
    # Display these fields in the list view
    list_display = (
        'display_name', 'number', 'category') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name', 'number')
    list_filter = ('category',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'category', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Currency, site=admin_site)
class CurrencyAdmin(TenantFilteringAdmin, BaseAdminNew, ReadOnlyAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']
    help_text = _("Read only model. Use cashControl for edits.")

    # Helpers
    form = forms.CurrencyAdminForm

    # Display these fields in the list view
    list_display = ('code', 'is_default', 'rate') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_description',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'description')
    list_filter = ('is_default',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_description', 'is_default', 'rate'),
            'classes': ('expand',),
        }),
        (_('Description'), {
            'fields': (*make_language_fields('description'), ),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.AccountCategory, site=admin_site)
class AccountCategoryAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'parent']

    # Helpers
    form = forms.AccountCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'number', 'display_name', 'display_parent'
    ) + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('number', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    ordering = [Cast('number', CharField())]

    # Search, filter
    search_fields = ('name', 'number')
    # list_filter = (TenantFilteredSetupListFilter,)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('number', 'parent', *make_language_fields('name'),),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


class AllocationsInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'to_cost_center']

    # Inline
    model = models.Allocation
    fields = ['share', 'to_cost_center']  # Only show these fields
    extra = 1  # Number of empty forms displayed
    autocomplete_fields = ['account']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model


@admin.register(models.Account, site=admin_site)
class AccountAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'category', 'currency']

    # Helpers
    form = forms.AccountAdminForm

    # Display these fields in the list view
    list_display = (
        'display_number', 'function', 'hrm', 'display_name', 'category'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('display_number', 'function', 'hrm', 'display_name',)
    readonly_fields = ('display_name', 'function', 'hrm') + FIELDS.C_READ_ONLY
    ordering = ['function', 'hrm', 'number']

    # Search, filter
    search_fields = ('name', 'number', 'function', 'hrm')
    list_filter = ('function', 'hrm')

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    # Inlines
    inlines = [AllocationsInline]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'category', *make_language_fields('name'),
                'currency', 'budget', 'target_max', 'target_min', 'function',
                'hrm'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


# Order Management ---------------------------------------------------------
@admin.register(models.OrderTemplate, site=admin_site)
class OrderTemplateAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup']
    
    # Display these fields in the list view
    list_display = ('name', 'is_default') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name',)

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'name', 'css', 'footer', 'html', 'is_default', 
                'is_display_document_name', 'is_display_item_article_nr', 
                'is_display_item_price_rounded', 'is_display_item_tax', 
                'is_display_item_unit', 'is_display_logo', 
                'is_display_org_address_in_window', 'is_display_page_nr', 
                'is_display_payments', 'is_display_pos_nr', 
                'is_display_recipient_nr', 'is_display_responsible_person',
                'is_display_zero_tax', 'is_overwrite_css', 'is_overwrite_html', 
                'is_qr_empty_amount', 'is_qr_no_lines', 
                'is_qr_no_reference_nr', 'letter_paper_file_id', 'logo_height',
                'page_size'
            ),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )
    

@admin.register(models.BookTemplate, site=admin_site)
class BookTemplateAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'credit_account', 'debit_account', 'tax'
    ]

    # Helpers
    form = forms.BookTemplateAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'type', 'display_name',  'credit_account', 'debit_account',
        'tax'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'type', *make_language_fields('name'),
                'credit_account', 'debit_account', 'tax'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.OrderCategoryContract, site=admin_site)
class OrderCategoryContractAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'template']

    # Helpers
    form = forms.OrderCategoryContractAdminForm

    # Display these fields in the list view
    list_display = (
        'type', 'code', 'display_name_plural') + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('type', 'code', 'display_name_plural')        
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name_singular', 'name_plural')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'type', 
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'), 
                'template', 'status_data', 'book_template_data'
            ),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.OrderCategoryIncoming, site=admin_site)
class OrderCategoryIncomingAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'credit_account', 'expense_account', 'bank_account',
        'tax', 'currency', 'template'
    ]

    # Helpers
    form = forms.OrderCategoryIncomingAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name_plural', 'expense_account', 'currency'
    ) + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('code', 'display_name_plural')
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'), 'template'
            ),
            'classes': ('expand',),
        }),
        (_('Booking'), {
            'fields': (
                'address_type', 'credit_account', 'expense_account',
                'bank_account', 'tax', 'rounding', 'currency', 'due_days',
                'status_data', 'book_template_data'
            ),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.OrderContract, site=admin_site)
class OrderContractAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'associate', 'category', 'currency',
        'responsible_person'
    ]

    # Display these fields in the list view
    list_display = (
        'date', 'display_category_type', 'description', 'display_supplier',
        'price_excl_vat', 'currency', 'status'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('date', 'display_category_type', 'description')

    # Search, filter
    search_fields = ('supplier__company', 'description')
    list_filter = ('category', 'status', 'date')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'category', 'associate', 'status', 'description', 'date',
                'price_excl_vat', 'currency'),
            'classes': ('expand',),
        }),
        (_('Contractual'), {
            'fields': (
                'valid_from', 'valid_until', 'notice_period_month',
                'responsible_person'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    inlines = [AttachmentInline]

    @admin.display(description=_('Partner'))
    def display_supplier(self, obj):
        return self.display_link_to_company(obj.associate)

@admin.register(models.IncomingOrder, site=admin_site)
class IncomingOrderAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'contract', 'category', 'responsible_person'
    ]

    # Display these fields in the list view
    list_display = (
        'date', 'display_category_type', 'description', 'display_supplier',
        'price_incl_vat', 'category__currency', 'status'
    )  + CORE_FIELDS.ICON_DISPLAY + FIELDS.C_DISPLAY_SHORT
    list_display_links = (
        'date', 'display_category_type', 'description'
    ) + CORE_FIELDS.LINK_ATTACHMENT
    readonly_fields = ('display_category_type',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('contract__associate_company', 'description')
    list_filter = ('category', 'status', 'date')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'category', 'contract', 'status', 'description', 'date',
                'price_incl_vat', 'due_days', 'responsible_person'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )
    
    inlines = [AttachmentInline]

    @admin.display(description=_('Partner'))
    def display_supplier(self, obj):
        return self.display_link_to_company(obj.contract.associate)


@admin.register(models.IncomingBookEntry, site=admin_site)
class IncomingBookEntry(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'order'
    ]

    # Display these fields in the list view
    list_display = (
        'date', 'order'
    )  + CORE_FIELDS.ICON_DISPLAY + FIELDS.C_DISPLAY_SHORT
    list_display_links = (
        'date', 'order'
    ) + CORE_FIELDS.LINK_ATTACHMENT
    readonly_fields =  FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('date',)
    list_filter = ('date',)

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('date', 'order', 'template_id'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.ArticleCategory, site=admin_site)
class ArticleCategoryAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'purchase_account',  'sales_account', 'sequence_nr'
    ]

    # Helpers
    form = forms.ArticleCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'display_parent') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('code', 'display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('setup',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', *make_language_fields('name'), 'sales_account'
            ),
            'classes': ('expand',),
        }),
        (_("Extra"), {
            'fields': (
                'parent', 'purchase_account', 'sequence_nr'
            ),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Article, site=admin_site)
class ArticleAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'category', 'currency', 'location', 'sequence_nr',
        'unit'
    ]

    # Helpers
    form = forms.ArticleAdminForm

    # Display these fields in the list view
    list_display = (
        'nr', 'display_name', 'sales_price', 'unit') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('nr', 'display_name')

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('category',)

    # Actions
    actions = [
        a.accounting_get_data,
        a.de_sync_accounting,
        a.sync_accounting
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'nr', 'category', *make_language_fields('name'),
                'sales_price', 'unit', *make_language_fields('description')),
            'classes': ('expand',),
        }),
        (_("Stock Management"), {
            'fields': (
                'location', 'bin_location', 'is_stock_article', 'stock',
                'min_stock', 'max_stock', 'sequence_nr'),
            'classes': ('collapse',),
        }),
        (_("Pricing"), {
            'fields': ('currency', 'last_purchase_price',
                       'is_sales_price_gross', 'is_purchase_price_gross'),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


# Ledger -------------------------------------------------------------------
@admin.register(models.Ledger, site=admin_site)
class LedgerAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'setup', 'period']

    # Helpers
    form = forms.LedgerAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'period',
        'link_to_balance', 'link_to_pl', 'link_to_ic',
        'display_current')
    list_display_links = ('code', 'display_name', )

    # Search, filter
    search_fields = ('code', 'name', 'period__name')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', *make_language_fields('name'), 'period'),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    list_per_page = 500  # Show 500 rows per page

    # Actions
    actions = [a.add_balance, a.add_pl, a.add_ic]

    @admin.display(description=_('Current'))
    def display_current(self, obj):
        return Display.boolean(obj.period.is_current)

    @admin.display(description=_('Balance'))
    def link_to_balance(self, obj):
        url = f"../ledgerbalance/?ledger__id__exact={obj.id}"
        return format_html(f'<a href="{url}">{_("Balance")}</a>', url)

    @admin.display(description=_('P&L'))
    def link_to_pl(self, obj):
        url = f"../ledgerpl/?ledger__id__exact={obj.id}"
        return format_html(f'<a href="{url}">{_("P/L")}</a>', url)

    @admin.display(description=_('IC'))
    def link_to_ic(self, obj):
        url = f"../ledgeric/?ledger__id__exact={obj.id}"
        return format_html(f'<a href="{url}">{_("IC")}</a>', url)


class LedgerBaseAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Display
    list_display_links = ('display_account_name',)
    list_per_page = 1000  # Show 1000 i.e. most probably all results per page
    ordering = ['function', '-type' ,'hrm']

    # Search, filter
    search_fields = ('function', 'hrm', 'name')

    # Actions
    actions = [
        a.download_balances,
        a.get_balances,
        a.upload_balances,
        a.add_excel_to_ledger
    ]

    # Methods
    def get_import_data(self, request, *args, **kwargs):
        # Pass the request to the import
        return self.resource_class.import_data(
            request=request, *args, **kwargs)

    @admin.display(description=_('Function'))
    def display_function(self, obj):
        if obj.type == self.model.TYPE.CATEGORY:
            function = str(obj.function)
            if obj.function in [2, 26, 260]:
                function = '0' + function  # add leading zero
            return function
        return ' '

    @admin.display(description=_('HRM 2'))
    def display_hrm(self, obj):
        if obj.type == self.model.TYPE.ACCOUNT:
            return str(obj.hrm)
        return ' '

    @admin.display(description=_('Name'))
    def display_account_name(self, obj):
        name = primary_language(obj.name)
        if obj.type == self.model.TYPE.CATEGORY:
            if len(obj.hrm) == 1:
                name = name.upper()
            return format_html(f"<b>{name}</b>")
        return format_html(name)

    @admin.display(description=_('C-ids'))
    def display_c_ids(self, obj):
        return obj.cash_ctrl_ids


@admin.register(models.LedgerBalance, site=admin_site)
class LedgerBalanceAdmin(ExportActionMixin, LedgerBaseAdmin):
    """
    Django Admin for LedgerBalance model.
    """
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'ledger', 'parent', 'account', 'category'
    ]

    # Helpers
    form = forms.LedgerBalanceAdminForm
    resource_class = LedgerBalanceResource

    # Display these fields in the list view
    list_display = (
        'display_function', 'display_hrm', 'display_account_name',
        'display_opening_balance', 'display_increase',
        'display_decrease', 'display_closing_balance',
        'display_c_ids', 'notes'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    #readonly_fields = ('closing_balance',)

    # Search, filter
    list_filter = ('side', 'is_enabled_sync', 'type')

    # Actions
    actions = [a.accounting_get_data, a.de_sync_accounting]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'ledger', 'hrm', *make_language_fields('name'), 'type',
                'function', 'parent', 'category', 'account'),
            'classes': ('expand',),
        }),
        ('Balances', {
            'fields': ('opening_balance', 'increase', 'decrease', 'closing_balance'),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Opening Balance'))
    def display_opening_balance(self, obj):
        return Display.big_number(obj.opening_balance)

    @admin.display(description=_('Closing Balance'))
    def display_closing_balance(self, obj):
        return Display.big_number(obj.closing_balance)

    @admin.display(description=_('Increase'))
    def display_increase(self, obj):
        return Display.big_number(obj.increase)

    @admin.display(description=_('Decrease'))
    def display_decrease(self, obj):
        return Display.big_number(obj.decrease)


class LedgerFunctional(ExportActionMixin, LedgerBaseAdmin):
    """
    Django Admin for LedgerBalance model.
    """
    # Safeguards
    protected_foreigns = [
        'tenant', 'setup', 'ledger', 'parent', 'account', 'category_expense',
        'category_revenue'
    ]

    # Helpers
    form = forms.LedgerPLAdminForm
    resource_class = LedgerPLResource

    # Display these fields in the list view
    list_display = (
        'display_function', 'display_hrm', 'display_account_name',
        'expense', 'revenue', 'expense_budget', 'revenue_budget',
        'expense_previous', 'revenue_previous',
        'display_c_ids', 'notes'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    # readonly_fields = ('closing_balance',)

    # Enable filtering options
    list_filter = ('is_enabled_sync', 'type', 'function')

    # Actions
    actions = [a.accounting_get_data, a.de_sync_accounting]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'ledger', 'hrm', *make_language_fields('name'), 'type',
                'function', 'parent', 'account',
                'category_expense', 'category_revenue',),
            'classes': ('expand',),
        }),
        ('Balances', {
            'fields': (
                'expense', 'revenue', 'expense_budget', 'revenue_budget',
                'expense_previous', 'revenue_previous'),
            'classes': ('collapse',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Opening Balance'))
    def display_opening_balance(self, obj):
        return Display.big_number(obj.opening_balance)

    @admin.display(description=_('Closing Balance'))
    def display_closing_balance(self, obj):
        return Display.big_number(obj.closing_balance)

    @admin.display(description=_('Increase'))
    def display_increase(self, obj):
        return Display.big_number(obj.increase)

    @admin.display(description=_('Decrease'))
    def display_decrease(self, obj):
        return Display.big_number(obj.decrease)


@admin.register(models.LedgerPL, site=admin_site)
class LedgerPL(LedgerFunctional):
    pass


@admin.register(models.LedgerIC, site=admin_site)
class LedgerIC(LedgerFunctional):
    pass



# Core Title, PersonCategory, Person ----------------------------------------
class Core(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['setup', 'core']

    # Display these fields in the list view
    list_display = ('core', ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    readonly_fields = FIELDS.C_READ_ONLY

    # Actions
    actions = [
        a.accounting_get_data, a.sync_accounting, a.de_sync_accounting]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('core', ),
            'classes': ('expand',),
        }),
        FIELDSET.CASH_CTRL
    )
    """
    def has_add_permission(self, request):
        return False  # Prevent adding new instances

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting instances
    """

@admin.register(models.Title, site=admin_site)
class TitleAdmin(Core):
    pass


@admin.register(models.PersonCategory, site=admin_site)
class PersonCategoryAdmin(Core):
    pass


@admin.register(models.Person, site=admin_site)
class PersonAdmin(Core):
    pass


# Cantonal Charts ---------------------------------------------------------
'''
do not include for now
'''
