from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _

from scerp.admin import BaseAdmin, BaseTabularInline
from scerp.admin_site import admin_site
from .models import (
    STATUS, Department, DeviceLocation, Customer, Category, Model, Device, 
    EventLog, CounterCategory, CounterUnit, CounterLog
)


@admin.register(Department, site=admin_site)
class DepartmentAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'description'),
            'classes': ('expand',),
        }),
    )


@admin.register(DeviceLocation, site=admin_site)
class DeviceLocationAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'description'),
            'classes': ('expand',),
        }),
    )


@admin.register(Customer, site=admin_site)
class CustomerAdmin(BaseAdmin):
    has_tenant_field = True
    related_tenant_fields = ['department']
    list_display = ('last_name', 'first_name', 'department')
    search_fields = ('last_name', 'first_name', 'location__name')
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'department'),
            'classes': ('expand',),
        }),
    )


@admin.register(Category, site=admin_site)
class CategoryAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    fieldsets = (
        (None, {
            'fields': ('name', 'code'),
            'classes': ('expand',),
        }),
    )


@admin.register(Model, site=admin_site)
class ModelAdmin(BaseAdmin):
    related_tenant_fields = ['category']    
    has_tenant_field = True
    list_display = ('name', 'category', 'description')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': (
                'name', 'category', 'description', 'purchace_price', 
                'warranty_years',
                'label_1', 'label_2', 'label_3', 'label_4'
            ),
            'classes': ('expand',),
        }),
    )

    def save_model(self, request, obj, form, change):
        print(f"Saving EventLog: {obj}")
        super().save_model(request, obj, form, change)


class EventLogInline(BaseTabularInline):
    related_tenant_fields = ['location', 'customer']
    has_tenant_field = True
    model = EventLog
    extra = 0
    fields = ('date', 'customer', 'location', 'device', 'status')


@admin.register(Device, site=admin_site)
class DeviceAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = (
        'serial_number', 'responsible', 'model', 'tag',
        'status', 'location', 'customer'
    )
    search_fields = ('serial_number', 'tag', 'status', 'location__name')
    list_filter = ('status', 'location')
    readonly_fields = ('location', 'customer')
    fieldsets = (
        (None, {
            'fields': (
                'serial_number', 'model', 'status', 'responsible', 'tag', 
                'location', 'customer')
        }),
    )
    inlines = [EventLogInline]
    
    def save_model(self, request, instance, form, change):
        instance.status = STATUS.RECEIVED
        super().save_model(request, instance, form, change)
        
    def save_related(self, request, form, formsets, change):                
        super().save_related(request, form, formsets, change)
        
        # Update status
        id = form.instance.id
        last_event = EventLog.objects.filter(
            device__id=id).order_by('-date', '-modified_at').first()        
        if last_event:
            Device.objects.filter(id=id).update(
                location=last_event.location,
                customer=last_event.customer,
                status=last_event.status)


@admin.register(CounterCategory, site=admin_site)
class CounterCategoryAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'code')
    search_fields = ('name', 'code', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description'),
            'classes': ('expand',),
        }),
    )
    
@admin.register(CounterUnit, site=admin_site)
class CounterUnitAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('name', 'code')
    search_fields = ('name', 'code', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description'),
            'classes': ('expand',),
        }),
    )
    


@admin.register(CounterLog, site=admin_site)
class CounterLogAdmin(BaseAdmin):
    has_tenant_field = True
    list_display = ('category', 'device', 'measured_at')
    search_fields = ('category', 'device__model__name')
    fieldsets = (
        (None, {
            'fields': (
                'category', 'value', 'device', 'measured_at',
                'label_1', 'label_2', 'label_3', 'label_4'
            ),
            'classes': ('expand',),
        }),
    )
