from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

from core.admin import AttachmentInline
from scerp.actions import export_excel, export_json, default_actions
from scerp.admin import (
    BaseAdmin, BaseTabularInline, Display, verbose_name_field
)
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site

from . import filters, actions as a
from .models import (
    Setup, Period, Route, Measurement, Subscription, SubscriptionArticle,
    SubscriptionArchive
)



@admin.register(Setup, site=admin_site)
class SetupAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'order_contract', 'order_category', 'contact']

    # Display these fields in the list view
    list_display = ('code', 'name',) + FIELDS.ICON_DISPLAY
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name')
    autocomplete_fields = ['contact']

    # Actions
    actions = default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'name', 'header',
                'order_contract', 'order_category', 'contact', 
                'show_partner'),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )



@admin.register(Period, site=admin_site)
class PeriodAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = (
        'name', 'start', 'end'
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
            'fields': ('code', 'name', 'start', 'end'),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )


@admin.register(Route, site=admin_site)
class RouteAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'period']
    protected_many_to_many = ['addresses', 'comparison_periods']

    # Display these fields in the list view
    list_display = (
        'name', 'period', 'display_start', 'display_end',
        'duration', 'display_filters', 'is_default', 'status'
    ) + (
        'number_of_subscriptions', 'number_of_counters',
        'number_of_addresses'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT
    list_display_links = ('name', 'period')
    readonly_fields = ('duration', 'status') + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('name', 'period__name')
    list_filter = ('is_default', 'status')

    # Actions
    actions = [
        a.export_counter_data_json,
        a.import_counter_data_json,        
        a.route_billing,
        #a.export_counter_data_excel,
        a.route_copy
    ] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'name', 'period', 'period_previous', 'comparison_periods',
                'setup'
            ),
        }),
        (_('Filters'), {
            'fields': (
                'areas', 'addresses', 'asset_categories', 'start', 'end',
            ),
            'classes': ('expand',),
        }),
        (_('Calculations'), {
            'fields': (
                'confidence_min', 'confidence_max', 'duration', 'status'
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT        
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

    @admin.display(description=_('Start'))
    def display_start(self, obj):
        return obj.get_start()

    @admin.display(description=_('End'))
    def display_end(self, obj):
        return obj.get_end()


@admin.register(Measurement, site=admin_site)
class MeasurementAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'counter', 'route', 'address', 'period',
        'subscription']

    # Display these fields in the list view
    list_display = (
        'id', 'datetime', 'display_abo_nr', 'address',
        'display_subscriber', 'display_area', 'route', 'display_consumption'
    ) + FIELDS.ICON_DISPLAY
    list_display_links = ('id', 'datetime')
    ordering = ('-period__end', '-consumption')
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = (
        'subscription__subscriber__company',
        'subscription__subscriber__last_name', 'counter__code', 'datetime')
    list_filter = (
        filters.MeasurementAreaFilter,
        filters.MeasurementPeriodFilter,
        filters.MeasurementRouteFilter,
        filters.MeasurementConsumptionFilter,
        'datetime')
    autocomplete_fields = ['counter', 'address', 'subscription']

    # Actions
    actions = [
        a.analyse_measurement,
        a.anaylse_measurent_excel,
    ] + [export_excel] + default_actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'counter', 'route', 
                'datetime', 'value', 'consumption', 'current_battery_level',
            ),
        }),
        (_('Last'), {
            'fields': (
                'datetime_latest', 'value_latest', 'consumption_latest',
            ),
            'classes': ('collapse',),
        }),        
        (_('References'), {
            'fields': (
                'address', 'period', 'subscription'
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

    @admin.display(description=_('Subscriber'))
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
        return obj.address.area


class ArticleInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'subscription', 'article']

    # Inline
    model = SubscriptionArticle
    fields = ['quantity', 'article']  # Only show these fields    
    extra = 0  # Number of empty forms displayed
    autocomplete_fields = ['article']  # Improves FK selection performance
    show_change_link = False  # Shows a link to edit the related model


@admin.register(Subscription, site=admin_site)
class SubscriptionAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = [
        'tenant', 'version', 'subscriber', 'partner', 'recipient', 'address']
    help_text = _(
        "Create a new subscription if owner changes, otherwise previous "
        "values are shown at the bill which is against policies. ")

    # Display these fields in the list view
    list_display = (
        'display_subscriber', 'partner', 'address', 'description',
        'display_invoice_address_list',
        'start', 'end', 'display_abo_nr', 'number_of_counters',
        'last_route_out', 'last_measurement'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT
    list_display_links = ('display_subscriber', 'address')
    readonly_fields = (
        'display_invoice_address', 'display_invoice_address_list',
        'display_counters', 'last_route_out',
        'routes_out', 'invoices', 'display_abo_nr'
    ) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = (
        'subscriber__company',
        'subscriber__last_name','subscriber__first_name',
        'partner__last_name','partner__first_name',
        'address__stn_label', 'address__adr_number', 'start', 'end',
        'description', 'counters__code', 'notes', 'subscriber_number')
    list_filter = (
        'tag', 'number_of_counters', 'end', 'subscriber__company')
    autocomplete_fields = ['subscriber', 'partner', 'recipient', 'address']

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'subscriber', 'partner', 'recipient',
                'display_invoice_address',
                'start', 'end', 'address', 'description', 'tag', 'counters'
            ),
        }),
        (_('Controlling'), {
            'fields': (
                'display_counters', 'routes_out', 'invoices', 'display_abo_nr'
            ),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

    # Actions
    actions = [export_excel] + default_actions
    
    # Inlines
    inlines = [ArticleInline]

    @admin.display(description=_('abo_nr'))
    def display_abo_nr(self, obj):
        return obj.subscriber_number

    @admin.display(description=_('Subscriber'))
    def display_subscriber(self, obj):
        return obj.subscriber.__str__()[:40]

    @admin.display(description=_(
        'Invoice Address (Invoice if specified else Main)'))
    def display_invoice_address(self, obj):
        return obj.invoice_address

    @admin.display(description=_('Invoice Address'))
    def display_invoice_address_list(self, obj):
        return obj.invoice_address   

    @admin.display(description=_('Counters'))
    def display_counters(self, obj):
        return ','.join([x.__str__() for x in obj.counters.order_by('nr')])
 
    @admin.display(description=_('Last Route'))
    def last_route_out(self, obj):
        route = obj.routes_out.last() 
        return str(route.id) if route else None
 
    @admin.display(description=_('Last Route / Measurement'))
    def last_measurement(self, obj):
        measurement = obj.measurements.last() 
        return (
            f"{measurement.route.id} / {round(measurement.consumption)}"
            if measurement and measurement.consumption else None
        )

@admin.register(SubscriptionArchive, site=admin_site)
class SubscriptionArchiveAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']
    read_only = True

    # Display these fields in the list view
    list_display = (
        'subscriber_number', 'subscriber_name', 'street_name', 'amount_gross'
    )

    # Search, filter
    search_fields = (
        'subscriber_number', 'subscriber_name', 'street_name', 'amount_gross'
    )
