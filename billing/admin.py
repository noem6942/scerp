from django.contrib import admin
from django.shortcuts import render
from django.http import HttpResponseRedirect

from scerp.admin import verbose_name_field, BaseAdmin
from scerp.admin_site import admin_site

from .models import Counter, Subscription


@admin.register(Counter, site=admin_site)
class CounterAdmin(BaseAdmin):
    list_display = ('nr', 'function', 'status', 'jg')
    search_fields = ('nr', 'function', 'jg', 'status')
    list_filter = ('function', 'jg', 'status')
    actions = ['update_status']

    def update_status(self, request, queryset):
        # Only proceed if 'apply' is in POST, ensuring the intermediate form is shown first.
        if 'apply' in request.POST:
            # User confirmed the action, so update dates
            queryset.update(status=None)
            
            # Show a success message and redirect back to the list view
            self.message_user(
                request, "Changed status on {} counters".format(queryset.count())
            )
            return HttpResponseRedirect(request.get_full_path())
        
        # Render intermediate confirmation page if 'apply' is not in POST
        return render(
            request, 'admin/counter_intermediate.html',
            context={'counters': queryset}
        )

    update_status.short_description = "Update status"
  

@admin.register(Subscription, site=admin_site)
class SubscriptionAdmin(BaseAdmin):
    list_display = ('abo_nr', 'name_vorname', 'tarif', 'tarif_bez', 'ansatz_nr', 'ansatz', 'basis', 'betrag')
    search_fields = ('name_vorname',)
    list_filter = (
        'tarif', 'ansatz_nr', 'ansatz')

    fieldsets = (
        (None, {
            'fields': (
                'abo_nr', 'r_empf', 'pers_nr', 'name_vorname', 'strasse', 'plz_ort',                 
            ),
            'classes': ('expand',),            
        }),
        ('Meter & Calculation Info', {
            'fields': (
                'periode', 'tage', 'basis', 
                'tarif', 'tarif_bez',                 
                'ansatz_nr', 'ansatz', 
                'betrag', 'inkl_mwst'
            ),
            'classes': ('collapse',),            
        }),
        ('Additional Text', {
            'fields': (
                'steuercode_zaehler', 
                'steuercode_gebuehren', 
                'berechnungs_code_zaehler', 
                'berechnungs_code_gebuehren',
                'gebuehrentext', 
                'gebuehren_zusatztext'
            ),
            'classes': ('collapse',),            
        }),
    )
