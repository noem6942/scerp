# process.py
from . import acc_cash_ctrl_api as ch_ctr
from .models import Admin
from .geo_mapping import GeoAdmin

class Test(object):
    
    def __init__(self, org):
        self.admin = Admin.objects.get(org=org)
        self.org = self.admin.org
        self.api_key = self.admin.api_key

    def api_get_test(self):
        obj_ = ch_ctr.Person(self.org, self.api_key)
        data = obj_.list()
        # data = obj_.tree()
        # data = obj_.get(28)
        with open('output.txt', 'w') as f:
            print("*writing", data)
            f.write(str(data))
            
    def api_post_test(self):
        obj_ = ch_ctr.Person(self.org, self.api_key)
        _dict = {
            "parentId": None,
            "sequenceNrId": None,
            "discountPercentage": None,
            "name": {
                "de": "Mein Lieferanten",
                "en": "MeinVendors",
                "fr": "Mein Fournisseurs",
                "it": "Mein Fornitori"
            }
        }
        _dict = {
            'company': 'metallic',
            'firstName': 'First name 1',
            'lastName': 'Last name 2',
            'custom': {
                'customField28': 'metallic grey',
            },
            'addresses': [{
                'type': 'MAIN',
                'address': 'Street 123',
                'city': 'City',
                'country': 'CHE',
                'zip': '7000'
            }],
            'contacts': [
                {'address': 'email@example.com', 'type': 'EMAIL_WORK'},
                {'address': '123456789', 'type': 'PHONE_WORK'}
            ],        
            'categoryId': 1,
            'sequenceNumberId': 1,
            'isInactive': False,
            # Add more fields here if needed
        }
        data = obj_.post(_dict)
        print("*writing", data)
     
    def other_test(self):
        address = dict(
            address='Am Holbrig',
            zip='8049',
            city='Zürich'
        )
        g = GeoAdmin()
        data = g.search(**address)
        print(data)
        with open('output.txt', 'w') as f:
            print("*writing", data)
            f.write(str(data))        