from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

from core.admin import AttachmentInline
from scerp.actions import export_excel, export_json
from scerp.admin import BaseAdminNew, Display, verbose_name_field
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site

from . import filters, actions as a
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

    @admin.display(description=_('filters'))
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
    list_display = (
        'id', 'datetime', 'display_subscriber',
        'display_area', 'display_consumption')
    list_display_links = ('id', 'datetime')
    readonly_fields = FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = ('subscription__subscriber__alt_name', 'datetime')
    list_filter = (
        filters.MeasurementBuildingAddressCategoryFilter, 
        filters.MeasurementPeriodFilter,
        filters.MeasurementRouteFilter,   
        filters.MeasurementConsumptionFilter,
        'datetime')
    ordering = ('-consumption', 'subscription__subscriber__alt_name')

    # Actions
    actions = [a.analyse_measurment, export_excel, export_json]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ( 
                'counter', 'route', 'datetime', 'datetime_previous',
                'value', 'value_previous', 
                'consumption', 'value_max', 'value_min'
            ),
        }),
        (_('References'), {
            'fields': ( 
                'building', 'period', 'subscription', 'consumption_previous'
            ),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

    def export_data(self, request, queryset):        
        __ = request        
        return [
            (x.id, x.consumption)
            for x in queryset.all()
        ]
        
    def export_headers(self, request, queryset):
        __ = request, queryset        
        return [
            verbose_name_field(self.model, 'id'),
            verbose_name_field(self.model, 'consumption')
        ]

    @admin.display(description=_('Consumption'))
    def display_subscriber(self, obj):       
        return obj.subscription.subscriber.__str__()[:40]
    
    @admin.display(description=_('Consumption'))
    def display_consumption(self, obj):       
        return Display.big_number(obj.consumption)    
 
    @admin.display(description=_('+/- in %'))
    def display_growth(self, obj):       
        return Display.big_number(obj.growth)   
 
    @admin.display(description=_('Period'))
    def display_period_code(self, obj):
        return obj.route.period.code

    @admin.display(description=_('Counter'))
    def display_counter(self, obj):
        return obj.counter.code

    @admin.display(description=_('Area'))
    def display_area(self, obj):       
        return obj.building.address.category_str('area')


@admin.register(Subscription, site=admin_site)
class SubscriptionAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant', 'subscriber', 'building']
    protected_many_to_many = ['articles']
    
    # Display these fields in the list view
    list_display = (
        'subscriber__alt_name', 'recipient__alt_name', 'building', 
        'start', 'end', 'display_abo_nr', 'notes')
    list_display_links = ('subscriber__alt_name', )
    readonly_fields = FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = (
        'subscriber__alt_name', 'subscriber__company', 'subscriber__last_name',
        'recipient__alt_name', 'recipient__company', 'recipient__last_name',
        'building__name', 'start', 'end', 'subscriber__notes')
    list_filter = (
        filters.SubscriptionArticlesFilter,
        'notes', 'end', 'subscriber__company')

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

    @admin.display(description=_('abo_nr'))
    def display_abo_nr(self, obj): 
        if obj.subscriber.notes:
            return obj.subscriber.notes.replace('abo_nr: ', '')
        return None

    @admin.display(description=_('Consumption'))
    def display_subscriber(self, obj):       
        return obj.subscription.subscriber.__str__()[:40]
