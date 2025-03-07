'''
billing/forms.py
'''
from django import forms
from django_admin_action_forms import action_with_form, AdminActionForm
from django.utils.translation import gettext_lazy as _

from core.models import UserProfile

class PeriodExportActionForm(AdminActionForm):
    employee = forms.ModelChoiceField(
        label=_('Employee responsible'),
        required=True, queryset=UserProfile.objects.none())
    key_enabled = forms.BooleanField(
        label=_('Test data'),
        required=False,
        initial=False,
        help_text=_("Generate Test Data"),
    )

    class Meta:
        list_objects = True
        help_text = "Are you sure you want proceed with this action?"

    def __post_init__(self, modeladmin, request, queryset):
        tenant = queryset.first().tenant
        employees = UserProfile.objects.filter(
            person__tenant=tenant).order_by('user__last_name', 'user__first_name')
        self.fields['employee'].queryset = employees
        
        
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
        