# accounting/api_cash_ctrl.py
from datetime import datetime
import json
import re
import requests
import xmltodict
from enum import Enum


DECODE = 'utf-8'


# mixins, we change right at down and uploading of data
def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def snake_to_camel(snake_str):
    components = snake_str.split('_')
    camel_case_str = ''.join(x.title() for x in components)

    # ensure the first letter is lowercase and return
    return camel_case_str[0].lower() + camel_case_str[1:]


def create_enum(name, items):
    return Enum(name, {item: item for item in items})


COUNTRY_CODES = [
	'AFG', 'ALA', 'ALB', 'DZA', 'ASM', 'AND', 'AGO', 'AIA', 'ATG', 'ARG', 'ARM',
	'ABW', 'AUS', 'AUT', 'AZE', 'BHS', 'BHR', 'BGD', 'BRB', 'BLR', 'BEL', 'BLZ',
	'BEN', 'BMU', 'BTN', 'BOL', 'BES', 'BIH', 'BWA', 'BVT', 'BRA', 'IOT', 'BRN',
	'BGR', 'BFA', 'BDI', 'KHM', 'CMR', 'CAN', 'CPV', 'CYM', 'CAF', 'TCD', 'CHL',
	'CHN', 'CXR', 'CCK', 'COL', 'COM', 'COG', 'COK', 'CRI', 'CIV', 'HRV', 'CUB',
	'CUW', 'CYP', 'CZE', 'DNK', 'DJI', 'DOM', 'DMA', 'ECU', 'EGY', 'SLV', 'GNQ',
	'ERI', 'EST', 'ETH', 'FLK', 'FRO', 'FJI', 'FIN', 'FRA', 'GUF', 'GUY', 'PYF',
	'GAB', 'GMB', 'GEO', 'DEU', 'GHA', 'GIB', 'GRC', 'GRL', 'GRD', 'GLP', 'GUM',
	'GTM', 'GGY', 'GNB', 'GIN', 'HTI', 'HMD', 'VAT', 'HND', 'HKG', 'HUN', 'IND',
	'IDN', 'IRN', 'IRQ', 'IRL', 'IMN', 'ISR', 'ITA', 'JAM', 'JPN', 'JEY', 'JOR',
	'KAZ', 'KEN', 'KIR', 'PRK', 'KOR', 'KWT', 'KGZ', 'LAO', 'LVA', 'LBN', 'LSO',
	'LBR', 'LBY', 'LIE', 'LTU', 'LUX', 'MAC', 'MKD', 'MDG', 'MWI', 'MYS', 'MDV',
	'SOM', 'MLI', 'MLT', 'MHL', 'MTQ', 'MRT', 'MUS', 'MYT', 'MEX', 'FSM', 'MDA',
	'MCO', 'MNG', 'MNE', 'MSR', 'MAR', 'MOZ', 'MMR', 'NAM', 'NRU', 'NPL', 'NLD',
	'NCL', 'NZL', 'NIC', 'NGA', 'NER', 'NIU', 'NFK', 'MNP', 'NOR', 'OMN', 'PAK',
	'PLW', 'PSE', 'PAN', 'PNG', 'PRY', 'PER', 'PHL', 'PCN', 'POL', 'PRT', 'PRI',
	'QAT', 'REU', 'ROU', 'RUS', 'RWA', 'BLM', 'SHN', 'KNA', 'LCA', 'MAF', 'SPM',
	'VCT', 'WSM', 'SMR', 'STP', 'SAU', 'SEN', 'SRB', 'SYC', 'SLE', 'SGP', 'SXM',
	'SVK', 'SVN', 'SLB', 'ZAF', 'SGS', 'SSD', 'ESP', 'LKA', 'SDN', 'SUR', 'SJM',
	'SWZ', 'SWE', 'CHE', 'SYR', 'TWN', 'TJK', 'TZA', 'THA', 'TLS', 'TGO', 'TKL',
	'TON', 'TTO', 'TUN', 'TUR', 'TKM', 'TCA', 'TUV', 'UGA', 'UKR', 'ARE', 'GBR',
	'USA', 'URY', 'UZB', 'VUT', 'VEN', 'VNM', 'VIR', 'VGB', 'WLF', 'YEM', 'ZMB',
	'ZWE', 'ISL']


class ADDRESS_TYPE(Enum):
    MAIN = 'MAIN'
    INVOICE = 'INVOICE'
    DELIVERY = 'DELIVERY'
    OTHER = 'OTHER'


class COUNTRY:
    pass
COUNTRY = create_enum('COUNTRY', sorted(COUNTRY_CODES))


class DATA_TYPE(Enum):
    TEXT = 'TEXT'
    TEXTAREA = 'TEXTAREA'
    CHECKBOX = 'CHECKBOX'
    DATE = 'DATE'
    COMBOBOX = 'COMBOBOX'
    NUMBER = 'NUMBER'
    ACCOUNT = 'ACCOUNT'
    PERSON = 'PERSON'


class ELEMENT_TYPE(Enum):
    JOURNAL = 'JOURNAL'
    BALANCE = 'BALANCE'
    PLS = 'PLS'
    STAGGERED = 'STAGGERED'
    COST_CENTER_PLS = 'COST_CENTER_PLS'
    COST_CENTER_BALANCE = 'COST_CENTER_BALANCE'
    COST_CENTER_ALLOCATION = 'COST_CENTER_ALLOCATION'
    COST_CENTER_TARGET = 'COST_CENTER_TARGET'
    COST_CENTER_STATEMENTS = 'COST_CENTER_STATEMENTS'
    CHART_OF_ACCOUNTS = 'CHART_OF_ACCOUNTS'
    OPEN_DEBTORS = 'OPEN_DEBTORS'
    OPEN_CREDITORS = 'OPEN_CREDITORS'
    ORG_CHART = 'ORG_CHART'
    SALES_TAX = 'SALES_TAX'
    TARGET = 'TARGET'
    RESULT_BY_ARTICLE_PER_PERSON = 'RESULT_BY_ARTICLE_PER_PERSON'
    EXPENSE_BY_PERSON = 'EXPENSE_BY_PERSON'
    REVENUE_BY_PERSON = 'REVENUE_BY_PERSON'
    REVENUE_BY_RESPONSIBLE_PERSON = 'REVENUE_BY_RESPONSIBLE_PERSON'
    RESULT_BY_ARTICLE = 'RESULT_BY_ARTICLE'
    STATEMENTS = 'STATEMENTS'
    BALANCE_LIST = 'BALANCE_LIST'
    KEY_FIGURES = 'KEY_FIGURES'
    EXPENSE_BY_PERSON_CHART = 'EXPENSE_BY_PERSON_CHART'
    REVENUE_BY_PERSON_CHART = 'REVENUE_BY_PERSON_CHART'
    RESULT_BY_ARTICLE_CHART = 'RESULT_BY_ARTICLE_CHART'
    BALANCE_PROG_CHART = 'BALANCE_PROG_CHART'
    BALANCE_SHARE_CHART = 'BALANCE_SHARE_CHART'
    CASH_FLOW_CHART = 'CASH_FLOW_CHART'
    TEXT_IMAGE = 'TEXT_IMAGE'


class FIELD_TYPE(Enum):
    JOURNAL = 'JOURNAL'
    ACCOUNT = 'ACCOUNT'
    INVENTORY_ARTICLE = 'INVENTORY_ARTICLE'
    INVENTORY_ASSET = 'INVENTORY_ASSET'
    ORDER = 'ORDER'
    PERSON = 'PERSON'
    FILE = 'FILE'


class GENDER(Enum):
    FEMALE = 'FEMALE'
    MALE = 'MALE'


class ACCOUNT_CATEGORY_TYPE(Enum):
    # Used for cashctrl
    ASSET = 1  # Aktiven
    LIABILITY = 2  # Passiven
    EXPENSE = 3  # Aufwand (INCOME), Ausgaben (INVEST),
    REVENUE = 4  # Ertrag (INCOME), Einnahmen (INVEST),
    BALANCE = 5  #


LANGUAGES = ['de', 'fr', 'it', 'en']
NAME_TAB = 'sc-erp'
NAME_TABS = {'values': {lang: NAME_TAB for lang in LANGUAGES}}

CUSTOM_FIELD_GROUPS = [
    {'type': FIELD_TYPE.ACCOUNT, 'name': NAME_TABS},
    {'type': FIELD_TYPE.INVENTORY_ARTICLE, 'name': NAME_TABS},
    {'type': FIELD_TYPE.INVENTORY_ASSET, 'name': NAME_TABS},
    {'type': FIELD_TYPE.ORDER, 'name': NAME_TABS},
    {'type': FIELD_TYPE.PERSON, 'name': NAME_TABS},
    {'type': FIELD_TYPE.FILE, 'name': NAME_TABS}
]

GROUP_NAME = 'sc-erp'


CUSTOM_FIELDS = [
    {'type': FIELD_TYPE.ACCOUNT, 'group_name': GROUP_NAME,
      'field': 'customField{i}', 'name': 'HRM 2', 'data_type': DATA_TYPE.TEXT
    },
    {'type': FIELD_TYPE.ACCOUNT, 'group_name': GROUP_NAME,
      'field': 'customField{i}', 'name': 'HRM 2 kurz', 'data_type': DATA_TYPE.TEXT
    },
    {'type': FIELD_TYPE.ACCOUNT, 'group_name': GROUP_NAME,
      'field': 'customField{i}', 'name': 'Budget', 'data_type': DATA_TYPE.NUMBER
    },
    {'type': FIELD_TYPE.ORDER, 'group_name': GROUP_NAME,
     'field': 'customField{i}', 'name': 'Kategorie', 'data_type': DATA_TYPE.TEXT,
     'values': ['Gebühren Werke']
    },
    {'type': FIELD_TYPE.PERSON, 'group_name': GROUP_NAME,
     'field': 'customField{i}', 'name': 'Kategorie', 'data_type': DATA_TYPE.COMBOBOX,
     'values': ['Abonnent Werke', 'Einwohner'], 'is_multi': True
    },
    {'type': FIELD_TYPE.FILE, 'group_name': GROUP_NAME,
     'field': 'customField{i}', 'name': 'Kategorie', 'data_type': DATA_TYPE.COMBOBOX,
     'values': ['Abonnent Werke', 'Einwohner'], 'is_multi': True
    }
]

class API_PROJECT(Enum):
    # Report, not implemented yet
    report = {'url': 'report/', 'actions': ['tree']}
    element = {'url': 'element/', 'actions': ['tree']}
    set = {'url': 'set/', 'actions': ['read']}


class CashCtrl(object):
    BASE = "https://{org}.cashctrl.com/api/v1/{url}{action}.json"

    def __init__(self, org, api_key):
        self.org = org
        self.auth = (api_key, '')
        self.data = None  # data can be loaded (list, read) or posted

    @staticmethod
    def str_to_dt(dt_string):
        '''Convert to a datetime object
            dt_string = '2024-10-14 09:58:33.0'
        '''
        return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S.%f')

    # Xml <-> JSON
    @staticmethod
    def clean_value(value):
        if type(value) == str and value.startswith('<values>'):
            # XML
            return xmltodict.parse(value)
        else:
            # Return original value
            return value

    @staticmethod
    def value_to_xml(value):
        # Check if value is a dictionary
        if type(value) is dict and 'values' in value:
            xmlstr = xmltodict.unparse(value['values'], full_document=False)
            return '<values>' + xmlstr + '</values>'
        # Return original value
        else:
            return value

    def clean_dict(self, data):
        post_data = {}
        for key, value in data.items():
            key = camel_to_snake(key)
            if key in ('created',  'last_updated', 'start', 'end'):
                try:
                    value = self.str_to_dt(value)
                except:
                    pass
            post_data[key] = self.clean_value(value)
        return post_data

    # REST API CashCtrl: post, get
    def get(self, url, params):
        response = requests.get(url, params=params, auth=self.auth)
        if response.status_code != 200:
            # Decode the content and include it in the error message
            error_message = response._content.decode(DECODE)
            raise Exception(
                    f"Get request failed with status {response.status_code}. "
                    f"Error message: {error_message}")
        else:            
            return response

    def post(self, url, data=None):
        # Load data from self.data if not given
        if data is None:
            data = self.data
        
        # Check
        if type(data) != dict:
            raise Exception(f"{data} is not of type dict")

        # Build data
        post_data = {}
        for key, value in data.items():
            camel_key = snake_to_camel(key)
            if camel_key in ('start', 'end'):
                value = value.strftime('%Y-%m-%d')
            else:
                value = self.value_to_xml(value)
            post_data[camel_key] = value

        # Post data
        print("*url", url, post_data)
        response = requests.post(url, data=post_data, auth=self.auth)
        if response.status_code != 200:
            # Decode the content and include it in the error message
            error_message = response.content.decode(DECODE)
            raise Exception(
                f"Post request failed with status {response.status_code}. "
                f"Error message: {error_message}")
        elif response.json().get('success') is False:
            # Decode the content and include it in the error message
            error_message = response.content.decode(DECODE)
            raise Exception(
                f"Post request failed with 'success': False. "
                f"Error message: {error_message}")
        else:
            return self.clean_dict(response.json())

    # REST API mine: list, read, create, update, delete
    def list(self, params={}, **filter):
        if filter:
            # e.g. categoryId=110,  camelCase!
            filters = []
            for key, value in filters.items():
                filters.append(
                    {'comparison': 'eq', 'field': key, 'value': value})
            params['filter'] = json.dumps(filters)

        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='list')
        response = self.get(url, params)
        self.data = [self.clean_dict(x) for x in response.json()['data']]
        return self.data

    def read(self, params={}):
        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='read')
        response = self.get(url, params)
        self.data = self.clean_dict(
            json.loads(response._content.decode(DECODE)))
        return self.data
        
    def create(self, data=None):
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='create')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': 'Custom field saved', 'insert_id': 58}

    def update(self, data=None):
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='update')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': 'Account saved', 'insert_id': 183}

    def delete(self, *ids):
        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='delete')
        data = {'ids': ','.join([str(id) for id in ids])}
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': '1 account deleted'}


# Element Classes
class API:
    # Common
    class Currency(CashCtrl):
        url = 'currency/'
        actions = ['list']

    class CurrencyLower(CashCtrl):
        url = 'currency/'
        actions = ['list']

    class CustomField(CashCtrl):
        url = 'customfield/'
        actions = ['list', 'create']
        
        def create(
                self, name, group, data_type, is_multi=False, values=[]):
            '''is_multi = True not tested yet
                group has type and name
            '''            
            type = group['type']
            group_obj = API.CustomFieldGroup(self.org, self.key)
            group_data = group_obj.get(group['name'], type)
            if not group_data:
                raise Exception(f"Group name '{group}' not found.")

            data = {
                'name': name,
                'type': type,
                'group_id': group_data['id'],
                'data_type': data_type,
                'is_multi': is_multi,
                'values': values
            }
            return super().create(data)        

        def get(self, name, type):            
            params =  {'type': type}
            fields = self.list(url, params)
            return next((
                x for x in fields if x['name'] == name), 
                None)

    class CustomFieldGroup(CashCtrl):
        url = 'customfield/group/'
        actions = ['list']
        
        def create(self, name, type):            
            ''' e.g. name = {values: {'de': 'Test'} 
                     type = type='ACCOUNT'}
            '''
            data = {
                'name': name, 
                'type': type
            }
            return super().create(data)

        def get(self, name, type):            
            params =  {'type': type}
            groups = self.list(url, params)
            return next((
                x for x in groups if x['name'] == name),
                None)

    class Rounding(CashCtrl):
        url = 'rounding/'
        actions = ['list']

    class SequenceNumber(CashCtrl):
        url = 'sequencenumber/'
        actions = ['list']

    class Tax(CashCtrl):
        url = 'tax/'
        actions = ['list']

    class Text(CashCtrl):
        url = 'text/'
        actions = ['list']
        params = {'type': 'ORDER_ITEM'}

    # Meta
    class FiscalPeriod(CashCtrl):
        url = 'fiscalperiod/'
        actions = ['list']

    class Location(CashCtrl):
        url = 'location/'
        actions = ['list', 'create']

    class Setting(CashCtrl):
        url = 'setting/'
        actions = ['read']

    # File
    class File(CashCtrl):
        url = 'file/'
        actions = ['list']

    class FileCategory(CashCtrl):
        url = 'file/category/'
        actions = ['list']

    # Account
    class Account(CashCtrl):
        url = 'account/'
        actions = ['list']

    class AccountCategory(CashCtrl):
        url = 'account/category/'
        actions = ['list', 'create']
        
        def _check_not_None(self):
            if self.data is None:
                raise Exception("data is None")            
        
        def _validate(self, data):
            if 'name' not in data:
                raise Exception("'name' missing in data")
            if 'number' not in data:
                raise Exception("'number' missing in data")
            if 'parent_id' not in data:
                raise Exception("'parent_id' missing in data")
                
        def create(self, data):
            self._validate(data)
            return super().create(data)                
                
        def top_categories(self):
            '''return top categories from self.data
                'ASSET', 'LIABILITY', 'EXPENSE', 'REVENUE' and 'BALANCE'
            '''
            self._check_not_None()
            
            return {
                x['account_class']: x 
                for x in self.data 
                if not x['parent_id']
            }        
            
        def leaves(self):
            """
            Returns all leaf nodes from the provided data_list.
            A leaf node is defined as a node where no other node has `parent_id` equal to its `id`.
            
            Args:
                data_list (list): A list of dictionaries, each representing a node.

            Returns:
                list: A list of dictionaries representing the leaf nodes.
            """
            # Init
            data_list = self.data
            
            # Extract all ids that are referenced as parent_id
            parent_ids = {
                item['parent_id'] 
                for item in data_list 
                if item['parent_id'] is not None
            }
            
            # Find all nodes whose id is not in the set of parent_ids
            leaves = [
                item for item in data_list 
                if item['id'] not in parent_ids
            ]
            
            return leaves

    class AccountCostCenter(CashCtrl):
        url = 'account/costcenter/'
        actions = ['list']
     
    # Inventory
    class Article(CashCtrl):
        url = 'inventory/article/'
        actions = ['list']

    class ArticleCategory(CashCtrl):
        url = 'inventory/article/category/'
        actions = ['list']

    class Asset(CashCtrl):
        url = 'inventory/asset/'
        actions = ['list']

    class AssetCategory(CashCtrl):
        url = 'inventory/asset/category/'
        actions = ['list']

    class Unit(CashCtrl):
        url = 'inventory/unit/'
        actions = ['list', 'create']

    # Orders
    class Order(CashCtrl):
        url = 'order/'
        actions = ['list']

    class OrderBookEntry(CashCtrl):
        url = 'order/bookentry/'
        actions = ['list']  # not working ever used?

    class OrderCategory(CashCtrl):
        url = 'order/category/'
        actions = ['list']

    class Document(CashCtrl):
        url = 'order/document/'
        actions = ['read']  # The ID of the order.

    class Template(CashCtrl):
        url = 'order/template/'
        actions = ['read']  # The ID of the entry.

    # Person
    class Person(CashCtrl):
        url = 'person/'
        actions = ['list']

    class PersonCategory(CashCtrl):
        url = 'person/category/'
        actions = ['list']

    class PersonTitle(CashCtrl):
        url = 'person/title/'
        actions = ['list']

# main
if __name__ == "__main__":
    org = 'bdo'
    key = 'cp5H9PTjjROadtnHso21Yt6Flt9s0M4P'
    params =  {}
    
    ctrl = API.Account(org, key)
    data = ctrl.list()
    print(data, "\n")

    """     
    ctrl = API.AccountCategory(org, key)
    categories = ctrl.list()
    top_categories = ctrl.top_categories()
    
    leaves = ctrl.leaves()
    print("*leaves\n\n\n")
    for leave in leaves:
        if leave is None:
            print("*")
            continue
        print("*", leave['name'])
    

    ids = [109, 110]
    response = ctrl.delete(API.account_category.value['url'], *ids)
    print("*response", response)   
        
    articles = ctrl.list(API.Article.url)
    print("article", articles)


    for api in API:
        print(api.name)
        for action in api.value['actions']:
            def_ = getattr(ctrl, action)
            params =  api.value.get('params', {})
            response = def_(api.value['url'], params)
            print(response, "\n")




    ctrl = API.AccountCategory(org, key)
    top_categories = ctrl.get_top()
    print("*top_categories", top_categories)
    
    # add P&L
    ACCOUNT_CATEGORIES = {
        'P&L':{
            'de': 'Erfolgsrechnung', 
            'en': 'P&L', 
            'fr': 'Compte de résultat', 
            'it': 'Conto economico'
        },        
        'IS': {  
            'de': 'Investitionsrechnung',
            'en': 'Investment Statement',
            'fr': 'Compte d’investissement',
            'it': 'Conto degli investimenti'
        }
    }
        
    for category in ['EXPENSE', 'REVENUE']:
        for number, name in enumerate(ACCOUNT_CATEGORIES.values(), start=1):
            data = {
                'name': {'values': name},
                'number': number,
                'parent_id': top_categories[category]['id']
            }
            response = ctrl.create(data)
            print("*response", response)
    
    ""|   
    ctrl = API.Account(org, key)
    accounts = ctrl.list()
    top_accounts = [x for x in accounts if not x['category_id']]
    print("*account", len(accounts), top_accounts, "\n")
    print("*account last key", accounts[-1].keys(), "\n")

    fiscal_periods = ctrl.list(API.fiscalperiod.value['url'])
    fiscal_period = next(x for x in fiscal_periods if x['is_current'] is True)
    print(fiscal_period, "\n")

    params={
        'fiscalPeriodId': fiscal_period['id'],
        # not working: 'filter': [{'comparison': 'eq', 'field': 'createdBy', 'value': 'SYSTEM4'}]
        'filter': json.dumps([{'comparison': 'eq', 'field': 'categoryId', 'value': 109}])
    }
    accounts_1 = ctrl.list(API.account.value['url'], params=params)

    params={
        'fiscalPeriodId': fiscal_period['id'],
        # not working: 'filter': [{'comparison': 'eq', 'field': 'createdBy', 'value': 'SYSTEM4'}]
        'filter': json.dumps([{'comparison': 'eq', 'field': 'categoryId', 'value': 110}])
    }
    accounts_2 = ctrl.list(API.account.value['url'], params=params)
    accounts = accounts_1 + accounts_2

    ids = [x['id'] for x in accounts]
    print(len(accounts), accounts, ids, "\n")


    # Store custom field group
    data = {
        'name': {'values': {'de': 'Custom Test A'}},
        'type': FIELD_TYPE.ACCOUNT.value
    }
    customfield_group = ctrl.create(API.customfield_group.value['url'], data)
    print("*customfield_group", customfield_group)

    # Store custom field
    group_id = customfield_group['insert_id']
    data = {
        'data_type': DATA_TYPE.TEXT.value,
        'name': {'values': {'de': 'Field Test A'}},
        'type': FIELD_TYPE.ACCOUNT.value,
        'group_id': group_id,
    }
    customfield = ctrl.create(API.customfield.value['url'], data)
    print("*customfield", customfield)


    # Get all information of custom field
    field_id = customfield['insert_id']
    params =  {
        'id': field_id
    }
    customfield = ctrl.read(API.customfield.value['url'], params)
    print("*customfield", customfield)
    variable = customfield['variable']

    # Read accounts
    accounts = ctrl.list(API.account.value['url'])
    account = next(x for x in accounts if x['number'] == '102604210.01')
    print("*account", account, "\n")

    # Update account
    id = account['id']
    account['custom']['values']['customField59'] = 'Test Content A'
    account['target_min'] = 1000.0
    account = ctrl.update(API.account.value['url'], account)
    print("*account", account, "\n")


    # Make custom fields

    # Create Groups
    for group in CUSTOM_FIELD_GROUPS:
        group['type'] = group['type'].value
        customfield_group = ctrl.create(API.customfield_group.value['url'], group)
        group['id'] = customfield_group['insert_id']
        print("group['id']", group['id'])

    # Create Fields
    for field in CUSTOM_FIELDS:
        field['type'] = field['type'].value
        field['data_type'] = field['data_type'].value
        field['group_id'] = next(
            x['id'] for x in CUSTOM_FIELD_GROUPS
            if x['type'] == field['type'])
        if field.get('values'):
            field['values'] = json.dumps(field['values'])
        customfield = ctrl.create(API.customfield.value['url'], field)
        print("*customfield", customfield)


    files = ctrl.list(API.file.value['url'])
    print("*", files)
    '''

    # init cashctrl

    """