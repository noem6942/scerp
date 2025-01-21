"""
scerp/locales.py

Central file for building up menus in admin.py
gets used by ./admin.py
"""
from django.utils.translation import gettext_lazy as _


APP_CONFIG = {
    'site_header': _('SC-ERP - das Schweizer City ERP'),
    'index_title': _('Willkommen!'),
    'site_title': _('SC-ERP - das Schweizer City ERP')
}


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
            'Message': ('1', None),
            'Tenant': ('2', None),
            'TenantLocation': ('3', None),
            'TenantSetup': ('4', None),
            'TenantLogo': ('5', None),
            'UserProfile': ('6', None)
        }
    },
    'crm': {
        'symbol': 'C',
        'is_mandatory': True,
        'models': {
            'Title': ('1', None),
            'Subscriber': ('2', None),
            'Employee': ('3', None),
            'BusinessPartner': ('4', None)
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
            'APISetup': ('01', None),
            'Setting': ('10', ' ⬇️'),
            'Location': ('11', ' ⬇️'),
            'FiscalPeriod': ('12', ' ⬇️'),
            'Currency': ('13', ' ⬇️'),
            'Unit': ('14', ' ⬇️'),
            'Tax': ('15', ' ⬇️'),
            'Rounding': ('16', ' ⬇️'),
            'SequenceNumber': ('17', ' ⬇️'),
            'OrderCategory': ('18', ' ⬇️'),
            'OrderTemplate': ('19', ' ⬇️'),
            'CostCenter': ('21', ' ⬇️'),
            'Article': ('22', ' ⬇️'),
            'ChartOfAccountsTemplate': ('C 20', None),
            'AccountPositionTemplate': ('C 21', None),
            'ChartOfAccounts': ('C 32', None),
            #'AccountPosition': ('C 33', None),
        }
    },
    'billing': {
        'symbol': 'B',
        'is_mandatory': False,
        'models': {
        }
    },
    'time_app': {
        'symbol': 'T',
        'is_mandatory': False,
        'models': {
            'Workspace': ('1', None),
            'ClockifyUser': ('2', None),
            'Tag': ('3', None),
            'Client': ('4', None),
            'Project': ('5', None),
            'TimeEntry': ('6', None)
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
