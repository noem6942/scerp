from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .models import (
    FiscalPeriod, AccountingSetup, Rounding, Vat, RevenueAccount,
    AccountingSystem)

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('accounting').verbose_name = "05 Finanzbuchhaltung"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML <title>, default is "Django site admin"


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(AccountingSetup)
class AccountingSetupAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(Rounding)
class RoundingAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(Vat)
class VatAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(RevenueAccount)
class RevenueAccountAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(AccountingSystem)
class AccountingSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'url')