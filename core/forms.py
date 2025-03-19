from django import forms
from django.contrib.auth.models import User, Group
from django.forms import SelectMultiple
from django_admin_action_forms import AdminActionForm
from django.utils.translation import gettext as _

from scerp.forms import MultilanguageForm, make_multilanguage_form
from .models import Title, PersonCategory, PersonAddress, PersonContact


# Address and person forms
class PersonAddressForm(forms.ModelForm):
    class Meta:
        model = PersonAddress
        fields = ['type', 'address']
        widgets = {
            'address': forms.Select(attrs={'style': 'width: 300px;'}),
            'post_office_box': forms.TextInput(attrs={'size': 10}),  
            'additional_information': forms.TextInput(attrs={'size': 30}),             
        }


class PersonContactForm(forms.ModelForm):
    class Meta:
        model = PersonContact
        fields = ['type', 'address']
        widgets = {
            'address': forms.TextInput(attrs={'size': 80}),  # Adjust width
        }


class TitleAdminForm(MultilanguageForm):        
    class Meta:
        model = Title
        fields = '__all__'

    multi_lang_fields = ['name', 'sentence']  
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


class PersonCategoryAdminForm(MultilanguageForm):        
    class Meta:
        model = PersonCategory
        fields = '__all__'

    multi_lang_fields = ['name']  
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


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
