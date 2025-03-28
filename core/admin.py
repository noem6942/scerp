# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.admin import GenericTabularInline
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from accounting.actions import de_sync_accounting, sync_accounting
from scerp.admin import (
    BaseTabularInline, Display, make_language_fields,
    BaseAdmin
)
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site
from . import actions as a
from . import filters, forms, models

FIELDSET_SYNC = (
    _('Sync'), {
        'fields': (
            'sync_to_accounting', 'is_enabled_sync'),
        'classes': ('collapse',),
    }
)


# Generic Attachments
class AttachmentInline(GenericTabularInline):
    model = models.Attachment
    extra = 1  # Number of empty forms to display by default
    fields = ('file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)  # Make uploaded_at read-only

    def save_model(self, request, obj, form, change):
        # Set the tenant and created_by fields based on the current user and tenant from the request
        obj.tenant = get_tenant_instance(request)
        obj.created_by = request.user
        super().save_model(request, instance, form, change)


@admin.register(models.Message, site=admin_site)
class MessageAdmin(TenantFilteringAdmin, BaseAdmin):
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


@admin.register(models.UserProfile, site=admin_site)
class UserProfileAdmin(TenantFilteringAdmin, BaseAdmin):
    # Display these fields in the list view
    list_display = ('user__username', 'person_photo', 'group_names')
    readonly_fields = ('user', 'group_names') + FIELDS.LOGGING

    # Search, filter
    search_fields = ('user__username',)

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('user', 'person', 'group_names'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING,
    )

    @admin.display(description=_('Groups'))
    def group_names(self, obj):
        return Display.list([x.name for x in obj.groups])

    @admin.display(description=_(''))
    def person_photo(self, obj):
        return Display.photo(obj.person.photo)


@admin.register(models.Tenant, site=admin_site)
class TenantAdmin(TenantFilteringAdmin, BaseAdmin):
    # Display these fields in the list view
    list_display = ('name', 'code', 'created_at')
    readonly_fields = FIELDS.LOGGING

    # Search, filter
    search_fields = ('name', 'code')

    # Actions
    actions = [a.init_setup]

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'is_app_time_trustee'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING,
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


@admin.register(models.TenantSetup, site=admin_site)
class TenantSetupAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant']

    # Display these fields in the list view
    list_display = (
        'display_users', 'group_names', 'display_apps', 'created_at')
    readonly_fields = ('display_users', ) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('tenant',)

    # Actions
    actions = [a.tenant_setup_create_user]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'canton', 'type', 'language', 'show_only_primary_language',
                'zips', 'display_users'
            ),  # Including the display method here is okay for readonly display
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
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


@admin.register(models.TenantLogo, site=admin_site)
class TenantLogoAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = ('tenant', 'name', 'type', 'display_logo')
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('tenant', 'name')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'logo'),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

    @admin.display(description=_('logo'))
    def display_logo(self, obj):
        return Display.photo_h(obj.logo)


# MunicipalAdmin + Tag ----------------------------------------------------
@admin.register(models.AddressMunicipal, site=admin_site)
class AddressMunicipalAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = (
        'display_zip', 'city', 'display_address', 'bdg_egid', 'bdg_category', 
        'area')
    list_display_links = ('display_zip', 'city', 'display_address')
    readonly_fields = (
        'display_zip', 'display_address') + FIELDS.LOGGING_TENANT
    list_per_page = 1000

    # Search, filter
    search_fields = ('zip', 'city', 'stn_label')
    list_filter = (filters.AreaFilter, 'zip', 'bdg_category', 'adr_status')

    # Fieldsets
    fieldsets = (
        (_('Municipality'), {
            'fields': (
                'com_fosnr', 'com_name', 'com_canton', 'display_zip', 'city'),
            'classes': ('expand',),
        }),
        (_('Street'), {
            'fields': ('str_esid', 'stn_label'),
            'classes': ('expand',),
        }),
        (_('Building'), {
            'fields': ('bdg_egid', 'bdg_category', 'bdg_name'),
            'classes': ('expand',),
        }),
        (_('Address'), {
            'fields': (
                'adr_egaid', 'adr_number', 'adr_status', 'adr_official',
                'adr_modified', 'adr_easting', 'adr_northing', 'lat', 'lon'
            ),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )

    @admin.display(description=_('ZIP'))
    def display_zip(self, obj):
        return str(obj.zip)

    @admin.display(description=_('Address'))
    def display_address(self, obj):
        return f"{obj.stn_label} {obj.adr_number}"


@admin.register(models.Area, site=admin_site)
class AreaAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = ('code', 'name')
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name')    

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'name'),
            'classes': ('expand',),
        }),
    )


# Address, Persons ---------------------------------------------------------
@admin.register(models.Title, site=admin_site)
class TitleAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Helpers
    form = forms.TitleAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('gender',)

    # Actions
    actions = [de_sync_accounting, sync_accounting]

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'gender', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        (_('Texts'), {
            'fields': (
                *make_language_fields('sentence'),),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET_SYNC
    )


@admin.register(models.PersonCategory, site=admin_site)
class PersonCategoryAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Helpers
    form = forms.PersonCategoryAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name')
    list_display_links = ('code', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ['code', 'name']

    # Actions
    actions = [de_sync_accounting, sync_accounting]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET_SYNC
    )


@admin.register(models.Address, site=admin_site)
class AddressAdmin(TenantFilteringAdmin, BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant', 'version']

    # Display these fields in the list view
    list_display = ('country', 'zip', 'city', 'address')
    list_display_links = ('zip', 'city',)

    # Search, filter
    search_fields = ('zip', 'city', 'address')

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': (('zip', 'city'), 'address', 'country'),
            'classes': ('expand',),
        }),
    )

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        """Set default country to 'CHE' (Switzerland) by fetching the instance."""
        return {'country': get_object_or_404(models.Country, alpha3='CHE')}


class AddressInline(BaseTabularInline):
    ''' slow, inlines need improvment --> read-only
    '''
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'address', 'person']

    # Inline
    model = models.PersonAddress
    form = forms.PersonAddressForm
    fields = ['type', 'address', 'post_office_box', 'additional_information']
    extra = 0  # Number of empty forms displayed
    autocomplete_fields = ['address']  # Enables a searchable dropdown
    show_change_link = True  # Allows editing the address
    verbose_name_plural = _("Addresses")


class BankAccountInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'person']

    # Inline
    model = models.PersonBankAccount
    fields = ['type', 'iban', 'bic']
    extra = 0  # Number of empty forms displayed
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Bank Accounts")


class ContactInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'version', 'person']

    # Inline
    model = models.PersonContact
    form = forms.PersonContactForm
    fields = ['type', 'address']
    extra = 0  # Number of empty forms displayed
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Contacts")


@admin.register(models.Person, site=admin_site)
class PersonAdmin(TenantFilteringAdmin, BaseAdmin):
    protected_foreigns = ['tenant', 'version', 'title', 'superior', 'category']

    # Display these fields in the list view
    list_display = (
        'company', 'first_name', 'last_name', 'alt_name', 'category',
        'display_photo'
    ) + FIELDS.ICON_DISPLAY + FIELDS.LINK_ATTACHMENT
    list_display_links = (
        'company', 'first_name', 'last_name', 'alt_name'
    ) + FIELDS.LINK_ATTACHMENT
    readonly_fields = ('nr',) + FIELDS.LOGGING_TENANT

    # Search, filter
    list_filter = ('category',)
    search_fields = ('company', 'first_name', 'last_name', 'alt_name')

    # Actions
    actions = [de_sync_accounting, sync_accounting]

    #Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'category', 'title', 'company', 'first_name', 'last_name',
                'alt_name',
            ),
        }),
        (_('Company/VAT/Work Information'), {
            'fields': (
                'vat_uid', 'industry', 'position', 'department', 'superior'
            ),
            'classes': ('collapse',),
        }),
        (_('Personal Details'), {
            'fields': ('date_birth', 'photo'),
            'classes': ('collapse',),
        }),
        (_('Categorization'), {
            'fields': (
                ('is_vendor', 'is_customer', 'is_insurance', ),
                ('is_employee', 'is_family', 'color')
            ),
            'classes': ('collapse',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET_SYNC
    )

    inlines = [
        AddressInline, ContactInline, BankAccountInline, AttachmentInline
    ]


@admin.register(models.PersonAddress, site=admin_site)
class PersonAddressAdmin(TenantFilteringAdmin, BaseAdmin):
    protected_foreigns = ['tenant', 'version', 'person', 'address']

    # Display these fields in the list view
    list_display = (
        'type', 'person', 'address') + FIELDS.ICON_DISPLAY
    readonly_fields = FIELDS.LOGGING_TENANT

    # Search, filter

    # Actions

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'type', 'person',
                'additional_information', 'post_office_box', 'address',
            ),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
        FIELDSET_SYNC
    )
