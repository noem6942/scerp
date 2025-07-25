from django.conf import settings
from decimal import Decimal
import json
import yaml

from api_cash_ctrl import *


if __name__ == "__main__":
    print("Testing.")

    org = 'test167'
    api = 'OCovoWksU32uCJZnXePEYRya08Na00uG'  # ''

    if False:
        conn = Unit(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if False:
        conn = PersonTitle(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if False:
        conn = Setting(org, api, convert_dt=False)
        data = conn.read()
        print("*", data)

    if False:
        conn = Person(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            if data['id'] in (54, 55):
                print("*", data)
                details = conn.read(data['id'])
                print("*details", details)

        data = {
            'category_id': 77,
            'first_name': None,
            'last_name': 'Leuenberger-Schneider Hedwig + Robert 2',
            'alt_name': {'de': 'Leuenberger-Schneider Hedwig + Robert 2'},
            'is_customer': True,
            'addresses': [{
                'type': 'MAIN',
                'address': 'Schulstrasse 1',
                'zip': '4617',
                'city': 'Gunzgen',
                'country': 'CHE',
            }, {
                'type': 'INVOICE',
                'company': 'Delta Finanz & Treuhand 2 GmbH',
                'firstName': None,
                'lastName': None,
                'isHideName': True,
                'address': 'Poststrasse 21',
                'zip': '8634',
                'city': 'Hombrechtikon',
                'country': 'CHE',
            }],
        }
        response = conn.create(data)
        print("*response", response)

    if False:
        conn = PersonCategory(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if False:
        conn = AccountCategory(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
            if data['id'] < 10:
                print("*", data['name'].upper(), "=", data['id'],
                    data['number'], type(data['number']))

        conn.create({'name': 'test 1_d', 'parent_id': 1, 'number': Decimal(99.9)})
        conn.create({'name': 'test 1_f', 'parent_id': 1, 'number': 99.9})
        conn.create({'name': 'test 1_str', 'parent_id': 1, 'number': '99.9'})

    if False:
        conn = AccountBankAccount(org, api, convert_dt=False)

        data = {
            #'is_inactive': False,
            'name': 'Postfinance XA',
            'type': 'DEFAULT',
            #'currency': None,
            #'bic': 'POFICHBEXXX',
            #'iban': 'CH1530000001460021397',
            #'qr_first_digits': None,
            #'qr_iban': None,
            #'url': '',
            #'account_id': 992,
            #'currency_id': None
        }
        response = conn.create(data)
        print("*response", response)

        #data_list = conn.list()
        #print("*", data_list)

    if False:
        conn = OrderCategory(org, api, convert_dt=False)
        data_list = conn.list(params={'type': 'PURCHASE'})
        filter_list = [
            data for data in data_list
            if 'orto 1' in str(data['name'])
        ]
        print("*", filter_list)

    if False:
        conn = OrderTemplate(org, api, convert_dt=False)
        data_list = conn.list()
        filter_list = [
            data for data in data_list
            #if 'orto 1' in str(data['name'])
        ]
        print("*", [(x['name'], x['id']) for x in filter_list])
        print("*", filter_list[0]['html'])

    if False:
        conn = Order(org, api, convert_dt=False)
        data_list = conn.list()
        filter_list = [
            data for data in data_list
            if '-03' in data['date']
        ]
        print("*", filter_list)

    if False:
        conn = OrderTemplate(org, api, convert_dt=False)
        data_list = conn.list()
        for data in data_list:
          if 'leer' in data['name']:
                print("*", data)

    if False:
        filepath = 'C:/Users/Administrator/Downloads/eCH-0093-3-0.xsd'
        conn = File(org, api)
        data = {'description': "test file"}
        file_id, file_name = conn.upload(filepath, data)
        print("*file_id", file_id)

    if False:
        conn = File(org, api)
        conn.download(24, 'C:/Users/Administrator/Downloads/')

    if False:
        conn = File(org, api)
        conn = Person(org, api, convert_dt=False)
        conn.attach_files(26, [18])

    if False:
        conn = Account(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", len(data_list))
        data = data_list[0]
        id = 1781  # data.get('id')
        balance = conn.get_balance(id)
        print("*", id, balance)

    if False:
        conn = Element(org, api, convert_dt=False)
        data = {
            'name': 'Balance List',  # we take list so we are faster
            'type': ELEMENT_TYPE.BALANCE_LIST,
            'config': {
                'accounts': '1:99999',  # take all
                'is_hide_zero': False
            }
        }
        response = conn.create(data)
        print("*response", response)  # we have now element_id_c = 1036

    if False:
        conn = Collection(org, api, convert_dt=False)
        data = {
            'name': 'SC-ERP'
        }
        response = conn.create(data)
        print("*response", response)  # we have now collection_id_c = 1002

    if False:
        conn = Element(org, api, convert_dt=False)
        data = {
            'name': 'Journal 1',  # we take list so we are faster
            'type': ELEMENT_TYPE.JOURNAL,
            #'collection_id': 1002,
        }
        response = conn.create(data)
        print("*response", response)  # we have now element_id_c = 1043
        data = conn.read(response['insert_id'])
        print("*response", data)  # we have now period_id_c = 13

    if False:
        conn = Report(org, api, convert_dt=False)
        data_list = conn.tree_json()
        print("*response", data_list)
        
    if False:
        conn = FiscalPeriod(org, api, convert_dt=False)
        data_list = conn.list()
        print("*response", data_list[-1])  # we have now period_id_c = 13

    if True:
        conn = Element(org, api, convert_dt=False)
        element_id_c = 1061
        response = conn.read(element_id_c)
        print("*response", response)
        #response = conn.delete(element_id_c)
        #print("*response", response)
        
    if False:
        conn = Element(org, api, convert_dt=False)
        element_id_c = 1041
        period_id_c = 13

        params = {
            'element_id': element_id_c,
            'fiscal_period': period_id_c
        }

        data_list = conn.data_json(params)

        print("*data_list", data_list)

