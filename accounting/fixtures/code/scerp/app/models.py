'''
'''
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


# helpers
def get_current_user():
    return _user.value


def prepare__str__(**kwargs):
    """
    Prepares a string by concatenating together the `values` from the `kwargs`,
    and separating them by a provided `separator`. If `separator` is not provided 
    in `kwargs`, it defaults to a space (' '). The `separator` is reset to a space 
    after each usage, for the next possible iteration. Only elements with truthy 
    `values` are considered (i.e., elements that are not None or empty).
    
    For example:
    Given a call like prepare__str__(name = 'John', last = 'Miller', separator = ', ', job = 'Engineer')
    The function will return the string "John Miller, Engineer"
    """    
    str = ''
    separator = ' '
    for key, value in kwargs.items():        
        if key == 'separator':
            separator = value        
        elif value:
            if str:
                str += separator   
                separator = ' '                
            str += f'{value}'
    return str  


# Abstract Base Models and Client -------------------------------------------
class AppNote(models.Model):
    notes = models.TextField(_("Notizen"), null=True, blank=True)  
    
    class Meta:
        abstract = True


class AppAttachment(models.Model):
    attachment = models.FileField(
        upload_to='media/attachment/', null=True, blank=True,
        help_text="Datei")       
        
    class Meta:
        abstract = True


class LoggingModel(models.Model):   
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, related_name='%(app_label)s_%(class)s_created_by', 
        on_delete=models.SET_NULL, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User, related_name='%(app_label)s_%(class)s_modified_by', 
        on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):        
        if not self.id:
            self.created_by = get_current_user()
        self.modified_by = get_current_user()
        super().save(*args, **kwargs)


class Client(LoggingModel, AppNote, AppAttachment):
    name = models.CharField(max_length=250)
    logo = models.FileField(
        upload_to='media/logos/', null=True, blank=True,
        help_text="Logo, kann nur in CashCtrl hochgeladen werden")     
    uploaded = models.BooleanField(
        _("FiBu Upload"), default=False, help_text="Hochgeladen zur FiBu")
        
    uploaded = models.BooleanField(
        _("FiBu Upload"), default=False, help_text="Hochgeladen zur FiBu")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("1 Organisation")
        verbose_name_plural = _("1 Organisationen")


class AppModel(models.Model):
    '''this is the base model used for all records
    '''
    client = models.ForeignKey(
        Client, related_name='%(app_label)s_%(class)s_client', null=True, 
        on_delete=models.SET_NULL)    


# Admin -------------------------------------------------------
class Admin(AppModel, AppNote, AppAttachment): 
    org = models.CharField(
        max_length=250, unique=True, help_text="'org' name of FiBu")
    api_key = models.CharField(
        max_length=250, help_text="api_key für FiBu")
    cc_custom_fields = models.JSONField(default=dict)

    def __str__(self):
        return self.org

    class Meta:
        ordering = ['org']
        verbose_name = _("0 Admin Setup")
        verbose_name_plural = _("0 Admin Setups")


# App Models -------------------------------------------------------
class Location(AppModel, AppNote, AppAttachment):
    '''https://app.cashctrl.com/static/help/en/api/index.html#/location
    '''
    class LocationType(models.TextChoices):
        MAIN = 'MAIN', _('Hauptsitz')
        BRANCH = 'BRANCH', _('Nebensitz')
        OTHER = 'OTHER', _('MwSt')        
        STORAGE = 'STORAGE', _('Lager')
    
    type = models.CharField(
        _("Type"), max_length=10, choices=LocationType.choices, 
        default=LocationType.MAIN)
    name = models.CharField(max_length=250)
    address = models.CharField(max_length=250, null=True, blank=True)
    bic = models.CharField(max_length=11, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=3, null=True, blank=True)
    footer = models.TextField(null=True, blank=True)
    iban = models.CharField(max_length=32, null=True, blank=True)
    is_inactive = models.BooleanField(default=False)
    logo_file_id = models.IntegerField(null=True, blank=True)
    org_name = models.CharField(max_length=250, null=True, blank=True)
    qr_first_digits = models.IntegerField(null=True, blank=True)
    qr_iban = models.CharField(max_length=32, null=True, blank=True)
    vat_uid = models.CharField(max_length=32, null=True, blank=True)
    zip = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("1.1 Standort, UID")
        verbose_name_plural = _("1.1 Standorte, UIDs")
       