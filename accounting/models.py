from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import (
    LogAbstract, NotesAbstract, TenantAbstract, CITY_CATEGORY)
from scerp.locales import CANTON_CHOICES
from .locales import (
    APP, API_SETUP, 
    CHART_OF_ACCOUNTS, ACCOUNT_POSITION, ACCOUNT_POSITION_CANTON, 
    ACCOUNT_CHART_MUNICIPALITY, ACCOUNT_POSITION_MUNICIPALITY,
)
from .mixins import (
    FiscalPeriodValidate,
    AccountPositionAbstractValidate, AccountPositionMunicipalityValidate)


# Definitions
class CHART_TYPE(models.IntegerChoices):
    # Used for Cantonal Charts
    BALANCE = (1, _('Bilanz'))
    FUNCTIONAL = (2, _('Funktionale Gliederung'))
    INCOME = (3, _('Erfolgsrechnung'))
    INVEST = (5, _('Investitionsrechnung') )


class DISPLAY_TYPE(models.IntegerChoices):
    # Used to display Municipality Charts
    BALANCE = CHART_TYPE.BALANCE
    INCOME = CHART_TYPE.INCOME
    INVEST = CHART_TYPE.INVEST


MAX_ACCOUNT_NR = {
    CHART_TYPE.BALANCE: 99999.99,
    CHART_TYPE.FUNCTIONAL: 9999.99,
    CHART_TYPE.INCOME: 9999.99,
    CHART_TYPE.INVEST: 9999.99,
}    

DECIMAL_FUNCTIONAL = 4, 0  # "Sachnummer" for functional is 4 digits, no comma
DECIMAL_ACCOUNT_NUMBER = 5, 2  # max length of account number incl. balance   
MAX_ACCOUNT_NR_OVERALL = max(x for x in MAX_ACCOUNT_NR.values())


# CashCtrl Basics ------------------------------------------------------------
class APISetup(TenantAbstract):
    '''only restricted to admin!
    '''
    org_name = models.CharField(
        max_length=100, **API_SETUP.Field.org_name)    
    api_key = models.CharField(
        max_length=100, **API_SETUP.Field.api_key)
    initialized = models.DateTimeField(
        max_length=100, null=True, blank=True, **API_SETUP.Field.initialized)
        
    def __str__(self):
        return self.tenant.name + self.symbols

    @property
    def api_key_hidden(self):
        return '*' * len(self.api_key)

    class Meta:
        ordering = ['tenant__name',]
        verbose_name = API_SETUP.verbose_name
        verbose_name_plural = API_SETUP.verbose_name_plural


class CashCtrl(TenantAbstract):
    '''id_cashctrl gets set after first synchronization
    '''
    c_id = models.PositiveIntegerField(
        null=True, blank=True)
    c_created = models.DateTimeField(
        default=timezone.now, null=True, blank=True)
    c_created_by = models.CharField(
        max_length=100, null=True, blank=True)
    c_last_updated = models.DateTimeField(null=True, blank=True)
    c_last_updated_by = models.CharField(
        max_length=100, null=True, blank=True)
    
    class Meta:
        abstract = True
        
        
class Location(CashCtrl):
    class Type(models.TextChoices):
        MAIN = "MAIN", _("Company Headquarters")
        BRANCH = "BRANCH", _("Branch Office")
        STORAGE = "STORAGE", _("Storage Facility")
        OTHER = "OTHER", _("Other / Tax")

    # Mandatory field
    name = models.CharField(max_length=250, help_text="A name to describe and identify the location.")

    # Optional fields
    address = models.TextField(max_length=250, blank=True, null=True, help_text="The address of the location (street, house number, additional info).")
    bic = models.CharField(max_length=11, blank=True, null=True, help_text="The BIC (Business Identifier Code) of your bank.")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="The town / city of the location.")
    country = models.CharField(max_length=3, blank=True, null=True, help_text="The country of the location, as an ISO 3166-1 alpha-3 code.")
    footer = models.TextField(blank=True, null=True, help_text="Footer text for order documents with limited HTML support.")
    iban = models.CharField(max_length=32, blank=True, null=True, help_text="The IBAN (International Bank Account Number).")
    isInactive = models.BooleanField(default=False, help_text="Marks the location as inactive. Possible values: true, false.")
    logoFileId = models.IntegerField(blank=True, null=True, help_text="File ID for the company logo. Supported types: JPG, GIF, PNG.")
    orgName = models.CharField(max_length=250, blank=True, null=True, help_text="The name of the company.")
    qrFirstDigits = models.PositiveIntegerField(blank=True, null=True, help_text="The first few digits of the Swiss QR reference. Specific to Switzerland.")
    qrIban = models.CharField(max_length=32, blank=True, null=True, help_text="The QR-IBAN, used especially for QR invoices. Specific to Switzerland.")
    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.MAIN,
        help_text="The type of location. Defaults to MAIN."
    )
    vatUid = models.CharField(max_length=32, blank=True, null=True, help_text="The VAT UID of the company.")
    zip = models.CharField(max_length=10, blank=True, null=True, help_text="The postal code of the location.")

    def __str__(self):
        return f"{self.name} (({self.type}), {self.address})"


class CostCenter(CashCtrl):
    '''CostCenters must only be created and edited in scerp
        most optional fields are null and not displayed
    '''
    name = models.CharField(max_length=100, help_text="The name of the cost center.")
    number = models.DecimalField(max_digits=20, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    class Meta:
        verbose_name = "Account Category"
        verbose_name_plural = "Account Categories"
        ordering = ['number']


class FiscalPeriod(CashCtrl, FiscalPeriodValidate):
    '''Fiscal Periods must only be created and edited in scerp
        most optional fields are null and not displayed;
        intially loaded from cashCtrl
    '''
    class CreationType(models.TextChoices):
        LATEST = "LATEST", _("Latest")
        EARLIEST = "EARLIEST", _("Earliest")

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
    is_current = models.BooleanField(
        default=False, 
        help_text="Check for current fiscl period.")

    def __str__(self):
        return self.name or f"Fiscal Period {self.pk}"

    def clean(self):
        super().clean()
        
    class Meta:
        ordering = ['-start']    


class Currency(CashCtrl):
    '''Rates must only be created and edited in scerp
        most optional fields are null and not displayed;
        intially loaded from cashCtrl
    '''
    code = models.CharField(max_length=3, help_text="The 3-characters currency code, like CHF, EUR, etc.")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['code']


class Unit(CashCtrl):
    '''Units must only be created and edited in scerp
        most optional fields are null and not displayed;
        intially loaded from cashCtrl
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

"""
class Type(LogAbstract, NotesAbstract):
    '''Model for Chart of Accounts (Canton).
    Only accessible by admin!
    '''
    type = models.PositiveSmallIntegerField(choices=CHART_TYPE.choices)

    def __str__(self):
        return self.get_type_display()
"""
class ChartOfAccountsCanton(LogAbstract, NotesAbstract):
    '''Model for Chart of Accounts (Canton).
    Only accessible by admin!
    '''    
    name = models.CharField(
        max_length=250, **CHART_OF_ACCOUNTS.Field.name)
    type = models.PositiveSmallIntegerField(
        choices=CHART_TYPE.choices, **CHART_OF_ACCOUNTS.Field.type) 
    canton = models.CharField(
        max_length=2, choices=CANTON_CHOICES, 
        **CHART_OF_ACCOUNTS.Field.canton)
    category = models.CharField(
        max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True, **CHART_OF_ACCOUNTS.Field.category)     
    chart_version = models.CharField(
        max_length=100, **CHART_OF_ACCOUNTS.Field.chart_version)
    date = models.DateField(
        **CHART_OF_ACCOUNTS.Field.date)
    excel = models.FileField(
        upload_to='uploads/', **CHART_OF_ACCOUNTS.Field.excel)
    exported_at = models.DateTimeField(
        null=True, blank=True, **CHART_OF_ACCOUNTS.Field.exported_at)

    def __str__(self):
        return f'{self.name}, V{self.chart_version}'

    class Meta:
        ordering = ['type', 'name']
        verbose_name = CHART_OF_ACCOUNTS.verbose_name
        verbose_name_plural = CHART_OF_ACCOUNTS.verbose_name_plural


# Model definition using ACCOUNT_POSITION for labels and help texts
class AccountPositionAbstract(models.Model, AccountPositionAbstractValidate):
    chart_of_accounts = models.ForeignKey(
        ChartOfAccountsCanton, on_delete=models.CASCADE, 
        related_name='%(class)s_account_position',
        **ACCOUNT_POSITION.Field.chart_of_accounts)
        
    # Excel data    
    account_number = models.CharField(        
        max_length=8, null=True, blank=True, 
        **ACCOUNT_POSITION.Field.account_number)
    account_4_plus_2 = models.CharField(
        max_length=8, null=True, blank=True, 
        **ACCOUNT_POSITION.Field.account_4_plus_2)
    name = models.CharField(
        max_length=255, **ACCOUNT_POSITION.Field.name)
    hrm_1 = models.CharField(
        max_length=255, null=True, blank=True, **ACCOUNT_POSITION.Field.hrm_1)
    description_hrm_1 = models.CharField(
        max_length=255, null=True, blank=True,
        **ACCOUNT_POSITION.Field.description_hrm_1)

    # Calculated data       
    account = models.CharField(        
        # use this for sorting, usually not displayed
        max_length=8, null=True, blank=True, 
        **ACCOUNT_POSITION.Field.account)
    ff = models.BooleanField(
        default=False,  **ACCOUNT_POSITION.Field.ff)    
    is_category = models.BooleanField(
        default=False,  **ACCOUNT_POSITION.Field.is_category)        
    number = models.DecimalField(
        max_digits=14, decimal_places=2, **ACCOUNT_POSITION.Field.number)

    def __str__(self):   
        if self.account_number:
            text = f"{self.account_number}"
        else:
            text = f"{self.account_4_plus_2}"
        return f"{text} {self.name}"

    def save(self, *args, **kwargs):
        # Call update and validation methods
        # Init
        chart_type = MAX_ACCOUNT_NR[self.chart_of_accounts.type]
        digits_functional, comma_functional, digits_nr, comma_nr = (
            *DECIMAL_FUNCTIONAL, *DECIMAL_ACCOUNT_NUMBER)
        max_account_nr = MAX_ACCOUNT_NR_OVERALL
            
        # Validate    
        self.update_related_data(
            digits_functional, comma_functional, digits_nr, comma_nr)
        self.validate_before_save(chart_type, max_account_nr)

        # Call the parent save method
        if not kwargs.pop('check_only', None):
            super().save(*args, **kwargs)

    class Meta:
        abstract = True            
    

class AccountPositionCanton(
        AccountPositionAbstract, LogAbstract, NotesAbstract):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['chart_of_accounts', 'account_number', 
                        'account_4_plus_2'], 
                name='unique_account_position_canton'
            )]     
        constraints = [
            models.UniqueConstraint(
                fields=['chart_of_accounts', 'number'], 
                name='unique_account_position_canton_number'
            )]             
        ordering = [
            'chart_of_accounts', 'chart_of_accounts__type', 'account',
            'account_4_plus_2']
        verbose_name = ACCOUNT_POSITION_CANTON.verbose_name
        verbose_name_plural = ACCOUNT_POSITION_CANTON.verbose_name_plural
    

class AccountChartMunicipality(TenantAbstract):
    '''Municipality account chart
    '''
    name = models.CharField(
        max_length=250, **ACCOUNT_CHART_MUNICIPALITY.Field.name)
    period = models.ForeignKey(
        FiscalPeriod, on_delete=models.PROTECT, related_name='period',
        **ACCOUNT_CHART_MUNICIPALITY.Field.period)

    def __str__(self):
        return f'{self.name}, {self.period}'
        
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], 
            name='unique_tenant_name')
        ]    
        ordering = ['name']
        verbose_name = ACCOUNT_CHART_MUNICIPALITY.verbose_name
        verbose_name_plural = ACCOUNT_CHART_MUNICIPALITY.verbose_name_plural


# Account related cashCtrl. Models --------------------------------------------
class AccountCategory(CashCtrl):
    '''Categories must only be created and edited in scerp
    '''    
    name = models.CharField(max_length=100, help_text="The name of the account category.")
    number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="The numeric identifier for sorting the category according to the chart of accounts."
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='subcategories',
        help_text="The parent category."
    )

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    class Meta:
        verbose_name = "Account Category"
        verbose_name_plural = "Account Categories"
        ordering = ['number']


class AccountPositionMunicipality(
        AccountPositionAbstract, CashCtrl,
        AccountPositionMunicipalityValidate):
    '''display_type cannot be functional
    '''    
    display_type = models.PositiveSmallIntegerField(
        choices=DISPLAY_TYPE.choices,
        **ACCOUNT_POSITION_MUNICIPALITY.Field.display_type)  
    chart = models.ForeignKey(
        AccountChartMunicipality, on_delete=models.CASCADE,
        related_name='%(class)s_chart', 
        **ACCOUNT_POSITION_MUNICIPALITY.Field.chart)      
    function = models.CharField(
        max_length=8, null=True, blank=True, 
        **ACCOUNT_POSITION_MUNICIPALITY.Field.function)
    category = models.ForeignKey(
        AccountCategory,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_category', 
        help_text="The category."
    )
    
    def __str__(self):
        if self.function:
            text = f'{self.function}.'
        else:
            text = ''
        return text + super().__str__()
        
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['chart', 'function', 'account_number', 
                        'account_4_plus_2', 'display_type'], 
                name='unique_account_position_municipality'
            )] 
        constraints = [
            models.UniqueConstraint(fields=['chart', 'number'], 
                name='unique_account_position_municipality_number'
            )]                 
        ordering = ['chart', 'function', 'account']
        verbose_name = ACCOUNT_POSITION_MUNICIPALITY.verbose_name
        verbose_name_plural = ACCOUNT_POSITION_MUNICIPALITY.verbose_name_plural

    def clean(self):
        super().clean()  # Call the parent's clean method
        self.clean_related_data(CHART_TYPE)


class TaxRate(CashCtrl):
    '''Rates must only be created and edited in scerp
        most optional fields are null and not displayed
    '''
    account = models.ForeignKey(
        AccountPositionMunicipality,
        on_delete=models.PROTECT,
        related_name='%(class)s_account',
        help_text="The account which collects the taxes."
    )      
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


class ArticleCategory(CashCtrl):
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
        AccountPositionMunicipality, 
        on_delete=models.PROTECT,
        related_name='purchase_account',
        help_text=(
            "The purchase account, which will be used when selling "
            "aticles in this category through."))
    sales_account = models.ForeignKey(
        AccountPositionMunicipality, 
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


class Article(CashCtrl):
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

