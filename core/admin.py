# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

from scerp.admin import admin_site, BaseAdmin, display_photo as display_photo_h
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
    fieldsets = (
        (None, {
            'fields': ('user', 'photo'),
            'classes': ('expand',),            
        }),
    )  

    @admin.display(description=_('Groups'))
    def display_photo(self, obj):
        return display_photo_h(obj.photo)

    @admin.display(description=_('Groups'))
    def group_names(self, obj):
        return obj.get_group_names()


@admin.register(Tenant, site=admin_site) 
class TenantAdmin(BaseAdmin):
    list_display = ('name', 'code', 'is_trustee')
    search_fields = ('name', 'code')
    list_filter = ('is_trustee',)    
    read_only_fields = ('initial_user_password',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'is_trustee', 'initial_user_email',
                       'initial_user_first_name', 'initial_user_last_name'),
            'classes': ('expand',),            
        }),
    )        
    
    def save_model(self, request, obj, form, change):
        """
        Save the Tenant model and handle additional actions for new tenants.
        """
        created = obj._state.adding  # Check if this is a new object
                
        # Save the object (this triggers the post_save signal)
        super().save_model(request, obj, form, change)
        
        # Post-save actions for new tenants
        if created:
            # Display messages in the admin interface
            msg = _("TenantSetup instance initiated.")
            messages.success(request, msg)
            
            # Check if password
            queryset = Tenant.objects.filter(pk=obj.pk)
            initial_password = queryset.first().initial_user_password
            msg = _("Created user '{username}' with password '{password}'.")
            messages.success(request, msg.format(
                username=obj.initial_user_email,
                password=initial_password))
            
            # Clear the password field without triggering another save
            queryset.update(initial_user_password=None)


@admin.register(TenantSetup, site=admin_site) 
class TenantSetupAdmin(BaseAdmin):    
    has_tenant_field = True
    list_display = ('tenant', 'display_apps')
    search_fields = ('tenant',)
    fieldsets = (
        (None, {
            'fields': (
                'canton', 'category', 'formats', 
                'apps', 'groups', 'users'),
            'classes': ('expand',),            
        }),
    )    
    
    @admin.display(description=_('apps'))
    def display_apps(self, obj):
        return ', '.join([x.name for x in obj.apps.all()])


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
        return display_photo_h(obj.logo)    
