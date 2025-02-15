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
            'UserProfile': ('6', '')
        }
    },
    'crm': {
        'symbol': 'C',
        'is_mandatory': True,
        'needs_tenant': True,
        'models': {
            'Title': ('1', ''),
            'Subscriber': ('2', ''),
            'Employee': ('3', ''),
            'BusinessPartner': ('4', '')
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
            'APISetup': ('* 01', ''),
            'CustomFieldGroup': ('* 02', ''),
            'CustomField': ('* 03', ''),
            'Setting': ('* 04', ' ⬇️'),

            # Accounting Admin
            'Location': ('* 10', ' ⬇️'),
            'CostCenterCategory': ('* 11', ''),
            'CostCenter': ('* 12', ''),

            'Currency': ('* 13', ''),
            'Tax': ('* 14', ''),
            'Rounding': ('* 15', ' ⬇️'),
            'SequenceNumber': ('* 16', ' ⬇️'),
            'Unit': ('* 17', ''),

            # CRM Admin
            'Title': ('22', ''),
            'PersonCategory': ('23', ''),
            'Person': ('24', ''),

            # Order Management
            'BookTemplate': ('O. 15', ''),
            'OrderCategoryContract': ('O. 16', ''),
            'OrderCategoryIncoming': ('O. 17', ''),
            'ContractOrder': ('O. 18', ''),
            'IncomingOrder': ('O. 19', ''),
            'OrderTemplate': ('O. 20', ''),
            'ArticleCategory': ('O. 21', ''),
            'Article': ('O. 22', ''),

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

    'billing': {
        'symbol': 'B',
        'is_mandatory': False,
        'needs_tenant': True,
        'models': {
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
