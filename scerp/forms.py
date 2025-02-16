# scerp/forms.py
from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .admin import verbose_name_field, get_help_text, is_required_field


def make_multilanguage_form(local, model, fields):
    '''
    Dynamically create fields for each language
    '''
    for field_name in fields:
        for language in settings.LANGUAGES:
            # variables
            lang_code, lang_name = language
            key = f'{field_name}_{lang_code}'
            verbose_name = verbose_name_field(model, field_name)
            help_text = get_help_text(model, field_name)

            # required
            required = (
                is_required_field(model, field_name) and 
                    lang_code == settings.LANGUAGE_CODE_PRIMARY)

            # label
            label = f"{verbose_name} ({lang_name})"

            # Use Textarea if it's a description field
            widget = (
                forms.Textarea(attrs={'rows': 1, 'cols': 80}) 
                if (field_name.startswith('description')
                    or field_name.startswith('sentence')) 
                else forms.TextInput()
            )
            
            # assign to local form
            local[key] = forms.CharField(
                required=required, label=label, help_text=help_text,
                widget=widget)


class MultilanguageForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        for field in self.MULTI_LANG_FIELDS:
            # Populate the dynamically created fields with data from the 'name' JSON field if it's available
            if self.instance.pk:  # Only do this if the instance already exists (i.e., it's an edit)
                name_data = getattr(self.instance, field) or {}  # Get the name field (JSON data)
                for lang_code, _ in settings.LANGUAGES:
                    field_name = f'{field}_{lang_code}'
                    if lang_code in name_data:
                        self.fields[field_name].initial = name_data[lang_code]  # Set the initial value for the field


    def clean(self):
        cleaned_data = super().clean()

        # Build the JSON structure from the individual fields
        for field in self.MULTI_LANG_FIELDS:
            name_data = {}
            for lang_code, _ in settings.LANGUAGES:
                lang_name = cleaned_data.get(f'{field}_{lang_code}', '')
                if lang_name:
                    name_data[lang_code] = lang_name

            # Explicitly assign the constructed name data to the model instance's name field
            setattr(self.instance, field, name_data)  # This step is necessary for the instance to save this data

            # Also store the data in cleaned_data for use during the form's save process
            cleaned_data[field] = name_data

        return cleaned_data
