'''
billing/calc.py
'''
from datetime import datetime
import json
import openpyxl
from openpyxl.styles import Font

from django.db.models import Q, Sum, Min, Max
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _

from asset.models import Device
from core.models import Area, AddressMunicipal, PersonAddress, Attachment
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


def convert_str_to_datetime(dt_string):
    # is only date
    try:
        naive_datetime = datetime.strptime(dt_string, '%Y-%m-%d')
    except:
        return None
        
    # Convert the naive datetime to an aware datetime
    return timezone.make_aware(naive_datetime)    


def extract_datetime_from_route_filename(filename):
    ''' e.g. filename = "route0120250325_2025-03-25_16-28-49.json"
    '''
    try:
        # Extract the datetime string after the first underscore
        datetime_part = (
            filename.split('_')[1] + '_'
            + filename.split('_')[2].split('.')[0])

        # Parse the datetime string into a naive datetime object
        naive_datetime = datetime.strptime(datetime_part, '%Y-%m-%d_%H-%M-%S')

        # Convert the naive datetime to an aware datetime
        aware_datetime = timezone.make_aware(naive_datetime)

        return aware_datetime
    except (ValueError, IndexError):
        # Return None if the filename doesn't match the expected pattern
        return None


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
    def get_addresses(self):
        # Filter Addresses
        if self.route.addresses.exists():
            addresses = self.route.addresses.all()
        else:
            queryset = AddressMunicipal.objects.filter(
                tenant=self.route.tenant)
            if self.route.areas.exists():                
                queryset = queryset.filter(area__in=areas)
            addresses = queryset.all()

        return addresses

    def get_subscriptions(self, addresses):
        # start, end
        start = self.route.get_start()
        end = self.route.get_start()

        # In scope
        queryset = Subscription.objects.filter(
            tenant=self.route.tenant,
            address__in=addresses,
            start__lte=end,
        ).filter(
            Q(end__gte=start) | Q(end__isnull=True)
        )
        return queryset.all()

    def get_consumption_previous(self, counter):
        if self.route.previous_period:
            total = Measurement.objects.filter(
                tenant=self.route.tenant,
                counter=counter,
                period=self.route.previous_period
            ).aggregate(Sum('consumption'))
            return total['consumption__sum'] or 0
        else:
            return 0

    def get_last_value(self, counter):
        measurement = Measurement.objects.filter(
                tenant=self.route.tenant,
                counter=counter,
                period=self.route.previous_period
            ).order_by('datetime').last()        
        return measurement.value or 0 if measurement else 0

    def make_meter(self, subscription, counter, excel, start, end):
        ''' make meter dict for json / excel export
        if excel we optimize data to our needs
        '''
        # last consumption
        value = self.get_last_value(counter)
        consumption_previous = self.get_consumption_previous(counter)
        
        min, max = value, value
        if consumption_previous:            
            min += consumption_previous * float(self.route.confidence_min)
            max += consumption_previous * float(self.route.confidence_max)

        # subscription
        name = subscription.subscriber.__str__()
        if subscription.partner:
            name += ' & ' + subscription.partner.__str__()

        # address
        address = subscription.address
        street = address.stn_label or ''
        nr = address.adr_number or ''

        # make record
        if excel:
            # Make record
            meter = {
                'counter_id': counter.number,
                'address': f"{street} {nr}",
                'subscriber': name,
                'area': address.area,
                'start': start,
                'end': end,
                'consumption_previous': consumption_previous,
                'obiscode': counter.obiscode
            }
        else:
            # current date
            if self.route_date:
                current_date = convert_datetime_to_date(self.route_date)
            else:
                current_date = None

            # previous date
            if self.route.previous_period:
                previous_date = convert_datetime_to_date(
                    self.route.previous_period.end)
            else:
                previous_date = None

            # encryption
            if self.key:
                name = shift_encode(name, self.key)
                nr = shift_encode(street, self.key)
                street = shift_encode(nr, self.key)

            meter = {
                'id': counter.number,
                'energytype': self.route.period.energy_type,
                'number': counter.number,
                'hint': json.dumps({
                    'subscription_id': subscription.id,
                    'address_id': address.id,
                    'consumption_previous': round(consumption_previous, 1)
                }),
                'address': {                    
                    'street': street,
                    'housenr': nr,
                    'city': address.city,
                    'zip': address.zip,
                    'hint': f'address_id: {address.id}',
                },
                'subscriber': {
                    'name': name,
                    'hint': subscription.subscriber.notes
                },
                'value': {
                    'obiscode': counter.obiscode,
                    'dateOld': previous_date,
                    'old': round(value, 1),
                    'min': round(min, 1),
                    'max': round(max, 1),
                    'dateCur': current_date
                }
            }

        return meter

    # Methods
    def get_data(self, excel=False):
        data = dict(METER.TEMPLATE)

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
        addresses = self.get_addresses()
        print("*addresses", len(addresses))
        subscriptions = self.get_subscriptions(addresses)
        print("*subscriptions", len(subscriptions))
        number_of_counters = 0
        # Fill in meters

        for subscription in subscriptions:
            for counter in subscription.counters.all():
                meter = self.make_meter(
                    subscription, counter, excel, start, end)
                data['billing_mde']['meter'].append(meter)
                number_of_counters += 1

        # Update route
        self.route.number_of_addresses = len(addresses)
        self.route.number_of_subscriptions = len(subscriptions)
        self.route.number_of_counters = number_of_counters
        self.route.status = Route.STATUS.COUNTER_EXPORTED
        self.route.save()

        # return data, if excel only meter records
        return data['billing_mde']['meter'] if excel else data

    def make_response_json(self, data, filename):
        # Create json
        json_data = json.dumps(data, ensure_ascii=False, indent=4)

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
        distinct_areas = Area.objects.filter(
            id__in=self.queryset.values('address__area')
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


class RouteMeterImport:
    
    def __init__(self, request, route):
        self.route = route
        self.user = request.user
        
    def process(self, json_file):
        # Load file
        file_data = json_file.read().decode('utf-8')
        data = json.loads(file_data)

        # Check file    
        try:
            measurements = data['billing_mde']['meter']
        except:
            raise ValueError(_("Not a valid file"))
        
        # get meter data
        count = 0
        for meter in measurements:
            counter = Device.objects.filter(
                tenant=self.route.tenant, code=meter['id']
            ).first()
            if not counter:
                raise ValueError(_(f"counter {meter['id']} not found."))

            # Prepare data
            value = meter['value']
            actual_value = (value['min'] + value['max']) / 2  # fake actual_value
            maintenance = json.loads(meter['hint'])
            
            data = {
                # previous
                'datetime_previous': convert_str_to_datetime(value['dateOld']),
                'value_previous': value['old'],                
                'value_max': value['max'],
                'value_min': value['min'],
                
                # import
                'datetime': convert_str_to_datetime(value['dateCur']),
                'value': actual_value,
                'consumption': actual_value - value['old'],

                # maintenance
                'period': self.route.period,
                'address_id': maintenance['address_id'],
                'subscription_id': maintenance['subscription_id'],
                'consumption_previous': maintenance['consumption_previous'],
                'tenant': self.route.tenant,
                'created_by': self.user,
            }
            
            # Store data
            obj, created = Measurement.objects.get_or_create(
                counter=counter, route=self.route,
                defaults=data)                
            if created:    
                count += 1

        # Create an Attachment instance
        attachment = Attachment.objects.create(
            tenant=self.route.tenant,  # Set the tenant
            content_object=self.route,  # Set the associated route
            file=json_file,  # The uploaded file
            created_by=self.user
        )
        
        # Add the attachment to the route's attachments
        self.route.attachments.add(attachment)
                
        # update route
        self.route.status = Route.STATUS.COUNTER_IMPORTED
        self.route.import_file_id = attachment.id
        self.route.save()
                
        return count
