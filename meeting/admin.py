from django.contrib import admin

from scerp.admin import (
    admin_site, App, AppConfig, BaseAdmin, display_empty, display_verbose_name,
    display_datetime)

from .locales import APP
from .models import Meeting, Agenda, Remark, AgendaFile, MeetingFile

# init admin
app = App(APP)


class RemarkInline(admin.StackedInline):
    model = Remark
    extra = 1  # Number of blank forms to display
    fields = ('name', 'text', 'visibility')
    readonly_fields = ('id',)


class AgendaFileInline(admin.TabularInline):
    model = AgendaFile
    extra = 1  # Number of blank forms to display
    fields = ('name', 'content', 'date')
    readonly_fields = ('id', 'date')  # Date is auto-added; make it readonly


class AgendaInline(admin.TabularInline):
    model = Agenda
    extra = 1  # Number of blank forms to display
    fields = ('name', 'order')
    readonly_fields = ('id',)
    show_change_link = True


class MeetingFileInline(admin.TabularInline):
    model = MeetingFile
    extra = 1  # Number of blank forms to display
    fields = ('name', 'content', 'order', 'is_appendix', 'date')
    readonly_fields = ('id', 'date')  # Date is auto-added; make it readonly


@admin.register(Meeting, site=admin_site)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('name', 'datetime')
    search_fields = ('name',)
    list_filter = ('datetime',)
    inlines = [AgendaInline, MeetingFileInline]


@admin.register(Agenda, site=admin_site)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'meeting')
    search_fields = ('name', 'meeting__name')
    list_display_links = ('name',)
    list_filter = ('meeting', 'meeting__datetime',)
    ordering = ['meeting', 'order']
    inlines = [AgendaFileInline, RemarkInline]  # Manage remarks and files within an agenda

''' only accessible via Meeting and Agenda 
@admin.register(Remark, site=admin_site)
class RemarkAdmin(admin.ModelAdmin):
    list_display = ('name', 'agenda', 'visibility')
    search_fields = ('name', 'text')
    list_filter = ('visibility', 'agenda__meeting')
    autocomplete_fields = ('agenda',)  # Makes agenda selection easier
    ordering = ['name']


@admin.register(AgendaFile, site=admin_site)
class AgendaFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'agenda', 'date')
    search_fields = ('name',)
    list_filter = ('agenda__meeting', 'date')
    autocomplete_fields = ('agenda',)  # Makes agenda selection easier
    ordering = ['name']
'''