# accounting/models.py
from enum import Enum
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.db import models, IntegrityError
from django.db.models import UniqueConstraint
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import (
    LogAbstract, NotesAbstract, Tenant, TenantAbstract, TenantSetup,
    TenantLogo, Country, Address, Contact, PersonAddress
)
from core.models import (
    Title as TitleCrm,
    PersonCategory as PersonCategoryCrm,
    Person as PersonCrm
)
from scerp.locales import CANTON_CHOICES
from scerp.mixins import get_code_w_name, primary_language
from .api_cash_ctrl import (
    URL_ROOT, FIELD_TYPE, DATA_TYPE, ROUNDING, TEXT_TYPE, COLOR, BOOK_TYPE,
    ORDER_TYPE, PERSON_TYPE)


# Definitions
class APPLICATION(models.TextChoices):
    CASH_CTRL = 'CC', 'Cash Control'


class TOP_LEVEL_ACCOUNT(models.TextChoices):
    '''Used for making unique categories, values are Decimals '''
    # CashCtrl
    ASSET = '1', 'ASSET'
    LIABILITY = '2', 'LIABILITY'
    EXPENSE = '3', 'EXPENSE'
    REVENUE = '4', 'REVENUE'
    BALANCE = '5', 'BALANCE'

    # OWN, comma to ensure unique number in cashCtrl
    PL_EXPENSE = '3.1', 'EXPENSE (PL)'  # Aufwand
    PL_REVENUE = '4.1', 'REVENUE (PL)'  # Ertrag
    IS_EXPENSE = '3.2', 'EXPENSE (IS)'  # Ausgaben
    IS_REVENUE = '4.2', 'REVENUE (IS)'  # Einnahmen

TOP_LEVEL_ACCOUNT_NRS = [Decimal(x.value) for x in TOP_LEVEL_ACCOUNT]



# CashCtrl Basics ------------------------------------------------------------
class APISetup(TenantAbstract):
    '''only restricted to admin!
        triggers signals.py past_save
        org_name, application is unique (cashCtrl)
        all cashCtrl entities have foreign key to APISetup
    '''
    org_name = models.CharField(
        'org_name', max_length=100, unique=True,
        help_text='name of organization as used in cashCtrl domain')
    api_key = models.CharField(
        _('api key'), max_length=100, help_text=_('api key'))
    application = models.CharField(
        _('application'), max_length=2, choices=APPLICATION.choices,
        default=APPLICATION.CASH_CTRL)
    initialized = models.DateTimeField(
        _('initialized'), max_length=100, null=True, blank=True,
        help_text=_('date and time when initialized'))
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
    is_default = models.BooleanField(
        _('Default setup'), default=True,
        help_text=_('use this setup for adding accounting data'))
    readonly_fields = ('api_key_hidden',)

    def __str__(self):
        return self.org_name

    @classmethod
    def get_setup(cls, tenant=None, tenant_id=None,**kwargs):
        ''' 
        get api_setup from different parameters
        currently only one accounting system --> derive only from tenant
        '''
        if tenant:
            return cls.objects.get(tenant=tenant, is_default=True)
        elif tenant_id:
            return cls.objects.get(tenant__id=tenant_id, is_default=True)        
        raise ValidationError('No tenant given')

    @property
    def url(self):
        return URL_ROOT.format(org=self.org_name)

    def get_custom_field_tag(self, code):
        ''' return xml tag that can be sent to cashCtrl '''
        try:
            field = CustomField.objects.get(tenant=self.tenant, code=code)
            return f"customField{field.c_id}"
        except:
            raise ValueError(f"'{code}' not existing.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['application', 'org_name'],
                name='unique_org_name_per_tenant'
            )
        ]
        ordering = ['tenant__name',]
        verbose_name = _('Accounting Setup')
        verbose_name_plural = _('Accounting Setups')


class AcctAppBase(models.Model):
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
    setup = models.ForeignKey(
        APISetup, verbose_name=_('Accounting Setup'),
        on_delete=models.CASCADE, related_name='%(class)s_setup',
        help_text=_('Account Setup used'))
    message = models.CharField(
        _('Message'), max_length=200, null=True, blank=True,
        help_text=_('Here we show error messages. Just be empty.'))
    is_enabled_sync = models.BooleanField(
        _("Enable Sync"), default=True,
        help_text="Disable sync with cashCtrl; useful for admin tasks.")
    sync_to_accounting = models.BooleanField(
        _("Sync to Accounting"), default=False,
        help_text=(
            "This records needs to be synched to cashctr, if the cycle is "
            "over it gets reset to False"))

    class Meta:
        abstract = True


class AcctApp(TenantAbstract, AcctAppBase):
    class Meta:
        abstract = True


# CashCtrl entities with foreign key to APISetup -----------------------------
class CustomFieldGroup(AcctApp):
    '''
    Create custom field group that is then sent to cashCtrl via signals
    '''
    FIELD_TYPE = [(x.value, x.value) for x in FIELD_TYPE]

    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('Name'), help_text="The name of the group.")
    type = models.CharField(
        _('Type'), max_length=50, choices=FIELD_TYPE,
        help_text='''
            The type of group, meaning: which module the group belongs to.
            Possible values: JOURNAL, ACCOUNT, INVENTORY_ARTICLE,
            INVENTORY_ASSET, ORDER, PersonCrm, FILE.''')

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'c_id'],
                name='unique_custom_field_group_setup'
            )
        ]
        ordering = ['type', 'code']
        verbose_name = _("Custom Field Group")
        verbose_name_plural = _("Custom Field Groups")


class CustomField(AcctApp):
    '''
    Create custom field that is then sent to cashCtrl via signals

        group is None allows the group field to be set to None temporarily
        if it starts as a string, so the pre_save signal can resolve and
        assign the correct instance.

    '''
    FIELD_TYPE = [(x.value, x.value) for x in FIELD_TYPE]
    DATA_TYPE = [(x.value, x.value) for x in DATA_TYPE]

    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    group_ref = models.CharField(
        _('Custom Field Group'), max_length=50, blank=True, null=True,
        help_text='internal reference for scerp used for getting foreign key')
    name = models.JSONField(
        _('Name'), help_text="The name of the field.")
    type = models.CharField(
        _("Field Type"), max_length=50, choices=FIELD_TYPE,
        help_text='''
            The type of group, meaning: which module the group belongs to.
            Possible values: JOURNAL, ACCOUNT, INVENTORY_ARTICLE,
            INVENTORY_ASSET, ORDER, PersonCrm, FILE.''')
    data_type = models.CharField(
        _("Data Type"), max_length=50, choices=DATA_TYPE,
        help_text='''
            The data type of the custom field. Possible values: TEXT, TEXTAREA,
            CHECKBOX, DATE, COMBOBOX, NUMBER, ACCOUNT, PERSON.''')
    description = models.JSONField(
        _('Description'), blank=True, null=True,
        help_text="Description of the field.")
    group = models.ForeignKey(
        CustomFieldGroup, verbose_name=_('Custom Field Group'),
        on_delete=models.CASCADE, blank=True, null=True,
        related_name='%(class)s_group',
        help_text=_('Internal reference'))
    is_multi = models.BooleanField(
        _("Is multi"), default=False,
        help_text="Is the custom field a multi-field?")
    values = models.JSONField(
        _('Values'), blank=True, null=True,
        help_text="Values the user can choose from, if the data type is COMBOBOX.")

    @property
    def custom_field_key(self):
        ''' return the key as used in cashCtrl api '''
        return f"customField{self.c_id}"

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'c_id'],
                name='unique_custom_setup_field'
            )
        ]
        ordering = ['group__code', 'code']
        verbose_name = _("Custom Field")
        verbose_name_plural = _("Custom Field")


class Location(AcctApp):
    '''Master, currently Read - only as bug in cashCtrl
    '''
    class TYPE(models.TextChoices):
        MAIN = 'MAIN', _('Headquarters')
        BRANCH = 'BRANCH', _('Branch Office')
        STORAGE = 'STORAGE', _('Storage Facility')
        OTHER = 'OTHER', _('Other / Tax')

    # Mandatory field
    name = models.CharField(max_length=100)
    type = models.CharField(
        _("Type"), max_length=50, choices=TYPE.choices, default=TYPE.MAIN,
        help_text=_("The type of location. Defaults to MAIN."))

    # Optional fields
    address = models.TextField(
        _("Address"), max_length=250, blank=True, null=True,
        help_text=_("The address of the location (street, house number, "
                    "additional info)."))
    zip = models.CharField(
        _("ZIP Code"), max_length=10, blank=True, null=True,
        help_text=_("The postal code of the location."))
    city = models.CharField(
        _("City"), max_length=100, blank=True, null=True,
        help_text=_("The town / city of the location."))
    country = models.CharField(
        _("Country"), max_length=3, default="CHE", blank=True, null=True,
        help_text=_("The country of the location, as an ISO 3166-1 alpha-3 code."))

    # Layout
    logo = models.ForeignKey(
        TenantLogo, verbose_name=_('Logo'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_logo',
        help_text=_('Logo to be used for accounting'))

    # Accounting
    bic = models.CharField(
        _("BIC"), max_length=11, blank=True, null=True,
        help_text=_("The BIC (Business Identifier Code) of your bank."))
    iban = models.CharField(
        _("IBAN"), max_length=32, blank=True, null=True,
        help_text=_("The IBAN (International Bank Account Number)."))
    qr_first_digits = models.PositiveIntegerField(
        _("QR First Digits"), blank=True, null=True,
        help_text=_("The first few digits of the Swiss QR reference. Specific "
                    "to Switzerland."))
    qr_iban = models.CharField(
        _("QR-IBAN"), max_length=32, blank=True, null=True,
        help_text=_("The QR-IBAN, used especially for QR invoices. Specific to "
                    "Switzerland."))
    vat_uid = models.CharField(
        _("VAT UID"), max_length=32, blank=True, null=True,
        help_text=_("The VAT UID of the company."))

    # Formats
    logo_file_id = models.IntegerField(
        _("Logo File ID"), blank=True, null=True,
        help_text=_("File ID for the company logo. Supported types: JPG, GIF, PNG."))
    footer = models.TextField(
        _("Footer Text"), blank=True, null=True,
        help_text=_("Footer text for order documents with limited HTML support."))

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'name', 'c_id'],
                name='unique_setup_location'
            )
        ]
        ordering = ['name']
        verbose_name = _("Location: Logo, Address, VAT, Codes, Formats etc. ")
        verbose_name_plural = f"{verbose_name}"


class FiscalPeriod(AcctApp):
    ''' FiscalPeriod '''
    name = models.CharField(
        _("Name"), max_length=30, blank=True, null=True,
        help_text=_(
            "The name of the fiscal period, required if isCustom is true."))
    start = models.DateTimeField(
        _("Start"), blank=True, null=True,
        help_text=_(
            "Start date of the fiscal period, required if isCustom is true."))
    end = models.DateTimeField(
        _("End"), blank=True, null=True,
        help_text=_(
            "End date of the fiscal period, required if isCustom is true."))
    is_closed = models.BooleanField(
        _("Is closed"), default=False,
        help_text="Check if fiscal period is closed.")
    is_current = models.BooleanField(
        _("Is current"), default=False,
        help_text="Check for current fiscal period.")

    def __str__(self):
        return self.name or f"Fiscal Period {self.pk}"

    def clean(self):
        if not self.start or not self.end:
            raise ValidationError(
                _("Custom periods require both a start and an end date."))
        if self.start > self.end:
            raise ValidationError(_("Start date cannot be after end date."))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'start', 'c_id'],
                name='unique_setup_period'
            )
        ]
        ordering = ['-start']
        verbose_name = _("Fiscal Period")
        verbose_name_plural = f"{_('Fiscal Periods')}"


class Currency(AcctApp):
    ''' Currency '''
    code = models.CharField(
        max_length=3,
        help_text=_("The 3-characters currency code, like CHF, EUR, etc."))
    description = models.JSONField(_('Description'), blank=True, null=True)
    rate = models.FloatField(_('Rate'), blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.code

    @classmethod
    def get_default_id(cls):
        """
        Returns the default currency if one is set; otherwise, returns None.
        """
        queryset = cls.objects.filter(is_default=True)
        return queryset.first().id if queryset else None

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_setup_currency'
            )
        ]
        ordering = ['code']
        verbose_name = _("Currency")
        verbose_name_plural = f"{_('Currencies')}"


class SequenceNumber(AcctApp):
    ''' SequenceNumber '''
    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'),  help_text=_("The name of the sequence number."),
        blank=True, null=True)
    pattern = models.CharField(
        _('pattern'),
        max_length=50,
        help_text=_(
            """The sequence number pattern, which consists of variables and
            arbitrary text from which a sequence number will be generated.
            Possible variables: $y = Current year. $m = Current month.
            $d = Current day. $ny = Sequence number, resets annually
            (on Jan 1st). $nm = Sequence number, resets monthly.
            $nd = Sequence number, resets daily. $nn = Sequence number,
            never resets. Example pattern: RE-$y$m$d$nd which may
            generate 'RE-2007151' (on July 15, 2020)."""))

    def save(self, *args, **kwargs):
        # Check mandatory code
        if not getattr(self, 'code', None):
            self.code = self.code = f"{self.c_id}, {self.pattern}"
        super().save(*args, **kwargs)

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'c_id'],
                name='unique_setup_sequence_number'
            )
        ]
        ordering = ['code']
        verbose_name = _("Sequence Number")
        verbose_name_plural = f"{_('Sequence Numbers')}"


class Unit(AcctApp):
    ''' Unit '''
    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), default=dict,
        help_text=_("The name of the unit ('hours', 'minutes', etc.)."))
    is_default = models.BooleanField(_("Is default"), default=False)

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'c_id'],
                name='unique_setup_unit'
            )
        ]
        ordering = ['code']
        verbose_name = _("Unit")
        verbose_name_plural = f"{_('Units')}"


class Text(AcctApp):
    ''' Text Blocks '''
    TEXT_TYPE = [(x.value, x.value) for x in TEXT_TYPE]

    name = models.CharField(
        _('Name'), max_length=200,
        help_text='A name to describe and identify the text template.')
    is_default = models.BooleanField(
        _('Is default'), default=False,
        help_text=_('use this setup for adding accounting data'))
    type = models.CharField(
        _('mode'), max_length=20, choices=TEXT_TYPE,
        help_text=_(
            '''The type of text template, meaning: Where the text template
                can be used. Possible values.'''))
    value = models.TextField(
        _('Text'),
        help_text=_(
            'The actual text template. This can contain limited HTML for '
            'styling.'))

    def __str__(self):
        return self.code

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'type', 'name'],
                name='unique_text_block'
            )
        ]
        ordering = ['type', 'name']
        verbose_name = _("Text Block")
        verbose_name_plural = f"{_('Text Blocks')}"


class CostCenterCategory(AcctApp):
    ''' CostCenterCategory '''
    name = models.JSONField(
        _('Name'), help_text="The name of the cost center category.")
    number = models.DecimalField(
        _('Number'), max_digits=20, decimal_places=2,
        help_text=_("The number of the cost center category."))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_parent',
        help_text=_('The parent category.'))

    def __str__(self):
        return f"{self.number} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'number', 'c_id'],
                name='unique_setup_cost_center_category'
            )
        ]
        ordering = ['number']
        verbose_name = _("Cost Center Category")
        verbose_name_plural = _("Cost Center Categories")


class CostCenter(AcctApp):
    ''' CostCenter '''
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the cost center.")
    number = models.DecimalField(
        _('Number'), max_digits=20, decimal_places=2,
        help_text=_(
            '''The cost center number. Must be numeric but can contain
               a decimal point.'''))
    category = models.ForeignKey(
        CostCenterCategory, verbose_name=_('Category'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_category')
    target_max = models.DecimalField(
        _('Target Maximum'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_(
            'The target maximum balance the cost center should to stay beneath '
            'end of the fiscal period. This will be displayed in the Targets '
            'report, comparing your target to the actual balance. Please '
            'first switch to the desired fiscal period to set the target for '
            'that period.'))
    target_min = models.DecimalField(
        _('Target min'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_(
            'The target minimum balance you hope this cost center to hit by the '
            'end of the fiscal period. This will be displayed in the Targets '
            'report, comparing your target to the actual balance. Please '
            'first switch to the desired fiscal period to set the target for '
            'that period.'))

    def __str__(self):
        return f"{self.number} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'number', 'c_id'],
                name='unique_setup_cost_center'
            )
        ]
        ordering = ['number']
        verbose_name = _("Cost Center")
        verbose_name_plural = _("Cost Centers")


class AccountCategory(AcctApp):
    '''
    Actual Account Category in cashCtrl
    AccountCategory and Account must be loaded before Tax and Rounding
    '''
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the cost center.")
    number = models.FloatField(
        _('Number'), help_text=_("The name of the account category."))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='%(class)s_parent',
        help_text=_('The parent category.'))
    is_scerp = models.BooleanField(
        _("Is scerp"), blank=True, null=True,
        help_text=_("true if account created by scerp"))

    @property
    def is_top_level_account(self):
        return Decimal(str(self.number)) in TOP_LEVEL_ACCOUNT_NRS

    def __str__(self):
        return f"{self.number} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                # Generous, as cashCtrl allows identical numbers.
                fields=['setup', 'number', 'c_id'],
                name='unique_setup_account_category'
            )
        ]
        # Lexicographic ordering
        ordering = [Cast('number', models.CharField())]
        verbose_name = ('Account Category')
        verbose_name_plural = _('Account Categories')


class Account(AcctApp):
    '''Actual cashCtrl account
        triggers signals.py post_save
       CUSTOM: gets transferred to JSON when uploaded and back
               (field_name, custom_field__code)
       Cost center allocations can only be transferred from scerp to cashCtrl
    '''
    CUSTOM = [
        ('function', 'account_function'),
        ('hrm', 'account_hrm'),
        ('budget', 'account_budget')
    ]
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the account.")
    category = models.ForeignKey(
        AccountCategory, blank=True, null=True,  # allow for maintenance
        verbose_name=_('Account Category'),
        on_delete=models.CASCADE, related_name='%(class)s_category',
        help_text=_('Internal reference'))
    number = models.DecimalField(
        _('Account Number'), max_digits=20, decimal_places=2,
        help_text=_(
            'The account number. Must be numeric but can contain a decimal point.'))
    currency = models.ForeignKey(
        Currency, verbose_name=_('Currency'), default=Currency.get_default_id,
        on_delete=models.PROTECT, related_name='%(class)s_currency',
        help_text=_(
            "Link to currency. Defaults to the system currency if not specified."))
    target_max = models.DecimalField(
        _('Target Maximum Balance'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_(
            'The target maximum balance (aka budget) you hope this account '
            'to stay beneath of by the end of the fiscal period. This will '
            'be displayed in the Targets report, comparing your target to '
            'the actual balance. Please first switch to the desired fiscal '
            'period to set the target for that period.'
        )
    )
    target_min = models.DecimalField(
        _('Target Minimum Balance'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_(
            'The target minimum balance you hope this account to hit by the '
            'end of the fiscal period. This will be displayed in the Targets '
            'report, comparing your target to the actual balance. Please '
            'first switch to the desired fiscal period to set the target for '
            'that period.'
        )
    )
    tax_c_id = models.PositiveIntegerField(
        '_Id to Tax', blank=True, null=True,
        help_text=_("Link to tax. Only used in cashCtrl."))

    # custom
    function = models.CharField(
         _('Function'), max_length=5, null=True, blank=True,
        help_text=_('Function code, e.g. 071'))
    hrm = models.CharField(
         _('HRM 2'), max_length=8, null=True, blank=True,
        help_text=_('HRM 2 number, e.g. 3100.01'))
    budget = models.DecimalField(
        _('Budget'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_('The budget as agreed.')
    )

    def __str__(self):
        if not self.hrm or self.hrm[0] in ['1', '2']:  # balance
            name = ''
        elif self.function:
            name = self.function + ' '
        return f"{name}{self.hrm} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'number', 'c_id'],
                name='unique_setup_account'
            )
        ]
        ordering = ['number']
        verbose_name = ('Account')
        verbose_name_plural = _('Accounts')


class Allocation(AcctApp):
    """
    Cost Center allocation to account
    """
    share =  models.DecimalField(
         _('Share'), max_digits=10, decimal_places=2,
        help_text=_(
            'Allocation share. This can be a percentage or just a share '
            'number.'))
    to_cost_center = models.ForeignKey(
        CostCenter, related_name='allocation_account',
        on_delete=models.CASCADE, verbose_name=_("Account"),
        help_text = _("cost center to allocate to")
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='allocation_account',
        verbose_name=_("Account")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'account', 'to_cost_center', 'c_id'],
                name='unique_allocation'
            )
        ]
        ordering = ['to_cost_center__number']
        verbose_name = ('Cost Center Allocation')
        verbose_name_plural = _('Cost Center Allocations')


# All the following entities have foreign keys to Account
class Setting(AcctApp):
    """
    Represents the system's configuration for financial and accounting settings.
    """
    # Format Settings
    csv_delimiter = models.CharField(
        _("CSV Delimiter"), max_length=5, default=";")
    thousand_separator = models.CharField(
        _("Thousand Separator"), max_length=1, blank=True, null=True)

    # Account Settings
    default_debtor_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='debtor_accounts',
        verbose_name=_("Default Debtor Account"))
    default_opening_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='opening_accounts',
        verbose_name=_("Default Opening Account"))
    default_creditor_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='creditor_accounts',
        verbose_name=_("Default Creditor Account"))
    default_exchange_diff_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exchange_diff_accounts',
        verbose_name=_("Default Exchange Difference Account"))
    default_profit_allocation_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profit_allocation_accounts',
        verbose_name=_("Default Profit Allocation Account"))
    default_inventory_disposal_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventory_disposal_accounts',
        verbose_name=_("Default Inventory Disposal Account"))
    default_input_tax_adjustment_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='input_tax_adjustment_accounts',
        verbose_name=_("Default Input Tax Adjustment Account"))
    default_sales_tax_adjustment_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_tax_adjustment_accounts',
        verbose_name=_("Default Sales Tax Adjustment Account"))
    default_inventory_depreciation_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventory_depreciation_accounts',
        verbose_name=_("Default Inventory Depreciation Account"))
    default_inventory_asset_revenue_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventory_asset_revenue_accounts',
        verbose_name=_("Default Inventory Asset Revenue Account"))
    default_inventory_article_expense_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventory_article_expense_accounts',
        verbose_name=_("Default Inventory Article Expense Account"))
    default_inventory_article_revenue_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventory_article_revenue_accounts',
        verbose_name=_("Default Inventory Article Revenue Account"))
    default_sequence_number_inventory_asset = models.IntegerField(
        _("Default Sequence Number for Inventory Asset"), default=4)
    default_sequence_number_inventory_article = models.IntegerField(
        _("Default Sequence Number for Inventory Article"), default=2)
    default_sequence_number_person = models.IntegerField(
        verbose_name=_("Default Sequence Number for Person"), default=5)
    default_sequence_number_journal = models.IntegerField(
        verbose_name=_("Default Sequence Number for Journal"), default=6)

    # General Settings
    first_steps_logo = models.BooleanField(
        _("Show Logo in First Steps"), default=True)
    first_steps_account = models.BooleanField(
        _("Enable First Steps Account Setup"), default=True)
    first_steps_currency = models.BooleanField(
        _("Enable First Steps Currency Setup"), default=True)
    first_steps_pro_demo = models.BooleanField(
        _("Enable Pro Demo First Steps"), default=True)
    first_steps_tax_rate = models.BooleanField(
        _("Enable First Steps Tax Rate Setup"), default=True)
    first_steps_tax_type = models.BooleanField(
        _("Enable First Steps Tax Type Setup"), default=True)
    order_mail_copy_to_me = models.BooleanField(
        _("Copy Order Mails to Me"), default=True)
    tax_accounting_method = models.CharField(
        _("Tax Accounting Method"), max_length=50, default="AGREED")
    journal_import_force_sequence_number = models.BooleanField(
        _("Force Sequence Number for Journal Import"), default=False)
    first_steps_opening_entries = models.BooleanField(
        _("First steps opening entries done"), default=False)
    journal_import_force_sequence_number = models.BooleanField(
        _("Force Sequence Number for Journal Import"), default=False)
    first_steps_two_factor_auth = models.BooleanField(
        _("First steps two factor auth"), default=False)

    def __str__(self):
        return f"Configuration {self.pk}"

    class Meta:
        verbose_name = _("Settings")
        verbose_name_plural = _("Settings")


class Tax(AcctApp):
    ''' Master
    '''
    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), blank=True, null=True,
        help_text=_("The name of the tax rate."))
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Account'),
        related_name='%(class)s_account',
        help_text=_('The account which collects the taxes.'))
    percentage = models.DecimalField(
        _('Percentage'), max_digits=5, decimal_places=2,
        help_text=_(
            'The tax rate percentage. This cannot be changed anymore '
            'if the tax rate has been used already.'))
    document_name = models.JSONField(
        _('Invoice tax name'), null=True, blank=True,
        help_text=_(
            "Invoice tax name as shown on the invoice. Use format like "
            "'CHE-112.793.129 MWST, Abwasser, 8.1%'"))
    calc_type = models.CharField(
        _('Calculation basis'),
        max_length=10, default='NET',
        help_text=(
            """The calculation basis of the tax rate. NET means the tax rate is
            based on the net revenue and GROSS means the tax rate is based on
            the gross revenue. Note that this only applies to the regular
            tax rate percentage, not the flat tax rate percentage
            (where always GROSS is used).
            Defaults to NET. Possible values: NET, GROSS."""))
    percentage_flat = models.DecimalField(
        _('Percentage flat'), null=True, blank=True,
        max_digits=5, decimal_places=2,
        help_text=_(
            "The flat tax rate percentage (Saldo-/Pauschalsteuersatz)."))

    def clean(self):
        if not self.name:
            raise ValidationError(_("Name must not be empty"))

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'c_id'],
                name='unique_setup_tax'
            )
        ]
        ordering = ['code']
        verbose_name = _("Tax Rate")
        verbose_name_plural = f"{_('Tax Rates')}"


class Rounding(AcctApp):
    ''' Rounding '''
    MODE = [(x.value, x.value) for x in ROUNDING]
    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), default=dict,
        help_text=_("The name of the rounding."))
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_account',
        verbose_name=_('Account'),
        help_text=_('The account which collects the roundings'))
    rounding = models.DecimalField(
        _('rounding'), max_digits=5, decimal_places=2)
    mode = models.CharField(
        _('mode'),
        max_length=20, choices=MODE, default=ROUNDING.HALF_UP.value,
        help_text=_("The rounding mode. Defaults to HALF_UP."))

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'c_id'],
                name='unique_setup_rounding'
            )
        ]
        ordering = ['code']
        verbose_name = _("Rounding")
        verbose_name_plural = f"{_('Roundings')}"


class ArticleCategory(AcctApp):
    ''' ArticleCategory
        allocation not implemented yet
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text=_("internal code"))
    name = models.JSONField(
        _('Name'), help_text="The name of the cost center category.")
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_parent',
        help_text=_('The parent category.'))
    purchase_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_purchase_account',
        verbose_name=_('Account'),
        help_text=_(
            "Purchase account, which will be used when purchasing articles. "
            "Leave empty"))
    sales_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_sales_account',
        verbose_name=_('Account'),
        help_text=_(
            "Sales account, which will be used when selling articles. "
            "Leave empty"))
    sequence_nr = models.ForeignKey(
        SequenceNumber, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_account',
        verbose_name=_('Sequence Number'),
        help_text=_(
            "The ID of the sequence number used for services in this category. "
            "Leave empty."))

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_setup_article_category'
            )
        ]
        ordering = ['code']
        verbose_name = _("Article Category")
        verbose_name_plural = _("Article Categories")


class Article(AcctApp):
    """
    Article Model for inventory and sales management.
    """
    nr = models.CharField(
        _('Article Number'), max_length=50,
        help_text=_("The article number."))
    name = models.JSONField(
        _('Name'),
        help_text=_("The name of the article. For localized text, use XML format: "
                    "<values><de>German text</de><en>English text</en></values>."),
        null=True,
        blank=True,
    )
    bin_location = models.CharField(
        _('Bin Location'),
        max_length=255, blank=True, null=True,
        help_text=_("The place within the building (e.g., A15, B04, C11). "
                    "Ignored unless isStockArticle is true."))
    category = models.ForeignKey(
        ArticleCategory, on_delete=models.CASCADE, null=True, blank=True,
        related_name='%(class)s_category',
        verbose_name=_('Category'))
    currency = models.ForeignKey(
        ArticleCategory, on_delete=models.CASCADE, null=True, blank=True,
        related_name='%(class)s_currency',
        verbose_name=_('Currency'))
    description = models.JSONField(
        _('Description'), null=True, blank=True,
        help_text=_(
            "A description of the article. For localized text, use XML format: "
            "<values><de>German text</de><en>English text</en></values>."))
    is_purchase_price_gross = models.BooleanField(
        _('Is Purchase Price Gross'), default=False,
        help_text=_("Defines the purchase price as gross (including tax). Defaults to false."),
    )
    is_sales_price_gross = models.BooleanField(
        _('Is Sales Price Gross'), default=False,
        help_text=_("Defines the sales price as gross (including tax). Defaults to false."),
    )
    is_stock_article = models.BooleanField(
        _('Is Stock Article'), default=False,
        help_text=_("Whether the article has stock and should be tracked."),
    )
    last_purchase_price = models.DecimalField(
        _('Last Purchase Price'), max_digits=11, decimal_places=2,
        null=True, blank=True,
        help_text=_(
            "The last purchase price of the article. Defaults to net unless  "
            "isPurchasePriceGross is true. Leave empty"),
    )
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_location',
        verbose_name=_('Location'),
        help_text=_("Location where the article can be found"))
    max_stock = models.PositiveIntegerField(
        _('Max Stock'), null=True, blank=True,
        help_text=_("The desired maximum stock of the article. Ignored unless "
                    "isStockArticle is true."),
    )
    min_stock = models.PositiveIntegerField(
        _('Min Stock'), null=True, blank=True,
        help_text=_("The desired minimum stock of the article. Ignored unless "
                    "isStockArticle is true."),)
    sales_price = models.DecimalField(
        _('Sales Price'), max_digits=11, decimal_places=2,
        null=True, blank=True,
        help_text=_("The sales price of the article. Defaults to net unless "
                    "isSalesPriceGross is true."))
    sequence_nr = models.ForeignKey(
        SequenceNumber, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_account',
        verbose_name=_('Sequence Number'),
        help_text=_(
            "The ID of the sequence number used for services in this category. "
            "Leave empty."))
    stock = models.PositiveIntegerField(
        _('Stock'), null=True, blank=True,
        help_text=_("The current stock of the article. Ignored unless "
                    "isStockArticle is true."))
    unit = models.ForeignKey(
        Unit, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_unit',
        verbose_name=_('Unit'))

    def __str__(self):
        return f"{self.nr} {primary_language(self.name)}"

    class Meta:
        ordering = ['nr']
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'nr'],
                name='unique_setup_article'
            )
        ]
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")


# Person ----------------------------------------------------------------
class Core(AcctApp):
    # redefine the related classes
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='%(class)s_core_tenant', 
        help_text='every instance must have a tenant')
    created_by = models.ForeignKey(
        User, verbose_name=_('created by'),
        on_delete=models.CASCADE, related_name='%(class)s_core_created')
    modified_by = models.ForeignKey(
        User, verbose_name=_('modified by'), null=True, blank=True,
        on_delete=models.CASCADE, related_name='%(class)s_core_modified')
        
    class Meta:
        abstract = True


class Title(Core):
    '''
    Title.
    Map core title to accounting system, not shown in any GUI
    '''
    core = models.ForeignKey(
        TitleCrm, on_delete=models.CASCADE, 
        related_name='%(class)s_core', help_text='origin')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'core'],
                name='accounting_unique_title')
        ] 


class PersonCategory(Core):
    '''
    Person's category.
    Map core person category to accounting system, not shown in any GUI
    '''
    core = models.ForeignKey(
        PersonCategoryCrm, on_delete=models.CASCADE,
        related_name='%(class)s_core', help_text='origin')
    parent = None  # we do not use this

    class Meta:
        pass
        """
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'core'],
                name='accounting_unique_person_category')
        ]
        """


class Person(Core):
    '''
    Person.
    Map core person to accounting system, not shown in any GUI
    '''
    core = models.ForeignKey(
        PersonCrm, on_delete=models.CASCADE,
        related_name='%(class)s_core', help_text='origin')
 
    @classmethod
    def get_accounting_object(cls, person_id):
        accounting_object = cls.objects.filter(
            core__id=person_id).first()
        if accounting_object:
            return accounting_object
        raise ValidationError("No accounting_object found for person")
 
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'core'],
                name='accounting_unique_person')
        ]
 

# Orders --------------------------------------------------------------------
class BookTemplate(AcctApp):
    '''
    BookTemplates
    not synchronized to cashCtrl
    we use it for booking and order management
    '''
    class TYPE(models.TextChoices):
        # CashCtrl
        CREDITOR_BOOKING = 'C_BOOK', _('Creditor Booked')
        CREDITOR_PAID = 'C_PAID', _('Creditor Paid')

    code = models.CharField(
        _('Code'), max_length=200,
        help_text=_("internal code"))
    type = models.CharField(
        _('Type'), max_length=10, choices=TYPE.choices,
        help_text=('''Workflow process step'''))
    name = models.JSONField(_('Name'))
    credit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_credit_account',
        verbose_name=_('Credit Account'),
        help_text="Typically the default creditor account in case of a payment")
    debit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_debit_account',
        verbose_name=_('Dedbt Account'),
        help_text="Typically an expense account in case of a payment")
    tax = models.ForeignKey(
        Tax, on_delete=models.CASCADE, blank=True, null=True,
        related_name='%(class)s_tax',
        verbose_name=_('Tax'),
        help_text="Tax rate to be applied.")

    def __str__(self):
        return f"{self.code}, {self.type}, {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code', 'type'],
                name='unique_c_id_per_tenant_setup__order_template'
            )
        ]
        ordering = ['code', 'type']
        verbose_name = _("Booking Template")
        verbose_name_plural = f"{_('Booking Templates')}"


class OrderCategory(AcctApp):
    ''' OrderCategory
    central category for booking:
        status: get derived from STATUS
        book_templates: only defined in OrderCategoryContract
        bookType: defined in classes  DEBIT, CREDIT
        due_days: defined in classes
        footer, header: defined in classes
        mail: empty for now
        responsiblePersonId: empty for now
        type: defined in classes  SALES, PURCHASE
    '''
    class TYPE(models.TextChoices):
        PURCHASE = "PURCHASE", _('Purchase')
        SALES = "SALES", _('Sales')

    code = models.CharField(
        _('Code'), max_length=50,
        help_text='Internal code for scerp')
    type = models.CharField(
        _('Type'), max_length=10,
        choices=TYPE.choices, default=TYPE.PURCHASE)
    name_singular = models.JSONField(
        _('Name, singular'), blank=True, null=True,
        help_text=_(
            "The singular name of the category (e.g. 'Invoices'). "
            "Fill if for at least one language."))
    name_plural = models.JSONField(
        _('Name, plural'), blank=True, null=True,
        help_text=_(
            "The plural name of the category (e.g. 'Invoices'). "
            "Fill if for at least one language."))
    status_data = models.JSONField(
        blank=True, null=True,
        help_text="Internal use for storing status_ids")
    book_template_data = models.JSONField(
        blank=True, null=True,
        help_text="Internal use for storing book_template_ids")

    @property
    def book_type(self):
        return (
            BOOK_TYPE.CREDIT if self.type == self.TYPE.PURCHASE
            else BOOK_TYPE.DEBIT
        )

    @property
    def is_switch_recipient(self):
        return self.type == TYPE.PURCHASE

    def get_sequence_number(self, prefix):
        return SequenceNumber.objects.filter(
            setup=self.setup, pattern__startswith=prefix).first()

    def clean(self):
        # Check for required fields and raise validation error if missing
        missing_fields = []

        if not self.name_singular:
            missing_fields.append("singular name")
        if not self.name_plural:
            missing_fields.append("plural name")

        if missing_fields:
            raise ValidationError(
                _("The following fields are mandatory: %s.") %
                ", ".join(missing_fields)
            )

    def __str__(self):
        return primary_language(self.name_plural)

    class Meta:
        ordering = ['code', 'name_plural']
        abstract = True


class OrderCategoryContract(OrderCategory):
    '''Contract Order Category
        use this to have an overview of all current contracts
        doesn't need to be showsn to users
    '''
    class STATUS(models.TextChoices):
        DRAFT = 'Draft', _("Draft")
        REQUEST = 'Request', _("Request")
        OFFER_RECEIVED = 'Offer Received', _("Offer Received")
        SHORTLISTED = 'Shortlisted', _("Shortlisted")
        AWARDED = 'Awarded', _("Awarded")
        RULING = 'Ruling', _("Ruling")
        APPEAL = 'Appeal', _("Appeal")
        CONTRACT_RECEIVED = 'Contract Received', _("Contract Received")
        CONTRACT_SIGNED = 'Contract Signed', _("Contract Signed")
        CANCELLED = 'Cancelled', _("Cancelled")
        TERMINATED = 'Terminated', _("Terminated")
        TERMINATION_CONFIRMED = 'Termination Confirmed', _("Termination Confirmed")
        ARCHIVED = 'Archived', _("Archived")

    COLOR_MAPPING = {
        STATUS.DRAFT: COLOR.GRAY,
        STATUS.REQUEST: COLOR.ORANGE,
        STATUS.OFFER_RECEIVED: COLOR.BLUE,
        STATUS.SHORTLISTED: COLOR.YELLOW,
        STATUS.AWARDED: COLOR.VIOLET,
        STATUS.RULING: COLOR.ORANGE,
        STATUS.APPEAL: COLOR.RED,
        STATUS.CONTRACT_RECEIVED: COLOR.BLUE,
        STATUS.CONTRACT_SIGNED: COLOR.GREEN,
        STATUS.CANCELLED: COLOR.BLACK,
        STATUS.TERMINATED: COLOR.RED,
        STATUS.TERMINATION_CONFIRMED: COLOR.BROWN,
        STATUS.ARCHIVED: COLOR.GRAY,
    }

    is_display_item_gross = False

    @property
    def account(self):
        ''' needed for cashCtrl so we take the first credit account '''
        credit_account = Account.objects.filter(
            setup=self.setup, hrm__startswith='2').first()
        if not credit_account:
            raise ValidationError(_("No credit account found."))
        return credit_account

    @property
    def sequence_number(self):
        return self.get_sequence_number('BE')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_order_category_contract'
            )
        ]
        verbose_name = _("Category: Contract")
        verbose_name_plural = _("Category Contracts")


class OrderCategoryIncoming(OrderCategory):
    '''Category for incoming invoices,
        use this to define all booking details
    '''
    class STATUS(models.TextChoices):
        OPEN = 'Open', _('Open')
        APPROVED_1 = 'Approved 1', _('Approved 1')
        APPROVED_2 = 'Approved 2', _('Approved 2')
        SUBMITTED = 'Submitted', _('Submitted')
        REMINDER_1 = 'Reminder 1', _('Reminder 1')
        REMINDER_2 = 'Reminder 2', _('Reminder 2')
        PAID = 'Paid', _('Paid')
        ARCHIVED = 'Archived', _('Archived')
        CANCELLED = 'Cancelled', _('Cancelled')

    COLOR_MAPPING = {
        STATUS.OPEN: COLOR.GRAY,
        STATUS.APPROVED_1: COLOR.GREEN,
        STATUS.APPROVED_2: COLOR.GREEN,
        STATUS.SUBMITTED: COLOR.BLUE,
        STATUS.REMINDER_1: COLOR.PINK,
        STATUS.REMINDER_2: COLOR.ORANGE,
        STATUS.PAID: COLOR.GREEN,
        STATUS.ARCHIVED: COLOR.BLACK,
        STATUS.CANCELLED: COLOR.YELLOW,
    }

    BOOKING_MAPPING = {
        STATUS.OPEN: True,
        STATUS.APPROVED_1: True,
        STATUS.APPROVED_2: True,
        STATUS.SUBMITTED: True,
        STATUS.REMINDER_1: True,
        STATUS.REMINDER_2:True,
        STATUS.PAID: True,
        STATUS.ARCHIVED: True,
        STATUS.CANCELLED: True,
    }
    is_display_item_gross = True

    credit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_credit_account',
        verbose_name=_('Credit Account'))
    expense_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_expense_account',
        verbose_name=_('Expense Account'))
    bank_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_banke_account',
        verbose_name=_('Bank Account (payment)'))
    tax = models.ForeignKey(
        Tax, on_delete=models.CASCADE, blank=True, null=True,
        related_name='%(class)s_tax',
        verbose_name=_('Tax'),
        help_text="Tax rate to be applied.")
    rounding = models.ForeignKey(
        Rounding, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_rounding',
        verbose_name=_('Rounding'))
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_currency',
        verbose_name=_('Currency'),
        help_text=_("Leave empty for CHF"))
    due_days = models.PositiveSmallIntegerField(
        _('Default due days'), default=30, null=True, blank=True)
    address_type = models.CharField(
        _('address type'), max_length=20,
        choices=PersonAddress.TYPE.choices,
        default=PersonAddress.TYPE.INVOICE,
        help_text=(
            '''Which address of the recipient to use in the order document.
               Possible values: MAIN, INVOICE, DELIVERY, OTHER.'''))

    @property
    def sequence_number(self):
        return self.get_sequence_number('ER')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_order_category_incoming'
            )
        ]
        verbose_name = _(" Category Invoice & Booking")
        verbose_name_plural = _("Category Invoices & Bookings")


class OrderContract(AcctApp):
    '''
    '''
    CUSTOM = [
        ('valid_from', 'order_procurement_valid_from'),
        ('valid_until', 'order_procurement_valid_until'),
        ('notice_period_month', 'order_procurement_notice')
    ]
    associate = models.ForeignKey(
        PersonCrm, on_delete=models.PROTECT, related_name='associate_2',
        verbose_name=_('Contract party'),
        help_text=_('Supplier or Client'))  # to be mapped to multiple in cashCtrl        
    category = models.ForeignKey(
        OrderCategoryContract, on_delete=models.CASCADE,
        related_name='%(class)s_category',
        verbose_name=_('Category'),
        help_text=_('category'))
    date = models.DateField(_('Date'))
    status = models.CharField(
        _('Status'), max_length=50,
        choices=OrderCategoryContract.STATUS.choices,
        default=OrderCategoryContract.STATUS.AWARDED)
    description = models.CharField(
        _('Description'), max_length=200, blank=True, null=True,
        help_text=_("e.g. Office contract from Jan 2022 to Dec. 2028 "))
    price_excl_vat = models.DecimalField(
        _('Price (Excl. VAT)'), max_digits=11, decimal_places=2)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Currency'), default=Currency.get_default_id)
    responsible_person = models.ForeignKey(
        PersonCrm, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Responsible'), related_name='%(class)s_person',        
        help_text=_('Principal'))
    valid_from = models.DateField(
        _('Valid From'), null=True, blank=True)
    valid_until = models.DateField(
        _('Valid Until'), null=True, blank=True)
    notice_period_month = models.PositiveSmallIntegerField(
        _('Notice Period (Months)'), null=True, blank=True)

    def __str__(self): 
        return f"{self.associate.company}, {self.date}, {self.description}"

    class Meta:
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")


class IncomingOrder(AcctApp):
    ''' IncomingOrder, i.e INVOICE
    Note:
    When incomding order is created first booking is done:
        account_id:
            account given
            (if empty taken from OrderCategory, but we avoid this)
        items:
            accountId: expense account, e.g. Wareneingang
            name: derived from contract
            unitPrice: use price_incl_vat
            quantity: use 1
            tax_id: derive from ...
    '''
    category = models.ForeignKey(
        OrderCategoryIncoming, on_delete=models.CASCADE,
        related_name='%(class)s_category',
        verbose_name=_('Category'),
        help_text=_('all booking details are defined in category'))
    contract = models.ForeignKey(
        OrderContract, on_delete=models.PROTECT,
        related_name='%(class)s_contract',
        verbose_name=_('Contract'),
        help_text=_(
            "Contract with booking instructions. "
            "Upload actual invoice as attachment."))
    date = models.DateField(_('Date'))
    description = models.TextField(
        _('Description'), blank=True, null=True,
        help_text=_("e.g. Services May"))
    price_incl_vat = models.DecimalField(
        _('Price (Incl. VAT)'), max_digits=11, decimal_places=2)
    status = models.CharField(
        _('Status'), max_length=50,
        choices=OrderCategoryIncoming.STATUS.choices)
    due_days = models.PositiveIntegerField(
        _('Due Days'), null=True, blank=True,
        help_text=_('''Leave blank to calculate from contract'''))
    responsible_person = models.ForeignKey(
        PersonCrm, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Clerk'), related_name='%(class)s_person',        
        help_text=_('Clerk'))    

    def __str__(self):
        return (f"{self.contract.associate.company}, {self.date}, "
                f"{self.description}")

    class Meta:
        verbose_name = _("Incoming Invoice")
        verbose_name_plural = _("Incoming Invoices")


class OrderTemplate(AcctApp):
    '''Read - only
    '''
    name = models.CharField(
        _('name'), max_length=200,
        help_text=_("The name to describe and identify the template."))
    is_default = models.BooleanField(
        _('is default'),
        help_text=_(
            "Mark the template as the default template to use. Defaults to "
            "false.  "))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Order Template")
        verbose_name_plural = f"{_('Order Templates')}"


# scerp entities with foreign key to Ledger ---------------------------------
class Ledger(AcctApp):
    '''
    Ledger assigned to a FiscalPeriod
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code')
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the ledger.")
    period = models.ForeignKey(
        FiscalPeriod, verbose_name=_('Fiscal Period'),
        on_delete=models.CASCADE, related_name='%(class)s_period',
        help_text=_("Fiscal period"))

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['period', 'code'],
                name='unique_ledger'
            )
        ]
        ordering = ['-period__start', 'code']
        verbose_name = ('Ledger')
        verbose_name_plural = _('Ledgers')


class AcctLedger(AcctApp):
    ledger = models.ForeignKey(
        Ledger, verbose_name=_('Ledger'),
        on_delete=models.CASCADE, related_name='%(class)s_ledger',
        help_text=_("Ledger assigned to the fiscal period"))

    class Meta:
        ordering = ['function', 'hrm']
        abstract = True


class LedgerAccount(AcctLedger):
    '''
    Used for HRM 2 account management:
    - type: leave empty to calculate later
    - parent: leave empty to calculate later
    - function: leave empty to calculate later
    - account: leave empty to calculate later

    Processing:
    In pre_save:
    - parent is calculated
    - Account.number is calculated
    - AccountCategory.number is calculated
    - categories or account are created
    - hrm, function, name are copied to categories or account

    '''
    class TYPE(models.TextChoices):
        CATEGORY = 'C', _('Category')
        ACCOUNT = 'A', _('Account')

    hrm = models.CharField(
         _('HRM 2'), max_length=8, null=True, blank=True,
        help_text=_('HRM 2 number, e.g. 3100.01'))
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the account.")
    type = models.CharField(
        _('Type'), max_length=1, choices=TYPE, blank=True, null=True,
        help_text=_("Category or account"))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='%(class)s_parent',
        help_text=_('The parent category.'))
    function = models.CharField(
         _('Function'), max_length=5, null=True, blank=True,
        help_text=_(
            'Function code, e.g. 071, in Balance this is the balance '
            'this is the acount group belonging to one category'))
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), null=True, blank=True,
        on_delete=models.PROTECT, related_name='%(class)s_category',
        help_text="The underlying account.")

    @property
    def cash_ctrl_ids(self):
        fields = [
            'account', 'category', 'category_expense', 'category_revenue']
        return [
            getattr(attr, 'c_id') for field in fields
            if ((attr := getattr(self, field, None))
                and getattr(attr, 'c_id', None))
        ]

    class Meta:
        ordering = ['function', '-type', 'hrm']
        abstract = True


class LedgerBalance(LedgerAccount):
    '''
    Used for HRM 2 account management:
    - category: leave empty to calculate later
    '''
    class SIDE(models.IntegerChoices):
        ASSET = 1, _('Asset')
        LIABILITY = 2, _('Liabilities')
        
    side = models.PositiveSmallIntegerField(
        _('Side'), choices=SIDE, blank=True, null=True,
        help_text=_("Assets or liabilities"))  
    category = models.ForeignKey(
        AccountCategory, verbose_name=_('Account Category'),
        on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_category',
        help_text="The underlying category.")
    opening_balance = models.DecimalField(
        _('Opening Balance'), max_digits=11, decimal_places=2,
        null=True, blank=True,
        help_text=_('The balance at the start of the year.')
    )
    closing_balance = models.DecimalField(
        _('Closing Balance'), max_digits=11, decimal_places=2,
        null=True, blank=True,
        help_text=_('The balance at the end of the year.')
    )
    increase = models.DecimalField(
        _('Increase'), max_digits=11, decimal_places=2, null=True, blank=True,
        help_text=_('The increase in value during the year.')
    )
    decrease = models.DecimalField(
        _('Decrease'), max_digits=11, decimal_places=2, null=True, blank=True,
        help_text=_('The decrease in value during the year.')
    )

    def __str__(self):
        return f"{self.hrm} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['ledger', 'hrm'],
                name='unique_balance'
            )
        ]
        verbose_name = ('Balance Account')
        verbose_name_plural = _('Balance')


class FunctionalLedger(LedgerAccount):
    category_expense = models.ForeignKey(
        AccountCategory, on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Account Category Expense'),
        related_name='%(class)s_category_expense',
        help_text="The underlying expense category.")
    category_revenue = models.ForeignKey(
        AccountCategory,  on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Account Category Revenue'),
        related_name='%(class)s_category_revenue',
        help_text="The underlying revenue category.")

    def __str__(self):
        if self.type == self.TYPE.CATEGORY:
            return f"{self.function} {primary_language(self.name)}"
        else:
            return f"{self.function}.{self.hrm} {primary_language(self.name)}"

    class Meta:
        abstract = True


class LedgerPL(FunctionalLedger):    
    expense = models.DecimalField(
        _('Expense'), max_digits=11, decimal_places=2, blank=True, null=True,
        help_text=_('The expense amount.')
    )
    revenue = models.DecimalField(
        _('Revenue'), max_digits=11, decimal_places=2, blank=True, null=True,
        help_text=_('The revenue amount.')
    )
    expense_budget = models.DecimalField(
        _('Expense Budget'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The budgeted expense amount.')
    )
    revenue_budget = models.DecimalField(
        _('Revenue Budget'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The budgeted revenue amount.')
    )
    expense_previous = models.DecimalField(
        _('Previous Expense'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The previous expense amount.')
    )
    revenue_previous = models.DecimalField(
        _('Previous Revenue'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The previous revenue amount.')
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'ledger', 'hrm', 'function'],
                name='unique_ledger_pl'
            )
        ]
        verbose_name = ('Profit/Loss')
        verbose_name_plural = _('Profit/Loss')


class LedgerIC(FunctionalLedger):        
    expense = models.DecimalField(
        _('Expense'), max_digits=11, decimal_places=2, blank=True, null=True,
        help_text=_('The expense amount.')
    )
    revenue = models.DecimalField(
        _('Revenue'), max_digits=11, decimal_places=2, blank=True, null=True,
        help_text=_('The revenue amount.')
    )
    expense_budget = models.DecimalField(
        _('Expense Budget'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The budgeted expense amount.')
    )
    revenue_budget = models.DecimalField(
        _('Revenue Budget'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The budgeted revenue amount.')
    )
    expense_previous = models.DecimalField(
        _('Previous Expense'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The previous expense amount.')
    )
    revenue_previous = models.DecimalField(
        _('Previous Revenue'), max_digits=11, decimal_places=2,
        blank=True, null=True,
        help_text=_('The previous revenue amount.')
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'ledger', 'hrm', 'function'],
                name='unique_ledger_ic'
            )
        ]
        verbose_name = ('Investment Calculation')
        verbose_name_plural = _('Investment Calculations')


# Accounting Charts -----------------------------------------------------------
'''
every balance belongs to one tenant
every income and invest belongs to one or more functions
every function belongs to one tenant
'''
class ChartOfAccountsTemplate(LogAbstract, NotesAbstract):
    '''Model for Chart of Accounts (Canton).
        visible for all, only editable by admin!
    '''
    class ACCOUNT_TYPE_TEMPLATE(models.IntegerChoices):
        # Used for Cantonal / Template Charts
        BALANCE = (1, _('Bilanz'))
        FUNCTIONAL = (2, _('Funktionale Gliederung'))
        INCOME = (3, _('Erfolgsrechnung'))
        INVEST = (5, _('Investitionsrechnung') )

    name = models.CharField(
        _('name'), max_length=250,
        help_text=_('Enter the name of the chart of accounts.'))
    account_type = models.PositiveSmallIntegerField(
        _('Type'), choices=ACCOUNT_TYPE_TEMPLATE.choices,
        help_text=_('Select the type of chart (e.g., Balance, Functional).'))
    canton = models.CharField(
        _('Canton'), max_length=2, choices=CANTON_CHOICES,
        help_text=_('Select the associated canton for this chart of accounts.'))
    type = models.CharField(
        _('Type'), max_length=1, choices=TenantSetup.TYPE.choices,
        null=True, blank=True,
        help_text=_('Choose the type from the available city options.'))
    chart_version = models.CharField(
        _('Chart Version'), max_length=100,
        help_text=_('Specify the version of the chart of accounts.'))
    date = models.DateField(
        _('Date'), help_text=_('Enter the date for this chart of accounts record.'))
    excel = models.FileField(
        _('Excel File'), upload_to='uploads/',
        help_text=_('Upload the Excel file associated with this chart of accounts.'))
    exported_at = models.DateTimeField(
        _('Exported At'), null=True, blank=True,
        help_text=_('Record the date and time this chart use to create positions.'))

    def __str__(self):
        return f'{self.name}, V{self.chart_version}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'canton', 'type', 'chart_version'],
                name='unique_chart_template'
            )
        ]
        ordering = ['account_type', 'name']
        verbose_name = _('Chart of Accounts (Canton)')
        verbose_name_plural = _('Charts of Accounts (Canton)')


class ChartOfAccounts(TenantAbstract):
    '''Model for Chart of Accounts (individual).
    '''
    name = models.CharField(
        _('name'), max_length=250,
        help_text=_('Enter the name of the chart of accounts.'))
    chart_version = models.CharField(
        _('Chart Version'), max_length=100, blank=True, null=True,
        help_text=_('Specify the version of the chart of accounts.'))
    period = models.ForeignKey(
        FiscalPeriod, verbose_name=_('period'),
        on_delete=models.CASCADE, related_name='%(class)s_chart',
        help_text=_('Fiscal period, automatically updated in Fiscal Period'))
    headings_w_numbers = models.BooleanField(
        _('headings with numbers'), default=True,
        help_text=_('Show numbers in headings of the accounting system'))

    def full_name(self):
        return f'{self.name} {self.period.name}, V{self.chart_version}'

    def __str__(self):
        return self.full_name()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'period'],
                name='unique_name_period'
            )
        ]
        ordering = ['name']
        verbose_name = _('Chart of Accounts')
        verbose_name_plural = _('Charts of Accounts')


# Account Position
class AccountPositionAbstract(LogAbstract):
    # Core data (input)
    account_number = models.CharField(
        _('Account Number'), max_length=8,
        help_text=_('Typically 4 digits for functions / categories, '
                    '4 + 2 for account positions, 5 + 2 for balance'))
    is_category = models.BooleanField(
        _('is category'), help_text=_('Flag indicating position is category'))
    name = models.CharField(
        _('name'), max_length=255,
        help_text=_('Name of the account'))
    description = models.TextField(
        _('Description'), null=True, blank=True,
        help_text=_('Position description'))
    parent = models.ForeignKey(
        'self', verbose_name=_("Parent"), null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='%(class)s_parent',
        help_text="The parent category."
    )

    # Calculated data, calculate with every save
    number = models.DecimalField(
        _('Number'), max_digits=14, decimal_places=2,
        help_text=_('Calculated account number for reference'))

    @property
    def level(self):
        return len(self.account_number.split('.')[0])

    def __str__(self):
        return f"{self.account_number} {self.name}"

    class Meta:
        abstract = True


class AccountPositionTemplate(
        AccountPositionAbstract, LogAbstract, NotesAbstract):
    ''' triggers signals.py pre_save
    '''
    chart = models.ForeignKey(
        ChartOfAccountsTemplate, verbose_name=_('Chart of Accounts'),
        on_delete=models.CASCADE, related_name='%(class)s_chart',
        help_text=_('Link to the relevant chart of accounts'))

    def save(self, *args, **kwargs):
        if not kwargs.pop('check_only', False):
            super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['chart', 'account_number', 'is_category'],
                name='unique_account_position_canton'
            ),
            models.UniqueConstraint(
                fields=['chart', 'number'],
                name='unique_account_position_canton_number'
            ),
        ]
        ordering = ['chart', 'account_number',  '-is_category']
        verbose_name = _('Account Position (Canton or Others)')
        verbose_name_plural = _('Account Positions (Canton or Others)')


class AccountPosition(AccountPositionAbstract, AcctApp):
    '''actual account for booking
        triggers signals.py pre_save
        allocations not implemented yet
    '''
    class ACCOUNT_TYPE(models.IntegerChoices):
        # Used to display Accounting Charts with bookings, no functionals
        BALANCE = ChartOfAccountsTemplate.ACCOUNT_TYPE_TEMPLATE.BALANCE
        INCOME = ChartOfAccountsTemplate.ACCOUNT_TYPE_TEMPLATE.INCOME
        INVEST = ChartOfAccountsTemplate.ACCOUNT_TYPE_TEMPLATE.INVEST

    class CATEGORY_HRM(Enum):
        # First digits account_number, name, DISCONTINUE
        ASSET = [1], "ASSET"
        LIABILITY = [2], "LIABILITY"
        EXPENSE = [3, 5], "EXPENSE"
        REVENUE = [4, 6], "REVENUE"
        BALANCE = [9], "BALANCE"

    function = models.CharField(
         _('Function'), max_length=8, null=True, blank=True,
        help_text=_('Function code'))
    account_type = models.PositiveSmallIntegerField(
        _('Account Type'), choices=ACCOUNT_TYPE.choices,
         help_text=_('Account Type: balance, income, invent'))
    chart = models.ForeignKey(
        ChartOfAccounts, verbose_name=_('Chart'),
        on_delete=models.CASCADE, related_name='%(class)s_chart',
        help_text=_('Chart the position belongs to if applicable'))
    responsible = models.ForeignKey(
        Group, verbose_name=_('responsible'), null=True, blank=True,
        on_delete=models.PROTECT, related_name='%(class)s_responsible',
        help_text=_('Responsible for budgeting and review'))
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Currency'),
        help_text=_("Leave empty for CHF"))

    # balance
    balance = models.DecimalField(
        _('Balance'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_('Acutal Balance'))
    balance_init = models.DecimalField(
        _('Balance, imported'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_('Balance, imported'))

    # custom fields
    budget = models.DecimalField(
        _('Budget'), max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_('Budget for period given, fill out manually'))
    previous = models.DecimalField(
        _('Previous Balance'),
        max_digits=20, decimal_places=2, blank=True, null=True,
        help_text=_('Balance of previous period'))
    explanation = models.TextField(
        _('Explanation'), null=True, blank=True,
        help_text=_('Explanation, esp. deviations to previous period'))

    @property
    def category_hrm(self):
        for category in CATEGORY_HRM:
            scope, _label = category.value
            if (self.account_number != ''
                    and int(self.account_number[0]) in scope):
                return category
        return None

    def __str__(self):
        if self.function:
            text = f'{self.function}.'
        else:
            text = ''
        return text + super().__str__()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['chart', 'function', 'account_number', 'account_type'],
                name='unique_account_position'
            ),
            models.UniqueConstraint(fields=['chart', 'number'],
                name='unique_account_position_number'
            )
        ]
        ordering = [
            'chart', 'account_type', 'function', '-is_category',
            'account_number']
        verbose_name = ('Account Position (Municipality)')
        verbose_name_plural = _('Account Positions')


"""
class Employee(CRM):
    '''store categories
    '''
    crm = models.OneToOneField(
        CrmEmployee,
        on_delete=models.CASCADE,
        related_name="employee",
        help_text="internal use for mapping")
"""
