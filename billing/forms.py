'''
billing/forms.py
'''
import datetime

from django import forms
from django_admin_action_forms import action_with_form, AdminActionForm
from django.utils.translation import gettext_lazy as _

from core.models import UserProfile


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
    key_enabled = forms.BooleanField(
        label=_('Test data'),
        required=False,
        initial=False,
        help_text=_("Generate Test Data"),
    )

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        tenant = route.tenant
        today = datetime.date.today()

        employees = UserProfile.objects.filter(
            person__tenant=tenant).order_by(
                'user__last_name', 'user__first_name')
        self.fields['responsible_user'].queryset = employees
        self.fields['route_date'].initial = datetime.date.today
        self.fields['filename'].initial = f"route_{route.name}_{today}.json"


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


class AnaylseMeasurentActionForm(AdminActionForm):

    # Add an HTML table
    info_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'readonly': 'readonly',
            'style': 'border: none; background: transparent; font-size: 14px;',
        }),
        initial="""
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr><th>Column 1</th><th>Column 2</th></tr>
            <tr><td>Data A</td><td>Data B</td></tr>
        </table>
        """,
    )

    class Meta:
        #list_objects = True
        help_text = "Are you <b>sure</b> you want proceed with this action?"
