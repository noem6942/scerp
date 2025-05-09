''' core/process.py
Init and Update Jobs
'''
import copy
import csv
import json
import logging  # initialized at process_core --> no need to re-init
import os
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, Permission
from django.db import transaction

from scerp.mixins import get_admin, read_yaml_file
from .models import App, Country, TenantSetup, Address, AddressMunicipal
from .models import Person, PersonAddress


# Get logging
logger = logging.getLogger('core')

BUILDING_CSV = 'amtliches-gebaeudeadressverzeichnis_ch_2056.csv'
SETUP_SYSTEM_YAML = 'init_system.yaml'

COUNTRY_DEFAULT = 'CHE'
COUNTRY_DIR = 'countries'
COUNTRY_FILENAME = 'countries.json'


# helpers
def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%d.%m.%Y')  # Parse date in the format "15.11.2024"
    except ValueError:
        return None  # Return None if the date cannot be parsed


# core
def update_or_create_apps(update=True):
    ''' Update or create apps
    '''
    # Open yaml
    init_data = read_yaml_file('core', SETUP_SYSTEM_YAML)

    # Init
    created, updated, deleted = 0, 0, 0
    admin = get_admin()
    app_names = []
    if update:
        db_op = App.objects.update_or_create
    else:
        db_op = App.objects.get_or_create

    # Create
    for app_config in apps.get_app_configs():
        name = app_config.label
        app_names.append(name)
        if name not in init_data['apps_ignore']:
            # Save
            is_mandatory = name in init_data['apps_mandatory']
            _obj, _created = db_op(
                name=name, defaults={
                    'is_mandatory': is_mandatory,
                    'verbose_name': app_config.verbose_name,
                    'created_by': admin
                })

            # Maintain
            if _created:
                created += 1
            else:
                updated += 1

            logger.info(
                f"App Label: {app_config.label}, "
                f"Verbose Name: {app_config.verbose_name}")

    # Delete
    if update:
        deleted, _records = App.objects.exclude(name__in=app_names).delete()

    return created, updated, deleted


def update_or_create_countries(update=True):
    ''' Update or create apps
    '''
    # Init
    admin = get_admin()
    alpha3_dict = {}
    languages = [lang for lang, _language in settings.LANGUAGES]
    lang_dict = {
        'name': {lang: None for lang in languages},
        'is_default': False,
        'created_by': admin
    }
    created, updated, deleted = 0, 0, 0

    # Parse
    for lang in languages:
        # Construct the path to the JSON file for the current language
        path_to_file = os.path.join(
            settings.BASE_DIR, 'core', 'fixtures', COUNTRY_DIR, lang,
            COUNTRY_FILENAME
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

                        if alpha3.upper() == COUNTRY_DEFAULT:
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
    if update:
        db_op = Country.objects.update_or_create
    else:
        db_op = Country.objects.get_or_create

    with transaction.atomic():
        for alpha3, country in alpha3_dict.items():
            # Use update_or_create to store data
            _obj, _created = db_op(
                alpha3=alpha3,  # Lookup field
                defaults=country
            )

            # Maintain
            if _created:
                created += 1
            else:
                updated += 1

    # Delete
    if update:
        deleted, _records = Country.objects.exclude(
            alpha3__in=alpha3_dict.keys()).delete()

    return created, updated, deleted


def update_or_create_groups(update=True):
    ''' Create Groups, no permissions are granted yet
    '''
    # Open yaml
    init_data = read_yaml_file('core', SETUP_SYSTEM_YAML)
    if update:
        db_op = Group.objects.update_or_create
    else:
        db_op = Group.objects.get_or_create

    # Init
    group_data = init_data['groups']
    created, updated, deleted = 0, 0, 0
    group_names = []

    # Create
    for category, names in group_data.items():
        for name in names:
            # Save
            _obj, _created = Group.objects.get_or_create(name=name)

            # Maintain
            group_names.append(name)
            if _created:
                created += 1
            logger.info(f"{category}: {name}, ")

    # Delete
    if update:
        deleted, _records = Group.objects.exclude(name__in=group_names).delete()

    return created, updated, deleted


def update_or_create_base_buildings(tenant_id=None, update=True):
    '''
    Load actual Buildings, currently per tenant, not grouped
    see https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/amtliches-gebaeudeadressverzeichnis_ch/amtliches-gebaeudeadressverzeichnis_ch_2056.csv.zip

    deleted not implemented yet
    '''
    # Init
    file_path = Path(settings.BASE_DIR / 'core' / 'fixtures' / BUILDING_CSV)
    admin = get_admin()
    country = Country.objects.get(alpha3=COUNTRY_DEFAULT)
    created, updated, deleted = 0, 0, 0

    # db_op
    if update:
        db_op = AddressMunicipal.objects.update_or_create
        db_op_a = Address.objects.update_or_create
    else:
        db_op = AddressMunicipal.objects.get_or_create
        db_op_a = Address.objects.get_or_create

    # Get tenants
    queryset = TenantSetup.objects.filter(is_inactive=False)
    if tenant_id:
        queryset = queryset.filter(tenant__id=tenant_id)

    for tenant_setup in queryset.all():
        # Open the CSV file
        with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=';')
            logger.info(f"Starting {tenant_setup.tenant}")

            # Iterate over each row in the CSV
            for row in csv_reader:
                # Prepare data dictionary with relevant fields
                zip, city = row.pop('ZIP_LABEL').split(' ', 1)

                # Check scope
                if (int(zip) not in tenant_setup.zips and
                        int(row['BDG_EGID']) not in tenant_setup.bdg_egids):
                    continue

                address_data = {
                    # import
                    'zip': zip,
                    'city': city,
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

                    # custom
                    'created_by': admin
                }

                # AddressMunicipal
                address, _created = db_op(
                    tenant=tenant_setup.tenant,
                    adr_egaid=address_data.pop('adr_egaid'),
                    defaults=address_data
                )

                # Address, we save it as well for further use
                address_a, _created_a = db_op_a(
                    tenant=tenant_setup.tenant,
                    address=f"{row['STN_LABEL']} {row['ADR_NUMBER']}",
                    zip=zip, city=city, country=country,
                    defaults={'created_by': admin}
                )

                # Maintain
                if _created:
                    created += 1
                else:
                    updated += 1


def clear_company_addresses():
    '''
    Billing set too many additional_information
    '''    
    queryset = PersonAddress.objects.exclude(
        additional_information=None
    )
    count = 0
    
    for item in queryset.all():
        if item.additional_information == item.person.company:
            item.additional_information = None
            item.sync_accounting = True
            item.save()
            count += 1
            logger.info(f"{item} updated.")                

    return count


# temp
def sync_person_again(tenant_id):
    ''' sync person, necessary as for some reason addresses were missing '''
    count = 0
    for person in Person.objects.filter(tenant__id=tenant_id).all():
        person.sync_to_accounting = True
        person.save()
        logging.info(f"saving {person}")
        count += 1

    return count


