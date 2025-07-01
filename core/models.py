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
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from accounting.banking import get_bic
from scerp.locales import CANTON_CHOICES
from scerp.mixins import primary_language, convert_ch1903_to_wgs84


# Base ----------------------------------------------------------------------
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
        return self.verbose_name

    class Meta:
        ordering = ['name']
        verbose_name = _('App')
        verbose_name_plural = '_' + _('Apps')


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
    # App
    is_app_time_trustee = models.BooleanField(
        _('Is AppTime Trustee'), default=False,
        help_text=_(
            'only trustees are allowed to download time entries'))
    apps = models.ManyToManyField(
        App, verbose_name=_('apps'),
        related_name='%(class)s_apps',
        help_text=_('apps subscribed'))

    # Accounting, currently only cashCtrl
    cash_ctrl_org_name = models.CharField(
        'Org Name (cashCtrl)', max_length=100, blank=True, null=True,
        help_text='name of organization as used in cashCtrl domain')
    cash_ctrl_api_key = models.CharField(
        _('api key'), max_length=100,  blank=True, null=True,
        help_text=_('api key'))

    # General accounting
    language = models.CharField(
        _('Language'), max_length=2, choices=settings.LANGUAGES, default='de',
        help_text=_('The main language of the person. May be used for documents.')
    )
    encode_numbers = models.BooleanField(
        _('Encode numbers in cashCtrl headings'), default=True,
        help_text=_(
            'e.g. 02 Allgemeinde Dienste'))
    account_plan_loaded = models.BooleanField(
        _('Account plan loaded'), default=False,
        help_text=_(
            'gets set to True if account plan uploaded to accounting system'))

    @property
    def cash_ctrl_url(self):
        if self.cash_ctrl_org_name:
            return f"https://{self.cash_ctrl_org_name}.cashctrl.com/"
        return None

    def __str__(self):
        return self.name

    def clean(self):
        # Ensure that both org_name and api_key are either both provided
        # or both not provided
        # cashCtrl
        if self.cash_ctrl_org_name:
            # Only check uniqueness if org_name is set
            if Tenant.objects.filter(
                        cash_ctrl_org_name=self.cash_ctrl_org_name
                    ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    {'cash_ctrl_org_name': _(
                        "Organization name must be unique.")})

        if self.cash_ctrl_org_name or self.cash_ctrl_api_key:
            if not self.cash_ctrl_org_name or not self.cash_ctrl_api_key:
                raise ValidationError(_("cashCtrl need Org Name and api-key"))

    def save(self, *args, **kwargs):
        self.clean()  # Ensure validation before saving
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']
        verbose_name = _('Tenant')
        verbose_name_plural = '_' + _('Tenants')


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
    zips = models.JSONField(
        _('municipality zips'), default=list,
        help_text=_(
            'Zips that belong to the tenant, e.g. [4617]. '
            'We use it for importing the building addresses. '))
    bdg_egids = models.JSONField(
        _('EGIDS to include'), default=list,
        help_text=_(
            'Egids that belong to the tenant, e.g. [4617]. '
            'We use it for importing the building addresses. '))
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
        verbose_name_plural = '_' + _('Messages')


class TenantAbstract(LogAbstract, NotesAbstract):
    ''' used for all models that refer to one tenant
    '''
    tenant = models.ForeignKey(
        Tenant, verbose_name=_('tenant'), on_delete=models.CASCADE,
        related_name='%(class)s_tenant',
        help_text=_('assignment of tenant / client'))

    def get_attachment_link(self, nr=1, html=False):
        try:
            attachments = self.attachments.all()
        except:
            attachments = []

        for index, attachment in enumerate(attachments, start=1):
            if index == nr:
                return attachment.file.url
        return None

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

    @classmethod
    def get_attachments_for_instance(cls, instance):
        """
        Returns a single Attachment for a given model instance using GenericForeignKey.
        Raises ValueError if no or multiple attachments are found.
        """
        content_type = ContentType.objects.get_for_model(instance)

        return cls.objects.filter(
            content_type=content_type, object_id=instance.pk
        ).order_by('-object_id')


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


class Ticket(TenantAbstract):
    '''used for generating tickets
    '''
    class IssueType(models.TextChoices):
        INCIDENT = 'incident', _('Incident')
        REQUEST = 'request', _('Request')
        CHANGE = 'change', _('Change')

    class Priority(models.TextChoices):
        CRITICAL = 'critical', _('Critical - System is down or users cannot work')
        HIGH = 'high', _('High - Major functions not working, no workaround')
        MEDIUM = 'medium', _('Medium - Some functions impaired, workaround available')
        LOW = 'low', _('Low - Minor issue or bug')

    class Department(models.TextChoices):
        IT = 'it', _('IT Support')
        HR = 'hr', _('HR')
        FINANCE = 'finance', _('Finance')
        FACILITIES = 'facilities', _('Facilities')
        CUSTOMER_SERVICE = 'customer_service', _('Customer Service')

    class Status(models.TextChoices):
        NEW = 'new', _('New')
        IN_PROGRESS = 'in_progress', _('In Progress')
        AWAITING_CUSTOMER = 'awaiting_customer', _('Awaiting Customer')
        RESOLVED = 'resolved', _('Resolved')
        CLOSED = 'closed', _('Closed')

    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'))
    issue_type = models.CharField(
        _('issue type'), max_length=20, choices=IssueType.choices)
    priority = models.CharField(
        _('priority'), max_length=20, choices=Priority.choices)
    status = models.CharField(
        _('status'), max_length=30, choices=Status.choices, default=Status.NEW)
    app = models.ForeignKey(
        App, models.SET_NULL, null=True, blank=True,
        verbose_name=_('app'), related_name="%(class)s_app",
        help_text=_('Related App where the issue occurs (optional).')
    )
    responsible = models.ForeignKey(
        User, verbose_name=_('respsonsible'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_respsonsible',
        help_text=_('User responsible to resolve'))
    def __str__(self):
        return f"{self.title} ({self.get_issue_type_display()})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')


class TicketAdminView(Ticket):
    class Meta:
        proxy = True
        verbose_name = _('Ticket - Admin View')
        verbose_name_plural = _('Tickets - Admin Views')


# Accounting --------------------------------------------------------
'''
We use this for entities that may be connected to the accounting system
if setup is not None
'''


class AcctApp(TenantAbstract):
    '''
    attributes to manage cashCtrl sync
    '''
    # CashCtrl
    c_id = models.PositiveIntegerField(
        _('CashCtrl id'), null=True, blank=True)
    c_created = models.DateTimeField(
        _('CashCtrl created'), null=True, blank=True)
    c_created_by = models.CharField(
        _('CashCtrl created_by'), max_length=100, null=True, blank=True)
    c_last_updated = models.DateTimeField(
        _('CashCtrl last_updated'), null=True, blank=True)
    c_last_updated_by = models.CharField(
        _('CashCtrl last_updated_by'), max_length=100, null=True, blank=True)
    last_received = models.DateTimeField(
        _('Last received'), null=True, blank=True,
        help_text=_(
            "Last time data has been received from cashCtrl. "
            "Gets filled out in signals_cash_ctrl.get "))
    message = models.CharField(
        _('Message'), max_length=200, null=True, blank=True,
        help_text=_('Here we show error messages. Just be empty.'))
    is_enabled_sync = models.BooleanField(
        _("Enable Sync"), default=True,
        help_text=_(
            "Disable sync with cashCtrl; useful for admin tasks. "
            "False if no accounting system is used."))
    sync_to_accounting = models.BooleanField(
        _("Sync to Accounting"), default=False,
        help_text=(
            "This records needs to be synched to cashctr, if the cycle is "
            "over it gets reset to False"))

    class Meta:
        abstract = True



# Official Address --------------------------------------------------------
'''
They are read only and provided centrally.
See https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/amtliches-gebaeudeadressverzeichnis_ch/amtliches-gebaeudeadressverzeichnis_ch_2056.csv.zip

data = {
    # City
    "ZIP_LABEL": "4052 Basel",
    "COM_FOSNR": 2701,
    "COM_NAME": "Basel",
    "COM_CANTON": "BS",

    # Street
    "STR_ESID": 10089624,
    "STN_LABEL": "Christoph Merian-Platz",

    # Building and Address
    "BDG_EGID": 443930,
    "BDG_CATEGORY": "residential",
    "BDG_NAME": None,

    "ADR_EDID": 0,  # not used
    "ADR_EGAID": 100335354,
    "ADR_NUMBER": "8",

    "ADR_STATUS": "real",
    "ADR_OFFICIAL": True,
    "ADR_MODIFIED": "15.11.2024",
    "ADR_EASTING": 2613090,
    "ADR_NORTHING": 1266479
}
'''
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
        verbose_name_plural = '_' + _('Countries')


# Area
class Area(TenantAbstract):
    code = models.CharField(
        _('Code'), max_length=50)
    name = models.CharField(
        _('Name'), max_length=200,
        help_text=_("Area to categorize addresses"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['code']
        verbose_name = _('Area')
        verbose_name_plural = _('Areas')


# Address Assignment must be quick so we use a flat table
class AddressMunicipal(TenantAbstract):
    '''These are the official addresses of the tenant's city,
        we use it for inhabitants, tags and buildings
    '''
    # Municipality
    com_fosnr = models.PositiveIntegerField(
        help_text="Unique identifier for the municipality."
    )
    com_name = models.CharField(
        max_length=255,
        help_text="Name of the municipality."
    )
    com_canton = models.CharField(
        max_length=2,
        help_text="Abbreviation for the canton (e.g., BS, ZH)."
    )
    zip = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1000), MaxValueValidator(9999)]
    )
    city = models.CharField(
        max_length=100, help_text="Name of the municipality."
    )

    # Street
    str_esid = models.PositiveBigIntegerField(
        help_text="Unique identifier for the street."
    )
    stn_label = models.CharField(
        _('Street'), max_length=255,
        help_text="Name of the street."
    )

    # Building
    bdg_egid = models.PositiveBigIntegerField(
        help_text="Unique identifier for the building."
    )
    bdg_category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Category of the building (e.g., residential, commercial)."
    )
    bdg_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the building (if applicable)."
    )

    # Address
    adr_egaid = models.PositiveBigIntegerField(
        help_text="Unique identifier for the address."
    )
    adr_number = models.CharField(
        max_length=10,
        help_text="Address number (e.g., 8, 12A)."
    )
    adr_status = models.CharField(
        max_length=50,
        help_text="The status of the address (e.g., real, historical)."
    )
    adr_official = models.BooleanField(
        help_text="Whether the address is official (true or false)."
    )
    adr_modified = models.DateField(
        help_text="The last modified date of the address."
    )
    adr_easting = models.PositiveIntegerField(
        help_text="Easting coordinate of the address (Swiss coordinate system)."
    )
    adr_northing = models.PositiveIntegerField(
        help_text="Northing coordinate of the address (Swiss coordinate system)."
    )
    lat = models.FloatField(
        blank=True,
        null=True,
        help_text="Latitude (WGS84)"
    )
    lon = models.FloatField(
        blank=True,
        null=True,
        help_text="Longitude (WGS84)"
    )

    # Custom
    address_label = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Address label for sorting - automatically filled out."
    )    
    area = models.ForeignKey(
        Area, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Area'), related_name="%(class)s_area",
        help_text=_("Area"))

    def save(self, *args, **kwargs):
        # Calc address_label
        self.address_label = self.stn_label or ''
        # append number to be sortable, e.g. '123'.rjust(5) → ' 123'
        length = 5 if self.adr_number and self.adr_number[-1].isalpha() else 4
        self.address_label += (self.adr_number or '').rjust(length)
        
        # Automatically calculate latitude and longitude if missing
        if self.adr_easting and self.adr_northing and (
                self.lat is None or self.lon is None):
            self.lat, self.lon = convert_ch1903_to_wgs84(
                self.adr_easting, self.adr_northing)
        super().save(*args, **kwargs)

    def __str__(self):
        notes_str = f", {self.notes}" if self.notes else ''
        return (
            f"{self.zip} {self.city}, {self.stn_label} {self.adr_number}"
            f", EGID {self.bdg_egid}{notes_str}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'adr_egaid'],
                name='unique_address_municipality'
            )
        ]
        ordering = ['zip', 'stn_label', 'adr_number']


# Base Entities: Country, Address, Contact

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

    def category_str(self, filter_type=None):
        # Prepare categories
        if filter_type:
            categories = self.categories.filter(type=filter_type)
        else:
            categories = self.categories

        # get and append category names
        names = []
        for cat in categories.all():
            type_str = '' if filter_type else cat.get_type_display()[0] + '-'
            name = cat.name[0]
            names.append(f'{type_str}{name}')

        return ', '.join(names)

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
        ordering = ['country', 'zip', 'city', 'address']
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


class BankAccount(TenantAbstract):

    class TYPE(models.TextChoices):
        # CashCtrl
        DEFAULT = 'DEFAULT', _('Default')
        ORDER = 'ORDER', _('Order')
        SALARY = 'SALARY', _('Salary')
        HISTORICAL = 'HISTORICAL', _('Historical')

    type = models.CharField(
        max_length=20, choices=TYPE.choices, default=TYPE.DEFAULT)
    iban = models.CharField(
        _('IBAN'), max_length=32, blank=True, null=True,
        help_text=_(
            'The IBAN (International Bank Account Number) of the person.'))
    bic = models.CharField(
        _('BIC Code'), max_length=11, blank=True, null=True,
        help_text=_(
            "The BIC (Business Identifier Code) of the person's bank. "
            "Most common Swiss BIC codes are detected automatically."))

    def clean(self):
        if (self.iban or self.qr_iban) and not self.bic:
            self.bic = get_bic(self.iban)
            #if not self.bic:
            #    raise ValidationError(_("No BIC Code found."))
        if not self.iban and not self.qr_iban:
            raise ValidationError(_("No IBAN given."))

    class Meta:
        abstract = True
        verbose_name = _('Bank Account')
        verbose_name_plural = _('Bank Accounts')

    def __str__(self):
        return f"{self.type} - {self.iban}"


class Title(AcctApp):
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

    def display(self, language=None):
        if language:
            return self.name.get
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


class PersonCategory(AcctApp):
    """
    this will trigger a create / update event to accounting
    """
    class CODE:
        # default codes for init
        ASSURANCE = 'assurance'
        CLIENT = 'client'
        EMPLOYEE = 'employee'
        EMPLOYEE_EXTERNAL = 'employee_external'
        SUBSCRIBER = 'subscriber'
        VENDOR = 'vendor'

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


class Person(AcctApp):
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
    is_customer = models.BooleanField(
        _('Is Customer'), default=False,
        help_text=_('Is the person a customer?'))
    is_employee = models.BooleanField(
        _('Is Employee'), default=False,
        help_text=_('Is the person an employee?'))
    is_family = models.BooleanField(
        _('Is Family'), default=False,
        help_text=_('Is the person a family?'))
    is_insurance = models.BooleanField(
        _('Is Insurance'), default=False,
        help_text=_('Is the person an insurance company?'))
    is_vendor = models.BooleanField(
        _('Is Supplier'), default=False,
        help_text=_('Is the person a supplier / vendor?'))

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

    @property
    def short_name(self):
        ''' output company name or lastname, firstname '''
        if self.company:
            return self.company 
        return f"{self.last_name}, {self.first_name}"

    def clean(self, *args, **kwargs):
        # Validate_person
        if not self.first_name and not self.last_name and not self.company:
            raise ValidationError(
                _('Either First Name, Last Name or Company must be set.'))

    def display_name(
            self, language=None, incl_title=False, title_line_break=False):
        lines = []
        if self.company:
            lines.append(self.company)

        if incl_title and self.title:
            title = self.title.display(language)
            if title_line_break:
                lines.append(title)
                lines.append(f"{self.first_name} {self.last_name}")
            else:
                lines.append(f"{title} {self.first_name} {self.last_name}")
        elif self.first_name or self.last_name:
            lines.append(f"{self.first_name} {self.last_name}")

        return '\n'.join(lines)

    def get_invoice_address(self):
        queryset = PersonAddress.objects.filter(person=self)

        # Try invoice, main
        for address_type in (
                PersonAddress.TYPE.INVOICE, PersonAddress.TYPE.MAIN):
            address = queryset.filter(type=address_type)
            if address:
                return address_type, address.first().address_full

        # Return first
        address = queryset.first()
        return address.type, address.address_full

    def __str__(self):
        if self.is_employee:
            company = '℗' + self.company
        elif self.company:
            company = '©' + self.company
        else:
            company = ''

        # Ensure all name components are strings (handle None)
        last_name = self.last_name or ''
        first_name = self.first_name or ''
        alt_name = self.alt_name or ''
        date_birth = str(self.date_birth) if self.date_birth else ''

        # Construct the full name
        name_parts = [last_name, first_name, alt_name, date_birth]
        name = ', '.join(filter(None, name_parts))  # Remove empty strings

        # Ensure at least one value is returned
        if company and name:
            return f"{company}, {name}"
        return company or name or "Unknown"  # Fallback if everything is empty

    class Meta:
        ordering = ['company', 'last_name', 'first_name', 'alt_name']
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
        help_text=_("e.g. c/o or company name for invoice addresses"))

    @property
    def address_address_full(self):
        value = ''
        if self.post_office_box:
            value += self.post_office_box + '\n'
        if self.additional_information:
            value += self.additional_information + '\n'
        if self.address.address:
            value += self.address.address + '\n'

        return value

    @property
    def address_full(self):
        value = ''
        if self.post_office_box:
            value += self.post_office_box + '\n'
        if self.additional_information:
            value += self.additional_information + '\n'
        if self.address.address:
            value += self.address.address + '\n'
        value += f"{self.address.zip} {self.address.city}"

        return value

    def __str__(self):
        return f"{self.address} ({self.type})"

    class Meta:
        ordering = ['address__zip', 'address__address', 'type']
        verbose_name = _('Person by Address')
        verbose_name_plural = _('Persons by Address')


class PersonBankAccount(BankAccount):
    '''
    Map Contact to Person
    '''
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        related_name='%(class)s_person',
        verbose_name=_('Address'))


class PersonContact(Contact):
    '''
    Map Contact to Person
    '''
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        related_name='%(class)s_person',
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
        verbose_name_plural =  _('Users') + ' (Scerp)'


# Buildings, Rooms
class Dwelling(TenantAbstract):
    ''' Used to identify own rooms '''
    name = models.CharField(_('Name'), max_length=200)
    ewid = models.PositiveIntegerField(
        'EWID', blank=True, null=True)
    address = models.ForeignKey(
        AddressMunicipal, verbose_name=_('Building'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_address')

    def __str__(self):
        return f"{self.name}, {self.address}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Dwelling or Room')
        verbose_name_plural = _('Dwelling or Room')


class Room(TenantAbstract):
    name = models.CharField(_('Name'), max_length=200)
    address = models.ForeignKey(
        AddressMunicipal, verbose_name=_('Building'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_address')
    dwelling = models.ForeignKey(
        Dwelling, verbose_name=_('Dwelling'),
        on_delete=models.CASCADE, related_name='%(class)s_dwelling')

    def __str__(self):
        return f"{self.name}, {self.building}, {self.dwelling}"

    class Meta:
        ordering = ['name']
        verbose_name = _('Dwelling or Room')
        verbose_name_plural = _('Dwelling or Room')


class RoomContact(Contact):
    room = models.ForeignKey(
        Room, verbose_name=_('Person'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_room')

    def __str__(self):
        return f"{self.room}, {self.type}, {self.address}"

    class Meta:
        ordering = ['type', 'address']
        verbose_name = _('Room Contact')
        verbose_name_plural = _('Room Contact')
