# use for invoice testing
import yaml
from api_cash_ctrl import *


if __name__ == "__main__":
    print("Testing.")

    org = 'test167'
    api = 'OCovoWksU32uCJZnXePEYRya08Na00uG'

    if False:
        # Get person category
        conn = PersonCategory(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            print("*PersonCategory", data['id'], data['name'])

    if False:
        # take 1170
        # Get tax category
        conn = Tax(org, api, convert_dt=False)
        data_list = conn.list()

        print("*Tax", data_list)

    if False:
        # done we use supplier id 43
        # Create supplier
        conn = Person(org, api, convert_dt=False)
        conn.delete(42)

        data = {
            'company': 'elektro',
            'addresses': [{
                'type': 'INVOICE',
                'address': 'Mittelgäustrasse 73',
                'zip': '4617',
                'city': 'Gunzgen'
            }],
            'bank_accounts' : [{
                'type': 'DEFAULT',
                'iban': 'CH3430808001569839654',
                'bic': 'RAIFCH22XXX'
            }]
        }
        response = conn.create(data)
        print("*response", response)

    if False:
        # done; we take
        '''
        1016: Vorsteuer
        992: Postfinance Wasserversorgung
        1017: Kreditoren
        1042: Telefon, Porto

        '''
        # Get accounts
        conn = Account(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            print("*", data['id'], data['name'])

    if False:
        conn = OrderTemplate(org, api, convert_dt=False)

    if False:
        '''we take 1001 leer - rechnungseingang False
        '''
        # Get Order Layouts
        conn = OrderLayout(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            print("*", data['id'], data['name'], data['is_default'])

    if False:
        '''ordercategory 1043
        '''
        # Create Creditor Invoicing
        conn = OrderCategory(org, api, convert_dt=False)
        data = {
            'account_id': 1017,
            'name_plural': 'Test Kreditorenrechnungen 02',   # use something like this
            'name_singular': 'Deckblatt - Kreditorenrechnung',   # use something like this
            'status': [{
                    'icon': 'YELLOW',
                    'name': 'Draft'
                }, {
                    'icon': 'RED',
                    'name': 'Open'
                }, {
                    'icon': 'BLUE',
                    'name': 'PAID'
                }
            ],
            'address_type': 'INVOICE',
            'is_switch_recipient': True,  # Creditor
            'book_type': 'CREDIT',
            'layout_id': 1001,
            'type': 'PURCHASE',
            'sequence_nr_id': 13,  # needs to be set as we don't wanto to set it in orders
            'is_display_prices': True,  # needs to be set otherwise prices are missing in the overview
            'message': 'Kreditorenrechnung'  # A message for the payment recipient
        }
        response = conn.create(data)
        print("*response", response)

    if False:
        '''SequenceNumber
        we take:
         1 Rechnungen
        13 Einkaufsrechnungen
        '''
        # Get SequenceNumber
        conn = SequenceNumber(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            print("*", data['id'], data['name'])

    if False:
        '''order, created 42
        '''
        # Create Creditor Invoicing
        conn = Order(org, api, convert_dt=False)
        data = {
            'associate_id': 43,
            'category_id': 1044,
            'date': '2025-03-13',
            'description': 'test invoice phone',
            'items': [{
                    'accountId': 1042,
                    'name': 'test phone bill 4',
                    'unitPrice': 103,
                    'taxId': 14,  # needs to be included in every position to be displayed at front
                    'description': 'no details',
                    'type': 'ARTICLE'
            }],
        }
        response = conn.create(data)
        print("*response", response)

    if False:
        ''' List bank accounts, for some reason it's not possible to create
            them; we take 2 Bank Test Postfinance
        '''
        # Read BankAccount
        conn = AccountBankAccount(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            print("*", data['id'], data['name'], data['iban'], data['bic'])

    if False:
        ''' List locations, for some reason it's not possible to create
            them; we take 6 Rechnungsstellung Wasser
        '''
        # Read Location
        conn = Location(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            print("*", data['id'], data['name'], data)

    if True:
        '''order, get document take 42
        '''
        # Read Invoicing document
        conn = Order(org, api, convert_dt=False)
        data_list = conn.list(params={'type': 'PURCHASE'})
        for data in data_list:
            print("*data", data['id'], data['date'])
            if data['id'] == 45:
                order = data

        # OrderDocument
        print("*order", order)
        conn = OrderDocument(org, api, convert_dt=False)
        document = conn.read(order['id'])
        print("*document", document)

        # OrderLayout
        conn = OrderLayout(org, api, convert_dt=False)
        layout = conn.read(document['layout_id'])
        # Write dictionary to a YAML file
        with open('layout.yaml', 'w') as file:            
            yaml.dump(
                layout, file, default_flow_style=False, allow_unicode=True, 
                width=float('inf'))
    if False:
        '''order, get document take 42
        '''
        # Read Invoicing document
        conn = OrderDocument(org, api, convert_dt=False)
        data = conn.read(42)
        print("*response", data)

    if False:
        '''get file categories, take 1
        '''
        conn = FileCategory(org, api, convert_dt=False)
        # Create FileCategories
        data = {
            'name': {'de': 'Kreditorenrechnungen'}
        }
        reponse = conn.create(data)

        # Get FileCategories
        data_list = conn.list()
        print("*data_list", data_list)
        for data in data_list:
            print("*", data['id'], data['name'], data)

    if False:
        '''file upload  -> take 42
        '''
        # Read Invoicing document
        conn = File(org, api, convert_dt=False)
        data = {
            'category_id': 1,

        }
        filepath = 'C:/Users/micha/Documents/01_high_prio_bus/00 dev/python/django/env_3.10_projects/scerp/accounting/fixtures/appendix_3.pdf'
        response = conn.upload(filepath, data)
        print("*response", response)

    if False:
        '''order, update document 43
        '''
        # Update Order document
        conn = OrderDocument(org, api, convert_dt=False)
        data = {
            'id': 43,
            'file_id': 42,
            'footer': 'This is <b>important</b>.',
            'header': 'This is <b>not</b> important.',
            'org_address': 'Bürgergemeinde Gunzgen\n4617 Gunzgen',  # for some reasons this needs to be entered again
            'org_bank_account_id': 2,
            'org_location_id': 6,
        }
        response = conn.update(data)
        print("*response", response)

    if False:
        '''order, update document 43
        '''
        # Update Order document
        conn = OrderPayment(org, api, convert_dt=False)
        data = {
            'date': '2025-03-13',
            'order_ids': '44,45',
            'type': 'PAIN'
        }
        response = conn.create(data)
        print("*date", data)
        print("*response", response)

        # Update Order document
        conn = OrderPayment(org, api, convert_dt=False)
        response = conn.download(data)
        print("*response", response)
