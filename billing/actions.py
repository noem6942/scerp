'''billing/actions.py
'''
from django.contrib import admin, messages
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django_admin_action_forms import action_with_form

from scerp.actions import action_check_nr_selected
from scerp.admin import Excel
from . import forms

from asset.models import Device
from .calc import RouteCalc, AnalyseMeasurement
from .models import Subscription


@action_with_form(
    forms.PeriodExportActionForm,
    description=_('Export Counter List for Routing'))
def export_counter_data(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, 1):
        route = queryset.first()
        employee = data['employee']
        key = 3 if data['key_enabled'] else None

        r = RouteCalc(route, employee.user, key)
        r.export()

        route.status = modeladmin.model.STATUS.COUNTER_EXPORTED
        route.save()


@admin.action(description=_('Consumption Analysis'))
def analyse_measurment(modeladmin, request, queryset):
    if action_check_nr_selected(request, queryset, min_count=1):
        try:
            a = AnalyseMeasurement(modeladmin.model, queryset)
            data = a.analyse()

            periods = ', '.join([
                str(period)
                for period in data['periods']
            ])

            routes = ', '.join([
                str(route)
                for route in data['routes']
            ])

            areas = ', '.join([
                str(area)
                for area in data['areas']
            ])
            consumption_previous = (
                round(data['consumption_previous'])
                if data['consumption_previous'] else None)
            consumption_change = (
                round(data['consumption_change'] * 100, 1)
                if data['consumption_change'] else None)

            # Prepare HTML for display
            table_html = f"""
                <table>
                    <thead>
                        <tr>
                            <th><b>{_('Label')}</b></th>
                            <th><b>{_('Value')}</b></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{_('Periods')}:</td>
                            <td>{periods}</td>
                        </tr>
                        <tr>
                            <td>{_('Routes')}:</td>
                            <td>{routes}</td>
                        </tr>
                        <tr>
                            <td>{_('Period Start, End')}:</td>
                            <td>{data['start']} - {data['end']}</td>
                        </tr>
                        <tr>
                            <td>{_('Areas')}:</td>
                            <td>{areas}</td>
                        </tr>
                        <tr>
                            <td>{_('Value dates from - to')}:</td>
                            <td>{data['min_date']} - {data['max_date']}</td>
                        </tr>
                        <tr>
                            <td>{_('Total consumption')}:</td>
                            <td>{round(data['consumption'])} m³</td>
                        </tr>
                        <tr>
                            <td>{_('    previous')}:</td>
                            <td>{consumption_previous}</td>
                        </tr>
                        <tr>
                            <td>{_('    change in %')}:</td>
                            <td>{consumption_change}</td>
                        </tr>
                    </tbody>
                </table>
                """

            # Use mark_safe to render the HTML
            success_message = mark_safe(
                f"<strong>Consumption Analysis</strong><br>"
                f"<i>{queryset.count()} {_('records processed')}.</i><br><br>"
                f"{table_html}"
            )
            modeladmin.message_user(request, success_message, messages.SUCCESS)

        except:
            messages.error(request, _('No valid data available'))


@admin.action(description=_('Export data'))
def export_measurement_data(modeladmin, request, queryset):
    if action_check_nr_selected(request, queryset, min_count=1):
        e = Excel()
        data = [
            (x.id, x.consumption)
            for x in queryset.all()
        ]
        response = e.generate_response(data)
        return response
