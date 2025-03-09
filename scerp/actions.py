'''
scerp/actions.py

General actions used by all apps
'''
import json

from django.contrib import admin
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from .admin import ExportExcel, ExportJSON
from .forms import ExportExcelActionForm, ExportJSONActionForm


# Helpers
def action_check_nr_selected(request, queryset, count=None, min_count=None):
    """
    This checks that a user selects the appropriate number of items in admin.py
    """
    if count is not None:
        if queryset.count() != count:
            msg = _('Please select excatly {count} record(s).').format(
                    count=count)
            messages.warning(request, msg)
            return False
    elif min_count is not None:
        if queryset.count() < min_count:
            msg =  _('Please select more than {count - 1} record(s).').format(
                    count=min_count)
            messages.warning(request, msg)
            return False

    return True


# Export
@action_with_form(ExportExcelActionForm, description=_('Export data to Excel'))
def export_excel(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare formats        
        model = modeladmin.model        
        file_name = data['file_name']
        ws_title = data['worksheet_name']
        orientation = data['orientation']
        
        header = {
            key.split('_')[1]: value 
            for key, value in data.items() 
            if 'header' in key
        }        
        footer = {
            key.split('_')[1]: value 
            for key, value in data.items() 
            if 'footer' in key
        }
        if data['col_widths']:
            try:
                col_widths = list(data['col_widths'])
            except:
                raise ValueError(_("No valid col widths"))
        else:
            col_widths = None
        
        # Prepare data
        data = modeladmin.export_data(request, queryset)      
        headers = (
            modeladmin.export_headers(request, queryset) 
            if getattr(modeladmin, 'export_headers', None) else []
        )
        
        # Create excel
        excel = ExportExcel(file_name, ws_title, header, footer, orientation)
        response = excel.generate_response(data, headers, col_widths)
        
        return response


@action_with_form(ExportJSONActionForm, description=_('Export data to JSON'))
def export_json(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare formats          
        file_name = data['file_name']
        
        # Prepare data
        data = modeladmin.export_data(request, queryset)  
        headers = (
            modeladmin.export_headers(request, queryset) 
            if getattr(modeladmin, 'export_headers', None) else []
        )
        
        # Create json
        excel = ExportJSON(file_name)
        response = excel.generate_response(data, headers)
        
        return response


# Default row actions, general
@admin.action(description=_('Set inactive'))
def set_inactive(modeladmin, request, queryset):
    queryset.update(is_inactive=True)
    msg = _("Set {count} records as inactive.").format(count=queryset.count())
    messages.success(request, msg)


@admin.action(description=_('Set protected'))
def set_protected(modeladmin, request, queryset):
    queryset.update(is_protected=True)
    msg = _("Set {count} records as protected.").format(count=queryset.count())
    messages.success(request, msg)
