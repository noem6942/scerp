'''
accounting/api_cash_ctrl.py

central file for communication to cash ctrl
'''
from datetime import datetime
from enum import Enum
import json
import re
import requests
import xmltodict


DECODE = 'utf-8'


# mixins, we change right at down and uploading of data
def camel_to_snake(name):
    ''' we don't use cashCtrl camel field names '''
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def snake_to_camel(snake_str):
    ''' we don't use cashCtrl camel field names '''
    components = snake_str.split('_')
    camel_case_str = ''.join(x.title() for x in components)

    # ensure the first letter is lowercase and return
    return camel_case_str[0].lower() + camel_case_str[1:]


def create_enum(name, items):
    ''' see COUNTRY '''
    return Enum(name, {item: item for item in items})


# class COUNTRY
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
COUNTRY = create_enum('COUNTRY', sorted(COUNTRY_CODES))

# pylint: disable=invalid-name
class ADDRESS_TYPE(Enum):
    '''see public api desc'''
    MAIN = 'MAIN'
    INVOICE = 'INVOICE'
    DELIVERY = 'DELIVERY'
    OTHER = 'OTHER'


# pylint: disable=invalid-name
class DATA_TYPE(Enum):
    '''see public api desc'''
    TEXT = 'TEXT'
    TEXTAREA = 'TEXTAREA'
    CHECKBOX = 'CHECKBOX'
    DATE = 'DATE'
    COMBOBOX = 'COMBOBOX'
    NUMBER = 'NUMBER'
    ACCOUNT = 'ACCOUNT'
    PERSON = 'PERSON'


# pylint: disable=invalid-name
class ELEMENT_TYPE(Enum):
    '''see public api desc'''
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


# pylint: disable=invalid-name
class FIELD_TYPE(Enum):
    '''see public api desc'''
    JOURNAL = 'JOURNAL'
    ACCOUNT = 'ACCOUNT'
    INVENTORY_ARTICLE = 'INVENTORY_ARTICLE'
    INVENTORY_ASSET = 'INVENTORY_ASSET'
    ORDER = 'ORDER'
    PERSON = 'PERSON'
    FILE = 'FILE'


# pylint: disable=invalid-name
class GENDER(Enum):
    '''see public api desc'''
    FEMALE = 'FEMALE'
    MALE = 'MALE'


# pylint: disable=invalid-name
class ACCOUNT_CATEGORY_TYPE(Enum):
    '''Used for cashctrl, see public api desc'''
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
    ''' Report, not implemented yet
    '''
    report = {'url': 'report/', 'actions': ['tree']}
    element = {'url': 'element/', 'actions': ['tree']}
    set = {'url': 'set/', 'actions': ['read']}


class CashCtrl():
    ''' Base Class with many children
    '''
    BASE = "https://{org}.cashctrl.com/api/v1/{url}{action}.json"

    def __init__(self, org, api_key):
        self.org = org
        self.api_key = api_key
        self.auth = (api_key, '')
        self.data = None  # data can be loaded (list, read) or posted

    def url(self):
        ''' defined in child class '''
        return getattr(self, 'url')

    @staticmethod
    def str_to_dt(dt_string):
        '''Convert to a datetime object
            dt_string = '2024-10-14 09:58:33.0'
        '''
        return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S.%f')

    # Xml <-> JSON
    @staticmethod
    def clean_value(value):
        ''' use cashctrl <values> xml '''
        if isinstance(value, str) and value.startswith('<values>'):
            # XML
            return xmltodict.parse(value)
        # Return original value
        return value

    @staticmethod
    def value_to_xml(value):
        ''' use cashctrl <values> xml '''
        # Check if value is a dictionary
        if isinstance(value, dict) and 'values' in value:
            xmlstr = xmltodict.unparse(value['values'], full_document=False)
            return '<values>' + xmlstr + '</values>'
        # Return original value
        return value

    def clean_dict(self, data):
        ''' convert cashctrl data '''
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
    def get(self, url, params, timeout=10):
        '''
        Get from cash_ctrl with timeout handling.
        '''
        try:
            response = requests.get(url, params=params, auth=self.auth, timeout=timeout)
            if response.status_code != 200:
                # Decode the content and include it in the error message
                content = getattr(response, '_content', None)
                error_message = content.decode(DECODE) if content else ''
                raise Exception(
                    f"Get request failed with status {response.status_code}. "
                    f"Error message: {error_message}"
                )
            return response
        except requests.exceptions.Timeout:
            raise Exception(f"Request to {url} timed out after {timeout} seconds.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"An error occurred during the request: {e}")

    def post(self, url, data=None, timeout=10):
        '''
        Post to cash_ctrl with timeout handling.
        '''
        # Load data from self.data if not given
        if data is None:
            data = self.data

        # Check
        if not isinstance(data, dict):
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

        try:
            # Post data
            response = requests.post(
                url, data=post_data, auth=self.auth, timeout=timeout)
            if response.status_code != 200:
                # Decode the content and include it in the error message
                error_message = response.content.decode(DECODE)
                raise Exception(
                    f"Post request failed with status {response.status_code}. "
                    f"Error message: {error_message}"
                )
            if not response.json().get('success', True):
                # Decode the content and include it in the error message
                error_message = response.content.decode(DECODE)
                raise Exception(
                    f"Post request failed with 'success': False. "
                    f"Error message: {error_message}"
                )
            return self.clean_dict(response.json())
        except requests.exceptions.Timeout:
            raise Exception(
                f"Post request to {url} timed out after {timeout} seconds.")
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"An error occurred during the post request: {e}")

    # REST API mine: list, read, create, update, delete
    def list(self, params=None, **filter_kwargs):
        ''' cash_ctrl list '''
        if params is None:
            params = {}  # Initialize the dictionary only when needed
        if filter_kwargs:
            # e.g. categoryId=110,  camelCase!
            filters = []
            for key, value in filter_kwargs.items():
                filters.append(
                    {'comparison': 'eq', 'field': key, 'value': value})
            params['filter'] = json.dumps(filters)

        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='list')
        response = self.get(url, params)
        self.data = [self.clean_dict(x) for x in response.json()['data']]
        return self.data

    def read(self, params=None):
        ''' cash_ctrl read '''
        # Get data
        if params is None:
            params = {}  # Initialize the dictionary only when needed
        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='read')
        response = self.get(url, params)
        content = getattr(response, '_content', None)

        # Return content
        if content:
            self.data = self.clean_dict(json.loads(content.decode(DECODE)))
            return self.data
        raise Exception("response has no _content ")

    def create(self, data=None):
        ''' cash_ctrl create '''
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='create')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': 'Custom field saved', 'insert_id': 58}

    def update(self, data=None):
        ''' cash_ctrl update '''
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='update')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': 'Account saved', 'insert_id': 183}

    def delete(self, *ids):
        ''' cash_ctrl delete '''
        data = {'ids': ','.join([str(id) for id in ids])}
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='delete')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': '1 account deleted'}


# Element Classes
# Common
class Currency(CashCtrl):
    '''see public api desc'''
    url = 'currency/'
    actions = ['list']

class CurrencyLower(CashCtrl):
    '''see public api desc'''
    url = 'currency/'
    actions = ['list']

class CustomFieldGroup(CashCtrl):
    '''see public api desc'''
    url = 'customfield/group/'
    actions = ['list']

    def get_from_name(self, name, cash_ctrl_type):
        params =  {'type': cash_ctrl_type}
        groups = self.list(params)
        return next((x for x in groups if x['name'] == name), None)

class CustomField(CashCtrl):
    '''see public api desc'''
    url = 'customfield/'
    actions = ['list', 'create']

    def create_from_group(self, name, group, data_type, **kwargs):
        '''is_multi = True not tested yet
            group has type and name
        '''
        # Init
        is_multi = kwargs.get('is_multi', False)
        values = kwargs.get('values', [])
        c_type = group['type']

        # Get
        group_obj = CustomFieldGroup(self.org, self.api_key)
        group_data = group_obj.get(group['name'], c_type)
        if not group_data:
            raise Exception(f"Group name '{group}' not found.")

        data = {
            'name': name,
            'type': c_type,
            'group_id': group_data['id'],
            'data_type': data_type,
            'is_multi': is_multi,
            'values': values
        }
        return super().create(data)

    def get_from_name(self, name, c_type):
        '''name: dict, c_type: str
        '''
        params =  {'type': c_type}
        fields = self.list(params)
        return next((
            x for x in fields if x['name'] == name),
            None)

class Rounding(CashCtrl):
    '''see public api desc'''
    url = 'rounding/'
    actions = ['list']

class SequenceNumber(CashCtrl):
    '''see public api desc'''
    url = 'sequencenumber/'
    actions = ['list']

class Tax(CashCtrl):
    '''see public api desc'''
    url = 'tax/'
    actions = ['list']

class Text(CashCtrl):
    '''see public api desc'''
    url = 'text/'
    actions = ['list']
    params = {'type': 'ORDER_ITEM'}

# Meta
class FiscalPeriod(CashCtrl):
    '''see public api desc'''
    url = 'fiscalperiod/'
    actions = ['list']

class Location(CashCtrl):
    '''see public api desc'''
    url = 'location/'
    actions = ['list', 'create']

class Setting(CashCtrl):
    '''see public api desc'''
    url = 'setting/'
    actions = ['read']

# File
class File(CashCtrl):
    '''see public api desc'''
    url = 'file/'
    actions = ['list']

class FileCategory(CashCtrl):
    '''see public api desc'''
    url = 'file/category/'
    actions = ['list']

# Account
class Account(CashCtrl):
    '''see public api desc'''
    url = 'account/'
    actions = ['list']

class AccountCategory(CashCtrl):
    '''see public api desc'''
    url = 'account/category/'
    actions = ['list', 'create']

    def create(self, data=None):
        if 'name' not in data:
            raise Exception("'name' missing in data")
        if 'number' not in data:
            raise Exception("'number' missing in data")
        if 'parent_id' not in data:
            raise Exception("'parent_id' missing in data")
        return super().create(data)

    def top_categories(self):
        '''return top categories from self.data
            'ASSET', 'LIABILITY', 'EXPENSE', 'REVENUE' and 'BALANCE'
        '''
        if self.data is None:
            raise Exception("data is None")

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
    '''see public api desc'''
    url = 'account/costcenter/'
    actions = ['list']

# Inventory
class Article(CashCtrl):
    '''see public api desc'''
    url = 'inventory/article/'
    actions = ['list']

class ArticleCategory(CashCtrl):
    '''see public api desc'''
    url = 'inventory/article/category/'
    actions = ['list']

class Asset(CashCtrl):
    '''see public api desc'''
    url = 'inventory/asset/'
    actions = ['list']

class AssetCategory(CashCtrl):
    '''see public api desc'''
    url = 'inventory/asset/category/'
    actions = ['list']

class Unit(CashCtrl):
    '''see public api desc'''
    url = 'inventory/unit/'
    actions = ['list', 'create']

# Orders
class Order(CashCtrl):
    '''see public api desc'''
    url = 'order/'
    actions = ['list']

class OrderBookEntry(CashCtrl):
    '''see public api desc'''
    url = 'order/bookentry/'
    actions = ['list']  # not working ever used?

class OrderCategory(CashCtrl):
    '''see public api desc'''
    url = 'order/category/'
    actions = ['list']

class Document(CashCtrl):
    '''see public api desc'''
    url = 'order/document/'
    actions = ['read']  # The ID of the order.

class Template(CashCtrl):
    '''see public api desc'''
    url = 'order/template/'
    actions = ['read']  # The ID of the entry.

# Person
class Person(CashCtrl):
    '''see public api desc'''
    url = 'person/'
    actions = ['list']

class PersonCategory(CashCtrl):
    '''see public api desc'''
    url = 'person/category/'
    actions = ['list']

class PersonTitle(CashCtrl):
    '''see public api desc'''
    url = 'person/title/'
    actions = ['list']

# main
if __name__ == "__main__":
    ORG = 'bdo'
    KEY = 'cp5H9PTjjROadtnHso21Yt6Flt9s0M4P'
    PARAMS =  {}

    ctrl = Account(ORG, KEY)
    data_ = ctrl.list()
    print(data_, "\n")

    """
    ctrl = AccountCategory(org, key)
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
    response = ctrl.delete(account_category.value['url'], *ids)
    print("*response", response)

    articles = ctrl.list(Article.url)
    print("article", articles)


    for api in API:
        print(api.name)
        for action in api.value['actions']:
            def_ = getattr(ctrl, action)
            params =  api.value.get('params', {})
            response = def_(api.value['url'], params)
            print(response, "\n")




    ctrl = AccountCategory(org, key)
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
    ctrl = Account(org, key)
    accounts = ctrl.list()
    top_accounts = [x for x in accounts if not x['category_id']]
    print("*account", len(accounts), top_accounts, "\n")
    print("*account last key", accounts[-1].keys(), "\n")

    fiscal_periods = ctrl.list(fiscalperiod.value['url'])
    fiscal_period = next(x for x in fiscal_periods if x['is_current'] is True)
    print(fiscal_period, "\n")

    params={
        'fiscalPeriodId': fiscal_period['id'],
        # not working: 'filter': [{'comparison': 'eq', 'field': 'createdBy', 'value': 'SYSTEM4'}]
        'filter': json.dumps([{'comparison': 'eq', 'field': 'categoryId', 'value': 109}])
    }
    accounts_1 = ctrl.list(account.value['url'], params=params)

    params={
        'fiscalPeriodId': fiscal_period['id'],
        # not working: 'filter': [{'comparison': 'eq', 'field': 'createdBy', 'value': 'SYSTEM4'}]
        'filter': json.dumps([{'comparison': 'eq', 'field': 'categoryId', 'value': 110}])
    }
    accounts_2 = ctrl.list(account.value['url'], params=params)
    accounts = accounts_1 + accounts_2

    ids = [x['id'] for x in accounts]
    print(len(accounts), accounts, ids, "\n")


    # Store custom field group
    data = {
        'name': {'values': {'de': 'Custom Test A'}},
        'type': FIELD_TYPE.ACCOUNT.value
    }
    customfield_group = ctrl.create(customfield_group.value['url'], data)
    print("*customfield_group", customfield_group)

    # Store custom field
    group_id = customfield_group['insert_id']
    data = {
        'data_type': DATA_TYPE.TEXT.value,
        'name': {'values': {'de': 'Field Test A'}},
        'type': FIELD_TYPE.ACCOUNT.value,
        'group_id': group_id,
    }
    customfield = ctrl.create(customfield.value['url'], data)
    print("*customfield", customfield)


    # Get all information of custom field
    field_id = customfield['insert_id']
    params =  {
        'id': field_id
    }
    customfield = ctrl.read(customfield.value['url'], params)
    print("*customfield", customfield)
    variable = customfield['variable']

    # Read accounts
    accounts = ctrl.list(account.value['url'])
    account = next(x for x in accounts if x['number'] == '102604210.01')
    print("*account", account, "\n")

    # Update account
    id = account['id']
    account['custom']['values']['customField59'] = 'Test Content A'
    account['target_min'] = 1000.0
    account = ctrl.update(account.value['url'], account)
    print("*account", account, "\n")


    # Make custom fields

    # Create Groups
    for group in CUSTOM_FIELD_GROUPS:
        group['type'] = group['type'].value
        customfield_group = ctrl.create(customfield_group.value['url'], group)
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
        customfield = ctrl.create(customfield.value['url'], field)
        print("*customfield", customfield)


    files = ctrl.list(file.value['url'])
    print("*", files)
    '''

    # init cashctrl

    """
