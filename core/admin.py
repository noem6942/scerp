# from django_admin_action_forms import action_with_form, AdminActionForm
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant, filter_query_for_tenant
from scerp.admin import (
    BaseAdmin, BaseTabularInline, Display, make_language_fields
)
from scerp.admin_site import admin_site
from . import actions as a, forms
from .models import (
    Message, Tenant, TenantSetup, TenantLogo, AddressCategory, UserProfile,
    AddressCategory, Address, PersonAddress, Contact, PersonContact, Title,
    PersonCategory, Person)
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

    @admin.display(description=_('Groups'))
    def group_names(self, obj):
        return Display.list([x.name for x in obj.groups])


@admin.register(Tenant, site=admin_site)
class TenantAdmin(BaseAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')

    actions = [a.init_setup]

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
            'fields': (
                'canton', 'type', 'language', 'show_only_primary_language',
                'display_users'
            ),  # Including the display method here is okay for readonly display
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


@admin.register(AddressCategory, site=admin_site)
class AddressCategoryAdmin(BaseAdmin):
    has_tenant_field = True
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
class TitleAdmin(BaseAdmin):
    # Safeguards
    has_tenant_field = True

    # Helpers
    form = forms.TitleAdminForm
    # Display these fields in the list view
    list_display = ('code', 'display_name')
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('gender',)

    #Fieldsets
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
    )


@admin.register(PersonCategory, site=admin_site)
class PersonCategoryAdmin(BaseAdmin):
    # Safeguards
    has_tenant_field = True

    # Helpers
    form = forms.PersonCategoryAdminForm

    # Display these fields in the list view
    list_display = ('code', 'display_name')
    list_display_links = ('code', 'display_name')
    readonly_fields = ('display_name',)

    # Search, filter
    search_fields = ['code', 'name']

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'code', 'display_name', *make_language_fields('name')),
            'classes': ('expand',),
        }),
    )


@admin.register(Address, site=admin_site)
class AddressAdmin(BaseAdmin):
    # Safeguards
    has_tenant_field = True
    related_tenant_fields = ['category']    

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
    has_tenant_field = True
    related_tenant_fields = ['tenant', 'person']

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
    has_tenant_field = True
    related_tenant_fields = ['tenant', 'person']

    # Inline
    model = PersonContact
    form = forms.PersonContactForm
    fields = ['type', 'address']
    extra = 1  # Number of empty forms displayed
    show_change_link = True  # Shows a link to edit the related model
    verbose_name_plural = _("Contacts")


@admin.register(Person, site=admin_site)
class PersonAdmin(BaseAdmin):
    # Safeguards
    has_tenant_field = True
    related_tenant_fields = ['title', 'superior', 'category']

    # Display these fields in the list view
    list_display = (
        'company', 'first_name', 'last_name', 'category', 'display_photo')
    list_display_links = ('company', 'first_name', 'last_name',)
    readonly_fields = ('nr',)

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
    )
    
    inlines = [AddressInline, ContactInline]
