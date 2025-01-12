# crm/forms.py
from django import forms
from django.conf import settings

from scerp.forms import MultilanguageForm        
from .models import Title


class TitleAdminForm(MultilanguageForm):
    MULTI_LANG_FIELDS = ['name', 'sentence']
    
    # Dynamically create fields for each language
    class Meta:
        model = Title
        fields = '__all__'
    
    # Dynamically create fields for each language
    for field in MULTI_LANG_FIELDS:   
        verbose_name = Meta.model._meta.get_field(field).verbose_name
        for lang_code, lang_name in settings.LANGUAGES:
            locals()[f'{field}_{lang_code}'] = forms.CharField(
                required=False,
                label=f"{verbose_name} ({lang_name})",
                help_text=f"The name of the title in {lang_name}.",
            )
