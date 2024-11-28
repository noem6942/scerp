# meeting/urls.py
from django.urls import path
from .views import make_minutes_view


app_name = 'meeting'  # Reserve a namespace for this app

urlpatterns = [
    path('minutes/', make_minutes_view, name='minutes'),
]

