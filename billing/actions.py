'''billing/actions.py
'''
from django.contrib import admin, messages
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django_admin_action_forms import action_with_form

from scerp.actions import action_check_nr_selected
from scerp.mixins import read_excel
from . import forms
from .calc import convert_str_to_datetime

from asset.models import Device
from core.models import Attachment
from .calc import (
    RouteCounterExport, RouteCounterImport, RouteCounterInvoicing,
    Measurement, MeasurementAnalyse
)
from .models import Route, Subscription, Measurement


ENCRYPTION_KEY = 3


@action_with_form(
    forms.RouteMeterExportJSONActionForm,
    description='1. ' + _('Export JSON Counter List for Routing'))
def export_counter_data_json(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Prepare
        route = queryset.first()
        if not route.period_previous:
            return

        key = 3 if data['key_enabled'] else None
        filename = data['filename']

        # Make and download json
        export = RouteCounterExport(
            modeladmin, request, route, data['responsible_user'].user,
            data['route_date'], data['energy_type'], key)
        data = export.get_counter_data_json()
        response = export.make_response_json(data, filename)

        return response


@action_with_form(
    forms.RouteMeterImportJSONActionForm,
    description='2. ' + _('Import JSON Counter List from Routing'))
def import_counter_data_json(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Prepare
        route = queryset.first()

        # Import
        route_import = RouteCounterImport(modeladmin, request, route)
        count = route_import.process(data['json_file'])

        messages.info(request, _("%s counters updated.") % count)
        messages.info(request, _("File uploaded and stored as attachment."))


def get_invoice_data(modeladmin, request, queryset, data=None):
    if action_check_nr_selected(request, queryset, 1):
        pass
        ''' old
        # Prepare
        route = queryset.first()

        # Import
        invoicing = RouteCounterInvoicing(modeladmin, queryset, request, route)
        invoices = invoicing.get_invoice_data_json()

        # Make excel
        data_list = invoices
        filename = f"preview_invoices_{route.name}.xlsx"
        response = invoicing.make_response_excel(
            data_list, filename)
        return response
        '''


@action_with_form(
    forms.RouteBillingForm,
    description='4. ' + _('Route Billing'))
def route_billing(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Prepare variables
        route = queryset.first()
        is_enabled_sync = data.get('is_enabled_sync', False)

        # Data select
        tag = data['tag']
        if tag:
            measurements = Measurement.objects.filter(
                route=route, subscription__tag=tag)
        else:
            measurements = data['measurements']
            if not measurements:
                measurements = Measurement.objects.filter(route=route)

        # Process
        invoice = RouteCounterInvoicing(
            modeladmin, request, route, data['status'], data['date'],
            is_enabled_sync)
        for measurement in measurements:
            invoice.bill(measurement)

        # output
        count = len(measurements)
        messages.info(
            request, _("{count} bills created").format(count=count))


@action_with_form(
    forms.RouteMeterExportExcelActionForm,
    description=_('Export internal Excel Counter List for Routing'))
def export_counter_data_excel(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        messages.warning(request, _("Not implemented yet."))
        """
        # Prepare
        route = queryset.first()
        key = ENCRYPTION_KEY if data['key_enabled'] else None
        filename = data['filename']

        # Make and download excel
        export = RouteMeterExport(
            modeladmin, request, queryset, route, key=key)
        data = export.get_data(excel=True)
        if not data:
            messages.warning(request, _("No data for this route"))
            return
        response = export.make_response_excel(data, filename)

        return response
        """


@action_with_form(
    forms.RouteCopyActionForm,
    description=_('Copy Route'))
def route_copy(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Copy
        route = queryset.first()
        route.pk = None  # Copy
        route.name = data['name']
        route.period_previous = route.period
        route.period = data['period']
        route.status = Route.STATUS.INITIALIZED
        route.number_of_addresses = None
        route.number_of_subscriptions = None
        route.number_of_counters = None
        route.save()

        # Copy many-to-many relationships explicitly
        # route.areas.add(*route.areas.all())
        # route.addresses.add(*route.addresses.all())


@admin.action(description=_("Consumption Analysis"))
def analyse_measurement(modeladmin, request, queryset):
    if action_check_nr_selected(request, queryset, min_count=1):
        template = 'billing/measurement_consumption.html'

        a = MeasurementAnalyse(modeladmin, queryset)
        data = a.analyse()

        try:
            # Pass data directly, no need to format lists here
            context = {
                "data": data,
                "record_count": queryset.count(),
                "consumption_change_percentage": (
                    round(data["consumption_change"] * 100, 1
                ) if data["consumption_change"] else None)
            }

            # Render template
            success_message = render_to_string(template, context)

            # Display as a message
            modeladmin.message_user(
                request, mark_safe(success_message), messages.SUCCESS)

        except Exception as e:
            messages.error(request, str(e), messages.ERROR)
        except:
            messages.error(request, _('No valid data available'))


@action_with_form(
    forms.AnalyseMeasurentExcelActionForm,
    description=_('Export Analysis to Excel'))
def anaylse_measurent_excel(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare
        a = MeasurementAnalyse(modeladmin, queryset)
        filename = data['filename']
        ws_title = data['ws_title']
        data = a.analyse()
        print("*data", data)
        data['record_count'] = queryset.count()

        # Make and download excel
        response = a.output_excel(data, filename, ws_title)

        return response


@admin.action(description=_("Assign Measurement Archive"))
def assign_measurement_archive(modeladmin, request, queryset):
    if action_check_nr_selected(request, queryset, count=1):
        # Init
        col_counter_id = 'Zähler-Nr.'
        col_value = 'Wert'
        col_obis_code = 'Obis'

        # Get archive
        archive = queryset.first()
        attachments = Attachment.get_attachments_for_instance(archive)

        # Load File
        try:
            filename = attachments.first().file.path
        except:
            messages.error(request, "No files or two many files attached.")

        # Process File
        data_list = read_excel(
            filename, header_nr=1, string_cols=[col_counter_id])
        count, counter_nok, measurement_nok = len(data_list), 0, 0

        for data in data_list:
            counter_id = data[col_counter_id]
            value = data[col_value]
            obis_code = data[col_obis_code]
            
            device = Device.objects.filter(
                tenant=archive.tenant,
                code=counter_id
            ).first()
            if device value:
                if value and not Measurement.objects.filter(
                        counter=device).exists():
                    measurement_nok += 1
                    messages.warning(
                        request, f"{counter_id}: {value} - value not existing [{obis_code}]")
                        
                    # create Measurement
                    measurement = dict(
                        tenant=archive.tenant,
                        counter=device,
                        route=archive.route,
                        period=archive.route.period,
                        datetime=convert_str_to_datetime(data['showDate2']),
                        value=data['Wert'],
                        datetime_latest=convert_str_to_datetime(
                            data.get('dtLast2')),
                        value_latest=data.get('lastValue'),
                        notes=(
                            f"abo-nr: {data['i.customerNo']}\n"
                            f"name: {data['Kundenname']}\n"                            
                            f"{data['Adresse']}\n"
                        ),
                        created_by=archive.created_by
                    )
                    obj = Measurement.objects.create(**measurement)
            else:
                # counter and measurement not existing
                counter_nok += 1
                messages.warning(
                    request,
                    f"{counter_id}: {value} - counter and measurement not existing [{obis_code}]")

        messages.info(request, (
            f"Result: {count} counters: "
            f"{counter_nok} missing counters, "
            f"{measurement_nok} missing measurements.")
        )
