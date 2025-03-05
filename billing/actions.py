'''billing/actions.py
'''
from django.contrib import admin, messages
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from scerp.actions import action_check_nr_selected
from . import forms

from asset.models import Device
from .calc import RouteCalc
from .models import Subscription


@action_with_form(
    forms.PeriodExportActionForm, description=_('Generate Counter Data'))
def export_counter_data(modeladmin, request, queryset, data):    
    if action_check_nr_selected(request, queryset, 1):
        route = queryset.first()
        employee = data['employee']
        key = 3 if data['key_enabled'] else None
                
        r = RouteCalc(route, employee.user, key)
        r.export()

        route.status = modeladmin.model.STATUS.COUNTER_EXPORTED
        route.save()
