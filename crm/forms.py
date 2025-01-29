# crm/forms.py
from django import forms
from django.conf import settings

from scerp.forms import MultilanguageForm, make_multilanguage_form
from .models import Title


class TitleAdminForm(MultilanguageForm):
    MULTI_LANG_FIELDS = ['name', 'sentence']
    
    # Dynamically create fields for each language
    class Meta:
        model = Title
        fields = '__all__'
    
    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, MULTI_LANG_FIELDS)
