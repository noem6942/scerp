from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TenantAbstract
from .locales import COUNTER


class Counter(TenantAbstract):
    '''Municipality account chart
    '''
    class FUNCTION(models.TextChoices):        
        WATER = ('W', _('water'))
    
    class STATUS(models.TextChoices):        
        DISPOSED = ('D', _('disposed'))
        MOUNTED = ('M', _('mounted'))
        STOCK = ('S', _('stock'))
        
    nr = models.CharField(max_length=32)
    function = models.CharField(max_length=2, choices=FUNCTION.choices)
    zw = models.PositiveSmallIntegerField()
    jg = models.PositiveSmallIntegerField(null=True, blank=True)
    st = models.PositiveSmallIntegerField()
    currency = models.CharField(max_length=32, null=True, blank=True)
    size = models.CharField(max_length=8, null=True, blank=True)
    type = models.CharField(max_length=32, null=True, blank=True)
    calibration_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=2, choices=STATUS.choices)
    
    def __str__(self):
        return f'{self.nr}, {self.calibration_date}'
        
    class Meta:
        ordering = ['-jg', 'nr']



        
        

class Subscription(TenantAbstract):
    abo_nr = models.CharField(max_length=255, verbose_name="AboNr")  # Subscription Number
    r_empf = models.IntegerField(verbose_name="R-Empf.")  # Invoice Recipient
    pers_nr = models.IntegerField(verbose_name="PersNr.")  # Personal Number
    name_vorname = models.CharField(max_length=255, verbose_name="NameVorname")  # Name + First Name
    strasse = models.CharField(max_length=255, null=True, blank=True, verbose_name="Strasse")  # Street, currently some addresses for institutions are blank
    plz_ort = models.CharField(max_length=255, verbose_name="Plz Ort")  # Postal Code + City
    
    tarif = models.IntegerField(null=True, blank=True, verbose_name="Tarif") 
    periode = models.IntegerField(verbose_name="Periode")  # Period    
    tarif_bez = models.CharField(max_length=255, verbose_name="TarifBez")  # Subscription Number
    basis = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Quantity")  # Base Amount, sometimes None
    ansatz_nr = models.IntegerField(null=True, blank=True, verbose_name="AnsatzNr")  # Approach Number, sometimes blank
    ansatz = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Ansatz")  # Approach
    tage = models.IntegerField(null=True, blank=True, verbose_name="Tage")  # Days
    betrag = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Betrag")  # Amount
    inkl_mwst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="InklMwSt")  # Including VAT
    steuercode_zaehler = models.CharField(max_length=255, null=True, blank=True, verbose_name="SteuercodeZähler")  # Tax Code Meter
    berechnungs_code_zaehler = models.IntegerField(null=True, blank=True, verbose_name="BerechnungscodeZähler")  # Calculation Code Meter
    steuercode_gebuehren = models.CharField(max_length=255, null=True, blank=True, verbose_name="SteuercodeGebühren")  # Tax Code Fees
    berechnungs_code_gebuehren = models.CharField(max_length=255, null=True, blank=True, verbose_name="BerechnungscodeGebühren")  # Calculation Code Fees
    gebuehrentext = models.TextField(null=True, blank=True, verbose_name="Gebührentext")  # Fee Text
    gebuehren_zusatztext = models.TextField(null=True, blank=True, verbose_name="GebührenZusatztext")  # Additional Fee Text

    def __str__(self):
        return f"Invoice {self.abo_nr} - {self.name_vorname}"

    


"""
# Create your models here.
class PersonCategory:
    SUBSCRIBER_WATER = 'Water'

class Person(models.Model):
    nr = models.PositiveIntegerField() 0 # PersNr.
    categories = manytomany(Category)
    einzug = DateField
    auszug = DateField
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    zip = models.CharField(max_length=8)
    city = models.CharField(max_length=8)


class Building(models.Model):
    ...


class Location(models.Model):
    '''Lager, weggeworfen, montiert
    '''


class Periode(models.Model):
    nr = models.PositiveIntegerField()  # Tarif
    name = models.CharField(max_length=200)  # TarifBez
    date_from = 
    date_to = 


class FixedAssetCategory:
    SUBSCRIBER_WATER = 'Counter'


class Counter(models.Model):  
    Werk-Nr.
    Zählerart
    Status    
    Zähler-Nr.
    Zoll/mm    
    Zählwerke
    Jahrgang
    Stellen
    Eichdatum
    Losnummer
    Stand 1. Zw
    Typ
    Bemerkung
    
class Sparte
    A

class SubscriberBuildingAssignment(models.Model):
    subscriber = Foreign(Subscriber)
    building = Foreign(Subscriber)
    date_from =
    date_to =
    

class CounterBuildingAssignment(models.Model):    
    counter = 
    building = Foreign(Subscriber)
    date_from =
    date_to =
    montage_nr = 

    

    subscriber = Foreign(Building)
    date =
    nr = 
    sparte = ForeignField(Sparte)
    
    
    
    



    
    
    


    category = models.ForeignField(FixedAssetCategory)
    dateAdded
    categoryId
    dateDisposed
    locationId
    Zoll/mm
    St
    

class Calibrate(models.Model):  
    '''Counter '''
    asset = models.ForeignField(FixedAsset)
    date = 


class ArticleCategory(models.Model):
    Abwasser
    Wasser
    Gebühren (Mahngebürhen)
    Zinsen (Verzugszinsen)


class Article(models.Model):
    nr = models.PositiveIntegerField()  # Tarif
    name = models.CharField(max_length=200)  # TarifBez + Ansatz 1/2
    salesPrice = models.FloatField()
    unitId


class Article(models.Model):
    nr = models.PositiveIntegerField()  # Tarif
    name = models.CharField(max_length=200)  # TarifBez + Ansatz 1/2
    salesPrice = models.FloatField()
    unitId


class Subscription(models.Model):
    abo_nr = models.CharField(max_length=32)
    article = models.ForeignField(Subscriber)
    counter = models.ForeignField(Counter)
    subscriber = models.ForeignField(Person)
    billing_to = models.ForeignField(Person)
    perdiode = models.ForeignField(Periode)
    
"""    