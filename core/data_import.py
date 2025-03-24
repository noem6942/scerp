'''
core/data_import.py

import central data
'''
import csv
import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings

from scerp.mixins import get_admin
from .models import (
    Country, Municipality, Street, Building, MunicipalityAddress)


# Helper function to parse the date string into a datetime object
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)  # Using the app name for logging

def parse_date(date_string):
    try:
        return datetime.strptime(date_string, "%d.%m.%Y")  # Parse date in the format "15.11.2024"
    except ValueError:
        return None  # Return None if the date cannot be parsed


class ImportCountry:
    '''
    Initializes alpha3_dict by reading country data from JSON files
    for each language defined in settings.LANGUAGES.
    '''
    def __init__(self, directory_name='countries'):
        self.directory_name = directory_name

    def load(self, country_default='CHE'):
        # Initialize the dictionary
        alpha3_dict = {}
        languages = [lang for lang, _language in settings.LANGUAGES]
        lang_dict = {
            'name': {lang: None for lang in languages},
            'is_default': False,
            'created_by': request.user
        }

        # Parse
        for lang in languages:
            # Construct the path to the JSON file for the current language
            path_to_file = os.path.join(
                settings.BASE_DIR, 'crm', 'fixtures', self.directory_name,
                lang, 'countries.json'
            )
            try:
                # Open and read the JSON file
                with open(path_to_file, 'r', encoding='utf-8') as file:
                    countries = json.load(file)  # Load JSON data

                    # Build/update the dictionary using 'alpha3' as the key
                    for country in countries:
                        alpha3 = country['alpha3'].upper()

                        if alpha3 not in alpha3_dict:
                            # Create an independent copy
                            alpha3_dict[alpha3] = copy.deepcopy(lang_dict)

                            if alpha3.upper() == country_default:
                                alpha3_dict[alpha3]['is_default'] = True

                        # Assign name correctly
                        alpha3_dict[alpha3]['name'][lang] = country['name']

            except FileNotFoundError:
                print(f"File not found for language '{lang}': {path_to_file}")
            except json.JSONDecodeError:
                print(f'''Error decoding JSON for language '{lang}'.
                    Please check the file format.''')
            except Exception as e:
                print(f"An unexpected error occurred for language '{lang}': {e}")

        # Save Db
        # Begin a database transaction for better performance
        with transaction.atomic():
            for alpha3, country in alpha3_dict.items():
                # Use update_or_create to store data
                _obj, _created = Country.objects.update_or_create(
                    alpha3=alpha3,  # Lookup field
                    defaults=country
                )

        # Info
        logger.info(
            f"Countries: '{ len(alpha3_dict) }' records created successfully."
        )


class ImportBuilding:
    '''
    Initializes alpha3_dict by reading country data from JSON files
    for each language defined in settings.LANGUAGES.
    '''
    def __init__(self):
        pass

    def load(self, file_name_csv):
        # Initialize the dictionary
        file_path = Path(
            settings.BASE_DIR) / 'core' / 'fixtures' / file_name_csv
        admin = get_admin()

        # Open the CSV file
        with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=';')  # Use semicolon as delimiter

            logger.info("Starting")

            # Iterate over each row in the CSV
            for count, row in enumerate(csv_reader):
                # Prepare data dictionary with relevant fields
                zip, label = row.pop('ZIP_LABEL').split(' ', 1)

                # Check scope
                if int(zip) not in [4616, 4617]:
                    continue

                address_data = {
                    'zip': zip,
                    'label': label,
                    'com_fosnr': row['COM_FOSNR'],  # Include COM_FOSNR here
                    'com_name': row['COM_NAME'],
                    'com_canton': row['COM_CANTON'],
                    'stn_label': row['STN_LABEL'],
                    'adr_number': row['ADR_NUMBER'],
                    'adr_status': row['ADR_STATUS'],
                    'adr_official': (
                        row['ADR_OFFICIAL'].strip().lower() == 'true'),
                    'adr_modified': parse_date(row['ADR_MODIFIED'].strip()),
                    'adr_easting': row['ADR_EASTING'],
                    'adr_northing': row['ADR_NORTHING'],
                    'bdg_egid': row['BDG_EGID'],
                    'bdg_category': row['BDG_CATEGORY'],
                    'bdg_name': (
                        row['BDG_NAME'].strip()
                        if row['BDG_NAME'].strip() else None),
                    'adr_egaid': row['ADR_EGAID'],
                    'str_esid': row['STR_ESID'],
                }

                # Municipality
                municipality, _created = Municipality.objects.update_or_create(
                    com_fosnr=address_data.pop('com_fosnr'),
                    defaults={
                        'com_name': address_data.pop('com_name'),
                        'com_canton': address_data.pop('com_canton'),
                        'zip': address_data.pop('zip'),
                        'city': address_data.pop('label'),
                        'created_by': admin
                    }
                )

                # Street
                street, _created = Street.objects.update_or_create(
                    str_esid=address_data.pop('str_esid'),
                    defaults={
                        'stn_label': address_data.pop('stn_label'),
                        'municipality': municipality,
                        'created_by': admin
                    }
                )

                # Building
                building, _created = (
                    Building.objects.update_or_create(
                        bdg_egid=address_data.pop('bdg_egid'),
                        defaults={
                            'bdg_category': address_data.pop('bdg_category'),
                            'bdg_name': address_data.pop('bdg_name'),
                            'street': street,
                        'created_by': admin
                        }
                    )
                )

                # Address
                address_data.update({
                    'building': building,
                    'created_by': admin
                })
                address, _created = (
                    AddressNew.objects.update_or_create(
                        adr_egaid=address_data.pop('adr_egaid'),
                        defaults=address_data
                    )
                )

        return count + 1
