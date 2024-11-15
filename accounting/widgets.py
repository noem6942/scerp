# accountings/widgets.py
from django import forms
import json
from django.conf import settings

class MultiLanguageTextWidget(forms.Widget):
    template_name = 'admin/multi_language_text_widget.html'

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = {}

        # Generate fields for each language
        rendered = ['<div class="form-row" style="padding-bottom: 10px;">']
        for code, lang_name in settings.LANGUAGES:
            lang_value = value.get(code, "") if value else ""
            rendered.append(
                f'<div style="margin-bottom: 15px;">'
                f'  <label for="{name}_{code}" style="margin-right: 10px; ">'
                f'{lang_name} ({code}):</label>'
                f'  <input type="text" name="{name}_{code}" id="{name}_{code}" '
                f'  value="{lang_value}" size="40">'
                f'</div>'
            )
        print("*rendered", rendered)
        return "\n".join(rendered)

    def value_from_datadict(self, data, files, name):
        return json.dumps({
            code: data.get(f"{name}_{code}", "") 
            for code, _ in settings.LANGUAGES
        })
