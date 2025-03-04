'''
billing/gesoft_counter_data_import.py
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
     Building, BuildingAddress
)

logger = logging.getLogger(__name__)

CITY = 'Gunzgen'
ZIP = 4617


class Import:

    def __init__(self, setup_id, route_id, datetime_default):
        '''
            datetime_default,e g. '2024-03-31'
        '''        
        # From setup
        self.setup = APISetup.objects.get(id=setup_id)
        self.tenant = self.setup.tenant
        self.created_by = self.setup.created_by        
        self.person_category = PersonCategory.objects.get(
            tenant=self.tenant, code='subscriber')
            
        # From route    
        self.route = Route.objects.get(
            tenant=self.tenant, id=route_id)
        self.asset_category = self.route.asset_category  # Counter
        
        # Time
        self.datetime = timezone.make_aware(
            datetime.strptime(datetime_default, "%Y-%m-%d"))
        self.date = self.datetime.date()        
        
        # Const
        self.article_category = ArticleCategory.objects.get(
            setup=self.setup, code='water')  

    @staticmethod
    def convert_to_date(date_string):
        ''' e.g. date_string = "22.04.2009"
        '''        
        return datetime.strptime(date_string, '%d.%m.%Y').date()

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

    # Models

    # Core
    def add_address(self, data):
        data['created_by'] = self.created_by
        obj, created = Address.objects.get_or_create(
            tenant=self.tenant,
            zip=data.pop('zip'),
            city=data.pop('city'),
            address=data.pop('address'),
            defaults=data
        )

        if not obj.categories.exists():
            if obj.address:
                code = 'Allend' if 'Allend' in obj.address else 'Gunzgen'
            else:
                code = 'Gunzgen'
            category, _ = AddressCategory.objects.get_or_create(
                    tenant=self.tenant,
                    code=code,
                    type=AddressCategory.TYPE.AREA,
                    created_by=self.created_by
            )
            obj.categories.add(category)
            obj.save()
            obj.refresh_from_db()

        return obj, created

    def add_building(self, name, description, address):
        obj, created = Building.objects.get_or_create(
            tenant=self.tenant,
            name=name,
            defaults={
                'description': description,
                'created_by': self.created_by
            }
        )
        if created:
            obj_address, created = BuildingAddress.objects.get_or_create(
                tenant=self.tenant,
                address=address,
                building=obj,
                created_by=self.created_by
            )

        return obj

    def add_person(self, data):
        data.update({
            'category': self.person_category,
            'is_customer': True,
            'sync_to_accounting': False,
            'created_by': self.created_by
        })
        obj, created = Person.objects.get_or_create(
            tenant=self.tenant,
            company=data.pop('company'),
            alt_name=data.pop('alt_name'),
            defaults=data
        )
        return obj

    def add_person_address(self, person, address, address_type):
        obj_address, created = PersonAddress.objects.get_or_create(
            tenant=self.tenant,
            address=address,
            type=address_type,
            person=person,
            created_by=self.created_by
        )

        return obj_address

    # Asset
    def add_device(self, data, category):
        data['created_by'] = self.created_by
        obj, created = Device.objects.get_or_create(
            tenant=self.tenant,
            code=data.pop('code'),
            category=category,
            defaults=data
        )
        return obj

    def add_event(self, device, date, status, data):
        data['created_by'] = self.created_by
        obj, created = EventLog.objects.get_or_create(
            tenant=self.tenant,
            device=device,
            date=date,
            status=status,
            defaults=data
        )
        return obj

    # Accounting
    def add_article(self, nr, category, name, sales_price):
        obj, created = Article.objects.get_or_create(
            tenant=self.tenant,
            setup=self.setup,
            nr=nr,
            category=category,
            defaults={
                'name': name,
                'sales_price': sales_price,
                'created_by': self.created_by
            }
        )
        return obj

    # Bill
    def add_measurement(self, counter, route, datetime, data):
        data['created_by'] = self.created_by
        obj, created = Measurement.objects.get_or_create(
            tenant=self.tenant,
            counter=counter,
            route=route,
            datetime=datetime,
            defaults=data
        )
        return obj

    def add_subscription(
            self, subscriber, recipient, building, start, end, articles=[]):
        obj, created = Subscription.objects.get_or_create(
            tenant=self.tenant,
            subscriber=subscriber,
            recipient=recipient,
            building=building,
            defaults=dict(
                start=start,
                end=end,
                created_by=self.created_by
            )
        )
        for article in articles:
            obj.articles.add(article)
        
        return obj

    def add_subscription_article(self, subscription, article):
        subscription.articles.add(article)

    def load_addresses(self, file_name):
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
            if (cells[0] and (
                    isinstance(cells[0], int) or isinstance(cells[0], float))):
                # Get data
                (
                    abo_nr, r_empf, persnr, namevorname, _, strasse, plz_ort, _,
                    tarif, periode, tarifbez, basis, ansatznr, ansatz, tage,
                    betrag, inklmwst, steuercodezähler, berechnungscodezähler,
                    steuercodegebühren, berechnungscodegebühren, gebührentext,
                     gebührenzusatztext
                ) = row

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

    def load_counter(self, file_name, address_data):
        # Load the workbook and select a sheet
        file_path = Path(
            settings.BASE_DIR) / 'billing' / 'fixtures' / file_name
        wb = load_workbook(file_path)
        ws = wb.active  # Or wb['SheetName']
        rows = [row for row in ws.iter_rows(values_only=True)]

        # Init
        addresses = []  # -> Address
        building = {}  # key: subscriber_number
        subscriber = {}  # key: subscriber_number
        subscription = {}
        counter = {}
        montage = {}
        product = {}
        measurements = []

        # Load
        for row_nr, row in enumerate(rows):
            cells = row
            if (cells[0] and isinstance(cells[0], str)
                    and cells[0].startswith('WA-')):
                # Subscription data ------------------------------------------                
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
                    
                address = self.clean_address(building_address)
                data = dict(
                    zip=ZIP,
                    city=CITY,
                    address=address
                )
                building_address, _created = self.add_address(data)

                # Building
                name = address
                building = self.add_building(
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
                }
                subscriber = self.add_person(data)

                # Add address
                self.add_person_address(
                    subscriber, building_address, PersonAddress.TYPE.MAIN)

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
                    recipient = self.add_person(data)

                    # Create recipient address
                    _obj = self.add_person_address(
                        recipient, invoice_address,
                        PersonAddress.TYPE.INVOICE)

            elif isinstance(cells[0], int):
                if cells[0] > 100:
                    # Counter data ------------------------------------------
                    (
                        counter_nr, montage_nr, wohnungsbez, abl_code, _,
                        montage_date, _, tarif, bez, tage, fkt, anz_zw,
                        zw_alt_1, zw_alt_2, strg_z, add, zuge, zuga, folge
                    ) = row

                    # Add Counter
                    date = self.convert_to_date(montage_date)
                    data = {
                        'code': counter_nr,
                        'number': counter_nr,
                        'date_added':date
                    }
                    device = self.add_device(data, self.asset_category)

                    # Add Montage
                    data = {
                        'building': building,
                    }
                    event = self.add_event(
                        device, date, DEVICE_STATUS.MOUNTED, data)

                else:
                    # Pricing data ------------------------------------------
                    (
                        tarif, bez, p_text, _ , _ , basis, anr, ansatz, betrag,
                        tage, text, _ , zusatztext, _ , strgz, berz, strgg,
                        berg, folge
                    ) = row

                    # Article
                    product_key = f"{tarif}_{anr or '0'}"
                    nr = product_key
                    name = {'de': p_text}

                    article = self.add_article(
                        nr, self.article_category, name, ansatz)

                    # Measurements
                    if tarif in [14, 20]:
                        data = {
                            'value': (zw_alt_1 if zw_alt_1 else 0) +
                                (basis if basis else 0),
                            'value_previous': zw_alt_1 if zw_alt_1 else None,
                        }
                        measurement = self.add_measurement(
                            device, self.route, self.datetime, data)

                    # Subscription
                    start_date = self.convert_to_date(start)
                    if exit:
                        end_date = self.convert_to_date(exit)
                    else:
                        end_date = None                    
    
                    subscription = self.add_subscription(
                        subscriber, recipient, building, start_date, end_date)

                    # Add article
                    self.add_subscription_article(subscription, article)
