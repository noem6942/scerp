# meeting/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import (
    Meeting, Agenda, AgendaResult, MeetingFile)


@login_required
def make_minutes_view(request):
    '''make a html for minutes, to add: tenant check!!!
    '''
    template = 'meeting/meeting.html'
    
    # Get Meeting
    id = request.GET.get('id')
    meeting = {
        'meeting': get_object_or_404(Meeting, id=id),
        'files': MeetingFile.objects.filter(meeting__id=id)
    }    

    # Get agenda
    agenda_ids = request.GET.get('agenda_ids', '').split(',')
    agendas = []
    for id in agenda_ids:
        agendas.append({
           'agenda':  get_object_or_404(Agenda, id=id),
           'result': AgendaResult.objects.filter(agenda__id=id).first()
        })
    
    # Return
    config = {
        'meeting': meeting,
        'agendas': agendas        
    }     
    return render(request, template, config)
