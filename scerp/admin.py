'''
scerp/admin.py

Admin configuration for the scerp app.

Helpers for admin.py

'''
import json

from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms import Textarea
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.formats import date_format
from django.utils.translation import get_language, gettext_lazy as _

from .admin_base import FIELDSET, TenantFilteringAdmin, RelatedModelInline
from .mixins import primary_language


# format
def format_big_number(value, thousand_separator=None, round_digits=None):
    '''
    use settings.THOUSAND_SEPARATOR and 2 commas for big numbers
    value: float
    '''
    if value is None:
        return None

    # Round
    if round_digits:
        value = round(value, round_digits)

    # Format number
    if thousand_separator is None:
        thousand_separator = settings.THOUSAND_SEPARATOR
    return f'{value:,.2f}'.replace(',', thousand_separator)


def format_percent(value, precision):
    '''
    use settings.THOUSAND_SEPARATOR and 2 commas for big numbers
    value: float
    '''
    if value is None:
        return None

    # Format number
    return f'{value:,.{precision}f}%'


def get_help_text(model, field_name):
    '''
    Get help text from model
    '''
    # pylint: disable=W0212
    return model._meta.get_field(field_name).help_text


def make_language_fields(field_name):
    # Currently show only LANGUAGE_CODE_PRIMARY
    languages = [
        (lang_code, lang) for lang_code, lang in settings.LANGUAGES
        if lang_code == settings.LANGUAGE_CODE_PRIMARY
    ]

    # Check if only show preferred languagen
    return [
        f'{field_name}_{lang_code}'
        for lang_code, _lang in languages
    ]


def is_required_field(model, field_name):
    '''
    Check if required field
    '''
    # pylint: disable=W0212
    field = model._meta.get_field(field_name)
    return not field.blank and not field.null


def verbose_name_field(model, field_name):
    '''
    Get verbose_name from model
    '''
    # pylint: disable=W0212
    return model._meta.get_field(field_name).verbose_name


class Display:

    def boolean(value):
        return '✔' if value else '✘'

    def datetime(value, default='-'):
        '''
        Display date time nice
        '''
        if value is None:
            return default
        return date_format(value, format='DATETIME_FORMAT')

    def big_number(value, round_digits=None, thousand_separator=None):
        '''
        use settings.THOUSAND_SEPARATOR and 2 commas for big numberss
        '''
        if value is None:
            return None

        # Format number
        try:
            number_str = format_big_number(
                value,
                round_digits=round_digits,
                thousand_separator=thousand_separator)
        except:
            number_str = value
        html = "<span style='text-align: right; display: block;'>{}</span>"
        return format_html(html, number_str)

    def percentage(value, precision=1):
        '''
        show percenate with{ precision} commas
        '''
        if value is None:
            return None

        # Format number
        number_str = format_percent(value, precision)
        html = "<span style='text-align: right; display: block;'>{}</span>"
        return format_html(html, number_str)

    def hierarchy(level, name):
        '''Function to print out hierarchy names nice;
            add spaces before the string if is_category == False
        '''
        if level == 1:
            return format_html(f'<b>{name.upper()}</b>')
        if level == 2:
            return format_html(f'<b>{name}</b>')
        return format_html(f'<i>{name}</i>')

    def json(value, sort=False):
        '''
        Print string for json
        '''
        if not value:
            return ''

        try:
            # Format JSON data with indentation and render it as preformatted text
            formatted_json = json.dumps(value, indent=4, ensure_ascii=False)
            return format_html(
                "<pre style='font-family: monospace;'>{}</pre>", 
                formatted_json)
        except ValueError as e:
            return f'Value Error displaying data: {e}'
        except (KeyError, TypeError) as e:  # Catch specific exceptions
            return f'Key or Type Error displaying data: {e}'
        except Exception as e:  # pylint: disable=W0718
            # Last resort: Catch any other exceptions
            return f'Unexpected error displaying data: {e}'

    def link(url, name):
        '''
        Generates a clickable link for the Django admin interface.

        Args:
            url (str): The URL to link to.
            name (str): The text to display for the link.

        Returns:
            str: HTML string with a clickable link.
        '''
        return format_html("<a href='{}' target='_blank'>{}</a>", url, name)

    def list(items):
        output_list = [f'<li>{item}</li>' for item in items]
        return format_html(''.join(output_list))

    def photo(url_field):
        '''
        Display photo
        '''
        if url_field:
            return mark_safe(
                f"<img src='{url_field.url}' width='60' height='60' "
                f"style='object-fit: cover;' />")
        return ''

    def verbose_name(def_cls, field):
        '''
        Display verbose name from field
        '''
        f_cls = getattr(def_cls, 'Field')
        return getattr(f_cls, field)['verbose_name']

    def name_w_levels(obj):
        '''obj needs to have name, is_category, level
        '''
        name = format_name(obj)
        if obj.is_category:
            level = obj.level
            if level < 3:
                return format_hierarchy(obj.level, name)
        return name


# Decorators
class BaseAdminNew:
    '''
    basic class 
    all security filtering is done in TenantFilteringAdmin
    '''

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        try:
            return primary_language(obj.name)
        except:
            return ''

    @admin.display(description=_('Number'))
    def display_number(self, obj):
        return Display.big_number(obj.number)

    @admin.display(description='')
    def display_is_inactive(self, obj):
        return '🔒' if obj.is_inactive else ''

    @admin.display(description=_('Photo'))
    def display_photo(self, obj):
        return Display.photo(obj.photo)

    @admin.display(description='')
    def display_attachment_icon(self, obj):
        """Displays a paperclip 📎 or folder 📂 icon if attachments exist."""
        if obj.attachments.exists():  # ✅ Efficient query
            return "📂"  # You can also use "📎" or "🗂️"
        return ""  # No icon if no attachments'

    @admin.display(description='')
    def display_notes_hint(self, obj):
        """Displays a hint (tooltip) with the note text if available."""
        if obj.notes:
            return format_html(
                '<span style="cursor: pointer; border-bottom: 1px dotted #555;" '
                'title="{}">📝</span>', obj.notes
            )  # ✅ Cursor + underline effect
        return ""

    @admin.display(description=_('last update'))
    def display_last_update(self, obj):
        return obj.modified_at


    @admin.display(description=_('Name Plural'))
    def display_name_plural(self, obj):
        try:
            return primary_language(obj.name_plural)
        except:
            return ''

    @admin.display(description=_('Parent'))
    def display_parent(self, obj):
        return self.display_name(obj.parent)

    @admin.display(description=_('Wording in document'))
    def display_document_name(self, obj):
        return primary_language(obj.document_name)

    @admin.display(description=_("Percentage"))
    def display_percentage(self, obj):
        return Display.percentage(obj.percentage, 1)

    @admin.display(description=_("Percentage Flat"))
    def display_percentage_flat(self, obj):
        return Display.percentage(obj.percentage_flat, 1)

    @admin.display(description=_('Balance'))
    def display_link_to_company(self, person):
        if not person.company:
            return "-"  # Fallback if company is missing
        url = f"../person/{person.id}/"
        return format_html('<a href="{}">{}</a>', url, person.company)
  
    @admin.display(description=_('Parent'))
    def display_category_type(self, obj):
        return obj.category.get_type_display()

    @admin.display(description=_('description'))
    def display_description(self, obj):
        return primary_language(obj.description)



class BaseAdmin(TenantFilteringAdmin):
    '''
    basic class 
    all security filtering is done in TenantFilteringAdmin
    '''

    @admin.display(description=_('Name'))
    def display_name(self, obj):
        try:
            return primary_language(obj.name)
        except:
            return ''

    @admin.display(description=_('Photo'))
    def display_photo(self, obj):
        return Display.photo(obj.photo)

    @admin.display(description='')
    def attachment_icon(self, obj):
        """Displays a paperclip 📎 or folder 📂 icon if attachments exist."""
        if obj.attachments.exists():  # ✅ Efficient query
            return "📂"  # You can also use "📎" or "🗂️"
        return ""  # No icon if no attachments'

    @admin.display(description='')
    def notes_hint(self, obj):
        """Displays a hint (tooltip) with the note text if available."""
        if obj.notes:
            return format_html(
                '<span style="cursor: pointer; border-bottom: 1px dotted #555;" '
                'title="{}">📝</span>', obj.notes
            )  # ✅ Cursor + underline effect
        return ""


class BaseTabularInline(RelatedModelInline):
    pass


class ReadOnlyAdmin(admin.ModelAdmin):
    """A mixin to make an admin model read-only."""
    def has_add_permission(self, request):
        return False  # Disable adding

    def has_change_permission(self, request, obj=None):
        return False  # Disable editing

    def has_delete_permission(self, request, obj=None):
        return False  # Disable deleting

    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only."""
        return [field.name for field in self.model._meta.fields]
