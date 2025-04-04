"""
scerp/admin.py

Admin configuration for the scerp app.

This module contains the configuration for models and views that manage the admin interface.
"""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant_data, save_logging
from .exceptions import APIRequestError


class FIELDS:
    LOGGING = ('modified_at', 'modified_by', 'created_at', 'created_by')
    LOGGING_TENANT = LOGGING + ('tenant',)
    LOGGING_SETUP = LOGGING_TENANT  # + ('tenant__setup',)
    LOGGING_SAVE = ('tenant', 'created_by')
    NOTES = ('notes', 'is_protected', 'is_inactive')
    ICON_DISPLAY = (
        'display_is_protected', 'display_is_inactive', 'display_notes')
    LINK_ATTACHMENT = ('display_attachment_icon',)

    # accounting
    SUPER_USER_EDITABLE_FIELDS = (
        'message',
        'is_enabled_sync',
        'sync_to_accounting',
    )
    C_FIELDS = (
        'c_id',
        'c_created',
        'c_created_by',
        'c_last_updated',
        'c_last_updated_by',
        'last_received',
    )    
    C_DISPLAY = (
        'display_last_update', 'c_id', 'message', 'is_enabled_sync')
    C_DISPLAY_SHORT = ('c_id', 'is_enabled_sync')
    C_ALL = C_FIELDS + C_DISPLAY
    C_READ_ONLY = LOGGING_SETUP + C_FIELDS


class FIELDSET:
    NOTES_AND_STATUS = (
        _('Notes and Status'), {
            'fields': FIELDS.NOTES,
            'classes': ('collapse',),
        })
    LOGGING = (
        _('Logging'), {
            'fields': FIELDS.LOGGING,
            'classes': ('collapse',),
        })
    LOGGING_TENANT = (
        _('Logging'), {
            'fields': FIELDS.LOGGING_TENANT,
            'classes': ('collapse',),
        })
    LOGGING_SETUP = (
        _('Logging'), {
            'fields': FIELDS.LOGGING_SETUP,
            'classes': ('collapse',),
        })
    CASH_CTRL = (
        'cashCtrl', {
            'fields': FIELDS.C_FIELDS + FIELDS.SUPER_USER_EDITABLE_FIELDS,
            'classes': ('collapse',),
        })


# Helpers
def is_form_read_only(modeladmin):
    return getattr(modeladmin, 'read_only', False)

def is_change_view(request):
    return request.path.endswith('/change/')

def edit_is_set(request):
    return request.GET.get('edit') == 'true'


class TenantFilteringAdmin(admin.ModelAdmin):
    '''
    A base admin class that handles tenant filtering efficiently.
    '''
    protected_foreigns = []  # ForeignKey optimization fields
    protected_many_to_many = []  # ManyToMany optimization fields
    has_errors = False

    def get_tenant_id(self, request):
        '''
        Retrieve tenant_id once per request
        '''
        if not hasattr(request, '_cached_tenant_id'):
            tenant_data = get_tenant_data(request)  # Fetch tenant info
            request._cached_tenant_id = (
                tenant_data.get('id', None) if tenant_data else None)

        return request._cached_tenant_id        

    def get_queryset(self, request):
        '''
        Filter the queryset by tenant.
        '''
        queryset = super().get_queryset(request)

        if not self.model:
            return queryset  # No model associated

        fields = {
            field.name
            for field in self.model._meta.get_fields()
        }  # Fast lookup
        tenant_id = self.get_tenant_id(request)

        # Filtering by 'tenant' if the field exists
        if 'tenant' in fields and tenant_id:
            queryset = queryset.filter(tenant__id=tenant_id)

        # Optimize ForeignKey and ManyToMany fields
        if self.protected_foreigns:
            queryset = queryset.select_related(*self.protected_foreigns)
        if self.protected_many_to_many:
            queryset = queryset.prefetch_related(*self.protected_many_to_many)

        return queryset

    def get_readonly_fields(self, request, obj=None):
        if obj and getattr(obj, 'is_protected', False):
            return [field.name for field in obj._meta.fields]

        return super().get_readonly_fields(request, obj)

    def has_change_permission(self, request, obj=None):
        if is_form_read_only(self) or (
                is_change_view(request) and not edit_is_set(request)):
            return False  # Disable editing
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if is_form_read_only(self) or (
                is_change_view(request) and not edit_is_set(request)):
            return False  # Disable deleting
        return super().has_delete_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        '''
        Filter ForeignKey choices by tenant.
        '''
        if db_field.name in self.protected_foreigns:
            tenant_id = self.get_tenant_id(request)

            fields = {
                field.name for field in self.model._meta.get_fields()
            }  # Fast lookup

            if (db_field.name == 'tenant' and
                    'tenant' in fields and tenant_id):
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    id=tenant_id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        '''
        Filter and optimize ManyToMany choices by tenant.
        '''
        if db_field.name in self.protected_many_to_many:
            # Fetch cached tenant
            tenant_id = self.get_tenant_id(request)

            fields = {
                field.name
                for field in self.model._meta.get_fields()
            }  # Use a set for fast lookup

            # Prefer filtering by 'tenant' if available
            if (db_field.name == 'tenant' and 'tenant' in fields
                    and tenant_id):
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    id=tenant_id)

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    # messaging
    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and getattr(obj, 'is_protected', False):
            messages.warning(request, _('Record is protected.'))
        return super().change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['help_text'] = getattr(self, 'help_text', None)

        return super().changelist_view(request, extra_context=extra_context)

    def response_change(self, request, obj):
        if obj.is_protected or self.has_errors:
            return HttpResponseRedirect(request.path)  # No success message

        return super().response_change(request, obj)

    def response_delete(self, request, obj_display, obj_id):
        """
        Custom delete response: prevent deletion if the object is protected.
        does not get called
        """
        if self.has_errors:
            return HttpResponseRedirect(request.path)  # Stay on the page if there are errors

        return super().response_delete(request, obj_display, obj_id)

    # Delete, save, save_related
    def delete_model(self, request, obj):
        self.has_errors = True
        try:
            with transaction.atomic():  # Ensure atomic deletion
                obj.delete()
                self.has_errors =False
        except APIRequestError as e:
            raise ValidationError(f'Cannot delete: {e}')  # Prevents Django from proceeding

        except Exception as e:
            messages.error(request, f'Error deleting category: {e}')

    def delete_queryset(self, request, queryset):
        count = 0
        self.has_errors = True
        with transaction.atomic():  # Ensures each delete is independent
            for obj in queryset:
                try:
                    obj.delete()
                    count += 1
                    self.has_errors = False
                except Exception as e:
                    messages.warning(request, f'{obj}: {str(e)}')

        msg = '{count} records successfully deleted.'.format(count=count)
        messages.info(request, msg)

    def save_model(self, request, instance, form, change):
        '''
        Override save to enforce tenant assignment, log actions,
        and handle errors.
        '''
        # Check if protected and has been protected
        if instance.is_protected:
            if change:
                old_instance = self.model.objects.get(pk=instance.pk)
                if getattr(old_instance, 'is_protected', None):
                    messages.warning(request, _('Record is protected.'))
                    return

        # Fetch cached tenant
        tenant_id = self.get_tenant_id(request)

        # Ensure tenant is set if they exist in protected_foreigns
        protected_foreigns = getattr(self, 'protected_foreigns', [])
        if ('tenant' in protected_foreigns and tenant_id
                and not getattr(instance, 'tenant', None)):
            # Assign the ID directly to avoid unnecessary lookups
            instance.tenant_id = tenant_id

        # Ensure sync_to_accounting is set
        if hasattr(instance, 'sync_to_accounting'):
            if not change or form.has_changed():
                # New instance or changed fields
                instance.sync_to_accounting = True

        # Proceed with logging
        save_logging(instance, request)

        # Atomic save with error handling
        self.has_errors = True

        # debug
        #"""
        with transaction.atomic():
            super().save_model(request, instance, form, change)
            self.has_errors = False
        return
        #"""

        try:
            with transaction.atomic():
                super().save_model(request, instance, form, change)
                self.has_errors = False
        except IntegrityError as e:
            if 'Duplicate entry' in str(e):
                messages.error(request, _('Unique constraints violated.'))
            else:
                messages.error(request, _('A database error occurred.'))
        except APIRequestError as e:
            messages.error(request, _('API request failed: ') + str(e))
        except Exception as e:
            messages.error(request, _('Unexpected error: ') + str(e))

    def save_related(self, request, form, formsets, change):
        '''
        Handle inlines by ensuring related objects get required fields from form.instance.
        '''
        for formset in formsets:
            model = getattr(formset, 'model', None)
            if not model:
                continue  # Skip formsets without an associated model

            field_names = {field.name for field in model._meta.get_fields()}  # Use set for O(1) lookup

            for obj in formset.save(commit=False):
                # Assign required fields from form.instance to related objects
                for field_name in FIELDS.LOGGING_SAVE:
                    if field_name in field_names:
                        value = getattr(form.instance, field_name, None)
                        setattr(obj, field_name, value)

                obj.save()  # Save the object

            # Ensure ManyToMany relationships are saved
            formset.save_m2m()

        # Call the default save_related method to handle remaining inline models
        super().save_related(request, form, formsets, change)


# Custom inline class to handle deletion logic for related models
class RelatedModelInline(admin.TabularInline):

    def delete_model(self, request, obj):
        try:
            obj.delete()  # Direct delete with signal triggering
        except APIRequestError as e:
            raise ValidationError(f'Cannot delete: {e}')  # Prevents Django from proceeding
        except Exception as e:
            logger.error(f'Error deleting {obj}: {str(e)}')
            messages.error(request, f'Error deleting {obj}: {e}')

    def delete_queryset(self, request, queryset):
        count = 0
        errors = []
        for obj in queryset:
            try:
                with transaction.atomic():  # Ensures each delete is safe
                    obj.delete()  # This triggers external signals
                count += 1
            except Exception as e:
                errors.append(f'{obj}: {str(e)}')  # Collect errors for later reporting

        messages.info(request, f'{count} related records successfully deleted.')
        if errors:
            messages.warning(request, 'Some deletions failed:\n' + '\n'.join(errors))

    def save_related(self, request, form, formsets, change):
        '''
        Optionally override to ensure any special processing or fields
        for related models are saved before the parent model.
        '''
        super().save_related(request, form, formsets, change)
