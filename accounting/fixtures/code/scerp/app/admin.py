from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .models import (
    Admin, Client, Location)

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('app').verbose_name = "01 Basis Modul"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML <title>, default is "Django site admin"


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('org', 'client')


class LocationInline(admin.TabularInline):
    model = Location
    fields = ('name', 'type') 
    extra = 1  # Number of extra forms to display at the end of the inline


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    readonly_fields = ('logo',)
    inlines = [LocationInline, ]
    list_display = ('name', 'logo', 'uploaded')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'vat_uid', 'client')

