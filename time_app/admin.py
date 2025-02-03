from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportActionMixin

from scerp.admin import BaseAdmin, Display
from scerp.admin_site import admin_site
from . import actions as a
from . import resources
from .models import Workspace, ClockifyUser, Tag, Client, Project, TimeEntry


@admin.register(Workspace, site=admin_site)
class WorkspaceAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name',)    
    actions = [a.load_time_entries]
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'name', 'mandatory_hours', 'api_key', 'c_id', 'tenant'),
            'classes': ('expand',),
        }),    
    )
 

@admin.register(ClockifyUser, site=admin_site)
class ClockifyUserAdmin(BaseAdmin):
    has_tenant_field = False
    list_display = ('user', 'c_id')        
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'user', 'c_id'),
            'classes': ('expand',),
        }),    
    )


@admin.register(Tag, site=admin_site)
class TagAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name',)    
    readonly_fields = ('c_id',)
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'name', 'workspace', 'c_id'),
            'classes': ('expand',),
        }),    
    )


@admin.register(Client, site=admin_site)
class ClientAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name',)    
    readonly_fields = ('c_id',)
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'name', 'workspace', 'c_id'),
            'classes': ('expand',),
        }),    
    )



@admin.register(Project, site=admin_site)
class ProjectAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name',)    
    # readonly_fields = ('c_id',)
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'workspace', 'name', 'billable', 'hourly_rate', 'currency',
                'tags', 'color', 'client', 'c_id'),
            'classes': ('expand',),
        }),
        (_('Accounting'), {
            'fields': ('type', 'project_code', 'position'),
            'classes': ('expand',),
        })        
    )


@admin.register(TimeEntry, site=admin_site)
class TimeEntryAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = resources.TimeEntryResource  # Attach the resource class
    
    has_tenant_field = True
    list_display = (
        'clockify_user', 'project', 'start_time', 'end_time', 
        'display_hours', 'total_hours')    
    readonly_fields = ('c_id',)
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'clockify_user', 'project', 'start_time', 'end_time', 
                'description', 'tags', 'c_id'),
            'classes': ('expand',),
        }),    
    )
  
    @admin.display(description=_('start'))
    def display_start_time(self, obj):
        return obj.start_time.strftime("%Y-%m-%d")
  
    @admin.display(description=_('end'))
    def display_end_time(self, obj):
        return obj.end_time.strftime("%Y-%m-%d")
  
    @admin.display(description=_('hours'))
    def display_hours(self, obj):
        return Display.big_number(obj.duration_in_hours, round_digits=2)  
  
    @admin.display(description=_('day hours'))
    def total_hours(self, obj):  
        if obj.is_latest_entry_of_day:
            # Extract the date part of start_time (ignoring the time portion)
            start_date = obj.start_time.date()  # Assuming start_time is a DateTimeField
            hours = TimeEntry.total_hours_for_user_on_day(
                obj.clockify_user, start_date)
            return Display.big_number(hours, round_digits=2)             
