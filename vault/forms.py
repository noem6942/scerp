# vault.forms.py
from django_admin_action_forms import AdminActionForm
from django.utils.translation import gettext as _


class OverrideConfirmationForm(AdminActionForm):
    """
    Custom form to confirm override action.
    """
    class Meta:
        list_objects = True
        help_text = _(
            "Are you sure you want to create positions and override existing?")            
