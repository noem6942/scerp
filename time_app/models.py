'''time_app/models.py

Data Model:

    a workspace belongs to one tenant
    a workspace can include x ClockifyUsers working belonging to N tenants
    a project always belongs to one tenant

'''
from datetime import datetime, time
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max
from django.utils.translation import get_language, gettext_lazy as _

from core.models import (
    LogAbstract, NotesAbstract,  TenantAbstract, UserProfile)

# Mandatory working hours (e.g., 8 hours per day)
MANDATORY_HOURS = 8


class Workspace(TenantAbstract):
    '''a Workspace belongs to one tenant (mainly trustee) but can serve users
        from many tenants
        verified by signals.py
    '''
    name = models.CharField(max_length=100, unique=True)
    c_created_at = models.DateTimeField(auto_now_add=True)
    api_key = models.CharField(max_length=100)    
    mandatory_hours = models.FloatField(default=MANDATORY_HOURS)
    c_id = models.CharField(max_length=24, db_index=True, unique=True)
        
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Validate tenant assignment (this replaces the clean method logic)
        if not self.tenant.is_app_time_trustee:
            raise ValidationError("Only Trustees can create workspaces")

        # Now proceed with saving the instance
        super().save(*args, **kwargs)

    class Meta:        
        ordering = ['name']
        verbose_name = _("Workspace")
        verbose_name_plural = f"Workspaces"


class ClockifyUser(LogAbstract, NotesAbstract):
    ''' ClockifyUsers can belonging to N tenants
    '''
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='time_app_profile')
    c_id = models.CharField(max_length=24, db_index=True)

    def __str__(self):
        return f"{self.user.username} (Clockify ID: {self.c_id})"

    class Meta:       
        ordering = ['user__username']
        verbose_name = _("Time User")
        verbose_name_plural = f"Time Users"


class Tag(TenantAbstract):
    ''' Belong to a workspace
    '''    
    name = models.CharField(max_length=50)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name='tag')
    c_id = models.CharField(
        max_length=24, db_index=True, blank=True, null=True)

    def __str__(self):
        return self.name


class Client(TenantAbstract):
    ''' Belong to a workspace, use carefully
    '''    
    name = models.CharField(max_length=100)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name='client')
    c_id = models.CharField(
        max_length=24, db_index=True, blank=True, null=True)

    def __str__(self):
        return self.name


class Project(TenantAbstract):
    ''' Belong to a tenant, usually not the same as the workspace owner
    '''      
    class TYPE(models.TextChoices):
        PRESENCE = 'Ab-/Anwesenheit'
        ENTRY = 'Freie Eingabe'
        CLIENT = 'Kundenauftrag'    
    
    class ClockifyColors(models.TextChoices):
        AMBER = "#FFC107", "Amber"
        BLUE = "#2196F3", "Blue"
        BLUE_GREY = "#607D8B", "Blue Grey"
        BROWN = "#795548", "Brown"
        CYAN = "#00BCD4", "Cyan"
        DEEP_ORANGE = "#FF5722", "Deep Orange"
        DEEP_PURPLE = "#673AB7", "Deep Purple"
        GREEN = "#4CAF50", "Green"
        GREY = "#9E9E9E", "Grey"
        INDIGO = "#3F51B5", "Indigo"
        LIGHT_BLUE = "#03A9F4", "Light Blue"
        LIGHT_GREEN = "#8BC34A", "Light Green"
        LIME = "#CDDC39", "Lime"
        ORANGE = "#FF9800", "Orange"
        PINK = "#E91E63", "Pink"
        PURPLE = "#9C27B0", "Purple"
        RED = "#F44336", "Red"
        TEAL = "#009688", "Teal"
        YELLOW = "#FFEB3B", "Yellow"
        
    name = models.CharField(max_length=100)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name='workspace')
    billable = models.BooleanField(default=True)
    hourly_rate = models.FloatField(blank=True, null=True)
    currency = models.CharField(max_length=3, default='CHF')
    tags = models.ManyToManyField(
        Tag, blank=True, related_name='related_projects')
    color = models.CharField(
        max_length=7,
        choices=ClockifyColors.choices,
        default=ClockifyColors.BLUE
    )    
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects'
    )    
    c_id = models.CharField(
        max_length=24, db_index=True, blank=True, null=True)    
    
    # Accounting
    type = models.CharField(
        max_length=20,
        choices=TYPE.choices,
        default=TYPE.ENTRY
    )    
    project_code = models.CharField(  # Renamed from 'project'
        max_length=100, 
        default='PR',  # 'Ab-/Anwesenheit'
        help_text="e.g. 21902412"
    )    
    position = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="e.g. 10-outsourcing"
    )        
    
    def __str__(self):
        return self.name


class TimeEntry(TenantAbstract):
    ''' Belong to a project
    '''  
    clockify_user = models.ForeignKey(
        ClockifyUser, on_delete=models.CASCADE, related_name='time_entries')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='time_entries')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='related_time_entries')  # Updated related_name
    c_id = models.CharField(
        max_length=24, db_index=True, blank=True, null=True)
        
    # Accounting
    datetime_downloaded = models.DateTimeField(blank=True, null=True)

    @property
    def duration_in_hours(self):
        """Calculate the difference in hours as a float."""
        if self.start_time and self.end_time:
            # Calculate the difference between end_time and start_time
            delta = self.end_time - self.start_time
            # Convert the difference to hours (float)
            return delta.total_seconds() / 3600
        return None
        
    @property
    def is_latest_entry_of_day(self):
        """Check if this record is the latest entry (based on start_time) for the day."""
        start_of_day = timezone.make_aware(
            datetime.combine(self.start_time.date(), time.min))
        end_of_day = timezone.make_aware(
            datetime.combine(self.start_time.date(), time.max))
        
        # Get the latest start_time for the day for this user
        latest_start_time = TimeEntry.objects.filter(
            clockify_user=self.clockify_user,
            start_time__gte=start_of_day,
            start_time__lte=end_of_day
        ).aggregate(latest_start=Max('start_time'))['latest_start']
        
        # Check if this entry is the latest one of the day
        return self.start_time == latest_start_time

    @staticmethod
    def total_hours_for_user_on_day(user, day):
        """Calculate the total hours worked by a user for a specific day."""
        
        # Create aware datetime objects for the start and end of the day
        start_of_day = timezone.make_aware(datetime.combine(day, time.min))  # start of the day
        end_of_day = timezone.make_aware(datetime.combine(day, time.max))    # end of the day
        
        # Get the time entries for the user on the specified day
        time_entries = TimeEntry.objects.filter(
            clockify_user=user,
            start_time__gte=start_of_day,
            end_time__lte=end_of_day
        )
        
        # Sum the duration of each time entry for that day
        total_duration = 0
        for entry in time_entries:
            total_duration += entry.duration_in_hours or 0

        return total_duration

    def __str__(self):
        return f"{self.start_time} to {self.end_time} ({self.duration_in_hours:.2f} hours)"
        
        
    def __str__(self):
        return (
            f"{self.clockify_user.user.username} - "
            f"{self.project.name} ({self.start_time} to {self.end_time})")

    class Meta:       
        ordering = ['clockify_user', '-start_time']
        verbose_name = _("Time Entry")
        verbose_name_plural = f"Time Entries"