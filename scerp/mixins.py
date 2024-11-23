# scerp.helpers
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.utils.text import slugify

import re
from openpyxl import load_workbook


# helpers, use this for all models in all apps

# excel functions
def read_excel_file(file_path, convert_to_str=True):
    '''read an excel sheet and interprete EVERY cell as string.
        i.e. empty cell -> ''
             111.11 -> '111.11'
             012 -> '012'
    '''
    # Load the workbook
    wb = load_workbook(filename=file_path, data_only=False)  # data_only=False to get formulas too
    ws = wb.active  # Use the active sheet
    
    # Iterate through the rows in the worksheet
    rows = []
    for row in ws.iter_rows(values_only=True):
        # Convert each cell to string while keeping leading zeros
        if convert_to_str:
            row = [
                str(cell).strip() if cell is not None else '' 
                for cell in row]
        rows.append(row)
    
    return rows


def snake_to_camel(snake_str):
    """
    Convert a snake_case string to camelCase.
    """
    components = snake_str.split('_')
    # Capitalize the first letter of each component except the first one
    # and join them together
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str):
    """
    Convert a camelCase string to snake_case.
    """
    # Insert underscores before each uppercase letter, then lowercase
    # everything
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()


def dict_snake_to_camel(data):
    return {snake_to_camel(k): v for k, v in data.items()}


def dict_camel_to_snake(data):
    return {camel_to_snake(k): v for k, v in data.items()}


def display_photo(photo):
    if photo:
        return format_html(
            '''
            <div style="background-color: #f0f0f0; padding: 5px; display: inline-block; border-radius: 5px;">
                <img src="{}" alt="Photo" style="max-width: 60px; max-height: 60px; width: auto; height: auto;" />
            </div>
            ''',
            photo.url
        )
    return "No Photo"


def get_admin():
    return User.objects.get(username='admin')


def is_url_friendly(name):
    slugified_name = slugify(name)
    # Check if the slugified name is non-empty and identical to the original, lowercased name
    return slugified_name == name.lower() and bool(slugified_name)
