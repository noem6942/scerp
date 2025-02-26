# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.admin import GenericTabularInline
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from scerp.admin import (
    BaseAdmin, BaseTabularInline, Display, make_language_fields,
    BaseAdminNew
)
from scerp.admin_base import TenantFilteringAdmin, FIELDS, FIELDSET
from scerp.admin_site import admin_site
from . import actions as a, forms
from .models import (
    Message, Tenant, TenantSetup, Attachment, TenantLogo, UserProfile, Country,
    AddressCategory, Address, PersonAddress, Contact, PersonContact, Title,
    PersonCategory, Person)


# Generic Attachments
class AttachmentInline(GenericTabularInline):
    model = Attachment
    extra = 1  # Number of empty forms to display by default
    fields = ('file', 'uploaded_at')  
    readonly_fields = ('uploaded_at',)  # Make uploaded_at read-only

    def save_model(self, request, obj, form, change):
        # Set the tenant and created_by fields based on the current user and tenant from the request
        obj.tenant = get_tenant_instance(request)
        obj.created_by = request.user
        super().save_model(request, instance, form, change) 


@admin.register(Message, site=admin_site)
class MessageAdmin(TenantFilteringAdmin, BaseAdminNew):
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
class UserProfileAdmin(TenantFilteringAdmin, BaseAdminNew):
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


@admin.register(Tenant, site=admin_site)
class TenantAdmin(TenantFilteringAdmin, BaseAdminNew):
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


@admin.register(TenantSetup, site=admin_site)
class TenantSetupAdmin(TenantFilteringAdmin, BaseAdminNew):
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
                'display_users'
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


@admin.register(TenantLogo, site=admin_site)
class TenantLogoAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']
    
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
        
        
# Address, Persons ---------------------------------------------------------
@admin.register(AddressCategory, site=admin_site)
class AddressCategoryAdmin(BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant']
    
    # Display these fields in the list view
    list_display = ('type', 'code', 'name')
    
    search_fields = ('type', 'code', 'name')
    fieldsets = (
        (None, {
            'fields': ('type', 'code', 'name', 'description'),
            'classes': ('expand',),
        }),
    )

    @admin.display(description=_('logo'))
    def display_logo(self, obj):
        return Display.photo_h(obj.logo)


@admin.register(Title, site=admin_site)
class TitleAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']

    # Helpers
    form = forms.TitleAdminForm
    
    # Display these fields in the list view
    list_display = ('code', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('gender',)

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
    )


@admin.register(PersonCategory, site=admin_site)
class PersonCategoryAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']

    # Helpers
    form = forms.PersonCategoryAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name')
    list_display_links = ('code', 'display_name')
    readonly_fields = ('display_name',) + FIELDS.LOGGING_TENANT

    # Search, filter
    search_fields = ['code', 'name']

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_name', *make_language_fields('name')),
            'classes': ('expand',),
        }),
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )


@admin.register(Address, site=admin_site)
class AddressAdmin(BaseAdmin):
    # Safeguards
    protected_foreigns = ['tenant']

    # Display these fields in the list view
    list_display = ('country', 'zip', 'city', 'address')
    list_display_links = ('zip', 'city',)

    # Search, filter
    list_filter = ('zip', 'country', )
    search_fields = ('zip', 'city', 'address')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (('zip', 'city'), 'address', 'country', 'categories'),
            'classes': ('expand',),
        }),
    )

    def get_changeform_initial_data(self, request):
        """Set default country to 'CHE' (Switzerland) by fetching the instance."""
        return {'country': get_object_or_404(Country, alpha3='CHE')}


class AddressInline(BaseTabularInline):
    # Safeguards
    protected_foreigns = ['tenant', 'person']
    
    # Inline
    model = PersonAddress
    form = forms.PersonAddressForm
    fields = ['type', 'address', 'post_office_box', 'additional_information']
    extra = 1  # Number of empty forms displayed
    autocomplete_fields = ['address']  # Improves FK selection performance
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Addresses")


class ContactInline(BaseTabularInline):  # or admin.StackedInline
    # Safeguards
    protected_foreigns = ['tenant', 'person']

    # Inline
    model = PersonContact
    form = forms.PersonContactForm
    fields = ['type', 'address']
    extra = 1  # Number of empty forms displayed
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Contacts")


@admin.register(Person, site=admin_site)
class PersonAdmin(TenantFilteringAdmin, BaseAdminNew):
    protected_foreigns = ['tenant', 'version', 'title', 'superior', 'category']

    # Display these fields in the list view
    list_display = (
        'company', 'first_name', 'last_name', 'category', 'display_photo'
    ) + FIELDS.ICON_DISPLAY
    list_display_links = (
        'company', 'first_name', 'last_name') + FIELDS.LINK_ATTACHMENT
    readonly_fields = ('nr',) + FIELDS.LOGGING_TENANT

    # Search, filter
    list_filter = ('category',)
    search_fields = ('company', 'first_name', 'last_name', 'alt_name')

    #Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'category', 'title', 'company', 'first_name', 'last_name',
                'alt_name', 'color'
                ),
            'description': _(
                "Either 'Company' or 'First Name' & 'Last Name' must be filled."),
        }),
        (_('Company/Work Information'), {
            'fields': ('industry', 'position', 'department', 'superior'),
            'classes': ('collapse',),
        }),
        (_('Finance & Banking'), {
            'fields': ('vat_uid', 'iban', 'bic', ),  # 'discount_percentage'
            'classes': ('collapse',),
        }),
        (_('Personal Details'), {
            'fields': ('date_birth', 'photo', 'nr'),
            'classes': ('collapse',),
        }),        
        FIELDSET.NOTES_AND_STATUS,
        FIELDSET.LOGGING_TENANT,
    )
    
    inlines = [AddressInline, ContactInline, AttachmentInline]
