from api_cash_ctrl import *


if __name__ == "__main__":
    print("Testing.")

    org = 'test167'
    api = 'OCovoWksU32uCJZnXePEYRya08Na00uG'

    if False:
        conn = PersonTitle(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if False:
        conn = Person(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if False:
        conn = PersonCategory(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if True:
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
