'''core/init_permissions.py
'''
USER_GROUP_TRUSTEE = 'Extern Treuhand'
USER_GROUP_TEST = 'zzz_test~'

USER_GROUPS = [
    # Intern    
    {'name': 'Intern Leitung', 'permissions': []},
    {'name': 'Intern Kanzlei', 'permissions': []},
    {'name': 'Intern Einwohnerdienste', 'permissions': []},
    {'name': 'Intern Personalwesen', 'permissions': []},
    {'name': 'Intern Gesundheit-/Sozialwesen', 'permissions': []},
    {'name': 'Intern Finanzen', 'permissions': []},
    {'name': 'Intern Steuern', 'permissions': []},
    {'name': 'Intern Liegenschaftsverwaltung', 'permissions': []},
    {'name': 'Intern Bauwesen', 'permissions': []},
    {'name': 'Intern Bildung', 'permissions': []},

    # Funktionen
    {'name': 'Funktion Zweckverband', 'permissions': []},

    # Bürgerrat
    {'name': 'Bürgerrat', 'permissions': []},

    # Gemeinderat
    {'name': 'Gemeinderat', 'permissions': []},
    {'name': 'Gemeinderat - Präsidiales', 'permissions': []},
    {'name': 'Gemeinderat - Finanzen', 'permissions': []},
    {'name': 'Gemeinderat - Sicherheit', 'permissions': []},
    {'name': 'Gemeinderat - Soziales', 'permissions': []},
    {'name': 'Gemeinderat - Planung/Wirtschaft/Tourismus', 'permissions': []},
    {'name': 'Gemeinderat - Hoch-/Tiefbau', 'permissions': []},
    {'name': 'Gemeinderat - Bildung/Kultur', 'permissions': []},

    # Rollen
    {'name': 'Bürgergemeindepräsident', 'permissions': []},    
    {'name': 'Bürgergemeindepräsidentin', 'permissions': []},   
    {'name': 'Bürgerratspräsident', 'permissions': []},    
    {'name': 'Bürgerratspräsidentin', 'permissions': []},  
    {'name': 'Bürgerschreiber', 'permissions': []},
    {'name': 'Bürgerschreiberin', 'permissions': []},  
    {'name': 'Gemeinderatspräsident', 'permissions': []},
    {'name': 'Gemeinderatspräsidentin', 'permissions': []},
    {'name': 'Gemeinderatsschreiber', 'permissions': []},
    {'name': 'Gemeinderatsschreiberin', 'permissions': []},
    {'name': 'Stadtpräsident', 'permissions': []},
    {'name': 'Stadtpräsidentin', 'permissions': []},
    {'name': 'Präsident Wasserkommission', 'permissions': []},
    {'name': 'Präsidentin Wasserkommission', 'permissions': []},
    {'name': 'Externer Experte', 'permissions': []},
    {'name': 'Externer Expertin', 'permissions': []},
    {'name': 'Extern IT', 'permissions': []},
    {'name': 'Extern Revision', 'permissions': []},    

    # Special
    {'name': USER_GROUP_TRUSTEE, 'permissions': []},
    {'name': USER_GROUP_TEST, 'permissions': []},
]


class PERMISSIONS:
    TRUSTEE = {
        'exceptions': [
            ('Model', 'apisetup'),
            ('Model', 'app'),
            ('Model', 'mappingid'),
            ('Permission', 'add_group'),
            ('Permission', 'change_group'),
            ('Permission', 'delete_group'),
            ('Permission', 'add_permission'),
            ('Permission', 'change_permission'),
            ('Permission', 'delete_permission'),
            ('Permission', 'delete_user'),
            ('Permission', 'change_logentry'),
            ('Permission', 'delete_logentry'),
            ('Permission', 'delete_message'),
            ('Permission', 'add_tenant'),
            ('Permission', 'change_tenant'),
            ('Permission', 'delete_tenant'),
            ('Permission', 'delete_tenantsetup'),
        ]
    }
