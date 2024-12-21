# core/models.py
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import Group, User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from scerp.locales import CANTON_CHOICES
from .mixins import validate_tenant, validate_tenant_setup


class CITY_CATEGORY(models.TextChoices):
    CITIZEN = ('B', _('Bürgergemeinde'))
    INHABITANTS = ('E', _('Einwohnergemeinde'))
    MUNICIPITY = ('G', _('Gemeinde'))
    CHURCH = ('K', _('Kirchgemeinde'))
    CITY = ('S', _('Stadt'))
    CORPORATION = ('Z', _('Zweckverband'))
    CANTON = ('C', _('Bürgergemeinde'))
    FEDERATION = ('F', _('Bund'))


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
        User, verbose_name=_('modified by'),
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
    protected = models.BooleanField(
        _('protected'), default=False,
        help_text=_('item must not be changed anymore'))
    is_inactive = models.BooleanField(
        _('is inactive'), default=False,
        help_text=_('item is not active anymore (but not permanently deleted)'),)

    @property
    def symbols(self):
        # add protection symbol to __str__
        ''' move to admin.py later '''
        symbols = ''
        if self.notes:
            symbols += ' \u270D'
        if self.attachment:
            symbols += ' \U0001F4CE'
        if self.protected:
            symbols += ' \U0001F512'
        if self.is_inactive:
            symbols += ' \U0001F6AB'

        return symbols

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
    is_trustee = models.BooleanField(
        _('is trustee'), default=False,
        help_text=_('Check if this is the trustee account that can created new tenants'))
    initial_user_email = models.EmailField(
        _('Email of initial user'), max_length=254, unique=True,
        help_text=_('Enter for creating initial user / admin'))
    initial_user_first_name = models.CharField(
        _('initial user first name'), max_length=30,
        help_text=_('Gets entered by system'))        
    initial_user_last_name = models.CharField(
        _('initial username last name'), max_length=30,
        help_text=_('Gets entered by system'))   
    initial_user_password = models.CharField(
        _('initial username password'), max_length=64, blank=True, null=True,
        help_text=_('Filled out by system'))

    def __str__(self):
        return self.name + self.symbols

    def clean(self):
        validate_tenant(self)
        super().clean()  # Call the parent's clean method

    class Meta:
        ordering = ['name']
        verbose_name = _('tenant')
        verbose_name_plural = _('tenants')


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
        
    def get_group_names(self):
        return [x.name for x in self.user.groups.all().order_by('name')]

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = _('User')
        verbose_name_plural =  _('Users')


class TenantAbstract(LogAbstract, NotesAbstract):
    ''' basic core model; for simplicity why make ALL models shown in the admin
        GUI Tenant Models
    '''
    tenant = models.ForeignKey(
        Tenant, verbose_name=_('tenant'), on_delete=models.CASCADE,
        related_name='%(class)s_tenant',
        help_text=_('assignment of tenant / client'))

    class Meta:
        abstract = True


class App(LogAbstract, NotesAbstract):
    ''' all available Apps
    '''
    name = models.CharField(max_length=100, unique=True)
    is_mandatory = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class TenantSetup(TenantAbstract):
    '''used for assign technical stuff
        gets automatically created after a Tenant has been created,
        see signals.py
    '''
    canton = models.CharField(
         _('canton'), max_length=2, choices=CANTON_CHOICES,
         null=True, blank=True)
    language = models.CharField(
        _('Language'), max_length=2, choices=settings.LANGUAGES, default='de',
        help_text=_('The main language of the person. May be used for documents.')
    )
    category = models.CharField(
         _('category'), max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True,
        help_text=_('category, add new one of no match'))
    apps = models.ManyToManyField(
        App, verbose_name=_('apps'), related_name='apps',
        help_text=_('all apps the tenant bought licences for'))
    groups = models.ManyToManyField(
        Group, verbose_name=_('groups'),
        help_text=_('groups used in this organization'))
    users = models.ManyToManyField(
        UserProfile, verbose_name=_('users'),
        help_text=_('users for this organization'))
    logo = models.ImageField(
        _('logo'), upload_to='profile_photos/',
        blank=True, null=True,
        help_text=_('logo used in website'))
    formats = models.JSONField(
        _('formats'), null=True, blank=True,
        help_text=_('format definitions'))

    def __str__(self):
        return self.tenant.name + self.symbols

    def clean(self):
        validate_tenant_setup(self)
        super().clean()

    class Meta:
        ordering = ['tenant__name']
        verbose_name = _('tenant setup')
        verbose_name_plural =  _('tenant setups')


class Year(TenantAbstract):
    # Define the year range directly with Min and Max validators
    year = models.PositiveSmallIntegerField(
        _("Year"),
        validators=[MinValueValidator(1900), MaxValueValidator(2099)],        
        help_text=_("Year available for data inputs, usually equal fiscal year")
    )

    def __str__(self):
        return str(self.year)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['year', 'tenant'],
                name='unique_year'
            )]    
        ordering = ('year',)
        verbose_name = _("Year")
        verbose_name_plural = _("Years")
