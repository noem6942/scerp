'''time_app/actions.py
'''
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from scerp.admin import action_check_nr_selected
from .connector_clockify import Clock, ClockConnector


@admin.action(description=_('Admin: Load timesheets'))
def load_time_entries(modeladmin, request, queryset):
    '''ensure later that this can only be accessed by a trustee / admin
    '''
    # Check
    if action_check_nr_selected(request, queryset, 1):
        instance = queryset.first()        
        c = ClockConnector(instance, request.user)
        count, warnings = c.load_timesheets()
        for warning in warnings:
            messages.warning(request, warning)          
        messages.info(request, f"{count} time entries created.")  
