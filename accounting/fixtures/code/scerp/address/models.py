'''
'''
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .geo_mapping import GeoAdmin
from .validations import validate_person
from app.models import AppModel, AppNote, AppAttachment, Client
from scerp.locale_global import LANGUAGE_CHOICES

# mixins
def show_user__str__(user):
    return f'{user.username}: {user.last_name}, {user.first_name}'    


class AddressModel(AppModel, AppNote, AppAttachment):
    
    class TypeChoices(models.TextChoices):
        MAIN = 'MAIN', _('Main address')
        INVOICE = 'INVOICE', _('Invoice address')
        DELIVERY = 'DELIVERY', _('Delivery address')
        OTHER = 'OTHER', _('Other')

    class CountryChoices(models.TextChoices):
        CHE = 'CHE', _('Schweiz')
     
    # Part cashCtrl 
    type = models.CharField(
        max_length=15, 
        choices=TypeChoices.choices,
        verbose_name=_('Type of address'),
        help_text=_('The type of address. Possible values: Main address, Invoice address, Delivery address, Other.')
    )
    address = models.TextField(
        null=True,
        blank=True, 
        verbose_name=_('Address'),
        help_text=_('The address (street, house number, additional info). Can contain multiple lines.')
    )
    house = models.CharField(
        max_length=10,
        null=True, 
        blank=True, 
        verbose_name=_('Gebäudebeschreibung'),
        help_text=_('Hausbeschreibung, z.B. wie 12-MFH für Wasser- oder Stromzählung')
    )    
    hint = models.TextField(
        null=True,
        blank=True, 
        verbose_name=_('Hinweise'),
        help_text=_('Hinweise wie z.B. zur Wasser- oder Stromzählung')
    )    
    zip = models.CharField(
        max_length=10,
        null=True, 
        blank=True, 
        verbose_name=_('Postal Code'),
        help_text=_('The postal code of the address.')
    )    
    city = models.CharField(
        max_length=100,
        null=True,
        blank=True, 
        verbose_name=_('City/Town'),
        help_text=_('The town/city of the address.')
    )
    country = models.CharField(
        max_length=3,
        null=True, 
        blank=True, 
        choices=CountryChoices.choices,
        default=CountryChoices.CHE,
        verbose_name=_('Country'),
        help_text=_('The country of the address in ISO Alpha-3 Codes.')
    )
    
    # Part scerp
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField(default='2099-12-31')

    def __str__(self):
        return prepare__str__(
            address=self.address, separator=', ', zip=self.zip, city=self.city)

    class Meta:
        verbose_name = _('Adresse')
        verbose_name_plural = _('Adressen')
         
        
class BasePerson(AppModel, AppAttachment):  
    company = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Company'),
        help_text=_('The name of the organization/company. Either firstName, lastName or company must be set.')
    )
    first_name = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('First Name'),
        help_text=_('The person\'s first (given) name. Either firstName, lastName or company must be set.')
    )
    last_name = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Last Name'),
        help_text=_('The person\'s last (family) name. Either firstName, lastName or company must be set.')
    )
    altName = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Alternative Name'),
        help_text=_('An alternative name for this person (for organizational chart). Can contain localized text.')
    )
    custom = models.JSONField(
        blank=True, 
        null=True, 
        verbose_name=_('Custom field values'),
        help_text=_('Custom field values. Stored as JSON.')
    )
    contacts = models.ManyToManyField(
        'self', 
        verbose_name=_('Contacts'),
        blank=True,
        help_text=_('A list of contact information (e-mail, phone, url, etc.).')
    )
    birth_date = models.DateField(
        blank=True, 
        null=True, 
        verbose_name=_('Date of Birth'),
        help_text=_('The person\'s date of birth (Format: DD.MM.YYYY).')
    )
    notes = models.TextField(
        null=True,
        blank=True, 
        verbose_name=_('Notes'),
        help_text=_('Some optional notes. This can contain limited HTML for styling.')
    )
    department = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=_('Department'),
        help_text=_('The department of the person within the company.')
    )
    discountPercentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name=_('Discount Percentage'),
        help_text=_('Discount percentage for this person, which may be used for orders.')
    )
    iban = models.CharField(
        max_length=32, 
        blank=True, 
        null=True, 
        verbose_name=_('IBAN'),
        help_text=_('The IBAN (International Bank Account Number) of the person.')
    )
    industry = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Industry'),
        help_text=_('The industry of the company or the trade/vocation of the person.')
    )
    isInactive = models.BooleanField(
        default=False,
        verbose_name=_('Is Inactive'),
        help_text=_('Mark the person as inactive. The person will be greyed out and no longer suggested.')
    )
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGES, blank=True, null=True,
        verbose_name=('Language'),
        help_text=('The main language of the person. May be used for documents.')
    )
    notes = models.TextField(
        blank=True, 
        verbose_name=_('Notes'),
        help_text=_('Some optional notes. This can contain limited HTML for styling.')
    )
    nr = models.CharField(
        max_length=50,
        blank=True, 
        null=True, 
        verbose_name=_('Person Number'),
        help_text=_('The person number (e.g., customer no.).')
    )
    position = models.CharField(
        max_length=100,
        blank=True, 
        null=True, 
        verbose_name=_('Position'),
        help_text=_('The position (job title) of the person within the company.')
    )
    sequenceNumberId = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Sequence Number ID'),
        help_text=_('The ID of the sequence number used to generate the person number (see nr).')
    )
    superiorId = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Superior ID'),
        help_text=_('The superior of this person (for organizational chart).')
    )
    titleId = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name=_('Title ID'),
        help_text=_('The person\'s title (e.g. \'Mr.\', \'Mrs.\', \'Dr.\').')
    )
    
    def __str__(self):
        return prepare__str__(
            company=self.company, last_name=self.last_name, 
            first_name=self.first_name, separator=', ',
            birth_date=self.birth_date)
    
    class Meta:
        abstract = True       
        
        
class Person(BasePerson, AppModel, AppAttachment):        
    '''synchronized with cashCtrl
    '''
    addresses = models.ManyToManyField(
        AddressModel, related_name='person_addresses')

    class Meta:
        ordering = ['last_name', 'first_name', 'company']
        verbose_name = _('Person')
        verbose_name_plural = _('Personen')          
 
    def save(self, *args, **kwargs):
        validate_person(self.first_name, self.last_name, self.company)
        super(Person, self).save(*args, **kwargs)
 
        
class Employee(BasePerson, AppModel, AppAttachment):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    addresses = models.ManyToManyField(
        AddressModel, related_name='employee_addresses')
    
    # additional fields
    employee_id = models.CharField(max_length=100)
    date_hired = models.DateField()

    def __str__(self):
        return show_user__str__(self.user)
 
    class Meta:
        # ordering = ['user__last_name', 'user__first_name']
        verbose_name = _("2.1 Mitarbeitende")
        verbose_name_plural = _("2.1 Mitarbeitende")           
        
        
class Trustee(BasePerson, AppModel, AppAttachment):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    addresses = models.ManyToManyField(
        AddressModel, related_name='trustee_addresses')
    # additional fields
    trustee_id = models.CharField(max_length=100)
    
    # You can specify the date that the person became a trustee
    date_created = models.DateField()

    def __str__(self):
        return show_user__str__(self.user)
 
    class Meta:
        # ordering = ['user__last_name', 'user__first_name']
        verbose_name = _("2.2 Externe")
        verbose_name_plural = _("2.2 Externe")    


class Inhabitant(BasePerson, AppModel, AppAttachment):
    addresses = models.ManyToManyField(
        AddressModel, related_name='inhabitant_addresses')
    def __str__(self):
        return self.name
        
    class Meta:
        # ordering = ['name']
        verbose_name = _("Einwohner")
        verbose_name_plural = _("Einwohner")

        
class Building(AppModel, AppNote, AppAttachment):
    address = models.ForeignKey(
        AddressModel, 
        on_delete=models.CASCADE, 
        related_name='building_addresses')

    def __str__(self):
        return show_user__str__(self.user)
 
    class Meta:
        # ordering = ['user__last_name', 'user__first_name']
        verbose_name = _("2.2 Externe")
        verbose_name_plural = _("2.2 Externe")    
        
        
class GeoSettings(AppModel, AppNote, AppAttachment):
    '''see https://map.geo.admin.ch/#/map?lang=de&center=2679861.44,1250977.95&z=8&bgLayer=ch.swisstopo.pixelkarte-farbe&topic=ech&swisssearch=250978.09375,679860.5&layers=ch.swisstopo.zeitreihen@year=1864,f;ch.bfs.gebaeude_wohnungs_register,f;ch.bav.haltestellen-oev,f;ch.swisstopo.swisstlm3d-wanderwege,f;ch.vbs.schiessanzeigen,f;ch.astra.wanderland-sperrungen_umleitungen,f
    '''
    class GeoSettingsType(models.TextChoices):
        MAP_GEO_ADMIN = 'MAP_GEO_ADMIN', _('Schweizerische Eidgenossenschaft - map.geo.admin.ch')
      
    type = models.CharField(
        _("Type"), max_length=30, choices=GeoSettingsType.choices, 
        default=GeoSettingsType.MAP_GEO_ADMIN)        
    name = models.CharField(max_length=250)
    config = models.JSONField(default=GeoAdmin.map_init)
    is_inactive = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("1.2 Geo Einstellungen")
        verbose_name_plural = _("1.2 Geo Einstellungen")       
        