'''
billing/calc.py
'''
from datetime import datetime
from decimal import Decimal
import json
import logging
import openpyxl
from openpyxl.styles import Font
from django.db import transaction

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum, Min, Max, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _

from accounting.models import Article, OutgoingOrder, OutgoingItem
from asset.models import Device
from core.models import Area, AddressMunicipal, PersonAddress, Attachment
from scerp.admin import ExportExcel
from scerp.mixins import format_date, primary_language
from .models import (
    ARTICLE_NR_POSTFIX_DAY, Period, Route, Measurement, Subscription
)

logger = logging.getLogger(__name__)


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
def calculate_growth(consumption_now, consumption_previous):
    """
    Calculates the percentage growth between two consumption values.
    Returns None if the previous consumption is zero (to avoid division by zero).
    """
    if consumption_previous == 0:
        return None  # Avoid division by zero
    return (
        (consumption_now - consumption_previous) / consumption_previous
    ) * 100


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


def get_element_by_index(elements, index):
    """
    Safely returns the element at the given index from the list.
    If the index is out of range, returns None.
    """
    return elements[index] if 0 <= index < len(elements) else None


def shift_encode(text, shift=3):
    return ''.join(chr((ord(c) + shift) % 126) for c in text)


def round_to_zero(value, digits):
    if value is None:
        return '-'        
    if digits == 0:
        return int(round(value, 0))                                
    if isinstance(value, Decimal):
        value = float(value)            
    return round(value, digits) 


class RouteManagement:
    '''
    base class to handle Route management
    '''
    def __init__(self, modeladmin, request, route):
        self.modeladmin = modeladmin
        self.request = request
        self.route = route
        self.tenant = route.tenant
        self.created_by = request.user
        
        # calc
        # start, end
        self.start = self.route.get_start()
        self.end = self.route.get_end()

    def get_last_measurement(self, counter):
        measurement = Measurement.objects.filter(
                tenant=self.tenant,
                counter=counter,
                period=self.route.period_previous
            ).order_by('datetime').last()
        return measurement

    def get_comparison_measurements(self, counter):
        period_ids = (
            [x.id for x in self.route.comparison_periods.order_by('-end')]
            if self.route.comparison_periods.exists()
            else [self.route.period_previous.id]
        )
        measurements = Measurement.objects.filter(
                tenant=self.tenant,
                counter=counter,
                period__id__in=period_ids
            ).order_by('-datetime')
        return measurements

    def make_response_json(self, data, filename):
        '''make json file
        input:
            - json data
            - output filename
        return: json file
        '''
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

    def make_response_excel(self, data_list, queryset, filename):
        '''make excel file
        input:
            - data_list (list of dict)
            - output filename
        return: json file
        '''
        # Init
        headers = tuple(data_list[0].keys())
        data = [tuple(data.values()) for data in data_list]

        # Make
        excel = ExportExcel(
            self.modeladmin, self.request, queryset, filename)
        response = excel.generate_response(
            headers=headers, data=data)

        return response


class RouteCounterExport(RouteManagement):
    '''
    use this class to
    - get_counter_data_json:
        create a json list that gets upload to GFT software

    responsible_user: Brunnenmeister
    key: decipher for JSON export
    '''
    def __init__(
            self, modeladmin, request, route, responsible_user=None, 
            route_date=None, energy_type='W', key=None):
        super().__init__(modeladmin, request, route)
        self.username = responsible_user.username if responsible_user else None
        self.name = f'{route.id}, {route.tenant.code}, {route.__str__()}'
        self.route_date = route_date
        self.energy_type = energy_type
        self.key = key  # encryption

    # Helpers
    def data_check(self, show_multiple=False):
        '''Check validity of addresses, counters
        show_multiple: show if a subscriber has multiple counters
        '''
        # Check addresses
        subs_without_address = Subscription.objects.filter(
            tenant=self.tenant,
            address=None,
            start__lte=self.end,
        ).filter(
            Q(end__gte=self.start) | Q(end__isnull=True)
        )
        if subs_without_address:
            messages.warning(
                self.request,
                _("Records having no address: %s") % subs_without_address
            )

        # Check counters
        subs_without_counters = Subscription.objects.annotate(
            counter_count=Count('counters')
        ).filter(
            tenant=self.tenant,
            counter_count=0,
            start__lte=self.end
        ).filter(
            Q(end__gte=self.start) | Q(end__isnull=True)
        )
        if subs_without_counters:
            messages.warning(
                self.request,
                _("Records having no counters: %s") % subs_without_counters
            )

        if show_multiple:
            subs_multiple_counters = Subscription.objects.annotate(
                counter_count=Count('counters')
            ).filter(
                tenant=self.tenant,
                counter_count__gte=1,
                start__lte=self.end
            ).filter(
                Q(end__gte=self.start) | Q(end__isnull=True)
            )
            if subs_without_counters:
                messages.warning(
                    self.request,
                    _("Records having multiple counters: %s") % (
                        subs_multiple_counters)
                )

    def get_addresses(self):
        # Filter Addresses
        if self.route.addresses.exists():
            addresses = self.route.addresses.all()
        else:
            queryset = AddressMunicipal.objects.filter(
                tenant=self.tenant)
            if self.route.areas.exists():
                queryset = queryset.filter(area__in=areas)
            addresses = queryset.all()

        return addresses

    def get_subscriptions(self, addresses):
        # In scope
        queryset = Subscription.objects.filter(
            tenant=self.tenant,
            address__in=addresses,
            start__lte=self.end,
        ).filter(
            Q(end__gte=self.start) | Q(end__isnull=True)
        )

        return queryset.all()

    def make_gft_meter(self, subscription, counter, excel):
        ''' make meter dict for json / excel export
        if excel we optimize data to our needs
        '''
        # last consumption
        last_measurement = self.get_last_measurement(counter)
        if last_measurement:
            value = last_measurement.value or 0
            consumption_previous = last_measurement.consumption or 0
        else:
            value = 0
            consumption_previous = 0

        # Calc min, max
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
            if self.route.period_previous:
                previous_date = convert_datetime_to_date(
                    self.route.period_previous.end)
            else:
                previous_date = None

            # encryption
            if self.key:
                name = shift_encode(name, self.key)
                nr = shift_encode(street, self.key)
                street = shift_encode(nr, self.key)

            meter = {
                'id': counter.number,
                'energytype': self.energy_type,
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
                    'obiscode': counter.category.code,
                    'dateOld': previous_date,
                    'old': round(value, 1),
                    'min': round(min, 1),
                    'max': round(max, 1),
                    'dateCur': current_date
                }
            }

        return meter

    # Methods, main
    def get_counter_data_json(self, excel=False, show_multiple=False):
        '''called to generate the json data for the export to GFT software
        excel: output to excel, creates a much simpler meter data
        show_multiple: show if a subscriber has multiple counters
        '''
        # Check validity of data
        self.data_check(show_multiple)

        # Update route
        data = dict(METER.TEMPLATE)
        data['billing_mde']['route'].update({
            'name': self.name,
            'user': self.username
        })

        # Get subscriptions
        addresses = self.get_addresses()
        subscriptions = self.get_subscriptions(addresses)
        number_of_counters = 0

        # Fill in meters
        for subscription in subscriptions:
            for counter in subscription.counters.all():
                # make meter
                meter = self.make_gft_meter(subscription, counter, excel)
                data['billing_mde']['meter'].append(meter)

                # add route to routes_out in Subscription
                subscription.routes_out.add(self.route)
                number_of_counters += 1

        # Update route
        self.route.number_of_addresses = len(addresses)
        self.route.number_of_subscriptions = len(subscriptions)
        self.route.number_of_counters = number_of_counters
        self.route.status = Route.STATUS.COUNTER_EXPORTED
        self.route.save()

        # return data, if excel only meter records
        return data['billing_mde']['meter'] if excel else data


class RouteCounterImport(RouteManagement):
    '''
    use this class to import GFT json list after tour is completed

    this generates for all meters in the json file a measurement,
    unique tenant, counter, route, datetime
    '''
    JSON_MAPPING = {
        # for billing
        'datetime': 'dateKey',  # reference data, e.g. "2025-03-31"
        'value': 'key',   # reference data, use this for billing (default)

        # latest, alternative billing, not used
        'datetime_latest': 'dateCur',
        'value_latest': 'cur',
        'current_battery_level': 'batteryLevel',
    }

    def __init__(self, modeladmin, request, route):
        super().__init__(modeladmin, request, route)

    def create_measurement(self, meter):
        # Get counter
        code = meter['id']
        counter = Device.objects.filter(
            tenant=self.tenant, code=code
        ).first()
        if not counter:
            messages.warning(
                self.request, _(f"counter {code} not found."))
            return None

        # Check data
        value = meter['value']
        if not value:
            messages.warning(
                self.request, _(f"counter {code} has no value."))
            return None

        # Check required keys
        if not all(k in value for k in ['key', 'dateKey', 'cur']):
            messages.warning(
                self.request, _(f"counter {code} has no measurement."))
            return None

        # References
        maintenance = json.loads(meter['hint'])

        # Check address
        address_id = maintenance['address_id']
        address = AddressMunicipal.objects.filter(
            tenant=self.tenant, id=address_id).first()
        if not address:
            messages.warning(
                self.request, _(f"Address {maintenance['address_id']} wrong."))
            return None

        # Check subscription
        subscription_id = maintenance['subscription_id']
        subscription = Subscription.objects.filter(
            tenant=self.tenant, id=subscription_id).first()
        if not subscription:
            messages.warning(
                self.request, _(f"Subscription {subscription_id} wrong."))
            return None

        # Check data
        reference_dt = convert_str_to_datetime(value['dateKey'])
        if not self.start <= reference_dt.date() <= self.end:
            messages.warning(
                self.request,
                _(f"{code}: {reference_dt.date()} not in "
                  f"{self.route.start} to {self.route.end}")
            )
            return None

        # Prepare Measurement data
        data = {
            field_name: value.get(key)
            for field_name, key in self.JSON_MAPPING.items()
        }

        # Convert dates
        for key in ['datetime', 'datetime_latest']:
            data[key] = convert_str_to_datetime(data[key])

        # Calc and update
        data.update({
            # Calc consumption
            'consumption': data['value'] - value['old'],
            'consumption_latest': data['value_latest'] - value['old'],

            # Efficiency analysis
            'address': address,
            'period': self.route.period,
            'subscription': subscription,

            # maintenance
            'created_by': self.created_by,
        })

        # Check if the record has been already imported
        # So it is not possible that same measurement is assigend to two
        # routes
        if Measurement.objects.filter(
                    tenant=self.tenant,
                    counter=counter,
                    datetime=data['datetime']
                ).exists():
            messages.warning(
                self.request, _(f"counter {meter['id']} already measured."))
            return None

        # Store data
        obj = Measurement.objects.create(
            tenant=self.tenant,
            route=self.route,
            counter=counter,
            **data
        )

        return obj

    def process(self, json_file):
        # Load file
        file_data = json_file.read().decode('utf-8')
        data = json.loads(file_data)

        # Check file
        try:
            measurements = data['billing_mde']['meter']
        except:
            raise ValueError(_("Not a valid file"))

        ''' next time
        # Assign route
        route_id = int(data['billing_mde']['route']['name'].split(',')[0])
        self.route = Route.objects.filter(
            tenant=self.tenant, id=route_id).frist()
        if not self.route:
            raise ValueError(_("No valid route id."))
        '''

        # start, end of route
        self.start = self.route.period.start
        self.end = self.route.period.end

        # get meter data
        count = 0
        for meter in measurements:
            measurement = self.create_measurement(meter)
            if measurement:
                count += 1

        # Create an Attachment instance
        attachment = Attachment.objects.create(
            tenant=self.tenant,  # Set the tenant
            content_object=self.route,  # Set the associated route
            file=json_file,  # Uploaded the file
            created_by=self.created_by
        )

        # Add the attachment to the route's attachments
        self.route.attachments.add(attachment)

        # update route
        self.route.status = Route.STATUS.COUNTER_IMPORTED
        self.route.import_file_id = attachment.id
        self.route.save()

        return count


class RouteCounterInvoicing(RouteManagement):
    '''use this to invoice route data
    
    is_enabled_sync: set true for drafts, set false for others
    '''
    def __init__(
            self, modeladmin, request, route, status, invoice_date,
            is_enabled_sync):
        super().__init__(modeladmin, request, route)
        self.status = status
        self.date = invoice_date
        self.is_enabled_sync = is_enabled_sync

    def get_quantity(
            self, measurement, article, rounding_digits, days=None):
        ''' quantity, not considered: individual from, to
        '''
        if article.unit.code == 'volume':
            return round(measurement.consumption_with_sign, rounding_digits)
        elif article.unit.code == 'day' and days:
            return days
        return 1

    def bill(self, measurement):
        ''' get called from actions '''
        # check day vs. period
        subscription = measurement.subscription
        unit_code = (
            'day' if (
                measurement.route.start
                or measurement.route.end
                or subscription.start > measurement.period.start
                or (subscription.end
                    and subscription.end < measurement.period.end)
            ) else 'period'
        )
        if unit_code == 'day':
            # start
            start = max(subscription.start or self.start, self.start)
            end = max(subscription.end or self.end, self.end)
            days = (end - start).days + 1
        else:
            days = None

        # description         
        setup = measurement.route.setup
        if subscription.description:
            description = ', ' + subscription.description
        else:
            description = ', ' + setup.description if setup.description else ''

        # billing base
        invoice = {
            'tenant': measurement.tenant,
            'category': setup.order_category,
            'contract': setup.order_contract,
            'description': measurement.route.__str__() + description,
            'responsible_person': setup.contact,
            'date': self.date,
            'status': self.status,
            'is_enabled_sync': self.is_enabled_sync,
            'sync_to_accounting': True,  # immediately sync with cashCtrl
            'created_by': self.created_by
        }

        # associate
        associate = (
            subscription.recipient if subscription.recipient
            else subscription.subscriber
        )
        invoice['associate'] = associate

        # address name
        name = ''
        if associate.title:
            name += primary_language(associate.title.name) + ' '
        if associate.last_name:
            name += f"{associate.first_name} {associate.last_name}"
        if associate.company:
            if name:
                name += ', '
            name += associate.company
        if subscription.partner:
            partner = subscription.partner
            name += '\n'
            if partner.title:
                name += primary_language(partner.title.name) + ' '
            name += f"{partner.first_name} {partner.last_name}"

        # add address
        type, address = associate.get_invoice_address()
        invoice['recipient_address'] = f"{name}\n{address}"

        # Get comparison consumption
        value_new = round_to_zero(measurement.value, setup.rounding_digits)
        value_old = '-'
        comparison = self.get_comparison_measurements(
            measurement.counter).last()
        if comparison and comparison.consumption:
            value_old = round_to_zero(comparison.value, setup.rounding_digits)
            consumption = round_to_zero(
                comparison.consumption, setup.rounding_digits)
        else:
            consumption = ''

        # building
        building = (
            f"{measurement.address.stn_label} {measurement.address.adr_number}"
        )   
        if measurement.address.notes:
            building_notes = ', ' + measurement.address.notes
        else:    
            building_notes = ''
          
        # header
        invoice['header'] = setup.header.format(
            building=building,
            building_notes=building_notes,
            description=description,
            start=format_date(self.start),
            end=format_date(self.end),
            consumption=consumption,
            counter_new=value_new,
            counter_old=value_old
        )

        # create as atomic so signals work correctly        
        invoice = OutgoingOrder.objects.create(**invoice)
        
        # add items
        for article in subscription.articles.order_by('nr'):
            if unit_code == 'day' and article.unit.code == 'period':
                # Replace article by daily
                article = Article.objects.filter(
                    tenant=article.tenant,
                    nr=article.nr + ARTICLE_NR_POSTFIX_DAY,
                ).first()

            item = OutgoingItem.objects.create(
                tenant=measurement.tenant,
                article=article,
                quantity=self.get_quantity(
                    measurement, article, setup.rounding_digits, days),
                order=invoice,
                created_by=self.created_by
            )
                
        # add bill        
        # subscription.invoices.add(invoice)

class MeasurementAnalyse:
    '''
    select measurements and analyse
    measurements is queryset from admin.py
    '''
    def __init__(self, modeladmin, measurements):
        self._model = modeladmin.model
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
        consumption = 0
        for measurement in self.queryset:
            if measurement.consumption:
                consumption += measurement.consumption_with_sign

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