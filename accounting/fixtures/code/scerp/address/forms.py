from django import forms
from django.core.exceptions import ValidationError

from .validations import validate_person
from .models import AddressModel, Person


class AddressForm(forms.ModelForm):
    class Meta:
        model = AddressModel
        fields = '__all__'        
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        print("*cleaned_data", cleaned_data)
        validate_person(
            first_name=cleaned_data.get("first_name"),
            last_name=cleaned_data.get("last_name"), 
            company=cleaned_data.get("company"), 
        )
        return cleaned_data
