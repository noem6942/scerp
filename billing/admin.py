from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

from core.admin import AttachmentInline
from scerp.actions import export_excel, export_json, default_actions
from scerp.admin import BaseAdmin, Display, verbose_name_field
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site

from . import filters, actions as a
from .models import Period, Route, Measurement, Subscription


@admin.register(Period, site=admin_site)
class PeriodAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'version']
    protected_many_to_many = ['asset_categories']

    # Display these fields in the list view
    list_display = (
        'name', 'display_categories', 'start', 'end'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name', 'start', 'end')
    list_filter = ('end',)
    
    # Actions
    actions = default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'energy_type', 'asset_categories', 'name', 'start',
                'end'),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

    @admin.display(description=_('Categories'))
    def display_categories(self, obj):
        values = [x.code for x in obj.asset_categories.all()]
        return ', '.join(values)


@admin.register(Route, site=admin_site)
class RouteAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'period']
    protected_many_to_many = ['addresses']

    # Display these fields in the list view
    list_display = (
        'name', 'period', 'start', 'end', 'duration', 'display_filters',
        'is_default', 'status'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT + (
        'number_of_subscriptions', 'number_of_counters',
        'number_of_addresses'    
    )
    readonly_fields = ('duration', 'status') + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('name', 'period')
    list_filter = ('is_default', 'status')

    # Actions
    actions = [
        a.export_counter_data_json, 
        a.export_counter_data_excel
    ] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'name', 'period', 'last_period', 
            ),
        }),
        (_('Filters'), {
            'fields': (
                'address_tags', 'addresses', 'start', 'end',                 
            ),
            'classes': ('expand',),
        }),
        (_('Calculations'), {
            'fields': (
                'confidence_min', 'confidence_max', 'duration', 'status'              
            ),
            'classes': ('expand',),
        }),
    )

    inlines = [AttachmentInline]

    @admin.display(description=_('filters'))
    def display_filters(self, obj):
        values = []
        if obj.addresses.exists():
            values.append(str(_('Addresses')))
        if obj.start:
            values.append(str(_('Start')))
        if obj.end:
            values.append(str(_('End')))
        return ', '.join(values)


@admin.register(Measurement, site=admin_site)
class MeasurementAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'counter', 'route', 'building', 'period', 
        'subscription']

    # Display these fields in the list view
    list_display = (
        'id', 'datetime', 'display_abo_nr',
        'display_subscriber', 'display_area', 'display_consumption'
    ) + FIELDS.ICON_DISPLAY
    list_display_links = ('id', 'datetime')
    ordering = ('-consumption', 'subscription__subscriber__alt_name')
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('subscription__subscriber__alt_name', 'datetime')
    list_filter = (
        filters.MeasurementBuildingAddressCategoryFilter,
        filters.MeasurementPeriodFilter,
        filters.MeasurementRouteFilter,
        filters.MeasurementConsumptionFilter,
        'datetime')

    # Actions
    actions = [
        a.analyse_measurment, 
        a.anaylse_measurent_excel,
    ] + [export_excel] + default_actions

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

    @admin.display(description=_('abo_nr'))
    def display_abo_nr(self, obj):
        return obj.subscription.subscriber_number

    @admin.display(
        description=_('Subscriber'),
        ordering='subscription__subscriber__alt_name')
    def display_subscriber(self, obj):
        return obj.subscription.subscriber.__str__()[:40]

    @admin.display(description=_('Consumption'), ordering='consumption')
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
class SubscriptionAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'subscriber', 'invoice_address', 'address']
    protected_many_to_many = ['articles']

    # Display these fields in the list view
    list_display = (
        'subscriber__alt_name', 'invoice_address', 'address',
        'start', 'end', 'display_abo_nr', 'number_of_counters'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT 
    list_display_links = ('subscriber__alt_name', )
    readonly_fields = ('address',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = (
        'subscriber__alt_name', 'subscriber__company', 'subscriber__last_name',        
        'building__name', 'start', 'end')
    list_filter = (
        filters.SubscriptionArticlesFilter,
        'number_of_counters', 'end', 'subscriber__company')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'subscriber', 'invoice_address', 'start', 'end', 'address',
                'articles'
            ),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

    # Actions    
    actions = [export_excel] + default_actions

    @admin.display(description=_('abo_nr'))
    def display_abo_nr(self, obj):
        return obj.subscriber_number

    @admin.display(description=_('Consumption'))
    def display_subscriber(self, obj):
        return obj.subscription.subscriber.__str__()[:40]
