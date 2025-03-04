'''
billing/forms.py
'''
from django_admin_action_forms import action_with_form, AdminActionForm
from django.utils.translation import gettext_lazy as _


class PeriodExportActionForm(AdminActionForm):
    # No fields needed

    class Meta:
        list_objects = True
        help_text = "Are you sure you want proceed with this action?"
