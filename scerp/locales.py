# scerp/locales.py
from django.utils.translation import gettext_lazy as _


class APP:
    verbose_name = _('SC-ERP - das Schweizer City ERP')
    title = _('SC-ERP - das Schweizer City ERP')
    welcome = _('Willkommen!')
    
    # Names of models in sitebar
    order_models = [
        # core
        'Tenant',
        'TenantSetup',
        'UserProfile',
        'Person',
        
        # accounting
        # 'APISetup',
        'ChartOfAccountsCanton',
        'AccountPositionCanton',
        'AccountChartMunicipality',        
        'AccountPositionMunicipality',
        
    ]    


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


LANGUAGE_CHOICES = [
    ('de', _('Deutsch')),
    ('fr', _('Französisch')),
    ('it', _('Italienisch')),
    ('en', _('Englisch')),
]


class ACTION:
    pass
