'''
billing/forms.py
'''
import datetime

from django import forms
from django.contrib import messages
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_admin_action_forms import action_with_form, AdminActionForm

from accounting.models import OrderCategoryOutgoing
from core.models import UserProfile
from .models import Period, Measurement, Subscription

LABEL_BACK = _("Back")


class RouteCopyActionForm(AdminActionForm):
    period = forms.ModelChoiceField(
        label=_('Period'),
        required=True,
        queryset=Period.objects.none()
    )
    name = forms.CharField(
        label=_('Route Name'),
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter name')})
    )

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        tenant = route.tenant
        self.fields['period'].queryset = Period.objects.filter(
            tenant=tenant).order_by('-end')


class RouteMeterExportJSONActionForm(AdminActionForm):
    route_date = forms.DateField(
        label=_('Route Date'),
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    responsible_user = forms.ModelChoiceField(
        label=_('Employee responsible'),
        required=True,
        queryset=UserProfile.objects.none()
    )
    filename = forms.CharField(
        label=_('Filename'),
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )
    energy_type = forms.CharField(
        label=_('Energy Type'),
        required=True,
        max_length=10,
        widget=forms.TextInput(attrs={'placeholder': _('Enter symbol')})
    )
    key_enabled = forms.BooleanField(
        label=_('Test data'),
        required=False,
        initial=False,
        help_text=_("Generate Test Data"),
    )

    class Meta:
        list_objects = True

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        tenant = route.tenant
        today = datetime.date.today()

        if not route.period_previous:
            messages.warning(request, _('Warning: no previous period given'))
            self.Meta.confirm_button_text = LABEL_BACK
            self.fields['responsible_user'].required = False

        employees = UserProfile.objects.filter(
            person__tenant=tenant).order_by(
                'user__last_name', 'user__first_name')
        self.fields['responsible_user'].queryset = employees
        self.fields['route_date'].initial = datetime.date.today
        self.fields['energy_type'].initial = 'W'
        self.fields['filename'].initial = f"route_{route.name}_{today}.json"


class RouteMeterImportJSONActionForm(AdminActionForm):
    json_file = forms.FileField(
        label=_('File'),
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'file-upload'}),
        help_text=_("JSON File with the collected data"),
    )

    class Meta:
        list_objects = True


class RouteMeterExportExcelActionForm(AdminActionForm):
    filename = forms.CharField(
        label=_('Filename'),
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )
    key_enabled = forms.BooleanField(
        label=_('Test data'),
        required=False,
        initial=False,
        help_text=_("Generate Test Data"),
    )

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        today = datetime.date.today()
        self.fields['filename'].initial = f"route_{route.name}_{today}.xlsx"


class RouteMeterInvoicingActionForm(AdminActionForm):
    id = forms.CharField(
        label=_('ID'),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('ID')}),
        help_text=_("Leave empty if all records"),
    )

    filename = forms.CharField(
        label=_('Filename'),
        required=False,
        initial='invoices_{route_id}',
        widget=forms.TextInput(attrs={
            'readonly': True,
            'placeholder': _('invoices_{route_id}')
        }),
        help_text=_("Default format: invoices_{route_id}")
    )


class AnalyseMeasurentExcelActionForm(AdminActionForm):
    filename = forms.CharField(
        label=_('Filename'),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )
    ws_title = forms.CharField(
        label=_('Worksheet Name'),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )

    def __post_init__(self, modeladmin, request, queryset):
        measurement = queryset.first()
        today = datetime.date.today()

        self.fields['filename'].initial = (
            f"analysis_{measurement.route.name}_{today}.xlsx")
        self.fields['ws_title'].initial = (f"{measurement.route.name}")


class RouteBillingForm(AdminActionForm):
    tag = forms.ChoiceField(
        label=_('Tag'),
        required=False,
        choices=[],
        help_text=(
            _("Invoice all subscriptions with this tag. Ignore ") +
            _('Measurements') + '.')

    )
    subscriptions = forms.ModelMultipleChoiceField(
        label=_('Subscriber'),
        required=False,
        queryset=Subscription.objects.none(),
        help_text=_("Leave empty for generating all invoices.")
    )
    status = forms.ChoiceField(
        label=_('Invoice Status'),
        required=True,
        choices=OrderCategoryOutgoing.STATUS.choices
    )
    date = forms.DateField(
        label=_('Invoice Date'),
        required=True,
        initial=now,  # or initial=now().date() if you only want the date
        widget=forms.DateInput(format='%d.%m.%Y'),  # optional formatting
        input_formats=['%d.%m.%Y'],  # optional parsing format
    )
    check_measurement = forms.BooleanField(
        label=_('Check measurement'),
        required=False, initial=True,
        help_text=_(
            "Check that measurement exists for subscriber.")
    )
    is_enabled_sync = forms.BooleanField(
        label=_('Sync with cashCtrl'),
        required=False,
        help_text=_(
            "Enable for draft invoices. Disable for hundreds of invoices")
    )

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()

        # Get Subscribers
        subscriptions = Subscription.objects.filter(
            tenant=route.tenant,
            is_inactive=False
        )
        self.fields['subscriptions'].queryset = subscriptions.order_by(
            'address__zip', 'address__stn_label', 'address__adr_number',
            'description'
        )
        
        # tags
        tags = list(set([x.tag for x in subscriptions.all()]))
        self.fields['tag'].choices = [(tag, tag if tag else '-') for tag in tags]
