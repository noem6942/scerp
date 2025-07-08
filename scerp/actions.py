'''
scerp/actions.py

General actions used by all apps
'''
import json

from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from .admin import ExportExcel, ExportJSON
from .forms import ExportExcelActionForm, ExportJSONActionForm
from core.models import TenantSetup

# Helpers
def action_check_nr_selected(
        request, queryset, count=None, min_count=None, max_count=None):
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
            msg =  _('Please select more than {min_count} record(s).').format(
                    count=min_count)
            messages.warning(request, msg)
            return False
    elif max_count is not None:
        if queryset.count() > max_count:
            msg =  _('Please select not more than {max_count} record(s).').format(
                    count=min_count)
            messages.warning(request, msg)
            return False
            
    return True


# Export
@action_with_form(ExportExcelActionForm, description=_('Export Data to Excel'))
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
        
        # Create excel
        excel = ExportExcel(
            modeladmin, request, queryset, file_name, 
            ws_title, header, footer, orientation)
        response = excel.generate_response(col_widths)
        
        return response


@action_with_form(ExportJSONActionForm, description=_('Export Data to JSON'))
def export_json(modeladmin, request, queryset, data):
    if action_check_nr_selected(request, queryset, min_count=1):
        # Prepare formats          
        file_name = data['file_name']        
        
        # Create json
        json_ = ExportJSON(modeladmin, request, queryset, file_name)
        response = json_.generate_response()
        
        return response

    
# Default row actions, general
@admin.action(description='---')
def _seperator(modeladmin, request, queryset):
    pass
    

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


@admin.action(description=_('Unprotect'))
def set_unprotected(modeladmin, request, queryset):
    queryset.update(is_protected=False)
    msg = _("Set {count} records as not protected.").format(
        count=queryset.count())
    messages.success(request, msg)
        
default_actions = [_seperator, set_inactive, set_protected, set_unprotected]    


# GIS Maps
def get_zoom_from_instance(instance, default=15):
    tenant = getattr(instance, 'tenant', None)
    setup = TenantSetup.objects.filter(tenant=tenant).first()
    return setup.zoom if setup else default


def map_display_response(
        modeladmin, request, points, title, subtitle, 
        unit='', zoom=15):
    # calc centers        
    # Compute map center
    if points:
        center_lat = sum(p['lat'] for p in points) / len(points)
        center_lng = sum(p['lng'] for p in points) / len(points)
    else:
        center_lat, center_lng = 46.8011, 8.2266
        zoom = 5
        subtitle = _("No data to visualize")
        
    context = {
        **modeladmin.admin_site.each_context(request),
        'data': points,
        'center_lat': center_lat,
        'center_lng': center_lng,
        'zoom': zoom,
        'title': title,
        'subtitle': subtitle,
        'unit': unit
    }

    return TemplateResponse(request, 'admin/map_view.html', context)
