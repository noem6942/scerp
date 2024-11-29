# scerp/locales.py
from django.utils.translation import gettext_lazy as _


class APP:
    verbose_name = _('SC-ERP - das Schweizer City ERP')
    title = _('SC-ERP - das Schweizer City ERP')
    welcome = _('Willkommen!')
    
    # A dictionary to define the order of apps and models
    APP_MODEL_ORDER = {
        'auth': {  # App label
            'symbol': '(A)',
            'models': {  # Models order
                'group': '1',
                'user': '2',
            }
        },
        'core': {
            'symbol': '@B',
            'models': {                
                'Tenant': '1',
                'TenantLocation': '2',
                'TenantSetup': '3',
                'UserProfile': '4',
            }
        },
        'crm': {
            'symbol': 'C',
            'models': {                
            }
        },
        'meeting': {
            'symbol': 'M',
            'models': {   
                'Meeting': '1',
                'Agenda': '2'           
            }
        }, 
        'vault': {
            'symbol': 'V',
            'models': {  
                'RegistrationPlanCanton': '1'
            }
        },  
        'accounting': {
            'symbol': 'A',
            'models': {
                'Location': '0',
                'ChartOfAccountsCanton': '1',
                'AccountPositionCanton': '2',
                'AccountChartMunicipality': '3',
                'AccountPositionMunicipality': '4'                
            }
        },
        'billing': {
            'symbol': 'B',
            'models': {                
            }
        },            
    }


CANTON_CHOICES = [
    ('AG', _('Aargau')),
    ('AI', _('Appenzell Innerrhoden')),
    ('AR', _('Appenzell Ausserrhoden')),
    ('BS', _('Basel-Stadt')),
    ('BL', _('Basel-Landschaft')),
    ('BE', _('Bern')),
    ('FR', _('Fribourg')),
    ('GE', _('Genf')),
    ('GL', _('Glarus')),
    ('GR', _('Graubünden')),
    ('JU', _('Jura')),    
    ('LU', _('Luzern')),
    ('NE', _('Neuenburg')),
    ('NW', _('Nidwalden')),
    ('OW', _('Obwalden')),
    ('SH', _('Schaffhausen')),
    ('SZ', _('Schwyz')),
    ('SO', _('Solothurn')),
    ('SG', _('St. Gallen')),
    ('TG', _('Thurgau')),
    ('UR', _('Uri')),
    ('VD', _('Waadt')),
    ('VS', _('Wallis')),
    ('ZG', _('Zug')),
    ('ZH', _('Zürich'))
]


COUNTRY_CHOICES = [
    ('CH', _('Schweiz'))
]
