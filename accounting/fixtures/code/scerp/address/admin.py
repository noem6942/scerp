from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .forms import AddressForm, PersonForm
from .models import (
    AddressModel, Person, Employee, Trustee, Inhabitant, Building, GeoSettings)

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('app').verbose_name = "01 Personen, Einwohner, Gebäude"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML <title>, default is "Django site admin"


class AddressInline(admin.TabularInline):
    model = AddressModel
    fields = ('name', 'type') 
    extra = 1  # Number of extra forms to display at the end of the inline


@admin.register(Person)
class Person(admin.ModelAdmin):    
    def get_form(self, request, obj=None, **kwargs):
        return AddressForm
        
    list_display = ('__str__',)


@admin.register(Employee)
class Employee(admin.ModelAdmin):
    list_display = ('__str__',)
    

@admin.register(Trustee)
class Trustee(admin.ModelAdmin):
    list_display = ('__str__',)    
    
    
@admin.register(Inhabitant)
class InhabitantAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


@admin.register(GeoSettings)
class Building(admin.ModelAdmin):
    list_display = ('__str__',)
