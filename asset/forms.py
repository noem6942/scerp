from django import forms
from django.contrib.auth.models import User, Group
from django.forms import SelectMultiple
from django_admin_action_forms import AdminActionForm
from django.utils.translation import gettext as _

from scerp.forms import MultilanguageForm, make_multilanguage_form
from .models import Unit, AssetCategory, Device


# Unit
class UnitAdminForm(MultilanguageForm):
    multi_lang_fields = ['name']

    class Meta:
        model = Unit
        fields = '__all__'

    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


# AssetCategory
class AssetCategoryAdminForm(MultilanguageForm):
    class Meta:
        model = AssetCategory
        fields = '__all__'

    multi_lang_fields = ['name']
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)


# Device
class DeviceAdminForm(MultilanguageForm):
    multi_lang_fields = ['name', 'description']

    # Dynamically create fields for each language
    class Meta:
        model = Device
        fields = '__all__'

    # Dynamically create fields for each language
    make_multilanguage_form(locals(), Meta.model, multi_lang_fields)
