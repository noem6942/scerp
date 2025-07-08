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
from scerp.actions import export_excel, default_actions
from scerp.admin import (
     BaseAdmin, BaseTabularInline, Display,
     verbose_name_field, make_language_fields)
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site
from scerp.mixins import primary_language, show_hidden

from . import forms, models, actions as a
from .api_cash_ctrl import URL_ROOT as cashControl_URL_ROOT
from .resources import (
    LedgerBalanceResource, LedgerPLResource, LedgerICResource
)


# Actions
accounting_actions_write = [    
    a.de_sync_accounting,
    a.sync_accounting
]
accounting_actions = [a.accounting_get_data] + accounting_actions_write


@admin.register(models.CustomFieldGroup, site=admin_site)
class CustomFieldGroupAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant']

    # Display these fields in the list view
    list_display = ('code', 'display_name', 'type') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type',)

    # Actions
    actions = accounting_actions + default_actions

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'type'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.CustomField, site=admin_site)
class CustomFieldAdmin(TenantFilteringAdmin, BaseAdmin):
    protected_foreigns = ['tenant', 'version', 'group']

    # Display these fields in the list view
    list_display = (
        'code', 'group', 'display_name', 'data_type') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type','data_type',)

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'group', 'name', 'data_type', 'description',
                'is_multi', 'values'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Setting, site=admin_site)
class SettingAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Helpers
    help_text = _("Read only model. Use cashControl for edits.")

    # Display these fields in the list view
    list_display = FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name', 'display_json') + FIELDS.C_READ_ONLY

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'display_json',
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Data'))
    def display_json(self, obj):
        return Display.json(obj.data)

    @admin.display(description=_('Link'))
    def display_url(self, obj):
        url = URL_ROOT.format(org=obj.tenant.cash_ctrl_org_name)
        return Display.link(url, 'cashCtrl', 'new')


@admin.register(models.Location, site=admin_site)
class Location(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']
    read_only = True

    # Helpers
    help_text = _("Read only model. Use cashControl for edits.")

    # Display these fields in the list view
    list_display = ('name', 'type', 'address', ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name', 'vat_uid')
    list_filter = ('type',)

    # Actions
    actions = accounting_actions + default_actions

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
        # do not use
        # (_('Accounting Information'), {
        #     'fields': (
        #         'bic', 'iban', 'qr_first_digits', 'qr_iban', 'vat_uid'
        #     ),
        #     'classes': ('collapse',),
        # }),

        # Layout
        (_('Layout'), {
            'fields': ('logo_file_id', 'footer'),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Applikation link'))
    def url(self, obj):
        if obj.type == obj.TYPE.MAIN:
            link = obj.tenant.setup.url
            return Display.link(link, link)


@admin.register(models.FiscalPeriod, site=admin_site)
class FiscalPeriodAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = (
        'name', 'start', 'end', 'is_current', 'display_last_update'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name', 'start', 'end', 'is_current')
    list_filter = ('is_current',)

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'name', 'start', 'end', 'salary_start', 'salary_end',
                'is_current'
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.BankAccount, site=admin_site)
class BankAccountAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'account', 'currency']
    #read_only = True  # as long as cashControl bug not resolved

    # Helpers
    help_text = _("Read only model. Use cashControl for edits.")
    form = forms.BankAccountAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'iban', 'account') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('code', 'display_name')

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type',)
    autocomplete_fields = ['account']

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', *make_language_fields('name'), 'iban', 'bic',
                'account', 'currency'
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Tax, site=admin_site)
class TaxAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Helpers
    form = forms.TaxAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'display_percentage', 'account'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = (
        'display_name', 'display_document_name', 'display_percentage_flat'
    ) + FIELDS.C_READ_ONLY
    list_display_links = ('code', 'display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('percentage',)

    # Actions
    actions = accounting_actions + default_actions

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
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Rounding, site=admin_site)
class RoundingAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

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
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'account', 'rounding', 'mode',
                *make_language_fields('name'),),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        return primary_language(obj.name)


@admin.register(models.SequenceNumber, site=admin_site)
class SequenceNumberAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']
    read_only = True

    # Helpers
    help_text = _("Read only model. Use cashControl for edits.")

    # Display these fields in the list view
    list_display = ('display_name', 'pattern') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name',)

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'pattern', 'name'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.CostCenterCategory, site=admin_site)
class CostCenterCategoryAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'parent']

    # Helpers
    form = forms.CostCenterCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'display_name', 'number', 'display_parent') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name', 'number')

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'parent', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.CostCenter, site=admin_site)
class CostCenterAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'category']

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
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'category', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Currency, site=admin_site)
class CurrencyAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']
    read_only = True

    # Helpers
    help_text = _("Read only model. Use cashControl for edits.")
    form = forms.CurrencyAdminForm

    # Display these fields in the list view
    list_display = ('code', 'is_default', 'rate') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_description',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'description')
    list_filter = ('is_default',)

    # Actions
    actions = accounting_actions + default_actions

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
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.AccountCategory, site=admin_site)
class AccountCategoryAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'parent']

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

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('number', 'parent', *make_language_fields('name'),),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


class AllocationsInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'to_cost_center']

    # Inline
    model = models.Allocation
    fields = ['share', 'to_cost_center']  # Only show these fields
    extra = 1  # Number of empty forms displayed
    autocomplete_fields = ['account']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model


@admin.register(models.Account, site=admin_site)
class AccountAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'category', 'currency']

    # Helpers
    form = forms.AccountAdminForm

    # Display these fields in the list view
    list_display = (
        'display_number', 'function', 'hrm', 'display_name', 'category'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('display_number', 'function', 'hrm', 'display_name',)
    # readonly_fields = ('display_name', 'function', 'hrm') + FIELDS.C_READ_ONLY
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    ordering = ['function', 'hrm', 'number']

    # Search, filter
    search_fields = ('name', 'number', 'function', 'hrm')
    list_filter = ('function', 'hrm')
    autocomplete_fields = ['category']

    # Actions
    actions = accounting_actions + default_actions

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
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


# Journal
@admin.register(models.JournalTemplate, site=admin_site)
class JournalTemplateAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'credit_account', 'debit_account', 'currency']

    # Display these fields in the list view
    list_display = (
        'code', 'name', 'credit_account', 'debit_account'
    )
    readonly_fields = FIELDS.C_READ_ONLY
    list_display_links = ('code', 'name')

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('is_opening_booking',)
    autocomplete_fields = ['credit_account', 'debit_account']

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'name', 'credit_account', 'debit_account', 'currency',
                'is_opening_booking'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )


@admin.register(models.Journal, site=admin_site)
class JournalAdmin(TenantFilteringAdmin, BaseAdmin):
    help_text=_("Create journals. See cashControl for results.")
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'template']
    
    # Display these fields in the list view
    list_display = (
        'title', 'date', 'amount') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = FIELDS.C_READ_ONLY
    list_display_links = ('title',)

    # Search, filter
    search_fields = ('title', 'amount')
    list_filter = ('date',)
    autocomplete_fields = ['template']

    # Actions
    actions = [a.de_sync_accounting, a.sync_accounting] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'title', 'template', 'amount', 'date', 'reference'
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


# Inventory
@admin.register(models.ArticleCategory, site=admin_site)
class ArticleCategoryAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'purchase_account',  'sales_account',
        'sequence_nr'
    ]

    # Helpers
    form = forms.ArticleCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'sales_account', 'tax') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('code', 'display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    autocomplete_fields = ['purchase_account',  'sales_account']

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', *make_language_fields('name'), 'sales_account',
                'tax', 'sequence_nr'
            ),
            'classes': ('expand',),
        }),
        (_("Extra"), {
            'fields': (
                'parent', 'purchase_account'
            ),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.Article, site=admin_site)
class ArticleAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'category', 'currency', 'location',
        'sequence_nr', 'unit'
    ]

    # Helpers
    form = forms.ArticleAdminForm

    # Display these fields in the list view
    list_display = (
        'nr', 'display_name', 'category', 'display_price', 'unit',
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('nr', 'display_name')

    # Search, filter
    search_fields = ('nr', 'name', 'unit__code', 'unit__name', 'sales_price')
    list_filter = ('category',)

    # Actions
    actions = accounting_actions + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'category', *make_language_fields('name'),
                'sales_price', 'unit', 'sequence_nr', 'nr',
                *make_language_fields('description')),
            'classes': ('expand',),
        }),
        (_("Stock Management"), {
            'fields': (
                'location', 'bin_location', 'is_stock_article', 'stock',
                'min_stock', 'max_stock'),
            'classes': ('collapse',),
        }),
        (_("Pricing"), {
            'fields': ('currency', 'last_purchase_price',
                       'is_sales_price_gross', 'is_purchase_price_gross'),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    @admin.display(description=_('Price (Excl. VAT)'))
    def display_price(self, obj):
        return Display.big_number(obj.sales_price)


# Order Management ---------------------------------------------------------
@admin.register(models.OrderLayout, site=admin_site)
class OrderLayoutAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = ('name', 'is_default') + FIELDS.C_DISPLAY_SHORT
    readonly_fields = FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('name',)

    # Actions
    actions = accounting_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'display_name', 'is_default',
            ),
            'classes': ('expand',),
        }),
        (_('Layout'), {
            'fields': (
                'elements', 'footer',
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
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

'''  not used so fare
@admin.register(models.BookTemplate, site=admin_site)
class BookTemplateAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'credit_account', 'debit_account', 'tax'
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
    autocomplete_fields = ['credit_account', 'debit_account']

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'type', *make_language_fields('name'),
                'credit_account', 'debit_account', 'tax'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )
'''

@admin.register(models.OrderCategoryContract, site=admin_site)
class OrderCategoryContractAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'layout']

    # Helpers
    form = forms.OrderCategoryContractAdminForm
    help_text = _("Template for Contracts.")

    # Display these fields in the list view
    list_display = (
        'type', 'code', 'display_name_plural') + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('type', 'code', 'display_name_plural')
    readonly_fields = (
        'display_name', 'status_data', 'book_template_data'
    ) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name_singular', 'name_plural')

    # Actions
    actions = accounting_actions_write + [a.accounting_copy]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'type',
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'),
                'org_location', 'is_display_prices',
                'layout', 'header', 'footer'
            ),
            'classes': ('expand',),
        }),
        (_('Status Definitions'), {
            'fields': (
                'status_data', 'book_template_data'
            ),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.OrderCategoryIncoming, site=admin_site)
class OrderCategoryIncomingAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'credit_account', 'expense_account',
        'bank_account', 'tax', 'currency', 'layout'
    ]

    # Helpers
    form = forms.OrderCategoryIncomingAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name_plural', 'credit_account', 'expense_account',
        'bank_account',
    ) + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('code', 'display_name_plural')
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    autocomplete_fields = ['credit_account', 'expense_account']

    # Actions
    actions = accounting_actions_write + [a.accounting_copy]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code',
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'), 'layout', 'header'
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
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.OrderCategoryOutgoing, site=admin_site)
class OrderCategoryOutgoingAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'debit_account', 'bank_account',
        'currency', 'layout'
    ]

    # Helpers
    form = forms.OrderCategoryOutgoingAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name_plural', 'debit_account', 'bank_account',
    ) + FIELDS.C_DISPLAY_SHORT
    list_display_links = ('code', 'display_name_plural')
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    autocomplete_fields = [
        'responsible_person', 'debit_account', 'bank_account']

    # Actions
    actions = accounting_actions_write + [a.accounting_copy]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code',
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'),
                'responsible_person',
            ),
            'classes': ('expand',),
        }),
        (_('Layout'), {
            'fields': (
                'layout', 'header', 'footer'
            ),
            'classes': ('expand',),
        }),
        (_('Booking'), {
            'fields': (
                'address_type', 'debit_account', 'bank_account', 'rounding',
                'currency', 'due_days'
            ),
            'classes': ('expand',),
        }),
        (_('Status and Booking Codes'), {
            'fields': (
                'status_data', 'book_template_data'
            ),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )


@admin.register(models.OrderContract, site=admin_site)
class OrderContractAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'associate', 'category', 'currency',
        'responsible_person'
    ]

    # Helpers
    help_text = _(
        'Every incoming invoice must be based on a contract. '
        'Here you define all repeating supplier data. ')

    # Display these fields in the list view
    list_display = (
        'date', 'category', 'description', 'associate__company',
        'price_excl_vat', 'currency', 'status'
    ) + FIELDS.C_DISPLAY_SHORT
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    list_display_links = ('date', 'description')

    # Search, filter
    search_fields = ('nr', 'supplier__company', 'description')
    list_filter = ('category', 'status', 'date')
    autocomplete_fields = ['associate', 'responsible_person']

    # Actions
    actions = accounting_actions_write + [a.accounting_copy]

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
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    inlines = [AttachmentInline]


class IncomingItemsInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'order', 'account', 'tax']

    # Inline
    model = models.IncomingItem
    fields = ['name', 'description', 'amount', 'quantity', 'account', 'tax']
    extra = 0  # Number of empty forms displayed
    autocomplete_fields = ['account']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model


@admin.register(models.IncomingOrder, site=admin_site)
class IncomingOrderAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'contract', 'category',
        'responsible_person'
    ]

    # Display these fields in the list view
    list_display = (
        'nr', 'name', 'date', 'display_supplier',
        'display_price', 'category__currency', 'display_bank_account',
        'status', 'display_cash_ctrl_url'
    )  + CORE_FIELDS.ICON_DISPLAY + CORE_FIELDS.LINK_ATTACHMENT + FIELDS.C_DISPLAY_SHORT
    list_display_links = (
        'nr', 'name'
    ) + CORE_FIELDS.LINK_ATTACHMENT
    readonly_fields = (
        'display_category_type', 'display_bank_account',
        'display_cash_ctrl_url'
    ) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = (
        'nr', 'contract__associate__company', 'name', 'description')
    list_filter = ('category', 'status', 'date')
    autocomplete_fields = ['responsible_person']

    # Actions
    actions = accounting_actions_write + [
        a.get_bank_data, a.incoming_order_approve]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'category', 'contract', 'status', 'name', 'description',
                'date', 'price_incl_vat', 'due_days', 'reference',
                'responsible_person', 'display_bank_account'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    inlines = [AttachmentInline, IncomingItemsInline]

    @admin.display(description=_('Price (Incl. VAT)'))
    def display_price(self, obj):
        return Display.big_number(obj.price_incl_vat)

    @admin.display(description=_('Supplier IBAN'))
    def display_bank_account(self, obj):
        account = obj.supplier_bank_account
        return account.iban if account else None

    @admin.display(description=_('Supplier'))
    def display_supplier(self, obj):
        return obj.contract.associate

    @admin.display(description=_('url'))
    def display_cash_ctrl_url(self, obj):
        return Display.link(obj.url, '🧾', 'new')


class OutgoingItemsInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'article', 'order']

    # Inline
    model = models.OutgoingItem
    fields = ['article', 'quantity', 'description']  # Only show these fields
    #formset = RequireOneOutgoingItemFormSet  # Force at least one article
    extra = 1  # Number of empty forms displayed
    autocomplete_fields = ['article']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model


@admin.register(models.OutgoingOrder, site=admin_site)
class OutgoingOrderAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'contract', 'category', 'dossier',
        'responsible_person'
    ]

    # Display these fields in the list view
    list_display = (
        'date', 'nr', 'description', 'category', 'associate',
        'status', 'display_cash_ctrl_url'
    )  + FIELDS.C_DISPLAY_SHORT + CORE_FIELDS.ICON_DISPLAY + CORE_FIELDS.LINK_ATTACHMENT
    list_display_links = (
        'date', 'nr'
    ) + CORE_FIELDS.LINK_ATTACHMENT
    readonly_fields = (
        'nr', 'display_cash_ctrl_url', 'display_cash_ctrl_url_form'
    ) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = (
        'nr', 'associate__company', 'associate__first_name',
        'associate__last_name',
        'description')
    list_filter = ('category', 'status', 'date')
    autocomplete_fields = [
        'associate', 'responsible_person', 'address', 'recipient']

    # Actions
    actions = accounting_actions_write + [
        a.order_status_update, a.order_get_status
    ]+ default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'nr', 'category', 'contract', 'status', 'description', 'date',
                'associate', 'due_days', 'responsible_person', 'dossier',
                'display_cash_ctrl_url_form'),
            'classes': ('expand',),
        }),
        (_('Details'), {
            'fields': (
                'header_description', 'address', 'recipient', 'start', 'end'),
            'classes': ('expand',),
        }),
        (_('Layout'), {
            'fields': (
                'header', 'footer', 'recipient_address'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET.CASH_CTRL
    )

    inlines = [OutgoingItemsInline, AttachmentInline]

    @admin.display(description=_('url'))
    def display_cash_ctrl_url(self, obj):
        return Display.link(obj.url, '🧾', 'new')

    @admin.display(description=_('url'))
    def display_cash_ctrl_url_form(self, obj):
        if obj.url:
            return Display.link(obj.url, '🧾 external url to cashCtrl', 'new')
        return '-'


# Ledger -------------------------------------------------------------------
@admin.register(models.Ledger, site=admin_site)
class LedgerAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'period']

    # Helpers
    form = forms.LedgerAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'period',
        'link_to_balance', 'link_to_pl', 'link_to_ic',
        'display_current')
    list_display_links = ('code', 'display_name', )
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name', 'period__name')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', *make_language_fields('name'), 'period'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
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


class LedgerBaseAdmin(TenantFilteringAdmin, BaseAdmin):
    # Display
    list_display_links = ('display_account_name',)
    list_per_page = 1000  # Show 1000 i.e. most probably all results per page
    ordering = ['function', '-type' ,'hrm']

    # Search, filter
    search_fields = ('function', 'hrm', 'name')
    autocomplete_fields = ['parent', 'account']

    # Actions
    actions = [
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
        'tenant', 'version', 'ledger', 'parent', 'account', 'category'
    ]

    # Helpers
    form = forms.LedgerBalanceAdminForm
    resource_class = LedgerBalanceResource

    # Display these fields in the list view
    list_display = (
        'display_function', 'display_hrm', 'display_account_name',
        'display_opening_balance', 'display_increase',
        'display_decrease', 'display_closing_balance',
        'balance_updated', 'display_c_ids', 'notes'
    ) + FIELDS.C_DISPLAY_SHORT + CORE_FIELDS.ICON_DISPLAY
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY
    #readonly_fields = ('closing_balance',)

    # Search, filter
    list_filter = ('side', 'is_enabled_sync', 'type')
    autocomplete_fields = ['account']

    # Actions
    actions = accounting_actions + [export_excel, a.get_balances] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'ledger', 'hrm', *make_language_fields('name'), 'type',
                'parent', 'category', 'account'),
            'classes': ('expand',),
        }),
        ('Balances', {
            'fields': ('opening_balance', 'increase', 'decrease', 'closing_balance'),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
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
        'tenant', 'version', 'ledger', 'parent', 'account',
        'category_expense', 'category_revenue'
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
    autocomplete_fields = [
        'parent', 'account', 'category_expense', 'category_revenue'
    ]

    # Actions
    actions = (
        accounting_actions + [export_excel, a.get_balances] + default_actions)

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
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
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


# Cantonal Charts ---------------------------------------------------------
'''
do not include for now
'''
