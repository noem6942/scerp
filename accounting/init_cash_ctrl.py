'''
accounting/init_cash_ctrl.py

Definition of all data that is used for a new api setup,
    triggered by signals.py
    
pylint check: 2024-12-24
'''

CUSTOM_FIELD_GROUPS = [{
    'key': 'account_tab',
    'type': 'ACCOUNT',
    'name': {
        'de': 'SC-ERP',
        'en': 'SC-ERP',
        'fr': 'SC-ERP',
        'it': 'SC-ERP'
    }
}, {
    'key': 'person_tab',
    'type': 'PERSON',
    'name': {
        'de': 'SC-ERP',
        'en': 'SC-ERP',
        'fr': 'SC-ERP',
        'it': 'SC-ERP'
    }
}]


CUSTOM_FIELDS = [{
    'key': 'account_hrm',
    'group_key': 'account_tab',
    'name': {
        'de': 'HRM',
        'en': 'HRM',
        'fr': 'HRM',
        'it': 'HRM'
    },
    'data_type': 'TEXT',
    'is_multi': False,
    'values': []
}, {
    'key': 'account_function',
    'group_key': 'account_tab',
    'name': {
        'de': 'Funktion',
        'en': 'Function',
        'fr': 'Fonction',
        'it': 'Funzione'
    },
    'data_type': 'TEXT',
    'is_multi': False,
    'values': []
}, {
    'key': 'person_category',
    'group_key': 'person_tab',
    'name': {
        'de': 'Kategorie',
        'en': 'Category',
        'fr': 'Fonction',
        'it': 'Funzione'
    },
    'data_type': 'TEXT',
    'is_multi': False,
    'values': []
}]


ACCOUNT_CATEGORIES = [{
    'key': 'p&l_expense',
    'top':'EXPENSE',
    'name': {
        'de': 'Erfolgsrechnung',
        'en': 'P&L',
        'fr': 'Compte de résultat',
        'it': 'Conto economico'
    }
}, {
    'key':'p&l_revenue',
    'top':'REVENUE',
    'name': {
        'de': 'Erfolgsrechnung',
        'en': 'P&L',
        'fr': 'Compte de résultat',
        'it': 'Conto economico'
    }
}, {
    'key':'is_expense',
    'top':'EXPENSE',
    'name': {
        'de': 'Investitionsrechnung',
        'en': 'Investment Statement',
        'fr': 'Compte d’investissement',
        'it': 'Conto degli investimenti'
    }
}, {
    'key':'is_revenue',
    'top':'REVENUE',
    'name': {
        'de': 'Investitionsrechnung',
        'en': 'Investment Statement',
        'fr': 'Compte d’investissement',
        'it': 'Conto degli investimenti'
    }
}]


# PERSON CATEGORIES are always top level
PERSON_CATEGORIES = [{
    'key': 'subscriber',
    'name': {'values': {
        'de': '*Abonnenten',
        'en': '*Subscribers',
        'fr': '*Subscribers',
        'it': '*Subscribers'
    }},
}, {
    'key': 'disclaimer',
    'name': {'values': {
        'de': '__in scerp zu erfassen__',
        'en': '__enter in scerp__',
        'fr': '__enter in scerp__',
        'it': '__enter in scerp__'
    }},
}]


UNITS = [{
    'name':  {'values': {
        'de': 'm³',
        'en': 'm³',
        'fr': 'm³',
        'it': 'm³'}
    }
}]


LOCATION_MAIN = {
    'name':  {'values': {
        'de': 'Hauptsitz',
        'en': 'Headquarter',
        'fr': 'Headquarter',
        'it': 'Headquarter'}
    },
    'type': 'MAIN'
} 
LOCATIONS = [{
    'name':  {'values': {
        'de': f'MWST {i}',
        'en': f'VAT {i}',
        'fr': f'VAT {i}',
        'it': f'VAT {i}'}
    },
    'type': 'OTHER'
} for i in range(1,3)]
