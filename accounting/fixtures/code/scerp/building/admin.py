from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .models import BuildingForLater

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('building').verbose_name = "06 Bauverwaltung"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML <title>, default is "Django site admin"


@admin.register(BuildingForLater)
class BuildingForLaterAdmin(admin.ModelAdmin):
    pass
    # list_display = ('name', 'client')