# meeting/actions.py
from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _


@admin.action(description=_('Generate the minutes in HTML'))
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
