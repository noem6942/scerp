'''billing/actions.py
'''
from django.contrib import admin, messages
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django_admin_action_forms import action_with_form

from scerp.actions import action_check_nr_selected
from . import forms

from asset.models import Device
from .calc import (
    RouteCounterExport, RouteCounterImport, RouteCounterInvoicing,
    MeasurementAnalyse
)
from .models import Route, Subscription


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
        route = queryset.first()
        is_enabled_sync = data.get('is_enabled_sync', False)
        invoice = RouteCounterInvoicing(
            modeladmin, request, route, data['status'], data['date'],
            is_enabled_sync)
        for measurement in data['measurements']:
            invoice.bill(measurement)

        # output
        count = len(data['measurements'])
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
            modeladmin.message_user(
                request, _("Error: ") + str(e), messages.ERROR)

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
