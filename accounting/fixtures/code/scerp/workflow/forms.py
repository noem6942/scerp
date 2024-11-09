from django import forms

class CustomActionForm(forms.Form):
    action = forms.ChoiceField(choices=[(None, '--- Select action ---')])
    confirm = forms.BooleanField()
