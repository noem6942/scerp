# accounting/models.py
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _
from decimal import Decimal

import json

from core.models import (
    LogAbstract, NotesAbstract, TenantAbstract, TenantLocation, CITY_CATEGORY)
from scerp.locales import CANTON_CHOICES

from .mixins import fiscal_period_validate, account_position_calc_number


# Definitions
class APPLICATION(models.TextChoices):
    CASH_CTRL = 'CC', 'Cash Control'


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


# CashCtrl Basics ------------------------------------------------------------
class APISetup(TenantAbstract):
    '''only restricted to admin!
        # triggers signals.py after creation!
    '''
    org_name = models.CharField(
        'org_name', max_length=100,
        help_text='name of organization as used in cashCtrl domain')
    api_key = models.CharField(
        _('api key'), max_length=100, help_text=_('api key'))
    application = models.CharField(
        _('application'), max_length=2, choices=APPLICATION.choices,
        default=APPLICATION.CASH_CTRL)
    initialized = models.DateTimeField(
        _('initialized'), max_length=100, null=True, blank=True,
        help_text=_('date and time when initialized'))
                
    # Custom groups for cashCtrl
    # name, type
    custom_field_group_account = models.PositiveSmallIntegerField(
        _('Tab Account'), blank=True, null=True,
        help_text=json.dumps({
            'name': {
                'values': {
                    'de': 'SC-ERP', 
                    'en': 'SC-ERP', 
                    'fr': 'SC-ERP', 
                    'it': 'SC-ERP'
                }},
            'type': 'ACCOUNT',
        }))        
            
    custom_field_group_person = models.PositiveSmallIntegerField(
        _('Tab Person'), blank=True, null=True,
        help_text=json.dumps({
            'name': {
                'values': {
                    'de': 'SC-ERP', 
                    'en': 'SC-ERP', 
                    'fr': 'SC-ERP', 
                    'it': 'SC-ERP'
                }},
            'type': 'PERSON',
        }))        

    # Custom fields for cashCtrl    
    custom_field_account_hrm = models.PositiveSmallIntegerField(
        _('Field Position Number'), blank=True, null=True,
        help_text=json.dumps({
            'name': {
                'values': {
                    'de': 'HRM', 
                    'en': 'HRM', 
                    'fr': 'HRM', 
                    'it': 'HRM'
                }},
            'group': custom_field_group_account.help_text, 
            'data_type': 'NUMBER', 
            'is_multi': False, 
            'values': []
        }))

    def __str__(self):
        # add symbol for notes, attachment, protected, inactive
        return self.tenant.name + self.symbols

    @property
    def api_key_hidden(self):
        return '*' * len(self.api_key)

    class Meta:
        ordering = ['tenant__name',]
        verbose_name = _('Api Setup')
        verbose_name_plural = _('Api Setup')


class AcctApp(TenantAbstract):
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

    class Meta:
        abstract = True


class Location(AcctApp):
    name = models.CharField(max_length=100)

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
        verbose_name = _("VAT, Codes, Formats")
        verbose_name_plural = verbose_name        


class CostCenter(AcctApp):
    '''CostCenters must only be created and edited in scerp
        most optional fields are null and not displayed
    '''
    name = models.CharField(max_length=100, blank=True, null=True)
    number = models.DecimalField(max_digits=20, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.number})"

    class Meta:
        verbose_name = "Cost Center"
        verbose_name_plural = "Cost Centers"


class FiscalPeriod(AcctApp):
    '''First period is loaded from cash_ctrl, all others must must only be 
        created and edited in scerp;
        most optional fields are null and not displayed;        
    '''
    name = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="The name of the fiscal period, required if isCustom is true."
    )
    start = models.DateField(
        blank=True,
        null=True,
        help_text="Start date of the fiscal period, required if isCustom is true."
    )
    end = models.DateField(
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
        fiscal_period_validate(self)

    class Meta:
        ordering = ['-start']


class Currency(AcctApp):
    '''Rates must only be created and edited in scerp
        most optional fields are null and not displayed;
        intially loaded from AcctApp
    '''    
    code = models.CharField(max_length=3, help_text="The 3-characters currency code, like CHF, EUR, etc.")
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['code']


class Unit(AcctApp):
    '''Units must only be created and edited in scerp
        most optional fields are null and not displayed;
        intially loaded from AcctApp
    '''
    name = models.CharField(max_length=100, help_text="The name of the unit ('hours', 'minutes', etc.).")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['name']


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
        _('Name'), max_length=250,
        help_text=_('Enter the name of the chart of accounts.'))
    account_type = models.PositiveSmallIntegerField(
        _('Type'), choices=ACCOUNT_TYPE_TEMPLATE.choices,
        help_text=_('Select the type of chart (e.g., Balance, Functional).'))
    canton = models.CharField(
        _('Canton'), max_length=2, choices=CANTON_CHOICES,
        help_text=_('Select the associated canton for this chart of accounts.'))
    category = models.CharField(
        _('Category'), max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True,
        help_text=_('Choose the category from the available city options.'))
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
        ordering = ['account_type', 'name']
        verbose_name = _('Chart of Accounts (Canton)')
        verbose_name_plural = _('Charts of Accounts (Canton)')


class ChartOfAccounts(TenantAbstract):
    '''Model for Chart of Accounts (individual).
    '''
    name = models.CharField(
        _('Name'), max_length=250,
        help_text=_('Enter the name of the chart of accounts.'))
    chart_version = models.CharField(
        _('Chart Version'), max_length=100, blank=True, null=True,
        help_text=_('Specify the version of the chart of accounts.'))
    period = models.ForeignKey(
        FiscalPeriod, verbose_name=_('period'),
        on_delete=models.CASCADE, related_name='%(class)s_chart',
        help_text=_('Fiscal period, automatically updated in Fiscal Period'))      

    def __str__(self):
        return f'{self.name}, V{self.chart_version}'

    class Meta:
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
        _('Name'), max_length=255,
        help_text=_('Name of the account'))
    description = models.TextField(
        _('Description'), null=True, blank=True,
        help_text=_('Position description'))

    # Calculated data, calculate with every save
    number = models.DecimalField(
        _('Number'), max_digits=14, decimal_places=2,
        help_text=_('Calculated account number for reference'))

    def __str__(self):
        return f"{self.account_number} {self.name}"
        
    class Meta:
        abstract = True


class AccountPositionTemplate(
        AccountPositionAbstract, LogAbstract, NotesAbstract):
    chart = models.ForeignKey(
        ChartOfAccountsTemplate, verbose_name=_('Chart of Accounts'),
        on_delete=models.CASCADE, related_name='%(class)s_chart',
        help_text=_('Link to the relevant chart of accounts'))     
     
    def save(self, *args, **kwargs):
        # Update number
        function = None
        number = account_position_calc_number(
            self.chart.account_type, function, self.account_number, 
            self.is_category)
        self.number = Decimal(number)
        
        # Save
        if not kwargs.pop('check_only', False):
            super().save(*args, **kwargs)
     
    class Meta:        
        constraints = [
            models.UniqueConstraint(
                fields=['chart', 'chart__account_type', 'account_number', 
                        'is_category'],
                name='unique_account_position_canton'
            )]
        constraints = [
            models.UniqueConstraint(
                fields=['chart', 'number'],
                name='unique_account_position_canton_number'
            )]
        ordering = [
            'chart', 'chart__account_type', 'account_number',  '-is_category']
        verbose_name = _('Account Position (Canton or Others)')
        verbose_name_plural = _('Account Positions (Canton or Others)')


class AccountPosition(AccountPositionAbstract, AcctApp):
    '''actual account for booking
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

    # balance
    balance = models.FloatField(
        _('Balance'), null=True, blank=True, 
        help_text=_('Balance, calculated'))
        
    # custom fields
    budget = models.FloatField(
        _('Budget'), null=True, blank=True,
        help_text=_('Budget for period given, fill out manually'))
    previous = models.FloatField(
        _('Previous Balance'), null=True, blank=True,
        help_text=_('Balance of previous period'))
    explanation = models.TextField(
        _('Explanation'), null=True, blank=True,
        help_text=_('Explanation, esp. deviations to previous period'))

    def __str__(self):
        if self.function:
            text = f'{self.function}.'
        else:
            text = ''
        return text + super().__str__()

    def clean(self):
        super().clean()  # Call the parent's clean method
        self.clean_related_data(CHART_TYPE)

    def save(self, *args, **kwargs):        
        # Update number
        number = account_position_calc_number(
            self.account_type, self.function, self.account_number, 
            self.is_category)
        self.number = Decimal(number)        
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['chart', 'function', 'account_number', 'account_type'],
                name='unique_account_position'
            )]

        constraints = [
            models.UniqueConstraint(fields=['chart', 'number'],
                name='unique_account_position_number'
            )]        
        ordering = ['chart', 'account_type', 'function', 'account_number']
        verbose_name = ('Account Position (Municipality)')
        verbose_name_plural = _('Account Positions')
        

class TaxRate(AcctApp):
    '''Rates must only be created and edited in scerp
        most optional fields are null and not displayed
    '''
    name = models.CharField(max_length=50, help_text="The name of the tax rate.")
    number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="A name to describe and identify the tax rate."
    )
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    document_name = models.CharField(
        max_length=50,
        help_text=(
            "The name for the tax rate displayed on documents (seen by "
            "customers). Leave empty to use the name instead."))

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    class Meta:
        ordering = ['number']


class ArticleCategory(AcctApp):
    '''Categories must only be created and edited in scerp
        all optional fields are null
        e.g. WATER = ('W', _('water'))
    '''
    name = models.CharField(max_length=100, help_text="The name of the account category.")
    allocations = models.ManyToManyField(CostCenter)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='subcategories',
        help_text="The parent category."
    )
    purchase_account = models.ForeignKey(
        AccountPosition,
        on_delete=models.PROTECT,
        related_name='purchase_account',
        help_text=(
            "The purchase account, which will be used when selling "
            "aticles in this category through."))
    sales_account = models.ForeignKey(
        AccountPosition,
        on_delete=models.PROTECT,
        related_name='sales_account',
        help_text=(
            "The sales account, which will be used when selling "
            "aticles in this category through."))

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    class Meta:
        verbose_name = "Account Category"
        verbose_name_plural = "Account Categories"
        ordering = ['name']


class Tarif(TenantAbstract):
    tarif = models.IntegerField(verbose_name="Tarif")  # Tariff
    tarif_bez = models.CharField(max_length=255, verbose_name="TarifBez")  # Tariff Description


class Article(AcctApp):
    name = models.CharField(
        max_length=240,
        help_text="The name of the article, with localized text as XML."
    )
    bin_location = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Location within the building (e.g., A15, B04). Only if isStockArticle is True."
    )
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.PROTECT,
        help_text="ID of the category to which this article belongs."
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        help_text="ID of the currency. Defaults to the system currency if not specified."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Localized description in XML format."
    )
    is_inactive = models.BooleanField(
        default=False,
        help_text="Mark the article as inactive. Default is false."
    )
    is_purchase_price_gross = models.BooleanField(
        default=False,
        help_text="Defines the purchase price as gross (including tax). Default is false."
    )
    is_sales_price_gross = models.BooleanField(
        default=False,
        help_text="Defines the sales price as gross (including tax). Default is false."
    )
    is_stock_article = models.BooleanField(
        default=False,
        help_text="Whether the article has a stock. Default is false."
    )
    last_purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Last purchase price of the article. Excludes tax unless is_purchase_price_gross is true."
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        help_text="ID of the tax or building location."
    )
    max_stock = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Desired maximum stock. Only applies if isStockArticle is true."
    )
    min_stock = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Desired minimum stock. Only applies if isStockArticle is true."
    )
    article_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The article number. Leave empty to generate using sequenceNumberId."
    )
    sales_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Sales price of the article, excludes tax unless is_sales_price_gross is true."
    )
    sequence_number_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="ID of the sequence number to generate article number."
    )
    stock = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Current stock level. Only applies if isStockArticle is true."
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        help_text="ID of the unit for the article."
    )
    # customs
    custom_tarif = models.ForeignKey(
        Tarif, null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="select Tarif"
    )
    custom_ansatz = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="ID of the unit for the article."
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
