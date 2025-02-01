'''
app_time/views.py
'''
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .connector_clockify import Clock
from .models import ClockifyUser, TimeEntry, Project, Tag, Client, Workspace
from .serializers import TimeEntrySerializer


class TimeEntryListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        workspace_id = request.query_params.get('workspace_id')
        date_str = request.query_params.get('date')

        if not workspace_id or not date_str:
            return Response(
                {'error': 'Both workspace_id and date are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Convert the date string into a date object
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert the date to a timezone-aware datetime object 
        # start of the day
        tz_aware_date_start = timezone.make_aware(datetime.combine(
            date, datetime.min.time()))
        # The end of the day
        tz_aware_date_end = tz_aware_date_start + timedelta(days=1)  

        # Filter the TimeEntry model by the date range and workspace_id
        time_entries = TimeEntry.objects.filter(
            start_time__gte=tz_aware_date_start,
            start_time__lt=tz_aware_date_end,
            project__workspace_id=workspace_id,
        )

        # Serialize the filtered time entries
        serializer = TimeEntrySerializer(time_entries, many=True)

        # Return the serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)


class SyncTimeEntriesAPIView(APIView):
    def get(self, request, *args, **kwargs):
            messages = []
            #try:
            # Instantiate Clock object
            api_key = "YzJkYTg3NTgtZWU5Zi00ZWM5LThhOTMtZjk0OTdlOTY4ZTBi"
            workspace_id="67829f2d1c567d719f23da07"            
            
            # api_key = request.query_params.get('api_key')
            # workspace_id = request.query_params.get('workspace_id')

            if not api_key or not workspace_id:
                return Response(
                    {'error': 'Both api_key and workspace_id are required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            clock = Clock(api_key, workspace_id)
            time_entries = clock.get_time_entries()

            created_entries = 0
            updated_entries = 0
            tenant = Workspace.objects.get(c_id=workspace_id).tenant

            for entry in time_entries:
                c_id = entry.get('id')
                description = entry.get('description', '')

                # Convert timestamps
                start_time = parse_datetime(entry['timeInterval']['start'])
                end_time = parse_datetime(entry['timeInterval']['end'])

                # Fetch related objects
                clockify_user, _ = ClockifyUser.objects.get_or_create(
                    c_id=entry['userId'], defaults={'name': 'Unknown User'}
                )
                
                project = Project.objects.filter(
                    c_id=entry['projectId']).first()
                if not project:
                    msg = f"*project {entry['projectId']} not existing)"
                    messages.append(msg)
                    print(msg)
                    continue

                # Get or create the time entry
                time_entry, created = TimeEntry.objects.get_or_create(
                    c_id=c_id,
                    defaults={
                        'clockify_user': clockify_user,
                        'project': project,
                        'start_time': start_time,
                        'end_time': end_time,
                        'description': description,
                        'created_by': request.user,
                        'tenant': tenant
                    }
                )

                if created:
                    created_entries += 1
                else:
                    updated_entries += 1
                    time_entry.start_time = start_time
                    time_entry.end_time = end_time
                    time_entry.description = description
                    time_entry.project = project
                    time_entry.clockify_user = clockify_user
                    time_entry.created_by = request.user
                    time_entry.tenant = tenant                    
                    time_entry.save()

                # Handle Many-to-Many Tags
                tag_ids = entry.get('tagIds') or [] 
                for tag_id in tag_ids:
                    tag = Tag.objects.filter(c_id=tag_id).first()
                    if not tag:
                        msg = f"*tag {tag_id} not existing)"
                        messages.append(msg)
                        print(msg)                        
                        continue

            msg = 'ok'
            if messages:
                msg += '.'.joins(messages)
                
            return Response({
                'message': msg,
                'created': created_entries,
                'updated': updated_entries,
            }, status=status.HTTP_200_OK)
            '''
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            '''