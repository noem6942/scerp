from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .models import Process, Task
from .forms import CustomActionForm

# Title
admin.site.site_header = _("SC-ERP - das Schweizer City ERP")  # default is "Django Administration"

# Sub title
apps.get_app_config('workflow').verbose_name = "02 Geschäftsverwaltung"
admin.site.index_title = _("Willkommen!")  # default is "Site administration"
admin.site.site_title = _("SC-ERP admin")  # this is what gets displayed in the HTML <title>, default is "Django site admin"


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ['client', 'name']
    actions = ['custom_action']
    action_form = CustomActionForm

    def custom_action(self, request, queryset):
        for process in queryset:
            # perform custom action on each process instance here
            pass
        self.message_user(request, 'Custom action was successfully performed!')

    custom_action.short_description = 'Perform custom action'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name',)
    