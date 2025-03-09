# scerp/forms.py
from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_admin_action_forms import AdminActionForm

from scerp.admin import PAGE_ORIENTATION, verbose_name_plural
from .admin import verbose_name_field, get_help_text, is_required_field


# currently show only LANGUAGE_CODE_PRIMARY
languages = [
    (lang_code, lang) for lang_code, lang in settings.LANGUAGES
    if lang_code == settings.LANGUAGE_CODE_PRIMARY
]


def make_multilanguage_form(local, model, fields):
    '''
    Dynamically create fields for each language
    '''
    for field_name in fields:
        for language in languages:
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
            widget = (
                forms.Textarea(attrs={'rows': 1, 'cols': 80})
                if (field_name.startswith('description')
                    or field_name.startswith('sentence'))
                else forms.TextInput(attrs={'size': 80})
            )

            # assign to local form
            local[key] = forms.CharField(
                required=required, label=label, help_text=help_text,
                widget=widget)


class MultilanguageForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        for field in self.multi_lang_fields:
            # Populate the dynamically created fields with data from the 'name' JSON field if it's available
            if self.instance.pk:  # Only do this if the instance already exists (i.e., it's an edit)
                name_data = getattr(self.instance, field) or {}  # Get the name field (JSON data)
                for lang_code, _ in languages:
                    field_name = f'{field}_{lang_code}'
                    if lang_code in name_data:
                        self.fields[field_name].initial = name_data[lang_code]  # Set the initial value for the field


    def clean(self):
        cleaned_data = super().clean()

        # Build the JSON structure from the individual fields
        for field in self.multi_lang_fields:
            name_data = {}
            for lang_code, _ in languages:
                lang_name = cleaned_data.get(f'{field}_{lang_code}', '')
                if lang_name:
                    name_data[lang_code] = lang_name

            # Explicitly assign the constructed name data to the model instance's name field
            setattr(self.instance, field, name_data)  # This step is necessary for the instance to save this data

            # Also store the data in cleaned_data for use during the form's save process
            cleaned_data[field] = name_data

        return cleaned_data


# Export
class ExportExcelActionForm(AdminActionForm):
    # Names
    file_name = forms.CharField(
        label=_('Filename'), max_length=100)
    worksheet_name = forms.CharField(
        label=_('Worksheet Name'), max_length=100)
    orientation = forms.ChoiceField(
        choices=PAGE_ORIENTATION, label=_("Page Orientation"))

    # ColWidths
    col_widths = forms.CharField(
        label=_('Column Widths in mm'), max_length=100, required=False,
        help_text=_("Leave empty for 'auto'"))

    # Header
    header_left = forms.CharField(
        label=_('Header left'), max_length=100, required=False)
    header_center = forms.CharField(
        label=_('Header center'), max_length=100, required=False)
    header_right = forms.CharField(
        label=_('Header right'), max_length=100, required=False)

    # Footer
    footer_left = forms.CharField(
        label=_('Footer left'), max_length=100, required=False)
    footer_center = forms.CharField(
        label=_('Footer center'), max_length=100, required=False)
    footer_right = forms.CharField(
        label=_('Footer right'), max_length=100, required=False)


    class Meta:
        help_text = _("{count} records selected.")

    def __post_init__(self, modeladmin, request, queryset):
        date = timezone.now().date()
        name_plural = verbose_name_plural(modeladmin.model)
        tenant = queryset.first().tenant

        self.Meta.help_text = self.Meta.help_text.format(
            count=queryset.count())

        self.fields['file_name'].initial = f'{name_plural}_{date}.xlsx'
        self.fields['worksheet_name'].initial = name_plural
        self.fields['col_widths'].initial = getattr(
            modeladmin, 'col_widths', '')
            
        if getattr(modeladmin, 'orientation', None):
            self.fields['orientation'].initial = modeladmin.orientation

        self.fields['header_left'].initial = tenant.name
        self.fields['header_center'].initial = verbose_name_plural(queryset.model)
        self.fields['header_right'].initial =  request.user.username

        self.fields['footer_left'].initial = date
        self.fields['footer_center'].initial = ''
        self.fields['footer_right'].initial = '&P / &N'


class ExportJSONActionForm(AdminActionForm):
    # Names
    file_name = forms.CharField(
        label=_('Filename'), max_length=100)

    class Meta:
        help_text = _("{count} records selected.")

    def __post_init__(self, modeladmin, request, queryset):
        date = timezone.now().date()
        name_plural = verbose_name_plural(modeladmin.model)        

        self.Meta.help_text = self.Meta.help_text.format(
            count=queryset.count())

        self.fields['file_name'].initial = f'{name_plural}_{date}.json'
