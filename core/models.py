# core/models.py
from django.db import models
from django.contrib.auth.models import Group, User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from scerp.mixins import display_photo
from scerp.locales import CANTON_CHOICES, LANGUAGE_CHOICES

from .locales import (
    APP, LOG_ABSTRACT, TENANT, TENANT_ABSTRACT, NOTES_ABSTRACT, 
    TENANT_SETUP, USER_PROFILE)
from .mixins import TenantMixin


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
        auto_now_add=True, **LOG_ABSTRACT.Field.created_at)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='%(class)s_created',
        **LOG_ABSTRACT.Field.created_by)
    modified_at = models.DateTimeField(
        auto_now=True, **LOG_ABSTRACT.Field.modified_at)
    modified_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='%(class)s_modified', 
        **LOG_ABSTRACT.Field.modified_by)
              
    class Meta:
        abstract = True  # This makes it an abstract model


class NotesAbstract(models.Model):
    '''handle notes and attachments
    '''
    notes = models.TextField(
        null=True, blank=True, **NOTES_ABSTRACT.Field.notes)
    attachment = models.FileField(
        upload_to='attachments/', blank=True, null=True, 
        **NOTES_ABSTRACT.Field.attachment)
    version = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='%(class)s_previous_versions',
        **NOTES_ABSTRACT.Field.version)
    protected = models.BooleanField(
        default=False, **NOTES_ABSTRACT.Field.protected)     
    inactive = models.BooleanField(
        default=False, **NOTES_ABSTRACT.Field.inactive)
    
    @property
    def symbols(self):
        # add protection symbol to __str__
        symbols = ''
        if self.notes:
            symbols += ' \u270D'
        if self.attachment:
            symbols += ' \U0001F4CE'
        if self.protected:
            symbols += ' \U0001F512'
        if self.inactive:
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


class Tenant(LogAbstract, NotesAbstract, TenantMixin):
    '''only admin and trustees are allowed to create Tenants
        sends signals after creation!
    '''
    name = models.CharField(
        max_length=100, unique=True, **TENANT.Field.name)
    code = models.CharField(
        max_length=32, unique=True, **TENANT.Field.code)
    is_trustee = models.BooleanField(
        default=False, **TENANT.Field.is_trustee)
    
    def __str__(self):
        return self.name + self.symbols
 
    def clean(self):
        super().clean()  # Call the parent's clean method
        self.clean_related_data()
 
    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if this is a new instance
        super().save(*args, **kwargs)  # Call the real save method
        if is_new:
            self.post_save(*args, **kwargs)
 
    class Meta:
        ordering = ['name']
        verbose_name = TENANT.verbose_name
        verbose_name_plural = TENANT.verbose_name_plural
        

class UserProfile(LogAbstract, NotesAbstract):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile',
        **USER_PROFILE.Field.user)
    photo = models.ImageField(
        upload_to='profile_photos/', blank=True, null=True,
        **USER_PROFILE.Field.photo)
 
    def __str__(self):
        return f'{self.user.last_name.upper()}, {self.user.first_name}'
 
    def display_photo(self):
        return display_photo(self.photo)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = USER_PROFILE.verbose_name
        verbose_name_plural = USER_PROFILE.verbose_name_plural  
        

class TenantAbstract(LogAbstract, NotesAbstract):
    ''' basic core model; for simplicity why make ALL models shown in the admin
        GUI Tenant Models
    '''
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='%(class)s_tenant', 
        **TENANT_ABSTRACT.Field.tenant)

    class Meta:
        abstract = True 


class TenantSetup(TenantAbstract):    
    '''used for assign technical stuff
        gets automatically created after a Tenant has been created, 
        see signals.py
    '''
    def init_tenant_setup_format():    
        return TENANT_SETUP_FORMAT
        
    canton = models.CharField(
        max_length=2, choices=CANTON_CHOICES, null=True, blank=True, 
        **TENANT_SETUP.Field.canton)
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, default='de',
        verbose_name=('Language'),
        help_text=('The main language of the person. May be used for documents.')
    )
    category = models.CharField(
        max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True, **TENANT_SETUP.Field.category)        
    users = models.ManyToManyField(
        UserProfile, **TENANT_SETUP.Field.users)
    logo = models.ImageField(
        upload_to='profile_photos/', 
        blank=True, null=True, **TENANT_SETUP.Field.logo)
    formats = models.JSONField(
         default=init_tenant_setup_format, null=True, blank=True, 
         **TENANT_SETUP.Field.formats)
    
    def __str__(self):
        return self.tenant.name + self.symbols
    
    def display_logo(self):
        return display_photo(self.logo)
    
    class Meta:
        ordering = ['tenant__name']
        verbose_name = TENANT_SETUP.verbose_name
        verbose_name_plural = TENANT_SETUP.verbose_name_plural
