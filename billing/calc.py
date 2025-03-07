'''
billing/calc.py
'''
import json

from django.db.models import Q, Sum, Min, Max
from django.utils import timezone

from asset.models import DEVICE_STATUS, Device, EventLog
from core.models import AddressCategory, Building
from .models import Period, Route, Measurement, Subscription


# Helpers    
def convert_datetime_to_date(dt):
    return dt.strftime('%Y-%m-%d')
        
        
def shift_encode(text, shift=3):
    return ''.join(chr((ord(c) + shift) % 126) for c in text)
    

class PeriodCalc:

    def __init__(self, period):
        self.period = period
        self.tenant = period.tenant

    @property
    def previous_period(self):
        return Period.objects.filter(
            tenant=self.tenant,
            asset_category=self.period.asset_category
        ).exclude(id=self.period.id).order_by('end').last()

    @property
    def routes(self):
        return Route.objects.filter(
            tenant=self.tenant,
            period=self.period,
            start__gte=self.period.start,
            end__lte=self.period.end,
        ).order_by('end')

    def get_buildings(self, route=None):
        # get address_categories
        categories = []
        if route:
            routes = [route]
        else:
            routes = self.routes

        for route in routes:
            for category in route.address_categories.all():
                if category not in categories:
                    categories.append(category)

        # get buildings        
        return Building.objects.filter(
            tenant=self.tenant,
            # address__categories__in=categories
        ).order_by('address')

    def get_subscriptions(self, buildings):
        return Subscription.objects.filter(
            tenant=self.tenant,
            building__in=buildings,
            start__lte=self.period.end,
        ).filter(
            Q(end__gte=self.period.start) | Q(end__isnull=True)
        ).order_by('subscriber__alt_name')

    @staticmethod
    def counter_get_date_mounted(events):
        for event in events:
            if event.status == DEVICE_STATUS.MOUNTED:
                return event.date
        return None

    @staticmethod
    def counter_get_date_last_negative_status(events):
        event = events[-1]
        if event.status != DEVICE_STATUS.MOUNTED:
            return event.dat
        return None

    def get_counters(self, buildings, start=None, end=None):
        ''' get all counters that were in office in this period of time '''
        # Get start, end
        if not start:
            start = self.period.start
        if not end:
            end = self.period.end

        # get all events for the buildings in scope
        queryset = EventLog.objects.filter(
            # all mounting events on this building
            tenant=self.tenant,
            building__in=buildings,
            date__lte=end
        ).order_by('date')
        events = [x for x in queryset.all()]

        # get all counters
        counters = []
        for event in events:
            counter = event.device
            counter_events = [x for x in events if x.device == counter]
            if not self.counter_get_date_mounted(counter_events):
                continue
            if self.counter_get_date_last_negative_status(counter_events):
                continue
            counters.append(counter)

        return counters

    def get_measurements(self, counters):
        return Measurement.objects.filter(
            tenant=self.tenant,
            counter__in=counters,
            datetime__gte=self.period.start,
            datetime__lte=self.period.end,
            counter__status=DEVICE_STATUS.MOUNTED
        ).order_by('counter__code')


class RouteCalc:

    def __init__(self, route, user, key=None):
        self.route = route
        self.name = f'{route.tenant.code}, {route.__str__()}'
        self.user = user.username
        self.energy_type = route.period.energy_type
        self.date_str = convert_datetime_to_date(timezone.now())
        self.key = key

    @staticmethod
    def assign_value(obiscode, date_str, measurement):
        # Init
        value = {
            'obiscode': obiscode,
            'dateCur': date_str,
            'cur': 0
        }
        
        if measurement:
            value.update({
                'dateOld': convert_datetime_to_date(
                    measurement.datetime.date()),
                'old': measurement.value,
                'min': measurement.value_min,
                'max': measurement.value_max
            })
        else:
            value.update({
                'dateOld': None,
                'old': 0,
                'min': None,
                'max': None
            })
            
        return value

    def export(self):
        # Init period
        handler = PeriodCalc(self.route.period)
        
        # Get core data
        buildings = handler.get_buildings(self.route)
        counters = handler.get_counters(
            buildings, self.route.start, self.route.end)

        # Subscriptions
        subscription = {
            subscription.building: subscription
            for subscription in handler.get_subscriptions(buildings)
        }

        # Get previous measurements
        previous_period = handler.previous_period
        handler_prev = PeriodCalc(previous_period)
        measurement_previous = {
            measurement.counter: measurement
            for measurement in handler_prev.get_measurements(counters)
        }

        # Make meters
        meters = []

        for counter in counters:
            # prepare            
            status = counter.get_status()
            building = status.building
            subscriber = subscription[building].subscriber
            notes = subscription[building].notes
            measurement = measurement_previous.get(counter)
            address = getattr(status.building, 'address', None)
            if not address:
                raise ValueError(f"{status.building} has no address")
            
            # build
            name = subscriber.alt_name
            street = address.address or ''
            if self.key:
                name = shift_encode(name, self.key)
                street = shift_encode(street, self.key)
            
            meters.append({
                'id': counter.number,
                'energytype': self.energy_type,
                'number': counter.number,
                'hint': counter.notes,
                'address': {
                    'street': street,
                    'housenr': '',
                    'city': address.city,
                    'zip': address.zip,
                    'hint': status.building.description
                },
                'subscriber': {
                    'name': name,
                    'hint': notes
                },
                'value': self.assign_value(
                    counter.obiscode, self.date_str, measurement)
            })

        # Make json
        data = {
            'billing_mde': {
                'route': {
                    'name': self.name,
                    'user': self.user
                },
                'meter': meters
            }
        }
    
        # Specify the filename
        filename = "data.json"

        # Open the file and write the JSON data
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


class Analyze:
    
    def __init__(self, model, queryset):
        self.model = model
        self.queryset = queryset
        

class AnalyseMeasurement(Analyze):
    
    def analyse(self):
        # Distinct values of periods (assuming 'route' relates to periods)
        distinct_periods = set([x.route.period for x in self.queryset.all()])

        # Distinct values of routes
        distinct_routes = set([x.route for x in self.queryset.all()])        

        # Distinct values of areas (assuming 'address__categories' link to areas)
        distinct_areas = AddressCategory.objects.filter(
            id__in=self.queryset.values('building__address__categories')
        ).distinct()

        # Start and end of periods
        start = min([x.period.start for x in self.queryset.all()])
        end = max([x.period.end for x in self.queryset.all()])

        # Min and Max datetime
        min_date = self.queryset.aggregate(
            Min('datetime'))['datetime__min'].date()
        max_date = self.queryset.aggregate(
            Max('datetime'))['datetime__max'].date()

        # Sum of consumption
        total_consumption = self.queryset.aggregate(
            Sum('consumption'))['consumption__sum'] or 0

        # Sum of consumption
        total_consumption_previous = self.queryset.aggregate(
            Sum('consumption_previous'))['consumption_previous__sum'] or 0

        # Growth        
        consumption_change = (
            1- (total_consumption - total_consumption_previous) 
            / total_consumption_previous
        ) if total_consumption_previous else None

        return {
            'periods': distinct_periods,
            'routes': distinct_routes,
            'areas': distinct_areas,
            'start': start,
            'end': end,
            'min_date': min_date,
            'max_date': max_date,
            'consumption': total_consumption,
            'consumption_previous': total_consumption_previous,
            'consumption_change': consumption_change
        }     
