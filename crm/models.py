from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from scerp.locales import COUNTRY_CHOICES, LANGUAGE_CHOICES
from core.models import TenantAbstract

from django.db import models
from django.core.validators import ValidationError


class PersonCategory(TenantAbstract): 
    name = models.JSONField(        
        help_text=("The name of the category. Can contain localized text in XML format: <values><de>German text</de><en>English text</en></values>")
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=("Discount percentage for this category, between 0.0 and 100.0.")
    )
    parent_id = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name="subcategories",
        help_text=("ID of the parent category.")
    )
    sequence_nr_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=("ID of the sequence number. Inherits from parent category if empty.")
    )   

    def __str__(self):
        return self.name

class PersonAccount(TenantAbstract):  
    '''full person profile as exported to Accounting
    '''
    company = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=('Company'),
        help_text=('The name of the organization/company. Either firstName, lastName or company must be set.')
    )
    first_name = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=('First Name'),
        help_text=('The person\'s first (given) name. Either firstName, lastName or company must be set.')
    )
    last_name = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=('Last Name'),
        help_text=('The person\'s last (family) name. Either firstName, lastName or company must be set.')
    )
    altName = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=('Alternative Name'),
        help_text=('An alternative name for this person (for organizational chart). Can contain localized text.')
    )    
    contacts = models.ManyToManyField(
        'self', 
        verbose_name=('Contacts'),
        blank=True,
        help_text=('A list of contact information (e-mail, phone, url, etc.).')
    )
    birth_date = models.DateField(
        blank=True, 
        null=True, 
        verbose_name=('Date of Birth'),
        help_text=('The person\'s date of birth (Format: DD.MM.YYYY).')
    )
    notes = models.TextField(
        null=True,
        blank=True, 
        verbose_name=('Notes'),
        help_text=('Some optional notes. This can contain limited HTML for styling.')
    )
    department = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=('Department'),
        help_text=('The department of the person within the company.')
    )
    discountPercentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name=('Discount Percentage'),
        help_text=('Discount percentage for this person, which may be used for orders.')
    )
    iban = models.CharField(
        max_length=32, 
        blank=True, 
        null=True, 
        verbose_name=('IBAN'),
        help_text=('The IBAN (International Bank Account Number) of the person.')
    )
    industry = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=('Industry'),
        help_text=('The industry of the company or the trade/vocation of the person.')
    )
    isInactive = models.BooleanField(
        default=False,
        verbose_name=('Is Inactive'),
        help_text=('Mark the person as inactive. The person will be greyed out and no longer suggested.')
    )
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, blank=True, null=True,
        verbose_name=('Language'),
        help_text=('The main language of the person. May be used for documents.')
    )
    notes = models.TextField(
        blank=True, 
        verbose_name=('Notes'),
        help_text=('Some optional notes. This can contain limited HTML for styling.')
    )
    nr = models.CharField(
        max_length=50,
        blank=True, 
        null=True, 
        verbose_name=('Person Number'),
        help_text=('The person number (e.g., customer no.).')
    )
    sequenceNumberId = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name=('Sequence Number ID'),
        help_text=('The ID of the sequence number used to generate the person number (see nr).')
    )
    superiorId = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name=('Superior ID'),
        help_text=('The superior of this person (for organizational chart).')
    )
    titleId = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name=('Title ID'),
        help_text=('The person\'s title (e.g. \'Mr.\', \'Mrs.\', \'Dr.\').')
    )
    category = models.ManyToManyField(PersonCategory)

    def save(self, *args, **kwargs):
        # Validate_person
        if not self.first_name and not self.last_name and not self.company:
            raise ValidationError(('Either First Name, Last Name or Company must be set.'))
        super().save(*args, **kwargs)      
    '''   
    def __str__(self):
        name = ''
        if self.company:
            name += self.company + ': '
        if self.first_name or self.last_name:
            name += f'{self.last_name}, {self.first_name}'
        if self.birth_date:
            name += f', {self.birth_date}'
        return self.last_name
    '''

class AddressAbstract(TenantAbstract):
    class CountryChoices(models.TextChoices):
        CHE = 'CHE', ('Schweiz')
     
    # Part cashCtrl 
    address = models.CharField(
        max_length=200,
        null=True,
        blank=True,         
        verbose_name=('Address'),
        help_text=('The address (street, house number, additional info). Can contain multiple lines.')
    )
    zip = models.CharField(
        max_length=10,
        null=True, 
        blank=True, 
        verbose_name=('Postal Code'),
        help_text=('The postal code of the address.')
    )    
    city = models.CharField(
        max_length=100,
        null=True,
        blank=True, 
        verbose_name=('City/Town'),
        help_text=('The town/city of the address.')
    )
    country = models.CharField(
        max_length=2, 
        choices=COUNTRY_CHOICES, blank=True, null=True,
        verbose_name=('Language'),
        help_text=('The main language of the person. May be used for documents.')
    )
    
    # Part scerp
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField(default='2099-12-31')    

    def __str_(self):
        return prepare__str_(
            address=self.address, separator=', ', zip=self.zip, city=self.city)

    class Meta:
        abstract = True
  
  
class AddressPerson(AddressAbstract):        
    class TypeChoices(models.TextChoices):
        MAIN = 'MAIN', ('Main address')
        INVOICE = 'INVOICE', ('Invoice address')
        DELIVERY = 'DELIVERY', ('Delivery address')
        OTHER = 'OTHER', ('Other')
    type = models.CharField(
        max_length=15, 
        choices=TypeChoices.choices,
        verbose_name=('Type of address'),
        default=TypeChoices.MAIN,
        help_text=('The type of address. Possible values: Main address, Invoice address, Delivery address, Other.')
    )
    person = models.ForeignKey(
        PersonAccount,
        on_delete=models.CASCADE,  # Specify the behavior on delete
        help_text="Filled out automatically"
    )        
    
        
class Contact(TenantAbstract):
    class ContactType(models.TextChoices):
        EMAIL_INVOICE = 'EMAIL_INVOICE', 'Invoice Email'
        EMAIL_WORK = 'EMAIL_WORK', 'Work Email'
        EMAIL_PRIVATE = 'EMAIL_PRIVATE', 'Private Email'
        PHONE_RECEPTION = 'PHONE_RECEPTION', 'Reception Phone'
        PHONE_WORK = 'PHONE_WORK', 'Work Phone'
        PHONE_PRIVATE = 'PHONE_PRIVATE', 'Private Phone'
        MOBILE_WORK = 'MOBILE_WORK', 'Work Mobile'
        MOBILE_PRIVATE = 'MOBILE_PRIVATE', 'Private Mobile'
        FAX = 'FAX', 'Fax'
        WEBSITE = 'WEBSITE', 'Website'
        MESSENGER = 'MESSENGER', 'Messenger'
        OTHER = 'OTHER', 'Other'

    type = models.CharField(
        max_length=16, choices=ContactType.choices,        
        help_text=('The type of address. Possible values: Main address, Invoice address, Delivery address, Other.')
    )
    address = models.CharField(max_length=200)
    person = models.ForeignKey(
        PersonAccount,
        on_delete=models.CASCADE,  # Specify the behavior on delete
        help_text="Filled out automatically"
    )    
    
    
class Building(AddressAbstract):
    class TypeChoices(models.TextChoices):
        MAIN = 'MAIN', ('Main address')
        ROOM = 'ROOM', ('Room address')
    name = models.CharField(max_length=200, blank=True, null=True)
    type = models.CharField(
        max_length=15, 
        choices=TypeChoices.choices,
        verbose_name=('Type of address'),
        default=TypeChoices.MAIN,
        help_text=('The type of address. Possible values: Main address, Invoice address, Delivery address, Other.')
    )
    
    def __str__(self):
        return f"{self.name}, {self.address}"
