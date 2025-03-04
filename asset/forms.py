from django import forms
from django.contrib.auth.models import User, Group
from django.forms import SelectMultiple
from django_admin_action_forms import AdminActionForm
from django.utils.translation import gettext as _

from scerp.forms import MultilanguageForm, make_multilanguage_form
from .models import AssetCategory


# AssetCategory
class AssetCategoryAdminForm(MultilanguageForm):        
    class Meta:
        model = AssetCategory
        fields = '__all__'

    multi_lang_fields = ['name']  
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)
