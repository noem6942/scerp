'''
time_app/resources.py
'''
from import_export.resources import ModelResource
from import_export import fields

from .models import TimeEntry


class TimeEntryResource(ModelResource):
    start_date = fields.Field(column_name='start_date')

    class Meta:
        model = TimeEntry
        fields = (
            'project__name', 'start_date', 'start_time', 'end_time',
            'description')

    def dehydrate_start_date(self, obj):
        return obj.start_time.strftime("%Y-%m-%d") if obj.start_time else ""

    def dehydrate_start_time(self, obj):
        return obj.start_time.strftime("%H:%M") if obj.start_time else ""

    def dehydrate_end_time(self, obj):
        return obj.end_time.strftime("%H:%M") if obj.end_time else ""
