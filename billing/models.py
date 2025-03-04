from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounting.models import Article
from core.models import TenantAbstract, AddressCategory, Person, Building
from asset.models import AssetCategory, Device


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
    confidence_min = models.DecimalField(
        _('Confidence Min.'), max_digits=3, decimal_places=2, default=0,
        help_text=_(
            "Min confidence factor based on previous period, "
            "e.g. 0.5: value must be ≥ 5 if previous value was 10"))
    confidence_max = models.DecimalField(
        _('Confidence Max.'), max_digits=3, decimal_places=2, default=2,
        help_text=_(
            "Max confidence factor based on previous period, "
            "e.g. 2: value must be ≤ 20 if previous value was 10"))

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

    class ENERGY_TYPE(models.TextChoices):
        WATER = 'WA', _('Water')
        GAS = 'G', _('Gas')
        ELECTRICITY = 'E', _('Electricity')

    name = models.CharField(
        _('name'), max_length=50, help_text=_("name"))
    period = models.ForeignKey(
        Period, verbose_name=_('Period'),
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    type = models.CharField(
        max_length=2, choices=ENERGY_TYPE.choices,
        help_text=_("Energy type"))
    asset_category = models.ForeignKey(
        AssetCategory, verbose_name=_('Category'),
        on_delete=models.PROTECT,
        help_text=_("Category"))
    address_categories = models.ManyToManyField(
        AddressCategory, verbose_name=_('Address Categories'), blank=True, 
        help_text=_(
            "Area Categories to include, leave empty if to include all"))
    subscribers = models.ManyToManyField(
        Person, verbose_name=_('Subscribers'), blank=True,
        help_text=_(
            "Subscribers, leave empty to include all in scope"))
    status = models.CharField(
        max_length=4, choices=STATUS.choices, default=STATUS.INITIALIZED,
        help_text=_("Current status of the routing."))
    is_default = models.BooleanField(
        _('Default route'), default=True,
        help_text=_("Inside default schedule"))
    attachments = GenericRelation('core.Attachment')  # Enables reverse relation

    def __str__(self):
        return f'{self.period}, {self.name}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'period', 'name'],
                name='unique_billing_route'
            )
        ]
        ordering = ['-period__end', 'period__code', 'name']
        verbose_name = _('Route')
        verbose_name_plural = _('Routes')


# Counters
class Measurement(TenantAbstract):
    counter = models.ForeignKey(
        Device, verbose_name=_('Counter'),
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    route = models.ForeignKey(
        Route, verbose_name=_('Period'),
        on_delete=models.PROTECT, related_name='%(class)s_counter')
    datetime = models.DateTimeField(
        _('Date and time'))
    datetime_previous = models.DateTimeField(
        _('Previous Date and time'), blank=True, null=True)
    value = models.FloatField(
        _('Value'), help_text=('Actual counter value'))
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
    current_battery_level = models.FloatField(
        blank=True, null=True)

    def __str__(self):
        return f'{self.route}, {self.counter}, {self.datetime}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'counter', 'route', 'datetime'],
                name='unique_measurement'
            )
        ]
        ordering = [
            '-route__period__end', 'counter__number']
        verbose_name = _('Measurement')
        verbose_name_plural = _('Measurements')


# Subscriptions
class Subscription(TenantAbstract):
    subscriber = models.ForeignKey(
        Person, verbose_name=_('Subscriber'),
        on_delete=models.PROTECT, related_name='%(class)s_subscriber',
        help_text=_(
            "subscriber / inhabitant / owner"
            "invoice address may be different to subscriber, defined under "
            "address"))
    recipient = models.ForeignKey(
        Person, verbose_name=_('Recipient'), blank=True, null=True,
        on_delete=models.PROTECT, related_name='%(class)s_recipient',
        help_text=_(
            "invoice person / company if different from subscriber"))
    building = models.ForeignKey(
        Building, verbose_name=_('Building'),
        on_delete=models.PROTECT, related_name='%(class)s_building')
    start = models.DateField(_('Start Date'))
    end = models.DateField(_('Exit Date'), blank=True, null=True)
    articles = models.ManyToManyField(
        Article, verbose_name=_('Article'),
        related_name='%(class)s_articles')

    def __str__(self):
        return f'{self.subscriber}, {self.start} - {self.end}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'subscriber', 'start', 'end', 'building'],
                name='unique_billing_subscription'
            )
        ]
        ordering = [
            'subscriber__alt_name', 'subscriber__company', 
            'subscriber__last_name', 'subscriber__first_name']
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
