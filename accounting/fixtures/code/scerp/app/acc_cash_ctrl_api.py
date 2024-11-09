"""
accounting_api.py

This script contains the implementation of an API wrapper for the CashCtrl financial accounting service.
"""
from django.utils.dateparse import parse_datetime

import json
import requests
import dicttoxml
import warnings
from xml.etree import ElementTree
from enum import Enum
from requests.auth import HTTPBasicAuth
from datetime import datetime
from time import sleep

from .models import Admin, Client, Location

# Define constants
BASE_URL = 'https://{org}.cashctrl.com/api/v1'
CONVERT_DATETIMES = False

ENCODING = 'utf-8'
LANGUAGES = ['de', 'en', 'fr', 'it']
LANGUAGE_API = 'en'  # for coding
LANGUAGE_DEFAULT = 'de'  # for displaying data, esp. PDFs, Excel sheets and CSV files

class DataType:
    TEXT = 'TEXT'
    CHECKBOX = 'CHECKBOX'


class FieldType(Enum):
    JOURNAL = 'JOURNAL'
    ACCOUNT = 'ACCOUNT'
    INVENTORY_ARTICLE = 'INVENTORY_ARTICLE'
    INVENTORY_ASSET = 'INVENTORY_ASSET'
    ORDER = 'ORDER'
    PERSON = 'PERSON'
    FILE = 'FILE'


class AdressType:
    MAIN = 'MAIN'


class Email:
    WORK = 'EMAIL_WORK'


class PhoneType:
    WORK = 'PHONE_WORK'


class CashCtrl:
    """
    An API Wrapper for CashCtrl Service
    """
    MAX_TRIES = 5
    SLEEP = 10    
    DATE_KEYS = [
        'created', 'lastUpdated', 'start', 'end', 'date', 'lastEntryDate']
    read_only = False  # default

    def __init__(self, org, api_key, language=LANGUAGE_DEFAULT):
        self.auth = HTTPBasicAuth(api_key, '')
        self.base = BASE_URL.format(org=org)
        self.language = language
        self.custom = self.load_custom_fields()

    # Helpers
    @staticmethod
    def get_response_get(url, **kwargs):
        response = requests.get(url, **kwargs)        
        if response.status_code == 200:
            return response.json().get('data')
        else:
            raise Exception(f"API get error occurred in '{url}': "
                            f"{response.status_code} - {response.text}")         

    @staticmethod    
    def get_response_post(url, **kwargs):
        for try_nr in range(5):
            response = requests.post(url, **kwargs)

            # If rate-limited, wait a bit and try again
            if response.status_code == 429:
                print("Rate limit reached. Sleeping for 10 seconds...")
                sleep(10)
                continue
                
            # Check HTTP status code
            elif not response.ok:
                raise Exception(
                    f"HTTP get error occurred in '{url}': "
                    f"{response.status_code} - {response.reason} {response.text}")                    

            # Parse JSON content
            content = response.json()
            print("*content", content)
            
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
            
            
    def load_custom_fields(self):
        return []
            
    def clean_get(self, data):   
        # Check if valid
        if not data:
            return data
            
        # Convert xmls to json
        for xml in self.xmls:
            if xml in data:
                data[xml] = self.xml_values_to_dict(data[xml])
                
        if 'customFields' in data:
            # Convert xmls to json in CustomFieldGroups (inconsistency)
            for field in data['customFields']:
                for xml in self.xmls:
                    if xml in field:
                        field[xml] = self.xml_values_to_dict(field[xml])                  

        # Make datetime
        if CONVERT_DATETIMES:
            for key in DATE_KEYS:
                if key in data and data[key]:
                    data[key] = parse_datetime(data[key]) 
        
        return data
          
    def clean_post(self, data):  
        # Check if valid
        if not data:
            return data
            
        # Convert jsons to json_string
        for key in self.jsons:
            if key in data:
                data[key] = json.dumps(data[key])
  
        # Convert xmls to string
        for xml in self.xmls:
            if xml in data:
                data[xml] = self.dict_to_xml_values(data[xml])                
  
        # Make datetime
        if CONVERT_DATETIMES:
            for key in DATE_KEYS:
                if key in data and data[key]:
                    data[key] = data[key].strftime('%Y-%m-%d %H:%M:%S.0')
        
        return data        
            
    def get(self, id, **kwargs):     
        kwargs['id'] = id        
        url = self.url.format(base=self.base, action='read')
        data = self.get_response_get(url, params=kwargs, auth=self.auth)            
        return self.clean_get(data)
 
    def list(self, action='list', **kwargs):
        url = self.url.format(base=self.base, action=action)        
        data = self.get_response_get(url, params=kwargs, auth=self.auth)
        
        return [self.clean_get(x) for x in data]

    def tree(self, **kwargs):
        return self.list(action='tree', **kwargs)

    def post(self, data):      
        '''post data 
           returns e.g. {'success': True, 
                         'message': 'Person saved', 
                         'insertId': 28}
        '''
        url = self.url.format(base=self.base, action='create')
        if self.read_only:
            raise Exception(f"api '{url}' is defined as 'read only'")                
        else:        
            data = self.clean_post(data)
            return self.get_response_post(url, data=data, auth=self.auth)
 
 
# Account    
class AccountCategory(CashCtrl):
    read_only = False
    xmls = []
    url = '{base}/account/category/{action}.json'


class Account(CashCtrl):
    read_only = False  
    jsons = []
    xmls = ['name', 'custom']  # adjust as needed
    url = '{base}/account/{action}.json'
    
 
 # Common
class Currency(CashCtrl):
    read_only = True
    xmls = ['description']
    url = '{base}/currency/{action}.json'    
    
    
class Rounding(CashCtrl):
    read_only = True
    xmls = ['name']
    url = '{base}/rounding/{action}.json'  

 
class SequenceNumber(CashCtrl):
    read_only = True
    xmls = ['name']
    url = '{base}/sequencenumber/{action}.json'     

    
class CustomField(CashCtrl):
    xmls = ['name', 'description', 'groupName']
    url = '{base}/customfield/{action}.json'  
    
 
class CustomFieldGroup(CashCtrl):
    xmls = ['name', 'description', 'groupName']
    url = '{base}/customfield/group/{action}.json'   

 
# File
class File(CashCtrl):
    read_only = False  
    jsons = []
    xmls = ['name', 'custom']  # adjust as needed
    url = '{base}/file/{action}.json'
 
 
# Inventory 
class InventoryArticle(CashCtrl):
    read_only = False  
    jsons = []
    xmls = ['name', 'custom']  # adjust as needed
    url = '{base}/inventory_article/{action}.json'


class InventoryAsset(CashCtrl):
    read_only = False  
    jsons = []
    xmls = ['name', 'custom']  # adjust as needed
    url = '{base}/inventory_asset/{action}.json'
 

# Journal 
class Journal(CashCtrl):
    read_only = False  
    jsons = []
    xmls = ['name', 'custom']  # adjust as needed
    url = '{base}/journal/{action}.json' 
    
    
# Meta    
class FiscalPeriod(CashCtrl):
    read_only = True
    xmls = []
    url = '{base}/fiscalperiod/{action}.json'    
    

# Order    
class Order(CashCtrl):
    read_only = False  
    jsons = []
    xmls = ['name', 'custom']  # adjust as needed
    url = '{base}/order/{action}.json'

    
# Person   
class PersonCategory(CashCtrl):
    read_only = False
    jsons = []
    xmls = ['name']
    url = '{base}/person/category/{action}.json'  


class Person(CashCtrl):  
    read_only = False  
    jsons = ['addresses', 'contacts']
    xmls = ['categoryDisplay', 'custom', 'titleName']
    url = '{base}/person/{action}.json'   
  
  
# Report
class Report(CashCtrl):  
    # Has action tree instead list
    read_only = True  
    xmls = []
    url = '{base}/report/{action}.json'   
    

class Element(CashCtrl):  
    read_only = False
    jsons = []
    xmls = []
    url = '{base}/report/element/{action}.json' 
    
    
class Set(CashCtrl):  
    read_only = False
    jsons = []
    xmls = []
    url = '{base}/report/set/{action}.json'     
