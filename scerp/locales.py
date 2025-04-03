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
            'Message': ('', ''),
            'Tenant': ('', ''),
            'TenantLocation': ('', ''),
            'TenantSetup': ('', ''),
            'TenantLogo': ('', ''),
            'UserProfile': ('', ''),
            'AddressCategory': ('', ''),
            'Address': ('', ''),
            'Title': ('', ''),
            'PersonCategory': ('', ''),
            'Person': ('', ''),
            'PersonAddress': ('', ''),
            'Building': ('', ''),
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
            # Operational
            # 'IncomingOrder': ('2', ''),
            # 'OrderContract': ('1', ''),

            # # Creditor Setups
            # 'OrderCategoryContract': ('', ''),
            # 'OrderCategoryIncoming': ('', ''),

            # # Admin
            # 'APISetup': ('', ''),
            # 'CustomFieldGroup': ('', ''),
            # 'CustomField':('', ''),
            # 'Setting': ('', ''),

            # # Accounting Admin
            # 'Location': ('', ''),
            # 'BankAccount': ('', ''),
            # 'CostCenterCategory': ('', ''),
            # 'CostCenter': ('', ''),
            # 'Currency': ('', ''),
            # 'Tax': ('', ''),
            # 'Rounding': ('', ''),
            # 'SequenceNumber': ('', ''),
            # 'Unit': ('', ''),

            # # CRM Admin
            # 'Title': ('', ''),
            # 'PersonCategory': ('', ''),
            # 'Person': ('', ''),

            # # Order Management
            # 'OrderTemplate': ('', ''),
            # 'BookTemplate': ('', ''),
            # 'IncomingBookEntry': ('', ''),
            # 'OrderTemplate': ('', ''),
            # 'ArticleCategory': ('', ''),
            # 'Article': ('', ''),

            # # Accounting
            # 'FiscalPeriod': ('', ''),
            # 'AccountCategory': ('', ''),
            # 'Account': ('', ''),
            # 'Ledger': ('', ''),
            # 'LedgerBalance': ('', ''),
            # 'LedgerPL': ('', ''),
            # 'LedgerIC': ('', ''),

            # # Inventory
            # 'ChartOfAccountsTemplate': ('', ''),
            # 'AccountPositionTemplate': ('', ''),
            # 'ChartOfAccounts': ('', ''),
            # #'AccountPosition': ('', ''),
        }
    },
    'asset': {
        'symbol': 'AT',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
            'AssetCategory': ('', ''),
            'Device': ('', ''),
            'EventLog': ('', ''),
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
