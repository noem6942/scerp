from api_cash_ctrl import *


if __name__ == "__main__":
    print("Testing.")

    org = 'test167'
    api = 'OCovoWksU32uCJZnXePEYRya08Na00uG'

    conn = OrderTemplate(org, api, convert_dt=False)
    data_list = conn.list()
    for data in data_list:
      if 'leer' in data['name']:
            print("*", data)
