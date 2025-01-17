# core/models.py
from django.conf import settings
from django.db import models
from django.contrib.auth.models import Group, User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from scerp.locales import CANTON_CHOICES


class LogAbstract(models.Model):
    '''used for time stamp handling
    '''
    created_at = models.DateTimeField(
        _('created at'), auto_now_add=True)
    created_by = models.ForeignKey(
        User, verbose_name=_('created by'),
        on_delete=models.CASCADE, related_name='%(class)s_created')
    modified_at = models.DateTimeField(
        _('modified at'), auto_now=True)
    modified_by = models.ForeignKey(
        User, verbose_name=_('modified by'), null=True, blank=True,
        on_delete=models.CASCADE, related_name='%(class)s_modified')

    class Meta:
        abstract = True  # This makes it an abstract model


class NotesAbstract(models.Model):
    '''handle notes and attachments
    '''
    notes = models.TextField(
        _('notes'), null=True, blank=True, help_text=_('notes to the record'))
    attachment = models.FileField(
        _('attachment'), upload_to='attachments/', blank=True, null=True,
        help_text=_('attachment for evidence'))
    version = models.ForeignKey(
        'self', verbose_name=_('version'), on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_previous_versions',
        help_text=_('previous_version'))
    is_inactive = models.BooleanField(
        _('is inactive'), default=False,
        help_text=_('item is not active anymore (but not permanently deleted)'),)
    is_protected = models.BooleanField(
        _('protected'), default=False,
        help_text=_('item must not be changed anymore'))

    def create_new_version(self, new_data):
        new_record = self.__class__.objects.create(
            data=new_data, version=self)
        # Inactivate the existing record
        existing_record.is_active = False
        existing_record.save()
        return new_record

    def get_record_history(self):
        record = self
        history = []
        while record.version:
            record = self.__class__.objects.filter(
                id=previous_version.id).first()
            if record:
                records.append(record)
        return history

    class Meta:
        abstract = True  # This makes it an abstract model


class App(LogAbstract, NotesAbstract):
    ''' all available Apps
    '''
    MANDATORY_APPS = ['core', 'crm']    
    name = models.CharField(max_length=100, unique=True)
    verbose_name = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def is_mandatory(self):
        return self.name in self.MANDATORY_APPS

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Tenant(LogAbstract, NotesAbstract):
    '''only admin and trustees are allowed to create Tenants
        sends signals after creation!
    '''
    name = models.CharField(
        _('name'), max_length=100, unique=True)
    code = models.CharField(
        _('code'), max_length=32, unique=True,
        help_text=_(
            'code of tenant / client, unique, max 32 characters, '
            'only small letters, should only contains characters that '
            'can be displayed in an url)'))
    apps = models.ManyToManyField(
        App, verbose_name=_('apps'), 
        related_name='%(class)s_apps', 
        help_text=_('apps subscribed'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _('tenant')
        verbose_name_plural = _('tenants')


class Message(LogAbstract, NotesAbstract):
    '''only admin and trustees are allowed to create Tenants
        sends signals after creation!
    '''
    class Severity(models.TextChoices):
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')
        
    name = models.CharField(_('name'), max_length=100)
    text = models.TextField(_('text'))        
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
        verbose_name=_("Severity"),
        help_text=_("Current status of the meeting.")
    )
    recepients = models.ManyToManyField(
        Tenant, verbose_name=_('recepients'), 
        related_name='%(class)s_tenant', 
        help_text=_('empty if all recepients'))
        
    def __str__(self):
        return f"{self.name}, {self.modified_at}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['is_inactive', 'name'],
                name='unique_name'
            )]    
        ordering = ['is_inactive', '-modified_at']
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')


class UserProfile(LogAbstract, NotesAbstract):
    user = models.OneToOneField(
        User, verbose_name=_('User'), on_delete=models.CASCADE,
        related_name='profile', 
        help_text=_(
            "Registered User. Click the 'pencil' to assign the user to groups"))
    photo = models.ImageField(
        _('photo'), upload_to='profile_photos/', blank=True, null=True,
        help_text=_('Load up your personal photo.'))

    def __str__(self):
        return f'{self.user.last_name.upper()}, {self.user.first_name}'
        
    @property    
    def groups(self):
        return self.user.groups.all().order_by('name')

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = _('User')
        verbose_name_plural =  _('Users')


class TenantAbstract(LogAbstract, NotesAbstract):
    ''' basic core model; for simplicity we make ALL models shown in the admin
        GUI Tenant Models
    '''
    tenant = models.ForeignKey(
        Tenant, verbose_name=_('tenant'), on_delete=models.CASCADE,
        related_name='%(class)s_tenant',
        help_text=_('assignment of tenant / client'))

    class Meta:
        abstract = True


class TenantSetup(TenantAbstract):
    '''used for assign technical stuff
        gets automatically created after a Tenant has been created,        
    '''
    class TYPE(models.TextChoices):
        CITIZEN = ('B', _('Bürgergemeinde'))
        INHABITANTS = ('E', _('Einwohnergemeinde'))
        MUNICIPITY = ('G', _('Gemeinde'))
        CHURCH = ('K', _('Kirchgemeinde'))
        CITY = ('S', _('Stadt'))
        CORPORATION = ('Z', _('Zweckverband'))
        CANTON = ('C', _('Bürgergemeinde'))
        FEDERATION = ('F', _('Bund'))
        TRUSTEE = ('T', _('Trustee'))    
        
    canton = models.CharField(
         _('canton'), max_length=2, choices=CANTON_CHOICES,
         null=True, blank=True)
    language = models.CharField(
        _('Language'), max_length=2, choices=settings.LANGUAGES, default='de',
        help_text=_('The main language of the person. May be used for documents.')
    )
    type = models.CharField(
         _('Type'), max_length=1, choices=TYPE.choices,
        null=True, blank=True,
        help_text=_('Type, add new one of no match'))
    formats = models.JSONField(
        _('formats'), null=True, blank=True,
        help_text=_('Format definitions'))
    users = models.ManyToManyField(
        User, verbose_name=_('Users'), 
        related_name='%(class)s_users', 
        help_text=_('users subscribed'))        

    def __str__(self):
        return self.tenant.name

    @property
    def logo(self):
        logo = TenantLogo.objects.filter(
            tenant=self.tenant, type=TenantLogo.Type.MAIN).first()
        if logo:
            return logo.logo
        return None
        
    @property    
    def groups(self):        
        groups = set()
        for user in self.users.all():
            for group in user.groups.all():
                groups.add(group)
        return groups

    class Meta:
        ordering = ['tenant__name']
        verbose_name = _('tenant setup')
        verbose_name_plural =  _('tenant setups')


class TenantLogo(TenantAbstract):
    '''used for logos for all apps 
        has signals
    '''
    class Type(models.TextChoices):
        MAIN = "MAIN", _("Main")
        OTHER = "OTHER", _("Other")
        
    name = models.CharField(
        _('name'), max_length=100, unique=True)
    type = models.CharField(
        _("Type"), max_length=50, choices=Type.choices, default=Type.MAIN,
        help_text=_("The type of logo. Defaults to MAIN."))
    logo = models.ImageField(
        _('logo'), upload_to='profile_photos/',
        blank=True, null=True,
        help_text=_('logo used in website'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['tenant__name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='unique_tenant_name'
            )
        ]           
        verbose_name = _('tenant logo')
        verbose_name_plural =  _('tenant logos')
