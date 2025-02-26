from api_cash_ctrl import *


if __name__ == "__main__":
    print("Testing.")

    org = 'test167'
    api = 'OCovoWksU32uCJZnXePEYRya08Na00uG'

    if True:
        conn = PersonTitle(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)

    if False:
        conn = Person(org, api, convert_dt=False)
        data_list = conn.list()
        print("*", data_list)
    
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
        