from django.apps import apps
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Route, Period, Subscriber, Meter, Value, BillSetup)

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('billing').verbose_name = "04 Gebühren"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML 

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)
    list_filter = ('name',)


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    pass


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    pass


@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    pass


@admin.register(Value)
class ValueAdmin(admin.ModelAdmin):
    pass


@admin.register(BillSetup)
class BillSetupAdmin(admin.ModelAdmin):
    pass

