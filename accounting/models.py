# accounting/models.py
from enum import Enum
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.db import models, IntegrityError
from django.db.models import UniqueConstraint
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from asset.models import AssetCategory, Unit
from core.models import (
    LogAbstract, NotesAbstract, Attachment ,
    Tenant, TenantAbstract, TenantSetup, TenantLogo,
    Country, Address, Contact, AddressMunicipal,
    PersonAddress, PersonBankAccount, Person, AcctApp
)
from scerp.locales import CANTON_CHOICES
from scerp.mixins import (
    SafeDict, format_date, get_code_w_name, primary_language
)
from .api_cash_ctrl import (
    URL_ROOT, FIELD_TYPE, DATA_TYPE, ROUNDING, TEXT_TYPE, COLOR, BOOK_TYPE,
    CALCULATION_BASE, ORDER_TYPE, PERSON_TYPE, BANK_ACCOUNT_TYPE,
    FISCAL_PERIOD_TYPE, ACCOUNT_CATEGORY_ID)


# Definitions
class APPLICATION(models.TextChoices):
    CASH_CTRL = 'CC', 'Cash Control'


class TOP_LEVEL_ACCOUNT(models.TextChoices):
    ''' choices do not support float '''
    # CachCtrl + OWN
    ASSET = '1', _('ASSET')
    LIABILITY = '2', _('Liability')

    # Expense
    EXPENSE = '3', _('Expense')
    PL_EXPENSE = '3.1', _('IV - Aufwand')
    IS_EXPENSE = '3.2', _('IV - Ausgaben')

    # Revene
    REVENUE = '4', _('Revenue')
    PL_REVENUE = '4.1', _('Ertrag')
    IS_REVENUE = '4.2', _('Einnahmen')

    # Balance
    BALANCE = '5', _('Balance')

TOP_LEVEL_ACCOUNT_NRS = [x.value for x in TOP_LEVEL_ACCOUNT]


# helpers
def today():
    return timezone.now().date()

def rank(nr):
    diff = 4 - nr
    return ' ' * (diff if diff > 0 else 0)


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
            INVENTORY_ASSET, ORDER, Person, FILE.''')

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code', 'c_id'],
                name='unique_custom_field_group'
            )
        ]
        ordering = ['type', 'code']
        verbose_name = _("Setup - Custom Field Group")
        verbose_name_plural = _("Setup - Custom Field Groups")


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
            INVENTORY_ASSET, ORDER, Person, FILE.''')
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
                fields=['tenant', 'code', 'c_id'],
                name='unique_custom_tenant_field'
            )
        ]

        ordering = ['group__code', 'code']
        verbose_name = _("Setup - Custom Field")
        verbose_name_plural = _("Setup - Custom Field")


class FileCategory(AcctApp):
    ''' FileCategory
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text=_("internal code"))
    name = models.JSONField(
        _('Name'), help_text="The name of the file category.")
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_parent',
        help_text=_('The parent category. Do not use'))

    def __str__(self):
        return get_code_w_name(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_tenant_file_category'
            )
        ]

        ordering = ['code']
        verbose_name = _("Setup - File Category")
        verbose_name_plural = _("Setup - File Categories")


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

    # Accounting, do not use; use entities BankAccount and Tax instead
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
                fields=['tenant', 'name', 'c_id'],
                name='unique_tenant_location'
            )
        ]

        ordering = ['name']
        verbose_name = _("Settings - Location, Logo")
        verbose_name_plural = _("Settings - Locations, Logos")



class File:

    @property
    def url(self):
        return (
            f'https://{self.setup.org_name}.cashctrl.com/'
            f'file/get?id={self.c_id}')



class FiscalPeriod(AcctApp):
    ''' FiscalPeriod '''
    TYPE = [(x.value, x.value) for x in FISCAL_PERIOD_TYPE]

    name = models.CharField(
        _("Name"), max_length=30, blank=True, null=True,
        help_text=_(
            "The name of the fiscal period, required if isCustom is true."))
    is_custom = models.BooleanField(
        _("Is Custom"), default=False, blank=True, null=True,
        help_text="Check if fiscal period is closed.")
    start = models.DateTimeField(
        _("Start"), blank=True, null=True,
        help_text=_(
            "Start date of the fiscal period, required if isCustom is true."))
    end = models.DateTimeField(
        _("End"), blank=True, null=True,
        help_text=_(
            "End date of the fiscal period, required if isCustom is true."))
    salary_start = models.DateTimeField(
        _("Salary Start"), blank=True, null=True,
        help_text=_(
            "Start date of the fiscal period, required if isCustom is true."))
    salary_end = models.DateTimeField(
        _("Salary End"), blank=True, null=True,
        help_text=_(
            "End date of the fiscal period, required if isCustom is true."))
    is_current = models.BooleanField(
        _("Is current"), default=False,
        help_text="Check for current fiscal period.")
    type = models.CharField(
        _('mode'), max_length=20, choices=TYPE, blank=True, null=True,
        help_text=_(
            '''Creation type for creating a calendar year, if isCustom is not
                set. Either LATEST, which will create the next year after the
                latest existing year, or EARLIEST, which will create the year
                before the earliest existing year. Defaults to LATEST.
            '''))

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
                fields=['tenant', 'name', 'c_id'],
                name='unique_tenant_period'
            )
        ]

        ordering = ['-start']
        verbose_name = _("Settings - Fiscal Period")
        verbose_name_plural = _('Settings - Fiscal Periods')


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_tenant_currency'
            )
        ]

        ordering = ['code']
        verbose_name = _("Settings - Currency")
        verbose_name_plural = _("Settings - Currencies")

    def clean(self):
        print("*s", self.__dict__)


class SequenceNumber(AcctApp):
    ''' SequenceNumber '''
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

    def __str__(self):
        return primary_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'pattern', 'c_id'],
                name='unique_tenant_sequence_number'
            )
        ]

        ordering = ['pattern']
        verbose_name = _("Settings - Sequence Number")
        verbose_name_plural = _("Settings - Sequence Numbers")


class Text(AcctApp):
    ''' Text Blocks, not used '''
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
                fields=['tenant', 'type', 'name'],
                name='unique_text_block'
            )
        ]

        ordering = ['type', 'name']
        verbose_name = 'Text Block, not used'
        verbose_name_plural = 'Text Blocks, not used'


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
                fields=['tenant', 'number', 'c_id'],
                name='unique_tenant_cost_center_category'
            )
        ]

        ordering = ['number']
        verbose_name = _("Settings - Cost Center Category")
        verbose_name_plural = _("Settings - Cost Center Categories")


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
                fields=['tenant', 'number', 'c_id'],
                name='unique_tenant_cost_center'
            )
        ]

        ordering = ['number']
        verbose_name = _("Settings - Cost Center")
        verbose_name_plural = _("Settings - Cost Centers")


class AccountCategory(AcctApp):
    '''
    Actual Account Category in cashCtrl
    AccountCategory and Account must be loaded before Tax and Rounding
    '''
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the cost center.")
    number = models.DecimalField(
        _('Number'), max_digits=20, decimal_places=2,
        help_text=_(
            'The account category number. Must be numeric but can contain a decimal '
            'point. In cashCtrl it is string'))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='%(class)s_parent',
        help_text=_('The parent category.'))
    is_scerp = models.BooleanField(
        _("Is scerp"), blank=True, null=True,
        help_text=_("true if account created by scerp"))

    @property
    def is_top_level_account(self):
        return str(self.number) in TOP_LEVEL_ACCOUNT_NRS

    def __str__(self):
        return f"{self.number} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                # Generous, as cashCtrl allows identical numbers.
                fields=['tenant', 'number', 'c_id'],
                name='unique_tenant_account_category'
            )
        ]

        # Lexicographic ordering
        ordering = [Cast('number', models.CharField())]
        verbose_name = ('Ledger - Setup Account Category')
        verbose_name_plural = _('Ledger - Setup Account Categories')


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
        Currency, on_delete=models.PROTECT,  blank=True, null=True,
        related_name='%(class)s_currency', verbose_name=_('Currency'),
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
            function = ''  # do not display
        elif self.function:
            function = self.function + ' '
        return f"{function}{self.hrm} {primary_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'number', 'c_id'],
                name='unique_tenant_account'
            )
        ]

        ordering = ['function', 'hrm', 'number']
        verbose_name = ('Ledger - Setup Account')
        verbose_name_plural = _('Ledger - Setup Accounts')


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
                fields=['tenant', 'account', 'to_cost_center', 'c_id'],
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
    we just save it as json to be flexible
    currently we do not use it actively
    """
    data = models.JSONField(
        _('name'), blank=True, null=True,
        help_text=_("Setting data"))

    def __str__(self):
        return f"Configuration {self.pk}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'c_id'],
                name='unique_setting'
            )
        ]
        verbose_name = _("Settings - Config")
        verbose_name_plural = _("Settings - Configs")


class Tax(AcctApp):
    ''' Master
    '''
    class CALC_TYPE(models.TextChoices):
        # CashCtrl
        NET = CALCULATION_BASE.NET, _('Net')
        GROSS = CALCULATION_BASE.GROSS, _('Gross')

    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), blank=True, null=True,
        help_text=_("The name of the tax rate."))
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
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
        max_length=10, choices=CALC_TYPE, default=CALC_TYPE.NET,
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
        return primary_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code', 'c_id'],
                name='unique_tenant_tax'
            )
        ]

        ordering = ['code']
        verbose_name = _("Settings - Tax Rate")
        verbose_name_plural = _("Settings - Tax Rates")


class BankAccount(AcctApp):
    ''' we use this only for internal banking accounts
    '''
    class TYPE(models.TextChoices):
        # CashCtrl
        DEFAULT = BANK_ACCOUNT_TYPE.DEFAULT, _('Default')

    code = models.CharField(
        _('Code'), max_length=50, null=True, blank=True,
        help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), blank=True, null=True,
        help_text=_("The name of the tax rate."))
    type = models.CharField(
        _('Type'), max_length=10, choices=TYPE.choices, default=TYPE.DEFAULT,
        help_text=('''Workflow process step'''))
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Account'),
        related_name='%(class)s_account',
        help_text=_('The account associated with the banking account. '
                    'Leave empty'))
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_currency',
        verbose_name=_('Currency'),
        help_text=_("Leave empty for CHF"))
    bic = models.CharField(
        _('BIC Code'), max_length=11, blank=True, null=True,
        help_text=_("The BIC (Business Identifier Code) of the person's bank."))
    iban = models.CharField(
        _('IBAN'), max_length=32, blank=True, null=True,
        help_text=('The IBAN (International Bank Account Number) of the person.')
    )
    qr_first_digits = models.PositiveIntegerField(
        _("QR First Digits"), blank=True, null=True,
        help_text=_("The first few digits of the Swiss QR reference. Specific "
                    "to Switzerland."))
    qr_iban = models.CharField(
        _("QR-IBAN"), max_length=32, blank=True, null=True,
        help_text=_("The QR-IBAN, used especially for QR invoices. Specific to "
                    "Switzerland."))
    url = models.URLField(
        _("url"), max_length=200, blank=True, null=True,
        help_text=_("URL for the bank's e-banking portal"))

    def clean(self):
        if not self.name:
            raise ValidationError(_("Name must not be empty"))

    def __str__(self):
        value = primary_language(self.name)
        if self.account:
            return f"{value}, {self.account}"
        return value

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code', 'c_id'],
                name='unique_tenant_bank_account'
            )
        ]

        ordering = ['code']
        verbose_name = _("Settings - Bank Account")
        verbose_name_plural = _("Settings - Bank Accounts")


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
        return primary_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code', 'c_id'],
                name='unique_tenant_rounding'
            )
        ]

        ordering = ['code']
        verbose_name = _("Settings - Rounding")
        verbose_name_plural = _("Settings - Roundings")


class ArticleCategory(AcctApp):
    ''' ArticleCategory
        allocation not implemented yet; maybe strip down
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
            "Mandatory for selling articles."))
    tax = models.ForeignKey(
        # additional field, not included in cashCtrl
        Tax, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_tax',
        verbose_name=_('Tax'), help_text=_("Applying tax rate"))
    sequence_nr = models.ForeignKey(
        SequenceNumber, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_account',
        verbose_name=_('Sequence Number'),
        help_text=_(
            "The ID of the sequence number used for services in this category. "
            "Leave empty."))

    def __str__(self):
        return primary_language(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_tenant_article_category'
            )
        ]
        ordering = ['code']
        verbose_name = _("Debtor - Article Category")
        verbose_name_plural = _("Debtor - Article Categories")


class JournalTemplate(AcctApp):
    code = models.CharField(
        _('Code'), max_length=200,
        help_text=_("internal code"))
    name = models.CharField(
        _("Name"), max_length=250, help_text=_("Name of journal template"))
    credit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_credit_account',
        verbose_name=_('Credit Account'),
        help_text="Typically the default creditor account in case of a payment")
    debit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_debit_account',
        verbose_name=_('Debit Account'),
        help_text="Typically an expense account in case of a payment")
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, null=True, blank=True,
        related_name='%(class)s_currency',
        verbose_name=_('Currency'),
        help_text=_("leave empty for default"))
    is_opening_booking = models.BooleanField(
        _('Is Opening Booking'), default=False,
        help_text=_("Default false"),
    )

    def __str__(self):
        return f"{self.code}: {self.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_journal_template'
            )
        ]
        ordering = ['code']
        verbose_name = _("Journal Template")
        verbose_name_plural = _("Journal Templates")


class Journal(AcctApp):
    title = models.CharField(
        _("Title"), max_length=250, blank=True, null=True,
        help_text=_("Title, leave empty if same as template name"))
    template = models.ForeignKey(
        JournalTemplate, on_delete=models.PROTECT,
        related_name='%(class)s_template',
        verbose_name=_('Journal Template'),
        help_text="Journal Template")
    amount = models.DecimalField(
        _('Amount'), max_digits=11, decimal_places=2,
        help_text=_("The amount of the book entry."))
    date = models.DateField(_('Date'), default=today)
    reference = models.CharField(
        _("Reference"), max_length=100, blank=True, null=True,
        help_text=_("An optional reference / receipt for the book entry."))

    def __str__(self):
        return f"{self.template.code}: {self.date} {self.title}"

    class Meta:
        ordering = ['-date', 'title']
        verbose_name = _("Journal")
        verbose_name_plural = _("Journals")


class Article(AcctApp):
    """
    Article Model for inventory and sales management.
    """
    nr = models.CharField(
        _('Article Number'), max_length=50, blank=True, null=True,
        help_text=_(
        "The article number. Leave empty per default. "
         "BUG: currently nr is mandatory and must be unique"))
    name = models.JSONField(
        _('Name'),
        help_text=_("The name of the article."),
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
        ArticleCategory, on_delete=models.PROTECT, null=True, blank=True,
        related_name='%(class)s_currency',
        verbose_name=_('Currency'))
    description = models.JSONField(
        _('Description'), null=True, blank=True,
        help_text=_(
            "A description of the article on the invoice. Default: empty "))
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
        return (
            f"{self.nr} {primary_language(self.name)}: "
            f"{self.currency or 'CHF'} {self.sales_price}")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'nr'],
                name='unique_tenant_article'
            )
        ]
        ordering = ['nr']
        verbose_name = _("Debtor - Article")
        verbose_name_plural = _("Debtor - Articles")


# Orders --------------------------------------------------------------------
class BookTemplate(AcctApp):
    '''
    BookTemplates, not used so fare
    not synchronized to cashCtrl
    we use it for booking and order management
    do not show to users !?
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
        verbose_name=_('Debit Account'),
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
                fields=['tenant', 'code', 'type'],
                name='unique_c_id_per_tenant_tenant__order_template'
            )
        ]

        ordering = ['code', 'type']
        verbose_name = _("Booking Template")
        verbose_name_plural = '_' + _('Booking Template')


class OrderLayout(AcctApp):
    PAGE_SIZES = [
        ("A0", "A0"), ("A1", "A1"), ("A2", "A2"), ("A3", "A3"), ("A4", "A4"),
        ("A5", "A5"), ("A6", "A6"), ("A7", "A7"), ("A8", "A8"), ("A9", "A9"),
        ("LEGAL", "LEGAL"), ("LETTER", "LETTER"), ("A4R", "A4R")
    ]

    # Required field
    name = models.CharField(
        _("Name"), max_length=100,
        help_text="A name to describe and identify the template.")

    # Optional fields
    elements =  models.JSONField(
        _('Elements'), blank=True, null=True,
        help_text=_(
            "List of elements containing HTML/CSS snippets for the different "
            "parts of the layout."))
    footer = models.TextField(
        _("Footer"), blank=True, null=True,
        help_text="Footer text with limited HTML.")

    # Boolean fields with default values
    is_default = models.BooleanField(
        _("Default Template"), blank=True, null=True)
    is_display_document_name = models.BooleanField(
        _("Display Document Name"), blank=True, null=True)
    is_display_item_article_nr = models.BooleanField(
        _("Display Item Article No."), blank=True, null=True)
    is_display_item_price_rounded = models.BooleanField(
        _("Display Rounded Item Prices"), blank=True, null=True)
    is_display_item_tax = models.BooleanField(
        _("Display Item Tax"), blank=True, null=True)
    is_display_item_unit = models.BooleanField(
        _("Display Item Unit"), blank=True, null=True)
    is_display_logo = models.BooleanField(
        _("Display Logo"), blank=True, null=True)
    is_display_org_address_in_window = models.BooleanField(
        _("Display Org Address in Window"), blank=True, null=True)
    is_display_page_nr = models.BooleanField(
        _("Display Page Numbers"), blank=True, null=True)
    is_display_payments = models.BooleanField(
        _("Display Payments"), blank=True, null=True)
    is_display_pos_nr = models.BooleanField(
        _("Display Item Numbering"), blank=True, null=True)
    is_display_recipient_nr = models.BooleanField(
        _("Display Recipient Number"), blank=True, null=True)
    is_display_responsible_person = models.BooleanField(
        _("Display Responsible Person"), blank=True, null=True)
    is_display_zero_tax = models.BooleanField(
        _("Display Zero Tax (0.00)"), blank=True, null=True)
    is_overwrite_css = models.BooleanField(
        _("Overwrite Default CSS"), blank=True, null=True)
    is_overwrite_html = models.BooleanField(
        _("Overwrite Default HTML"), blank=True, null=True)
    is_qr_empty_amount = models.BooleanField(
        _("Leave Amount Empty in QR Code"), blank=True, null=True)
    is_qr_no_lines = models.BooleanField(
        _("QR Invoice Without Lines"), blank=True, null=True)
    is_qr_no_reference_nr = models.BooleanField(
        _("QR Invoice Without Reference Number"), blank=True, null=True)

    # Numeric fields
    letter_paper_file_id = models.PositiveIntegerField(
        _("Letter Paper File ID"), blank=True, null=True,
        help_text=_("ID of the letter paper file (PDF). Max size: 500KB."))
    logo_height = models.DecimalField(
        _("Logo Height"), max_digits=3, decimal_places=1, blank=True, null=True,
        help_text=_("Height of the logo in cm. Min: 0.1, Max: 9.0."))
    page_size = models.CharField(
        _("Page Size"), max_length=10, choices=PAGE_SIZES, default="A4", blank=True,
        help_text=_("Page size of the document. Defaults to A4."))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='%(class)s_parent',
        help_text=_("The parent category. We don't use it"))

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name', 'c_id'],
                name='unique_order_layout'
            )
        ]

        ordering = ['name']
        verbose_name = _("Order Settings - Layout")
        verbose_name_plural = _("Order Settings - Layout")


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
        PURCHASE = "PURCHASE", _('Creditor')
        SALES = "SALES", _('Debtor')

    code = models.CharField(
        _('Code'), max_length=50,
        help_text='Internal code for scerp')
    name_singular = models.JSONField(
        _('Name, invoice'), blank=True, null=True,
        help_text=_(
            "The name as shown on the invoice. e.g. 'Rechnung'). "
            "Fill if for at least one language. "))
    name_plural = models.JSONField(
        _('Name, internal'), blank=True, null=True,
        help_text=_(
            "The name internally used (e.g. 'Rechnungen Wasser'). "))
    status_data = models.JSONField(
        blank=True, null=True,
        help_text="Internal use for storing status_ids")
    book_template_data = models.JSONField(
        blank=True, null=True,
        help_text="Internal use for storing book_template_ids")

    # Layout
    layout = models.ForeignKey(
        OrderLayout, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_order_template',
        verbose_name=_('Order Layout'),
        help_text=_(
            "Layout of invoice (use Swiss QR for outgoing invoices)"))
    is_display_prices = models.BooleanField(
        _('Display prices'), default=True,
        help_text=_(
            'Whether prices and totals are displayed on the document. '
            'Set to True unless no price is shown on first page! '))
    footer = models.TextField(
        _("Footer Text"), blank=True, null=True,
        help_text=_(
            "The text displayed below the items list on the document used by "
            "default for order objects"))

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
            tenant=self.tenant, pattern__startswith=prefix).first()

    def clean(self):
        # Check for required fields and raise validation error if missing
        missing_fields = []

        if not self.name_singular:
            verbose_name = self._meta.get_field('name_singular').verbose_name
            missing_fields.append(verbose_name)
        if not self.name_plural:
            verbose_name = self._meta.get_field('name_plural').verbose_name
            missing_fields.append(verbose_name)

        if missing_fields:
            raise ValidationError(
                _("The following fields are mandatory: %s.") %
                ", ".join(missing_fields)
            )

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
        ONGOING = 'On Going', _("On Going")
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
        STATUS.ONGOING: COLOR.GREEN,
        STATUS.CONTRACT_RECEIVED: COLOR.BLUE,
        STATUS.CONTRACT_SIGNED: COLOR.GREEN,
        STATUS.CANCELLED: COLOR.BLACK,
        STATUS.TERMINATED: COLOR.RED,
        STATUS.TERMINATION_CONFIRMED: COLOR.BROWN,
        STATUS.ARCHIVED: COLOR.GRAY,
    }

    type = models.CharField(
        _('type'), max_length=10,
        choices=OrderCategory.TYPE.choices,
        default=OrderCategory.TYPE.PURCHASE,
        help_text=('Underlying contract aligend to purchases or sales'))
    org_location = models.ForeignKey(
        Location, verbose_name=_('Organisation'),
        on_delete=models.PROTECT, related_name='%(class)s_location',
        help_text=_(
            'Responsible Internal Organisation, will be shown in invoicing '
            'documents (paying and receivable, address and title'))
    is_display_item_gross = False
    header = models.TextField(
        _("Header Text"), blank=True, null=True,
        help_text=_(
            "The text displayed above  the items list on the document used by "
            "default for order objects"))
    block_update = models.BooleanField(
        # used to change categories with existing entities in cashCtrl
        _("Block update"), default=False, 
        help_text=("Do not update to cashCtrl this time. (Admin only)"))
            
    @property
    def account(self):
        ''' needed for cashCtrl so we take the first credit account '''
        credit_account = Account.objects.filter(
            tenant=self.tenant, hrm__startswith='2').first()
        if credit_account:
            return credit_account

        # try again, shouldn't happen
        queryset = Account.objects.filter(tenant=self.tenant)
        for credit_account in queryset.all():
            if int(str(credit_account.number)[0]) == 2:
                return credit_account

        raise ValidationError(_("No credit account found."))

    @property
    def sequence_number(self):
        return self.get_sequence_number('BE')

    def clean(self):
        if (not self.org_location.address
                or not self.org_location.zip
                or not self.org_location.city):
            raise ValidationError(
                _("Address missing for location"))
        super().clean()

    def __str__(self):
        return (
            f"{self.get_type_display()}: - "
            f"{primary_language(self.name_plural)}")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_order_category_contract'
            )
        ]
        ordering = ['type', 'code']
        verbose_name = _("Contract - Category")
        verbose_name_plural = _("Contract - Categories")  # rank(2) +


class OrderCategoryIncoming(OrderCategory):
    '''Category for incoming invoices,
        use this to define all booking details
    '''
    class STATUS(models.TextChoices):
        OPEN = 'Open', _('Open')
        APPROVED_1 = 'Approved 1', _('Approved 1')
        APPROVED_2 = 'Approved 2', _('Approved 2')
        BOOKED = 'Booked', _('Booked')
        TRANSFERRED = 'Transferred', _('Transferred (pain.001)')
        REMINDER_1 = 'Reminder 1', _('Reminder 1')
        REMINDER_2 = 'Reminder 2', _('Reminder 2')
        PAID = 'Paid', _('Paid')
        ARCHIVED = 'Archived', _('Archived')
        CANCELLED = 'Cancelled', _('Cancelled')

    COLOR_MAPPING = {
        STATUS.OPEN: COLOR.GRAY,
        STATUS.APPROVED_1: COLOR.GREEN,
        STATUS.APPROVED_2: COLOR.GREEN,
        STATUS.BOOKED: COLOR.BLUE,
        STATUS.TRANSFERRED: COLOR.VIOLET,
        STATUS.REMINDER_1: COLOR.PINK,
        STATUS.REMINDER_2: COLOR.ORANGE,
        STATUS.PAID: COLOR.GREEN,
        STATUS.ARCHIVED: COLOR.BLACK,
        STATUS.CANCELLED: COLOR.YELLOW,
    }

    BOOKING_MAPPING = {
        STATUS.OPEN: False,
        STATUS.APPROVED_1: False,
        STATUS.APPROVED_2: False,
        STATUS.BOOKED: True,
        STATUS.TRANSFERRED: False,
        STATUS.REMINDER_1: False,
        STATUS.REMINDER_2:False,
        STATUS.PAID: True,
        STATUS.ARCHIVED: False,
        STATUS.CANCELLED: True,
    }

    BOOKING_STEP = {
        STATUS.BOOKED: _('Booking'),
        STATUS.PAID: _('Payment')
    }

    HEADER = (
        '{name}<br>\n'
        'Account Paying: {iban_paying}<br>\n'
        'Account Receiving: {iban_receiving}'
    )

    header = models.TextField(
        _("Header Text"), default=HEADER,
        help_text=_(
            "The text displayed above  the items list on the document used by "
            "default for order objects"))
    is_display_item_gross = True
    type = OrderCategory.TYPE.PURCHASE
    credit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_credit_account',
        verbose_name=_('Credit Account'))
    expense_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_expense_account',
        verbose_name=_('Expense Account'))
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE,
        related_name='%(class)s_banke_account',
        verbose_name=_('Bank Account for paying'))
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
    message = models.CharField(
        _('Message'), max_length=50, blank=True, null=True,
        help_text=(
            '''A message for the payment recipient (included in the pain.001
               xml file).'''))

    @property
    def sequence_number(self):
        return self.get_sequence_number('ER')

    def __str__(self):
        return _('Incoming Invoice') + ': ' + primary_language(self.name_plural)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_order_category_incoming'
            )
        ]

        verbose_name = _("Creditor - Category")
        verbose_name_plural = _("Creditor - Categories")


class OrderCategoryOutgoing(OrderCategory):
    '''Category for outgoing invoices,
        use this to define all booking details
        replace by article category
    '''
    class STATUS(models.TextChoices):
        DRAFT = 'Draft', _('Draft')
        BOOKED = 'Booked', _('Booked')
        SENT = 'Sent', _('Sent')  # Versendet
        REMINDER_1 = 'Reminder 1', _('Reminder 1')  # Mahnstufe 1
        REMINDER_2 = 'Reminder 2', _('Reminder 2')  # Mahnstufe 2, verbucht
        REMINDER_3 = 'Reminder 3', _('Reminder 3')  # Mahnstufe 3, verbucht
        PAID = 'Paid', _('Paid')  # Bezahlt, Buchung
        ARCHIVED = 'Archived', _('Archived')  # Archiviert
        CANCELLED = 'Cancelled', _('Cancelled')  # Storniert, verbucht

    COLOR_MAPPING = {
        STATUS.DRAFT: COLOR.GRAY,
        STATUS.BOOKED: COLOR.BLUE,
        STATUS.SENT: COLOR.YELLOW,
        STATUS.REMINDER_1: COLOR.ORANGE,
        STATUS.REMINDER_2: COLOR.RED,
        STATUS.REMINDER_3: COLOR.RED,
        STATUS.PAID: COLOR.GREEN,
        STATUS.ARCHIVED: COLOR.BLACK,
        STATUS.CANCELLED: COLOR.PINK,
    }

    BOOKING_MAPPING = {
        STATUS.DRAFT: False,
        STATUS.BOOKED: True,
        STATUS.SENT: False,
        STATUS.REMINDER_1: False,
        STATUS.REMINDER_2: True,
        STATUS.REMINDER_3: True,
        STATUS.PAID: True,
        STATUS.ARCHIVED: False,
        STATUS.CANCELLED: True,
    }

    BOOKING_STEP = {
        STATUS.BOOKED: _('Booking'),
        STATUS.PAID: _('Payment')
    }

    is_display_item_gross = True
    type = OrderCategory.TYPE.SALES
    header = models.TextField(
        _("Header Text"), blank=True, null=True,
        help_text=_(
            "The text displayed above  the items list on the document used by "
            "default for order objects"))
    header_installment = models.TextField(
        _("Text Installment"), 
        default=_("Ratenzahlung {nr}/{total} von {invoice_nr}"),
        help_text=_(
            "The text displayed above  the items list on the document used by "
            "default for order objects"))            
    debit_account = models.ForeignKey(
        Account, on_delete=models.CASCADE,
        related_name='%(class)s_debit_account',
        verbose_name=_('Debit Account'))
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE,
        related_name='%(class)s_banke_account',
        verbose_name=_('Bank Account (receiving)'))
    rounding = models.ForeignKey(
        Rounding, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_rounding',
        verbose_name=_('Rounding'))
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_currency',
        verbose_name=_('Currency'),
        help_text=_("Leave empty for CHF"))
    installment_article = models.ForeignKey(
        Article, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_article',
        verbose_name=_('Installment Fee'),
        help_text=_("article for installment fees, leave empty if none"))
    due_days = models.PositiveSmallIntegerField(
        _('Default due days'), default=30, null=True, blank=True)
    address_type = models.CharField(
        _('address type'), max_length=20,
        choices=PersonAddress.TYPE.choices,
        default=PersonAddress.TYPE.INVOICE,
        help_text=(
            '''Which address of the recipient to use in the order document.
               Possible values: MAIN, INVOICE, DELIVERY, OTHER.'''))
    responsible_person = models.ForeignKey(
        Person, on_delete=models.PROTECT,
        verbose_name=_('Responsible'), related_name='%(class)s_person',
        help_text=_('Contact person mentioned in invoice.'))
            
    @property
    def sequence_number(self):
        return self.get_sequence_number('RE')

    # overwriting of order categories seems to work
    '''
    def clean(self):
        # Check if not changeable
        if self.pk and IncomingOrder.objects.filter(category=self).exists():
            raise ValidationError(
                _("Categories with existing contracts cannot be changed"))
        super().clean()
    '''

    def __str__(self):
        return f"{_('Debtors')} - {primary_language(self.name_plural)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='unique_order_category_outgoing'
            )
        ]
        verbose_name = _("Debtor - Invoice Category")
        verbose_name_plural = _("Debtor - Invoice Categories")  # rank(2) + _("Creditors - Categories")


class Order(AcctApp):
    ''' Base class for orders
    '''
    category = models.ForeignKey(
        OrderCategoryContract, on_delete=models.CASCADE,
        related_name='%(class)s_category',
        verbose_name=_('Category'),
        help_text=_(
            'Order category, here are all booking processes and status '
            'defined '))
    date = models.DateField(_('Date'))
    nr = models.CharField(
        _('Order Number'), max_length=50, blank=True, null=True,
        help_text=_("The order number."))

    @property
    def url(self):
        if self.c_id:
            return f'{self.tenant.cash_ctrl_url}#order/document?id={self.c_id}'
        return None

    class Meta:
        abstract = True


class OrderContract(Order):
    '''
    '''
    CUSTOM = [
        ('valid_from', 'order_procurement_valid_from'),
        ('valid_until', 'order_procurement_valid_until'),
        ('notice_period_month', 'order_procurement_notice')
    ]
    contract_date = models.DateField(_('Contract Date'))
    associate = models.ForeignKey(
        # to be mapped to manytomany field in cashCtrl
        Person, on_delete=models.PROTECT,
        related_name='%(class)s_associate',
        verbose_name=_('Contract party'),
        help_text=_('Supplier or Client, usually a company'))
    status = models.CharField(
        _('Status'), max_length=50,
        choices=OrderCategoryContract.STATUS.choices,
        default=OrderCategoryContract.STATUS.AWARDED)
    description = models.CharField(
        _('Description'), max_length=200, blank=True, null=True,
        help_text=_("e.g. Office contract from Jan 2022 to Dec. 2028 "))
    price_excl_vat = models.DecimalField(
        _('Price (Excl. VAT)'), max_digits=11, decimal_places=2,
        null=True, blank=True)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Currency'))
    responsible_person = models.ForeignKey(
        Person, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Responsible'), related_name='%(class)s_person',
        help_text=_('Signer of the contract'))
    valid_from = models.DateField(
        _('Valid From'), null=True, blank=True)
    valid_until = models.DateField(
        _('Valid Until'), null=True, blank=True)
    notice_period_month = models.PositiveSmallIntegerField(
        _('Notice Period (Months)'), null=True, blank=True)
    attachments = GenericRelation('core.Attachment')

    def __str__(self):
        return (
            f"{self.category.get_type_display()}: {self.associate.company}, "
            f"{self.date}, {self.description}")

    class Meta:
        ordering = ['category', 'associate__company', '-date']
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")


class IncomingOrder(Order):
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
    name = models.CharField(
        _('Name'), max_length=100, help_text=_("e.g. Services May"))
    description = models.TextField(
        _('Description'), blank=True, null=True,
        help_text=_("e.g. late delivery"))
    price_incl_vat = models.DecimalField(
        _('Price'), max_digits=11, decimal_places=2, null=True, blank=True,
        help_text=_('incl. VAT'))
    status = models.CharField(
        _('Status'), max_length=50,
        choices=OrderCategoryIncoming.STATUS.choices)
    due_days = models.PositiveSmallIntegerField(
        _('Due Days'), null=True, blank=True,
        help_text=_('''Leave blank to calculate from contract'''))
    responsible_person = models.ForeignKey(
        Person, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Clerk'), related_name='%(class)s_person',
        help_text=_('Clerk'))
    attachment = models.FileField(
        _('Invoice File'), blank=True, null=True,
        upload_to=Attachment.get_attachment_upload_path,
        help_text=_('Invoice in PDF incl. QR Code'))
    reference = models.CharField(
        _('QR Reference'), max_length=50, blank=True, null=True,
        help_text=_('Reference in invoice'))
    recipient_address = models.TextField(
        _('Recipient address'), max_length=255, blank=True, null=True,
        help_text=_(
            "The recipient address in the banking instruction formatted "
            "with line breaks."))

    @property
    def supplier_bank_account(self):
        return PersonBankAccount.objects.filter(
            person=self.contract.associate,
            type=PersonBankAccount.TYPE.DEFAULT
        ).first()

    def __str__(self):
        return (f"{self.contract.associate.company}, {self.date}, "
                f"{self.description}")

    def clean(self):
        if not PersonBankAccount.objects.filter(
                person=self.contract.associate).exclude(iban=None).exists():
            # Check bank_accounts
            raise ValidationError(_("No Iban specified for contract partner"))

        if self.attachment:
            # Check file extension
            if not self.attachment.name.lower().endswith('.pdf'):
                raise ValidationError(
                    {'attachment': _("Only PDF files are allowed.")})

            # Check MIME type if available (works if uploaded via form)
            content_type = getattr(self.attachment.file, 'content_type', None)
            if content_type and content_type != 'application/pdf':
                raise ValidationError({'attachment': _(
                    "Uploaded file is not recognized as a valid PDF.")})

    class Meta:
        verbose_name = _("Creditor - Invoice")
        verbose_name_plural = _("Creditor - Invoices")


class IncomingItem(AcctApp):
    name = models.CharField(
        _('Name'), max_length=200,
        help_text=_("Name of positions"))
    description = models.CharField(
        _('Description'), max_length=200, blank=True, null=True,
        help_text=_("Custom description for position, leave empty for default"))
    account = models.ForeignKey(
        Account, verbose_name=_('Account'),
        on_delete=models.PROTECT, related_name='%(class)s_account',
        help_text="Expense account")
    tax = models.ForeignKey(
        # additional field, not included in cashCtrl
        Tax, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='%(class)s_tax',
        verbose_name=_('Tax'), help_text=_("Applying tax rate"))
    amount = models.DecimalField(
        _('Amount'), max_digits=11, decimal_places=2,
        help_text=_("The amount of the position (incl. VAT)."))
    quantity = models.DecimalField(
        _('Quantity'), max_digits=11, decimal_places=2, blank=True, null=True,
        help_text=_("leave empty for default"))
    order = models.ForeignKey(
        IncomingOrder, on_delete=models.CASCADE,
        related_name='%(class)s_order',
        verbose_name=_('Order'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Position")
        verbose_name_plural = _("Split amount into positions (default empty)")


class OutgoingOrder(Order):
    ''' Outgoing, i.e INVOICE
    Note:
    When outcomding order is created first booking is done:
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
        OrderCategoryOutgoing, on_delete=models.CASCADE,
        related_name='%(class)s_category',
        verbose_name=_('Category'),
        help_text=_('contact details and contractual base (if any)'))
    contract = models.ForeignKey(
        OrderContract, on_delete=models.PROTECT,
        related_name='%(class)s_contract',
        verbose_name=_('Contract'),
        help_text=_(
            "Contract with booking instructions. "
            "Upload actual invoice as attachment."))
    associate = models.ForeignKey(
        # to be mapped to manytomany field in cashCtrl
        Person, on_delete=models.PROTECT,
        related_name='%(class)s_associate',
        verbose_name=_('Client'),
        help_text=_('Client'))
    description = models.TextField(
        _('Description'), blank=True, null=True,
        help_text=_("internal note, e.g. Services May"))
    dossier = models.ForeignKey(
        'self', on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_dossier',
        verbose_name=_('Dossier'),
        help_text=_("Link to another related invoice. Default: leave empty "))
    recipient_address = models.TextField(
        _('Recipient Address'), blank=True, null=True,
        help_text=_(
            "Enter specific address text, otherwise person addresss is "
            "selected"))
    status = models.CharField(
        _('Status'), max_length=50,
        choices=OrderCategoryOutgoing.STATUS.choices)
    due_days = models.PositiveSmallIntegerField(
        _('Due Days'), null=True, blank=True,
        help_text=_('''Leave blank to calculate from contract'''))
    responsible_person = models.ForeignKey(
        Person, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name=_('Clerk'), related_name='%(class)s_person',
        help_text=_('Clerk, leave empty if defined in category'))
    discount_percentage = models.DecimalField(
        _('Discount'), max_digits=5, decimal_places=2, null=True, blank=True,
        help_text=_('The discount percentage for the entire order.'))
    attachments = GenericRelation('core.Attachment')

    # custom
    reference = models.CharField(
        _('QR Reference'), max_length=50, blank=True, null=True,
        help_text=_('Reference in invoice'))
    header = models.TextField(
        _("Header Text"), blank=True, null=True,
        help_text=_(
            "The text displayed above the items list on the document. "
            "Leave empty if default."))
    footer = models.TextField(
        _("Footer Text"), blank=True, null=True,
        help_text=_(
            "The text displayed below the items list on the document. "
            "Leave empty if default."))

    # City specific
    header_description = models.TextField(
        _('Header description'), blank=True, null=True,
        help_text=_("Specific header description, e.g. Hydrantengebrauch"))
    address = models.ForeignKey(
        AddressMunicipal, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_address', verbose_name=_('Building Address'),
        help_text=_("Relate invoice to building address or leave empty."))
    recipient = models.ForeignKey(
        # to be mapped to manytomany field in cashCtrl
        Person, on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_recipient',
        verbose_name=_('Recipient'),
        help_text=_('Leave empty or fill in to specify recipient.'))
    start = models.DateField(
        _('Start Date'), blank=True, null=True,
        help_text=_("Start date of invoiced service."))
    end = models.DateField(
        _('Exit Date'), blank=True, null=True,
        help_text=_("End date of invoiced service."))

    def __str__(self):
        return (f"{self.nr} {self.contract.associate.company}, {self.date}, "
                f"{self.description}")

    def save(self, *args, **kwargs):
        if not self.header:
            # no header given, fill in city specific header

            # building / "Objekt"
            building = (
                f"{self.address.stn_label} {self.address.adr_number}"
            ) if self.address else ''
            building_notes = (
                ', ' + self.address.notes
            ) if self.address and self.address.notes else ''

            # recipient_short_name
            recipient_short_name = (
                f", {self.recipient.short_name}" if self.recipient else '')

            # build
            template = self.category.header or ''
            self.header = template.format_map(SafeDict(
                building=building,
                building_notes=building_notes,
                description=self.header_description or '',
                recipient_short_name=recipient_short_name,
                start=format_date(self.start) if self.start else '',
                end=format_date(self.end) if self.end else ''
            ))

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-id']
        verbose_name = _("Debtor - Invoice")
        verbose_name_plural = _("Debtor - Invoices")


class OutgoingItem(AcctApp):
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name='%(class)s_article',
        verbose_name=_('Article'))
    quantity = models.DecimalField(
        _('Quantity'), max_digits=11, decimal_places=2)
    description = models.CharField(
        _('Description'), max_length=200, blank=True, null=True,
        help_text=_("Custom description for article, leave empty for default"))
    discount_percentage = models.DecimalField(
        _('Discount'), max_digits=5, decimal_places=2, null=True, blank=True,
        help_text=_('The discount percentage for position.'))        
    order = models.ForeignKey(
        OutgoingOrder, on_delete=models.CASCADE,
        related_name='%(class)s_order',
        verbose_name=_('Order'))

    def __str__(self):
        return f"{self.quantity} * {primary_language(self.article.name)}"

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")


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
        verbose_name_plural = _('Ledger')


class LedgerAccount(AcctApp):
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
    ledger = models.ForeignKey(
        Ledger, verbose_name=_('Ledger'),
        on_delete=models.CASCADE, related_name='%(class)s_ledger',
        help_text=_("Ledger assigned to the fiscal period"))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='%(class)s_parent',
        help_text=_(
            "The parent category. Specify if it cannot be derived from the "
            "HRM 2 code. Empty if top category (asset or functional)."))
    function = models.CharField(
         _('Function'), max_length=5, null=True, blank=True,
        help_text=_(
            'Function code, e.g. 071, leave empty for Balance positions, as '
            'it gets filled automatically.' ))
    account = models.ForeignKey(
        Account, verbose_name=_('Account'), null=True, blank=True,
        on_delete=models.PROTECT, related_name='%(class)s_account',
        help_text="The underlying account. Empty for categories.")
    manual_creation = models.BooleanField(
        default=True, help_text=(
            "For import / export this is set to False so ledger.py uses "
            "last inserted category as parent instead of parent"))
    balance_updated = models.DateTimeField(
        _('Balance last update'), null=True, blank=True,
        help_text=_('Date and time of last update of balance'))

    @property
    def cash_ctrl_ids(self):
        fields = [
            'account', 'category', 'category_expense', 'category_revenue']
        return [
            getattr(attr, 'c_id') for field in fields
            if ((attr := getattr(self, field, None))
                and getattr(attr, 'c_id', None))
        ]

    def clean(self):
        if False and not self.parent and self.manual_creation:
            # disabled
            raise ValidationError(_("No parent specified"))

    class Meta:
        ordering = ['function', 'hrm']
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

        verbose_name = ('Ledger - Balance')
        verbose_name_plural = _('Ledger - Balances')


class FunctionalLedger(LedgerAccount):
    category_expense = models.ForeignKey(
        AccountCategory, on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Account Category Expense'),
        related_name='%(class)s_category_expense',
        help_text="The underlying expense category. Empty for accounts.")
    category_revenue = models.ForeignKey(
        AccountCategory,  on_delete=models.CASCADE, blank=True, null=True,
        verbose_name=_('Account Category Revenue'),
        related_name='%(class)s_category_revenue',
        help_text="The underlying revenue category. Empty for accounts.")

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
                fields=['tenant', 'ledger', 'hrm', 'function'],
                name='unique_ledger_pl'
            )
        ]

        verbose_name = ('Ledger - Profit/Loss')
        verbose_name_plural = _('Ledger - Profit/Loss')


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
                fields=['tenant', 'ledger', 'hrm', 'function'],
                name='unique_ledger_ic'
            )
        ]

        verbose_name = ('Ledger - Investment Calculation')
        verbose_name_plural = _('Ledger - Investment Calculations')


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
