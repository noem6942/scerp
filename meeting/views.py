# meeting/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import (
    Meeting, Agenda, AgendaResult, MeetingFile)


def get_agenda(id):
    return {
       'agenda':  get_object_or_404(Agenda, id=id),
       'result': AgendaResult.objects.filter(agenda__id=id).first()
    }


# meeting/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Meeting, Agenda, AgendaResult, MeetingFile

def get_agenda(id):
    '''Fetch agenda and its corresponding result.'''
    agenda = get_object_or_404(Agenda, id=id)
    result = AgendaResult.objects.filter(agenda__id=id).first()  # .first() to avoid exceptions if no results
    return {
        'agenda': agenda,
        'result': result  # it could be None if no result exists
    }


@login_required
def show_agenda_view(request):
    '''View for showing agenda details. Make sure the user is logged in.'''
    template = 'meeting/agenda.html'

    # Get 'id' from GET parameters, handle invalid input
    id = request.GET.get('id')
    if not id:
        # Handle error if 'id' is missing (e.g., redirect or show an error message)
        return render(request, 'error_template.html', {'message': 'Agenda ID is required.'})

    # Fetch the agenda details
    agenda_data = get_agenda(id)

    # Return the rendered template with agenda data
    config = {        
        'agenda': agenda_data
    }
    return render(request, template, config)


@login_required
def make_minutes_view(request):
    '''View to generate minutes in HTML format.'''
    template = 'meeting/meeting.html'

    # Get 'id' and 'agenda_ids' from GET parameters
    id = request.GET.get('id')
    if not id:
        return render(request, 'error_template.html', {'message': 'Meeting ID is required.'})

    # Fetch the meeting data
    meeting = get_object_or_404(Meeting, id=id)
    files = MeetingFile.objects.filter(meeting__id=id)

    # Get the 'agenda_ids' from GET parameters and handle the case where it's empty
    agenda_ids = request.GET.get('agenda_ids', '')
    if agenda_ids:
        agenda_ids = agenda_ids.split(',')
        agendas = [get_agenda(agenda_id) for agenda_id in agenda_ids]
    else:
        agendas = []  # In case no agenda_ids are provided

    # Return the rendered template with meeting and agendas data
    config = {
        'meeting': {
            'meeting': meeting,
            'files': files
        },
        'agendas': agendas        
    }
    return render(request, template, config)
