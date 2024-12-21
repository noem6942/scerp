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
            'models': {  # Models order, postfix
                'group': ('1', None),
                'user': ('2', None)
            }
        },
        'core': {
            'symbol': '@',
            'is_mandatory': True,
            'models': {                
                'Tenant': ('1', None),
                'TenantLocation': ('2', None),
                'TenantSetup': ('3', None),
                'UserProfile': ('4', None)
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
                'Meeting': ('1', None),
                'Agenda': ('2',  None)           
            }
        }, 
        'vault': {
            'symbol': 'V',
            'is_mandatory': False,
            'models': {  
                'RegistrationPlanCanton': ('1', None),
                'RegistrationPositionCanton': ('2', None)
            }
        },  
        'accounting': {
            'symbol': 'A',
            'is_mandatory': False,
            'models': {
                'APISetup': ('1', None),
                'Setting': ('10', ' ⬇️'),
                'Location': ('11', ' ⬇️'),
                'FiscalPeriod': ('12', ' ⬇️'),
                'Currency': ('13', ' ⬇️'),
                'Unit': ('14', ' ⬇️'),
                'Tax': ('15', ' ⬇️'),
                'CostCenter': ('16', ' ⬇️'),
                'ChartOfAccountsTemplate': ('20', None),
                'AccountPositionTemplate': ('21', None),
                'ChartOfAccounts': ('32', None),
                #'AccountPosition': ('33', None),     
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
