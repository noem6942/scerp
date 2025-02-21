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

from core.safeguards import get_tenant, save_logging
from core.models import Country, Address, Contact
from scerp.admin import (
     BaseAdmin, BaseTabularInline, Display,
     verbose_name_field, make_language_fields, set_inactive, set_protected)
from scerp.admin_site import admin_site
from scerp.mixins import primary_language, show_hidden

from . import actions as a
from . import filters, forms, models
from .resources import (
    LedgerBalanceResource, LedgerPLResource, LedgerICResource
)


class CASH_CTRL:
    SUPER_USER_EDITABLE_FIELDS = [
        'message',
        'is_enabled_sync',
        'sync_to_accounting',
        'setup'
    ]
    FIELDS = [
        'c_id',
        'c_created',
        'c_created_by',
        'c_last_updated',
        'c_last_updated_by',
        'last_received',
    ]
    REVENUE_FIELDS = [
        'c_rev_id',
        'c_rev_created',
        'c_rev_created_by',
        'c_rev_last_updated',
        'c_rev_last_updated_by'
    ]
    WARNING_READ_ONLY = _("Read only model. <i>Use cashControl for edits!</i>")
    LIST_DISPLAY = (
        'display_last_update', 'c_id', 'message', 'is_enabled_sync')
    LIST_DISPLAY_SHORT = ('c_id', 'is_enabled_sync')


@admin.register(models.APISetup, site=admin_site)
class APISetupAdmin(BaseAdmin):
    # Safeguards
    has_tenant_field = True
    related_tenant_fields = ['tenant']

    # Display these fields in the list view
    list_display = ('tenant', 'org_name', 'display_api_key')
    search_fields = ('tenant', 'org_name')

    # Actions
    actions = [
        a.api_setup_get,
        a.init_setup,
        a.api_setup_delete_hrm_accounts,
        a.api_setup_delete_system_accounts,
        a.api_setup_delete_hrm_categories,
        a.api_setup_delete_system_categories
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
    )
    
    @admin.display(description=_('API Key'))
    def display_api_key(self):
        return show_hidden(self.api_key)      
    

class CashCtrlAdmin(BaseAdmin):
    has_tenant_field = True

    def get_default_api_setup(self, request):
        ''' Fetch the default api setup '''
        tenant = get_tenant(request)
        return get_object_or_404(
            models.APISetup, tenant__id=tenant['id'], is_default=True)

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

    def get_form(self, request, obj=None, change=False, **kwargs):
        ''' set default value for setup '''
        # Get the form from the parent class
        form = super().get_form(request, obj, change, **kwargs)

        # Set the default value for the 'sync_to_accounting' field in the
        form.base_fields['sync_to_accounting'].widget.attrs['checked'] = True

        # Only set default value if this is a new instance (obj is None)
        if not obj:
            # Set the default value for the 'setup' field in the form            
            api_setup = self.get_default_api_setup(request)
            form.base_fields['setup'].initial = api_setup

        return form

    def save_inlines(self, request, form, formset, change):
        """ Safe setup for inlines """
        instances = formset.save(commit=False)  # Get unsaved inline instances
        
        # Fetch the correct setup instance
        api_setup = self.get_default_api_setup(request)
        form.base_fields['setup'].initial = api_setup

        for instance in instances:
            if getattr(instance, 'setup_id', None):
                if not instance.setup_id:  # Only set if it's not already set
                    instance.setup = api_setup  # Assign the actual APISetup instance
                instance.save()

        formset.save_m2m()  # Save many-to-many relationships

    @admin.display(description=_('last update'))
    def display_last_update(self, obj):
        return obj.modified_at

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        try:
            return primary_language(obj.name)
        except:
            return ''

    @admin.display(description=_('Name Plural'))
    def display_name_plural(self, obj):
        try:
            return primary_language(obj.name_plural)
        except:
            return ''

    @admin.display(description=_('Parent'))
    def display_parent(self, obj):
        return self.display_name(obj.parent)

    @admin.display(description=_('last update'))
    def display_number(self, obj):
        return Display.big_number(obj.number)

    @admin.display(description=_('Balance'))
    def display_link_to_company(self, person):
        if not person.company:
            return "-"  # Fallback if company is missing
        url = f"../person/{person.id}/"
        return format_html('<a href="{}">{}</a>', url, person.company)

    @admin.display(description=_('Parent'))
    def display_type(self, obj):
        return obj.category.get_type_display()


@admin.register(models.CustomFieldGroup, site=admin_site)
class CustomFieldGroupAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Display these fields in the list view
    list_display = ('code', 'name', 'type') + CASH_CTRL.LIST_DISPLAY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type',)

    # Actions
    actions = [a.accounting_get_data]

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'type'),
            'classes': ('expand',),
        }),
    )

@admin.register(models.CustomField, site=admin_site)
class CustomFieldAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'group']

    # Display these fields in the list view
    list_display = (
        'code', 'group', 'name', 'data_type') + CASH_CTRL.LIST_DISPLAY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type','data_type',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'group', 'name', 'data_type', 'description',
                'is_multi', 'values'),
            'classes': ('expand',),
        }),
    )


@admin.register(models.Location, site=admin_site)
class Location(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'logo']
    has_tenant_field = True
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    # Display these fields in the list view
    list_display = (
        'name', 'type', 'vat_uid', 'logo', 'address', 'display_last_update',
        'url') + CASH_CTRL.LIST_DISPLAY

    # Search, filter
    search_fields = ('name', 'vat_uid')
    list_filter = ('type',)

    # Actions
    actions = [a.accounting_get_data]

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
    )

    @admin.display(description=_('Applikation link'))
    def url(self, obj):
        if obj.type == obj.TYPE.MAIN:
            link = obj.setup.url
            return Display.link(link, link)


@admin.register(models.FiscalPeriod, site=admin_site)
class FiscalPeriodAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']
    is_readonly = False
    warning = CASH_CTRL.WARNING_READ_ONLY

    # Display these fields in the list view
    list_display = ('name', 'start', 'end', 'is_current', 'display_last_update')

    # Search, filter
    search_fields = ('name', 'start', 'end', 'is_current')
    list_filter = ('is_current',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('name', 'start', 'end', 'is_closed', 'is_current'),
            'classes': ('expand',),
        }),
    )


@admin.register(models.Currency, site=admin_site)
class CurrencyAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.CurrencyAdminForm

    # Display these fields in the list view
    list_display = ('code', 'is_default', 'rate') + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('display_description',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('is_default',)

    # Actions
    actions = [a.accounting_get_data]

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
    )

    @admin.display(description=_('description'))
    def display_description(self, obj):
        return primary_language(obj.description)


@admin.register(models.Title, site=admin_site)
class TitleAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.TitleAdminForm
    # Display these fields in the list view
    list_display = ('code', 'display_name') + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('gender',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'gender', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        (_('Texts'), {
            'fields': (
                *make_language_fields('sentence'),),
            'classes': ('collapse',),
        }),
    )


@admin.register(models.Unit, site=admin_site)
class UnitAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.UnitAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name') + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('code', 'display_name')
    readonly_fields = ('display_name',)

    # Display these fields in the list view
    search_fields = ('code', 'name')
    # list_filter = ('code',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', *make_language_fields('name')),
            'classes': ('collapse',),
        }),
    )


@admin.register(models.Tax, site=admin_site)
class TaxAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.TaxAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'display_document_name',
        'display_percentage') + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('code', 'display_name',)
    readonly_fields = (
        'display_name', 'display_document_name', 'display_percentage_flat')

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('percentage',)

    # Actions
    actions = [a.accounting_get_data]

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
    )

    @admin.display(description=_('Wording in document'))
    def display_document_name(self, obj):
        return primary_language(obj.document_name)

    @admin.display(description=_("Percentage"))
    def display_percentage(self, obj):
        return Display.percentage(obj.percentage, 1)

    @admin.display(description=_("Percentage Flat"))
    def display_percentage_flat(self, obj):
        return Display.percentage(obj.percentage_flat, 1)


@admin.register(models.Rounding, site=admin_site)
class RoundingAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.RoundingAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'rounding') + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('display_name',)

    # Display these fields in the list view
    search_fields = ('code', 'name')
    list_filter = ('mode',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'account', 'rounding', 'mode',
                *make_language_fields('name'),),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        return primary_language(obj.name)


@admin.register(models.SequenceNumber, site=admin_site)
class SequenceNumberAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    # Display these fields in the list view
    list_display = ('local_name', 'pattern') + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('local_name',)

    # Search, filter
    search_fields = ('name',)
    list_filter = ('setup',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'local_name', 'pattern'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('Name'))
    def local_name(self, obj):
        return primary_language(obj.name)


"""

@admin.register(models.OrderTemplate, site=admin_site)
class OrderTemplateAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    # Display these fields in the list view
    list_display = ('name', 'is_default') + CASH_CTRL.LIST_DISPLAY

    # Search, filter
    search_fields = ('name',)
    list_filter = ('setup',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('name', 'is_default'),
            'classes': ('expand',),
        }),
    )
"""

@admin.register(models.CostCenterCategory, site=admin_site)
class CostCenterCategoryAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'parent']

    # Helpers
    form = forms.CostCenterCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'display_name', 'number', 'display_parent') + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ('name', 'number')
    list_filter = ('setup',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'parent', *make_language_fields('name')),
            'classes': ('expand',),
        }),
    )


@admin.register(models.CostCenter, site=admin_site)
class CostCenterAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'category']

    # Helpers
    form = forms.CostCenterAdminForm
    # Display these fields in the list view
    list_display = (
        'display_name', 'number', 'category') + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('display_name',)


    # Search, filter
    search_fields = ('name', 'number')
    list_filter = ('category',)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'category', *make_language_fields('name')),
            'classes': ('expand',),
        }),
    )


@admin.register(models.AccountCategory, site=admin_site)
class AccountCategoryAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'parent']

    # Helpers
    form = forms.AccountCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'number', 'display_name', 'display_parent'
    ) + CASH_CTRL.LIST_DISPLAY
    readonly_fields = ('display_name',)
    ordering = [Cast('number', CharField())]

    # Search, filter
    search_fields = ('name', 'number')
    # list_filter = (TenantFilteredSetupListFilter,)

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('number', 'parent', *make_language_fields('name'),),
            'classes': ('expand',),
        }),
    )


class AllocationsInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    related_tenant_fields = ['setup', 'to_cost_center']

    # Inline
    model = models.Allocation
    fields = ['share', 'to_cost_center']  # Only show these fields
    extra = 1  # Number of empty forms displayed
    autocomplete_fields = ['account']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model


@admin.register(models.Account, site=admin_site)
class AccountAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'category']
    optimize_foreigns = ['category', 'currency']
    save_for_related = ['setup']

    # Helpers
    form = forms.AccountAdminForm

    # Display these fields in the list view
    list_display = (
        'display_number', 'function', 'hrm', 'display_name', 'category'
    ) + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('display_name',)
    readonly_fields = ('display_name', 'function', 'hrm')
    ordering = ['function', 'hrm', 'number']

    # Search, filter
    search_fields = ('name', 'number', 'function', 'hrm')
    list_filter = ('function', 'hrm')

    # Actions
    actions = [a.accounting_get_data]

    # Inlines
    inlines = [AllocationsInline]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'number', 'category', *make_language_fields('name'),
                'currency', 'target_max', 'target_min', 'function', 'hrm'),
            'classes': ('expand',),
        }),
    )


@admin.register(models.Setting, site=admin_site)
class SettingAdmin(CashCtrlAdmin):
    # Safeguards
    is_readonly = True
    warning = CASH_CTRL.WARNING_READ_ONLY

    # Display these fields in the list view
    list_display = CASH_CTRL.LIST_DISPLAY

    # Actions
    actions = [a.accounting_get_data]

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
    )


# Order Management ---------------------------------------------------------
@admin.register(models.BookTemplate, site=admin_site)
class BookTemplateAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'credit_account', 'debit_account', 'tax']
    optimize_foreigns = ['credit_account', 'debit_account', 'tax']

    # Helpers
    form = forms.BookTemplateAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'type', 'display_name',  'credit_account', 'debit_account', 
        'tax'
    ) + CASH_CTRL.LIST_DISPLAY_SHORT

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
    )


@admin.register(models.OrderCategoryContract, site=admin_site)
class OrderCategoryContractAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.OrderCategoryContractAdminForm

    # Display these fields in the list view
    list_display = (
        'type', 'code', 'display_name_plural') + CASH_CTRL.LIST_DISPLAY_SHORT
    list_display_links = ('type', 'code', 'display_name_plural')
    
    # Search, filter
    search_fields = ('code', 'name_singular', 'name_plural')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'type', 
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'), 'status_data'
            ),
            'classes': ('expand',),
        }),
    )


@admin.register(models.OrderCategoryIncoming, site=admin_site)
class OrderCategoryIncomingAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'credit_account', 'expense_account', 'bank_account', 'tax',
        'currency']
    optimize_foreigns = [
        'setup', 'credit_account', 'expense_account', 'bank_account', 'tax',
        'currency']

    # Helpers
    form = forms.OrderCategoryIncomingAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name_plural', 'expense_account', 'currency'
    ) + CASH_CTRL.LIST_DISPLAY_SHORT

    # Search, filter
    search_fields = ('code', 'name')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code',  
                *make_language_fields('name_singular'),
                *make_language_fields('name_plural'),
            ),
            'classes': ('expand',),
        }),
        (_('Booking'), {
            'fields': (
                'address_type', 'credit_account', 'expense_account', 
                'bank_account', 'tax', 'rounding', 'currency', 'due_days'
            ),
            'classes': ('expand',),
        }),
    )


class OrderIncomingAdmin(CashCtrlAdmin):

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Call super() first to let filter_foreignkeys (or any other logic) run
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

        # Get setup
        api_setup = self.get_default_api_setup(request)
        
        # Ensure filtering applies to 'responsible_person'
        if db_field.name == "responsible_person" and formfield is not None:
            formfield.queryset = models.Person.objects.filter(
                setup=api_setup, category__c_id=models.PERSON_TYPE.EMPLOYEE)
        
        return formfield

    @admin.display(description=_('Type'))
    def display_type(self, obj):
        return obj.category.get_type_display()
    

@admin.register(models.OrderContract, site=admin_site)
class OrderContractAdmin(OrderIncomingAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'associate', 'category', 'currency', 'responsible_person']
    optimize_foreigns = [
        'setup', 'associate', 'category', 'currency', 'responsible_person']    

    # Display these fields in the list view
    list_display = (
        'date', 'display_type', 'description', 'display_supplier', 
        'price_excl_vat', 'currency', 'status'
    ) + CASH_CTRL.LIST_DISPLAY_SHORT    
    list_display_links = ('date', 'display_type', 'description')
 
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
    )

    @admin.display(description=_('Partner'))
    def display_supplier(self, obj):
        return self.display_link_to_company(obj.associate)

@admin.register(models.IncomingOrder, site=admin_site)
class IncomingOrderAdmin(OrderIncomingAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'contract', 'category', 'responsible_person']
    optimize_foreigns = [
        'setup', 'contract', 'category', 'responsible_person']    
    
    # Display these fields in the list view
    list_display = (
        'date', 'display_type', 'description', 'display_supplier', 
        'price_incl_vat', 'category__currency', 'status'
    ) + CASH_CTRL.LIST_DISPLAY_SHORT       
    list_display_links = ('date', 'display_type', 'description')
 
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
    )

    @admin.display(description=_('Partner'))
    def display_supplier(self, obj):
        return self.display_link_to_company(obj.contract.associate)


@admin.register(models.ArticleCategory, site=admin_site)
class ArticleCategoryAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'parent', 'purchase_account', 'sales_account', 'sequence_nr']

    # Helpers
    form = forms.ArticleCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'display_parent') + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('code', 'display_name',)
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('setup',)

    # Actions
    actions = [a.accounting_get_data]

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
    )


@admin.register(models.Article, site=admin_site)
class ArticleAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'category', 'currency', 'location', 'sequence_nr', 'unit']

    # Helpers
    form = forms.ArticleAdminForm

    # Display these fields in the list view
    list_display = (
        'nr', 'display_name', 'sales_price', 'unit') + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('nr', 'display_name')
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = (filters.ArticleCategoryFilter, )

    # Actions
    actions = [a.accounting_get_data]

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
    )


# Ledger -------------------------------------------------------------------
@admin.register(models.Ledger, site=admin_site)
class LedgerAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup', 'period']

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


class LedgerBaseAdmin(CashCtrlAdmin):
    # Display
    list_display_links = ('display_account_name',)
    list_per_page = 1000  # Show 1000 i.e. most probably all results per page
    ordering = ['function', '-type' ,'hrm']

    # Search, filter
    search_fields = ('function', 'hrm', 'name')

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
    related_tenant_fields = [
        'setup', 'ledger', 'parent', 'account', 'category']
    optimize_foreigns = ['ledger', 'parent', 'account', 'category']

    # Helpers
    form = forms.LedgerBalanceAdminForm
    resource_class = LedgerBalanceResource

    # Display these fields in the list view
    list_display = (
        'display_function', 'display_hrm', 'display_account_name',
        'display_opening_balance', 'display_increase',
        'display_decrease', 'display_closing_balance',
        'display_c_ids', 'notes'
    ) + CASH_CTRL.LIST_DISPLAY
    #readonly_fields = ('closing_balance',)

    # Search, filter
    list_filter = (
        filters.LedgerFilteredSetupListFilter, 'is_enabled_sync', 'type')

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
    related_tenant_fields = [
        'setup', 'ledger', 'parent', 'account', 'category_expense',
        'category_revenue']
    optimize_foreigns = ['ledger', 'parent', 'account', 'category_expense',
        'category_revenue']

    # Helpers
    form = forms.LedgerPLAdminForm
    resource_class = LedgerPLResource

    # Display these fields in the list view
    list_display = (
        'display_function', 'display_hrm', 'display_account_name',
        'expense', 'revenue', 'expense_budget', 'revenue_budget',
        'expense_previous', 'revenue_previous',
        'display_c_ids', 'notes'
    ) + CASH_CTRL.LIST_DISPLAY
    # readonly_fields = ('closing_balance',)

    # Enable filtering options
    list_filter = (
        filters.LedgerFilteredSetupListFilter, 'is_enabled_sync', 
        'type', 'function')

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




"""
@admin.register(models.Article, site=admin_site)
class ArticleAdmin(CashCtrlAdmin):
    related_tenant_fields = ['setup']

    list_display = (
        'nr', 'display_name', 'display_sales_price') + CASH_CTRL.LIST_DISPLAY
    search_fields = ('name', 'nr')
    list_filter = ('is_stock_article', 'category_id')
    readonly_fields = ('display_name', 'display_sales_price')

    # Actions
    actions = [a.accounting_get_data]

    #Fieldsets
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

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        return primary_language(obj.name)

    @admin.display(description=_('price in CHF'))
    def display_sales_price(self, obj):
        return Display.big_number(obj.sales_price)
"""

@admin.register(models.ChartOfAccountsTemplate, site=admin_site)
class ChartOfAccountsTemplateAdmin(BaseAdmin):
    # Safeguards
    has_tenant_field = False

    # Display these fields in the list view
    list_display = ('name', 'chart_version', 'link_to_positions')
    readonly_fields = ('exported_at',)

    # Search, filter
    search_fields = ('name', 'account_type', 'canton', 'type')
    list_filter = ('account_type', 'type', 'canton', 'chart_version')

    # Actions
    actions = [a.coac_positions_check, a.coac_positions_create]

    #Fieldsets
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

    @admin.display(description=_('Type - display positions'))
    def link_to_positions(self, obj):
        url = f"../accountpositiontemplate/?chart__id__exact={obj.id}"
        name = obj.get_account_type_display()
        return format_html(f'<a href="{url}">{name}</a>', url)


@admin.register(models.AccountPositionTemplate, site=admin_site)
class AccountPositionTemplateAdmin(BaseAdmin):
    # Safeguards
    related_tenant_fields = ['parent']
    has_tenant_field = False

    # Display these fields in the list view
    list_display = ('category_number', 'position_number', 'display_name',)
    list_display_links = ('display_name',)
    readonly_fields = ('chart', 'number')

    # Search, filter
    list_filter = (
        'chart__account_type',
        'chart__canton', 'chart__chart_version', 'chart')
    search_fields = ('account_number', 'name', 'notes', 'number')

    # Actions
    actions = [
        a.apc_export_balance,
        a.apc_export_function_to_income,
        a.apc_export_function_to_invest,
        a.position_insert
    ]

    #Fieldsets
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
        description=verbose_name_field(models.AccountPosition, 'name'))
    def display_name(self, obj):
        return Display.name_w_levels(obj)


@admin.register(models.ChartOfAccounts, site=admin_site)
class ChartOfAccountsAdmin(BaseAdmin):
    # Safeguards
    related_tenant_fields = ['period']
    has_tenant_field = True

    # Display these fields in the list view
    list_display = (
        'display_name', 'chart_version', 'period', 'link_to_positions')
    # readonly_fields = ('period',)

    # Search, filter
    search_fields = ('name',)

    #Fieldsets
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


@admin.register(models.AccountPosition, site=admin_site)
class AccountPositionAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = [
        'setup', 'parent', 'chart', 'allocations', 'currency' ]
    has_tenant_field = True
    has_revenue_id = True
    is_readonly = False

    # Display these fields in the list view
    list_display = (
        'display_function', 'position_number', 'display_name',
        'display_end_amount_credit', 'display_end_amount_debit',
        'display_balance_credit', 'display_balance_debit',
        'display_budget', 'display_previous', 'display_cashctrl', 'responsible')
    list_display_links = ('display_name',)
    list_per_page = 1000  # Show 1000 i.e. most probably all results per page
    readonly_fields = ('balance', 'budget', 'previous', 'number')

    # Search, filter
    list_filter = ('account_type', 'chart', 'responsible')
    search_fields = ('function', 'account_number', 'number', 'name')

    #Fieldsets
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

    # Actions
    actions = [
        a.apm_add_income,
        a.apm_add_invest,
        a.check_accounts,
        a.account_names_convert_upper_case,
        a.upload_accounts,
        a.download_balances, a.get_balances,
        a.upload_balances,
        a.assign_responsible,
        set_inactive,
        set_protected,
        a.position_insert
    ]

    @admin.display(
        description=verbose_name_field(models.AccountPosition, 'name'))
    def display_name(self, obj):
        return Display.name_w_levels(obj)

    @admin.display(
        description=verbose_name_field(models.AccountPosition, 'function'))
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

'''
@admin.register(models.PersonCategory, site=admin_site)
class PersonCategoryAdmin(CashCtrlAdmin):
    # Safeguards
    related_tenant_fields = ['setup']

    # Helpers
    form = forms.PersonCategoryAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name') + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('code', 'display_name')
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ['code', 'name']
    list_filter = ('setup',)

    # Actions
    actions = [a.accounting_get_data, a.de_sync_accounting]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_name', *make_language_fields('name'),
                'parent'),
            'classes': ('expand',),
        }),
    )


@admin.register(Address, site=admin_site)
class AddressAdmin(admin.ModelAdmin):
    # Safeguards
    related_tenant_fields = ['tenant', 'person', 'categories']
    optimize_foreigns = ['tenant', 'person', 'categories']

    # Display these fields in the list view
    list_display = ('country', 'zip', 'city', 'address')
    list_display_links = ('zip', 'city',)

    # Search, filter
    list_filter = ('zip', 'country', )
    search_fields = ('zip', 'city', 'address')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (('zip', 'city'), 'address', 'country', 'categories'),
            'classes': ('expand',),
        }),
    )

    def get_changeform_initial_data(self, request):
        """Set default country to 'CHE' (Switzerland) by fetching the instance."""
        return {'country': get_object_or_404(Country, alpha3='CHE')}


class AddressInline(BaseTabularInline):
    # Safeguards
    has_tenant_field = True
    related_tenant_fields = ['setup', 'person']

    # Inline
    model = models.AddressMapping
    form = forms.AddressPersonForm
    fields = ['type', 'address', 'post_office_box', 'additional_information']
    extra = 1  # Number of empty forms displayed
    autocomplete_fields = ['address']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Addresses")


class ContactInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    has_tenant_field = True
    related_tenant_fields = ['tenant', 'person']

    # Inline
    model = models.ContactMapping
    form = forms.ContactPersonForm
    fields = ['type', 'address']
    extra = 1  # Number of empty forms displayed
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Contacts")


@admin.register(models.Person, site=admin_site)
class PersonAdmin(CashCtrlAdmin):
# Safeguards
    related_tenant_fields = ['setup', 'title', 'superior', 'category']
    has_tenant_field = True

    # Display these fields in the list view
    list_display = (
        'company', 'first_name', 'last_name', 'category',
        'display_last_update') + CASH_CTRL.LIST_DISPLAY
    list_display_links = ('company', 'first_name', 'last_name',)
    readonly_fields = ('nr',)

    # Search, filter
    list_filter = (filters.PersonCategoryFilter,)
    search_fields = ('company', 'first_name', 'last_name', 'alt_name')

    # Actions
    actions = [a.sync_accounting, a.de_sync_accounting]

    #Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'category', 'title', 'company', 'first_name', 'last_name',
                'alt_name', 'color'
                ),
            'description': _(
                "Either 'Company' or 'First Name' & 'Last Name' must be filled."),
        }),
        (_('Company/Work Information'), {
            'fields': ('industry', 'position', 'department', 'superior'),
            'classes': ('collapse',),
        }),
        (_('Finance & Banking'), {
            'fields': ('vat_uid', 'iban', 'bic', ),  # 'discount_percentage'
            'classes': ('collapse',),
        }),
        (_('Additional Details'), {
            'fields': ('date_birth', 'nr'),
            'classes': ('collapse',),
        }),
    )

    inlines = [AddressInline, ContactInline]

    def save_formset(self, request, form, formset, change):
        """ Ensure setup is set before saving. """
        self.save_inlines(request, form, formset, change)
'''