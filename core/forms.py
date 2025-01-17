from django import forms
from django.contrib.auth.models import User, Group
from django.forms import SelectMultiple
from django_admin_action_forms import AdminActionForm
from django.utils.translation import gettext as _


class CreateUserForm(AdminActionForm):
    username = forms.CharField(label=_('Username'))
    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))
    email = forms.EmailField(label=_('Email'))
    groups = forms.ModelMultipleChoiceField(
        label=_('Groups'),
        queryset = Group.objects.all().order_by('name'),
        required=True,
        widget=SelectMultiple(attrs={'size': '20'}),
        help_text=_("Select the appropriate groups for user.")
    )

    class Meta:
        help_text = _("Add a user")
