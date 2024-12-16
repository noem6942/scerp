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


class API:
    # Common
    class Currency:
        url = 'currency/'
        actions = ['list']

    class CurrencyLower:
        url = 'currency/'
        actions = ['list']

    class CustomField:
        url = 'customfield/'
        actions = ['list', 'create']
        params = {'type': 'ACCOUNT'}

    class CustomFieldGroup:
        url = 'customfield/group/'
        actions = ['list']
        params = {'type': 'ACCOUNT'}

    class Rounding:
        url = 'rounding/'
        actions = ['list']

    class SequenceNumber:
        url = 'sequencenumber/'
        actions = ['list']

    class Tax:
        url = 'tax/'
        actions = ['list']

    class Text:
        url = 'text/'
        actions = ['list']
        params = {'type': 'ORDER_ITEM'}

    # Meta
    class FiscalPeriod:
        url = 'fiscalperiod/'
        actions = ['list']

    class Location:
        url = 'location/'
        actions = ['list', 'create']

    class Setting:
        url = 'setting/'
        actions = ['read']

    # File
    class File:
        url = 'file/'
        actions = ['list']

    class FileCategory:
        url = 'file/category/'
        actions = ['list']

    # Account
    class Account:
        url = 'account/'
        actions = ['list']

    class AccountCategory:
        url = 'account/category/'
        actions = ['list']

    class AccountCostCenter:
        url = 'account/costcenter/'
        actions = ['list']
     
    # Inventory
    class Article:
        url = 'inventory/article/'
        actions = ['list']

    class ArticleCategory:
        url = 'inventory/article/category/'
        actions = ['list']

    class Asset:
        url = 'inventory/asset/'
        actions = ['list']

    class AssetCategory:
        url = 'inventory/asset/category/'
        actions = ['list']

    class Unit:
        url = 'inventory/unit/'
        actions = ['list']

    # Orders
    class Order:
        url = 'order/'
        actions = ['list']

    class OrderBookEntry:
        url = 'order/bookentry/'
        actions = ['list']  # not working ever used?

    class OrderCategory:
        url = 'order/category/'
        actions = ['list']

    class Document:
        url = 'order/document/'
        actions = ['read']  # The ID of the order.

    class Template:
        url = 'order/template/'
        actions = ['read']  # The ID of the entry.

    # Person
    class Person:
        url = 'person/'
        actions = ['list']

    class PersonCategory:
        url = 'person/category/'
        actions = ['list']

    class PersonTitle:
        url = 'person/title/'
        actions = ['list']



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

    # REST API
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

    def post(self, url, data):
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

    def list(self, url, params={}, **filter):
        if filter:
            # e.g. categoryId=110,  camelCase!
            filters = []
            for key, value in filters.items():
                filters.append(
                    {'comparison': 'eq', 'field': key, 'value': value})
            params['filter'] = json.dumps(filters)

        url = self.BASE.format(
            org=self.org, url=url, params=params, action='list')
        response = self.get(url, params)
        return [self.clean_dict(x) for x in response.json()['data']]

    def read(self, url, params={}):
        url = self.BASE.format(
            org=self.org, url=url, params=params, action='read')
        response = self.get(url, params)
        return self.clean_dict(json.loads(response._content.decode(DECODE)))

    def delete(self, url, *ids):
        url = self.BASE.format(
            org=self.org, url=url, params=params, action='delete')
        data = {'ids': ','.join([str(id) for id in ids])}
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': '1 account deleted'}

    def create(self, url, data):
        url = self.BASE.format(
            org=self.org, url=url, data=data, action='create')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': 'Custom field saved', 'insert_id': 58}

    def update(self, url, data):
        url = self.BASE.format(
            org=self.org, url=url, data=data, action='update')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': 'Account saved', 'insert_id': 183}

    # Customized Actions
    def create_customfield_group(self, name, type):
        url = API.CustomFieldGroup.url
        data = {'name': name, 'type': type}
        return self.create(url, data)

    def get_customfield_group(self, name, type):
        url = API.CustomFieldGroup.url
        params =  {'type': type}
        groups = self.list(url, params)

        return next((x for x in groups if x['name'] == name), None)

    def create_customfield(
            self, name, group, data_type, is_multi=False, values=[]):
        '''is_multi = True not tested yet
        '''
        url = API.CustomField.url
        type = group['type']
        group = self.get_customfield_group(group['name'], type)
        if not group:
            raise Exception(f"Group name '{group}' not found.")

        data = {
            'name': name,
            'type': type,
            'group_id': group['id'],
            'data_type': data_type,
            'is_multi': is_multi,
            'values': values
        }
        return self.create(url, data)

    def get_customfield(self, name, type):
        url = API.CustomField.url
        params =  {'type': type}
        fields = self.list(url, params)
        return next((x for x in fields if x['name'] == name), None)


# main
if __name__ == "__main__":
    org = 'bdo'
    key = 'cp5H9PTjjROadtnHso21Yt6Flt9s0M4P'
    params =  {}
    ctrl = CashCtrl(org, key)

    articles = ctrl.list(API.Article.url)
    print("article", articles)

    """
    for api in API:
        print(api.name)
        for action in api.value['actions']:
            def_ = getattr(ctrl, action)
            params =  api.value.get('params', {})
            response = def_(api.value['url'], params)
            print(response, "\n")


    setting = ctrl.read(API.setting.value['url'])
    print(setting, "\n")

    account = ctrl.list(API.account.value['url'])
    print("*account", len(account), account[-2:], "\n")
    print("*account last key", account[-1].keys(), "\n")
    '''

    account_category = ctrl.list(API.account_category.value['url'])
    top_accounts = [x for x in account_category if x['parent_id'] is None]
    for accounts in top_accounts:
        print(accounts['id'], accounts['account_class'])

    '''
    ids = [109, 110]
    response = ctrl.delete(API.account_category.value['url'], *ids)
    print("*response", response)


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