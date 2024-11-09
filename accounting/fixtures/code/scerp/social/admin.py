from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .models import Social

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('social').verbose_name = "09 Sozialwesen"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML <title>, default is "Django site admin"


@admin.register(Social)
class SocialAdmin(admin.ModelAdmin):
    pass
    # list_display = ('name', 'client')