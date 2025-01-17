# accounting/tests/test_person.py
import logging
from django.test import TestCase

from .. import api_cash_ctrl as api
from .credentials import ORG, KEY

logger = logging.getLogger(__name__)


class PersonTests(TestCase):
    '''
    python manage.py test accounting.tests.test_cash_ctrl.PersonTests
    '''
    def setUp(self):
        """Set up any initial test data or configurations."""
        self.ctrl = api.Person(ORG, KEY)

    def test_create_person(self):
        """Test the creation of a person."""
        data = {
            'category_id': 1,
            'first_name': None,
            'last_name': 'BDO AG, 4600 Olten',
            'company': 'BDO',
            'addresses': [{
                'type': api.ADDRESS_TYPE.MAIN,
                'zip': '4600',
                'city': 'Olten',
                'country': 'CHE',
            }],
            'contacts': [{
                'address': 'bz-gunzgen@bdo.ch',
                'type': api.CONTACT_TYPE.EMAIL_WORK,
            }, {
                'address': '062 387 95 29',
                'type': api.CONTACT_TYPE.PHONE_WORK,
            }],
            'color': api.COLOR.BLUE
        }

        response = self.ctrl.create(data)
        # Use assertions to validate the response
        self.assertIsNotNone(
            response, "Response should not be None")        
        self.assertEqual(
            response.get('success'), True, f"success: {response}")


class TaxTests(TestCase):
    '''
    python manage.py test accounting.tests.test_cash_ctrl.TaxTests
    '''
    def setUp(self):
        """Set up any initial test data or configurations."""
        self.ctrl = api.Tax(ORG, KEY)

    def test_create_tax(self):
        """Test the creation of a person."""
        taxes = self.ctrl.list()

        account_id = 34
        data = {
            'account_id': account_id, 
            'name': {'values': {
                'de': 'Vorsteuer 8.1%', 
                'en': 'Input tax 8.1%', 
                'fr': 'Impôt préalable 8.1%', 
                'it': 'Imposta precedente 8.1%'
            }}, 
            'document_name': {'values': {
                'de': 'CHE-111.222.333 MWST, Abwasser, 8.1%', 
                'en': 'VAT 8.1%', 
                'fr': 'TVA 8.1%', 
                'it': 'IVA 8.1%'
            }}, 
            'calc_type': 'NET', 
            'percentage': 8.1, 
            'percentage_flat': None,             
        }

        response = self.ctrl.create(data)
        logger.info(f"Response: '{ response }'")        
        
        # Use assertions to validate the response
        self.assertIsNotNone(
            response, "Response should not be None")        
        self.assertEqual(
            response.get('success'), True, f"success: {response}")


class PersonTitle(TestCase):
    '''
    python manage.py test accounting.tests.test_cash_ctrl.PersonTitle
    '''
    def setUp(self):
        """Set up any initial test data or configurations."""
        self.ctrl = api.PersonTitle(ORG, KEY)

    def test_list_person_title(self):
        """Test the creation of a person."""
        titles = self.ctrl.list()
        logger.info(f"Response: '{ titles }'")
        # Use assertions to validate the response
        self.assertIsNotNone(
            titles, "Response should not be None")        
