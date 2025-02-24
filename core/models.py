# core/models.py
import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from scerp.locales import CANTON_CHOICES
from scerp.mixins import primary_language


# Base
class LogAbstract(models.Model):
    '''used for time stamp handling
    '''
    created_at = models.DateTimeField(
        _('created at'), auto_now_add=True)
    created_by = models.ForeignKey(
        User, verbose_name=_('created by'),
        on_delete=models.CASCADE, related_name='%(class)s_created')
    modified_at = models.DateTimeField(
        _('modified at'), auto_now=True)
    modified_by = models.ForeignKey(
        User, verbose_name=_('modified by'), null=True, blank=True,
        on_delete=models.CASCADE, related_name='%(class)s_modified')

    class Meta:
        abstract = True


class NotesAbstract(models.Model):
    '''handle notes and attachments
    '''
    notes = models.TextField(
        _('notes'), null=True, blank=True, help_text=_('notes to the record'))
    attachment = models.FileField(
        _('attachment'), upload_to='attachments/', blank=True, null=True,
        help_text=_('attachment for evidence'))
    version = models.ForeignKey(
        'self', verbose_name=_('version'), on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_previous_versions',
        help_text=_('previous_version'))
    is_inactive = models.BooleanField(
        _('is inactive'), default=False,
        help_text=_('item is not active anymore (but not permanently deleted)'),)
    is_protected = models.BooleanField(
        _('protected'), default=False,
        help_text=_('item must not be changed anymore'))

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


# App
class App(LogAbstract, NotesAbstract):
    ''' all available Apps
    '''
    name = models.CharField(max_length=100, unique=True)
    is_mandatory = models.BooleanField(default=False)
    verbose_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


# Tenant, User, Message
class Tenant(LogAbstract, NotesAbstract):
    '''only admin and trustees are allowed to create Tenants
        sends signals after creation!
    '''
    name = models.CharField(
        _('name'), max_length=100, unique=True)
    code = models.CharField(
        _('code'), max_length=32, unique=True,
        help_text=_(
            'code of tenant / client, unique, max 32 characters, '
            'only small letters, should only contains characters that '
            'can be displayed in an url)'))
    is_app_time_trustee = models.BooleanField(
        _('Is AppTime Trustee'), default=False,
        help_text=_(
            'only trustees are allowed to download time entries'))
    apps = models.ManyToManyField(
        App, verbose_name=_('apps'),
        related_name='%(class)s_apps',
        help_text=_('apps subscribed'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _('tenant')
        verbose_name_plural = _('tenants')


class TenantSetup(LogAbstract, NotesAbstract):
    '''used for assign technical stuff
        gets automatically created after a Tenant has been created,
    '''
    class TYPE(models.TextChoices):
        CITIZEN = ('B', _('Bürgergemeinde'))
        INHABITANTS = ('E', _('Einwohnergemeinde'))
        MUNICIPITY = ('G', _('Gemeinde'))
        CHURCH = ('K', _('Kirchgemeinde'))
        CITY = ('S', _('Stadt'))
        CORPORATION = ('Z', _('Zweckverband'))
        CANTON = ('C', _('Bürgergemeinde'))
        FEDERATION = ('F', _('Bund'))
        TRUSTEE = ('T', _('Trustee'))

    tenant = models.OneToOneField(
        Tenant, verbose_name=_('tenant'), on_delete=models.CASCADE,
        related_name='%(class)s_tenant',
        help_text=_('assignment of tenant / client'))
    canton = models.CharField(
         _('canton'), max_length=2, choices=CANTON_CHOICES,
         null=True, blank=True)
    language = models.CharField(
        _('Language'), max_length=2, choices=settings.LANGUAGES, default='de',
        help_text=_('The main language of the person. May be used for documents.')
    )
    show_only_primary_language = models.BooleanField(
        _('Show only primary language'), default=True,
        help_text=_('Show only primary language in forms')
    )
    type = models.CharField(
         _('Type'), max_length=1, choices=TYPE.choices,
        null=True, blank=True,
        help_text=_('Type, add new one of no match'))
    formats = models.JSONField(
        _('formats'), null=True, blank=True,
        help_text=_('Format definitions'))
    users = models.ManyToManyField(
        User, verbose_name=_('Users'),
        related_name='%(class)s_users',
        help_text=_('users subscribed'))

    def __str__(self):
        return self.tenant.name

    @property
    def logo(self):
        logo = TenantLogo.objects.filter(
            tenant=self.tenant, type=TenantLogo.Type.MAIN).first()
        if logo:
            return logo.logo
        return None

    @property
    def groups(self):
        groups = set()
        for user in self.users.all():
            for group in user.groups.all():
                groups.add(group)
        return groups

    class Meta:
        ordering = ['tenant__name']
        verbose_name = _('tenant setup')
        verbose_name_plural =  _('tenant setups')


class Message(LogAbstract, NotesAbstract):
    '''only admin and trustees are allowed to create Tenants
        sends signals after creation!
    '''
    class Severity(models.TextChoices):
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')

    name = models.CharField(_('name'), max_length=100)
    text = models.TextField(_('text'))
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
        verbose_name=_("Severity"),
        help_text=_("Current status of the meeting.")
    )
    recipients = models.ManyToManyField(
        Tenant, verbose_name=_('recipients'),
        related_name='%(class)s_tenant',
        help_text=_('empty if all recipients'))

    def __str__(self):
        return f"{self.name}, {self.modified_at}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['is_inactive', 'name'],
                name='unique_name'
            )]
        ordering = ['is_inactive', '-modified_at']
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')


class TenantAbstract(LogAbstract, NotesAbstract):
    ''' used for all models that refer to one tenant
    '''
    tenant = models.ForeignKey(
        Tenant, verbose_name=_('tenant'), on_delete=models.CASCADE,
        related_name='%(class)s_tenant',
        help_text=_('assignment of tenant / client'))

    class Meta:
        abstract = True


# Attachment
class Attachment(LogAbstract):
    '''
    A generic attachment model that allows files to be attached to any model.
    '''
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='%(class)s_tenant',
        verbose_name=_('Tenant'), help_text=_('assignment of tenant / client'))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()  # Instance ID of that model
    content_object = GenericForeignKey('content_type', 'object_id')  # The actual model instance

    file = models.FileField(
        _('File'), upload_to='attachments/')  # Temporary placeholder
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_attachment_upload_path(self, filename):
        # Create a path that includes tenant ID
        path = self.tenant.code
        # Build the path string, e.g., 'attachments/test_125/'
        return os.path.join('attachments', path, filename)

    # Override the file field's upload_to dynamically
    # Use the custom method
    file = models.FileField(upload_to=get_attachment_upload_path)

    def __str__(self):
        return f'Attachment {self.id} for {self.content_object}'


class TenantLogo(TenantAbstract):
    '''used for logos for all apps
        has signals
    '''
    class Type(models.TextChoices):
        MAIN = "MAIN", _("Main")
        OTHER = "OTHER", _("Other")

    name = models.CharField(
        _('name'), max_length=100, unique=True)
    type = models.CharField(
        _("Type"), max_length=50, choices=Type.choices, default=Type.MAIN,
        help_text=_("The type of logo. Defaults to MAIN."))
    logo = models.ImageField(
        _('logo'), upload_to='profile_photos/',
        blank=True, null=True,
        help_text=_('logo used in website'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['tenant__name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='unique_tenant_name'
            )
        ]
        verbose_name = _('tenant logo')
        verbose_name_plural =  _('tenant logos')


# Base Entities: Country, Address, Contact
class AddressCategory(TenantAbstract):
    class TYPE(models.TextChoices):
        # CashCtrl
        AREA = 'Area', _('Area')
        REGION = 'Region', _('Region')
        ROUTE = 'Route', _('Route')
        OTHER = 'OTHER', _('Other')

    type = models.CharField(max_length=20, choices=TYPE.choices)
    code = models.CharField(
        _('Code'), max_length=50, help_text=_("Code"))
    name = models.CharField(
        _('Name'), max_length=100, help_text=_("Name"))
    description = models.TextField(
        _('Description'), blank=True, null=True)

    class Meta:
        ordering = ['code', 'name']
        verbose_name = _('Address Category')
        verbose_name_plural = _('Address Categories')

    def __str__(self):
        return f"{self.type} {self.name}"


class Country(LogAbstract):
    """Model to represent a person's category.
    not used: parentId
    """
    alpha2 = models.CharField(
        _('Country'),
        max_length=2, help_text=_("2-letter country code")
    )
    alpha3 = models.CharField(
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
        return f'{self.alpha3}, {primary_language(self.name)}'

    class Meta:
        ordering = ['-is_default', 'alpha3']
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')


class Address(TenantAbstract):
    ''' Addresses, per Tenant
    '''
    # address
    address = models.CharField(
        _('Address'), max_length=100,
        help_text=_("Street, house number")
    )
    zip = models.CharField(
        _('ZIP Code'), max_length=20,
        help_text=_("Postal code for the address"))
    city = models.CharField(
        _('City'), max_length=100,
        help_text=_("City of the address")
    )
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="%(class)s_country",
        verbose_name=_('Country'), default=Country.get_default_id,
        help_text=_("Country")
    )
    categories = models.ManyToManyField(
        AddressCategory, related_name='address_categories',
        verbose_name=_('Category'), blank=True,
        help_text=_('Categorize address for planning or statistical analysis.')
    )

    def __str__(self):
        if self.country.alpha3 == 'CHE':
            return f"{self.zip} {self.city}, {self.address}"
        return f"{self.country} {self.zip} {self.city}, {self.address}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['country', 'zip', 'address'],
                name='unique_address'
            )
        ]
        ordering = ['country', 'zip', 'city']
        verbose_name = _('Address Entry')
        verbose_name_plural = _('Addresses')


class Contact(TenantAbstract):

    class TYPE(models.TextChoices):
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

    type = models.CharField(max_length=20, choices=TYPE.choices)
    address = models.CharField(
        _('Contact'), max_length=100,
        help_text=_("The actual contact information (e-mail address, phone number, etc.).")
    )

    class Meta:
        abstract = True
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

    def __str__(self):
        return f"{self.type} - {self.address}"


class Title(TenantAbstract):
    """
    Model to represent a person's title.
        this will trigger a create / update event to accounting
    """
    class GENDER(models.TextChoices):
        # CashCtrl
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')

    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
    name = models.JSONField(
        _('Name'),
        blank=True,  null=True,  # null necessary to handle multi languages
        help_text=_("The name of the title (i.e. the actual title)."))
    gender = models.CharField(
        _('Gender'), max_length=6, blank=True, null=True,
        choices=GENDER.choices,
        help_text=_(
            "The person's biological gender (male or female). Possible "
            "values: MALE, FEMALE."))
    sentence = models.JSONField(
        _('Sentence'), blank=True,  null=True,  # null necessary to handle multi languages
        help_text=_(
            "The letter salutation (e.g. 'Dear Mr.', etc.). May be used in "
            "mail."))

    def __str__(self):
        return primary_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='core_unique_title'
            )
        ]
        ordering = ['code']
        verbose_name = _("Title")
        verbose_name_plural = _("Titles")


class PersonCategory(TenantAbstract):
    """
    this will trigger a create / update event to accounting
    """
    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('Name'),
        help_text=_("The name of the category.")
    )

    def __str__(self):
        return primary_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='person_category_unique'
            )
        ]
        ordering = ['code']
        verbose_name = _("Person Category")
        verbose_name_plural = _("Person Categories")


class Person(TenantAbstract):
    '''
    this will trigger a create / update event to accounting
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
        _('Company'), max_length=100, blank=True, null=True,
        help_text=_(
            "The name of the organization/company. Either firstName, lastName "
            "or company must be set."))
    title = models.ForeignKey(
        Title,
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Title'), related_name="%(class)s_title",
        help_text=_("The person's title (e.g. 'Mr.', 'Mrs.', 'Dr.')."))
    first_name = models.CharField(
        _('First Name'), max_length=50, blank=True, null=True,
        help_text=_(
            "The person\'s first (given) name. Either firstName, lastName or "
            "company must be set."))
    last_name = models.CharField(
        _('Last Name'), max_length=50, blank=True, null=True,
        help_text=_(
            "The person\'s last (family) name. Either firstName, lastName or "
            "company must be set."))
    alt_name = models.CharField(
        _('Alternative Name'), max_length=100, blank=True, null=True,
        help_text=_(
            "An alternative name for this person (for organizational chart). "
            "Can contain localized text."))
    bic = models.CharField(
        _('BIC Code'), max_length=11, blank=True, null=True,
        help_text=_("The BIC (Business Identifier Code) of the person's bank."))
    category = models.ForeignKey(
        PersonCategory, on_delete=models.PROTECT,
        related_name='%(class)s_category',
        verbose_name=_('Category'), help_text=_("The person's category."))
    color = models.CharField(
        max_length=10, choices=COLOR.choices, blank=True, null=True,
        help_text=_(
            "The color to use for this person in the organizational chart or "
            "for internal categorization."))
    date_birth = models.DateField(
        _('Date of Birth'), blank=True, null=True,
        help_text=('The person\'s date of birth.'))
    department = models.CharField(
        _('Department'), max_length=100, blank=True, null=True,
        help_text=_('The department of the person within the company.'))
    discount_percentage = models.FloatField(
        _('Discount'), blank=True, null=True,
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
        _('IBAN'), max_length=32, blank=True, null=True,
        help_text=('The IBAN (International Bank Account Number) of the person.')
    )
    industry = models.CharField(
        _('Industry'), max_length=100, blank=True, null=True,
        help_text=_(
            "The industry of the company or the trade/vocation of the person."))
    language = models.CharField(
        _('Language'), max_length=2, blank=True, null=True,
        choices=settings.LANGUAGES,
        help_text=('The main language of the person. May be used for documents.'))
    nr = models.CharField(
        _('Person Number'), max_length=50, blank=True, null=True,
        help_text=('The person number (e.g., customer no.).'))
    position = models.CharField(
        _("Position"), max_length=100, blank=True, null=True,
        help_text=_(
            "The position (job title) of the person within the company."))
    superior = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name="%(class)s_subordinates",
        verbose_name=_('Superior'),
        help_text=_("The superior of this person (for organizational chart)."))
    vat_uid = models.CharField(
        _('VAT no.'), max_length=32, blank=True, null=True,
        help_text=_('The UID (VAT no.) of the company.'))
    photo = models.ImageField(
        _('photo'), upload_to='profile_photos/', blank=True, null=True,
        help_text=_('Load up your personal photo.'))
    attachments = GenericRelation('Attachment')  # Enables reverse relation

    def clean(self, *args, **kwargs):
        # Validate_person
        if not self.first_name and not self.last_name and not self.company:
            raise ValidationError(
                _('Either First Name, Last Name or Company must be set.'))

    def __str__(self):
        if self.company:
            if self.last_name:
                return f"{self.company}, {self.last_name} {self.first_name}"
            return self.company
        if self.date_birth:
            return f"{self.last_name} {self.first_name}, {self.date_birth}"
        return f"{self.last_name} {self.first_name}"

    class Meta:
        verbose_name = _('Person')
        verbose_name_plural = _('Persons')


class PersonAddress(TenantAbstract):
    '''
    Map Address to Person
    '''
    class TYPE(models.TextChoices):
        # CashCtrl
        MAIN = 'MAIN', _('Main Address')
        INVOICE = 'INVOICE', _('Invoice Address')
        DELIVERY = 'DELIVERY', _('Delivery Address')
        OTHER = 'OTHER', _('Other Address')

    type = models.CharField(
        _('Type'), max_length=20, choices=TYPE.choices)
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        related_name='%(class)s_address',
        verbose_name=_('Address'))
    address = models.ForeignKey(
        Address, on_delete=models.CASCADE,
        related_name='%(class)s_address',
        verbose_name=_('Address'))
    post_office_box = models.CharField(
        _('PO Box'), max_length=8,
        blank=True, null=True,
        help_text=_("Post Office Box"))
    additional_information = models.CharField(
        _('Additional Address Information'),
        max_length=50, blank=True, null=True,
        help_text=_("e.g. c/o"))

    def __str__(self):
        return f"{self.address}"

    class Meta:
        ordering = ['type']
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')


class PersonContact(Contact):
    '''
    Map Contact to Person
    '''
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        related_name='%(class)s_address',
        verbose_name=_('Address'))


class UserProfile(LogAbstract, NotesAbstract):
    user = models.OneToOneField(
        User, verbose_name=_('User'), on_delete=models.CASCADE,
        related_name='profile',
        help_text=_(
            "Registered User. Click the 'pencil' to assign the user to groups"))
    person = models.OneToOneField(
        Person, verbose_name=_('User Details'), on_delete=models.CASCADE,
        related_name='%(class)s_person',
        help_text=_("Details and photo of person"))

    def __str__(self):
        return f'{self.user.last_name.upper()}, {self.user.first_name}'

    @property
    def groups(self):
        return self.user.groups.all().order_by('name')

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = _('User')
        verbose_name_plural =  _('Users')


# Buildings, Rooms
class BuildingX(TenantAbstract):
    ''' Used to identify own buildings '''
    name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Building')
        verbose_name_plural = _('Buildings')


class BuildingAddress(TenantAbstract):
    address = models.ForeignKey(
        Address, verbose_name=_('Address'),
        on_delete=models.CASCADE, related_name='%(class)s_address_building')
    building = models.ForeignKey(
        BuildingX, verbose_name=_('Accounting Setup'),
        on_delete=models.CASCADE, related_name='%(class)s_building')


class BuildingRoom(TenantAbstract):
    ''' Used to identify own rooms '''
    name = models.CharField(_('Name'), max_length=200)
    building = models.ForeignKey(
        BuildingX, verbose_name=_('Building'),
        on_delete=models.CASCADE, related_name='%(class)s_building')

    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Building')
        verbose_name_plural = _('Buildings')


class RoomContact(Contact):
    room = models.ForeignKey(
        BuildingRoom, verbose_name=_('Person'),
        on_delete=models.CASCADE, related_name='%(class)s_room')
