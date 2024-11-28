# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

from scerp.admin import admin_site, BaseAdmin
from .models import Tenant, TenantSetup, TenantLocation, UserProfile


# Register User, Group
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)


@admin.register(UserProfile, site=admin_site) 
class UserProfileAdmin(BaseAdmin):
    list_display = ('user', 'display_photo')  # Add the display_photo method
    search_fields = ('user__username',)    
    fieldsets = (
        (None, {
            'fields': ('user', 'photo'),
            'classes': ('expand',),            
        }),
    )  


@admin.register(Tenant, site=admin_site) 
class TenantAdmin(BaseAdmin):
    list_display = ('name', 'code', 'is_trustee',)
    search_fields = ('name', 'code')
    list_filter = ('is_trustee',)    
    readonly_fields = ('is_trustee',)
    fieldsets = (
        (None, {
            'fields': ('name', 'code'),
            'classes': ('expand',),            
        }),
    )    
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        msg = _("TenantSetup instance initiated.")        
        messages.success(request, msg)


@admin.register(TenantSetup, site=admin_site) 
class TenantSetupAdmin(BaseAdmin):    
    has_tenant_field = True
    list_display = ('tenant', 'display_logo',)
    search_fields = ('tenant',)
    fieldsets = (
        (None, {
            'fields': ('canton', 'category', 'formats', 'logo', 'users'),
            'classes': ('expand',),            
        }),
    )    


@admin.register(TenantLocation, site=admin_site) 
class TenantLocationAdmin(BaseAdmin):    
    has_tenant_field = True
    list_display = ('org_name', 'type',)
    search_fields = ('org_name', 'type',)
    fieldsets = (
        (None, {
            'fields': ('org_name', 'type', 'address', 'zip', 'city', 'country'),
            'classes': ('expand',),            
        }),
        (_('Layout'), {
            'fields': ('logo', 'logoFileId', 'footer'),
            'classes': ('expand',),            
        }),
    )    
