from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin import AttachmentInline
from scerp.actions import export_excel, default_actions
from scerp.admin import BaseAdmin, BaseTabularInline, make_language_fields
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site

from . import filters, forms
from .models import AssetCategory, Device, EventLog


@admin.register(AssetCategory, site=admin_site)
class AssetCategory(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant']
    
    # Helpers
    form = forms.AssetCategoryAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'display_name', 'unit', 'counter_factor'
    ) + FIELDS.ICON_DISPLAY
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('code',)
    
    # Actions
    actions = [export_excel] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_name', *make_language_fields('name'),
                'unit', 'counter_factor'
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )


class EventLogInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'customer', 'address', 'dwelling', 'room']

    # Inline
    model = EventLog
    fields = [
        'datetime', 'status', 
        'customer', 'address', 'dwelling', 'room']  # Only show these fields
    extra = 0  # Number of empty forms displayed
    autocomplete_fields = ['customer', 'address']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model


@admin.register(Device, site=admin_site)
class DeviceAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'category']
    
    # Helpers
    form = forms.DeviceAdminForm

    # Display these fields in the list view
    list_display = (
        'code', 'category', 'display_name', 'number', 'status'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT
    list_display_links = ('code', 'display_name') + FIELDS.LINK_ATTACHMENT
    readonly_fields = ('display_name', 'status') + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = (
        'code' , 'name', 'number', 'nr', 'serial_number', 'category__code')
    list_filter = ('status', filters.CategoryFilter, 'category__code')
    
    # Actions
    actions = [export_excel] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_name', *make_language_fields('name'),
                'category', 'purchase_price', 
                *make_language_fields('description')),
        }),
        (_("Status & Dates"), {
            'fields': (
                'status', 'date_added', 'date_disposed', 'warranty_months'),
        }),
        (_("Identification"), {
            'fields': (
                'number', 'serial_number', 'tag', 'registration_number',
                'batch'),
            'classes': ('collapse',),  # Collapsible section
        }),        
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )
    
    inlines = [EventLogInline]


@admin.register(EventLog, site=admin_site)
class EventLogAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'customer', 'address', 'dwelling', 'room']

    # Display these fields in the list view
    list_display = (
        'device', 'device__category', 'datetime', 'status', 'address'
    ) + FIELDS.ICON_DISPLAY
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = (
        'device__code', 'device__name', 'device__number', 
        'device__description', 'datetime')
    list_filter = ('status', 'datetime')
    
    # Actions
    actions = [export_excel] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'device', 'datetime', 'status', 'customer', 'address',
                'dwelling', 'room'
            ),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )
