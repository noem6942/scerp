# forms.py
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import SelectMultiple
from django.utils.html import format_html
from django.utils.translation import gettext as _

from django_admin_action_forms import action_with_form, AdminActionForm

from core.models import PersonAddress as AddressMapping
from core.safeguards import get_tenant
from core.models import Address, Contact
from scerp.admin import verbose_name_field
from scerp.forms import MultilanguageForm, make_multilanguage_form

from . banking import extract_qr_from_pdf, get_bic
from .models import (
    AccountPositionTemplate, ChartOfAccountsTemplate,
    ChartOfAccounts, AccountPosition, Currency, CostCenterCategory,
    CostCenter, Rounding, AccountCategory, Account, BankAccount, Allocation, 
    Unit, Tax, BookTemplate, OrderCategoryContract, OrderCategoryIncoming,
    ArticleCategory, Article, Ledger, LedgerBalance, LedgerPL, LedgerIC
)

LABEL_BACK = _("Back")


# Name forms
class NameAdminForm(MultilanguageForm):
    multi_lang_fields = ['name']

    # Dynamically create fields for each language
    class Meta:
        model = Rounding
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


class RoundingAdminForm(NameAdminForm):
    pass


class CostCenterCategoryAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = CostCenterCategory


class CostCenterAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = CostCenter


class AccountCategoryAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = AccountCategory


class AccountAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = Account


class UnitAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = Unit


class TaxAdminForm(NameAdminForm):
    multi_lang_fields = ['name', 'document_name']

    class Meta:
        model = Tax
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


class BookTemplateAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = BookTemplate


class OrderCategoryContractAdminForm(MultilanguageForm):
    multi_lang_fields = ['name_singular', 'name_plural']

    class Meta:
        model = OrderCategoryContract
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


class OrderCategoryIncomingAdminForm(MultilanguageForm):
    multi_lang_fields = ['name_singular', 'name_plural']

    class Meta:
        model = OrderCategoryIncoming
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


class ArticleCategoryAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = ArticleCategory


class BankAccountAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = BankAccount


class ArticleAdminForm(MultilanguageForm):
    multi_lang_fields = ['name', 'description']

    # Dynamically create fields for each language
    class Meta:
        model = Article
        fields = '__all__'
        
    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


"""
class OrderCategoryAdminForm(NameAdminForm):
    multi_lang_fields = ['name_plural', 'document_name']
       
    class Meta(NameAdminForm.Meta):
        model = OrderCategory
"""

class LedgerAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = Ledger


class LedgerBalanceAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = LedgerBalance


class LedgerPLAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = LedgerPL


class LedgerICAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = LedgerIC


# Other multilanguage forms
class CurrencyAdminForm(NameAdminForm):
    multi_lang_fields = ['description']

    # Dynamically create fields for each language
    class Meta:
        model = Currency
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


# AccountSetup
class ConfirmForm(AdminActionForm):
    # Show data
    class Meta:
        list_objects = False
        help_text = _(
            "Are you sure you want proceed with this action?")


# Update data
class AccountingUpdateForm(AdminActionForm):
    overwrite_data = forms.BooleanField(
        label='Overwrite Data',
        initial=True,
        required=False,
        help_text=_(
            'Overwrite existing data with values from accounting system.')
    )
    delete_not_existing = forms.BooleanField(
        label='Delete Not Existing',
        initial=True,
        required=False,
        help_text=_('Delete items that do not exist in accounting system.')
    )
    

class IncomingOrderForm(AdminActionForm):
    price_incl_vat = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=True, 
        label=_('Price (Incl. VAT)')
    )    
    iban = forms.CharField(
        max_length=255, 
        required=True, 
        label=_('IBAN')
    )
    qr_iban = forms.CharField(
        max_length=255, 
        required=True, 
        label=_('QR IBAN')
    )    
    bic = forms.CharField(
        max_length=255, 
        required=True, 
        label=_('BIC Code')
    )    

    def __post_init__(self, modeladmin, request, queryset):
        # Get invoice
        invoice = queryset.first()
        bank_account = invoice.supplier_bank_account

        # Helptext
        label = _('from contract')   
        self.fields['price_incl_vat'].help_text=(
            f"{label}: {invoice.contract.price_excl_vat} ({_('excl. VAT')})")
        if bank_account:         
            self.fields['iban'].help_text = f"{label}: {bank_account.iban}"
            self.fields['qr_iban'].help_text = f"{label}: {bank_account.qr_iban}"
            self.fields['bic'].help_text = f"{label}: {bank_account.bic}"
        
        # file retrieving
        print("*bank_account", bank_account)
        if invoice.attachments.exists():
            for attachment in invoice.attachments.all():
                # Ensure it's a PDF
                if attachment.file.name.lower().endswith('.pdf'):
                    # Pass the file path
                    qr_data = extract_qr_from_pdf(attachment.file.path)  
                    if qr_data and qr_data.get('creditor'):
                        iban = qr_data['creditor']['iban']
                        self.fields['price_incl_vat'].initial = qr_data[
                            'amount']
                        self.fields['iban'].initial = iban                        
                        self.fields['qr_iban'].initial = iban
                        self.fields['bic'].initial = get_bic(iban)
                        break

# ChartOfAccountsCanton
class ChartOfAccountsTemplateForm(AdminActionForm):
    # Show data
    class Meta:
        list_objects = False
        help_text = _(
            "Former chart positions get overwritten. "
            "Are you sure you want proceed with this action?")


# ChartOfAccounts
class ChartOfAccountsForm(AdminActionForm):
    # Show data
    chart = forms.ChoiceField(
        label=verbose_name_field(AccountPosition, 'chart'),
        choices=[], required=True,
        help_text=_("Select the appropriate chart for the municipality."))

    class Meta:
        list_objects = False
        help_text = _("Non existing positions will be created, existing "
                      "positions will be updated.")

    def assign_charts(self, request):
        # Get charts
        charts = ChartOfAccounts.objects.all()

        # Filter tenant
        tenant = get_tenant(request)
        if tenant['id']:
            charts = charts.filter(tenant__id=tenant['id'])

        self.fields['chart'].choices = [(x.id, str(x)) for x in charts]

    def hide_controls(self):
        self.fields.pop('chart', None)
        self.fields.pop('allow_overwrite', None)
        self.Meta.confirm_button_text = LABEL_BACK

    def check_types(self, request, queryset, type_from):
        # Check mixed types
        types = set([x.chart.account_type for x in queryset.all()])
        if len(types) > 1:
            messages.error(request, _("mixed types are not allowed."))
            self.hide_controls()
            return

        # Check if mixed types
        template = ChartOfAccountsTemplate.ACCOUNT_TYPE_TEMPLATE
        for type in types:
            if type in [template.INCOME, template.INVEST]:
                msg = _("Income or invest positions can only be created "
                        "from functionals.")
                messages.error(request, msg)
                self.hide_controls()
                return

        # Check if wrong type
        type_select = types.pop()
        if type_select != type_from:
            msg = _("not a type '{type_from}' selected.").format(
                type_from=type_from.label)
            messages.error(request, msg)
            self.hide_controls()
            return

        self.Meta.confirm_button_text = None  # default


class ChartOfAccountsBalanceForm(
        ChartOfAccountsForm):
    def __post_init__(self, modeladmin, request, queryset):
        self.assign_charts(request)
        self.check_types(
            request, queryset,
            ChartOfAccountsTemplate.ACCOUNT_TYPE_TEMPLATE.BALANCE)


class ChartOfAccountsFunctionForm(
        ChartOfAccountsForm):
    def __post_init__(self, modeladmin, request, queryset):
        self.assign_charts(request)
        self.check_types(
            request, queryset,
            ChartOfAccountsTemplate.ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL)


# AccountPosition
class AccountPositionForm(AdminActionForm):
    # Show data
    positions = forms.ModelMultipleChoiceField(
        label=ChartOfAccountsTemplate._meta.verbose_name,
        queryset = AccountPositionTemplate.objects.filter(
            is_category=False).order_by('account_number'),
        required=True,
        widget=SelectMultiple(attrs={'size': '20'})  # Adjust number of visible rows
    )

    class Meta:
        list_objects = True
        help_text = None

    def error(self, request, msg):
        messages.error(request, msg)
        self.fields.pop('positions', None)
        self.Meta.confirm_button_text = LABEL_BACK

    def __post_init__(self, modeladmin, request, queryset, account_type):
        # Check account type
        for function in queryset:
            if function.account_type != account_type:
                msg = _("Postion selected must be type '{account_type}'.").format(
                        account_type=account_type.label)
                self.error(request, msg)
                return

        # Check function length
        for function in queryset:
            if len(function.function) < 4:
                msg = _("'{function.function} {function.name}' is not an account. "
                    ).format(function=function)
                msg += _("Postions can only be added to 4 digit accounts. ")
                self.error(request, msg)
                return

        # define choices
        filter = self.fields['positions'].queryset.filter(
            chart__account_type=account_type)
        self.fields['positions'].queryset = filter


class AccountPositionAddIncomeForm(AccountPositionForm):
    def __post_init__(self, modeladmin, request, queryset):
        super().__post_init__(modeladmin, request, queryset,
        ACCOUNT_TYPE_TEMPLATE.INCOME)


class AccountPositionAddInvestForm(AccountPositionForm):
    def __post_init__(self, modeladmin, request, queryset):
        super().__post_init__(modeladmin, request, queryset,
        ACCOUNT_TYPE_TEMPLATE.INVEST)


class ChartOfAccountsDateForm(AdminActionForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Effective Date",
        required=True,
        help_text=_(
            "Enter the date shown in opening bookings. Must be within "
            "fiscal period")
    )

    def __post_init__(self, modeladmin, request, queryset):
        # Determine the maximum 'modified_at' date from the queryset
        last_modified = queryset.order_by('modified_at').last()
        if last_modified:
            # Set the initial value for the 'date' field
            self.fields['date'].initial = last_modified.modified_at


class AssignResponsibleForm(AdminActionForm):
    responsible = forms.ModelChoiceField(
        queryset=Group.objects.all().order_by('name'),
        required=True,
        label="Responsible Group",
        help_text="Select a group to assign as responsible."
    )


class LedgerBalanceUploadForm(AdminActionForm):
    excel_file = forms.FileField(
        required=True,
        label=_("Upload Excel File"),
        help_text=(
            _("Excel must contain the following colums:") +
            "'hrm', 'name'" + " ," + _("optionally") +
            "'opening_balance', 'closing_balance', 'increase', 'decrease', 'notes'")
    )

    class Meta:
        help_text = format_html(_(
            '''Upload Excel File to Balance.
                Excel must contain the following colums:<br>
                - hrm<br>
                - name<br><br>
                Optionally:<br>
                - opening_balance<br>
                - closing_balance<br>
                - increase<br>
                - decrease<br>
                - notes
            '''))



class LedgerPLUploadForm(AdminActionForm):
    excel_file = forms.FileField(
        required=True,
        label=_("Upload Excel File"),
    help_text = _(
        "Excel must contain the following columns: "
        "'hrm', 'name', optionally: 'expense', 'revenue', 'expense_budget', "
        "'revenue_budget', 'expense_previous', 'revenue_previous', 'notes'."
    ))

    class Meta:
        help_text = format_html(_(
            '''Upload Excel File to Balance.
                Excel must contain the following colums:<br>
                - hrm<br>
                - name<br><br>
                Optionally:<br>
                - expense<br>
                - revenue<br>
                - expense_budget<br>
                - revenue_budget<br>
                - expense_previous<br>
                - revenue_previous
            '''))


class LedgerICUploadForm(AdminActionForm):
    excel_file = forms.FileField(
        required=True,
        label=_("Upload Excel File"),
    help_text = _(
        "Excel must contain the following columns: "
        "'hrm', 'name', optionally: 'expense', 'revenue', 'expense_budget', "
        "'revenue_budget', 'expense_previous', 'revenue_previous', 'notes'."
    ))

    class Meta:
        help_text = format_html(_(
            '''Upload Excel File to Balance.
                Excel must contain the following colums:<br>
                - hrm<br>
                - name<br><br>
                Optionally:<br>
                - expense<br>
                - revenue<br>
                - expense_budget<br>
                - revenue_budget<br>
                - expense_previous<br>
                - revenue_previous
            '''))


