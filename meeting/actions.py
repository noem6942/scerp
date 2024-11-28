# meeting/actions.py
from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from scerp.actions import action_check_nr_selected


@admin.action(description=_('1. Make minutes web page from agenda points'))
def make_minutes(modeladmin, request, queryset):
    '''
    Admin action to redirect to a custom view for generating meeting minutes.
    '''
    # Extract the IDs of selected meetings
    id = queryset.first().meeting.id
    agenda_ids = queryset.values_list('id', flat=True)    
    agenda_ids = ','.join(map(str, agenda_ids))

    # Redirect to a custom view with the meeting IDs
    url = reverse('meeting:minutes') + f'?id={id}&agenda_ids={agenda_ids}'
    return HttpResponseRedirect(url)


@admin.action(description=_('2. Show agenda as web page'))
def show_agenda(modeladmin, request, queryset):
    '''
    Admin action to redirect to a custom view for generating meeting minutes.
    '''
    if action_check_nr_selected(request, queryset, count=1):
        # Extract the IDs of selected meetings
        id = queryset.first().id
        
        # Redirect to a custom view with the meeting IDs
        url = reverse('meeting:agenda') + f'?id={id}'
        return HttpResponseRedirect(url)
