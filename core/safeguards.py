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
from django.utils.translation import gettext_lazy as _
from core.models import Tenant, TenantSetup, UserProfile


# Security mixins
def filter_query_for_tenant(request, query):
    tenant = get_tenant(request)

    # filter query
    try:
        x = tenant['id']
    except:
        raise ValidationError(f'No tenant id {tenant}')

    if tenant['id']:
        return query.filter(tenant__id=tenant['id'])
    else:
        return query.none()


def set_tenant(request, tenant_id):
    '''set tenant data on request.session
    '''
    # Recheck if allowed
    queryset = TenantSetup.objects.filter(tenant__id=tenant_id)
    if not request.user.is_superuser or not getattr(
            settings, 'ADMIN_ACCESS_ALL', False):
        queryset = queryset.filter(users=request.user)

    # Save
    if queryset:
        tenant_setup = queryset.first()
        request.session['tenant'] = {
            'id': tenant_id,
            'setup_id': tenant_setup.id,
            'name': tenant_setup.tenant.name,
            'language': tenant_setup.language,
            'logo': (
                tenant_setup.logo.url if tenant_setup.logo else settings.LOGO)
        }
        return tenant_setup.tenant
    else:
        raise PermissionDenied(_('User has no access to tenant'))


def set_year(request, year):
    tenant = get_tenant(request)
    if tenant:
        request.session['tenant']['year'] = year


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
        queryset = TenantSetup.objects.filter(
            users=request.user).order_by('tenant__name')
        available_tenants = [{
            'id': tenant.id,
            'name': tenant.name
        } for tenant in queryset]

    # Store available tenants
    request.session['available_tenants'] = available_tenants
    return available_tenants


def get_tenant(request):
    '''get tenant data from request.session
    '''
    return request.session.get('tenant')


def save_logging(
        instance, request=None, add_tenant=False, tenant=None, user=None):
    # set created_by, modified_by
    if instance.pk:
        # Set the user who modified it
        instance.modified_by = request.user or user
    else:
        # New object, set the creator
        instance.created_by = request.user or user

    if add_tenant:
        if not tenant:
            # get tenant
            tenant_data = get_tenant(request)
            tenant = Tenant.objects.filter(id=tenant_data['id']).first()
        if tenant:
            instance.tenant = tenant
        else:
            raise ValidationError(_('No appropriate tenant given'))
