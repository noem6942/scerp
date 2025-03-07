"""
'''
crm/admin.py

'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scerp.admin import BaseAdmin
from scerp.admin_site import admin_site

from .models import AddressEch


@admin.register(AddressEch, site=admin_site)
class AddressEchAdmin(TenantFilteringAdmin, BaseAdminNew):
    ''' currently not used '''
    # Safeguards

    # Display these fields in the list view
    list_display = ('country', 'display_zip', 'town', 'street', 'house_number')
    list_display_links = ('display_zip', 'town',)

    # Search, filter
    list_filter = ('swiss_zip_code', 'foreign_zip_code', )
    search_fields = (
        'country', 'swiss_zip_code', 'foreign_zip_code', 'street', 'town')

    #Fieldsets
    fieldsets = (
        (None, {
            'fields': (
                ('swiss_zip_code', 'town'), 'street', 'house_number',
                'dwelling_number'),
            'classes': ('expand',),
        }),
        (_('Foreign Address'), {
            'fields': ('country', 'foreign_zip_code'),
            'classes': ('collapse',),
        }),
        (_('Switzerland Details'), {
            'fields': ('swiss_zip_code_add_on',),
            'classes': ('collapse',),
        }),
    )
    

    def save_model(self, request, obj, form, change):
        # Save logging
        if obj.pk:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

    @admin.display(description=_('ZIP'))
    def display_zip(self, obj):
        return obj.zip   
"""