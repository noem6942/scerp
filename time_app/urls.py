from django.urls import path
from .views import ProjectListAPIView, TimeListAPIView

urlpatterns = [
    path('projects/', ProjectListAPIView.as_view(), name='project-list'),
    path('time-entries/', TimeListAPIView.as_view(), name='project-list'),
]
