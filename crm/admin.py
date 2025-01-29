from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from . import forms
from accounting.models import Title as AcctTitle
from scerp.admin import BaseAdmin, make_multilanguage
from scerp.admin_site import admin_site


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
    list_display = ('code', 'name', 'is_in_accounting')    
    read_only = ('name')    
    
    fieldsets = (    
        (_('Name'), {
            'fields': (
                'code', *make_multilanguage('name'), 
                *make_multilanguage('sentence')),
            'classes': ('expand',),
        }),
    )
    
    @admin.display(description=_('accounting'))
    def is_in_accounting(self, obj):
        return "✔" if AcctTitle.objects.filter(id=obj.id).exists() else "✘"
