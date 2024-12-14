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
            'is_mandatory': True,
            'models': {  # Models order
                'group': '1',
                'user': '2',
            }
        },
        'core': {
            'symbol': '@',
            'is_mandatory': True,
            'models': {                
                'Tenant': '1',
                'TenantLocation': '2',
                'TenantSetup': '3',
                'UserProfile': '4',
            }
        },
        'crm': {
            'symbol': 'C',
            'is_mandatory': True,
            'models': {                
            }
        },
        'meeting': {
            'symbol': 'M',
            'is_mandatory': False,
            'models': {   
                'Meeting': '1',
                'Agenda': '2'           
            }
        }, 
        'vault': {
            'symbol': 'V',
            'is_mandatory': False,
            'models': {  
                'RegistrationPlanCanton': '1',
                'RegistrationPositionCanton': '2'
            }
        },  
        'accounting': {
            'symbol': 'A',
            'is_mandatory': False,
            'models': {
                'APISetup': '0',
                'Location': '10',
                'FiscalPeriod': '11',
                'ChartOfAccountsTemplate': '20',
                'AccountPositionTemplate': '21',
                'ChartOfAccounts': '32',
                'AccountPosition': '33'                
            }
        },
        'billing': {
            'symbol': 'B',
            'is_mandatory': False,
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
