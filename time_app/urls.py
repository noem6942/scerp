'''
app_time/urls.py

usage: e.g. /api/time/time-entries/?workspace_id=1&date=2025-01-16

'''
from django.urls import path
from .views import TimeEntryListAPIView, SyncTimeEntriesAPIView


urlpatterns = [
    path('time-entries/', TimeEntryListAPIView.as_view(), 
        name='time-entry-list'),
    path('sync-time-entries/', SyncTimeEntriesAPIView.as_view(),
        name='sync-time-entries'),        
]
