from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from accounting.models import Person
from core.models import (
    LogAbstract, TenantAbstract, Country, Address, Contact)
from scerp.admin import Display
from scerp.mixins import primary_language


'''
We lean the title and person model to cashctrl so we easily store it there.
'''
# Address ech
class AddressEch(LogAbstract):
    ''' Unique Address
    ech Standard eCH-0010 
        Datenstandard Postadresse für natürliche Personen, Firmen, 
        Organisationen und Behörden
    '''
    # address
    street = models.CharField(
        _('Address'), max_length=100, 
        help_text=_("Street")
    )
    house_number = models.CharField(
        _('House number'), max_length=50, blank=True, null=True,
        help_text=_("house number")
    )
    dwelling_number = models.CharField(
        _('Dwelling number'), max_length=30, blank=True, null=True,
        help_text=_("house number")
    )
    swiss_zip_code = models.PositiveSmallIntegerField(
        _('Swiss ZIP Code'), blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(9999)],
        help_text=_(
            "Von der Schweizer Post vergebene Postleitzahl in der Form, "
            "wie sie auf Briefen aufgedruckt wird.")
    )
    swiss_zip_code_add_on = models.PositiveSmallIntegerField(
        _('Swiss ZIP Code On'), blank=True, null=True,
        validators=[MinValueValidator(10000), MaxValueValidator(99999)],
        help_text=_(
            "Eindeutige, 5 stellige Schweizer Postleitzahl")
    )
    foreign_zip_code = models.CharField(
        _('Foreign ZIP Code'), max_length=20, blank=True, null=True,
        help_text=_("Ausländische Postleitzahl")
    )    
    town = models.CharField(
        _('City'), max_length=100,
        help_text=_("City of the address")
    )
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="%(class)s_country",
        verbose_name=_('Country'), default=Country.get_default_id,
        help_text=_("Country")
    )

    @property
    def zip(self):
        if self.swiss_zip_code:
            return self.swiss_zip_code
        elif self.foreign_zip_code:
            return f"{self.country.alpha2} {self.foreign_zip_code}"
        return None
        
    def __str__(self):
        return f"{self.country}, {self.zip} {self.city}, {address}"
        if self.swiss_zip_code:
            return (
                f"{self.swiss_zip_code} {self.town}, {self.street} "
                f"{self.house_number}")
        else:
            return (
                f"{self.country} {self.foreign_zip_code} {self.town}, "
                f"{self.street} {self.house_number}")

    def save(self, *args, **kwargs):
        if not self.zip:
            raise ValidationError(_("No zip code given."))
        
        # clean
        for field_name in ['street', 'house_number', 'dwelling_number']:
            value = getattr(self, field_name)
            if value:
                setattr(self, field_name, value.strip())
        
        super().save(*args, **kwargs)        

    class Meta:
        constraints = [
            models.UniqueConstraint(                
                fields=[
                    'country', 'swiss_zip_code', 'foreign_zip_code', 
                    'street', 'house_number', 'dwelling_number'],
                name='unique_address_ech'
            )
        ]             
        ordering = [
            'country', 'swiss_zip_code', 'foreign_zip_code', 'town', 'street',
            'house_number']
        verbose_name = _('eCH-Address Entry')
        verbose_name_plural = _('eCH-Addresses')        

"""
class PersonCrm(Person):
    '''
    We take this from accounting
    '''
    class Meta:
        proxy = True 


class Inhabitant(Person):
    '''
    A person who is an inhabitant.
    
    https://www.bfs.admin.ch/bfs/de/home/register/personenregister/registerharmonisierung/meldewesen-datenaustausch.html
    harm@bfs.admin.ch
    '''
    pass


class Employee(Person):
    '''own person, not related to subscriber or inhabitant
    '''
    job_title = models.CharField(max_length=100)
    hire_date = models.DateField()

    class Meta:
        ordering = [
            'last_name',
            'first_name',
            'date_birth'
        ]
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
"""

class Building(TenantAbstract):
    ''' Used to identify own buildings '''
    name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Building')
        verbose_name_plural = _('Buildings')


class AddressBuilding(TenantAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_building')
    building = models.ForeignKey(
        Building, verbose_name=_('Accounting Setup'),
        on_delete=models.CASCADE, related_name='%(class)s_building')
        

class Room(TenantAbstract):
    ''' Used to identify own rooms '''
    name = models.CharField(_('Name'), max_length=200)
    building = models.ForeignKey(
        Building, verbose_name=_('Building'),
        on_delete=models.CASCADE, related_name='%(class)s_building')
        
    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Building')
        verbose_name_plural = _('Buildings')


class ContactRoom(Contact):
    building = models.ForeignKey(
        Building, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_building')
