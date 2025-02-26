from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import CharField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import formats
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportActionMixin

from core.safeguards import get_tenant, save_logging
from core.models import Country, Address, Contact
from scerp.actions import set_inactive, set_protected
from scerp.admin import (
     BaseAdmin, BaseAdminNew, BaseTabularInline, Display,
     verbose_name_field, make_language_fields)
from scerp.admin_base import (
    TenantFilteringAdmin, FIELDS as BASE_FIELDS, FIELDSET as BASE_FIELDSET)
from scerp.admin_site import admin_site
from scerp.mixins import primary_language, show_hidden

from . import forms, models, actions as a
from .admin_base import FIELDS, FIELDSET, CashCtrlAdmin
from .resources import (
    LedgerBalanceResource, LedgerPLResource, LedgerICResource
)


@admin.register(models.APISetup, site=admin_site)
class APISetupAdmin(TenantFilteringAdmin, BaseAdminNew):
    # Safeguards
    protected_foreigns = ['tenant']

    # Display these fields in the list view
    list_display = ('tenant', 'org_name', 'display_api_key')
    readonly_fields = ('display_name',) + BASE_FIELDS.LOGGING_TENANT
    
    # Search, filter
    search_fields = ('tenant', 'org_name')

    # Actions
    actions = [
        a.api_setup_get,
        a.init_setup,
        a.api_setup_delete_hrm_accounts,
        a.api_setup_delete_system_accounts,
        a.api_setup_delete_hrm_categories,
        a.api_setup_delete_system_categories
    ]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                'org_name',
                'api_key',
                'language',
                'is_default'
            ),
            'classes': ('expand',),
        }),
        BASE_FIELDSET.NOTES_AND_STATUS,
        BASE_FIELDSET.LOGGING_TENANT,        
    )
    
    @admin.display(description=_('API Key'))
    def display_api_key(self, obj):
        return show_hidden(obj.api_key)       
    

@admin.register(models.CustomFieldGroup, site=admin_site)
class CustomFieldGroupAdmin(TenantFilteringAdmin, CashCtrlAdmin):
    # Safeguards
    protected_foreigns = ['setup', 'tenant']

    # Display these fields in the list view
    list_display = ('code', 'name', 'type') + FIELDS.C_DISPLAY
    readonly_fields = ('display_name',) + FIELDS.C_READ_ONLY

    # Search, filter
    search_fields = ('code', 'name')
    list_filter = ('type',)

    # Actions
    actions = [a.accounting_get_data, a.accounting_get_data_2]

    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'type'),
            'classes': ('expand',),
        }),
        FIELDSET.CASH_CTRL,     
    )
    

# Core Title, PersonCategory, Person
class Core(TenantFilteringAdmin, CashCtrlAdmin):
    # Safeguards
    protected_foreigns = ['setup', 'core']

    # Display these fields in the list view
    list_display = ('core', ) + FIELDS.C_DISPLAY
    readonly_fields = FIELDS.C_READ_ONLY

    # Actions
    actions = [
        a.accounting_get_data, a.sync_accounting, a.de_sync_accounting]

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': ('core', ),
            'classes': ('expand',),
        }),
        # BASE_FIELDSET.NOTES_AND_STATUS,
        FIELDSET.CASH_CTRL,            
    )
    """
    def has_add_permission(self, request):
        return False  # Prevent adding new instances

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting instances    
    """

@admin.register(models.Title, site=admin_site)
class TitleAdmin(Core):
    pass
    

@admin.register(models.PersonCategory, site=admin_site)
class PersonCategoryAdmin(Core):
    pass
    

@admin.register(models.Person, site=admin_site)
class PersonAdmin(Core):
    pass