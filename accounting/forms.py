# forms.py
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.forms import SelectMultiple
from django_admin_action_forms import action_with_form, AdminActionForm

from core.safeguards import get_tenant
from .models import (
    ACCOUNT_TYPE_TEMPLATE, AccountPositionTemplate, ChartOfAccountsTemplate,
    ChartOfAccounts, AccountPosition, Currency, Title, CostCenterCategory,
    CostCenter, Rounding, AccountCategory, Account, Allocation, Unit, Tax,
    LedgerBalance
)
from scerp.admin import verbose_name_field
from scerp.forms import MultilanguageForm, make_multilanguage_form

LABEL_BACK = _("Back")

# Name forms
class NameAdminForm(MultilanguageForm):
    MULTI_LANG_FIELDS = ['name']

    # Dynamically create fields for each language
    class Meta:
        model = Rounding
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, MULTI_LANG_FIELDS)


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
    class Meta(NameAdminForm.Meta):
        model = Tax


class LedgerBalanceAdminForm(NameAdminForm):
    class Meta(NameAdminForm.Meta):
        model = LedgerBalance


# Other multilanguage forms
class CurrencyAdminForm(NameAdminForm):
    MULTI_LANG_FIELDS = ['description']

    # Dynamically create fields for each language
    class Meta:
        model = Currency
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, MULTI_LANG_FIELDS)


# Title
class TitleAdminForm(MultilanguageForm):
    MULTI_LANG_FIELDS = ['name', 'sentence']

    # Dynamically create fields for each language
    class Meta:
        model = Title
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, MULTI_LANG_FIELDS)


# AccountSetup
class ConfirmForm(AdminActionForm):
    # Show data
    class Meta:
        list_objects = False
        help_text = _(
            "Are you sure you want proceed with this action?")


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
        for type in types:
            if type in [ACCOUNT_TYPE_TEMPLATE.INCOME,
                        ACCOUNT_TYPE_TEMPLATE.INVEST]:
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
        self.check_types(request, queryset, ACCOUNT_TYPE_TEMPLATE.BALANCE)


class ChartOfAccountsFunctionForm(
        ChartOfAccountsForm):
    def __post_init__(self, modeladmin, request, queryset):
        self.assign_charts(request)
        self.check_types(request, queryset, ACCOUNT_TYPE_TEMPLATE.FUNCTIONAL)


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
