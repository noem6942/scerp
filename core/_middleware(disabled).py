# core.middleware.py
'''
    this is the central file for handling tenant management
    we use it as we don't want to solely trust on admin.py
    
    currently disabled
'''
from django.http import HttpResponseForbidden, Http404
from django.utils.translation import gettext_lazy as _

from .models import Tenant, TenantSetup, UserProfile
from .safeguards import get_tenant 
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
                return HttpResponseForbidden(
                    _("User profile not found. Contact Admin."))
                    
            # Check if tenant set        
            _ = get_tenant(request)
            
        else:
            return HttpResponseForbidden("User is not authenticated.")

        # Continue processing the request
        return self.get_response(request)
