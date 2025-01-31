'''
time_app/serializers.py
'''
from rest_framework import serializers
from .models import TimeEntry, Tag, Client, Project


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'c_id']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'c_id']


class ProjectSerializer(serializers.ModelSerializer):
    client = ClientSerializer()  # Nested client serializer
    tags = TagSerializer(many=True)  # Nested tag serializer

    class Meta:
        model = Project
        fields = ['id', 'name', 'client', 'tags', 'color', 'billable', 'hourly_rate', 'currency']


class TimeEntrySerializer(serializers.ModelSerializer):
    project = ProjectSerializer()  # Nested project serializer
    tags = TagSerializer(many=True)  # Nested tag serializer

    class Meta:
        model = TimeEntry
        fields = [
            'id', 'clockify_user', 'start_time', 'end_time', 
            'description', 'tags', 'project', 'c_id', 'datetime_downloaded'
        ]
