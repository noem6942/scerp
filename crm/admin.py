from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scerp.admin import make_multilanguage
from . import forms

from scerp.admin import admin_site, BaseAdmin

from .models import (
    Address, Contact, Title, PersonCategory, Building)


# Define inline for AddressPerson
class AddressInline(admin.TabularInline):
    model = Address
    extra = 1  # Specifies number of blank forms displayed for new Addresses


# Define inline for Contact
class ContactInline(admin.TabularInline):
    model = Contact
    extra = 1  # Specifies number of blank forms displayed for new Contacts


@admin.register(Title, site=admin_site)
class TitleAdmin(BaseAdmin):
    has_tenant_field = True
    form = forms.TitleAdminForm    
    list_display = ('name',)    
    read_only = ('name')    
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                *make_multilanguage('name'), *make_multilanguage('sentence')),
            'classes': ('expand',),
        }),
    )
