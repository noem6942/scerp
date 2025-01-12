from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from scerp.locales import COUNTRY_CHOICES
from core.models import TenantAbstract

from django.db import models
from django.core.validators import ValidationError


'''
We lean the title and person model to cashctrl so we easily store it there.
'''
class PersonCategory(TenantAbstract):
    """Model to represent a person's category.
    not used: parentId
    """
    name = models.JSONField(
        _('name'), 
        help_text=_("The name of the category.")
    )
    discount_percentage = models.FloatField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0.0, message=_("Discount percentage must be at least 0.")),
            MaxValueValidator(100.0, message=_("Discount percentage cannot exceed 100."))
        ],
        help_text=_(
            "Discount percentage for this person, which may be used for orders. "
            "This can also be set on the category for all people in that category."
        ),
    )       
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="parents",
        verbose_name=_('Superior'),
        help_text=_("The ID of the parent category. Currently not used")
    ) 

    def __str__(self):
        return self.name
     

class Title(TenantAbstract):
    """Model to represent a person's title."""
    class GENDER(models.TextChoices):
        # CashCtrl
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        # Others        

    name = models.JSONField(
        _('name'), 
        blank=True,  null=True,  # null necessary to handle multi languages
        help_text=_("The name of the title (i.e. the actual title).")
    )
    gender = models.CharField(
        max_length=6,
        choices=GENDER.choices,
        blank=True,
        null=True,
        help_text=_("The person's biological gender (male or female). Possible values: MALE, FEMALE.")
    )
    sentence = models.JSONField(
        _('Sentence'), 
        blank=True,  null=True,  # null necessary to handle multi languages
        help_text=_("The letter salutation (e.g. 'Dear Mr.', etc.). May be used in mail.")
    )

    def __str__(self):
        for lang_code, lang_name in settings.LANGUAGES:
            if self.name.get(lang_code):
                return self.name[lang_code]
        return None
     

class Address(TenantAbstract):
    # Address Types Enum (choices for the 'type' field)
    class AddressType(models.TextChoices):
        # CashCtrl
        MAIN = 'MAIN', _('Main Address')
        INVOICE = 'INVOICE', _('Invoice Address')
        DELIVERY = 'DELIVERY', _('Delivery Address')
        OTHER = 'OTHER', _('Other Address')
        # Others

    type = models.CharField(
        max_length=10, choices=AddressType.choices, default=AddressType.MAIN,
        help_text=_("The type of address: MAIN, INVOICE, DELIVERY, OTHER.")
    )
    address = models.TextField(
        _('Address'),
        help_text=_("Street, house number, additional address information.")
    )
    zip = models.CharField(
        max_length=20, blank=True, null=True, 
        help_text=_("Postal code for the address")
    )
    city = models.CharField(
        max_length=100, blank=True, null=True, 
        help_text=_("City of the address")
    )
    country = models.CharField(
        max_length=3, blank=True, null=True, default='CHE',
        help_text=_("3-letter country code")
    )

    def __str__(self):
        return f"{self.type} Address"

    class Meta:
        ordering = ['type', 'address']
        verbose_name = _('Address Entry')
        verbose_name_plural = _('Addresses')


class Contact(TenantAbstract):    
    
    class ContactType(models.TextChoices):
        # CashCtrl
        EMAIL_INVOICE = 'EMAIL_INVOICE', _('Invoice Email')
        EMAIL_WORK = 'EMAIL_WORK', _('Work Email')
        EMAIL_PRIVATE = 'EMAIL_PRIVATE', _('Private Email')
        PHONE_RECEPTION = 'PHONE_RECEPTION', _('Reception Phone')
        PHONE_WORK = 'PHONE_WORK', _('Work Phone')
        PHONE_PRIVATE = 'PHONE_PRIVATE', _('Private Phone')
        MOBILE_WORK = 'MOBILE_WORK', _('Work Mobile')
        MOBILE_PRIVATE = 'MOBILE_PRIVATE', _('Private Mobile')
        FAX = 'FAX', _('Fax')
        WEBSITE = 'WEBSITE', _('Website')
        MESSENGER = 'MESSENGER', _('Messenger')
        OTHER = 'OTHER', _('Other')    
        # Others        
    
    address = models.TextField(
        _('Address'), 
        help_text=_("The actual contact information (e-mail address, phone number, etc.).")
    )
    type = models.CharField(max_length=20, choices=ContactType.choices)
    
    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

    def __str__(self):
        return f"{self.type} - {self.address}"


class Person(TenantAbstract):  
    '''full person profile (abstract), can be stored in Accounting
    not used fields (need to be stored in Accounting:
        custom
        sequenceNumberId        
    ''' 
    class COLOR(models.TextChoices):
        # CashCtrl
        WHITE = 'WHITE', _('White')
        BLUE = 'BLUE', _('Blue')
        GREEN = 'GREEN', _('Green')
        RED = 'RED', _('Red')
        YELLOW = 'YELLOW', _('Yellow')
        ORANGE = 'ORANGE', _('Orange')
        BLACK = 'BLACK', _('Black')
        GRAY = 'GRAY', _('Gray')
        BROWN = 'BROWN', _('Brown')
        VIOLET = 'VIOLET', _('Violet')
        PINK = 'PINK', _('Pink')        
        # Others        
        
    company = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Company'),
        help_text=('The name of the organization/company. Either firstName, lastName or company must be set.')
    )
    first_name = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('First Name'),
        help_text=('The person\'s first (given) name. Either firstName, lastName or company must be set.')
    )
    last_name = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Last Name'),
        help_text=('The person\'s last (family) name. Either firstName, lastName or company must be set.')
    )
    addresses = models.ManyToManyField(
        Address, related_name='%(class)s_addresses', blank=True,
        verbose_name=_(_('Addresses')),
        help_text=_('A list of addresses (street, house number, zip, city, country).')        
    )
    alt_mame = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Alternative Name'),
        help_text=_('An alternative name for this person (for organizational chart). Can contain localized text.')
    )    
    bic = models.CharField(
        max_length=11, 
        blank=True, 
        null=True,
        verbose_name=_('Business Identifier Code'),
        help_text=_("The BIC (Business Identifier Code) of the person's bank.")
    )  
    category = models.ForeignKey(
        # retrieve automatically
        PersonCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Category'),
        help_text=_("The person's category.")
    )    
    color = models.CharField(
        max_length=10,
        choices=COLOR.choices,
        blank=True,
        null=True,
        help_text=_(
            "The color to use for this person in the organizational chart. "
            "Leave empty for white."
        ),
    )
    contacts = models.ManyToManyField(
        Contact, related_name='%(class)s_contacts', blank=True,
        verbose_name=_('Contacts'),
        help_text=_('A list of addresses (street, house number, zip, city, country).')        
    )
    date_birth = models.DateField(
        blank=True, 
        null=True, 
        verbose_name=_('Date of Birth'),
        help_text=('The person\'s date of birth.')
    )
    department = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=_('Department'),
        help_text=('The department of the person within the company.')
    )
    discount_percentage = models.FloatField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0.0, message=_("Discount percentage must be at least 0.")),
            MaxValueValidator(100.0, message=_("Discount percentage cannot exceed 100."))
        ],
        help_text=_(
            "Discount percentage for this person, which may be used for orders. "
            "This can also be set on the category for all people in that category."
        ),
    )
    iban = models.CharField(
        max_length=32, 
        blank=True, 
        null=True, 
        verbose_name=_('IBAN'),
        help_text=('The IBAN (International Bank Account Number) of the person.')
    )
    industry = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('Industry'),
        help_text=('The industry of the company or the trade/vocation of the person.')
    )
    language = models.CharField(
        max_length=2, 
        choices=settings.LANGUAGES, blank=True, null=True,
        verbose_name=_('Language'),
        help_text=('The main language of the person. May be used for documents.')
    )
    nr = models.CharField(
        max_length=50,
        blank=True, 
        null=True, 
        verbose_name=_('Person Number'),
        help_text=('The person number (e.g., customer no.).')
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("The position (job title) of the person within the company."),
    )    
    superior = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subordinates",
        verbose_name=_('Superior'),
        help_text=_("The superior of this person (for organizational chart)."),
    )
    title = models.ForeignKey(
        Title,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("The person's title (e.g. 'Mr.', 'Mrs.', 'Dr.').")
    )
    vat_uid = models.CharField(
        max_length=32, 
        blank=True, 
        null=True,
        verbose_name=_('VAT no.'),
        help_text=_('The UID (VAT no.) of the company.')
    )     

    def save(self, *args, **kwargs):
        # Validate_person
        if not self.first_name and not self.last_name and not self.company:
            raise ValidationError(('Either First Name, Last Name or Company must be set.'))
        super().save(*args, **kwargs)      

    def __str__(self):
        name = ''
        if self.company:
            name += self.company + ': '
        if self.first_name or self.last_name:
            name += f'{self.last_name}, {self.first_name}'
        if self.date_birth:
            name += f', {self.date_birth}'
        return name

    class Meta:
        abstract = True


class PhysicalPerson(Person):
    """
    A concrete physical person who can be a Subscriber and an Inhabitant, etc.
    """
    class Meta:
        verbose_name = _('Person')
        verbose_name_plural = _('Persons')


class Subscriber(TenantAbstract):
    """
    A person who is a subscriber.
    """
    physical_person = models.OneToOneField(
        PhysicalPerson, on_delete=models.CASCADE, related_name='subscriber')
    subscription_date = models.DateField()
    subscription_status = models.CharField(
        max_length=50, choices=[('active', 'Active'), ('inactive', 'Inactive')])

    def __str__(self):
        return f"Subscriber: {self.physical_person}"

    class Meta:
        ordering = [
            'physical_person__company', 
            'physical_person__last_name', 
            'physical_person__first_name'
        ]
        verbose_name = _('Subscriber')
        verbose_name_plural = _('Subscribers')


class Inhabitant(TenantAbstract):
    """
    A person who is an inhabitant.
    """
    physical_person = models.OneToOneField(
        PhysicalPerson, on_delete=models.CASCADE, related_name='inhabitant')
    move_in_date = models.DateField()
    move_out_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Inhabitant: {self.physical_person} at {self.address}"

    class Meta:
        ordering = [      
            'physical_person__last_name', 
            'physical_person__first_name',
            '-physical_person__date_birth'
        ]                
        verbose_name = _('Inhabitant')
        verbose_name_plural = _('Inhabitants')


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


class BusinessPartner(Person):
    preferred_contact_method = models.CharField(max_length=50)
    is_vip = models.BooleanField(default=False)
  
    
class Building(TenantAbstract):
    class TypeChoices(models.TextChoices):
        MAIN = 'MAIN', ('Main address')
        ROOM = 'ROOM', ('Room address')
    name = models.CharField(max_length=200, blank=True, null=True)
    type = models.CharField(
        max_length=15, 
        choices=TypeChoices.choices,
        verbose_name=_('Type of address'),
        default=TypeChoices.MAIN,
        help_text=('The type of address. Possible values: Main address, Invoice address, Delivery address, Other.')
    )
    addresses = models.ManyToManyField(
        Address, related_name='buildings', blank=True,
        verbose_name=_(_('Addresses')),
        help_text=_('A list of addresses (street, house number, zip, city, country).')        
    )    
    contacts = models.ManyToManyField(
        Contact, related_name='buildings', blank=True,
        verbose_name=_('Contacts'),
        help_text=_('A list of addresses (street, house number, zip, city, country).')        
    )    
    
    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['type', 'name']
        verbose_name = _('Building')
        verbose_name_plural = _('Buildings')
