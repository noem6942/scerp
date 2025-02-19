"""
scerp/admin.py

Admin configuration for the scerp app.

This module contains the configuration for models and views that manage the admin interface.
"""
import json

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError, transaction
from django.forms import Textarea
from django.http import HttpResponseForbidden
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.formats import date_format
from django.utils.translation import get_language, gettext_lazy as _

from core.models import Message, Tenant
from core.safeguards import get_tenant, filter_query_for_tenant, save_logging
from .exceptions import APIRequestError

GUI_ROOT = settings.ADMIN_ROOT
SPACE = '\u00a0'  # invisible space

# helpers
LOGGING_FIELDS = ['created_at', 'created_by', 'modified_at', 'modified_by']
REQUIRED_LOGGING_FIELDS = ['tenant', 'created_by']

NOTES_FIELDS = [
    'notes', 'attachment', 'is_protected', 'is_inactive']
TENANT_FIELD = 'tenant'

TEXTAREA_DEFAULT = {
    'rows': 1,
    'cols': 80,
}


# Helpers
def action_check_nr_selected(request, queryset, count=None, min_count=None):
    """
    This checks that a user selects the appropriate number of items in admin.py
    """
    if count is not None:
        if queryset.count() != count:
            msg = _('Please select excatly {count} record(s).').format(
                    count=count)
            messages.warning(request, msg)
            return False
    elif min_count is not None:
        if queryset.count() < min_count:
            msg =  _('Please select more than {count - 1} record(s).').format(
                    count=min_count)
            messages.warning(request, msg)
            return False

    return True


@admin.action(description=_('Set inactive'))
def set_inactive(modeladmin, request, queryset):
    queryset.update(is_inactive=True)
    msg = _("Set {count} records as inactive.").format(count=queryset.count())
    messages.success(request, msg)


@admin.action(description=_('Set protected'))
def set_protected(modeladmin, request, queryset):
    queryset.update(is_protected=True)
    msg = _("Set {count} records as protected.").format(count=queryset.count())
    messages.success(request, msg)


def format_name(obj, fieldname='name'):
    '''add symbols to name
    '''
    value = getattr(obj, fieldname)
    if value is None:
        return value
    if obj.notes:
        value += ' \u270D'
    if obj.attachment:
        value += ' \U0001F4CE'
    if obj.is_protected:
        value += ' \U0001F512'
    if obj.is_inactive:
        value += ' \U0001F6AB'
    return value


def format_big_number(value, thousand_separator=None, round_digits=None):
    """
    use settings.THOUSAND_SEPARATOR and 2 commas for big numbers
    value: float
    """
    if value is None:
        return None

    # Round
    if round_digits:
        value = round(value, round_digits)

    # Format number
    if thousand_separator is None:
        thousand_separator = settings.THOUSAND_SEPARATOR
    return f"{value:,.2f}".replace(',', thousand_separator)


def format_percent(value, precision):
    """
    use settings.THOUSAND_SEPARATOR and 2 commas for big numbers
    value: float
    """
    if value is None:
        return None

    # Format number
    return f"{value:,.{precision}f}%"


def get_help_text(model, field_name):
    """
    Get help text from model
    """
    # pylint: disable=W0212
    return model._meta.get_field(field_name).help_text


def make_language_fields(field_name):      
    # Currently show only LANGUAGE_CODE_PRIMARY
    languages = [
        (lang_code, lang) for lang_code, lang in settings.LANGUAGES
        if lang_code == settings.LANGUAGE_CODE_PRIMARY
    ]
    
    # Check if only show preferred languagen
    return [
        f'{field_name}_{lang_code}'
        for lang_code, _lang in languages
    ]


def is_required_field(model, field_name):
    """
    Get verbose_name from model
    """
    # pylint: disable=W0212
    field = model._meta.get_field(field_name)
    return not field.blank and not field.null


def verbose_name_field(model, field_name):
    """
    Get verbose_name from model
    """
    # pylint: disable=W0212
    return model._meta.get_field(field_name).verbose_name


class Display:

    def boolean(value):
        return '✔' if value else '✘'

    def datetime(value, default='-'):
        """
        Display date time nice
        """
        if value is None:
            return default
        return date_format(value, format='DATETIME_FORMAT')

    def big_number(value, round_digits=None, thousand_separator=None):
        """
        use settings.THOUSAND_SEPARATOR and 2 commas for big numberss
        """
        if value is None:
            return None

        # Format number
        try:
            number_str = format_big_number(
                value,
                round_digits=round_digits,
                thousand_separator=thousand_separator)
        except:
            number_str = value
        html = '<span style="text-align: right; display: block;">{}</span>'
        return format_html(html, number_str)

    def percentage(value, precision=1):
        """
        show percenate with{ precision} commas
        """
        if value is None:
            return None

        # Format number
        number_str = format_percent(value, precision)
        html = '<span style="text-align: right; display: block;">{}</span>'
        return format_html(html, number_str)

    def hierarchy(level, name):
        '''Function to print out hierarchy names nice;
            add spaces before the string if is_category == False
        '''
        if level == 1:
            return format_html(f"<b>{name.upper()}</b>")
        if level == 2:
            return format_html(f"<b>{name}</b>")
        return format_html(f"<i>{name}</i>")

    def json(value, sort=False):
        """
        Print string for json
        """
        if not value:
            return ''

        try:
            # Format JSON data with indentation and render it as preformatted text
            formatted_json = json.dumps(value, indent=4, ensure_ascii=False)
            return format_html(
                '<pre style="font-family: monospace;">{}</pre>', formatted_json)
        except ValueError as e:
            return f"Value Error displaying data: {e}"
        except (KeyError, TypeError) as e:  # Catch specific exceptions
            return f"Key or Type Error displaying data: {e}"
        except Exception as e:  # pylint: disable=W0718
            # Last resort: Catch any other exceptions
            return f"Unexpected error displaying data: {e}"

    def link(url, name):
        """
        Generates a clickable link for the Django admin interface.

        Args:
            url (str): The URL to link to.
            name (str): The text to display for the link.

        Returns:
            str: HTML string with a clickable link.
        """
        return format_html('<a href="{}" target="_blank">{}</a>', url, name)

    def list(items):
        output_list = [f"<li>{item}</li>" for item in items]
        return format_html(''.join(output_list))

    def photo(url_field):
        """
        Display photo
        """
        if url_field:
            return mark_safe(
                f'<img src="{url_field.url}" width="60" height="60" '
                f'style="object-fit: cover;" />')
        return ''

    def verbose_name(def_cls, field):
        """
        Display verbose name from field
        """
        f_cls = getattr(def_cls, 'Field')
        return getattr(f_cls, field)['verbose_name']

    def name_w_levels(obj):
        '''obj needs to have name, is_category, level
        '''
        name = format_name(obj)
        if obj.is_category:
            level = obj.level
            if level < 3:
                return format_hierarchy(obj.level, name)
        return name


# Widgets
def override_textfields_default(attrs=None):
    """
    Default textfield too small
    """
    if attrs is None:
        attrs = TEXTAREA_DEFAULT

    return {
        models.TextField: {'widget': Textarea(attrs=attrs)}
    }


# Customize classes

# Constraints
def filter_foreignkeys(modeladmin, db_field, request, kwargs):
    """
    Limit availabe foreign keys to items you are allowed to choose from
    """
    if db_field.name in getattr(modeladmin, 'related_tenant_fields', []):
        tenant_data = get_tenant(request)  # Get the tenant from the request
        tenant_id = tenant_data.get('id')

        if not tenant_id:
            raise ValueError("Tenant ID is missing from tenant data")

        # Dynamically get the related model using db_field.remote_field.model
        related_model = db_field.remote_field.model

        # Filter the queryset of the field by tenant
        if hasattr(related_model, 'tenant'):
            kwargs['queryset'] = related_model.objects.filter(
                tenant_id=tenant_id)
        else:
            kwargs['queryset'] = related_model.objects.none()


def filter_manytomany(modeladmin, db_field, request, **kwargs):
    """
    Limit availabe manytomany keys to items you are allowed to choose from
    """
    tenant_data = get_tenant(request)  # Get the tenant from the request
    tenant_id = tenant_data.get('id')

    if not tenant_id:
        raise ValueError("Tenant ID is missing from tenant data")

    if db_field.name in getattr(
            modeladmin, 'related_tenant_manytomany_fields', []):
        kwargs['queryset'] = Recipient.objects.filter(
            tenant__id=tenant_data['id'])


def filter_queryset(modeladmin, request, queryset):
    """
    Limit queryset based on user or other criteria.
    """
    if getattr(modeladmin, 'has_tenant_field', False):
        tenant_data = get_tenant(request)  # Get tenant information

        # Use select_related for ForeignKey fields and prefetch_related for Many-to-Many
        optimize_foreigns = getattr(modeladmin, 'optimize_foreigns', [])
        optimize_many_to_many = getattr(
            modeladmin, 'optimize_many_to_many', [])

        if optimize_foreigns:
            queryset = queryset.select_related(*optimize_foreigns)
        if optimize_many_to_many:
            queryset = queryset.prefetch_related(*optimize_many_to_many)

        # Filter queryset based on tenant-specific criteria
        try:
            queryset = filter_query_for_tenant(request, queryset)
        except Exception as e:
            # Catch unexpected errors and log them
            msg = _("Unexpected error filtering tenant: {e}").format(e=e)
            messages.error(request, msg)
            raise  # Re-raise the exception to propagate it

    return queryset


class BaseTabularInline(admin.TabularInline):
    """
    Constrains for TabularInline classes
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        filter_foreignkeys(self, db_field, request, kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        filter_manytomany(self, db_field, request, **kwargs)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class BaseAdmin(ModelAdmin):
    """
    Constrains for ModelAdmin classes
    """
    # format
    formfield_overrides = override_textfields_default(
        {'rows': 3, 'cols': 80})  # Set form field overrides here if needed
    list_display = ('',)  # Default fields to display in list view
    readonly_fields = []  # Fields that are read-only by default

    # list_display_links = None  # Removes the links from list display
    # empty_value_display = _('-empty-')  # can be defined individually

    def get_list_display(self, request):
        ''' Automatically append 'has_notes' and 'has_attachment' etc. to list_display '''
        # Get the original list_display from any child class
        list_display = super().get_list_display(request)

        return list_display

    def get_fieldsets(self, request, obj=None):
        """Return all fields in a single fieldset, with optional additional sections."""
        # Check all fields
        fields = []
        if self.fieldsets:
            for _label, dict_ in self.fieldsets:
                fields += dict_['fields']

        # Check tenant
        if getattr(self, 'has_tenant_field', False) and 'tenant' in fields:
            messages.error(request, _('Tenant is not included') )
            return []

        # Custom fields
        note_fields = [x for x in NOTES_FIELDS if x not in fields]

        # Logging fields
        logging_fields = [x for x in LOGGING_FIELDS if x not in fields]
        if getattr(self, 'has_tenant_field', False):
            logging_fields.append(TENANT_FIELD)

        # Build used fields
        used_fields = list(self.list_display)
        if not hasattr(self, 'fieldsets') or not self.fieldsets:
            self.fieldsets = (
                (None, {
                    'fields': used_fields,
                    'classes': ('expand',),
                }),
            )

        # Create a base fieldset
        fieldsets = (
            list(self.fieldsets) if getattr(self, 'fieldsets', None)
            else [])

        # If no fieldsets are defined, initialize with a default fieldset
        if not fieldsets:
            fieldsets = [
                (None, {
                    'fields': self.list_display,  # or other default fields
                    'classes': ('expand',),
                }),
            ]

        # Add additional sections like Notes and Logging
        return self.fieldsets + (
            (_('Notes, Attachment and Status'), {
                'fields': note_fields,
                'classes': ('collapse',),
            }),
            (_('Logging'), {
                'fields': logging_fields,
                'classes': ('collapse',),
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        """
        Dynamically set read-only fields based on user or conditions.
        """
        # Readonly fields
        readonly_fields = list(self.readonly_fields)
        readonly_fields.extend(LOGGING_FIELDS)

        # Hide tenant
        if getattr(self, 'has_tenant_field', False):
            readonly_fields.extend([TENANT_FIELD])
        return readonly_fields

    def changelist_view(self, request, extra_context=None):
        """
        Show warning for a model if specified
        """
        if not request.session.get('_messages_shown', False):
            ''' show a info message at the top '''
            # Check if messages were already displayed
            if getattr(self, 'warning', ''):
                messages.warning(request, mark_safe(self.warning))
            if getattr(self, 'info', ''):
                messages.info(request, mark_safe(self.info))
            if getattr(self, 'error', ''):
                messages.error(request, mark_safe(self.error))

        return super().changelist_view(request, extra_context=extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        filter_foreignkeys(self, db_field, request, kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        filter_manytomany(self, db_field, request, **kwargs)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return filter_queryset(self, request, queryset)

    def delete_model(self, request, obj):
        try:
            with transaction.atomic():  # Ensure atomic deletion
                obj.delete()

        except APIRequestError as e:
            raise ValidationError(f"Cannot delete: {e}")  # Prevents Django from proceeding

        except Exception as e:
            messages.error(request, f"Error deleting category: {e}")

    def delete_queryset(self, request, queryset):
        count = 0
        for obj in queryset:
            try:
                with transaction.atomic():  # Ensures each delete is independent
                    obj.delete()
                count += 1
            except Exception as e:
                messages.warning(request, f"{obj}: {str(e)}")

        msg = "{count} records successfully deleted.".format(count=count)
        messages.info(request, msg)

    def save_model(self, request, instance, form, change):
        """
        Override save to include additional logging or other custom logic.
        """
        # Check if tenant mandatory
        add_tenant = getattr(self, 'has_tenant_field', False)
        print("*add_tenant")
        # Check tenant
        if add_tenant and not getattr(instance, 'tenant', None):
            # Get the tenant from the request
            tenant_data = get_tenant(request)

            # Set initial value
            instance.tenant = Tenant.objects.get(id=tenant_data['id'])

        # Proceed with logging
        queryset = save_logging(instance, request, add_tenant=add_tenant)

        # APISetup update
        # Handle forbidden response from logging
        if isinstance(queryset, HttpResponseForbidden):
            messages.error(request, f"{queryset.content.decode()}")
            return  # Early return to prevent further processing
        print("*APISetup")
        
        # Save the model instance first (this ensures it gets an id)
        super().save_model(request, instance, form, change)

        # Now that the object has an id, save the many-to-many relationships
        if instance.pk:  # Ensure the instance has been saved and has an ID
            instance.bookings.set(form.cleaned_data['bookings'])        
        
        # Only save the model if there are no errors
        try:
            with transaction.atomic():
                print("*1")
                super().save_model(request, instance, form, change)
                print("*2")
        except IntegrityError as e:
            if "Duplicate entry" in str(e):
                messages.error(request, _("Unique constraints violated."))
            else:
                messages.error(request, _("A database error occurred."))
        except APIRequestError as e:
            messages.error(request, _("API request failed: ") + str(e))
        except Exception as e:
            messages.error(request, _("Unexpected error: ") + str(e))


    def save_related(self, request, form, formsets, change):
        """
        Used for inlines
        Loop through each formset to check if we have some required fields
        that can be derived from form.instance
        """        
        # See if some special fields need to be considered
        save_for_related = getattr(self, 'save_for_related', [])

        for formset in formsets:
            # Save the related EventLog instances without committing them to
            # the DB yet
            field_names = [x.name for x in formset.model._meta.get_fields()]
            for obj in formset.save(commit=False):
                # Check related must fields
                for field_name in REQUIRED_LOGGING_FIELDS + save_for_related:
                    if field_name in field_names:
                        value = getattr(form.instance, field_name)
                        setattr(obj, field_name, value)

                # Save the obj
                # obj.save()

        # Call the default save_related method to save the inline models
        super().save_related(request, form, formsets, change)
