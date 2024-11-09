import json
import requests
import dicttoxml
import warnings
from xml.etree import ElementTree
from enum import Enum
from requests.auth import HTTPBasicAuth
from time import sleep

BASE_URL = 'https://{org}.cashctrl.com/api/v1'

ENCODING = 'utf-8'
LANGUAGES = ['de', 'en', 'fr', 'it']
LANGUAGE_API = 'en'  # for coding
LANGUAGE_DEFAULT = 'de'  # for displaying data, esp. PDFs, Excel sheets and CSV files

class DATA_TYPE:
    TEXT = 'TEXT'
    CHECKBOX = 'CHECKBOX'


class FIELD_TYPE(Enum):
    JOURNAL = 'JOURNAL'
    ACCOUNT = 'ACCOUNT'
    INVENTORY_ARTICLE = 'INVENTORY_ARTICLE'
    INVENTORY_ASSET = 'INVENTORY_ASSET'
    ORDER = 'ORDER'
    PERSON = 'PERSON'
    FILE = 'FILE'


class ADRESS_TYPE:
    MAIN = 'MAIN'


class EMAIL:
    WORK = 'EMAIL_WORK'


class PHONE:
    WORK = 'PHONE_WORK'



class CashCtrl(object):

    def __init__(self, org, api_key, language=LANGUAGE_DEFAULT):
        self.auth = HTTPBasicAuth(api_key, '')
        self.base = BASE_URL.format(org=org)
        self.language = language
        self.custom = self.load_custom_fields()

    # Helpers
    @staticmethod
    def get_response(request_callable, url, **kwargs):
        for try_nr in range(5):
            response = request_callable(url, **kwargs)

            # If rate-limited, wait a bit and try again
            if response.status_code == 429:
                print("Rate limit reached. Sleeping for 10 seconds...")
                sleep(10)
                continue
                
            # Check HTTP status code
            elif not response.ok:
                raise Exception(f"HTTP error occurred: {response.status_code} - "
                                f"{response.reason} {response.text}")            

            # Parse JSON content
            content = response.json()
            
            # Check if 'success' field in the content is False
            if not content.get('success', False):
                # Handle application-specific errors
                error_message = ''
                for error in content.get('errors', []):
                    error_message += (
                        f"Field: {error.get('field', 'Unknown')}, "
                        f"Error Message: {error.get('message', '')}")
                raise Exception(f"JSON error occurred: {error_message}")

            # Else, proceed as normal...
            return response.json()

        raise Exception(f"Maximum of {try_nr + 1} reached")
    
    @staticmethod
    def dict_to_xml_values(dictionary):
        '''e.g. data_dict = {
                "de": "cust_color",
                "en": "cust_color",
                "fr": "cust_color",
                "it": "cust_color"
            }
            returns <values><de>cust_color</de><en>cust_color</en><fr>cust_color</fr><it>cust_color</it></values>
        '''        
        if dictionary:                   
            # add values as key
            data = dict(values=dictionary)
            
            # Convert dictionary to XML
            xml_str = dicttoxml.dicttoxml(data, custom_root='root', attr_type=False)

            # Parse the XML string
            root = ElementTree.fromstring(xml_str)

            # Find the 'values' element and convert it back to a string
            values_element = root.find('values')
            xml_bytes = ElementTree.tostring(values_element, encoding=ENCODING)

            # Decode bytes to string
            xml_string = xml_bytes.decode(ENCODING)
        else:
            xml_string = ''
        
        return xml_string

    @staticmethod
    def xml_values_to_dict(xml_str):
        '''e.g. xml_str = "<values><de>cust_color</de><en>cust_color</en><fr>cust_color</fr><it>cust_color</it></values>"
            returns {
                "de": "cust_color",
                "en": "cust_color",
                "fr": "cust_color",
                "it": "cust_color"
            }
        '''
        if xml_str:
            # Parse the XML string
            root = ElementTree.fromstring(xml_str)
            
            # Convert XML to dictionary
            return {child.tag: child.text for child in root}
        else:
            return {}

    # Get Field Name, initialize at beginning
    def load_custom_fields(self):
        ''' Get existing fields
        '''        
        return []

    def convert_custom_dict_to_xml(self, custom_data, field_type):
        # Convert 'custom' field to XML if present
        if custom_data:
            # Make data
            data = {}
            for key, value in custom_data.items():
                field = next(
                    (x['fieldId'] for x in self.custom[field_type]
                     if x['name'][LANGUAGE_API] == key
                    ), None)
                if field:
                    data[field] = value
                else:
                    raise ValueError(f"No matching custom field '{key}'")
            
            # Convert            
            return self.dict_to_xml_values(data)
        else:
            return ''

    def convert_custom_xml_to_dict(self, data):            
        if 'custom' in data:
            custom = self.xml_values_to_dict(data.pop('custom'))
            data['custom'] = {}
            for field, value in custom.items():
                key = next(
                    (x['name'].get(LANGUAGE_API)
                     for x in self.custom[self.field_type]
                     if x['fieldId'] == field), None)
                if key:
                    data['custom'][key] = value
                else:
                    warnings.warn(
                        f"Ignoring custom field for: '{field}' "
                        f"with value '{value}'")

        return data

    # Function to get
    def get_account_list(self):
        url = f'{self.base}/account/category/list.json'
        response = requests.get(url, auth=self.auth)
        return response.json()
    
    def get_settings(self):
        url = f'{self.base}/setting/read.json'
        response = requests.get(url, auth=self.auth)
        return response.json()
    
    def get_categories(self):
        url = f'{self.base}/account/category/tree.json'
        response = requests.get(url, auth=self.auth)        
        return response.json()

    def get_journal_list(self):
        url = f'{self.base}/journal/list.json'
        response = requests.get(url, auth=self.auth)
        return response.json()

    def get_order_list(self):
        url = f'{self.base}/order/read.json'
        params = {'id': 5}
        response = requests.get(url, params=params, auth=self.auth)
        return response.json()

    # Function to create a new book entry
    def create_book_entry(
            self, date_added, title, sequence_number_id, debit_id, credit_id,
            tax_id, amount):
        url = f'{self.base}/journal/create.json'
        data = {
            'dateAdded': date_added,
            'title': title,
            'sequenceNumberId': sequence_number_id,
            'debitId': debit_id,
            'creditId': credit_id,
            'taxId': tax_id,
            'amount': amount
        }
        print("*", title)        
        response = self.get_response(
            requests.post, url, data=data, auth=self.auth)

    def create_order_entry(self, data=None):
        url = f'{self.base}/order/create.json'
        data = {
            # mandatory
            "associateId": "1",
            "categoryId": 4,
            "date": "2024-10-12",

            # optional
            "accountId": 4,
            "currencyId": None,
            "currencyRate": 1.0,
            "custom": "<values><customField32>2023-10-01</customField32><customField33>2024-03-31</customField33><customField34>2023-04-01</customField34><customField35>2023-09-30</customField35><customField36>33</customField36><customField37>76</customField37><customField38>m³</customField38><customField39>Wasserabrechnung</customField39><customField41>['Wasser - schriftlich innert 10 Tagen an die Wasserkommission der Bürgergemeinde Gunzgen','Abwasser - schriftlich innert 10 Tagen an den Einwohnergemeinderat Gunzgen']</customField41><customField42>['Wasser: CHE-108.964.801 MWST','Abwasser: CHE-112.793.129 MWST']</customField42><customField43>22527801</customField43></values>",
            "daysBefore": None,
            "description": "Wasserrechnung",
            "discountPercentage": None,
            "dueDays": 30,
            "endDate": None,
            "isDisplayItemGross": False,
            "items": [
                {
                    "accountId": 42,
                    "name": "Wasser - Verbrauch",
                    "unitPrice": 1.1286,
                    "allocations": [],
                    "articleNr": "A-00002",
                    "description": "Vorperiode 01.04.2023 - 30.09.2023: 76 m³ (-55%)",
                    "discountPercentage": None,
                    "quantity": 33.0,
                    "taxId": 3,
                    "type": "ARTICLE",
                    "unitId": 1000
                }
            ],
            "language": None,
            "notes": "Wichtig!<br />",
            "notifyEmail": False,
            "notifyPersonId": None,
            "notifyType": None,
            "notifyUserId": None,
            "previousId": None,
            "recurrence": None,
            "responsiblePersonId": 24,
            "roundingId": None,
            "sequenceNumberId": None,
            "startDate": None,
            "statusId": 16
        }

        data["items"] = json.dumps(data.get("items"))
        print("*done")        
        response = self.get_response(
            requests.post, url, data=data, auth=self.auth)

                

    def get_custom_fields(self, type):
        # get data
        url = f'{self.base}/customfield/list.json'
        params = {'type': type}
        response = requests.get(url, params=params, auth=self.auth)        
        fields = response.json().get('data')

        # convert       
        for field in fields:
            for label in ['name', 'description']:
                field[label] = self.xml_values_to_dict(field.pop(label))                
        
        return fields 

    def create_custom_field(self, field):        
        # convert
        for label in ['name', 'description']:
            field[label] = self.dict_to_xml_values(field.pop(label))           

        # create
        url = f'{self.base}/customfield/create.json'
        requests.post(url, data=field, auth=self.auth)

    def get_custom_groups(self):
        # get data
        url = f'{self.base}/customfield/group/list.json'
        params = {'type': FIELD_TYPE.PERSON.value}
        response = requests.get(url, params=params, auth=self.auth)
        groups = response.json().get('data')

        # convert
        for group in groups:
            group['name'] = self.xml_values_to_dict(group.pop('name'))
            
        return groups       

    def create_custom_group(self, group):        
        # convert
        group['name'] = self.dict_to_xml_values(group['name'])

        # create
        url = f'{self.base}/customfield/group/create.json'
        requests.post(url, data=group, auth=self.auth)
                    
    def create_custom_fields(self, groups, fields):
        '''name: e.g. 'CustomField_de'
        '''
        # get existing groups
        groups_existing = self.get_custom_groups()

        # create groups if not existing
        groups_created = 0
        for group in groups:
            reference = next(
                (x for x in groups_existing
                 if (x['type'] == group['type'] and
                     x['name'].get(LANGUAGE_API) == group['name'][LANGUAGE_API])
                 ), None)
            
            if not reference:                
                self.create_custom_group(group)
                groups_created += 1

        if groups_created:
            # reload groups
            groups_existing = self.get_custom_groups()
            print(f"{groups_created} groups created.")

        # get existing custom fields
        fields_created = 0
        for field in fields:
            name = field['name'][LANGUAGE_API]
            existing = next(
                (x for x in self.custom[field['type']]
                 if x['name'].get(LANGUAGE_API) == name), None)
            if not existing:
                # search group
                field['groupId'] = next(
                    (x['id'] for x in groups_existing
                     if (x['type'] == field['type'] and
                         x['name'].get(LANGUAGE_API) == field['reference'])
                    ), None)

                self.create_custom_field(field)
                fields_created += 1
                if not field['groupId']:
                    warnings.warn(f"No matching group found for: {field}")

        if fields_created:
            # reload custom fields
            self.custom = self.load_custom_fields()
            print(f"{fields_created} fields created.")

    def get(self, id):
        # Init
        url = self.url.format(action='read.json')
        params = {'id': id}

        # Get
        response = requests.get(url, params=params, auth=self.auth)
        data = response.json()['data']

        # clear
        self.convert_custom_xml_to_dict(data)
        
        return data        

    def gets(self, limit):
        # Init
        url = self.url.format(action='list.json')
        params = {'id': id}

        # Get
        response = requests.get(url, params=params, auth=self.auth)
        data = response.json()['data']

        # clear
        data = [self.convert_custom_xml_to_dict(x) for x in data]        
        
        return data   

    def _pre_post(self, data):
        # Convert jsons as API only takes str, not JSON
        for key in self.jsons:
            person_data[key] = json.dumps(data.get(key))

        # Convert 'custom' field to XML if any
        if 'custom' in data:
            # Get existing fields
            data['custom'] = self.convert_custom_dict_to_xml(data.pop('custom'))
                                                             
        return data

    def create(self, data):
        '''create data
        '''
        url = self.url.format(action='update.json')
        response = requests.post(url, data=_pre_post(data), auth=self.auth)                                               
        return response.json()

    def patch(self, id, data):
        '''retrieve record with id given, and patch with data given
        '''
        person_data = self.get(id)
        data = {**person, **data}  # merge data
        return self.post(data)

    def post(self, data):     
        url = self.url.format(action='update.json')
        response = requests.post(url, data=_pre_post(data), auth=self.auth)                                               
        return response.json() 
            

class Person(CashCtrl):
    field_type = FIELD_TYPE.PERSON
    jsons = ['addresses', 'contacts']
    # url = f'{base}/person/{action}'    

    def put(self, data):
        '''data: complete person record incl. id
        '''
        pass
    

# Define parameters
org = 'bdo'  # replace with your org name
key = 'cp5H9PTjjROadtnHso21Yt6Flt9s0M4P'  # replace with your key

# Enable
enable_get_account_list = True
enable_get_journal_list = False
enable_get_order_list = False
enable_get_categories = False
enable_get_person = False
enable_get_persons = False
enable_get_settings = False
enable_create_book_entry = False
enable_create_custom_fields = False
enable_create_order_entry = False
enable_create_person_data = False
enable_update_person_data = False

ctrl = CashCtrl(org, key)

if enable_create_order_entry:
    # Test orders
    order = ctrl.create_order_entry()
    print(f'created test order {order}')

if enable_get_account_list:
    # Journal list
    account_list = ctrl.get_account_list()
    print(f'get account_list {account_list}')

if enable_get_journal_list:
    # Journal list
    journal_list = ctrl.get_journal_list()
    print(f'get journal_list {journal_list}')

if enable_get_order_list:
    # order list
    order_list = ctrl.get_order_list()
    print(f'get orderl_list {order_list}')

if enable_get_categories:
    # categories
    categories = ctrl.get_categories()
    print(f'get get_categories {categories}')

if enable_get_settings:
    # settings
    settings = ctrl.get_settings()
    print(f'get get_settings {settings}')

if enable_get_person:
    # person
    id = 21
    person = ctrl.get_person(id)
    print(f'get person {person}')

if enable_get_persons:
    # persons
    persons = ctrl.get_persons()
    print(f'get persons {persons}')

if enable_create_book_entry:
    # Create book entry
    nr = 5000
    for i in range(500):
        date_added = '2024-07-06'
        title = f'{nr}_{i} API generated book entry'
        sequence_number_id = 6
        debit_id = 1
        credit_id = 15
        tax_id = 1
        amount = 500

        response = ctrl.create_book_entry(
            date_added, title, sequence_number_id, debit_id, credit_id, tax_id,
            amount)
              
    print(f'created book entries')

if enable_create_custom_fields:
    # Groups
    groups = [{
        'type': FIELD_TYPE.PERSON,
        'name': {
             'de': 'Zusatz',
             'en': 'Additional',
             'fr': 'Additional',
             'it': 'Additional'
        }
    }]

    # Custom Fields
    fields = [{
        'type': FIELD_TYPE.PERSON,
        'reference': 'Additional',
        'name': {
             'de': 'Farbe',
             'en': 'color',
             'fr': 'color',
             'it': 'color'
        },
        'description': {
             'de': 'Farbe',
             'en': 'Color',
             'fr': 'Color',
             'it': 'Color'
        },
        'data_type': DATA_TYPE.TEXT,
        'isMulti': False,
        'values': [],
    }, {
        'type': FIELD_TYPE.PERSON,
        'reference': 'Additional',
        'name': {
             'de': 'Abgeschlossen',
             'en': 'completed',
             'fr': 'completed',
             'it': 'completed'
        },
        'description': {},
        'data_type': DATA_TYPE.TEXT,
        'isMulti': False,
        'values': [],
    }]
    
    ctrl.create_custom_fields(groups, fields)

if enable_create_person_data:
    person_data = {
        'company': 'Company name',
        'firstName': 'First name',
        'lastName': 'Last name',
        'custom': {
            'cust_color': 'blue',
            'test': 'xxx'
        },
        'addresses': [{
            'type': ADRESS_TYPE.MAIN,
            'address': 'Street 123',
            'city': 'City',
            'country': 'CHE',
            'zip': '7000'
        }],
        'contacts': [
            {'address': 'email@example.com', 'type': EMAIL.WORK},
            {'address': '123456789', 'type': PHONE.WORK}
        ],        
        'categoryId': 1,
        'contacts': [{'address': 'email@example.com', 'type': EMAIL.WORK},
                     {'address': '123456789', 'type': PHONE.WORK}],
        'sequenceNumberId': 1,
        'isInactive': False,
        # Add more fields here if needed
    }

    response = ctrl.create_person(person_data)
    print(f'person_data {response}')

if enable_update_person_data:
    # no put available!!!
    # get person
    id = 22
    person = ctrl.get_person(id)
    print(f'get person {person}')    
    
    data = {    
        'company': 'Züri à la carte Company AG',
        'firstName': 'Otto',
        'lastName': 'Test2',
        'dateBirth': '2020-01-15',
        'custom': {'color': 'green', 'completed': True}
    }

    response = ctrl.update_person({**person, **data})
    print(f'person_data {response}')
