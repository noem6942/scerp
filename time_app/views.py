'''
app_time/views.py
'''
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, date
from django.http import JsonResponse

from .models import Person
from .connector_clockify import Clock
from .serializers import ProjectSerializer, TimeEntrySerializer


# Mocked display_projects function
def display_projects(person, start_date, end_date):
    # Replace with the actual function or API call.
    # Mocked data returned here:
    return [{
        'id': '6782b0480f50991d14c2a663', 
        'name': 'Development', 
        'workspace_id': '67829f2d1c567d719f23da07',
        'archived': False
    }, {
        'id': '6782c2fd5be34b0f965897fa', 
        'name': 'Testing', 
        'workspace_id': '67829f2d1c567d719f23da07', 
        'archived': False
    }]


class Base(APIView):
    
    def get(self, request, *args, **kwargs):
        person_id = request.query_params.get('person_id', None)
        person = Person.objects.filter(id=person_id).first()
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)

        # Use today's date if no start_date or end_date is provided
        try:
            start_date = (
                datetime.strptime(start_date, '%Y-%m-%d').date()
                if start_date
                else date.today()
            )
            end_date = (
                datetime.strptime(end_date, '%Y-%m-%d').date()
                if end_date
                else date.today()
            )
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate required parameters
        if not person or not start_date or not end_date:
            msg = 'Missing required parameters: person, start_date, end_date'
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        return person, start_date, end_date


class ProjectListAPIView(Base):
    def get(self, request, *args, **kwargs):
        person, start_date, end_date = super().get(request, *args, **kwargs)

        # Call display_projects
        clock = Clock(person.api_key, person.workspace_id)
        projects = clock.get_projects(start_date, end_date)
        print("*projects", projects)

        # Serialize the projects
        serializer = ProjectSerializer(data=projects, many=True)
        serializer.is_valid(raise_exception=True)

        # Return the projects as a JSON response
        return Response(serializer.data, status=status.HTTP_200_OK)


class TimeListAPIView(Base):
    def get(self, request, *args, **kwargs):
        person, start_date, end_date = super().get(request, *args, **kwargs)
         
        # Fetch time entries
        clock = Clock(person.api_key, person.workspace_id)
        time_entries = clock.get_time_entries(start_date, end_date)
        print("*time_entries", time_entries)

        # Serialize and return response
        serializer = TimeEntrySerializer(data=time_entries, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)