'''
billing/models.py

Data Model (Draft)

Workflow:
1. A subscription is created with EGID address and description which are unique
   Use tags to classify subscriptions.
2. A counter is created.
3. The subscription is updated with counter assigned. Now the subscription is
   functional.

Measuring:
1. Create a period (usually semi-annual)
2. Create a route (usually one per period) and check all tags assigned
   (usually all). Apply filters (e.g.

Every counter in use has a subscription --> foreign counter is unique
Every subscription has a subscriber

'''
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounting.models import (
    Article, OrderCategoryOutgoing, OrderContract, OutgoingOrder
)
from core.models import (
    TenantAbstract, AddressMunicipal, Area, Person, PersonAddress)
from asset.models import AssetCategory, Device, Unit


# use this postfix to specify article_nr for unit = Day
ARTICLE_NR_POSTFIX_DAY = '-D'

# use this to default header for billing invoices
SETUP_HEADER = '''<small>
Objekt: {building}{building_notes}{description}, {subscription_id}<br>
Periode: {start} bis {end}<br>
Verbrauch letzte Periode: {consumption} m³, Zählerstand Id {counter_id} alt {counter_old}, neu {counter_new}
<small>'''


class Setup(TenantAbstract):
    code = models.CharField(
        _('Code'), max_length=50,
        help_text=_("e.g. water, semi annual"))
    name = models.CharField(
        _('Name'), max_length=50, help_text=_("name"))
    header = models.TextField(
        _('Header'), default=SETUP_HEADER,
        help_text=_("name"))
    description = models.CharField(
        _('Description'), max_length=200, blank=True, null=True,
        help_text=('default invoice description, usually empty'))
    show_partner = models.BooleanField(
        _('Show partner'), default=True,
        help_text=_("Show partner on invoice bill"))
    order_contract = models.ForeignKey(
        OrderContract, on_delete=models.PROTECT, null=True,
        verbose_name=_('Invoice Contract'),
        related_name='%(class)s_order_contract')
    order_category = models.ForeignKey(
        OrderCategoryOutgoing, on_delete=models.PROTECT,
        verbose_name=_('Order Category'), null=True,
        related_name='%(class)s_order_category')
    contact = models.ForeignKey(
        Person, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Clerk'), related_name='%(class)s_person',
        help_text=_('Clerk, leave empty if defined in category'))
    rounding_digits = models.PositiveSmallIntegerField(
        _('Rounding Digits'), default=0,
        help_text=_('Rounding consumption on invoice'))

    def __str__(self):
        return self.code

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_billing_setup'
            )
        ]
        ordering = ['code']
        verbose_name = _('Setup')
        verbose_name_plural = _('Setups')


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


# Subscriptions
class Subscription(TenantAbstract):
    subscriber_number = models.CharField(
        _('Abo Nr'), max_length=50, blank=True, null=True,
        help_text=('Old subscription number, leave empty'))
    description = models.CharField(
        _('Description'), max_length=200, blank=True, null=True,
        help_text=(
            'leave empty, use for exceptions that should be on the invoice'))
    tag = models.CharField(
        _('Tag'), max_length=50, blank=True, null=True,
        help_text=('Tag a subscriber, e.g. to invoice only these'))
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
    recipient = models.ForeignKey(
        Person, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Invoice recipient'),
        related_name='%(class)s_recipient',
        help_text=_("Invoice recipient if not subscriber."))
    dossier = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Dossier'), related_name='%(class)s_dossier',
        help_text=_("main subscription if multiple counters"))
    address = models.ForeignKey(
        AddressMunicipal, verbose_name=_('Building Address'), null=True,
        on_delete=models.PROTECT, related_name='%(class)s_address',
        help_text=_("May be null at the beginning but must be entered later"))
    start = models.DateField(
        _('Start Date'), help_text=_("Start date of subscription."))
    end = models.DateField(
        _('Exit Date'), blank=True, null=True)
    counter = models.ForeignKey(
        Device, on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Counter'), related_name='%(class)s_counter',
        help_text=_("main subscription if multiple counters"))
    attachments = GenericRelation('core.Attachment')  # Enables reverse relation

    @property
    def invoice_address(self):
        # Get Field
        if self.recipient:
            # First check point, usually empty
            addresses = PersonAddress.objects.filter(person=self.recipient)
        else:
            # Take subscriber
            addresses = PersonAddress.objects.filter(person=self.subscriber)

        # Get address
        invoice = addresses.filter(type=PersonAddress.TYPE.INVOICE)
        if invoice:
            return invoice.first()

        main = addresses.filter(type=PersonAddress.TYPE.MAIN)
        if main:
            return main.first()

        return addresses.first()

    @property
    def number(self):
        return f'S-{self.id}'

    @property
    def invoices(self):
        invoices = [
            measurement.invoice
            for measurement in Measurement.objects.filter(
                subscription=self
            ).exclude(invoice=None).order_by('-datetime')
        ]
        return invoices

    @property
    def measurements(self):
        return Measurement.objects.filter(
            subscription=self).order_by('datetime')

    def __str__(self):
        name = f'{self.address}'
        if self.description:
            name += ' - ' + self.description
        return name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'address', 'description', 'is_inactive'],
                name='unique_billing_subscription'
            )
        ]
        ordering = [
            'subscriber__alt_name', 'subscriber__company',
            'subscriber__last_name', 'subscriber__first_name',
            'address__zip', 'address__stn_label', 'address__adr_number', 'id']
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')


class SubscriptionArticle(TenantAbstract):
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE,
        verbose_name=_('Subscription'),
        related_name='%(class)s_subscription')
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, null=True,
        verbose_name=_('Article'), related_name='%(class)s_article')
    quantity = models.PositiveSmallIntegerField(
        _('Quantity'), blank=True, null=True,
        help_text=(
            "Leave blank if unit is m3 / quantity derived from measurement")
    )

    def __str__(self):
        return f'{self.subscription}, {self.article}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'subscription', 'article'],
                name='unique_subscription_article'
            )
        ]


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
        Period, on_delete=models.PROTECT,
        verbose_name=_('Period'), related_name='%(class)s_period')
    setup = models.ForeignKey(
        Setup, on_delete=models.PROTECT, null=True,
        verbose_name=_('Setup'), related_name='%(class)s_setup')
    period_previous = models.ForeignKey(
        Period, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Previous Period'),
        related_name='%(class)s_last_period',
        help_text=_("This is used to calculate the consumption."))
    comparison_periods = models.ManyToManyField(
        Period, blank=True, verbose_name=_('Comparison Periods'),
        related_name='comparison_periods',
        help_text=_(
            "Periods' measurements used to report on all invoices. "
            "If none is given, last one is taken."))
    areas = models.ManyToManyField(
        Area, verbose_name=_('Areas'), blank=True,
        help_text=_(
            "Areas that should be included, "
            "leave empty to include all in scope"))
    addresses = models.ManyToManyField(  # discontinue
        AddressMunicipal, verbose_name=_('Addresses'), blank=True,
        help_text=_(
            "Addresses that should be included, "
            "leave empty to include all in scope"))
    subscriptions = models.ManyToManyField(  # new
        Subscription, verbose_name=_('Subscriptions'), blank=True,
        help_text=_(
            "Subscriptions that should be included, "
            "leave empty to include all in scope"))
    asset_categories = models.ManyToManyField(
        AssetCategory, verbose_name=_('Categories'), blank=True,
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

    def get_comparison_periods(self):
        queryset = self.comparison_periods.all().order_by('-end')
        if queryset:
            return queryset
        return [self.period_previous]  # take last period

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


# Counters
class Measurement(TenantAbstract):
    counter = models.ForeignKey(
        Device, verbose_name=_('Counter'),
        blank=True, null=True,  # only for archive
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    route = models.ForeignKey(
        Route, verbose_name=_('Route'), blank=True, null=True,
        on_delete=models.PROTECT, related_name='%(class)s_counter')

    # measurement data used for bill
    datetime = models.DateTimeField(
        _('Reference Date'), db_index=True,
        help_text=_('Date and time, reference measurement'))
    value = models.FloatField(
        _('Value'), blank=True, null=True,
        help_text=('Value at reference measurement'))

    # for billing and statistics
    consumption = models.FloatField(
        _('Consumption'), blank=True, null=True,
        help_text=('Consumption = value - value_previous'))

    # latest data
    datetime_latest = models.DateTimeField(
        _('Date and time, latest'), blank=True, null=True)
    value_latest = models.FloatField(
        _('Value'), blank=True, null=True,
        help_text=('Actual counter value'))
    consumption_latest = models.FloatField(
        _('Consumption latest'), blank=True, null=True,
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
        AddressMunicipal, verbose_name=_('Address'), blank=True, null=True,
        on_delete=models.PROTECT, related_name='%(class)s_address')
    period = models.ForeignKey(
        Period, verbose_name=_('Period'),
        on_delete=models.PROTECT, related_name='%(class)s_period')
    subscription = models.ForeignKey(
        Subscription, verbose_name=_('Subscription'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_subscriber')

    # prevent double charging
    invoice = models.ForeignKey(
        OutgoingOrder, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_('Invoice'), related_name='measurement_invoice',
        help_text=_("Related invoice")
    )

    @property
    def value_old(self):
        if self.value is None or self.consumption is None:
            return None
        return self.value - self.consumption

    def __str__(self):
        if self.subscription:
            tag = self.subscription.tag or ''
            if tag:
                tag += ', '

            desc = self.subscription.description or ''
            if desc:
                desc = ', ' + desc

            return (
                f"{tag}{self.subscription.subscriber_number} "
                f"{self.subscription.subscriber}, {self.address}{desc}: "
                f"{self.route}, {self.counter}, {self.datetime}"
            )
        else:
            return  f"{self.route}, {self.counter}, {self.datetime} - Unassigned!"

    def save_consumption(self):
        # get previous_measurement
        previous_measurement = Measurement.objects.filter(
                tenant=self.tenant,
                counter=self.counter,
                datetime__lt=self.datetime
            ).order_by('datetime').last()
        if (previous_measurement
                and self.value is not None
                and previous_measurement.value is not None):
            self.consumption = self.value - previous_measurement.value
            self.save()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'counter', 'route', 'datetime'],
                name='unique_measurement'
            )
        ]
        ordering = [
            '-route__period__end', 'address__zip', 'address__stn_label',
            'address__adr_number', 'subscription__description']
        verbose_name = _('Measurement')
        verbose_name_plural = _('Measurements')


class MeasurementArchive(TenantAbstract):
    datetime = models.DateTimeField(
        _('Reference Date'), db_index=True,
        help_text=_('Date of File as specified in mex'))
    route = models.ForeignKey(
        Route, verbose_name=_('Route'),
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    data = models.JSONField(
        _('data'), blank=True, null=True,
        help_text=_("Get's automatically assigned.")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'datetime', 'route'],
                name='unique_measurement_archive'
            )
        ]
        ordering = ['-datetime']
        verbose_name = _('Measurement Archive')
        verbose_name_plural = _('Measurements Archive')


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
