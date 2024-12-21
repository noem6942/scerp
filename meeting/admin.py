from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from crm.models import Building
from core.safeguards import get_tenant
from scerp.admin import (
    admin_site, BaseAdmin, display_empty, display_verbose_name,
    display_datetime)

from .actions import show_agenda, make_minutes
from .models import (
    Meeting, AgendaItem, AgendaRemark, AgendaFile, MeetingFile, AgendaNotes, 
    AgendaResult)


class AgendaRemarkInline(admin.StackedInline):
    model = AgendaRemark
    extra = 0  # Number of blank forms to display
    fields = ('name', 'text', 'visibility')
    readonly_fields = ('id',)


class AgendaFileInline(admin.TabularInline):
    model = AgendaFile
    extra = 0  # Number of blank forms to display
    fields = ('name', 'content', 'date')
    readonly_fields = ('id', 'date')  # Date is auto-added; make it readonly


class AgendaNotesInline(admin.StackedInline):
    model = AgendaNotes
    extra = 0  # Number of blank forms to display
    fields = ('text',)
    readonly_fields = ('id',)
    show_change_link = True


class AgendaResultInline(admin.StackedInline):
    model = AgendaResult
    extra = 0  # Number of blank forms to display
    fields = ('vote', 'votes_yes', 'votes_no', 'votes_abstention')
    readonly_fields = ('id',)
    show_change_link = True
    classes = ['collapse']


class AgendaItemInline(admin.TabularInline):
    model = AgendaItem
    extra = 0  # Number of blank forms to display
    fields = ('order', 'name', 'is_business', 'id_business')
    readonly_fields = ('id', 'id_business')
    show_change_link = True


class MeetingFileInline(admin.TabularInline):
    model = MeetingFile
    extra = 1  # Number of blank forms to display
    fields = ('name', 'content', 'order', 'is_appendix', 'date')
    readonly_fields = ('id', 'date')  # Date is auto-added; make it readonly


@admin.register(Meeting, site=admin_site)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'agenda')
    search_fields = ('name',)
    list_filter = ('date',)
    inlines = [AgendaItemInline, MeetingFileInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'committee', 'date', 'opening_time', 'venue'),
            'classes': ('expand',),  # This could be collapsed by default
        }),
        (_('Invite'), {
            'fields': ('president', 'secretary'),
            'classes': ('collapse',),  # This could be collapsed by default
        }),
        # (_('Closing'), {
        #     'fields': ('vault_position',),
        #     'classes': ('collapse',),  # This could be collapsed by default
        # }),
    )

    @admin.display(description=_('Meeting Details'))
    def agenda(self, obj):
        # We create a link to the agendas' page
        link = f'../agendaitem/?meeting__id__exact={obj.id}'
        queryset = AgendaItem.objects.filter(meeting=obj).order_by('order')
        agenda_str = ', '.join([x.name for x in queryset])
        return format_html(f'<a href="{link}">{agenda_str}</a>')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'venue':
            # Filter the queryset for building to only include type='ROOM'
            kwargs['queryset'] = Building.objects.filter(
                type=Building.TypeChoices.ROOM)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AgendaItem, site=admin_site)
class AgendaItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'meeting')
    search_fields = ('name', 'meeting__name')
    list_display_links = ('name',)
    list_filter = ('meeting', 'meeting__date',)
    ordering = ['meeting', 'order']
    readonly_fields = ('meeting', 'name', 'order')
    
    inlines = [
        AgendaFileInline, AgendaRemarkInline, AgendaNotesInline, 
        AgendaResultInline]
    actions = [make_minutes, show_agenda]

    fieldsets = (
        (None, {
            'fields': ('meeting', 'name', 'order'),
            'classes': ('expand',),  # This could be collapsed by default
        }),
    )


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