# accounting/models.py
from enum import Enum

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.db.models import UniqueConstraint
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .api_cash_ctrl import (
    URL_ROOT, FIELD_TYPE, DATA_TYPE, ROUNDING, TEXT_TYPE)
from scerp.mixins import multi_language


from core.models import (
    LogAbstract, NotesAbstract, Tenant, TenantAbstract, TenantSetup,
    TenantLogo)
from crm.models import (
    PersonCategory as CrmPersonCategory,
    Title as CrmTitle,
    PhysicalPerson as CrmPerson,
    Employee as CrmEmployee
)
from scerp.locales import CANTON_CHOICES


CODE_MAX_LEN = 200  # for converting cashCtrl name to key

# Definitions
class APPLICATION(models.TextChoices):
    CASH_CTRL = 'CC', 'Cash Control'


class ACCOUNT_SIDE(models.TextChoices):
    CREDIT = 'C', _('Credit')
    DEBIT = 'D', _('Debit')


class ACCOUNT_TYPE_TEMPLATE(models.IntegerChoices):
    # Used for Cantonal / Template Charts
    BALANCE = (1, _('Bilanz'))
    FUNCTIONAL = (2, _('Funktionale Gliederung'))  # only for template
    INCOME = (3, _('Erfolgsrechnung'))
    INVEST = (5, _('Investitionsrechnung') )


class ACCOUNT_TYPE(models.IntegerChoices):
    # Used to display Accounting Charts with bookings, no functionals
    BALANCE = ACCOUNT_TYPE_TEMPLATE.BALANCE
    INCOME = ACCOUNT_TYPE_TEMPLATE.INCOME
    INVEST = ACCOUNT_TYPE_TEMPLATE.INVEST


class CATEGORY_HRM(Enum):
    # First digits account_number, name
    ASSET = [1], "ASSET"
    LIABILITY = [2], "LIABILITY"
    EXPENSE = [3, 5], "EXPENSE"
    REVENUE = [4, 6], "REVENUE"
    BALANCE = [9], "BALANCE"

    def get_scope(category):
        try:
            scope, _label = category.value
            return scope
        except:
            return None


# CashCtrl Basics ------------------------------------------------------------
class APISetup(TenantAbstract):
    '''only restricted to admin!
        triggers signals.py past_save
        org_name, application is unique (cashCtrl)
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

    @property
    def api_key_hidden(self):
        return '*' * len(self.api_key)

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


class Acct(models.Model):
    '''id_cashctrl gets set after first synchronization
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

    class Meta:
        abstract = True


class AcctApp(TenantAbstract, Acct):
    '''id_cashctrl gets set after first synchronization
    '''
    def assign_setup(self):
        if not getattr(self, 'setup', None):
            # Query the default value
            default_value = APISetup.objects.filter(
                tenant=self.tenant, is_default=True).first()
            if not default_value:
                raise IntegrityError(f"No default_value for {self.org_name}")
            self.setup = default_value

    class Meta:
        abstract = True


# Internals for cashCtrl
class CustomFieldGroup(AcctApp):
    '''
    Create custom field group that is then sent to cashCtrl via signals
    '''
    FIELD_TYPE = [(x.value, x.value) for x in FIELD_TYPE]

    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
    name = models.JSONField(
        _('Name'), help_text="The name of the group.")
    type = models.CharField(
        _("Type"), max_length=50, choices=FIELD_TYPE,
        help_text='''
            The type of group, meaning: which module the group belongs to.
            Possible values: JOURNAL, ACCOUNT, INVENTORY_ARTICLE,
            INVENTORY_ASSET, ORDER, PERSON, FILE.''')

    def __str__(self):
        return self.code

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
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
        _('Code'), max_length=50, help_text='Internal code for scerp')
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
            INVENTORY_ASSET, ORDER, PERSON, FILE.''')
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

    def __str__(self):
        return self.code

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_custom_setup_field'
            )
        ]
        ordering = ['group__code', 'code']
        verbose_name = _("Custom Field")
        verbose_name_plural = _("Custom Field")


class Setting(TenantAbstract):
    '''Read - only
    '''
    data = models.JSONField(_('Index'), blank=True, null=True)
    setup = models.ForeignKey(
        APISetup, verbose_name=_('Accounting Setup'),
        on_delete=models.CASCADE, related_name='%(class)s_setup',
        help_text=_('Account Setup used'))

    def __str__(self):
        return self.setup.org_name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup',],
                name='unique_setup'
            )
        ]
        ordering = ['setup__org_name']
        verbose_name = _("Settings")
        verbose_name_plural = f"{verbose_name}"


class MappingId(AcctApp):
    '''For maintenance only
    '''
    class TYPE(models.TextChoices):
        CUSTOM_FIELD_GROUP = 'custom_field_group'
        CUSTOM_FIELD = 'custom_field'
        ACCOUNT_CATEGORY = 'account_category'
        PERSON_CATEGORY = 'person_category'
        ACCOUNT = 'account'

    # Mandatory field
    type = models.CharField(_("Type"), max_length=50, choices=TYPE)
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), null=True, blank=True)

    def __str__(self):
        return f'{self.type}-{self.name}: {self.c_id}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'type', 'name'],
                name='unique_constants'
            )
        ]
        ordering = ['type', 'name']
        verbose_name = _("Mapping Id")
        verbose_name_plural = _("Mapping Ids")


# CashCtrl entities
class Location(AcctApp):
    '''Master, currently Read - only
    '''
    class TYPE(models.TextChoices):
        MAIN = "MAIN", _("Headquarters")
        BRANCH = "BRANCH", _("Branch Office")
        STORAGE = "STORAGE", _("Storage Facility")
        OTHER = "OTHER", _("Other / Tax")

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
                fields=['setup', 'name'],
                name='unique_setup_location'
            )
        ]
        ordering = ['name']
        verbose_name = _("Location: Logo, Address, VAT, Codes, Formats etc. ")
        verbose_name_plural = f"{verbose_name}"
        

class Currency(AcctApp):
    '''Read - only
    '''
    code = models.CharField(
        max_length=3,
        help_text=_("The 3-characters currency code, like CHF, EUR, etc."))
    description = models.JSONField(_('Description'), blank=True, null=True)    
    rate = models.FloatField(_('Rate'), blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.code

    @classmethod
    def get_default(cls):
        """
        Returns the default currency if one is set; otherwise, returns None.
        """
        return cls.objects.filter(is_default=True).first()

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
    '''Read - only
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
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
        return self.code

    class Meta:
        '''
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_setup_sequence_number'
            )
        ]
        '''
        ordering = ['name']
        verbose_name = _("Sequence Number")
        verbose_name_plural = f"{_('Sequence Numbers')}"


class Unit(AcctApp):
    ''' Master
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), default=dict,
        help_text=_("The name of the unit ('hours', 'minutes', etc.)."))
    is_default = models.BooleanField(_("Is default"), default=False)

    def __str__(self):
        return self.code

    class Meta:
        '''
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_setup_unit'
            )
        ]
        '''
        ordering = ['name']
        verbose_name = _("Unit")
        verbose_name_plural = f"{_('Units')}"


class Text(AcctApp):
    ''' Text Blocks
    '''
    TEXT_TYPE = [(x.value, x.value) for x in TEXT_TYPE]
    
    name = models.CharField(
        _('Name'), max_length=200, 
        help_text='A name to describe and identify the text template.')
    is_default = models.BooleanField(
        _('Is default'), default=False, 
        help_text=_('use this setup for adding accounting data'))
    type = models.CharField(
        _('mode'),
        max_length=20, choices=TEXT_TYPE, 
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
    '''Master
    '''
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
        return f"{self.number} {multi_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'number'],
                name='unique_setup_cost_center_category'
            )
        ]
        ordering = ['number']
        verbose_name = _("Cost Center Category")
        verbose_name_plural = _("Cost Center Categories")


class CostCenter(AcctApp):
    '''Master
    '''
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
        return f"{self.number} {multi_language(self.name)}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'number'],
                name='unique_setup_cost_center'
            )
        ]        
        ordering = ['number']
        verbose_name = _("Cost Center")
        verbose_name_plural = _("Cost Centers")


class AccountCategory(AcctApp):
    '''Actual Account Category in cashCtrl
    AccountCategory and Account must be loaded before Tax and Rounding
    '''    
    name = models.JSONField(
        _('Name'), default=dict, help_text="The name of the cost center.")
    number = models.FloatField(
        _('Number'), help_text=_("The name of the account category."))
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True, null=True,
        on_delete=models.CASCADE, related_name='%(class)s_parent',
        help_text=_('The parent category.'))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'c_id'], 
                name='unique_setup_account_category'
            )
        ]
        # Lexicographic ordering
        ordering = [Cast('number', models.CharField())]  
        verbose_name = ('Account Category')
        verbose_name_plural = _('Account Categories')

    def __str__(self):
        return f"{self.number} {multi_language(self.name)}"
        

class Account(AcctApp):
    '''Actual cashCtrl account
        triggers signals.py post_save
    '''
    category = models.ForeignKey(
        AccountCategory, verbose_name=_('Account Category'),
        on_delete=models.CASCADE, related_name='%(class)s_category',
        help_text=_('Internal reference'))
    account_number = models.DecimalField(
        _('Account Number'), max_digits=20, decimal_places=2,
        help_text=_(
            'The account number. Must be numeric but can contain a decimal point.'))
    allocations = models.ManyToManyField(
        CostCenter, verbose_name=_('Allocations'),
        help_text=_(
            'Allocations to cost centers, if this account is either an expense '
            'or revenue account.'))
    currency = models.ForeignKey(
        Currency, verbose_name=_('Currency'), default=Currency.get_default,
        on_delete=models.PROTECT, related_name='%(class)s_currency',
        help_text=_(
            "Link to currency. Defaults to the system currency if not specified."))
    custom = models.JSONField(
        _('Custom Fields'), blank=True, null=True,
        help_text=_(
            'Custom field values. Example: '
            '{"customField1": "My value", "customField2": ["value 1", "value 2"]}. '
            'Refer to the Custom Fields API for variable names.'
        )
    )
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
    tax = models.ForeignKey(
        'Tax', verbose_name=_('Tax'),
        on_delete=models.PROTECT, blank=True, null=True,
        related_name='%(class)s_tax',
        help_text=_("Link to tax. Not used."))  # Verify
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'account_number'],
                name='unique_setup_account'
            )
        ]
        ordering = ['account_number']
        verbose_name = ('Account')
        verbose_name_plural = _('Accounts')
        

class Configuration(AcctApp):
    """
    Represents the system's configuration for financial and accounting settings.
    """    
    # Format Settings
    csv_delimiter = models.CharField(
        max_length=5, 
        default=";", 
        verbose_name=_("CSV Delimiter")
    )
    thousand_separator = models.CharField(
        max_length=1, 
        blank=True, 
        null=True, 
        verbose_name=_("Thousand Separator")
    )
    
    # Account Settings
    default_debtor_account = models.ForeignKey(
        'Account', 
        related_name='debtor_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Debtor Account")
    )
    default_opening_account = models.ForeignKey(
        'Account', 
        related_name='opening_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Opening Account")
    )
    default_creditor_account = models.ForeignKey(
        'Account', 
        related_name='creditor_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Creditor Account")
    )
    default_exchange_diff_account = models.ForeignKey(
        'Account', 
        related_name='exchange_diff_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Exchange Difference Account")
    )
    default_profit_allocation_account = models.ForeignKey(
        'Account', 
        related_name='profit_allocation_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Profit Allocation Account")
    )
    default_inventory_disposal_account = models.ForeignKey(
        'Account', 
        related_name='inventory_disposal_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Inventory Disposal Account")
    )
    default_input_tax_adjustment_account = models.ForeignKey(
        'Account', 
        related_name='input_tax_adjustment_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Input Tax Adjustment Account")
    )
    default_sales_tax_adjustment_account = models.ForeignKey(
        'Account', 
        related_name='sales_tax_adjustment_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Sales Tax Adjustment Account")
    )
    default_inventory_depreciation_account = models.ForeignKey(
        'Account', 
        related_name='inventory_depreciation_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Inventory Depreciation Account")
    )
    default_inventory_asset_revenue_account = models.ForeignKey(
        'Account', 
        related_name='inventory_asset_revenue_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Inventory Asset Revenue Account")
    )
    default_inventory_article_expense_account = models.ForeignKey(
        'Account', 
        related_name='inventory_article_expense_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Inventory Article Expense Account")
    )
    default_inventory_article_revenue_account = models.ForeignKey(
        'Account', 
        related_name='inventory_article_revenue_accounts', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Default Inventory Article Revenue Account")
    )
    default_sequence_number_inventory_asset = models.IntegerField(
        default=4, 
        verbose_name=_("Default Sequence Number for Inventory Asset")
    )
    default_sequence_number_inventory_article = models.IntegerField(
        default=2, 
        verbose_name=_("Default Sequence Number for Inventory Article")
    )
    default_sequence_number_person = models.IntegerField(
        default=5, 
        verbose_name=_("Default Sequence Number for Person")
    )
    default_sequence_number_journal = models.IntegerField(
        default=6, 
        verbose_name=_("Default Sequence Number for Journal")
    )

    # General Settings
    first_steps_logo = models.BooleanField(
        default=True, 
        verbose_name=_("Show Logo in First Steps")
    )
    first_steps_account = models.BooleanField(
        default=True, 
        verbose_name=_("Enable First Steps Account Setup")
    )
    first_steps_currency = models.BooleanField(
        default=True, 
        verbose_name=_("Enable First Steps Currency Setup")
    )
    first_steps_pro_demo = models.BooleanField(
        default=True, 
        verbose_name=_("Enable Pro Demo First Steps")
    )
    first_steps_tax_rate = models.BooleanField(
        default=True, 
        verbose_name=_("Enable First Steps Tax Rate Setup")
    )
    first_steps_tax_type = models.BooleanField(
        default=True, 
        verbose_name=_("Enable First Steps Tax Type Setup")
    )
    order_mail_copy_to_me = models.BooleanField(
        default=True, 
        verbose_name=_("Copy Order Mails to Me")
    )
    tax_accounting_method = models.CharField(
        max_length=50, 
        default="AGREED", 
        verbose_name=_("Tax Accounting Method")
    )
    journal_import_force_sequence_number = models.BooleanField(
        default=False, 
        verbose_name=_("Force Sequence Number for Journal Import")
    )

    def __str__(self):
        return f"Configuration {self.pk}"

    class Meta:
        verbose_name = _("Configuration")
        verbose_name_plural = _("Configurations")


class Tax(AcctApp):
    ''' Master
    '''
    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), blank=True, null=True,
        help_text=_("The name of the tax rate."))
    account = models.ForeignKey(
        'Account', verbose_name=_('Account'),
        on_delete=models.CASCADE, blank=True, null=True,
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

    def __str__(self):
        return self.code

    class Meta:
        '''
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_setup_tax'
            )
        ]
        '''
        ordering = ['name']
        verbose_name = _("Tax Rate")
        verbose_name_plural = f"{_('Tax Rates')}"


class Rounding(AcctApp):
    '''Needs to have an account
    '''
    MODE = [(x.value, x.value) for x in ROUNDING]
    code = models.CharField(
        _('Code'), max_length=50, help_text='Internal code for scerp')
    name = models.JSONField(
        _('name'), default=dict,
        help_text=_("The name of the rounding."))
    account = models.ForeignKey(
        'Account', verbose_name=_('Account'),
        on_delete=models.CASCADE, null=True, blank=True,  # remove later
        related_name='%(class)s_account',
        help_text=_('The account which collects the roundings'))        
    rounding = models.DecimalField(
        _('rounding'), max_digits=5, decimal_places=2)
    mode = models.CharField(
        _('mode'),
        max_length=20, choices=MODE, default=ROUNDING.HALF_UP.value,
        help_text=_("The rounding mode. Defaults to HALF_UP."))

    def __str__(self):
        return self.code

    class Meta:
        '''
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'code'],
                name='unique_setup_rounding'
            )
        ]
        '''
        ordering = ['name']
        verbose_name = _("Rounding")
        verbose_name_plural = f"{_('Roundings')}"


class FiscalPeriod(AcctApp):
    '''Read - only
    '''
    name = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="The name of the fiscal period, required if isCustom is true."
    )
    start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Start date of the fiscal period, required if isCustom is true."
    )
    end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="End date of the fiscal period, required if isCustom is true."
    )
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
                fields=['setup', 'name'],
                name='unique_setup_period'
            )
        ]
        ordering = ['-start']
        verbose_name = _("Fiscal Period")
        verbose_name_plural = f"{_('Fiscal Periods')}"


class OrderCategory(AcctApp):
    '''Read - only
    '''
    name_plural = models.JSONField(
        _('name'), blank=True, null=True,
        help_text=_("he plural name of the category (e.g. 'Invoices')."))
    account_id = models.PositiveIntegerField(
        _('Account Id'), blank=True, null=True,
        help_text=_(
            """The ID of the account, which is typically the debtors
            account for sales and the creditors account for purchase. """))
    status = models.JSONField(
        _('status'),
        help_text=_(
            "The status list (like 'Draft', 'Open', 'Paid', etc.) for this "
            "order category."))
    address_type = models.CharField(
        _('address type'), max_length=20,
        help_text=(
            """Which address of the recipient to use in the order document.
            Defaults to MAIN. Possible values: MAIN, INVOICE, DELIVERY,
            OTHER."""))
    due_days =  models.PositiveIntegerField(
        _('Due Days'), null=True, blank=True,
        help_text=_(
            """The due days used by default for order objects in this category.
            The order date + due days equals the due date."""))

    @property
    def local_name(self):
        return multi_language(self.name_plural)

    def __str__(self):
        return self.local_name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'c_id'],
                name='unique_c_id_per_tenant_setup__order_category'
            )
        ]
        ordering = ['name_plural']
        verbose_name = _("Order Category")
        verbose_name_plural = f"{_('Order Categories')}"


class OrderTemplate(AcctApp):
    '''Read - only
    '''
    name = models.TextField(
        _('name'),
        help_text=_("The name to describe and identify the template."))
    is_default = models.BooleanField(
        _('is default'),
        help_text=_(
            "Mark the template as the default template to use. Defaults to "
            "false.  "))

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'c_id'],
                name='unique_c_id_per_tenant_setup__order_template'
            )
        ]
        ordering = ['name']
        verbose_name = _("Order Template")
        verbose_name_plural = f"{_('Order Templates')}"


class Article(AcctApp):
    """
    Article Model for inventory and sales management.
    """
    name = models.JSONField(
        _('Name'),
        help_text=_("The name of the article. For localized text, use XML format: "
                    "<values><de>German text</de><en>English text</en></values>."),
        null=True,
        blank=True,
    )
    bin_location = models.CharField(
        _('Bin Location'),
        max_length=255,
        help_text=_("The place within the building (e.g., A15, B04, C11). "
                    "Ignored unless isStockArticle is true."),
        null=True,
        blank=True,
    )
    category_id = models.PositiveIntegerField(
        _('Category ID'),
        help_text=_("The ID of the category. See Article category."),
        null=True,
        blank=True,
    )
    currency_id = models.PositiveIntegerField(
        _('Currency ID'),
        help_text=_("The ID of the currency. Leave empty to use the default currency."),
        null=True,
        blank=True,
    )
    custom = models.JSONField(
        _('Custom Fields'),
        help_text=_("Custom field values in XML format: "
                    "<values><customField1>My value</customField1></values>."),
        null=True,
        blank=True,
    )
    description = models.JSONField(
        _('Description'),
        help_text=_("A description of the article. For localized text, use XML format: "
                    "<values><de>German text</de><en>English text</en></values>."),
        null=True,
        blank=True,
    )
    is_inactive = models.BooleanField(
        _('Is Inactive'),
        default=False,
        help_text=_("Mark the article as inactive. Defaults to false."),
    )
    is_purchase_price_gross = models.BooleanField(
        _('Is Purchase Price Gross'),
        default=False,
        help_text=_("Defines the purchase price as gross (including tax). Defaults to false."),
    )
    is_sales_price_gross = models.BooleanField(
        _('Is Sales Price Gross'),
        default=False,
        help_text=_("Defines the sales price as gross (including tax). Defaults to false."),
    )
    is_stock_article = models.BooleanField(
        _('Is Stock Article'),
        default=False,
        help_text=_("Whether the article has stock and should be tracked."),
    )
    last_purchase_price = models.DecimalField(
        _('Last Purchase Price'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("The last purchase price of the article. Defaults to net unless isPurchasePriceGross is true."),
    )
    location_id = models.PositiveIntegerField(
        _('Location ID'),
        null=True,
        blank=True,
        help_text=_("The ID of the location (e.g., a warehouse). Ignored unless isStockArticle is true."),
    )
    max_stock = models.PositiveIntegerField(
        _('Max Stock'),
        null=True,
        blank=True,
        help_text=_("The desired maximum stock of the article. Ignored unless isStockArticle is true."),
    )
    min_stock = models.PositiveIntegerField(
        _('Min Stock'),
        null=True,
        blank=True,
        help_text=_("The desired minimum stock of the article. Ignored unless isStockArticle is true."),
    )
    notes = models.TextField(
        _('Notes'),
        null=True,
        blank=True,
        help_text=_("Optional notes with limited HTML support. "
                    "Allowed tags: a, p, div, etc."),
    )
    nr = models.CharField(
        _('Article Number'),
        max_length=50,
        null=True,
        blank=True,
        help_text=_("The article number. Leave empty to auto-generate."),
    )
    sales_price = models.DecimalField(
        _('Sales Price'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("The sales price of the article. Defaults to net unless isSalesPriceGross is true."),
    )
    sequence_number_id = models.PositiveIntegerField(
        _('Sequence Number ID'),
        null=True,
        blank=True,
        help_text=_("The ID of the sequence number used to generate the article number."),
    )
    stock = models.PositiveIntegerField(
        _('Stock'),
        null=True,
        blank=True,
        help_text=_("The current stock of the article. Ignored unless isStockArticle is true."),
    )
    unit_id = models.CharField(
        _('Unit ID'),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("The ID of the unit (like pcs., meters, liters)."),
    )

    def __str__(self):
        return multi_language(self.name)

    class Meta:
        ordering = ['nr']
        constraints = [
            models.UniqueConstraint(
                fields=['setup', 'c_id'],
                name='unique_c_id_per_tenant_setup'
            )
        ]
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")


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
    '''
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
    allocations = models.ManyToManyField(CostCenter)
    currency = models.ForeignKey(
        Currency, verbose_name=_('Currency'), null=True, blank=True,
        on_delete=models.PROTECT,
        help_text="ID of the currency. Defaults to the system currency if not specified."
    )

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

    @property
    def side(self):
        category = self.category_hrm
        if category in [CATEGORY_HRM.ASSET, CATEGORY_HRM.EXPENSE]:
            return ACCOUNT_SIDE.DEBIT
        return ACCOUNT_SIDE.CREDIT

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


# CRM models ------------------------------------------------------------
class CRM(Acct):
    tenant = models.ForeignKey(
        Tenant, verbose_name=_('tenant'),
        on_delete=models.CASCADE,
        help_text=_('assignment of tenant / client'))

    class Meta:
        abstract = True


class PersonCategory(CRM):
    '''store categories
    '''
    crm = models.OneToOneField(
        CrmPersonCategory,
        on_delete=models.CASCADE,
        related_name="person_category",
        help_text="internal use for mapping")


class Title(CrmTitle, AcctApp):
    ''' Superset of CrmTitle which is not abstract 
    '''
    class Meta:        
        pass  # handle constraints in CRM
        

class Person(CRM):
    '''store categories
    '''
    crm = models.OneToOneField(
        CrmPerson,
        on_delete=models.CASCADE,
        related_name="person",
        help_text="internal use for mapping")


class Employee(CRM):
    '''store categories
    '''
    crm = models.OneToOneField(
        CrmEmployee,
        on_delete=models.CASCADE,
        related_name="employee",
        help_text="internal use for mapping")
