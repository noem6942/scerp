from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _

# from core.models import TenantAbstract, to be done later
from crm.models import Building
#from vault.models import RegistrationPosition


class Meeting(models.Model):
    # Core
    name = models.CharField(max_length=255)
    committee = models.ForeignKey(
        Group, on_delete=models.CASCADE,
        related_name='committee') 
    date = models.DateField()
    opening_time = models.DateTimeField()
    closing_time = models.DateTimeField(null=True, blank=True)
    venue = models.ForeignKey(
        Building, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='meeting')     
        
    # Details    
    ''' move to CRM
    place = models.ForeignKey(
        TenantLocation, on_delete=models.CASCADE, 
        related_name='place')   
    '''
    president  = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='president')        
    secretary  = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='secretary')        
        
    # Closing   
    '''    
    vault_position = models.ForeignKey(
        RegistrationPosition, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='meeting')     
    '''
    def __str__(self):
        return self.name


class AgendaItem(models.Model):
    '''has signals
    '''
    meeting = models.ForeignKey(Meeting, related_name='agenda_points', on_delete=models.CASCADE)
    name = models.CharField(
        _("name"), max_length=255, 
        help_text=_("name of agenda"))
    order = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    is_business = models.BooleanField(default=True)
    id_business = models.CharField(max_length=16, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.meeting.name})"

    class Meta:
        # unique_together = ('meeting', 'name')
        ordering = ['order']
        verbose_name = _('Agenda Item')
        verbose_name_plural =  _('Agenda Items')


class AgendaRemark(models.Model):
    VISIBILITY_CHOICES = [
        ('personal', 'Personal'),
        ('organizer', 'Organizer'),
        ('all_members', 'All Members'),
    ]

    name = models.CharField(max_length=255)
    text = models.TextField()
    agenda = models.ForeignKey(
        AgendaItem, null=True, blank=True, on_delete=models.CASCADE, 
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
        AgendaItem, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='agenda_file')
 
 
class AgendaNotes(models.Model):
    text = models.TextField()
    agenda = models.OneToOneField(
        AgendaItem, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='agenda_notes')


class AgendaResult(models.Model):
    VOTE_CHOICES = [
        ('approved', 'Angenommen'),
        ('denied', 'Abgelehnt'),
    ]

    agenda = models.OneToOneField(
        AgendaItem, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='agenda_result') 
    vote = models.CharField(
        max_length=20, choices=VOTE_CHOICES, null=True, blank=True)    
    votes_yes = models.PositiveIntegerField(null=True, blank=True)
    votes_no = models.PositiveIntegerField(null=True, blank=True)
    votes_abstention = models.PositiveIntegerField(null=True, blank=True)        
        

class MeetingFile(File):
    is_appendix = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, null=True, blank=True)
    meeting = models.ForeignKey(
        Meeting, null=True, blank=True, on_delete=models.CASCADE, 
        related_name='minutes_file')

    class Meta:        
        ordering = ['order', 'name']
