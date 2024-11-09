# core.middleware.py
'''
    this is the central file for handling tenant management

'''
from django.http import HttpResponseForbidden, Http404

from .models import Tenant, TenantSetup, UserProfile
from .safeguards import get_tenant_id_from_session   
from scerp.urls import GUI_ROOT


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):        
        # Allow access to certain public resources
        if (
            request.path == f'/{GUI_ROOT}/' or
            request.path.startswith(f'/{GUI_ROOT}/login/') or
            request.path.startswith(f'/{GUI_ROOT}/logout/') or
            request.path.startswith(f'/{GUI_ROOT}/password_reset/') or
            request.path == '/favicon.ico' or
            request.path == '/'
        ):
            return self.get_response(request)  # Allow public access

        # Check admin access
        # Save tenant
        try:
            request.tenant = get_tenant_id_from_session(request)
            request.tenant_name = tenant.name
            tenant_setup = TenantSetup.objects.filter(
                tenant=tenant).first()
            request.logo = tenant_setup.logo.url
        except:
            request.tenant, request.tenant_name = None, None

        return self.get_response(request) 

        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Check if the user is a superuser
            if request.user.is_superuser:
                return self.get_response(request)  # Superuser has full access
            
            # Get profile
            try:
                # Attempt to get the user's profile
                user_profile = request.user.profile
            except UserProfile.DoesNotExist:
                return HttpResponseForbidden("User profile not found. Contact Admin.")

            # Set the default tenant to the user's primary tenant
            request.tenant_id = user_profile.primary_tenant.id

            # Check tenant_selected
            tenant_selected_id = request.GET.get('tenant_selected_id')  # Use request.GET to get query parameters
            if tenant_selected_id:
                # Validate that the selected tenant is one of the user's additional tenants
                if not user_profile.additional_tenants.filter(id=tenant_selected_id).exists():                    
                    return HttpResponseForbidden("You do not have access to this tenant.")
                else:
                    # If tenant is valid, set the tenant_id
                    request.tenant_id = tenant_selected_id  # Update the tenant_id to the selected one

        else:
            return HttpResponseForbidden("User is not authenticated.")

        # Continue processing the request
        return self.get_response(request)
