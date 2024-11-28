# meeting/urls.py
from django.urls import path
from .views import show_agenda_view, make_minutes_view


app_name = 'meeting'  # Reserve a namespace for this app

urlpatterns = [
    path('agenda/', show_agenda_view, name='agenda'),
    path('minutes/', make_minutes_view, name='minutes'),    
]

