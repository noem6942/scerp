from django.conf import settings
from django.shortcuts import render, redirect


# Views ----------------------------------------------------------------------

def home(request):
    template = 'core/home.html'
    
    context = {'gui_root': settings.ADMIN_ROOT}
    return render(request, template, context=context)


def select_tenant(request):
    template = 'templates/select_tenant.html'

    if request.user.is_authenticated and request.user.is_trustee:
        # Get the list of tenants the trustee has access to
        user_profile = request.user.profile
        available_tenants = user_profile.additional_tenants.all()

        if request.method == 'POST':
            # Get the selected tenant from the form
            selected_tenant_id = request.POST.get('tenant')
            
            try:
                selected_tenant = Tenant.objects.get(id=selected_tenant_id)
                
                # Set the selected tenant in the session
                request.session['tenant_id'] = selected_tenant.id

                # Redirect to the desired page after selection
                return redirect('/admin/')
            except Tenant.DoesNotExist:
                return HttpResponseForbidden(
                    "Tenant not found or access denied.")
        
        return render(request, self.template, {'tenants': available_tenants})

    return HttpResponseForbidden(
        "You do not have permission to select tenants.")
