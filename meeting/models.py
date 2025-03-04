from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _

# from core.models import TenantAbstract, to be done later
from core.models import Building
from vault.models import Status


from django.db import models
from django.utils.translation import gettext_lazy as _


class Meeting(models.Model):
    # Core fields
    name = models.CharField(
        max_length=255,
        verbose_name=_("Meeting Name"),
        help_text=_("The name of the meeting.")
    )
    committee = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='committee',
        verbose_name=_("Committee"),
        help_text=_("The committee responsible for the meeting.")
    )
    date = models.DateField(
        verbose_name=_("Meeting Date"),
        help_text=_("The date of the meeting.")
    )
    opening_time = models.DateTimeField(
        verbose_name=_("Opening Time"),
        help_text=_("The date and time the meeting starts.")
    )
    closing_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Closing Time"),
        help_text=_("The date and time the meeting ends.")
    )
    venue = models.ForeignKey(
        Building, null=True, blank=True, on_delete=models.CASCADE,
        related_name='meeting',
        verbose_name=_("Venue"),
        help_text=_("The venue where the meeting is held.")
    )

    # Status field
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.INITIALIZATION,
        verbose_name=_("Meeting Status"),
        help_text=_("Current status of the meeting.")
    )

    # Details
    president = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='president',
        verbose_name=_("President"),
        help_text=_("The president presiding over the meeting.")
    )
    secretary = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='secretary',
        verbose_name=_("Secretary"),
        help_text=_("The secretary responsible for documenting the meeting.")
    )

    def __str__(self):
        return f"{self.name}, {self.date}"

    class Meta:
        ordering = ['-date', 'committee']
        verbose_name = _("Meeting")
        verbose_name_plural = _("Meetings")


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
