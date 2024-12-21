"""
scerp/mixins.py
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from openpyxl import load_workbook


# helpers, use this for all models in all apps
current_timezone = timezone.get_current_timezone()

# Get User.
# This approach will work even if you later decide to switch to a custom
# user model, as get_user_model() always fetches the model defined in
# AUTH_USER_MODEL.
User = get_user_model()


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
    '''handsome for assigning base logging data to have the admin user
    '''
    return User.objects.get(username='admin')


def is_url_friendly(name):
    '''ensure right org_names are chosen
    '''
    slugified_name = slugify(name)
    # Check if the slugified name is non-empty and identical to the original, lowercased name
    return slugified_name == name.lower() and bool(slugified_name)


def make_timeaware(naive_datetime):
    '''used to save datetimes from external data
    '''
    return timezone.make_aware(naive_datetime, current_timezone)
