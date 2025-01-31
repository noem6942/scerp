# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant, filter_query_for_tenant
from scerp.admin import BaseAdmin, Display
from scerp.admin_site import admin_site
from . import actions as a
from .models import Message, Tenant, TenantSetup, TenantLogo, UserProfile
from .safeguards import get_available_tenants, set_tenant


# Register User, Group
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)


@admin.register(Message, site=admin_site) 
class MessageAdmin(BaseAdmin):
    ''' currently only a superuser function '''
    list_display = (
        'name', 'severity', 'modified_at', 'show_recipients', 'is_inactive')
    search_fields = ('name', 'text')    
    fieldsets = (
        (None, {
            'fields': (
                'name', 'text', 'recipients', 'severity', 'is_inactive'),
            'classes': ('expand',),            
        }),
    )  

    @admin.display(description=_('Photo'))
    def show_recipients(self, obj):        
        return ", ".join([tenant.name for tenant in obj.recipients.all()])
            

@admin.register(UserProfile, site=admin_site) 
class UserProfileAdmin(BaseAdmin):
    list_display = ('user', 'display_photo', 'group_names')
    search_fields = ('user__username',)   
    readonly_fields = ('user', 'group_names')
    fieldsets = (
        (None, {
            'fields': ('user', 'photo', 'group_names'),
            'classes': ('expand',),            
        }),
    )  

    @admin.display(description=_('Photo'))
    def display_photo(self, obj):
        return Display.photo(obj.photo)

    @admin.display(description=_('Groups'))
    def group_names(self, obj):
        return Display.list([x.name for x in obj.groups])
        

@admin.register(Tenant, site=admin_site) 
class TenantAdmin(BaseAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'is_app_time_trustee'),
            'classes': ('expand',),            
        }),
    )        

    def save_model(self, request, obj, form, change):
        """
        Override save_model to perform session update
        """
        # Save the object first
        super().save_model(request, obj, form, change)
        
        # Perform your post-save action
        if not change:  # If this is a new object being created
            # Set session variables
            get_available_tenants(request, recheck_from_db=True)
            set_tenant(request, obj.id)
            messages.success(request, _("Session updated."))


@admin.register(TenantSetup, site=admin_site)
class TenantSetupAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = (
        'tenant', 'display_users', 'group_names', 'display_apps', 'created_at')
    search_fields = ('tenant',)
    readonly_fields = ('display_users', )
    actions = [a.tenant_setup_create_user]

    # Define which fields are in the form
    fieldsets = (
        (None, {
            'fields': ('canton', 'type', 'display_users'),  # Including the display method here is okay for readonly display
            'classes': ('expand',),            
        }),
    )

    @admin.display(description=_('Apps'))
    def display_apps(self, obj):
        return Display.list(
            sorted([x.verbose_name for x in obj.tenant.apps.all()]))

    @admin.display(description=_('Users'))
    def display_users(self, obj):
        # Custom method to display users as a read-only field in the admin
        users = [x.username for x in obj.users.all()]
        return Display.list(users)

    @admin.display(description=_('Groups'))
    def group_names(self, obj):
        return Display.list(sorted([x.name for x in obj.groups]))


@admin.register(TenantLogo, site=admin_site) 
class TenantLogoAdmin(BaseAdmin):    
    has_tenant_field = True
    list_display = ('tenant', 'name', 'type', 'display_logo')
    search_fields = ('tenant', 'name')
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'logo'),
            'classes': ('expand',),            
        }),
    )
    
    @admin.display(description=_('logo'))
    def display_logo(self, obj):
        return Display.photo_h(obj.logo)    
