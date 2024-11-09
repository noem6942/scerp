from django.utils.translation import gettext_lazy as _


class APP:
    id = 'M04'
    name = 'billing'
    verbose_name = _('Billing')
    app_separatur = ' '
    model_separatur = '. '
    show_app_id = True
    show_model_id = True


class COUNTER:    
    verbose_name = _('city category')
    verbose_name_plural = _('city categories')
    
    class Field:
        nr = {
            'verbose_name': _('nr'),
            'help_text': _('nr')
        }
        function = {
            'verbose_name': _('function'),
            'help_text': _('function')
        }
        jg = {
            'verbose_name': _('jg'),
            'help_text': _('jg')
        }
