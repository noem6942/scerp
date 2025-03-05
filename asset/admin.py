from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scerp.admin import BaseAdminNew, make_language_fields
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site

from . import forms
from .models import AssetCategory, Device, EventLog


@admin.register(AssetCategory, site=admin_site)
class AssetCategory(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']
    
    # Helpers
    form = forms.AssetCategoryAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('code',)

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )


@admin.register(Device, site=admin_site)
class DeviceAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'category']

    # Display these fields in the list view
    list_display = (
        'code', 'name', 'number', 'category', )
    readonly_fields = ('display_name', 'status') + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('number', 'name', 'category')
    list_filter = ('status', 'obiscode', 'category')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'name', 'category', 'description'),
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
        (_("Technical Details"), {
            'fields': ('obiscode',),
            'classes': ('collapse',),  # Collapsible section
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )


@admin.register(EventLog, site=admin_site)
class EventLogAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'customer', 'building', 'dwelling', 'room']

    # Display these fields in the list view
    list_display = ('device', 'date', 'status')
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('device', 'date', 'status')
    list_filter = ('status', 'date')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'device', 'date', 'status', 'customer', 'building',
                'dwelling', 'room'
            ),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )
