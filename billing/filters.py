'''
core/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from accounting.models import Article
from core.safeguards import get_tenant_data
from core.models import AddressTag
from scerp.mixins import primary_language
from .models import ARTICLE, Period, Route


# Custom Filters for Subscription
class SubscriptionArticlesFilter(admin.SimpleListFilter):
    title = _('Article')
    parameter_name = 'article'

    def lookups(self, request, model_admin):
        '''Return categories filtered by tenant'''
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        articles = Article.objects.filter(
            tenant_id=tenant_id,
            nr__startswith=ARTICLE.TYPE.PREFIX
        ).values_list('id', 'name')

        # return translated names
        return [
            (id, primary_language(name))
            for id, name in articles
        ]

    def queryset(self, request, queryset):
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,  # Ensure tenant filter applies here too
                articles__id=self.value()
            )
        return queryset


# Custom Filters for Measurement
class MeasurementPeriodFilter(admin.SimpleListFilter):
    title = _('Period')
    parameter_name = 'period'

    def lookups(self, request, model_admin):
        '''Return categories filtered by tenant'''
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        categories = Period.objects.filter(
            tenant_id=tenant_id  # Add tenant filtering here
        ).values_list('id', 'name')

        return categories

    def queryset(self, request, queryset):
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

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
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        categories = Route.objects.filter(
            tenant_id=tenant_id  # Add tenant filtering here
        ).values_list('id', 'name')

        return categories

    def queryset(self, request, queryset):
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,  # Ensure tenant filter applies here too
                route__id=self.value()
            )
        return queryset


class MeasurementBuildingAddressCategoryFilter(admin.SimpleListFilter):
    title = _('Area')
    parameter_name = 'tags'

    def lookups(self, request, model_admin):
        '''Return categories filtered by tenant'''
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        tags = AddressTag.objects.filter(
            tenant_id=tenant_id  # Add tenant filtering here
        ).values_list('id', 'tag')

        return tags

    def queryset(self, request, queryset):
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')

        if self.value():
            return queryset.filter(
                tenant__id=tenant_id,  # Ensure tenant filter applies here too
                building__address__categories__id=self.value()
            )
        return queryset


class MeasurementConsumptionFilter(admin.SimpleListFilter):
    title = _('Consumption')  # The title of the filter
    parameter_name = 'consumption'  # The query parameter in the URL
    STEPS = [0, 50, 100, 1000]    
    STEP_MAX = max(STEPS)

    def lookups(self, request, model_admin):
        '''
        Return a list of tuples of filter options (displayed in the admin filter sidebar).
        '''
        steps = self.STEPS        
        
        return [
            ('null', _('Empty'))
        ] + [
            (str(steps[i]), f'{steps[i]} - {steps[i + 1]} m³')  # Ensure keys are strings
            for i in range(len(steps) - 1)
        ] + [
            (str(self.STEP_MAX), f'{self.STEP_MAX} m³ +')
        ]

    def queryset(self, request, queryset):
        '''
        Filter the queryset based on the selected filter option.
        '''
        value = self.value()

        if value is None:
            return queryset  # No filter applied

        if value == 'null':
            return queryset.filter(consumption__isnull=True)

        try:
            value = int(value)  # Convert value to integer
        except ValueError:
            return queryset  # Return unchanged if conversion fails

        if value == self.STEP_MAX:
            return queryset.filter(consumption__gt=self.STEP_MAX)

        # Filter ranges
        steps = self.STEPS
        for i in range(len(steps) - 1):
            min_val, max_val = steps[i], steps[i + 1]
            if value == min_val:
                return queryset.filter(
                    consumption__gte=min_val, consumption__lt=max_val)

        return queryset
