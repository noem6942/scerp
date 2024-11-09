# api_cash_ctrl.py
import dicttoxml
from dateutil.parser import parse as parse_datetime
from enum import Enum
from xml.etree import ElementTree
import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from time import sleep

# Constants
BASE_URL = 'https://{org}.cashctrl.com/api/v1'
ENCODING = 'utf-8'
LANGUAGES = ['de', 'en', 'fr', 'it']
LANGUAGE_API = 'en'
LANGUAGE_DEFAULT = 'de'
CONVERT_DATETIMES = False

DATE_KEYS = [
    'created', 'lastUpdated', 'start', 'end', 'date', 'lastEntryDate'
]

XML_KEYS = [
    'custom', 'description', 'groupName', 'categoryDisplay', 
    'titleName'
]

JSON_KEYS = [
    'addresses', 'contacts'
]

from enum import Enum


class FieldType(Enum):
    JOURNAL = 'JOURNAL'
    ACCOUNT = 'ACCOUNT'
    INVENTORY_ARTICLE = 'INVENTORY_ARTICLE'
    INVENTORY_ASSET = 'INVENTORY_ASSET'
    ORDER = 'ORDER'
    PERSON = 'PERSON'
    FILE = 'FILE'
    

# Custom Exception Class
class APIError(Exception):

    def __init__(
            self, message, status_code=None, url=None, response_text=None):
        self.message = message
        self.status_code = status_code
        self.url = url
        self.response_text = response_text
        super().__init__(self.message)

    def __str__(self):
        return (f"{self.message} (Status Code: {self.status_code}, "
                f"URL: {self.url}, Response: {self.response_text})")

class CashCtrl:
    """
    An API Wrapper for CashCtrl Service
    """
    MAX_TRIES = 5
    SLEEP_DURATION = 10
    read_only = False  # Default to allow read and write
    CUSTOM_XML = []
    
    def __init__(self, org, api_key, language=LANGUAGE_DEFAULT):
        """
        Initialize CashCtrl API instance.

        Args:
            org (str): The organization identifier for the CashCtrl API.
            api_key (str): API key for authentication.
            language (str): Language for the API requests, defaulting to 'de'.
        """
        self.auth = HTTPBasicAuth(api_key, '')
        self.base = BASE_URL.format(org=org)
        self.language = language
        self.custom = self.load_custom_fields()

    # === Utility Methods ===
        
    @staticmethod
    def get_response_get(url, **kwargs):
        """
        Performs a GET request and processes the response.

        Args:
            url (str): The URL for the GET request.

        Returns:
            dict: The response data if the request is successful.

        Raises:
            APIError: If the GET request fails.
        """
        response = requests.get(url, **kwargs)
        if response.status_code == 200:
            content_type = response.headers['Content-Type']
            if 'json' in content_type:
                return response.json().get('data')
            else:
                print("not implemented yet")
        else:
            raise APIError(f"GET request failed for '{url}': {response.status_code} - {response.text}")

    @staticmethod    
    def get_response_post(url, **kwargs):
        """
        Performs a POST request with retry for rate limiting.

        Args:
            url (str): The URL for the POST request.

        Returns:
            dict: The response data if the request is successful.

        Raises:
            APIError: If the POST request fails or rate limits are exceeded.
        """
        for attempt in range(CashCtrl.MAX_TRIES):
            response = requests.post(url, **kwargs)

            if response.status_code == 429:  # Rate limit
                print("Rate limit reached. Retrying...")
                sleep(CashCtrl.SLEEP_DURATION)
                continue
            elif not response.ok:
                raise APIError(f"POST request failed for '{url}': {response.status_code} - {response.reason} {response.text}")

            content = response.json()
            if not content.get('success', False):
                errors = "; ".join(
                    f"{err.get('field', 'Unknown')}: {err.get('message', '')}"
                    for err in content.get('errors', [])
                )
                raise APIError(f"POST request error in '{url}': {errors}")

            return content

        raise APIError(f"Maximum retry attempts ({CashCtrl.MAX_TRIES}) reached for POST request to '{url}'.")


    @staticmethod
    def dict_to_xml_values(dictionary):
        """
        Converts a dictionary into XML formatted string of <values> elements.

        Args:
            dictionary (dict): Input dictionary with keys and values for different languages.
        
        Returns:
            str: XML string with <values> tag as the root, or an empty string if input is empty.
        
        Example:
            data_dict = {
                "de": "cust_color",
                "en": "cust_color",
                "fr": "cust_color",
                "it": "cust_color"
            }
            Result: "<values><de>cust_color</de><en>cust_color</en><fr>cust_color</fr><it>cust_color</it></values>"
        """
        if not dictionary:
            return ''
        
        try:
            # Wrapping the dictionary to fit the expected XML structure.
            data_wrapped = {'values': dictionary}
            
            # Convert dictionary to XML bytes without attribute types and custom root.
            xml_bytes = dicttoxml.dicttoxml(data_wrapped, custom_root='root', attr_type=False)
            
            # Parse XML and locate the <values> element for final output.
            root = ElementTree.fromstring(xml_bytes)
            values_element = root.find('values')
            
            # Convert <values> element back to string and decode it.
            return ElementTree.tostring(values_element, encoding=ENCODING).decode(ENCODING)
        
        except Exception as e:
            logging.error(f"Failed to convert dictionary to XML: {e}")
            return ''

    @staticmethod
    def xml_values_to_dict(xml_str):
        """
        Converts an XML string of <values> elements into a dictionary.

        Args:
            xml_str (str): XML string with <values> as the root element and children for each key-value pair.

        Returns:
            dict: Dictionary representation of the XML data, or an empty dictionary if input is empty or parsing fails.

        Example:
            xml_str = "<values><de>cust_color</de><en>cust_color</en><fr>cust_color</fr><it>cust_color</it></values>"
            Result: {"de": "cust_color", "en": "cust_color", "fr": "cust_color", "it": "cust_color"}
        """
        if not xml_str:
            return {}

        try:
            # Parse the XML string
            root = ElementTree.fromstring(xml_str)
            
            # Convert XML children to dictionary
            return {child.tag: child.text for child in root}
        
        except ElementTree.ParseError as e:
            logging.error(f"XML parsing error: {e}")
            return {}

    # === Data Processing Methods ===

    def load_custom_fields(self):
        """Placeholder method to load custom fields."""
        return []

    def clean_get(self, data):
        """
        Cleans and processes data received via GET requests.

        Args:
            data (dict): The original data to be cleaned.

        Returns:
            dict: Cleaned data with XML and datetime conversions applied.
        """
        if not data:
            return data
        
        # Convert specified XML fields to dictionaries
        for xml in XML_KEYS + self.CUSTOM_XML:
            if xml in data:
                data[xml] = self.xml_values_to_dict(data[xml])

        # Process custom fields with XML conversions if present
        if 'customFields' in data:
            for field in data['customFields']:
                for xml in XML_KEYS + self.CUSTOM_XML:
                    if xml in field:
                        field[xml] = self.xml_values_to_dict(field[xml])

        # Convert date strings to datetime objects
        if CONVERT_DATETIMES:
            for key in DATE_KEYS:
                if key in data and data[key]:
                    data[key] = parse_datetime(data[key])

        return data

    def clean_post(self, data):
        """
        Cleans and prepares data for POST requests.

        Args:
            data (dict): The original data to be cleaned.

        Returns:
            dict: Data ready for posting with JSON and datetime conversions applied.
        """
        if not data:
            return data

        # Convert JSON fields to JSON strings
        for key in JSON_KEYS:
            if key in data:
                data[key] = json.dumps(data[key])

        # Convert specified dictionary fields to XML strings
        for xml in XML_KEYS + self.CUSTOM_XML:
            if xml in data:
                data[xml] = self.dict_to_xml_values(data[xml])

        # Format datetime objects as strings
        if CONVERT_DATETIMES:
            for key in DATE_KEYS:
                if key in data and data[key]:
                    data[key] = data[key].strftime('%Y-%m-%d %H:%M:%S.0')

        return data

    # === API Interface Methods ===

    def get(self, id, **kwargs):
        """
        Retrieves data for a specific item by ID.

        Args:
            id (int): Unique identifier for the item.

        Returns:
            dict: Cleaned data for the requested item.
        """
        kwargs['id'] = id        
        url = self.url.format(base=self.base, action='read')
        data = self.get_response_get(url, params=kwargs, auth=self.auth)            
        return self.clean_get(data)

    def list(self, action='list', **kwargs):
        """
        Retrieves a list of items for the specified action.

        Args:
            action (str): Action type, defaulting to 'list'.

        Returns:
            list: Cleaned data for each item in the list.
        """
        url = self.url.format(base=self.base, action=action)   
        data = self.get_response_get(url, params=kwargs, auth=self.auth)        
        return [self.clean_get(item) for item in data]

    def tree(self, **kwargs):
        """
        Retrieves a tree structure of items.

        Returns:
            list: Tree-structured list of items.
        """
        return self.list(action='tree', **kwargs)

    def post(self, data):
        """
        Posts data to create or update an item.

        Args:
            data (dict): Data to post.

        Returns:
            dict: Response indicating success or failure.
        """
        url = self.url.format(base=self.base, action='create')
        if self.read_only:
            raise Exception(f"API '{url}' is read-only.")
        
        cleaned_data = self.clean_post(data)
        return self.get_response_post(url, data=cleaned_data, auth=self.auth)
        
        
# CustomFields
class CustomFieldCtrl(CashCtrl):

    def list(self, **kwargs):
        # If 'type' is provided, call the superclass method directly
        if kwargs.get('type'):
            return super().list(**kwargs)  # Calls CashCtrl's list method
        else:
            # Fetch for all entity types and construct a dictionary
            results = {}            
            for type_enum in FieldType:
                type = type_enum.value
                kwargs['type'] = type
                results[type] = super().list(**kwargs)
            
            return results


class CustomField(CustomFieldCtrl):
    read_only = False  
    url = '{base}/customfield/{action}.json'            
    
 
class CustomFieldGroup(CustomFieldCtrl):
    read_only = False  
    url = '{base}/customfield/group/{action}.json'   


# Account    
class AccountCategory(CashCtrl):
    read_only = False
    url = '{base}/account/category/{action}.json'


class Account(CashCtrl):
    read_only = False  
    url = '{base}/account/{action}.json'
    
 
 # Common
class Currency(CashCtrl):
    read_only = True
    url = '{base}/currency/{action}.json'    
    
    
class Rounding(CashCtrl):
    read_only = True
    url = '{base}/rounding/{action}.json'  

 
class SequenceNumber(CashCtrl):
    read_only = True
    url = '{base}/sequencenumber/{action}.json'     

 
class Tax(CashCtrl):
    read_only = False  
    url = '{base}/tax/{action}.json'      
 
 
# File
class File(CashCtrl):
    read_only = False  
    url = '{base}/file/{action}.json'
 
 
# Inventory 
class InventoryArticle(CashCtrl):
    read_only = False  
    url = '{base}/inventory_article/{action}.json'


class InventoryAsset(CashCtrl):
    read_only = False  
    url = '{base}/inventory_asset/{action}.json'
 

# Journal 
class Journal(CashCtrl):
    read_only = False  
    jsons = []
    url = '{base}/journal/{action}.json' 
    
    
# Meta    
class FiscalPeriod(CashCtrl):
    read_only = True
    url = '{base}/fiscalperiod/{action}.json'    
 

class OrganizationLogo(CashCtrl):
    read_only = True
    url = '{base}/domain/logo/'  
 

class Setting(CashCtrl):
    read_only = False
    url = '{base}/setting/'
 

# Order    
class Order(CashCtrl):
    read_only = False  
    url = '{base}/order/{action}.json'
    
    
class DocumentTemplate(CashCtrl):
    read_only = False  
    url = '{base}/order/template/{action}.json'

    
# Person   
class PersonCategory(CashCtrl):
    read_only = False
    url = '{base}/person/category/{action}.json'  


class Person(CashCtrl):  
    read_only = False  
    url = '{base}/person/{action}.json'   
  
  
# Report
class Report(CashCtrl):  
    # Has action tree instead list
    read_only = True  
    url = '{base}/report/{action}.json'   
    

class Element(CashCtrl):  
    read_only = False
    url = '{base}/report/element/{action}.json' 
    
    
class Set(CashCtrl):  
    read_only = False
    url = '{base}/report/set/{action}.json'     


    