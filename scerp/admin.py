from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import AdminSite, ModelAdmin
from django.db import models
from django.forms import Textarea
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

import json

from .locales import APP
from core.safeguards import (
    get_available_tenants, set_tenant, filter_query_for_tenant, save_logging)


GUI_ROOT = settings.ADMIN_ROOT
SPACE = '\u00a0'  # invisible space

# helpers
LOGGING_FIELDS = [
    'created_at', 'created_by', 'modified_at', 'modified_by']
NOTES_FIELDS = [
    'notes', 'attachment', 'protected', 'is_inactive']
TENANT_FIELD = 'tenant'

TEXTAREA_DEFAULT = {
    'rows': 1,
    'cols': 80,
}


# Helpers
def get_help_text(model, field_name):
    return model._meta.get_field(field_name).help_text


def verbose_name_field(model, field_name):
    return model._meta.get_field(field_name).verbose_name


def display_datetime(value, default='-'):
    if value is None:
        return default
    else:
        return date_format(value, format='DATETIME_FORMAT')


def display_empty(value=None, default=' '):
    if value is None or value == '':
        return default
    else:
        return str(value)


def display_big_number(value):
    if value is None:
        return display_empty()
    else:
        number_str = "{:,.2f}".format(value).replace(
            ',', settings.THOUSAND_SEPARATOR)
        html = '<span style="text-align: right; display: block;">{}</span>'
        return format_html(html, number_str)


def display_json(value):
    try:
        # Sort keys
        data = {
            key: value[key]
            for key in sorted(value.keys())
        }

        # Format JSON data with indentation and render it as preformatted text
        formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
        return formatted_json

    except Exception as e:
        return f"Error displaying data: {e}"


def format_hierarchy(level, name):
    '''Function to print out hierarchy names nice;
        add spaces before the string if is_category == False
    '''
    if level == 1:
        return format_html(f"<b>{name.upper()}</b>")
    elif level == 2:
        return format_html(f"<b>{name}</b>")
    else:
        return format_html(f"<i>{name}</i>")


def display_photo(url_field):
    if url_field:
        return mark_safe(f'<img src="{url_field.url}" width="60" height="60" style="object-fit: cover;" />')
    return ''


def display_verbose_name(def_cls, field):
    f_cls = getattr(def_cls, 'Field')
    return getattr(f_cls, field)['verbose_name']


# Widgets
def override_textfields_default(attrs=TEXTAREA_DEFAULT):
    return {
        models.TextField: {'widget': Textarea(attrs=attrs)}
    }


class Site(AdminSite):
    site_header = APP.verbose_name  # Default site header
    site_title = APP.title  # Default site title
    index_title = APP.welcome  # Default index title

    DEFAULT_ORDER = '\u00A0'  # Non-visible space character for late-order apps
    SEPARATOR_APP = '. '
    SEPARATOR_MODEL = '.'

    def get_app_list(self, request, app_label=None):
        '''Build the side menu left (the app list)'''

        # Get the default app list from the superclass
        app_list = super().get_app_list(request)

        if app_label is None:
            # Process the general admin index page
            return self._get_ordered_app_list(app_list)
        else:
            # Render a specific app's models
            return self._get_app_detail_list(app_list, app_label)

    def _get_ordered_app_list(self, app_list):
        '''Generate an ordered list of all apps.'''
        ordered_app_list = []

        for app_label, app_info in APP.APP_MODEL_ORDER.items():
            app = self._find_app(app_list, app_label)
            if app:
                self._process_app(app, app_info)
                ordered_app_list.append(app)

        # Append remaining apps
        remaining_apps = [
            app for app in app_list
            if app['app_label'] not in APP.APP_MODEL_ORDER
        ]
        ordered_app_list.extend(remaining_apps)

        return ordered_app_list

    def _get_app_detail_list(self, app_list, app_label):
        '''Generate a detailed list of models for a specific app.'''
        app_info = APP.APP_MODEL_ORDER.get(app_label)
        if not app_info:
            return []

        app = self._find_app(app_list, app_label)
        if app:
            self._process_app(app, app_info)
            return [app]

        return []

    def _find_app(self, app_list, app_label):
        '''Find an app in the app list by its label.'''
        return next(
            (app for app in app_list if app['app_label'] == app_label), None
        )

    def _process_app(self, app, app_info):
        '''Process the app and its models.'''
        symbol = app_info.get('symbol', self.DEFAULT_ORDER)
        app_config = apps.get_app_config(app['app_label'])
        verbose_name = app_config.verbose_name
        app['name'] = f"{symbol}{self.SEPARATOR_APP}{verbose_name}"

        model_order_dict = app_info.get('models', {})
        app['models'] = sorted(
            app['models'],
            key=lambda model: (
                model_order_dict.get(
                    model['object_name'], (self.DEFAULT_ORDER, None))[0],
                model_order_dict.get(
                    model['object_name'], (self.DEFAULT_ORDER, None))[1]
            )
        )

        for model in app['models']:
            order, postfix = model_order_dict.get(
                model['object_name'], (self.DEFAULT_ORDER, None)
            )
            postfix = postfix or ''
            name = f"{order} {model['name']}".strip()
            model['name'] = (
                f"{symbol}{self.SEPARATOR_MODEL}{name}{postfix}")



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
            (_('Notes and Status'), {
                'fields': note_fields,
                'classes': ('collapse',),
            }),
            (_('Logging'), {
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

    def changelist_view(self, request, extra_context=None):
        """
        Show warning for a model if specified
        """
        if getattr(self, 'warning', ''):
            messages.warning(request, mark_safe(self.warning))
        if getattr(self, 'info', ''):
            messages.info(request, mark_safe(self.info))
        if getattr(self, 'error', ''):
            messages.error(request, mark_safe(self.error))
        return super().changelist_view(request, extra_context=extra_context)

    # security
    def get_queryset(self, request):
        """
        Limit queryset based on user or other criteria.
        """
        # add security
        queryset = super().get_queryset(request)
        if getattr(self, 'has_tenant_field', False):
            # Filter queryset
            try:
                queryset = filter_query_for_tenant(request, queryset)
            except Exception as e:
                # If an error occurs, capture the exception and return an error message
                msg = _("Error filtering tenant: {e}").format(e=e)
                messages.error(request, msg)

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
