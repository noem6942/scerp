'''
billing/calc.py
'''
from datetime import datetime
import json
import logging
import openpyxl
from openpyxl.styles import Font

from django.contrib import messages
from django.db.models import Count, Sum, Min, Max, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _

from asset.models import Device
from core.models import Area, AddressMunicipal, PersonAddress, Attachment
from scerp.admin import ExportExcel
from .models import Period, Route, Measurement, Subscription

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


class RouteMeterExport:
    '''
    use this class to
    - get_counter_data_json:
        create a json list that gets upload to GFT software
    - get_invoice_data_json:
        create a json list that gets used for invoicing
    '''
    def __init__(
            self, modeladmin, request, queryset, route, responsible_user=None,
            route_date=None, energy_type='W', key=None):
        self.modeladmin = modeladmin
        self.request = request
        self.queryset = queryset
        self.name = f'{route.tenant.code}, {route.__str__()}'
        self.route = route
        self.tenant = route.tenant
        self.username = responsible_user.username if responsible_user else None
        self.route_date = route_date
        self.energy_type = energy_type

        # encryption
        self.key = key

    # Helpers
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

    def data_check(self, start, end, show_multiple=False):
        # Check addresses
        subs_without_address = Subscription.objects.filter(
            tenant=self.tenant,
            address=None,
            start__lte=end,
        ).filter(
            Q(end__gte=start) | Q(end__isnull=True)
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
            start__lte=end
        ).filter(
            Q(end__gte=start) | Q(end__isnull=True)
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
                start__lte=end
            ).filter(
                Q(end__gte=start) | Q(end__isnull=True)
            )
            if subs_without_counters:
                messages.warning(
                    self.request,
                    _("Records having multiple counters: %s") % (
                        subs_multiple_counters)
                )

    def get_subscriptions(self, addresses):
        # start, end
        start = self.route.get_start()
        end = self.route.get_end()

        # check
        self.data_check(start, end)

        # In scope
        queryset = Subscription.objects.filter(
            tenant=self.tenant,
            address__in=addresses,
            start__lte=end,
        ).filter(
            Q(end__gte=start) | Q(end__isnull=True)
        )

        return queryset.all()

    def get_consumption(self, counter):
        if self.route.period_previous:
            total = Measurement.objects.filter(
                tenant=self.tenant,
                counter=counter,
                period=self.route.period_previous
            ).aggregate(Sum('consumption'))
            return total['consumption__sum'] or 0
        else:
            return 0

    def get_last_measurement(self, counter):
        measurement = Measurement.objects.filter(
                tenant=self.tenant,
                counter=counter,
                period=self.route.period_previous
            ).order_by('datetime').last()
        return measurement

    def make_meter(self, subscription, counter, excel, start, end):
        ''' make meter dict for json / excel export
        if excel we optimize data to our needs
        '''
        # last consumption
        last_measurement = self.get_last_measurement(counter)
        value = last_measurement.value or 0 if measurement else 0
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

    def get_route_start(self):
        if self.route.start:
            return self.route.start
        return self.route.period.start

    def get_route_end(self):
        if self.route.end:
            return self.route.end
        return self.route.period.end

    # Methods, main
    def get_counter_data_json(self, excel=False):
        '''called to generate the json data for the export to GFT software
        '''
        # Update route
        data = dict(METER.TEMPLATE)
        data['billing_mde']['route'].update({
            'name': self.name,
            'user': self.username
        })

        # Start, end
        start = self.get_route_start()
        end = self.get_route_end()

        # Get subscriptions
        addresses = self.get_addresses()
        subscriptions = self.get_subscriptions(addresses)
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

    def get_invoice_data_json(
            self, reference_mode=True, incl_title=False,
            title_line_break=False, max_history=4, max_articles=4):
        # Init
        invoices = []
        start = self.get_route_start()
        end = self.get_route_end()

        # Get subscriptions, use same as meter export
        addresses = self.get_addresses()
        subscriptions = self.get_subscriptions(addresses)
        number_of_counters = 0
        comparison_periods = self.route.get_comparison_periods()

        # Work through every subscription in scope
        for index, subscription in enumerate(subscriptions, start=1):
            # Get invoice address
            address_type, invoice_address = (
                subscription.subscriber.get_invoice_address())

            # Get latest measurements
            measurement = Measurement.objects.filter(
                tenant=self.tenant,
                subscription=subscription,
                route=self.route
            ).order_by('-datetime').first()

            data = {
                # general
                'id': index,
                'reference_mode': reference_mode,

                # period
                'period_start': self.route.period.start,
                'period_end': self.route.period.end,

                # subscription
                'subscription_nr': subscription.number,
                'abo_nr': subscription.subscriber_number,
                'subscription_address': (
                    f"{subscription.address.stn_label} "
                    f"{subscription.address.adr_number} "
                ),

                # subscriber person
                'subscriber': subscription.subscriber.display_name(
                    self.tenant.language, incl_title, title_line_break),

                # subscriber partner
                'partner': subscription.partner.display_name(
                    self.tenant.language, incl_title, title_line_break
                ) if subscription.partner else None,

                # invoice address
                'type': str(address_type.label),
                'address': invoice_address,

                # consumption
                'value': (
                    measurement.value if reference_mode
                    else measurement.value_latest
                ) if measurement else None,
                'consumption': (
                    measurement.consumption if reference_mode
                    else measurement.consumption_latest
                ) if measurement else None,
            }

            # Prepare history report
            queryset_history = Measurement.objects.filter(
                tenant=self.tenant,
                subscription=subscription,
                route__period__in=comparison_periods
            ).order_by('-datetime')

            # filter unique, only take latest measurement per period
            history = {}
            if data['value']:
                value_last = data['value']
                consumption_last = data['consumption']
                for hist in queryset_history.all():
                    period = hist.route.period                    
                    if hist.consumption:
                        growth = calculate_growth(
                            consumption_last, hist.consumption)
                        sign = '+' if growth > 0 else ''                            
                        growth_str = f" ({sign}{round(growth)})"
                    else:
                        growth_str = ''
                        
                    # Report

                    history[period] = (
                        f"Vergleich Vorperiode:\n"                        
                        f"Verbrauch: {hist.consumption}\n"
                        f"Entwicklung: {growth_str}%)"
                    )

                    # adjust
                    consumption_last = hist.consumption

                # Make report
                for index in range(max_history):
                    key = f"history_{index + 1}"
                    data[key] = get_element_by_index(
                        list(history.values()), index)

            # Prepare articles
            articles = [
                f"{article.nr} {article.name[self.tenant.language]}"
                for article in subscription.articles.order_by('nr')]
            for index in range(max_articles):
                key = f"article_{index + 1}"
                data[key] = get_element_by_index(articles, index)

            invoices.append(data)

        return invoices

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

    def make_response_excel(self, data_list, filename):
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
    '''use this class to import GFT json list after tour is completed
    '''
    def __init__(self, request, route):
        self.route = route
        self.tenant = route.tenant
        self.request = request
        self.user = request.user

    def process(self, json_file):
        # Load file
        file_data = json_file.read().decode('utf-8')
        data = json.loads(file_data)
        start = self.route.period.start
        end = self.route.period.end

        # Check file
        try:
            measurements = data['billing_mde']['meter']
        except:
            raise ValueError(_("Not a valid file"))

        # get meter data
        count = 0
        for meter in measurements:
            # Get counter
            code = meter['id']
            counter = Device.objects.filter(
                tenant=self.tenant, code=code
            ).first()
            if not counter:
                messages.warning(
                    self.request, _(f"counter {code} not found."))
                continue

            # Check data
            value = meter['value']
            if not value:
                messages.warning(
                    self.request, _(f"counter {code} has no value."))
                continue

            # Check required keys
            if not all(k in value for k in ['key', 'dateKey', 'cur']):
                messages.warning(
                    self.request, _(f"counter {code} has no measurement."))
                continue

            # References
            maintenance = json.loads(meter['hint'])

            # Check address
            address_id = maintenance['address_id']
            address = AddressMunicipal.objects.filter(
                tenant=self.tenant, id=address_id).first()
            if not address:
                messages.warning(
                    self.request, _(f"Address {maintenance['address_id']} wrong."))
                continue

            # Check subscription
            subscription_id = maintenance['subscription_id'] + 496  # temp !!!
            subscription = Subscription.objects.filter(
                tenant=self.tenant, id=subscription_id).first()
            if not subscription:
                messages.warning(
                    self.request, _(f"Subscription {subscription_id} wrong."))
                continue

            # Check data
            reference_dt = convert_str_to_datetime(value['dateKey'])
            if not start <= reference_dt.date() <= end:
                messages.warning(
                    self.request,
                    _(f"{code}: {reference_dt.date()} not in "
                      f"{self.route.start} to {self.route.end}")
                )
                continue

            # Prepare Measurement data
            data = {
                # previous
                'datetime_previous': convert_str_to_datetime(value['dateOld']),
                'value_previous': value['old'],
                'value_max': value['max'],
                'value_min': value['min'],

                # measurement data used for bill
                'datetime': reference_dt,
                'value': value['key'],
                'consumption': value['key'] - value['old'],

                # latest data
                'datetime':  convert_str_to_datetime(value['dateCur']),
                'value':  value['cur'],
                'consumption_latest':  value['cur'] - value['old'],
                'current_battery_level': value['batteryLevel'],

                # efficiency analysis
                'address': address,
                'period': self.route.period,
                'subscription': subscription,
                'consumption_previous': maintenance['consumption_previous'],

                # maintenance
                'created_by': self.user,
            }

            # Store data
            obj, created = Measurement.objects.get_or_create(
                tenant=self.tenant,
                route=self.route,
                counter=counter,
                datetime=data.pop('datetime'),
                defaults=data)
            if created:
                count += 1
            else:
                messages.warning(
                    self.request, _(f"counter {meter['id']} already measured."))

        # Create an Attachment instance
        attachment = Attachment.objects.create(
            tenant=self.tenant,  # Set the tenant
            content_object=self.route,  # Set the associated route
            file=json_file,  # Uploaded the file
            created_by=self.user
        )

        # Add the attachment to the route's attachments
        self.route.attachments.add(attachment)

        # update route
        self.route.status = Route.STATUS.COUNTER_IMPORTED
        self.route.import_file_id = attachment.id
        self.route.save()

        return count
