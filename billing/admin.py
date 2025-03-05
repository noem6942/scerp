from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin import AttachmentInline
from scerp.admin import BaseAdminNew
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site

from . import actions as a
from .models import Period, Route, Measurement, Subscription


@admin.register(Period, site=admin_site)
class PeriodAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']
    
    # Display these fields in the list view
    list_display = ('name', 'start', 'end')    
    readonly_fields = FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = ('code', 'name', 'start', 'end')
    list_filter = ('end',)

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'energy_type', 'asset_category', 'name', 'start', 
                'end'),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

   

@admin.register(Route, site=admin_site)
class RouteAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'period']
    protected_many_to_many = ['buildings', 'address_categories']
    
    # Display these fields in the list view
    list_display = (
        'name', 'period', 'start', 'end', 'duration', 'display_filters',
        'is_default', 'status'
    ) + FIELDS.LINK_ATTACHMENT
    readonly_fields = ('duration', 'status') + FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = ('name', 'period')
    list_filter = ('is_default', 'status')

    # Actions
    actions = [a.export_counter_data]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'name', 'period', 'address_categories', 'buildings',
                'start', 'end', 'confidence_min', 'confidence_max',
                'duration', 'status'
            ),
        }),
    )

    inlines = [AttachmentInline]

    @admin.display(description='filters')
    def display_filters(self, obj):
        value = ''
        if obj.buildings.exists():
            value += 'B'
        return value


@admin.register(Measurement, site=admin_site)
class MeasurementAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'counter', 'route']
    
    # Display these fields in the list view
    list_display = ('route', 'counter', 'datetime')
    readonly_fields = FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = ('route', 'counter', 'datetime')
    list_filter = ('route', 'datetime')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ( 
                'counter', 'route', 'datetime', 'datetime_previous',
                'value', 'value_previous', 
                'consumption', 'value_max', 'value_min'
            ),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )
    

@admin.register(Subscription, site=admin_site)
class SubscriptionAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'subscriber', 'building']
    protected_many_to_many = ['articles']
    
    # Display these fields in the list view
    list_display = ('subscriber__alt_name', 'recipient__alt_name', 'building', 'start', 'end')
    readonly_fields = FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = (
        'subscriber__alt_name', 'subscriber__company', 'subscriber__last_name',
        'recipient__alt_name', 'recipient__company', 'recipient__last_name',
        'building__name', 'start', 'end')
    list_filter = ('end', 'articles', 'subscriber__company')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'subscriber', 'recipient', 'start', 'end', 'building', 
                'articles'
            ),            
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )
