# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

from scerp.admin import BaseAdmin, Display
from scerp.admin_site import admin_site
from . import actions as a
from .models import Message, Tenant, TenantSetup, TenantLogo, UserProfile


# Register User, Group
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)


@admin.register(Message, site=admin_site) 
class MessageAdmin(BaseAdmin):
    list_display = ('name', 'modified_at', 'is_inactive')
    search_fields = ('name', 'text')    
    fieldsets = (
        (None, {
            'fields': ('name', 'text', 'is_inactive'),
            'classes': ('expand',),            
        }),
    )  


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
