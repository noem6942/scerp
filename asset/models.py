'''
asset/models

see https://github.com/dalasidaho/asset_management
'''
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import (
    TenantAbstract, Person, AddressMunicipal, Dwelling, Room)
from scerp.mixins import primary_language


class DEVICE_STATUS(models.TextChoices):
    RECEIVED = 'REC', _('Received')  # Device added to inventory
    IN_STOCK = 'STK', _('In Stock')  # Device available in inventory
    DEPLOYED = 'DPL', _('Deployed')  # Device issued for use
    CALIBRATED = 'CAL', _('Calibrated')  # Device verified and adjusted for accuracy
    MOUNTED = 'MNT', _('Mounted')  # Device mounted on a wall, house etc.
    DEMOUNTED = 'DMT', _('De-Mountied')  # Device currently not in function
    MAINTENANCE = 'MTN', _('Under Maintenance')  # Device undergoing service
    DECOMMISSIONED = 'DCM', _('Decommissioned')  # Device no longer in use
    DISPOSED = 'DSP', _('Disposed')  # Device removed permanently, "Entsorgt"
    LOST = 'LST', _('Lost')  # Device reported as missing
    STOLEN = 'STN', _('Stolen')  # Device reported as stolen


class AssetCategory(TenantAbstract):
    '''
    aligend to cashCtrl; we don't use parents
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text=_("Code"))
    name = models.JSONField(
        _('Name'), blank=True,  null=True,  # null necessary to handle multi languages
        help_text=_("The name of the title (i.e. the actual title)."))

    class Meta:
        ordering = ['code']
        verbose_name = _('Asset Category')
        verbose_name_plural = _('Asset Categories')

    def __str__(self):
        name = primary_language(self.name)
        return name if name else self.code


class Device(TenantAbstract):
    """ Device representing Asset in accounting,
        financial data is set in accounting (if wanted)
    """
    # Base
    code = models.CharField(
        _('Code'), max_length=50, db_index=True,
        help_text=_(
            'Internal code for scerp. '
            'This is also transferred to water counter software'))
    name = models.CharField(
        _('Name'), max_length=100, blank=True, null=True)
    category = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT,
        related_name='%(class)s_category',
        verbose_name=_('Category'), help_text=_("The asset's category."))
    date_added = models.DateField(
        _("Date added"),
        help_text=_("The date when the fixed asset has been added."))
    status = models.CharField(
        max_length=3, choices=DEVICE_STATUS.choices, null=True, blank=True,
        help_text='Gets updated automatically')
    description = models.JSONField(
        _('Description'), null=True, blank=True,
        help_text=_(
            "A description of the article. For localized text, use XML format: "
            "<values><de>German text</de><en>English text</en></values>."))
    warranty_months = models.PositiveSmallIntegerField(
        _('Warranty'), null=True, blank=True,
        help_text=_("Warranty in months"))
    date_disposed = models.DateField(
        _("Date disposed"), blank=True, null=True,
        help_text=_("The date of the disposal."))
    number = models.CharField(
        _("Number or Id"), max_length=50, null=True, blank=True)
    serial_number = models.CharField(
        _("Serial Number"), max_length=50, null=True, blank=True)
    tag = models.CharField(
        max_length=50, null=True, blank=True)
    registration_number = models.CharField(
        _("Registration number"), max_length=50, null=True, blank=True,
        help_text=_("Registration number of device"),
    )
    batch = models.CharField(
        _("Batch"), max_length=50, null=True, blank=True,
        help_text=_("Batch or order id"),
    )
    obiscode = models.CharField(
        _('OBIS Code'), max_length=20, blank=True, null=True,
        help_text='for counters, default: 8-0:1.0.0')
    attachments = GenericRelation('core.Attachment')  # Enables reverse relation

    def get_status(self, date=None):
        ''' returns last event <= date '''
        queryset = EventLog.objects.filter(device=self)
        if date:
            queryset = queryset.filter(date__lte=date)
        return queryset.order_by('date').last()

    def __str__(self):
        name = self.code
        if self.name:
            name += ' ' + self.name
        return name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'category', 'code', 'number'],
                name='unique_device_per_tenant'
            )
        ]
        ordering = ['name']
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")


class EventLog(TenantAbstract):
    """
    Model representing the assignment or reassignment of a device to a customer.
    """
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        verbose_name=_("Device"),
        related_name='event_log_device',
    )
    datetime = models.DateTimeField(_("Date and Time"), default=timezone.now)
    status = models.CharField(
        max_length=3, choices=DEVICE_STATUS.choices,
        default=DEVICE_STATUS.IN_STOCK,
        help_text='Gets updated automatically')
    customer = models.ForeignKey(
        Person, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Person"),
        related_name='%(class)s_customer',
        help_text=_(
            "Leave empty if irrelevant (e.g. counters)."
            "Do not use for counters."))
    address = models.ForeignKey(
        AddressMunicipal, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Address"),
        related_name='%(class)s_customer',
        help_text=_(
            "Mandatory for counters, "
            "leave empty if irrelevant (e.g. room specified)"))
    dwelling = models.ForeignKey(
        Dwelling, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Dwelling"),
        related_name='%(class)s_dwelling',
        help_text=_("leave empty if irrelevant (e.g. room specified)"))
    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Room"),
        related_name='%(class)s_room',
        help_text=_("leave empty if irrelevant (e.g. building specified)"))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update status in counter
        event = EventLog.objects.filter(
            device=self.device).order_by('datetime').last()
        self.device.status = event.status
        self.device.save()

    def __str__(self):
        return f"{self.modified_at.strftime('%B %d, %Y, %H:%M')}, {self.device}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'device', 'datetime', 'status'],
                name='unique_event_log_per_tenant'
            )
        ]
        ordering = ['-datetime', '-modified_at']
        verbose_name = _("Event Log")
        verbose_name_plural = _("Event Logs")
