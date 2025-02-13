from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from core.models import LogAbstract, TenantAbstract
from scerp.admin import Display
from scerp.mixins import multi_language


'''
We lean the title and person model to cashctrl so we easily store it there.
'''
class Country(LogAbstract):
    """Model to represent a person's category.
    not used: parentId
    """
    code = models.CharField(
        _('Country'),
        max_length=3, help_text=_("3-letter country code")
    )
    name = models.JSONField(
        _('Name'),
        help_text=_("The name of the country")
    )
    is_default = models.BooleanField(
        _('Is default'), default=False,
        help_text=_("Default for data entry"))

    def get_default_id():
        default = Country.objects.filter(is_default=True).first()
        return default.id if default else None

    def __str__(self):
        return f'{self.code}, {multi_language(self.name)}'

    class Meta:
        ordering = ['-is_default', 'code']
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')


class Title(TenantAbstract):
    """Model to represent a person's title."""
    class GENDER(models.TextChoices):
        # CashCtrl
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        # Others
    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
    name = models.JSONField(
        _('Name'),
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
        return f'{multi_language(self.name)}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='crm_unique_title'
            )
        ]
        ordering = ['code']
        verbose_name = _("Title")
        verbose_name_plural = _("Titles")


class Address(LogAbstract):
    ''' Unique Address '''
    address = models.CharField(
        _('Address'), max_length=100, 
        help_text=_("Street, house number")
    )
    zip = models.CharField(
        _('ZIP Code'), max_length=20,
        help_text=_("Postal code for the address")
    )
    city = models.CharField(
        _('City'), max_length=100,
        help_text=_("City of the address")
    )
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="country",
        verbose_name=_('Country'), default=Country.get_default_id,
        help_text=_("Country")
    )

    def __str__(self):
        return f"{self.country}, {self.zip} {self.city}, {address}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['country', 'zip', 'city', 'address'],
                name='unique_address'
            )
        ]             
        ordering = ['country', 'zip', 'city', 'address']
        verbose_name = _('Address Entry')
        verbose_name_plural = _('Addresses')


class PersonCategory(TenantAbstract):
    """Model to represent a person's category.
    not used: parentId
    """
    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('Name'),
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
        return multi_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='person_cateogry_unique'
            )
        ]
        ordering = ['code']
        verbose_name = _("Person Category")
        verbose_name_plural = _("Person Categories")


class PersonAbstract(TenantAbstract):
    '''full person profile (abstract), can be stored in Accounting
    not used fields (need to be stored in Accounting:
        custom
        sequenceNumberId
    '''
    class COLOR(models.TextChoices):
        # cashCtrl
        # Ordered from lightest to darkest based on human readability
        WHITE = 'WHITE', _('White')
        YELLOW = 'YELLOW', _('Yellow')
        ORANGE = 'ORANGE', _('Orange')
        GREEN = 'GREEN', _('Green')
        BLUE = 'BLUE', _('Blue')
        PINK = 'PINK', _('Pink')
        VIOLET = 'VIOLET', _('Violet')
        RED = 'RED', _('Red')
        BROWN = 'BROWN', _('Brown')
        GRAY = 'GRAY', _('Gray')
        BLACK = 'BLACK', _('Black')

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
    alt_name = models.CharField(
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
        verbose_name=_('BIC Code'),
        help_text=_("The BIC (Business Identifier Code) of the person's bank.")
    )
    category = models.ForeignKey(
        # retrieve automatically
        PersonCategory, on_delete=models.PROTECT,
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


class Person(PersonAbstract):
    """
    A concrete physical person who can be a Subscriber and an Inhabitant, etc.
    use this for creditors, target: only use this for simplicity
    """
    class Meta:
        verbose_name = _('Person')
        verbose_name_plural = _('Persons')


class Subscriber(TenantAbstract):
    """
    A person who is a subscriber.
    """
    person = models.OneToOneField(
        Person, on_delete=models.CASCADE, related_name='subscriber')
    subscription_date = models.DateField()
    subscription_status = models.CharField(
        max_length=50, choices=[('active', 'Active'), ('inactive', 'Inactive')])

    def __str__(self):
        return f"Subscriber: {self.person}"

    class Meta:
        ordering = [
            'person__company',
            'person__last_name',
            'person__first_name'
        ]
        verbose_name = _('Subscriber')
        verbose_name_plural = _('Subscribers')


class Inhabitant(TenantAbstract):
    """
    A person who is an inhabitant.
    """
    person = models.OneToOneField(
        Person, on_delete=models.CASCADE, related_name='inhabitant')
    move_in_date = models.DateField()
    move_out_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Inhabitant: {self.person} at {self.address}"

    class Meta:
        ordering = [
            'person__last_name',
            'person__first_name',
            '-person__date_birth'
        ]
        verbose_name = _('Inhabitant')
        verbose_name_plural = _('Inhabitants')


class Employee(PersonAbstract):
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


class BusinessPartner(PersonAbstract):
    ''' use this for creditors '''
    pass


class Building(TenantAbstract):
    ''' Used to identify own buildings '''
    name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Building')
        verbose_name_plural = _('Buildings')


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


# Contact Entities
class ContactAbstract(TenantAbstract):

    class CONTACT_TYPE(models.TextChoices):
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

    type = models.CharField(max_length=20, choices=CONTACT_TYPE.choices)
    address = models.CharField(
        _('Address'), max_length=100,
        help_text=_("The actual contact information (e-mail address, phone number, etc.).")
    )

    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        abstract = True

    def __str__(self):
        return f"{self.type} - {self.address}"


class ContactPerson(ContactAbstract):
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_contact_person')


class ContactSubscriber(ContactAbstract):
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_contact_subscriber')


class ContactInhabitant(ContactAbstract):
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_contact_inhabitant')


class ContactEmployee(ContactAbstract):
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_contact_employee')


class ContactBusinessPartner(ContactAbstract):
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_contact_business')


class ContactRoom(ContactAbstract):
    building = models.ForeignKey(
        Building, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_building')


# Address Entities
class AddressBuilding(TenantAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_building')
    building = models.ForeignKey(
        Building, verbose_name=_('Accounting Setup'),
        on_delete=models.CASCADE, related_name='%(class)s_building')


class AddressAbstract(TenantAbstract):
    # Address Types Enum (choices for the 'type' field)
    class AddressType(models.TextChoices):
        # CashCtrl
        MAIN = 'MAIN', _('Main Address')
        INVOICE = 'INVOICE', _('Invoice Address')
        DELIVERY = 'DELIVERY', _('Delivery Address')
        OTHER = 'OTHER', _('Other Address')
        # Others

    type = models.CharField(
        _('Type'), max_length=10, 
        choices=AddressType.choices, default=AddressType.MAIN,
        help_text=_("The type of address: MAIN, INVOICE, DELIVERY, OTHER.")
    )
    additional_information = models.CharField(
        _('Additional Address Information'), max_length=10, blank=True, null=True,
        help_text=_("e.g. PO, c/o")
    )    


class AddressPerson(AddressAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_person',
        help_text=_("select or create address"))
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_person')


class AddressSubscriber(AddressAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_person')
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_person')


class AddressInhabitant(AddressAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_person')
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_person')


class AddressEmployee(AddressAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_person')
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_person')


class AddressBusinessPartner(AddressAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_person')
    person = models.ForeignKey(
        Person, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_person')
