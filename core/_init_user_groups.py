# core/init_user_groups.py

ADMIN_GROUP_NAME = 'Admin'

USER_GROUPS = [
    # Intern
    {'name': ADMIN_GROUP_NAME, 'permissions': []},  # must be first
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
    {'name': 'Extern Treuhand', 'permissions': []},

    # Testing
    {'name': 'local_user', 'permissions': []},
]

'''
    {'name': 'local_admin', 'permissions': [
    'core.add_person',
    'core.change_person',
    'core.delete_person',
    'core.view_person',

    'core.add_userprofile',
    'core.change_userprofile',
    'core.delete_userprofile',
    'core.view_userprofile',

    'auth.add_user',
    'auth.change_user',
    'auth.delete_user',
    'auth.view_user',]},
'''