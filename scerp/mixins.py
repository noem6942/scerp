# scerp/mixins.py
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

import re
from openpyxl import load_workbook


# helpers, use this for all models in all apps
timezone = timezone.get_current_timezone()


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


def get_admin():
    return User.objects.get(username='admin')


def is_url_friendly(name):
    slugified_name = slugify(name)
    # Check if the slugified name is non-empty and identical to the original, lowercased name
    return slugified_name == name.lower() and bool(slugified_name)


def make_timeaware(naive_datetime):    
    return timezone.make_aware(naive_datetime, timezone)