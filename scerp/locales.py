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
        'needs_tenant': False,
        'models': {  # Models order, postfix
            'group': ('1', ''),
            'user': ('2', '')
        }
    },
    'core': {
        'symbol': '@',
        'is_mandatory': True,
        'needs_tenant': False,
        'models': {
            'Message': ('1', ''),
            'Tenant': ('2', ''),
            'TenantLocation': ('3', ''),
            'TenantSetup': ('4', ''),
            'TenantLogo': ('5', ''),
            'UserProfile': ('6', ''),        
            'AddressCategory': ('21', ''),
            'Title': ('22', ''),
            'PersonCategory': ('23', ''),
            'Person': ('24', ''),         
            'Building': ('25', ''),               
        }
    },
    'crm': {
        'symbol': 'C',
        'is_mandatory': True,
        'needs_tenant': True,
        'models': {
        }
    },
    'meeting': {
        'symbol': 'M',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            'Meeting': ('1', ''),
            'Agenda': ('2',  '')
        }
    },
    'vault': {
        'symbol': 'V',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            'RegistrationPlanCanton': ('1', ''),
            'RegistrationPositionCanton': ('2', '')
        }
    },
    'accounting': {
        'symbol': 'A',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            # Admin
            'APISetup': ('Setup 01', ''),
            'CustomFieldGroup': ('Setup 02', ''),
            'CustomField': ('Setup 03', ''),
            'Setting': ('Setup 04', ' ⬇️'),

            # Accounting Admin
            'Location': ('Settings 01', ' ⬇️'),
            'CostCenterCategory': ('Settings 02', ''),
            'CostCenter': ('Settings 03', ''),

            'Currency': ('Settings 04', ''),
            'Tax': ('Settings 05', ''),
            'Rounding': ('Settings 06', ' ⬇️'),
            'SequenceNumber': ('Settings 07', ' ⬇️'),
            'Unit': ('Settings 08', ''),

            # CRM Admin
            'Title': ('22', ''),
            'PersonCategory': ('23', ''),
            'Person': ('24', ''),

            # Order Management
            'OrderTemplate': ('O. 14', ''),
            'BookTemplate': ('O. 15', ''),
            'OrderCategoryContract': ('O. 16', ''),
            'OrderCategoryIncoming': ('O. 17', ''),
            'OrderContract': ('O. 18', ''),
            'IncomingOrder': ('O. 19', ''),
            'IncomingBookEntry': ('O. 20', ''),
            'OrderTemplate': ('O. 21', ''),
            'ArticleCategory': ('O. 22', ''),
            'Article': ('O. 23', ''),

            # Accounting
            'FiscalPeriod': ('* 18', ' ⬇️'),
            'AccountCategory': ('L 19', ' ⬇️'),
            'Account': ('L 20', ' ⬇️'),
            'Ledger': ('L 21', ''),
            'LedgerBalance': ('L 22', ''),
            'LedgerPL': ('L 23', ''),
            'LedgerIC': ('L 24', ''),

            # Inventory
            'ChartOfAccountsTemplate': ('C 31', ''),
            'AccountPositionTemplate': ('C 11', ''),
            'ChartOfAccounts': ('C 42', ''),
            #'AccountPosition': ('C 43', ''),            
        }
    },
    'asset': {
        'symbol': 'AT',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            'AssetCategory': ('1', ''),
            'Device': ('2', ''),
            'EventLog': ('3', ''),
        }
    },
    'billing': {
        'symbol': 'B',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            'Period': ('1', ''),
            'Route': ('2', ''),
            'Measurement': ('3', ''),
            'Subscriptions': ('4', ''),
        }
    },
    'time_app': {
        'symbol': 'T',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            'Workspace': ('1', ''),
            'ClockifyUser': ('2', ''),
            'Tag': ('3', ''),
            'Client': ('4', ''),
            'Project': ('5', ''),
            'TimeEntry': ('6', '')
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
