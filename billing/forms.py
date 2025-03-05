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
        