from django.db import models

from crm.models import Building


class Meeting(models.Model):
    name = models.CharField(max_length=255)
    datetime = models.DateTimeField()
    place = models.ForeignKey(
        Building, null=True, on_delete=models.CASCADE, 
        related_name='meeting')      

    def __str__(self):
        return self.name


class Agenda(models.Model):
    VOTE_CHOICES = [
        ('approved', 'Angenommen'),
        ('denied', 'Abgelehnt'),
    ]

    meeting = models.ForeignKey(Meeting, related_name='agenda_points', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    vote = models.CharField(
        max_length=20, choices=VOTE_CHOICES, null=True, blank=True)    
    votes_yes = models.PositiveIntegerField(null=True, blank=True)
    votes_no = models.PositiveIntegerField(null=True, blank=True)
    votes_abstention = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.meeting.name})"

    class Meta:
        # unique_together = ('meeting', 'name')
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.name}"


class Remark(models.Model):
    VISIBILITY_CHOICES = [
        ('personal', 'Personal'),
        ('organizer', 'Organizer'),
        ('all_members', 'All Members'),
    ]

    name = models.CharField(max_length=255)
    text = models.TextField()
    agenda = models.ForeignKey(
        Agenda, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='remark')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='personal')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        
        
class File(models.Model):
    name = models.CharField(max_length=255)
    content = models.FileField(upload_to='uploads/files/')
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ['name']

class AgendaFile(File):
    agenda = models.ForeignKey(
        Agenda, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='agenda_file')
        

class MeetingFile(File):
    is_appendix = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, null=True, blank=True)
    meeting = models.ForeignKey(
        Meeting, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='minutes_file')

    class Meta:        
        ordering = ['order', 'name']
