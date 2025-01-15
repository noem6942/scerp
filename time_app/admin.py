from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Project

from scerp.admin import admin_site, BaseAdmin


@admin.register(Project, site=admin_site)
class ProjectAdmin(BaseAdmin):
    list_display = ('name',)    
    
    fieldsets = (
        (_('Name'), {
            'fields': (
                'person', 'name', 'client_id', 'billable', 'color',
                'tags'),
            'classes': ('expand',),
        }),
    )
