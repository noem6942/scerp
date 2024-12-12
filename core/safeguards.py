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
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import Tenant, TenantSetup, UserProfile


# Security mixins
def filter_query_for_tenant(request, query, recheck_from_db=False):
    # get tenant
    if recheck_from_db:
        tenant = set_tenant(request)
    else:
        tenant = get_tenant(request)
        
    # filter query
    if tenant['id']:
        return query.filter(tenant__id=tenant['id']) 
    else:
        return query.none()
    

def set_tenant(request, tenant_setup_id=None):
    '''set tenant data on request.session
        use tenant_setup_id if user has access to more than one tenant
    '''
    # Get available tenants    
    queries = get_available_tenants(request)
    if tenant_setup_id:
        queries = queries.filter(id=tenant_setup_id)
        
    # Check for failure    
    if not queries:
        raise ValidationError(_('No appropriate tenant assigned'))
    elif queries.count() > 1:
        raise ValidationError(_('User has multiple tenants'))
    else:
        # Set first
        tenant_setup = queries.first()
        
        # Save
        request.session['tenant'] = {        
            'id': tenant_setup.tenant.id,
            'setup_id': tenant_setup.id,
            'name': tenant_setup.tenant.name,
            'language': tenant_setup.language,
            'logo': (
                tenant_setup.logo.url if tenant_setup.logo else settings.LOGO)
        }
        
        # promote
        request.session.modified = True  # Ensure the session is saved immediately
        return request.session['tenant']


def set_year(request, year):
    tenant = get_tenant(request)
    if tenant:
        request.session['tenant']['year'] = year


def get_available_tenants(request):
    # Check if the user is a superuser with global access to all tenants
    if request.user.is_superuser and getattr(
            settings, 'ADMIN_ACCESS_ALL', False):
        return TenantSetup.objects.order_by('tenant__name')

    try:
        return TenantSetup.objects.filter(users__user=request.user).order_by(
            'tenant__name')            
    except ObjectDoesNotExist:
        return False  # Or handle this case accordingly


def get_tenant(request):
    '''get tenant data from request.session        
    '''
    tenant = request.session.get('tenant')
    if tenant:
        return tenant
    else:
        # try to get one, raises errors
        return set_tenant(request)
    

def save_logging(request, obj, add_tenant=False, recheck_from_db=False):
    # set created_by, modified_by
    if not obj.pk:  # New object, set the creator
        obj.created_by = request.user
    obj.modified_by = request.user  # Set the user who modified it
    
    if add_tenant and not getattr(obj, 'tenant', None):
        if recheck_from_db:
            set_tenant(request)
    
        tenant_data = get_tenant(request)
        obj.tenant = Tenant.objects.filter(id=tenant_data['id']).first()
        if not obj.tenant:
            return HttpResponseForbidden(
                _('No appropriate tenant assigned'), status=403)
