"""
scerp/mixins.py
"""
import logging
import os
import secrets
import string
import yaml
from pathlib import Path
from openpyxl import load_workbook

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)  # Using the app name for logging

# helpers, use this for all models in all apps
current_timezone = timezone.get_current_timezone()

# Get User.
# This approach will work even if you later decide to switch to a custom
# user model, as get_user_model() always fetches the model defined in
# AUTH_USER_MODEL.
User = get_user_model()


# I/O functions
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


def read_yaml_file(app_name, filename_yaml):
    '''
    Load the YAML file with app_name as parent dir 
    '''
    file_path = os.path.join(
        settings.BASE_DIR, app_name, filename_yaml)
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def get_admin():
    '''
    Handsome for assigning base logging data to have the admin user
    '''
    return User.objects.get(username='admin')


def is_url_friendly(name):
    '''ensure right org_names are chosen
    '''
    slugified_name = slugify(name)
    # Check if the slugified name is non-empty and identical to the original, lowercased name
    return slugified_name == name.lower() and bool(slugified_name)


def generate_random_password(length=settings.PASSWORD_LENGTH):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def make_timeaware(naive_datetime):
    '''used to save datetimes from external data
    '''
    return timezone.make_aware(naive_datetime, current_timezone)


def make_multi_language(name, language=None):
    value = {lang: None for lang, _ in settings.LANGUAGES}
    if not language:
        language = settings.LANGUAGE_CODE_PRIMARY
    value[language] = name
    return value


def multi_language(value_dict):
    '''show language default instead of all values
    '''    
    if value_dict is None or isinstance(value_dict, str):
        return value_dict

    # get languages
    try:
        language = get_language().split('-')[0]
    except:
        language = settings.LANGUAGE_CODE_PRIMARY

    # Check if None
    if value_dict:
        values = dict(value_dict)
    else:
        values = {lang: None for lang, _ in settings.LANGUAGES}
        
    if values and language in values:
        return values[language]
    elif values and settings.LANGUAGE_CODE_PRIMARY in values:
        return values[language]
    return str(value_dict)
    

# signals, load and init yaml data
def init_yaml_data(
        app_name, tenant, created_by, filename_yaml, accounting_setup=None,
        model_filter=[]):
            
    return  # currently no installations when create a new tenant
    
    # Load the YAML file
    file_path = os.path.join(
        settings.BASE_DIR, app_name, filename_yaml)
    with open(file_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)

    # Create data
    try:
        with transaction.atomic():
            for model_name, data_list in data.items():
                if model_filter and model_name not in model_filter:
                    continue
                for data in data_list:
                    # Prepare data
                    print("*data", data)
                    data.update({
                        'tenant': tenant,
                        'created_by': created_by
                    })
                    if accounting_setup:
                        data['setup'] = accounting_setup

                    # Create data
                    model = apps.get_model(
                        app_label=app_name, model_name=model_name)
                    obj = model.objects.create(**data)

                    logger.info(f"{model}: created {obj}.")

        # At this point, all operations are successful and committed
        logger.info("All operations completed successfully!")
    except Exception as e:
        # If any exception occurs, the transaction is rolled back
        logger.error(f"Transaction failed: {e}")

        # Re-raise the exception to propagate it further
        raise  # This will raise the same exception that was caught
