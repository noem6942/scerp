# accounting/tests/test_person.py
from django.test import TestCase

from ..api_cash_ctrl import Person, CONTACT_TYPE, ADDRESS_TYPE, COLOR
from .credentials import ORG, KEY


class PersonTests(TestCase):
    '''
    python manage.py test accounting.tests.test_person.PersonTests
    '''
    def setUp(self):
        """Set up any initial test data or configurations."""
        self.ctrl = Person(ORG, KEY)

    def test_create_person(self):
        """Test the creation of a person."""
        data = {
            'category_id': 1,
            'first_name': None,
            'last_name': 'BDO AG, 4600 Olten',
            'company': 'BDO',
            'addresses': [{
                'type': ADDRESS_TYPE.MAIN,
                'zip': '4600',
                'city': 'Olten',
                'country': 'CHE',
            }],
            'contacts': [{
                'address': 'bz-gunzgen@bdo.ch',
                'type': CONTACT_TYPE.EMAIL_WORK,
            }, {
                'address': '062 387 95 29',
                'type': CONTACT_TYPE.PHONE_WORK,
            }],
            'color': COLOR.BLUE
        }

        response = self.ctrl.create(data)
        # Use assertions to validate the response
        self.assertIsNotNone(
            response, "Response should not be None")        
        self.assertEqual(
            response.get('success'), True, f"success: {response}")
