# scerp/forms.py
from django import forms
from django.conf import settings


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
