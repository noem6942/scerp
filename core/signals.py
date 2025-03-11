# core/signals.py
import copy
import json
import logging
import os
from datetime import date
from PIL import Image

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from asset.models import AssetCategory
from billing.models import Period

from .models import App, Tenant, TenantSetup, TenantLogo, UserProfile, Country
from scerp.mixins import is_url_friendly


PASSWORD_LENGTH = 32
logger = logging.getLogger(__name__)  # Using the app name for logging

from scerp.mixins import init_yaml_data


@receiver(pre_save, sender=Tenant)
def tenant_pre_save(sender, instance, **kwargs):
    """Check before new Tenant is created."""
    __ = sender  # not used
    if not is_url_friendly(instance.code):
        msg = _("Code cannot be displayed in an url.")
        raise ValidationError(msg)
    elif instance.code != instance.code.lower():
        msg = _("Code contains upper letters")
        raise ValidationError(msg)


@receiver(post_save, sender=Tenant)
def tenant_post_save(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Tenant is created."""
    __ = sender  # not used
    if created:
        # Add default apps
        for app in App.objects.order_by('name'):
            if app.is_mandatory:
                instance.apps.add(app)

        # Create TenantSetup
        tenant_setup = TenantSetup.objects.create(
            tenant=instance,
            created_by=instance.created_by)
        logger.info(f"Tenant Setup '{instance.code}' created.")

        # Init Data
        for app_name in ['asset']:
            init_yaml_data(
                app_name,
                tenant=instance,
                created_by=instance.created_by,
                filename_yaml='tenant_init.yaml')

    if kwargs.get('init'):
        ''' run first init scripts '''
        request = kwargs.get('request')
        country_default = kwargs.get('country_default', 'che').upper()

        """
        # Country ------------------------------------------------------
        '''
        Initializes alpha3_dict by reading country data from JSON files
        for each language defined in settings.LANGUAGES.
        '''
        # Initialize the dictionary
        country_default = kwargs.get('country_default', 'che').upper()
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
                settings.BASE_DIR, 'crm', 'fixtures', 'countries', lang,
                'countries.json'
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

        """

        # asset
        wa_obj, _created = AssetCategory.objects.get_or_create(
            tenant=instance,
            code='WA',
            defaults=dict(
                name={'de': 'Wasserzähler', 'en': 'Water Counter'},
                created_by=request.user
            )
        )

        hwa_obj, _created = AssetCategory.objects.get_or_create(
            tenant=instance,
            code='HWA',
            defaults=dict(
                name={'de': 'Warmwasserzähler', 'en': 'Hot Water Counter'},
                created_by=request.user
            )
        )

        # billing
        obj, _created = Period.objects.get_or_create(
            tenant=instance,
            code='WA',
            defaults=dict(
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
                created_by=request.user)
        )
        obj.asset_categories.add(wa_obj)
        obj.asset_categories.add(hwa_obj)


@receiver(pre_save, sender=TenantSetup)
def tenant_setup_pre_save(sender, instance, **kwargs):
    """Check before new TenantSetup is saved"""
    MAX_SIZE_KB = 400  # unit: KB
    MAX_RESOLUTION = (2500, 2500)

    # Logo
    if instance.logo:  # Ensure a logo is uploaded before validation
        # Validate that the uploaded file is of an allowed type.
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if instance.logo.file.content_type not in allowed_types:
            msg = _("Unsupported file type. Only JPG, GIF, and PNG are allowed.")
            raise ValidationError(msg)

        # Validate that the file size does not exceed MAX_SIZE_KB.
        if instance.logo.size > MAX_SIZE_KB * 1024:
            raise ValidationError(_(f"File size exceeds {MAX_SIZE_KB}KB."))

        # Validate that the image resolution does not exceed 2500x2500 pixels.
        try:
            img = Image.open(instance.logo)
            if img.width > MAX_RESOLUTION[0] or img.height > MAX_RESOLUTION[1]:
                raise ValidationError(
                    _("Image resolution exceeds "
                      f"{MAX_RESOLUTION[0]} * {MAX_RESOLUTION[1]} pixels."))
        except Exception:
            raise ValidationError(_("Invalid image file."))


@receiver(post_save, sender=TenantLogo)
def tenant_logo(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new Logo is created."""
    __ = created  # always perform check
    LOGO_TYPE = TenantLogo.Type
    if instance.type == LOGO_TYPE.MAIN:
        # Ensure only only one Main
        TenantLogo.objects.exclude(id=instance.id).filter(
            tenant=instance.tenant, type=LOGO_TYPE.MAIN
        ).update(type=LOGO_TYPE.OTHER)
