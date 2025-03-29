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
from .calc import RouteMeterExport, RouteMeterImport, MeasurementAnalyse
from .models import Route, Subscription


ENCRYPTION_KEY = 3


@action_with_form(
    forms.RouteMeterExportJSONActionForm,
    description=_('Export external JSON Counter List for Routing'))
def export_counter_data_json(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Prepare
        route = queryset.first()
        if not route.previous_period:
            return

        key = 3 if data['key_enabled'] else None
        filename = data['filename']

        # Make and download json
        export = RouteMeterExport(
            modeladmin, request, queryset, route,
            data['responsible_user'].user, data['route_date'], key)
        data = export.get_data()
        response = export.make_response_json(data, filename)

        return response


@action_with_form(
    forms.RouteMeterImportJSONActionForm,
    description=_('Import JSON Counter List from Routing'))
def import_counter_data_json(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Prepare
        route = queryset.first()

        # Import
        route_import = RouteMeterImport(request, route)
        count = route_import.process(data['json_file'])
        
        messages.info(request, _("{count} counters updated."))
        messages.info(request, _("File uploaded and stored as attachment."))


@action_with_form(
    forms.RouteMeterExportExcelActionForm,
    description=_('Export internal Excel Counter List for Routing'))
def export_counter_data_excel(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Prepare
        route = queryset.first()
        key = ENCRYPTION_KEY if data['key_enabled'] else None
        filename = data['filename']

        # Make and download json
        export = RouteMeterExport(
            modeladmin, request, queryset, route, key=key)
        data = export.get_data(excel=True)
        if not data:
            messages.warning(request, _("No data for this route"))
            return
        response = export.make_response_excel(data, filename)

        return response



@action_with_form(
    forms.RouteCopyActionForm,
    description=_('Copy Route'))
def route_copy(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        # Copy
        route = queryset.first()
        route.pk = None  # Copy
        route.name = data['name']
        route.previous_period = route.period
        route.period = data['period']
        route.status = Route.STATUS.INITIALIZED
        route.save()

        # Copy many-to-many relationships explicitly
        # route.areas.add(*route.areas.all())
        # route.addresses.add(*route.addresses.all())


@admin.action(description=_("Consumption Analysis"))
def analyse_measurment(modeladmin, request, queryset):
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
    forms.AnaylseMeasurentExcelActionForm,
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
