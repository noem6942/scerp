'''
core/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant_data
from core.models import Area
from scerp.filters import StepFilter
from scerp.mixins import primary_language
from .models import Period, Route


# Custom Filters for Measurement
class MeasurementPeriodFilter(admin.SimpleListFilter):
    title = _('Period')
    parameter_name = 'period'

    def lookups(self, request, model_admin):
        '''Return categories filtered by tenant'''
        tenant_id = get_tenant_data(request).get('id')

        categories = Period.objects.filter(
            tenant_id=tenant_id  # Add tenant filtering here
        ).values_list('id', 'name')

        return categories

    def queryset(self, request, queryset):
        tenant_id = get_tenant_data(request).get('id')

        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,  # Ensure tenant filter applies here too
                route__period__id=self.value()
            )
        return queryset


class MeasurementRouteFilter(admin.SimpleListFilter):
    title = _('Route')
    parameter_name = 'route'

    def lookups(self, request, model_admin):
        '''Return categories filtered by tenant'''
        tenant_id = get_tenant_data(request).get('id')

        categories = Route.objects.filter(
            tenant_id=tenant_id  # Add tenant filtering here
        ).values_list('id', 'name')

        return categories

    def queryset(self, request, queryset):
        tenant_id = get_tenant_data(request).get('id')

        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,  # Ensure tenant filter applies here too
                route__id=self.value()
            )
        return queryset


class MeasurementAreaFilter(admin.SimpleListFilter):
    title = _('Area')
    parameter_name = 'areas'

    def lookups(self, request, model_admin):
        '''Return categories filtered by tenant'''
        tenant_id = get_tenant_data(request).get('id')

        areas = Area.objects.filter(
            tenant_id=tenant_id  # Add tenant filtering here
        ).values_list('id', 'name')

        return areas

    def queryset(self, request, queryset):
        tenant_id = get_tenant_data(request).get('id')

        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,  # Ensure tenant filter applies here too
                address__area=self.value()
            )
        return queryset


class MeasurementBatteryFilter(StepFilter):
    title = _('Battery Level')  # The title of the filter
    fieldname = 'current_battery_level'
    parameter_name = fieldname  # The query parameter in the URL
    unit = _('Periods')
    steps = [0, 3, 10, 20]
    step_max = max(steps)


class MeasurementConsumptionFilter(StepFilter):
    title = _('Consumption')  # The title of the filter
    fieldname = 'consumption'
    parameter_name = fieldname  # The query parameter in the URL
    unit = 'm³'
    steps = [0, 50, 100, 1000]
    step_max = max(steps)
