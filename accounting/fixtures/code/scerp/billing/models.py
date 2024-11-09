from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from app.models import AppModel, AppNote, AppAttachment, Client
from address.models import AddressModel, Inhabitant


class Route(AppModel, AppNote, AppAttachment):
    name = models.CharField(
        _('Name der Route'), max_length=100, default='Route 1',
        help_text=_("Name der Route für den Brunnenmeister"))
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name=_('Benutzer'),
        help_text=_("Brunnenmeister, Zählmeister etc."))
    note = models.TextField(_("Notiz"))

    def __str__(self):
        return prepare__str__(
            address=self.name, separator=f", {_('verantwortlich')}",
            last_name=self.user.last_name, first_name=self.user.first_name)

    class Meta:
        verbose_name = _('Adresse')
        verbose_name_plural = _('Adressen')


class Period(AppModel, AppNote, AppAttachment):
    name = models.CharField(_("Name"), max_length=200)
    start_date = models.DateTimeField(_("Start-Datum"))
    end_date = models.DateTimeField(_("End-Datum"))
    note = models.TextField(_("Notiz"))

    class Meta:
        verbose_name = _("Abrechnungsperiode")
        verbose_name_plural = _("Abrechnungsperioden")

    def __str__(self):
        return self.name

'''
Eichungen
Geräteserien
Messmodelle
Parametrierung
Standartlastprofile
Tarifzeiten
Zeitreihen
'''

class Subscriber(AppModel,  AppNote, AppAttachment):
    inhabitant_ref = models.ForeignKey(Inhabitant, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Meter(AppModel, AppNote, AppAttachment):
    meter_id = models.CharField('Meter ID', max_length=8, unique=True, help_text="Unique identifier for the meter")
    energytype = models.CharField('Energy Type', max_length=10, help_text="Type of energy")
    number = models.CharField('Number', max_length=50, help_text="Number associated with the meter")
    hint = models.CharField('Hint', max_length=100, help_text="Additional hint about the meter")
    address = models.ForeignKey(AddressModel, on_delete=models.CASCADE, help_text="Address associated with the meter")
    subscriber_ref = models.ForeignKey(Subscriber, on_delete=models.CASCADE, help_text="Subscriber associated with the meter")

    def __str__(self):
        return self.id

class Value(AppModel,  AppNote, AppAttachment):
    obiscode = models.CharField('Obis Code', max_length=9, help_text="Obis code for the meter reading")
    dateOld = models.DateField('Old Date', help_text="Date of old reading")
    old = models.DecimalField('Old Reading', max_digits=5, decimal_places=2, help_text="Old meter reading")
    min = models.DecimalField('Minimum Reading', max_digits=5, decimal_places=2, help_text="Minimum meter reading")
    max = models.DecimalField('Maximum Reading', max_digits=5, decimal_places=2, help_text="Maximum meter reading")
    dateCur = models.DateField('Current Date', help_text="Date of current reading")
    meter_ref = models.ForeignKey(Meter, on_delete=models.CASCADE, help_text="Meter associated with the reading")

    def __str__(self):
        return self.obiscode


class BillSetup(AppModel, AppNote, AppAttachment):
    name = models.CharField(_("Name"), max_length=200)
    rate = models.FloatField(_("Rate"))
    # additional fields...

    class Meta:
        verbose_name = _("Rechnungssetup")
        verbose_name_plural = _("Rechnungen - Setup")

    def __str__(self):
        return self.name
