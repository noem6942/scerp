from django.contrib import admin

from scerp.admin import (
    admin_site, BaseAdmin, display_verbose_name, display_datetime)

from .models import (
    PersonAccount, AddressPerson, Contact, PersonCategory, Building)


# Define inline for AddressPerson
class AddressInline(admin.TabularInline):
    model = AddressPerson
    extra = 1  # Specifies number of blank forms displayed for new Addresses


# Define inline for Contact
class ContactInline(admin.TabularInline):
    model = Contact
    extra = 1  # Specifies number of blank forms displayed for new Contacts


# Admin for PersonAccount, including AddressPerson and Contact inlines
@admin.register(PersonAccount, site=admin_site) 
class PersonAccountAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'company', 'birth_date', 'isInactive')
    search_fields = ('first_name', 'last_name', 'company')
    inlines = [AddressInline, ContactInline]
    

# Register PersonCategory model separately
@admin.register(PersonCategory, site=admin_site) 
class PersonCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percentage', 'parent_id', 'sequence_nr_id')



# Register Building
@admin.register(Building, site=admin_site) 
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'zip', 'city', 'address')
