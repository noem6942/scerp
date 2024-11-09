from django.db import models
from django.utils.translation import gettext_lazy as _

from app.models import AppModel, AppNote, AppAttachment, Client


class FiscalPeriod(AppModel, AppNote, AppAttachment):
    class FiscalType(models.TextChoices):
        EARLIEST = 'EARLIEST', _('Earliest')
        LATEST = 'LATEST', _('Latest')    
       
    id_acc = models.PositiveIntegerField()
    org = models.CharField(max_length=250)
    end = models.DateField(
        _("Ende"), null=True, blank=True, 
        help_text=_("The end date of the fiscal period, if isCustom is set to "
                    "true, ignored otherwise."))
    start = models.DateField(
        _("Start"), null=True, blank=True, 
        help_text=_("The start date of the fiscal period, if isCustom is set "
                    "to true, ignored otherwise."))
    isCustom = models.BooleanField(
        default=False, 
        help_text=_("If true, create a custom fiscal period with start and "
                    "end date. type will be ignored. Defaults to false."))
    name = models.CharField(
        _("Name"), max_length=30, null=True, blank=True, 
        help_text=_("The name of the fiscal period, if isCustom is set to true, "
                    "ignored otherwise."))
    type = models.CharField(
        max_length=20, 
        choices=FiscalType.choices,         
        help_text=_("Creation type for creating a calendar year, if isCustom "
                    "is not set. Either LATEST, which will create the next "
                    "year after the latest existing year, or EARLIEST, which "
                    "will create the year before the earliest existing year. "
                    "Defaults to LATEST."))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Rechnungsperiode")
        verbose_name_plural = _("Rechnungsperioden")    


class AccountingSetup(AppModel, AppNote, AppAttachment):
    name = models.CharField(max_length=250)
    # not working
    # fiscalperiod = models.ForeignKey(
    #    FiscalPeriod, on_delete=models.CASCADE, related_name='accounting_setup',
    #    verbose_name=_('Rechnungsperiode'))    

    def __str__(self):
        return self.name 
 
    class Meta:
        ordering = ['name']
        verbose_name = _("Accounting Setup")
        verbose_name_plural = _("Accounting Setup")    


class Rounding(AppModel, AppNote, AppAttachment):
    name = models.CharField(max_length=250)
    def __str__(self):
        return self.name
 
    class Meta:
        ordering = ['name']
        verbose_name = _("Runden")
        verbose_name_plural = _("Runden")    
    
    
class Vat(AppModel, AppNote, AppAttachment):
    name = models.CharField(max_length=250)
    def __str__(self):
        return self.name
 
    class Meta:
        ordering = ['name']
        verbose_name = _("Mehrwertsteuer")
        verbose_name_plural = _("Mehrwertsteuer")    
    
    
class RevenueAccount(AppModel, AppNote, AppAttachment):
    name = models.CharField(max_length=250) 
    class Meta:
        ordering = ['name']
        verbose_name = _("Ertragskonto")
        verbose_name_plural = _("Ertragskonti")    


class AccountingSystem(AppModel, AppNote, AppAttachment):     
    name = models.CharField(max_length=250, default='CashCtrl')
    url = models.URLField(default='https://app.cashctrl.com/auth/login.html')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("System")
        verbose_name_plural = _("Systeme")