'''
accounting/api_cash_ctrl.py

central file for communication to cash ctrl
'''
from datetime import datetime
from decimal import Decimal
from enum import Enum
from time import sleep

import json
import logging
import mimetypes
import os
import pytz
import re
import requests
import xmltodict


DECODE = 'utf-8'
TIMEZONE = pytz.timezone('Europe/Zurich')
URL_ROOT = "https://{org}.cashctrl.com"


# Standard Accounts
"""
Standard account definitions with descriptive English names, numeric codes,
and German descriptions as comments.
"""
class STANDARD_ACCOUNT(Enum):
    # settings
    OPENING_BALANCE = 9100  # Eröffnungsbilanz
    EXCHANGE_DIFFERENCES = 6960  # Kursdifferenzen
    ANNUAL_PROFIT_OR_LOSS = 9200  # Jahresgewinn oder -verlust
    TRADING_INCOME = 3200  # Handelsertrag
    COST_OF_GOODS_SOLD = 4200  # Warenaufwand
    DEPRECIATION = 6800  # Abschreibungen
    ASSET_DISPOSALS = 6801  # Anlagenabgänge
    REVENUE_FROM_MOBILE_ASSETS = 7900  # Ertrag Mobile Sachanlagen
    RECEIVABLES = 1100  # Debitoren
    PAYABLES = 2000  # Kreditoren
    VAT_RECONCILIATION = 2202  # Umsatzsteuerausgleich Abrechnungsmethode
    INPUT_TAX_RECONCILIATION = 1172  # Vorsteuerausgleich Abrechnungsmethode

    # not directly in settings
    PRAE_TAX = 1170  # Vorsteuer
    REVENUE_TAX = 2200  # Umsatzsteuer
    SERVICE_REVENUE = 3400  # Dienstleistungsertrag
    ROUNDING = 6961  # Rundungsdifferenzen


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



'''
cashCtrl definitions:
    - we only use Enum if used for selection in django model choices
'''
class ACCOUNT_CATEGORY_ID:
    ''' id is integer, account number str '''
    ASSETS = 1
    LIABILITIES = 2
    EXPENSE = 3
    REVENUE = 4
    BALANCE = 5


class ADDRESS_TYPE:
    '''see public api desc'''
    MAIN = 'MAIN'
    INVOICE = 'INVOICE'
    DELIVERY = 'DELIVERY'
    OTHER = 'OTHER'


class BANK_ACCOUNT_TYPE:
    '''see public api desc'''
    DEFAULT = 'DEFAULT'
    ORDER = 'ORDER'
    SALARY = 'SALARY'
    HISTORICAL = 'HISTORICAL'
    OTHER = 'OTHER'


class CONTACT_TYPE:
    EMAIL_INVOICE = 'EMAIL_INVOICE'
    EMAIL_WORK = 'EMAIL_WORK'
    EMAIL_PRIVATE = 'EMAIL_PRIVATE'
    PHONE_RECEPTION = 'PHONE_RECEPTION'
    PHONE_WORK = 'PHONE_WORK'
    PHONE_PRIVATE = 'PHONE_PRIVATE'
    MOBILE_WORK = 'MOBILE_WORK'
    MOBILE_PRIVATE = 'MOBILE_PRIVATE'
    FAX = 'FAX'
    WEBSITE = 'WEBSITE'
    MESSENGER = 'MESSENGER'
    OTHER = 'OTHER'


class COLOR:
    BLUE = 'BLUE'
    GREEN = 'GREEN'
    RED = 'RED'
    YELLOW = 'YELLOW'
    ORANGE = 'ORANGE'
    BLACK = 'BLACK'
    GRAY = 'GRAY'
    BROWN = 'BROWN'
    VIOLET = 'VIOLET'
    PINK = 'PINK'


class BOOK_TYPE:
    CREDIT = 'CREDIT'
    DEBIT = 'DEBIT'


class CALCULATION_BASE:
    NET = 'NET'
    GROSS = 'GROSS'


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


class FISCAL_PERIOD_TYPE(Enum):
    '''see public api desc'''
    EARLIEST = 'EARLIEST'
    LATEST = 'LATEST'


class PERSON_CATEGORY(Enum):
    CUSTOMER = 1
    VENDOR = 2
    EMPLOYER = 3
    INSURANCE = 8


class ROUNDING(Enum):
    '''Modes for rounding behavior'''
    UP = 'UP'
    DOWN = 'DOWN'
    CEILING = 'CEILING'
    FLOOR = 'FLOOR'
    HALF_UP = 'HALF_UP'
    HALF_DOWN = 'HALF_DOWN'
    HALF_EVEN = 'HALF_EVEN'
    UNNECESSARY = 'UNNECESSARY'


class TEXT_TYPE(Enum):
    '''Types for Text'''
    ORDER_HEADER = 'ORDER_HEADER'
    ORDER_FOOTER = 'ORDER_FOOTER'
    ORDER_MAIL = 'ORDER_MAIL'
    ORDER_ITEM = 'ORDER_ITEM'


class TITLE(Enum):
    MR = 1  # Herr
    MRS = 2  # Frau


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


class FIELD_TYPE(Enum):
    '''see public api desc'''
    JOURNAL = 'JOURNAL'
    ACCOUNT = 'ACCOUNT'
    INVENTORY_ARTICLE = 'INVENTORY_ARTICLE'
    INVENTORY_ASSET = 'INVENTORY_ASSET'
    ORDER = 'ORDER'
    PERSON = 'PERSON'
    FILE = 'FILE'


class GENDER:
    '''see public api desc'''
    FEMALE = 'FEMALE'
    MALE = 'MALE'


class PERSON_TYPE:
    CLIENT = 1
    SUPPLIER = 2
    EMPLOYEE = 3


class ORDER_TYPE:
    '''see public api desc'''
    SALES = 'SALES'
    PURCHASE = 'PURCHASE'


# Helpers

# Conversions
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


def str_to_dt(dt_string, timezone):
    '''Convert to a datetime object
        dt_string = '2024-10-14 09:58:33.0'
    '''
    naive_dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S.%f')  # Naive datetime
    aware_dt = timezone.localize(naive_dt)
    return aware_dt


def slugify_filename(filename):
    """Converts a filename into a safe format."""
    filename = filename.lower()  # Convert to lowercase
    filename = re.sub(r'[^\w\s.-]', '', filename)  # Remove special characters except dot & hyphen
    # filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
    return filename


# Xml <-> JSON
def clean_value(value):
    ''' use cashctrl <values> xml and remove <values> '''
    if isinstance(value, str) and value.startswith('<values>'):
        try:
            # XML to dict
            # Skip 'values' if it exists, otherwise return the
            # original dictionary
            value_dict = xmltodict.parse(value)
            return value_dict.get('values', value_dict)
        except Exception as e:
            raise ValueError(f"{value}: Could not parse XML: {str(e)}")

    # Return original value
    return value


def convert_to_xml(value):
    '''
    Converts a dictionary into an XML-formatted string, where each key-value
    pair is wrapped in a single `<values>` tag.

    If the input `value` is a dictionary, the function iterates over each
    key-value pair, converts them into an XML string using
    `xmltodict.unparse`, and wraps the result in `<values>` tags.

    If the input `value` is not a dictionary, it is returned as-is.

    Args:
        value (dict or any): The input data to be converted to XML. If not a
            dictionary, it is returned unchanged.

    Returns:
        str or any: An XML-formatted string if the input is a dictionary, or
            the original value if it is not.

    Example:
        Input:
            value = {
                'de': 'Freund',
                'en': 'foo'
            }

        Output:
            "<values><de>Freund</de><en>foo</en></values>"
    '''
    # Check if value is a dictionary
    if isinstance(value, dict):
        value = dict(values=value)
        xmlstr = xmltodict.unparse(value['values'], full_document=False)
        return '<values>' + xmlstr + '</values>'
    elif isinstance(value, list):  # Now only checking for lists
        return json.dumps(value)

    # Return original value
    return value


def clean_dict(data, convert_dt=True, timezone=pytz.utc):
    ''' convert cashctrl data to python '''
    DATE_TIME_KEYS = (
        'created',  'last_updated', 'start', 'end',
        'salary_start', 'salary_end'
    )

    post_data = {}
    for key, value in data.items():
        key = camel_to_snake(key)
        if convert_dt and key in DATE_TIME_KEYS:
            try:
                value = str_to_dt(value, timezone)
            except:
                pass
        post_data[key] = clean_value(value)

    return post_data


def prepare_dict(data):
    ''' convert python data to cashctrl '''
    post_data = {}
    for key, value in data.items():
        camel_key = snake_to_camel(key)
        if camel_key in ('start', 'end'):
            value = value.strftime('%Y-%m-%d')
        elif isinstance(value, Decimal):
            value = float(value)
        else:
            value = convert_to_xml(value)
        post_data[camel_key] = value

    return post_data


class CashCtrl():
    '''
    Base Class with many children
    BASE: used for almost all queries
    BASE_DIR: used for queries not have not .json at end of url

    :org:  cashCtrl org
    :api_key:  cashCtrl api_key
    :language:  cashCtrl language - for api we always use 'en' if not
        explicitly declared otherwise
    :org:  cashCtrl org
    :org:  cashCtrl org
    '''
    BASE_DIR = URL_ROOT + "/api/v1/{url}{action}"
    BASE = BASE_DIR + '.json'  # default

    # Rate-limiting constants
    MAX_TRIES = 5  # Maximum number of retries
    SLEEP_DURATION = 2  # Sleep duration between retries in second

    def __init__(
            self, org, api_key, language='en', convert_dt=True,
            timezone=TIMEZONE):
        # Auth
        self.org = org
        self.api_key = api_key
        self.auth = (api_key, '')

        # Params
        self.language = language
        self.timezone = timezone
        self.convert_dt = convert_dt

        # Data
        self.data = None  # data can be loaded (list, read) or posted

    def url(self):
        ''' defined in child class '''
        return getattr(self, 'url')

    # REST API CashCtrl: post, get
    def get(self, url, params, timeout=10):
        '''
        Get from CashCtrl with timeout handling and rate-limiting retries.
        '''
        # Ensure language is always set
        if not params.get('language'):
            params['lang'] = self.language

        if params.get('filter'):
            params['filter'] = json.dumps(params['filter'])
        response = requests.get(
            url, params=params, auth=self.auth, timeout=timeout)

        for attempt in range(self.MAX_TRIES):
            try:
                response = requests.get(
                    url, params=params, auth=self.auth, timeout=timeout
                )

                if response.status_code == 429:
                    logging.info("GET rate limit hit. Retrying...")
                    sleep(self.SLEEP_DURATION)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.Timeout:
                raise Exception(f"GET attempt {attempt + 1}/{self.MAX_TRIES} timed out.")
            except requests.exceptions.RequestException as e:
                raise Exception(f"GET request error: {e}")

            if attempt < self.MAX_TRIES - 1:
                logging.info(f"Retrying GET request to {url} (Attempt {attempt + 2})...")
                sleep(self.SLEEP_DURATION)

        raise Exception(
            f"Maximum retry attempts ({self.MAX_TRIES}) reached for GET request to '{url}'."
        )


    def post(self, url, data=None, params={}, timeout=10):
        """
        Post to CashCtrl with timeout handling and rate-limiting retries.
        """
        # Add language
        if not params.get('language'):
            params['lang'] = self.language

        # Load data from self.data if not given
        if data is None:
            data = self.data

        # Check
        if not isinstance(data, dict):
            raise Exception(f"{data} is not of type dict")

        # Build data
        post_data = prepare_dict(data)

        # Retry mechanism for rate-limiting
        for attempt in range(self.MAX_TRIES):
            try:
                response = requests.post(
                    url, params=params, data=post_data,
                    auth=self.auth, timeout=timeout
                )

                if response.status_code == 429:  # Rate limit
                    logging.info("Rate limit reached. Retrying...")
                    sleep(self.SLEEP_DURATION)
                    continue

                if not response.ok:
                    raise Exception(
                        f"POST request failed for '{url}': "
                        f"{response.status_code} - {response.reason} "
                        f"{response.text}"
                    )

                content = response.json()
                if not content.get('success', False):
                    raise Exception(
                        f"POST request error in '{url}': {content['message']},"
                        f"{content.get('errors')}")

                # Clean and return response content
                return clean_dict(content, self.convert_dt, self.timezone)

            except requests.exceptions.Timeout:
                raise Exception(
                    f"Attempt {attempt + 1}/{self.MAX_TRIES} timed out.")
            except requests.exceptions.RequestException as e:
                raise Exception(
                    f"An error occurred during the POST request: {e}")

            # Sleep before retrying if it's not the last attempt
            if attempt < self.MAX_TRIES - 1:
                logging.info(
                    f"Retrying POST request to {url} "
                    f"(Attempt {attempt + 2})...")
                sleep(self.SLEEP_DURATION)

        # Raise an exception if all attempts fail
        raise Exception(
            f"Maximum retry attempts ({self.MAX_TRIES}) reached for POST "
            f"request to '{url}'."
        )

    # File management
    def upload_file(self, file_path):
        file_name = file_path.split('/')[-1]

        # Step 1: Determine the MIME type based on the file extension
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:  # If mime_type is None or not found, use a default
            mime_type = 'application/octet-stream'

        # Step 2: Prepare
        url = self.BASE.format(org=self.org, url=self.url, action='prepare')
        print("*mime_type", mime_type)

        files = json.dumps([{'name': file_name, 'mimeType': mime_type}])

        # Raise and process the response
        response = requests.post(
            url, auth=self.auth, files={'files': (None, files)})
        response_data = response.json()
        if not response_data.get('success'):
            raise Exception('Failed to prepare file upload')

        file_info = response_data['data'][0]
        file_id = file_info['fileId']
        write_url = file_info['writeUrl']

        # Step 2: Put (Upload the file)
        with open(file_path, 'rb') as f:
            put_response = requests.put(write_url, data=f)

        if put_response.status_code != 200:
            raise Exception('Failed to upload file')


        # Step 3: Persist
        persist_url = (
            f'https://{self.org}.cashctrl.com/api/v1/file/persist.json')
        persist_response = requests.post(
            persist_url, auth=self.auth, data={'ids': file_id})

        if not persist_response.json().get('success'):
            raise Exception('Failed to persist file')

        return file_id, file_name

    def download_file(self, file_id, output_path):
        # Read data to get name
        data = self.read(file_id)

        # Download
        params = {'id': file_id}
        url = self.BASE_DIR.format(
            org=self.org, url=self.url, action='get')
        response = requests.get(
            url, auth=self.auth, params=params, allow_redirects=True)

        if response.status_code == 200:
            # If output_path is a directory, use file_id as the filename
            if os.path.isdir(output_path):
                file_name = slugify_filename(data['name'])
                output_path = os.path.join(output_path,file_name)

            with open(output_path, 'wb') as f:
                f.write(response.content)
        else:
            raise Exception(f'Failed to download file: {response}')

    # REST API mine: list, read, create, update, delete, data
    def list(self, params={}):
        ''' cash_ctrl list '''
        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='list')
        response = self.get(url, params)
        self.data = [
            clean_dict(x, self.convert_dt, self.timezone)
            for x in response.json()['data']
        ]
        return self.data

    def read(self, id=None, params=None):
        """ Fetch a single entry by ID. """
        # Init params
        params = params or {}
        if id:
            params['id'] = id  # Ensure ID is included

        # Get
        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action="read")
        response = self.get(url, params)

        # Process
        if response.status_code == 200:
            data = response.json()
            if id:
                # default, only settings has no data
                if data.get('success', False):
                    data = data.get('data')
                else:
                    raise ValueError(data.get('errorMessage'))                    

            return clean_dict(data, self.convert_dt, self.timezone)

        return response

    def data_json(self, params={}):
        '''
        get json data, params keys in sentence letters (not camel!)
        see e.g. https://app.cashctrl.com/static/help/en/api/index.html#/report/element/data.json
        '''
        url = self.BASE.format(
            org=self.org, url=self.url, params=prepare_dict(params),
            action='data')
        response = self.get(url, params)
        self.data = [
            clean_dict(x, self.convert_dt, self.timezone)
            for x in response.json()['data']
        ]
        return self.data

    def tree_json(self, params={}):
        '''
        get json tree, params should be {}
        see e.g. https://app.cashctrl.com/static/help/en/api/index.html#/report
        '''
        url = self.BASE.format(
            org=self.org, url=self.url, params=params, action='tree')
        response = self.get(url, params)
        self.data = [
            clean_dict(x, self.convert_dt, self.timezone)
            for x in response.json()['data']
        ]
        return self.data


    def create(self, data=None, params={}):
        ''' cash_ctrl create '''
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='create')
        response = self.post(url, data=data, params=params)
        return response  # e.g. {'success': True, 'message': 'Custom field saved', 'insert_id': 58}

    def update(self, data=None, params={}):
        ''' cash_ctrl update '''
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='update')
        response = self.post(url, data=data, params={})
        return response  # e.g. {'success': True, 'message': 'Account saved', 'insert_id': 183}

    def delete(self, *ids, force=None):
        ''' cash_ctrl delete
            force is only used for File;
                if True file gets permanently deleted else it gets moved to the
                archive
        '''
        data = {'ids': ','.join([str(id) for id in ids])}
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='delete')
        response = self.post(url, data=data)
        return response  # e.g. {'success': True, 'message': '1 account deleted'}

    def attach_files(self, id, file_ids):
        '''
        Attach files with id file_ids to object id,
        see https://app.cashctrl.com/static/help/en/api/index.html#examples
        '''
        data = {
            "id": id,
            "file_ids": ",".join(map(str, file_ids))  # Convert list to comma-separated string
        }
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='update_attachments')
        response = self.post(url, data=data)
        return response

    def get_data(self, action='data.json', **params):
        '''
        get json data,
        e.g. see https://app.cashctrl.com/static/help/en/api/index.html#/report/element/data.json
        '''
        data = {
            "id": id,
            "file_ids": ",".join(map(str, file_ids))  # Convert list to comma-separated string
        }
        url = self.BASE.format(
            org=self.org, url=self.url, data=data, action='update_attachments')
        response = self.post(url, data=data)
        return response


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
    '''see public api desc
        CustomFieldGroup has no filter param --> get_from_name
    '''
    url = 'customfield/group/'
    actions = ['list']

    def get_from_name(self, name, cash_ctrl_type):
        params =  {'type': cash_ctrl_type}
        groups = self.list(params)
        return next((x for x in groups if x['name'] == name), None)

class CustomField(CashCtrl):
    '''see public api desc
        CustomField has no filter param --> get_from_name
    '''
    url = 'customfield/'
    actions = ['list', 'create']

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
    actions = ['list', 'switch']

    def set_as_current(id):
        pass  # currently not implemented

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

    def delete(self, file_id, archive=True):
        super().delete(file_id, force=not archive)

    def download(self, file_id, output_path):
        self.download_file(file_id, output_path)

    def upload(self, file_path, data={}):
        '''
            data: if not empty categorize file with category, name,
                description, notes, custom
        '''
        file_id, file_name = self.upload_file(file_path)
        if data:
            # Cataloge file
            data.update({
                'id': file_id,
                'name': data.pop('name', file_name)
            })
            self.create(data)

        return file_id, file_name

class FileCategory(CashCtrl):
    '''see public api desc'''
    url = 'file/category/'
    actions = ['list']

# Account
class Account(CashCtrl):
    '''see public api desc'''
    url = 'account/'
    actions = ['list']

    def get_balance(self, id, date=None):
        ''' cash_ctrl read '''
        # Get params
        params = {'id': id}
        if date:
            if not isinstance(date, str):
                date = date.strftime('%Y-%m-%d')
            params['date'] = date

        # Get data
        url = self.BASE_DIR.format(
            org=self.org, url=self.url, params=params, action='balance')
        response = self.get(url, params)
        return float(response.json())

    @property
    def standard_account(self):
        '''return dict with top accounts from self.data
        '''
        if self.data is None:
            raise Exception("data is None")

        standard_accounts = [x.value for x in STANDARD_ACCOUNT]
        return {
            x['number']: x
            for x in self.data
            if x['number'] in standard_accounts
        }


class AccountBankAccount(CashCtrl):
    '''see public api desc'''
    url = 'account/bank/'
    actions = ['list', 'create']


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

    @property
    def top_category(self):
        '''return dict with top categories from self.data
            'ASSET', 'LIABILITY', 'EXPENSE', 'REVENUE' and 'BALANCE'
        '''
        if self.data is None:
            raise Exception("data is None")

        return {
            x['account_class']: x
            for x in self.data
            if not x['parent_id']
        }

    def get_leaves(self):
        """
        Returns all leaf nodes from the provided data_list.
        A leaf node is defined as a node where no other node has `parent_id` equal to its `id`.

        Args:
            data_list (list): A list of dictionaries, each representing a node.

        Returns:
            list: A list of dictionaries representing the leaf nodes.
        """
        # Init
        data_list = list(self.data)

        # Extract all ids that are referenced as parent_id
        parent_ids = {
            item['parent_id']
            for item in data_list
            if item['parent_id'] is not None
        }

        '''
        # Extract all ids that are referenced as parent_id
        acc = Account(self.org, self.api_key)
        accounts = acc.list()
        parent_ids_acc = {
            item['parent_id']
            for item in accounts
            if item['parent_id'] is not None
        }

        # union
        all_parent_ids = parent_ids.union(parent_ids_acc)
        '''

        # Find all nodes whose id is not in the set of parent_ids
        leaves = [
            item for item in data_list
            if item['id'] not in parent_ids
        ]

        return leaves

class AccountCostCenterCategory(CashCtrl):
    '''see public api desc'''
    url = 'account/costcenter/category/'
    actions = ['list']

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

# Journal
class Journal(CashCtrl):
    '''see public api desc'''
    url = 'journal/'
    actions = ['list', 'create']

    def create_collective_entry(data, items):
        pass


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
    '''see public api desc
        list: use params = {'type': ORDER_TYPE.PURCHASE}
    '''
    url = 'order/category/'
    actions = ['list']

    def list(self, params=None, **filter_kwargs):
        # Get data
        categories = super().list(params=params, **filter_kwargs)

        '''
        # Convert stati names
        for category in categories:
            for status in category['status']:
                status['name'] = xmltodict.parse(status['name'])
        '''
        return categories

class OrderDocument(CashCtrl):
    '''see public api desc'''
    url = 'order/document/'
    actions = ['read']  # The ID of the order.

class OrderLayout(CashCtrl):
    '''see public api desc'''
    url = 'order/layout/'
    actions = ['read']  # The ID of the order.

class OrderTemplate(CashCtrl):
    '''see public api desc'''
    url = 'order/template/'
    actions = ['read']  # The ID of the entry.


class OrderPayment(CashCtrl):
    '''see public api desc'''
    url = 'order/payment/'
    actions = ['read']  # The ID of the order.

    def download(self, data, filename='pain_001.xml'):
        ''' data: data sent to create before, e.g.
        {
            "date": "2024-03-13",  # Mandatory: Payment execution date (YYYY-MM-DD)
            "orderIds": "123,456,789",  # Mandatory: Comma-separated order IDs
            "type": "PAIN"  # Explicitly request a PAIN file (XML)
        }
        '''
        # Request parameters
        params = prepare_dict(data)
        print("*params", params)
        url = self.BASE_DIR.format(
            org=self.org, url=self.url, action='download')
        print("*url", url)
        response = requests.get(url, auth=self.auth, params=params)

        # Check response status
        if response.status_code == 200:
            # Save the PAIN file as an XML document
            with open(filename, "wb") as file:
                file.write(response.content)

            print(f"PAIN file downloaded successfully: {filename}")
        else:
            print(f"Error: {response.status_code} - {response.text}")

# Person
class Person(CashCtrl):
    '''see public api desc'''
    url = 'person/'
    actions = ['list']

class PersonCategory(CashCtrl):
    '''see public api desc'''
    url = 'person/category/'
    actions = ['list']

    def get_name(self, values):
        name = values.get('en')
        return name.upper() if name else None

    @property
    def top_category(self):
        '''return dict with top categories from self.data
            'EMPLOYEE', 'CUSTOMER'
        '''
        if self.data is None:
            raise Exception("data is None")

        return {
            self.get_name(x['name']['values']): x
            for x in self.data
            if not x['parent_id'] and isinstance(x['name'], dict)
        }

class PersonTitle(CashCtrl):
    '''see public api desc'''
    url = 'person/title/'
    actions = ['list']

# Reporting
class Report(CashCtrl):
    '''see public api desc - not working!'''
    url = 'report/'
    actions = ['tree_json']


class Collection(CashCtrl):
    '''see public api desc'''
    url = 'report/collection/'
    actions = ['list', 'create']

    def create(self, data, params={}):
        if 'config' in data:
            data['config'] = json.dumps(prepare_dict(data['config']))
        return super().create(data, params)


class Element(CashCtrl):
    '''see public api desc'''
    url = 'report/element/'
    actions = ['list', 'create', 'read_json']

    def create(self, data, params={}):
        if 'config' in data:
            data['config'] = json.dumps(prepare_dict(data['config']))
        return super().create(data, params)
