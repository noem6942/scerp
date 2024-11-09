# core/safeguards.py
"""
Role model:
    * user must login into admin
    * standard users have only access to one tenant -> store in session
    * users with more than one tenant need to pick the tenant at login
        -> store in session
    * no user is allowed to do action in admin if no session stored
    * in the session we store:
        - name, code, id from tenant
        - id and logo from tenant_setup
"""
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden
from django.utils.translation import gettext_lazy as _
from core.models import Tenant, TenantSetup, UserProfile


# Security mixins
def get_available_tenant_setups(request):
    # Check if the user is a superuser with global access to all tenants
    if request.user.is_superuser and getattr(settings, 'ADMIN_ACCESS_ALL', False):
        return TenantSetup.objects.order_by('tenant__name')

    try:
        UserProfile.objects.get(user=request.user)
    except ObjectDoesNotExist:
        return False  # Or handle this case accordingly

    # Return TenantSetup available to the user
    return TenantSetup.objects.filter(users__user=request.user).order_by(
        'tenant__name')


def get_tenant_setup_from_db_and_store(request, tenant_setup_id=None):
    # Retrieve user profile
    try:
        UserProfile.objects.get(user=request.user)
    except ObjectDoesNotExist:
        return HttpResponseForbidden(_('User profile not found. Contact Admin.'))

    # Get the specific tenant setup
    tenant_setup = TenantSetup.objects.filter(
        users__user=request.user, id=tenant_setup_id)
    if tenant_setup.count() == 1:
        tenant_setup = tenant_setup.first()
        save_session_from_tenant_setup(request, tenant_setup)
        return tenant_setup
    elif tenant_setup.count() > 1:
        return HttpResponseForbidden(_('User has multiple tenants'), status=403)
    else:
        return HttpResponseForbidden(_('No appropriate tenant assigned'), status=403)


def get_tenant_from_session(request, recheck_from_db=False):
    '''Returns the tenant object from the session; reloads from DB if requested or missing.'''
    tenant_id = request.session.get('selected_tenant_id')
    if recheck_from_db or not tenant_id:
        tenant_setup = get_tenant_setup_from_db_and_store(request)
        if tenant_setup:
            return tenant_setup.tenant
    else:
        try:
            return Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return None

    return HttpResponseForbidden(_('User profile not found. Contact Admin.'))


def get_tenant_id_from_session(request, recheck_from_db=False):
    '''Returns tenant ID from session; reloads from DB if requested or missing.'''
    tenant_id = request.session.get('selected_tenant_id')
    if recheck_from_db or not tenant_id:
        tenant_setup = get_tenant_setup_from_db_and_store(request)
        try:
            tenant_id = tenant_setup.tenant.id
        except:
            return None

    return tenant_id


def filter_query_for_tenant(request, query, recheck_from_db=False):
    tenant_id = get_tenant_id_from_session(request, recheck_from_db=recheck_from_db)
    return query.filter(tenant__id=tenant_id) if tenant_id else query.none()


def save_logging(request, obj, add_tenant=False, recheck_from_db=False):
    if not obj.pk:  # New object, set the creator
        obj.created_by = request.user
    obj.modified_by = request.user  # Set the user who modified it
    
    if add_tenant and not getattr(obj, 'tenant', None):
        obj.tenant = get_tenant_from_session(
            request, recheck_from_db=recheck_from_db)
        if not obj.tenant:
            return HttpResponseForbidden(_('No appropriate tenant assigned'), status=403)


def save_session_from_tenant_setup(request, tenant_setup):
    '''Stores tenant and tenant setup details in the session.'''
    request.session['selected_tenant_setup_id'] = tenant_setup.id
    request.session['selected_tenant_id'] = tenant_setup.tenant.id
    request.session['selected_tenant_name'] = tenant_setup.tenant.name
    request.session['selected_tenant_logo'] = tenant_setup.logo.url if tenant_setup.logo else settings.LOGO

    request.session.modified = True  # Ensure the session is saved immediately
