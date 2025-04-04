from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounting.models import Article
from core.models import (
    TenantAbstract, AddressMunicipal, Area, Person, PersonAddress)
from asset.models import AssetCategory, Device, Unit


# Timing
class Period(TenantAbstract):
    code = models.CharField(
        _('Code'), max_length=50,
        help_text=_("e.g. water, semi annual"))
    name = models.CharField(
        _('name'), max_length=50, help_text=_("name"))
    start = models.DateField(
        _("Start"), help_text=_("Start date of the  period"))
    end = models.DateField(
        _("End"), help_text=_("End date of the period"))
    attachments = GenericRelation('core.Attachment')  # Enables reverse relation

    def __str__(self):
        return f'{self.name}, {self.start} - {self.end}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code', 'start', 'end'],
                name='unique_billing_period'
            )
        ]
        ordering = ['-end', 'code']
        verbose_name = _('Period')
        verbose_name_plural = _('Periods')


class Route(TenantAbstract):
    class STATUS(models.TextChoices):
        # Processing stages
        INITIALIZED = 'INIT', _('Route initialized')
        COUNTER_EXPORTED = 'CEX', _('Counter File Exported')
        COUNTER_IMPORTED = 'CIM', _('Counter File Imported')
        TEST_INVOICES = 'TIN', _('Test Invoices Generated')
        INVOICES_GENERATED = 'INV', _('Invoices Generated')

    name = models.CharField(
        _('name'), max_length=50,
        help_text=_("name and period for route, e.g. Water, 24/1"))
    period = models.ForeignKey(
        Period, verbose_name=_('Period'),
        on_delete=models.PROTECT, related_name='%(class)s_period')
    previous_period = models.ForeignKey(
        Period, verbose_name=_('Previous Period'), blank=True, null=True,
        on_delete=models.PROTECT, related_name='%(class)s_last_period')
    areas = models.ManyToManyField(
        Area, verbose_name=_('Areas'), blank=True,
        help_text=_(
            "Areas that should be included, "
            "leave empty to include all in scope"))
    addresses = models.ManyToManyField(
        AddressMunicipal, verbose_name=_('Addresses'), blank=True,
        help_text=_(
            "Addresses that should be included, "
            "leave empty to include all in scope"))
    asset_categories = models.ManyToManyField(
        AssetCategory, verbose_name=_('Categories'),
        help_text=_(
            "Categories of counters to be included. Leave empty if all. "))
    start = models.DateField(
        _("Start"), blank=True, null=True,
        help_text=_("Leave empty if period start"))
    end = models.DateField(
        _("End"), blank=True, null=True,
        help_text=_("Leave empty if period end"))
    duration = models.PositiveSmallIntegerField(
        f'{_("Duration")} [{_("days")}]', blank=True, null=True,
        help_text=_("Period duration in days"))
    status = models.CharField(
        max_length=4, choices=STATUS.choices, default=STATUS.INITIALIZED,
        help_text=_("Current status of the routing."))
    is_default = models.BooleanField(
        _('Default route'), default=True,
        help_text=_("Inside default schedule"))
    confidence_min = models.DecimalField(
        _('Confidence Min.'), max_digits=3, decimal_places=2, default=0.1,
        help_text=_(
            "Min confidence factor based on previous period, "
            "e.g. 0.5: value must be ≥ 5 if previous value was 10"))
    confidence_max = models.DecimalField(
        _('Confidence Max.'), max_digits=3, decimal_places=2, default=2,
        help_text=_(
            "Max confidence factor based on previous period, "
            "e.g. 2: value must be ≤ 20 if previous value was 10"))
    attachments = GenericRelation('core.Attachment')  # Enables reverse relation
    import_file_id = models.PositiveIntegerField(
        blank=True, null=True, help_text=('for internal usage'))

    # For analysis
    number_of_addresses = models.PositiveIntegerField(
        _('Number of Addresses'), blank=True, null=True, editable=False)
    number_of_subscriptions = models.PositiveIntegerField(
        _('Number of Subscriptions'), blank=True, null=True, editable=False)
    number_of_counters = models.PositiveIntegerField(
        _('Number of Counters'), blank=True, null=True, editable=False)

    def get_start(self):
        return self.start if self.start else self.period.start

    def get_end(self):
        return self.end if self.end else self.period.end

    def save(self, *args, **kwargs):
        ''' Make calcuatiolations '''
        # Calculate duration before saving the object.
        self.duration = (self.get_end() - self.get_start()).days + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.period}, {self.name}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'period', 'name'],
                name='unique_billing_route'
            )
        ]
        ordering = ['-period__end', '-start', '-end', 'period__code', 'name']
        verbose_name = _('Route')
        verbose_name_plural = _('Routes')


# Subscriptions
class Subscription(TenantAbstract):
    nr = models.CharField(
        _('Subscription Number'), max_length=50, blank=True, null=True,
        help_text=('New subscription number, retrieved automatically'))
    subscriber_number = models.CharField(
        _('Abo Nr'), max_length=50, blank=True, null=True,
        help_text=('Old subscription number, leave empty'))
    subscriber = models.ForeignKey(
        Person, verbose_name=_('Subscriber'),
        on_delete=models.PROTECT, related_name='%(class)s_subscriber',
        help_text=_(
            "subscriber / inhabitant / owner"
            "invoice address may be different to subscriber, defined under "
            "address"))
    partner = models.ForeignKey(
        Person, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Partner'), related_name='%(class)s_partner',
        help_text=_(
            "subscriber / inhabitant / owner"
            "invoice address may be different to subscriber, defined under "
            "address"))
    address = models.ForeignKey(
        AddressMunicipal, verbose_name=_('Building Address'), null=True,
        on_delete=models.PROTECT, related_name='%(class)s_address',
        help_text=_("May be null at the beginning but must be entered later"))
    start = models.DateField(
        _('Start Date'))
    end = models.DateField(
        _('Exit Date'), blank=True, null=True)
    counters = models.ManyToManyField(
        Device, verbose_name=_('Counter'), blank=True,
        related_name='%(class)s_counter')
    articles = models.ManyToManyField(
        Article, verbose_name=_('Article'),
        related_name='%(class)s_articles')
    number_of_counters = models.PositiveSmallIntegerField(
        _('Number of counters'), default=0, editable=False,
        help_text=_('Gets updated automatically by signals'))
    attachments = GenericRelation('core.Attachment')  # Enables reverse relation

    @property
    def invoice_address(self):
        addresses = PersonAddress.objects.filter(person=self.subscriber)
        invoice = addresses.filter(type=PersonAddress.TYPE.INVOICE)
        if invoice:
            return invoice.first()

        main = addresses.filter(type=PersonAddress.TYPE.MAIN)
        if main:
            return main.first()

        return addresses.first()

    @property
    def number(self):
        return f'S {self.id}'


    def save(self, *args, **kwargs):
        ''' Make number '''
        if not self.pk:
            # Nr
            self.nr = f'SC {self.tenant.id}-{self.id}'

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.subscriber}, {self.start} - {self.end}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'subscriber', 'start', 'end', 'address'],
                name='unique_billing_subscription'
            )
        ]
        ordering = [
            'subscriber__alt_name', 'subscriber__company',
            'subscriber__last_name', 'subscriber__first_name']
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')


class SubscriptionArchive(TenantAbstract):    
    subscriber_number = models.CharField(
        _('Abo Nr'), max_length=50)
    subscriber_name = models.CharField(
        _('Name'), max_length=200, blank=True, null=True)        
    street_name = models.CharField(
        _('Strasse'), max_length=200, blank=True, null=True)
    zip_city = models.CharField(
        _('PLZ Ort'), max_length=200, blank=True, null=True)
    tarif = models.PositiveSmallIntegerField(
        _('Tarif'), blank=True, null=True)
    period = models.PositiveSmallIntegerField(
        _('Period'), blank=True, null=True)
    tarif_name = models.CharField(
        _('Bez.'), max_length=200, blank=True, null=True)
    consumption = models.FloatField(
        _('Base'), blank=True, null=True)
    amount = models.DecimalField(
        _('Amount'), max_digits=10, decimal_places=2,
        blank=True, null=True)
    amount_gross = models.DecimalField(
        _('Amount incl. VAT'), max_digits=10, decimal_places=2,
        blank=True, null=True)


# Counters
class Measurement(TenantAbstract):
    counter = models.ForeignKey(
        Device, verbose_name=_('Counter'),
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    route = models.ForeignKey(
        Route, verbose_name=_('Route'),
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    datetime_previous = models.DateTimeField(
        _('Previous Date and Time'), blank=True, null=True)
    value_previous = models.FloatField(
        _('Previous Value'), blank=True, null=True,
        help_text=('Previous counter value'))
    value_max = models.FloatField(
        _('Min. Value'), blank=True, null=True,
        help_text=('Max counter value'))
    value_min = models.FloatField(
        _('Max. Value'), blank=True, null=True,
        help_text=('Min counter value'))

    # import
    datetime = models.DateTimeField(
        _('Date and time'))
    datetime_reference = models.DateTimeField(
        _('Date and time'), blank=True, null=True)
    value = models.FloatField(
        _('Value'), blank=True, null=True,
        help_text=('Actual counter value'))
    consumption = models.FloatField(
        _('Consumption'), blank=True, null=True,
        help_text=('Consumption = value - value_previous'))
    current_battery_level = models.FloatField(
        _('Battery Level'), blank=True, null=True,
        help_text=_('number of recommended periods for using'))

    # not used
    status = models.CharField(
        max_length=50, blank=True, null=True)
    remark = models.CharField(
        max_length=200, blank=True, null=True)
    bemerkung = models.CharField(
        max_length=200, blank=True, null=True)
    manufacturer = models.CharField(
        max_length=200, blank=True, null=True)
    radio_nr = models.CharField(
        max_length=50, blank=True, null=True)
    radio_manufacturer = models.CharField(
        max_length=200, blank=True, null=True)
    radio_version = models.CharField(
        max_length=20, blank=True, null=True)

    # for efficiency analysis, automatically updated
    address = models.ForeignKey(
        AddressMunicipal, verbose_name=_('Address'),
        on_delete=models.PROTECT, related_name='%(class)s_address')
    period = models.ForeignKey(
        Period, verbose_name=_('Period'),
        on_delete=models.PROTECT, related_name='%(class)s_period')
    subscription = models.ForeignKey(
        Subscription, verbose_name=_('Subscription'),
        on_delete=models.PROTECT, related_name='%(class)s_subscriber')
    consumption_previous = models.FloatField(
        _('Consumption'), blank=True, null=True)

    def __str__(self):
        return f'{self.route}, {self.counter}, {self.datetime}'

    class Meta:
        '''
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'counter', 'route', 'datetime'],
                name='unique_measurement'
            )
        ]
        '''
        ordering = [
            '-route__period__end', 'counter__number']
        verbose_name = _('Measurement')
        verbose_name_plural = _('Measurements')
