from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub titles
apps.get_app_config('citizen').verbose_name = "Einwohnerwesen"
apps.get_app_config('workflow').verbose_name = "Geschäftsverwaltung"

