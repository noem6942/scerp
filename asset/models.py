'''
asset/models

see https://github.com/dalasidaho/asset_management
'''
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TenantAbstract


class STATUS(models.TextChoices):
    RECEIVED = 'REC', _('Received')  # Device added to inventory
    IN_STOCK = 'STK', _('In Stock')  # Device available in inventory
    DEPLOYED = 'DPL', _('Deployed')  # Device issued for use
    MOUNTED = 'MNT', _('Mounted')  # Device mounted on a wall, house etc.
    CALIBRATED = 'CAL', _('Calibrated')  # Device verified and adjusted for accuracy
    TRANSFERRED = 'TRF', _('Transferred')  # Device moved to a new user/project
    MAINTENANCE = 'MTN', _('Under Maintenance')  # Device undergoing service
    DECOMMISSIONED = 'DCM', _('Decommissioned')  # Device no longer in use
    DISPOSED = 'DSP', _('Disposed')  # Device removed permanently, "Entsorgt"
    LOST = 'LST', _('Lost')  # Device reported as missing
    STOLEN = 'STN', _('Stolen')  # Device reported as stolen


class Department(TenantAbstract):
    """ Model representing set department for customer or Tracker
    """
    name = models.CharField(
        max_length=50, blank=False, null=False)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class DeviceLocation(TenantAbstract):
    """Model representing set location/site for customer or device
    """
    name = models.CharField(
        _("name"), max_length=50, blank=False, null=False)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        """
        String for representing the DeviceLocation object (in Admin site etc.)
        """
        return self.name

    class Meta:
        ordering = ['id']
        verbose_name = "Location"
        verbose_name_plural = "Locations"


class Customer(TenantAbstract):
    """ Model representing an Customer.
    """
    first_name = models.CharField(
        _("first name"), max_length=100)
    last_name = models.CharField(
        _("last name"), max_length=100)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return '%s, %s' % (self.last_name, self.first_name)

    class Meta:
        ordering = ['last_name']


class Category(TenantAbstract):
    """ Model representing a devices type
    """
    name = models.CharField(
        _("name"), max_length=200, help_text="Laptop / desktop etc")
    code = models.CharField(
        _("Code"), max_length=50, blank=True, null=True,
        help_text="Laptop / desktop etc")
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Label description"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='unique_name_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_code_per_tenant'
            )
        ]
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")


class Model(TenantAbstract):
    """ Model representing a devices model
    """
    # Base
    name = models.CharField(
        _("name"), max_length=200, help_text="Enter a hardware Model")
    category = models.ForeignKey(
        # remove blank later
        Category, on_delete=models.CASCADE)
    description = models.TextField(
        _("description"), blank=True, null=True,
        help_text="Enter a hardware Model")
    purchace_price = models.FloatField(
        _("Purchase Price"), null=True, blank=True,
        help_text=_("The initial purchase price of the asset."))
    warranty_years = models.FloatField(
        null=True, blank=True, verbose_name="Warranty End")

    # Size
    length_mm = models.PositiveIntegerField(
        _("Length (mm)"), null=True, blank=True,
        help_text=_("Enter the length of the device in millimeters.")
    )
    width_mm = models.PositiveIntegerField(
        _("Width (mm)"), null=True, blank=True,
        help_text=_("Enter the width of the device in millimeters.")
    )
    height_mm = models.PositiveIntegerField(
        _("Height (mm)"), null=True, blank=True,
        help_text=_("Enter the height of the device in millimeters.")
    )
    diameter_mm = models.PositiveIntegerField(
        _("Diameter (mm)"), null=True, blank=True,
        help_text=_("Enter the diameter of the device in millimeters (if applicable).")
    )
    size_remark = models.CharField(
        _("Size Remark"), max_length=100, blank=True, null=True,
        help_text=_("Additional remarks or comments about the size.")
    )

    # Label fields for internal categorization
    label_1 = models.CharField(
        _("Label 1"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_2 = models.CharField(
        _("Label 2"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_3 = models.CharField(
        _("Label 3"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_4 = models.CharField(
        _("Label 4"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )

    def __str__(self):
        return f"{self.category.name}: {self.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'category', 'name'],
                name='unique_name_category_per_tenant'
            )
        ]
        ordering = ['name']


class Device(TenantAbstract):
    """ Model representing a devices (details).
    """
    # Base
    serial_number = models.CharField(
        _("Serial Number or Id"), max_length=50)
    model = models.ForeignKey(
        Model, on_delete=models.CASCADE)
    responsible = models.ForeignKey(
        Department, on_delete=models.SET_NULL, blank=True, null=True)
    tag = models.CharField(
        max_length=50, null=True, blank=True)
    status = models.CharField(
        max_length=3, choices=STATUS.choices,
        help_text='Gets updated automatically')
    location = models.ForeignKey(
        DeviceLocation, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Location"),
        help_text='Gets updated automatically')
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='customer', verbose_name=_("Customer"),
        help_text=_('Gets updated automatically')
    )

    # Details
    year = models.PositiveSmallIntegerField(
        _("Year"), null=True, blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        help_text=_("Enter a year between 1900 and 2100."),
    )
    batch = models.CharField(
        _("Batch"), max_length=50, null=True, blank=True,
        help_text=_("Batch or order id"),
    )
    registration_number = models.CharField(
        _("Registration number"), max_length=50, null=True, blank=True,
        help_text=_("Registration number of device"),
    )
    batch = models.CharField(
        _("Batch"), max_length=50, null=True, blank=True,
        help_text=_("Batch or order id"),
    )

    # Label fields for internal categorization
    label_1 = models.CharField(
        _("Label 1"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_2 = models.CharField(
        _("Label 2"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_3 = models.CharField(
        _("Label 3"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_4 = models.CharField(
        _("Label 4"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )

    def __str__(self):
        return f"{self.model.name} {self.serial_number}"

    class Meta:
        ordering = ['model__category', 'model__name', 'serial_number']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'model', 'serial_number'],
                name='unique_model_serial_number_per_tenant'
            )
        ]
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")


class EventLog(TenantAbstract):
    """
    Model representing the assignment or reassignment of a device to a customer.
    """
    date = models.DateField(_("Date"), default=timezone.now)
    status = models.CharField(
        max_length=3, choices=STATUS.choices, default=STATUS.IN_STOCK,
        help_text='Gets updated automatically')
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Customer"),
        related_name='event_log_customer',
    )
    location = models.ForeignKey(
        DeviceLocation, on_delete=models.SET_NULL, blank=True, null=True
    )
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        verbose_name=_("Device"),
        related_name='event_log_device',
    )

    def __str__(self):
        return f"{self.modified_at.strftime('%B %d, %Y, %H:%M')}, {self.device}"

    class Meta:
        ordering = ['-date', '-modified_at']
        verbose_name = _("Event Log")
        verbose_name_plural = _("Event Logs")


class CounterCategory(TenantAbstract):
    """ Counting Events
    """
    name = models.CharField(
        _("name"), max_length=200, help_text="Laptop / desktop etc")
    code = models.CharField(
        _("Code"), max_length=50, blank=True, null=True,
        help_text=_("Water, Energy etc."))
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Label description"))

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='unique_counter_name_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_counter_code_per_tenant'
            )
        ]
        ordering = ['name']


class CounterUnit(TenantAbstract):
    """ Units for counter
    """
    name = models.CharField(
        _("name"), max_length=200, help_text="Laptop / desktop etc")
    code = models.CharField(
        _("Code"), max_length=50, blank=True, null=True,
        help_text=_("Water, Energy etc."))
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Description"))

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='unique_unit_name_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_unit_code_per_tenant'
            )
        ]
        ordering = ['name']


class CounterLog(TenantAbstract):
    """
    Model representing counting events
    """
    # Base
    category = models.ForeignKey(
        CounterCategory, on_delete=models.CASCADE,
        verbose_name=_("Category"),
        related_name='counter_log',
    )
    unit = models.ForeignKey(
        CounterUnit, on_delete=models.CASCADE,
        verbose_name=_("Unit"),
        related_name='counter_unit',
    )
    measured_at = models.DateTimeField(
        _("Measured at"))
    value = models.FloatField(
        _("Value"), blank=True, null=True)
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        verbose_name=_("Device"),
        related_name='counter_log_device',
    )

    # Label fields for internal categorization
    label_1 = models.CharField(
        _("Label 1"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_2 = models.CharField(
        _("Label 2"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_3 = models.CharField(
        _("Label 3"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )
    label_4 = models.CharField(
        _("Label 4"), max_length=100, null=True, blank=True,
        help_text=_("Iinternal category or label for categorization.")
    )

    def __str__(self):
        return f"{self.modified_at.strftime('%B %d, %Y, %H:%M')}, {self.device}"

    class Meta:
        ordering = ['category', '-measured_at']
        verbose_name = _("Counter Log")
        verbose_name_plural = _("Counter Logs")
