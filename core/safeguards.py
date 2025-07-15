# core/safeguards.py
"""
Role model:
    * user must login into admin
    * standard users have only access to one tenant -> store in session
    * users with more than one tenant need to pick the tenant at login
        -> store in session
    * no user is allowed to do action in admin if no session stored

    request.session['tenant'] = {
        'id': tenant_id,
        'setup_id': tenant_setup.id,
        'name': tenant_setup.tenant.name,
        'language': tenant_setup.language,
        'logo': (
            tenant_setup.logo.url if tenant_setup.logo else settings.LOGO)
    }

    request.session['available_tenants'] = [{
        'id': tenant.id,
        'name': tenant.name
    } for tenant in queryset]

    # Store available tenants
    request.session['available_tenants'] = available_tenants

"""
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from core.models import Tenant, TenantSetup, TenantUser


# Security mixins
def get_available_tenants(request, recheck_from_db=False):
    # Check if the user is a superuser with global access to all tenants
    if not recheck_from_db:
        available_tenants = request.session.get('available_tenants')
        if available_tenants:
            return available_tenants

    # Get available tenants
    if request.user.is_superuser and getattr(
            settings, 'ADMIN_ACCESS_ALL', False):
        queryset = Tenant.objects.order_by('name')
        available_tenants = [{
            'id': tenant.id,
            'name': tenant.name
        } for tenant in queryset]
    else:
        queryset = TenantUser.objects.filter(
            user=request.user).order_by('tenant__name')
        available_tenants = [{
            'id': user.tenant.id,
            'name': user.tenant.name
        } for user in queryset]

    # Store available tenants    
    request.session['available_tenants'] = available_tenants
    return available_tenants


def get_tenant_data(request):
    '''
    get tenant data from request.session, use this in future
    '''
    return request.session.get('tenant')


def get_tenant(request):
    '''
    get Tenant instance from request.session, use this in future
    '''
    tenant_data = get_tenant_data(request)
    if tenant_data:
        tenant = get_object_or_404(Tenant, id=tenant_data['id'])
        return tenant
    return None


def save_logging(instance, request=None, user=None):
    # set created_by, modified_by
    if instance.pk:
        # Set the user who modified it
        instance.modified_by = user or request.user
    else:
        # New object, set the creator
        instance.created_by = user or request.user


def set_tenant(request, tenant_id):
    '''set tenant data on request.session
    '''
    # Recheck if allowed
    if request.user.is_superuser and getattr(
            settings, 'ADMIN_ACCESS_ALL', False):                
        tenant_setup = TenantSetup.objects.filter(tenant__id=tenant_id).first()
    else:        
        # Check if user belongs to the tenant (allowed to access)
        allowed = TenantUser.objects.filter(
            tenant__id=tenant_id,
            user=request.user
        ).exists()

        if not allowed:
            # User is NOT allowed — handle permission denied
            raise PermissionDenied("You do not have access to this tenant.")

        # If allowed, fetch TenantSetup safely
        tenant_setup = TenantSetup.objects.filter(tenant__id=tenant_id).first()

    # Save
    if tenant_setup:
        request.session['tenant'] = {
            'id': tenant_id,
            'setup_id': tenant_setup.id,
            'code': tenant_setup.tenant.code,
            'name': tenant_setup.tenant.name,
            'language': tenant_setup.language,
            'cash_ctrl_org_name': tenant_setup.tenant.cash_ctrl_org_name,
            'show_only_primary_language': (
                tenant_setup.show_only_primary_language),
            'logo': (
                tenant_setup.logo.url if tenant_setup.logo else settings.LOGO)
        }
        return tenant_setup.tenant
    else:
        raise PermissionDenied(_('User has no access to tenant'))
