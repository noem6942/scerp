# accounting/tests/test_order.py
from django.test import TestCase

from .. import api_cash_ctrl as api
from ..api_cash_ctrl import value_to_xml
from .credentials import ORG, KEY


class OrderTests(TestCase):
    '''
    python manage.py test accounting.tests.test_order.OrderTests
    '''
    def setUp(self):
        """Set up any initial test data or configurations."""
        pass
 
    def test_create_person(self): 
        PARAMS =  {}

        # create OrderCategory
        ctrl = api.OrderCategory(ORG, KEY)

        account_id = 714
        rounding_id = 1
        sequence_nr_id = 1
        responsible_person_id = 3
        template_id = 1000

        data = {
            'account_id': account_id, 
            'name_singular': {'values': {
                'de': 'Rechnung Test',
                'en': 'Invoice', 
                'fr': 'Facture', 
                'it': 'Fattura'}}, 
            'name_plural': {'values': {
                'de': 'Rechnungen Test', 
                'en': 'Invoices', 
                'fr': 'Factures', 
                'it': 'Fatture'}},
            'status': [{
                'icon': api.COLOR.GRAY,
                'name': value_to_xml({'values': {
                    'de': 'Entwurf',
                    'en': 'Draft', 
                    'fr': 'Projet', 
                    'it': 'Progetto'}}) 
            }, {
                'icon': api.COLOR.BLUE,
                'name': value_to_xml({'values': {
                    'de': 'Gewonnen',
                    'en': 'Won', 
                    'fr': 'Won', 
                    'it': 'Won'}})
            }],
            'address_type': api.ADDRESS_TYPE.INVOICE,  # default is 'MAIN', ensure there is always an INVOICE address
            # 'book_templates, 
            'book_type': api.BOOK_TYPE.DEBIT, 
            'due_days': 30, 
            'footer': '<i>Rechtsmittel: Wasser - schriftlich innert 10 Tagen an die Wasserkommission der BürgergemeindeGunzgenAbwasser - schriftlich innert 10 Tagen an den Einwohnergemeinderat Gunzgen</i>',
            'header': '''Kontakt:<br>
                Tel. 062 387 95 29<br>
                E-Mail: bz-gunzgen@bdo.ch<br>
                <br>
                Abrechnungsperiode: $customField27<br>
                Objekt: $customField30<br>
                Zählernummer: $customField30<br>
                Zählerstand neu: $customField28 m³ (alt $customField29 m³)''', 
            'is_display_prices': True, 
            'is_display_item_gross': False, 
            'responsible_person_id': responsible_person_id,  # Sachbearbeiter
            'rounding_id': rounding_id,  # auf 0.05 runden
            'sequence_nr_id': sequence_nr_id,  # RE ...
            'template_id': template_id, 
            'type': api.ORDER_TYPE.SALES
        }   
        response = ctrl.create(data)
        # Use assertions to validate the response
        self.assertIsNotNone(
            response, "Response should not be None")
        self.assertEqual(
            response.get('success'), True, f"success: {response}")
