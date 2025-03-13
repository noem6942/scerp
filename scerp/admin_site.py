"""
scerp/admin_site.py

Overwrite Site to check for tenant select and Site menus

"""
import re

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import AdminSite
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import get_language, gettext_lazy as _

from core.safeguards import get_tenant_data, get_available_tenants, set_tenant
from core.models import Message, Tenant, TenantSetup
from .locales import APP_CONFIG, APP_MODEL_ORDER


class Site(AdminSite):
    """
    Customized AdminSite; get's called with every Model in admin.py
    """
    # Titles
    site_header = APP_CONFIG['site_header']  # Default site header
    site_title = APP_CONFIG['site_title']  # Default site title
    index_title = APP_CONFIG['index_title']  # Default index title
    
    # Side Menu
    current_app = None  # assign from path
    app_setup = {}  # assign in _get_ordered_app_list

    # Order and seperators
    DEFAULT_ORDER = '\u00A0'  # Non-visible space character for late-order apps
    SEPARATOR_APP = '. '
    SEPARATOR_MODEL = '. '    

    # Handle requests
    def index(self, request, extra_context=None):
        ''' this gets called with every page view 
        '''        
        # Handle tenant selection
        if request.method == 'POST':
            # Handle the form submission when a tenant is selected
            tenant_id = int(request.POST.get('tenant'))
            if tenant_id:
                try:
                    # Set request.session
                    _tenant = set_tenant(request, tenant_id)
                    # Redirect to admin page after selection                    
                    return redirect(request.path)  # Reload the same page
                except Tenant.DoesNotExist:
                    return HttpResponseForbidden(
                        _("Tenant not found or access denied."))
            else:
                return HttpResponseForbidden(_("No tenant selected."))            
            
        # Handle GET request: Get the current tenant and available tenants
        tenant_data = get_tenant_data(request)  # get_tenant
        available_tenants = get_available_tenants(request)
        
        # Pass available tenants and selected tenant ID to the template
        extra_context = extra_context or {}
        extra_context.update({
            'available_tenants': available_tenants,
            'tenant': tenant_data
        })
        
        # Render the regular admin index page
        return super().index(request, extra_context=extra_context)

    # Build menus
    def get_app_list(self, request, app_label=None):
        '''Build the side menu left (the app list)'''

        # Extract app_label from the URL
        pattern = rf'/{settings.ADMIN_ROOT}/([^/]+)/'
        match = re.search(pattern, request.path)
        self.current_app = match.group(1) if match else None

        # Get the default app list from the superclass
        app_list = super().get_app_list(request)

        if app_label is None:
            # Process the general admin index page
            if 'login' in request.path:
                pass  # don't show on login screen
            elif not request.session.get('tenant_message_shown', False):
                # Get messages
                queryset = Message.objects.filter(
                    is_inactive=False).order_by('-modified_at')

                # Display messages
                for message in queryset:
                    call = (
                        messages.warning
                        if message.severity == Message.Severity.WARNING
                        else messages.info
                    )
                    call(request, message.text)

                # Set session variables
                request.session['tenant_message_shown'] = True  # Mark message as shown
            return self._get_ordered_app_list(app_list, request)

        # Else render a specific app's models
        return self._get_app_detail_list(app_list, app_label)

    def _get_ordered_app_list(self, app_list, request):
        '''Generate an ordered list of all apps.'''
        ordered_app_list = []
        tenant = get_tenant_data(request)
        
        # Builds App Setup
        app_setup = dict(APP_MODEL_ORDER)
        if self.current_app and self.current_app in app_setup:
            current_app = {self.current_app: app_setup.pop(self.current_app)}
        else:
            current_app = {}            
        self.app_setup = {**current_app, **app_setup}

        # Make Menu
        for app_label, app_info in self.app_setup.items():
            if not app_info.get('needs_tenant', True) or tenant:
                app = self._find_app(app_list, app_label)
                if app:
                    self._process_app(app, app_info)
                    ordered_app_list.append(app)

        # Append remaining apps
        remaining_apps = [
            app for app in app_list
            if (
                app['app_label'] not in self.app_setup
                and (not app_info.get('needs_tenant', True) or tenant)
            )
        ]
        ordered_app_list.extend(remaining_apps)    
        
        return ordered_app_list

    def _get_app_detail_list(self, app_list, app_label):
        '''Generate a detailed list of models for a specific app.'''
        app_info = self.app_setup.get(app_label)
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
        '''
        app['models'] = sorted(
            app['models'],
            key=lambda model: (
                model_order_dict.get(
                    model['object_name'], (self.DEFAULT_ORDER, None))[0],
                model_order_dict.get(
                    model['object_name'], (self.DEFAULT_ORDER, None))[1]
            )
        )
        '''
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
