'''
billing/gesoft_import.py
'''
import json
import logging
from datetime import date, datetime
from openpyxl import load_workbook
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from accounting.models import APISetup, ArticleCategory, Article
from asset.models import DEVICE_STATUS, AssetCategory, Device, EventLog
from billing.models import Period, Route, Measurement, Subscription
from core.models import (
     AddressCategory, Address, PersonCategory, Person, PersonAddress,
     Building
)
from scerp.mixins import parse_gesoft_to_datetime
from .models import ARTICLE

logger = logging.getLogger(__name__)

# Address default
CITY = 'Gunzgen'
ZIP = 4617


# Needed for area assignment
ALLMEND = [
    'Aerni Anton',
    'Plüss-Holliger Dominik und Marlies',
    'Schickling-Gasser Bernhard + Monika',
    'Heeb Edda',
    'Uhlmann Rudolf',
    'Grütter-Flühmann Liliane',
    'Romano Adriano',
    'Schönenberger Urs',
    'Meier-Holzherr Leonore',
    'Düblin Sascha',
    'Widmer-Lanz Peter + Ursula',
    'Rainer Walter',
    'NSNW AG',
    'Marché Restaurants Schweiz AG',
    'Kieswerk Gunzgen AG',
    'Wagner-Stulz Thomas + Sandra',
    'Baggenstos Franziska Ursula',
    'Lanz Kevin',
    'Krähenbühl Sascha',
    'Valora Schweiz SA',
    'Caderas Jacqueline'
]


class Import:

    def __init__(self, setup_id):
        '''
            datetime_default,e g. '2024-03-31'
        '''
        # From setup
        self.setup = APISetup.objects.get(id=setup_id)
        self.tenant = self.setup.tenant
        self.created_by = self.setup.created_by
        self.person_category = PersonCategory.objects.get(
            tenant=self.tenant, code='subscriber')

    @staticmethod
    def clean_address(address):
        if address:
            address = address.replace('Gunzgen', '')
            address = address.replace('strase', 'strasse')
            address = address.replace('str.', 'strasse')
            address = address.strip()
            if address[-1] == ',':
                address = address[:-1].strip()

        return address

    def add_address(self, data):
        data['created_by'] = self.created_by
        obj, created = Address.objects.get_or_create(
            tenant=self.tenant,
            zip=data.pop('zip'),
            city=data.pop('city'),
            address=data.pop('address'),
            defaults=data
        )
        return obj, created


class ImportAddress(Import):

    def load(self, file_name):
        '''get Addresses
        we use this to get the invoicing addresses

        file_name = 'Abonnenten Gebühren einzeilig.xlsx'
        writes address_data with abo_nr as key
        '''
        file_path = Path(
            settings.BASE_DIR) / 'billing' / 'fixtures' / file_name
        wb = load_workbook(file_path)
        ws = wb.active  # Or wb['SheetName']
        rows = [row for row in ws.iter_rows(values_only=True)]

        # Init
        address_data = {}

        # Read
        for row in rows:
            cells = row
            if cells[0] and isinstance(cells[0], (int, float)):
                # Get data
                (abo_nr, _, _, namevorname, _, strasse, plz_ort, *_) = row

                # Make address
                if not strasse:
                    # e.g. Autobahnraststätte Gunzgen Nord AG
                    strasse = namevorname.strip()

                # Save address
                data = {
                    'zip': plz_ort.split(' ')[0],
                    'city': plz_ort.split(' ')[1],
                    'address': self.clean_address(strasse)
                }
                obj, _created = self.add_address(data)

                # make link to abo_nr
                address_data[abo_nr] = obj

        return address_data


class ImportData(ImportAddress):

    def __init__(self, setup_id, route_id, datetime_default):
        '''
            datetime_default,e g. '2024-03-31'
        '''
        super().__init__(setup_id)

        # From route
        self.route = Route.objects.get(
            tenant=self.tenant, id=route_id)
        self.period = self.route.period
        self.asset_categories = self.period.asset_categories.all()  # WA + HWA

        # Time
        self.datetime = timezone.make_aware(
            datetime.strptime(datetime_default, "%Y-%m-%d"))
        self.date = self.datetime.date()

        # Const
        self.article_category = ArticleCategory.objects.filter(
            setup=self.setup, code='water').first()

    @staticmethod
    def convert_to_date(date_string):
        ''' e.g. date_string = "22.04.2009"
        '''
        return datetime.strptime(date_string, '%d.%m.%Y').date()

    @staticmethod
    def get_company(name):
        if ' AG' in name:
            return name
        elif ' gmbh' in name.lower():
            return name
        elif 'genossenschaft' in name.lower():
            return name
        elif 'verband' in name.lower():
            return name
        elif 'verein' in name.lower():
            return name
        elif 'gemeinde' in name.lower():
            return name
        elif 'STWEG' in name.upper():
            return name

        return None

    @staticmethod
    def get_last_name(name):
        return name.split(' ', 1)[0]

    @staticmethod
    def make_article(category, tarif, anr, name, price):
        '''
        e.g.
            category = self.category
            tarif = 1
            anr = 1
            price = 1.1
        '''
        tarif_str = str(tarif).zfill(2)  # leading 0
        praefix = (
            ARTICLE.TYPE.WATER if tarif_str[0] == '0'
            else ARTICLE.TYPE.SEWAGE
        )
        nr = f"{praefix}-{tarif_str}_{anr or '0'}"
        name = name

        return {
            'nr': nr,
            'category': category,
            'name': name,
            'price': price

        }
        article, _created = self.add_article(
            nr, self.article_category, name, ansatz)

    # Models

    # Core
    def add_address_category(self, building_address, alt_name):
        if (alt_name in ALLMEND
                or building_address.address.startswith('Allmend ')):
            # e.g. Allmend 4 but not Allmendstrasse 
            category = AddressCategory.objects.get(
                tenant=self.tenant, code='allmend')
        elif building_address.zip == str(ZIP):
            category = AddressCategory.objects.get(
                tenant=self.tenant, code='gunzgen')            
        else:
            return

        building_address.categories.add(category)

    def add_building(self, name, description, address):
        obj, created = Building.objects.get_or_create(
            tenant=self.tenant,
            name=name,
            defaults={
                'address': address,
                'description': description,
                'created_by': self.created_by
            }
        )
        return obj, created

    def add_person(self, data):
        data.update({
            'category': self.person_category,
            'is_customer': True,
            'sync_to_accounting': False,
            'created_by': self.created_by
        })
        obj, created = Person.objects.update_or_create(
            tenant=self.tenant,
            company=data.pop('company'),
            alt_name=data.pop('alt_name'),
            defaults=data
        )
        return obj, created

    def add_person_address(self, person, address, address_type):
        obj, created = PersonAddress.objects.get_or_create(
            tenant=self.tenant,
            address=address,
            type=address_type,
            person=person,
            created_by=self.created_by
        )

        return obj, created

    # Asset
    def add_device(self, data):
        data['created_by'] = self.created_by
        obj, created = Device.objects.get_or_create(
            tenant=self.tenant,
            code=data.pop('code'),
            defaults=data
        )
        if created:
            logger.warning(f"counter {obj.code} did not exist. Created now")
        
        return obj, created

    def add_event(self, device, dt, status, data):
        data['created_by'] = self.created_by
        obj, created = EventLog.objects.get_or_create(
            tenant=self.tenant,
            device=device,
            datetime=dt,
            status=status,
            defaults=data
        )
        return obj, created

    # Accounting
    def add_article(self, data):
        # Prepare data
        data.update({
            'sales_price': data.pop('price'),
            'created_by': self.created_by,
            'is_enabled_sync': True,
            'sync_to_accounting': True
        })

        # Save data
        obj, created = Article.objects.get_or_create(
            tenant=self.tenant,
            setup=self.setup,
            nr=data.pop('nr'),
            category=data.pop('category'),
            defaults=data
        )

        return obj, created

    # Billing
    def add_measurement(self, counter, route, datetime, data):
        data['created_by'] = self.created_by
        obj, created = Measurement.objects.get_or_create(
            tenant=self.tenant,
            counter=counter,
            route=route,
            datetime=datetime,
            defaults=data
        )
        return obj, created

    def add_subscription(self, subscriber_number, data):
        obj, created = Subscription.objects.get_or_create(
            tenant=self.tenant,
            created_by=self.created_by,
            subscriber_number=subscriber_number,
            defaults=data
        )
        return obj, created

    def add_subscription_article(self, subscription, article):
        subscription.articles.add(article)

    def load_block_intro(self, row_nr, rows, address_data):
        ''' load first block, 4 lines
            returns:
                subscriber_number
                building
                subscription

        '''
        (
            period, subscriber_name, _, _, _, subscriber_number, *_
        ) = rows[row_nr]
        (
            _, invoice_address, _, _, mut_c, *_
        ) = rows[row_nr + 1]
        (
            _, _, _, _, _, start, _, _, _, _, _, building_address, *_
        ) = rows[row_nr + 2]
        (
            _, invoice_receiver, _, _, _, exit, _, _, _, _, _,
            building_category, *_
        ) = rows[row_nr + 3]

        logger.info(f"Reading abo_nr {subscriber_number}")

        # Building Address
        if not building_address:
            # Make address, e.g. Autobahnraststätte Gunzgen Nord AG
            building_address = subscriber_name.strip()

        # Make address
        address = self.clean_address(building_address)
        data = dict(
            zip=ZIP,
            city=CITY,
            address=address
        )
        building_address, _created = self.add_address(data)

        # Building
        name = address
        building, _created = self.add_building(
            name, building_category, building_address)

        # Subscriber
        subscriber_name = subscriber_name.strip()
        company = self.get_company(subscriber_name)
        alt_name = subscriber_name
        if company:
            last_name = None
        else:
            last_name = self.get_last_name(subscriber_name)

        data = {
            'company': company,
            'last_name': last_name,
            'alt_name': subscriber_name,

            # we use notes for storing old number
            'notes': f'abo_nr: {subscriber_number}'
        }
        subscriber, _created = self.add_person(data)

        # Add address
        self.add_person_address(
            subscriber, building_address, PersonAddress.TYPE.MAIN)

        # AddressCategory
        self.add_address_category(building_address, subscriber_name)        

        # Invoice address
        invoice_address = address_data[subscriber_number]
        if building_address == invoice_address:
            self.add_person_address(
                subscriber, building_address,
                PersonAddress.TYPE.INVOICE)
            recipient = subscriber
        else:
            # Create recipient
            company = self.get_company(invoice_receiver)
            alt_name = invoice_receiver.strip()
            if company:
                last_name = None
            else:
                last_name = self.get_last_name(invoice_receiver)

            data = {
                'company': company,
                'last_name': last_name,
                'alt_name': invoice_receiver,
            }
            recipient, _created = self.add_person(data)

            # Create recipient address
            _obj, _created = self.add_person_address(
                recipient, invoice_address,
                PersonAddress.TYPE.INVOICE)

        # Subscription
        start_date = self.convert_to_date(start)
        if exit:
            end_date = self.convert_to_date(exit)
        else:
            end_date = None

        data = {
            'subscriber': subscriber,
            'recipient': recipient,
            'building': building,
            'start': start_date,
            'end': end_date,
        }
        subscription, _created = self.add_subscription(
            subscriber_number, data)

        return subscriber_number, building, subscription

    def load_block_counter(self, row, building, subscription):
        '''
        returns:
            water_tarif
            counter
            measurement
        '''
        (
            counter_nr, montage_nr, wohnungsbez, abl_code, _,
            montage_date, _, tarif, bez, tage, fkt, anz_zw,
            zw_alt_1, zw_alt_2, strg_z, add, zuge, zuga, folge
        ) = row
                    
        # Add Counter
        dt = parse_gesoft_to_datetime(montage_date)        
        data = {
            'code': counter_nr,
            'number': counter_nr,
            'date_added': dt.date(),        
        }      

        # Add device
        device, _created = self.add_device(data)

        # Add to subscription
        subscription.counters.add(device)

        # Add Montage
        data = {
            'building': building,
            'notes': f'Mont-Nr. {montage_nr}'
        }
        event, _created = self.add_event(
            device, dt, DEVICE_STATUS.MOUNTED, data)

        # Add Measurements
        data = {
            'value_previous': zw_alt_1 or zw_alt_2,
            'building': building,  # efficieny
            'period': self.period,  # efficieny
            'subscription': subscription,  # efficieny
        }
        measurement, _created = self.add_measurement(
            device, self.route, self.datetime, data)

        return tarif, device, measurement

    def load_block_pricing(
            self, row, subscription, measurement, consumption_only=False):
        '''use consumption_only if values should be not updated and it is
            just for statictics; these records needs to be manually updated
        '''
        (
            tarif, bez, p_text, _ , _ , basis, anr, ansatz, betrag,
            tage, text, _ , zusatztext, _ , strgz, berz, strgg,
            berg, folge
        ) = row

        # Measurement
        if measurement and tarif in [14, 20]:
            # Update consumption
            measurement.consumption = basis or 0

            # Update value
            if not consumption_only:
                # Update value
                value_previous = measurement.value_previous or 0
                measurement.value = value_previous + measurement.consumption

                # Update value_min, value_max
                self.value_min = (
                    measurement.consumption * self.route.confidence_min)
                self.value_max = (
                    measurement.consumption * self.route.confidence_max)

            measurement.save()

        # Article
        name = {'de': p_text}
        price = ansatz
        data = self.make_article(
            self.article_category, tarif, anr, name, price)

        article, _created = self.add_article(data)

        # Add article
        self.add_subscription_article(subscription, article)

    def load(self, file_name, address_data):
        # Load the workbook and select a sheet
        file_path = Path(
            settings.BASE_DIR) / 'billing' / 'fixtures' / file_name
        wb = load_workbook(file_path)
        ws = wb.active  # Or wb['SheetName']
        rows = [row for row in ws.iter_rows(values_only=True)]

        # Load
        for row_nr, row in enumerate(rows):
            first_cell = row[0]
            if (first_cell and isinstance(first_cell, str)
                    and first_cell.startswith('WA-')):
                # Load intro
                result = self.load_block_intro(row_nr, rows, address_data)
                subscriber_number, building, subscription = result
                measurements = []
                tarif_water = None
            elif isinstance(first_cell, (int, float)):
                if first_cell > 100:
                    # Load counters
                    result = self.load_block_counter(
                        row, building, subscription)
                    tarif_water, counter, measurement = result

                    # Add measurement
                    measurements.append(measurement)

                    # Add water
                    water = self.make_article(
                        self.article_category,
                        tarif_water,
                        ARTICLE.WATER.anr,
                        ARTICLE.WATER.name,
                        ARTICLE.WATER.price
                    )
                    article, _created = self.add_article(water)
                    self.add_subscription_article(subscription, article)

                else:
                    # Load pricing
                    if measurements:
                        # we take the first
                        
                        # If there are more than one counter we just take the
                        # first one and put the total consumption in the first
                        # counter; manually update later!!!
                        update_measurement = measurements[0]
                        consumption_only = len(measurements) > 1

                        # load consumption
                        self.load_block_pricing(
                            row, subscription, update_measurement,
                            consumption_only)
                    else:
                        msg = f"Row nr {row_nr}: no measurement created for {row}" 
                        logger.warning(msg)
