'''
billing/calc.py
'''
import json
import openpyxl
from openpyxl.styles import Font

from django.db.models import Q, Sum, Min, Max
from django.http import HttpResponse
from django.utils.translation import gettext as _

from core.models import AddressTag, AddressMunicipal, PersonAddress
from scerp.admin import ExportExcel
from .models import Period, Route, Measurement, Subscription


# GFT Template
class METER:
    TEMPLATE = {
        'billing_mde': {
            'route': {
                'name': None,
                'user': None
            },
            'meter': []
        }
    }


# Helpers
def convert_datetime_to_date(dt):
    return dt.strftime('%Y-%m-%d')


def shift_encode(text, shift=3):
    return ''.join(chr((ord(c) + shift) % 126) for c in text)


class RouteMeterExport:

    def __init__(
            self, modeladmin, request, queryset, route, responsible_user=None,
            route_date=None, key=None):
        self.modeladmin = modeladmin
        self.request = request
        self.queryset = queryset
        self.name = f'{route.tenant.code}, {route.__str__()}'
        self.route = route
        self.username = responsible_user.username if responsible_user else None
        self.route_date = route_date

        # encryption
        self.key = key

    # Helpers
    def get_buildings(self):
        # Get address_tags
        tags = [x for x in self.route.address_tags.all()]

        # Filter Buildings
        if self.route.buildings.exists():
            queryset = self.route.buildings.all()
        else:
            queryset = Building.objects.filter(tenant=self.route.tenant)
        buildings = queryset.filter(address__tags__in=tags)

        return buildings

    def get_subscriptions(self, buildings):
        # start, end
        start = self.route.get_start()
        end = self.route.get_start()

        # In scope
        queryset = Subscription.objects.filter(
            tenant=self.route.tenant,
            building__in=buildings,
            start__lte=end,
        ).filter(
            Q(end__gte=start) | Q(end__isnull=True)
        )
        return queryset.all()

    def get_last_consumption(self, counter):
        if self.route.last_period:
            total = Measurement.objects.filter(
                tenant=self.route.tenant,
                counter=counter,
                period=self.last_period
            ).aggregate(Sum('consumption'))
            return total['consumption__sum']
        else:
            return 0

    def make_meter(self, subscription, counter, excel, start, end):
        ''' make meter dict for json / excel export
        if excel we optimize data to our needs
        '''
        # last consumption
        consumption = self.get_last_consumption(counter)
        consumption = round(consumption, 1) if consumption else None
        min = (
            round(consumption * float(self.route.confidence_min), 1)
            if consumption else 0)
        max = (
            round(consumption * float(self.route.confidence_max), 1)
            if consumption else None)

        # subscription
        name = subscription.subscriber.alt_name

        # building address
        address = subscription.building.address
        address_category_names = ','.join([
            x.code for x in subscription.building.address.categories.all()])
        street = address.address or ''

        # encryption
        if self.key:
            name = shift_encode(name, self.key)
            street = shift_encode(street, self.key)

        # make record
        if excel:
            # Get recepient address
            recipient_addr = PersonAddress.objects.filter(
                person=subscription.recipient,
                type=PersonAddress.TYPE.INVOICE).first().address

            # Make record
            meter = {
                'counter_id': counter.number,
                'street': street,
                'subscriber': name,
                'invoice_recipient': subscription.recipient.alt_name,
                'invoice_address': (
                    f"{recipient_addr.address}, "
                    f"{recipient_addr.zip}, {recipient_addr.city}"
                ),
                'area': address_category_names,
                'start': start,
                'end': end,
                'consumption_old': consumption
            }
        else:
            # current date
            if self.route_date:
                current_date = convert_datetime_to_date(self.route_date)
            else:
                current_date = None

            # previous date
            if self.route.last_period:
                previous_date = convert_datetime_to_date(
                    self.route.last_period.end)
            else:
                previous_date = None

            meter = {
                'id': counter.number,
                'energytype': self.route.period.energy_type,
                'number': counter.number,
                'hint': counter.notes,
                'address': {
                    'street': street,
                    'housenr': '',
                    'city': address.city,
                    'zip': address.zip,
                    'hint': subscription.building.description
                },
                'subscriber': {
                    'name': name,
                    'hint': subscription.subscriber.notes
                },
                'value': {
                    'obiscode': counter.obiscode,
                    'dateOld': previous_date,
                    'old': consumption,
                    'min': min,
                    'max': max,
                    'dateCur': current_date
                }
            }

        return meter

    # Methods
    def get_data(self, excel=False):
        data = METER.TEMPLATE

        # Update route
        data['billing_mde']['route'].update({
            'name': self.name,
            'user': self.username
        })

        # Start, end
        start = (
            self.route.start if self.route.start else self.route.period.start)
        end = (
            self.route.end if self.route.end else self.route.period.end)

        # Get subscriptions
        buildings = self.get_buildings()
        subscriptions = self.get_subscriptions(buildings)
        number_of_counters = 0
        # Fill in meters

        for subscription in subscriptions:
            for counter in subscription.counters.all():
                meter = self.make_meter(
                    subscription, counter, excel, start, end)
                data['billing_mde']['meter'].append(meter)
                number_of_counters += 1

        # Update route
        self.route.number_of_buildings = len(buildings)
        self.route.number_of_subscriptions = len(subscriptions)
        self.route.number_of_counters = number_of_counters
        self.route.save()

        # return data, if excel only meter records
        return data['billing_mde']['meter'] if excel else data

    def make_response_json(self, data, filename):
        # Create json
        json_data = json.dumps(data, ensure_ascii=False)

        # Create the HTTP response and set the appropriate content type with
        # UTF-8 charset
        response = HttpResponse(
            json_data, content_type='application/json; charset=utf-8')

        # Define the file name for the download
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"')

        return response

    def make_response_excel(self, data_list, filename):
        # Init
        headers = tuple(data_list[0].keys())
        data = [tuple(data.values()) for data in data_list]

        # Make
        excel = ExportExcel(
            self.modeladmin, self.request, self.queryset, filename)
        response = excel.generate_response(
            headers=headers, data=data)

        return response


class MeasurementAnalyse:

    def __init__(self, modeladmin, queryset):
        self.model = modeladmin.model
        self.queryset = queryset

    def analyse(self):
        '''
        analyse data and returns dictionary
        '''
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

    def output_excel(self, data, filename=None, title=None):
        # Create an Excel workbook and worksheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title if title else _('Consumption Analysis')

        if not filename:
            filename = 'output.xlsx'

        # Add header with bold font
        header = [_('Label'), _('Value')]
        ws.append(header)

        bold_font = Font(bold=True)
        for col_num, cell in enumerate(ws[1], 1):
            cell.font = bold_font  # Make header bold

        # Add data rows
        rows = [
            [_('Records Processed'), data['record_count']],
            [_('Periods'), ', '.join(x.name for x in data['periods'])],
            [_('Routes'), ', '.join(x.name for x in data['routes'])],
            [_('Areas'), ', '.join(x.code for x in data['areas'])],
            [_('Period Start, End'), f"{data['start']} - {data['end']}"],
            [_('Value Dates From - To'), f"{data['min_date']} - {data['max_date']}"],
            [_('Total Consumption'), f"{data['consumption']:.0f} m³"],
            [_('Previous'),
             f"{data['consumption_previous']:.0f}"
             if data['consumption_previous'] else '-'],
            [_('Change in %'), data['consumption_change']],
        ]

        for row in rows:
            ws.append(row)

        # Auto-adjust column widths
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2  # Padding

        # Prepare HTTP response
        response = HttpResponse(
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )
        response['Content-Disposition'] = f"attachment; filename={filename}"

        # Save workbook to response
        wb.save(response)
        return response
