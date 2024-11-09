import requests

# Define the API endpoint
url = "https://api3.geo.admin.ch/rest/services/api/SearchServer"


class GeoAdmin(object):

    MAP_DEFAULT = {
        'z': 8,
        'bgLayer': 'ch.swisstopo.pixelkarte-farbe',
        'topic': 'ech',
        'layers': 'ch.swisstopo.zeitreihen@year=1864,f'
        'ch.bfs.gebaeude_wohnungs_register,f'
        'ch.bav.haltestellen-oev,f'
        'ch.swisstopo.swisstlm3d-wanderwege,f'
        'ch.vbs.schiessanzeigen,f'
        'ch.astra.wanderland-sperrungen_umleitungen,f'
    }

    def __init__(self):
        self.api_key = '{yourAPIkey}'

    @staticmethod
    def map_init():
        return GeoAdmin.MAP_DEFAULT

    def search(self, search_text='', *args, **kwargs):
        '''e.g. am holbrig 7, 8049 zürich
        '''
        # get searchText
        if args:
            search_text += ' '.join(args)
        if kwargs:
            search_text += ' '.join(list(kwargs.values()))

            # Define the parameters for the API call
            params = {
                'searchText': search_text,
                'type': 'locations',
                'apikey': self.api_key
            }

            # Make the GET request
            response = requests.get(url, params=params)

            # Ensure the request was successful
            if response.status_code == 200:
                # Extract the JSON data from the response
                data = response.json()

                # Print the result
                return data
            else:
                raise Exception(
                    f"api 'API request {url} failed with status code "
                    f"{response.status_code}")
