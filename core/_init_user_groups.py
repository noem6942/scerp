# core/init_user_groups.py

USER_GROUPS = [
    # Testing
    {'name': 'local_user', 'permissions': []},

    # Funktionen
    {'name': 'Funktion Zweckverband', 'permissions': []},

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
    {'name': 'Gemeinderatspräsident', 'permissions': []},
    {'name': 'Gemeinderatspräsidentin', 'permissions': []},
    {'name': 'Gemeinderatsschreiber', 'permissions': []},
    {'name': 'Gemeinderatsschreiberin', 'permissions': []},
    {'name': 'Stadtpräsident', 'permissions': []},
    {'name': 'Stadtpräsidentin', 'permissions': []},

    # Intern
    {'name': 'Admin', 'permissions': []},
    {'name': 'Intern Leitung', 'permissions': []},
    {'name': 'Intern Kanzlei', 'permissions': []},
    {'name': 'Intern Einwohnerdienste', 'permissions': []},
    {'name': 'Intern Personalwesen', 'permissions': []},
    {'name': 'Intern Gesundheit-/Sozialwesen', 'permissions': []},
    {'name': 'Intern Finanzen', 'permissions': []},
    {'name': 'Intern Steuern', 'permissions': []},
    {'name': 'Intern Liegenschaftsverwaltung', 'permissions': []},
    {'name': 'Intern Bauwesen', 'permissions': []},
    {'name': 'Intern Bildung', 'permissions': []},]
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