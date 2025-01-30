'''
accounting/init_cash_ctrl.py

Definition of all data that is used for a new api setup,
    triggered by signals.py
    
pylint check: 2024-12-24
'''
from .api_cash_ctrl import (
    value_to_xml, ADDRESS_TYPE, CONTACT_TYPE, BOOK_TYPE, COLOR, ORDER_TYPE,
    FIELD_TYPE, DATA_TYPE, TOP_LEVEL_ACCOUNT_CATEGORY
)

# RUN 1 - no other data needed -------------------------------------------
CUSTOM_FIELD_GROUPS = [{
    'key': 'account_tab',
    'type': FIELD_TYPE.ACCOUNT,
    'name': {
        'de': 'SC-ERP',
        'en': 'SC-ERP',
        'fr': 'SC-ERP',
        'it': 'SC-ERP'
    }
}, {
    'key': 'order_tab',
    'type': FIELD_TYPE.ORDER,
    'name': {
        'de': 'SC-ERP',
        'en': 'SC-ERP',
        'fr': 'SC-ERP',
        'it': 'SC-ERP'
    }
}, {
    'key': 'person_tab',
    'type': FIELD_TYPE.PERSON,
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
    'data_type': DATA_TYPE.TEXT,
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
    'data_type': DATA_TYPE.TEXT,
    'is_multi': False,
    'values': []
}, {
    'key': 'order_period',
    'group_key': 'order_tab',
    'name': {
        'de': 'Abrechnungsperiode',
        'en': 'Period',
        'fr': 'Period',
        'it': 'Period'
    },
    'data_type': DATA_TYPE.TEXT,
    'is_multi': False,
    'values': []
}, {
    'key': 'order_counter_id',
    'group_key': 'order_tab',
    'name': {
        'de': 'Zähler-ID',
        'en': 'Function',
        'fr': 'Fonction',
        'it': 'Funzione'
    },
    'data_type': DATA_TYPE.TEXT,
    'is_multi': False,
    'values': []
}, {
    'key': 'order_counter_actual',
    'group_key': 'order_tab',
    'name': {
        'de': 'Zählerstand aktuell',
        'en': 'Function',
        'fr': 'Fonction',
        'it': 'Funzione'
    },
    'data_type': DATA_TYPE.NUMBER,
    'is_multi': False,
    'values': []
}, {
    'key': 'order_counter_past',
    'group_key': 'order_tab',
    'name': {
        'de': 'Zählerstand vorher',
        'en': 'Function',
        'fr': 'Fonction',
        'it': 'Funzione'
    },
    'data_type': DATA_TYPE.NUMBER,
    'is_multi': False,
    'values': []
}, {
    'key': 'order_object',
    'group_key': 'order_tab',
    'name': {
        'de': 'Objekt',
        'en': 'Function',
        'fr': 'Fonction',
        'it': 'Funzione'
    },
    'data_type': DATA_TYPE.TEXT,
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
    'data_type': DATA_TYPE.ACCOUNT,
    'is_multi': True,
    'values': []
}]


        'de': 'Erfolgsrechnung',
        'en': 'P&L',
        'fr': 'Compte de résultat',
        'it': 'Conto economico'       

        'de': 'Investitionsrechnung',
        'en': 'Investment Statement',
        'fr': 'Compte d’investissement',
        'it': 'Conto degli investimenti'

ACCOUNT_CATEGORIES = [{
    'number': 3.1,
    'parent_number': TOP_LEVEL_ACCOUNT_CATEGORY.EXPENSE,
    'name': {
        'de': 'Aufwand (ER)',
        'en': 'Expense (P&L)',
        'fr': 'Dépense',
        'it': 'Spesa'
    }
}, {
    'number': 4.1,
    'parent_number': TOP_LEVEL_ACCOUNT_CATEGORY.REVENUE,
    'name': {
        'de': 'Ertrag (ER)',
        'en': 'Income (P&L)',
        'fr': 'Revenu (CR)',
        'it': 'Reddito (CE)'
    }
}, {
    'number': 3.2,
    'parent_number': TOP_LEVEL_ACCOUNT_CATEGORY.EXPENSE,
    'name': {
        'de': 'Ausgaben (IV)',
        'en': 'Expenses (IS)',
        'fr': 'Dépenses (CR)',
        'it': 'Spese (CE)'
    }
}, {
    'number': 4.2,
    'parent_number': TOP_LEVEL_ACCOUNT_CATEGORY.REVENUE,
    'name': {
        'de': 'Einnahmen (IV)',
        'en': 'Revenue (IS)',
        'fr': 'Revenus (CI)',
        'it': 'Entrate (CI)'
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
    'key': 'sac',
    'name': {'values': {
        'de': 'Kundenservice',
        'en': 'Customer Service',
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


# RUN 2 - previous data needed -------------------------------------------
def persons(**kwargs):
    category_id = kwargs.get('category_id')  # Sachbearbeiter

    return [{
        'category_id': category_id, 
        'first_name': None, 
        'last_name': 'BDO AG, 4600 Olten', 
        'company': 'BDO', 
        'addresses': [{
            'type': ADDRESS_TYPE.MAIN,
            'zip': '4600', 
            'city': 'Olten', 
            'country': 'CHE', 
        }],
        'contacts': [{
            'address': 'bz-gunzgen@bdo.ch',
            'type': CONTACT_TYPE.EMAIL_WORK,
        }, {
            'address': '062 387 95 29',
            'type': CONTACT_TYPE.PHONE_WORK,
        }],
        'color': COLOR.BLUE
    }]


def order_categories(**kwargs):
    account_id = kwargs.get('account_id')  # 714
    rounding_id = kwargs.get('rounding_id')  #  1
    sequence_nr_id = kwargs.get('sequence_nr_id')  #  1
    responsible_person_id = kwargs.get('responsible_person_id')  #  3
    template_id = kwargs.get('template_id')  #  1000

    return [{
        'account_id': account_id, 
        'name_singular': {'values': {
            'de': 'Rechnung Test',
            'en': 'Invoice', 
            'fr': 'Facture', 
            'it': 'Fattura'}}, 
        'name_plural': {'values': {
            'de': 'Rechnungen Test', 
            'en': 'Invoices', 
            'fr': 'Factures', 
            'it': 'Fatture'}},
        'status': [{
            'icon': COLOR.GRAY,
            'name': process_to_xml({'values': {
                'de': 'Entwurf',
                'en': 'Draft', 
                'fr': 'Projet', 
                'it': 'Progetto'}}) 
        }, {
            'icon': COLOR.BLUE,
            'name': process_to_xml({'values': {
                'de': 'Gewonnen',
                'en': 'Won', 
                'fr': 'Won', 
                'it': 'Won'}})
        }],
        'address_type': ADDRESS_TYPE.INVOICE,  # default is 'MAIN', ensure there is always an INVOICE address
        # 'book_templates, 
        'book_type': BOOK_TYPE.DEBIT, 
        'due_days': 30, 
        'footer': '<i>Rechtsmittel: Wasser - schriftlich innert 10 Tagen an die Wasserkommission der BürgergemeindeGunzgenAbwasser - schriftlich innert 10 Tagen an den Einwohnergemeinderat Gunzgen</i>',
        'header': '''Kontakt:<br>
            Tel. 062 387 95 29<br>
            E-Mail: bz-gunzgen@bdo.ch<br>
            <br>
            Abrechnungsperiode: $customField27<br>
            Objekt: $customField30<br>
            Zählernummer: $customField30<br>
            Zählerstand neu: $customField28 m³ (alt $customField29 m³)''', 
        'is_display_prices': True, 
        'is_display_item_gross': False, 
        'responsible_person_id': responsible_person_id,  # Sachbearbeiter
        'rounding_id': rounding_id,  # auf 0.05 runden
        'sequence_nr_id': sequence_nr_id,  # RE ...
        'template_id': template_id, 
        'type': ORDER_TYPE.SALES
    }] 
