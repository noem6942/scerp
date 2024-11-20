from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import AdminSite, ModelAdmin
from django.db import models
from django.forms import Textarea
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .locales import APP
from core.models import Tenant, TenantSetup, UserProfile
from core.safeguards import (
    get_available_tenants, set_tenant, filter_query_for_tenant, save_logging)


GUI_ROOT = settings.ADMIN_ROOT

# helpers
LOGGING_FIELDS = [
    'created_at', 'created_by', 'modified_at', 'modified_by']
NOTES_FIELDS = [
    'notes', 'attachment', 'protected', 'inactive']
TENANT_FIELD = 'tenant'

TEXTAREA_DEFAULT = {
    'rows': 1,
    'cols': 80,
}


def display_datetime(value, default='-'):
    if value is None:
        return default
    else:
        return date_format(value, format='DATETIME_FORMAT')


def display_empty(value, default=''):
    if value is None:
        return default
    else:
        return str(value)
    
    
def display_verbose_name(def_cls, field):
    f_cls = getattr(def_cls, 'Field')
    return getattr(f_cls, field)['verbose_name']


def override_textfields_default(attrs=TEXTAREA_DEFAULT):
    return {
        models.TextField: {'widget': Textarea(attrs=attrs)}
    }


# Layout Home
class AppConfig:
    app_cls = None


class App(object):
  
    def __init__(self, app_cls):
        id = app_cls.id  # Fetch the application's ID
        name = app_cls.name  # Fetch the application's name
        
        verbose_name = app_cls.verbose_name  # Fetch the default verbose name
        if app_cls.show_app_id:  # Check if the app ID should be shown
            verbose_name = f"{id}{app_cls.app_separatur}{verbose_name}"  # Modify the verbose name
        
        # Set the modified verbose name in the application config
        apps.get_app_config(name).verbose_name = verbose_name  
        
        # store props
        AppConfig.app_cls = app_cls


class Site(AdminSite):
    site_header = APP.verbose_name  # Default site header
    site_title = APP.title  # Default site title
    index_title = APP.welcome  # Default index title

    def get_app_list(self, request):
        """
        Override get_app_list to add a numeric prefix to each model's verbose name
        for displaying in the sidebar.
        """
        app_list = super().get_app_list(request)  # Call the original method

        for app in app_list:
            # Create a mapping from order_models for fast index retrieval
            order_index_map = {
                model_name: index 
                for index, model_name in enumerate(APP.order_models)}

            # Prepare a list to hold ordered and not ordered models
            ordered_models = []
            not_ordered_models = []

            for model in app['models']:
                model_name = model['object_name']

                # Check if the model is in the order list and categorize 
                # accordingly
                if model_name in order_index_map:
                    # Store index and model
                    ordered_models.append((order_index_map[model_name], model))
                else:
                    # Store models not in order_models
                    not_ordered_models.append(model)  

            # Sort ordered models by their indices
            ordered_models.sort(key=lambda x: x[0])  # Sort by index

            # Apply prefix to ordered models
            for index, (_, model) in enumerate(ordered_models):
                if AppConfig.app_cls.show_model_id:
                    # Add zero-padding for order
                    model['name'] = f"{index + 1:02d} {model['name']}"

            # Combine the ordered models with the not ordered ones
            app['models'] = (
                [model for _, model in ordered_models] + not_ordered_models)

        return app_list

    def index(self, request, extra_context=None):
        # Get all tenants associated with the user
        # We use the TenantSetup object for all tenant information!!
        # We don't allow a user to continue without selecting a tenant
        available_tenants = get_available_tenants(request)

        # Process
        if available_tenants.count() == 1:
            # no choice, save and go to the organization
            set_tenant(request, available_tenants.first().id)
            
        elif request.method == "POST" and "tenant_setup" in request.POST:
            # a new selection has been posted, handle it
            tenant_setup_id = int(request.POST.get("tenant_setup"))
            #try:                        
            set_tenant(request, tenant_setup_id)
            #    return redirect(request.path_info)  # Redirects to the same page
            #except:
            #    return HttpResponseForbidden(_("User has no access."))
            
        # Pass tenant list and selected tenant info to the template
        tenant = request.session.get('tenant')        
        setup_id = int(tenant['setup_id']) if tenant else 0
         
        extra_context = extra_context or {}
        extra_context.update({
            'available_tenants': available_tenants,
            'selected_tenant_setup_id': setup_id
        })
        return super().index(request, extra_context=extra_context)


# Initialize the custom admin site
admin_site = Site(name='admin_site')


# Customize classes
class BaseAdmin(ModelAdmin):
    """
    A base admin class that contains reusable functionality.
    """    
    # format    
    formfield_overrides = override_textfields_default()  # Set form field overrides here if needed
    list_display = ('',)  # Default fields to display in list view
    readonly_fields = []  # Fields that are read-only by default

    # list_display_links = None  # Removes the links from list display
    empty_value_display = '-empty-'  # Adjust this to a shorter string if needed
    
    def get_list_display(self, request):
        ''' Automatically append 'has_notes' and 'has_attachment' etc. to list_display '''
        # Get the original list_display from any child class
        list_display = super().get_list_display(request)
              
        return list_display 
    
    def get_fieldsets(self, request, obj=None):
        """Return all fields in a single fieldset, with optional additional sections."""
        # Check all fields
        fields = []
        if self.fieldsets:
            for label, dict_ in self.fieldsets: 
                fields += dict_['fields']
        
        # Check tenant
        if getattr(self, 'has_tenant_field', False) and 'tenant' in fields:
            messages.error(request, _('Tenant is not included') )
            return []
        
        # Custom fields
        note_fields = [x for x in NOTES_FIELDS if x not in fields]

        # Logging fields
        logging_fields = [x for x in LOGGING_FIELDS if x not in fields]
        if getattr(self, 'has_tenant_field', False):
            logging_fields.append(TENANT_FIELD)

        # Build used fields
        used_fields = list(self.list_display)
        if not hasattr(self, 'fieldsets') or not self.fieldsets:
            self.fieldsets = (
                (None, {
                    'fields': used_fields,
                    'classes': ('expand',),
                }),
            )

        # Create a base fieldset
        fieldsets = (
            list(self.fieldsets) if getattr(self, 'fieldsets', None) 
            else [])

        # If no fieldsets are defined, initialize with a default fieldset
        if not fieldsets:
            fieldsets = [
                (None, {
                    'fields': self.list_display,  # or other default fields
                    'classes': ('expand',),
                }),
            ]

        # Add additional sections like Notes and Logging
        return self.fieldsets + (
            ('Notes and Status', {
                'fields': note_fields,
                'classes': ('collapse',),
            }),
            ('Logging', {
                'fields': logging_fields,
                'classes': ('collapse',),
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        """
        Dynamically set read-only fields based on user or conditions.
        """
        # Readonly fields
        readonly_fields = list(self.readonly_fields)
        readonly_fields.extend(LOGGING_FIELDS)

        # Hide tenant        
        if getattr(self, 'has_tenant_field', False):
            readonly_fields.extend([TENANT_FIELD]) 
        return readonly_fields

    # security
    def get_queryset(self, request):
        """
        Limit queryset based on user or other criteria.
        """
        # add security        
        queryset = super().get_queryset(request)
        if getattr(self, 'has_tenant_field', False):
            # Filter queryset
            queryset = filter_query_for_tenant(request, queryset)     
            
            # Store the data in obj for later usage
            self.tenant = request.session.get('tenant', 'en')             
        
        return queryset
        
    def save_model(self, request, obj, form, change):
        """
        Override save to include additional logging or other custom logic.
        """
        # Proceed with logging
        add_tenant = getattr(self, 'has_tenant_field', False)
        queryset = save_logging(request, obj, add_tenant=add_tenant)

        # Handle forbidden response from logging
        if isinstance(queryset, HttpResponseForbidden):          
            messages.error(request, f"{queryset.content.decode()}")
            return  # Early return to prevent further processing

        # Only save the model if there are no errors
        super().save_model(request, obj, form, change)
