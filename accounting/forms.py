# forms.py
from django import forms
from django.contrib import messages
from django.utils.translation import gettext as _
from django.forms import SelectMultiple
from django_admin_action_forms import action_with_form, AdminActionForm

from core.safeguards import get_tenant_id_from_session
from .models import (
    CHART_TYPE, AccountPositionCanton, ChartOfAccountsCanton,
    AccountChartMunicipality
)
from .locales import ACCOUNT_CHART_MUNICIPALITY, CHART_OF_ACCOUNTS

LABEL_BACK = _("Back")


# AccountChartCanton
class AccountChartCantonForm(AdminActionForm):
    # Show data
    class Meta:
        list_objects = False
        help_text = _(
            "Former chart positions get overwritten. "
            "Are you sure you want proceed with this action?")


# AccountChartMunicipality
class AccountChartMunicipalityForm(AdminActionForm):
    # Show data
    chart = forms.ChoiceField(
        label=ACCOUNT_CHART_MUNICIPALITY.verbose_name, 
        choices=[], required=True,
        help_text=_("Select the appropriate chart for the municipality."))

    class Meta:
        list_objects = False
        help_text = _("Non existing positions will be created, existing "
                      "positions will be updated.")

    def assign_charts(self, request):
        # Get charts
        charts = AccountChartMunicipality.objects.all()

        # Filter tenant
        tenant_id = get_tenant_id_from_session(request, recheck_from_db=True)
        if tenant_id:
            charts = charts.filter(tenant__id=tenant_id)

        self.fields["chart"].choices = [(x.id, str(x)) for x in charts]

    def hide_controls(self):
        self.fields.pop('chart', None)
        self.fields.pop('allow_overwrite', None)
        self.Meta.confirm_button_text = LABEL_BACK

    def check_types(self, request, queryset, type_from):
        # Check mixed types
        types = set([x.chart_of_accounts.type for x in queryset.all()])
        if len(types) > 1:
            messages.error(request, _("mixed types are not allowed."))
            self.hide_controls()
            return

        # Check if mixed types
        for type in types:
            if type in [CHART_TYPE.INCOME, CHART_TYPE.INVEST]:
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


class AccountChartMunicipalityBalanceForm(
        AccountChartMunicipalityForm):
    def __post_init__(self, modeladmin, request, queryset):
        self.assign_charts(request)
        self.check_types(request, queryset, CHART_TYPE.BALANCE)


class AccountChartMunicipalityFunctionForm(
        AccountChartMunicipalityForm):
    def __post_init__(self, modeladmin, request, queryset):
        self.assign_charts(request)
        self.check_types(request, queryset, CHART_TYPE.FUNCTIONAL)


# AccountPositionMunicipality
class AccountPositionMunicipalityForm(AdminActionForm):
    # Show data
    positions = forms.ModelMultipleChoiceField(
        label=CHART_OF_ACCOUNTS.verbose_name,
        queryset = AccountPositionCanton.objects.filter(
            is_category=False).order_by('account_4_plus_2'),
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

    def __post_init__(self, modeladmin, request, queryset, type):
        # Check display type
        for function in queryset:
            if function.display_type != type:
                msg = _("Postion selected must be type '{type}'.").format(
                        type=type.label)
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
            chart_of_accounts__type=type)
        self.fields['positions'].queryset = filter


class AccountPositionMunicipalityAddIncomeForm(
        AccountPositionMunicipalityForm):
    def __post_init__(self, modeladmin, request, queryset):
        super().__post_init__(modeladmin, request, queryset, CHART_TYPE.INCOME)


class AccountPositionMunicipalityAddInvestForm(
        AccountPositionMunicipalityForm):
    def __post_init__(self, modeladmin, request, queryset):
        super().__post_init__(modeladmin, request, queryset, CHART_TYPE.INVEST)
