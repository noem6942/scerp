from django.utils.translation import gettext_lazy as _


class APP:
    id = 'M01'
    name = 'core'
    verbose_name = _('Basis')
    app_separatur = ' '
    model_separatur = '. '
    show_app_id = True
    show_model_id = True


# Abastracts
class LOG_ABSTRACT:    
    verbose_name = None
    verbose_name_plural = None
    
    class Field:
        created_at = {
            'verbose_name': _('created at'),
            'help_text': ''
        }
        created_by = {
            'verbose_name': _('created by'),
            'help_text': ''
        }
        modified_at = {
            'verbose_name': _('modified at'),
            'help_text': ''
        }
        modified_by = {
            'verbose_name': _('modified by'),
            'help_text': ''
        }


class NOTES_ABSTRACT:    
    verbose_name = None
    verbose_name_plural = None
    
    class Field:
        notes = {
            'verbose_name': _('notes'),
            'help_text': _('notes to the record'),
        }
        attachment = {
            'verbose_name': _('attachment'),
            'help_text': _('attachment for evidence'),
        }
        inactive = {
            'verbose_name': _('inactive'),
            'help_text': _('item is not active anymore (but not permanently deleted)'),
        }
        protected = {
            'verbose_name': _('protected'),
            'help_text': _('item must not be changed anymore'),
        }
        version = {
            'verbose_name': _('version'),
            'help_text': _('previous_version'),
        }


class TENANT_ABSTRACT:    
    verbose_name = None
    verbose_name_plural = None
    
    class Field:
        tenant = {
            'verbose_name': _('tenant'),
            'help_text': _('assignment of tenant / client')
        }

class CITY_CATEGORY:    
    verbose_name = _('city category')
    verbose_name_plural = _('city categories')
    
    class Field:
        abbreviation = {
            'verbose_name': _('abbreviation'),
            'help_text': _('abbreviation (max 2 letters)')
        }
        name = {
            'verbose_name': _('name'),
            'help_text': _('name')
        }


class TENANT: 
    verbose_name = _('tenant')
    verbose_name_plural = _('tenants')
    
    class Field:
        name = {
            'verbose_name': _('name'),
            'help_text': _('name of tenant / client (unique)')
        }
        code = {
            'verbose_name': _('code'),
            'help_text': _(
                'code of tenant / client, unique, max 32 characters, '
                'only small letters, should only contains characters that '
                'can be displayed in an url)')
        }
        is_trustee = {
            'verbose_name': _('is trustee'),
            'help_text': _(
                'Check if this is the trustee account that can created new tenants')
        }


class TENANT_SETUP: 
    verbose_name = _('tenant setup')
    verbose_name_plural =  _('tenant setups')
    
    class Field:
        canton = {
            'verbose_name': _('canton'),
            'help_text': _('canton')
        }
        category = {
            'verbose_name': _('category'),
            'help_text': _('category, add new one of no match')
        }
        formats = {
            'verbose_name': _('formats'),
            'help_text': _('format definitions')
        }
        logo = {
            'verbose_name': _('logo'),
            'help_text': _('logo used in website')
        }
        users = {
            'verbose_name': _('users'),
            'help_text': _('users for this organization')
        }


class PERSON:
    verbose_name = _('person')
    verbose_name_plural =  _('person')
    
    class Field:
        first_name = {
            'verbose_name': _('First Name'),
            'help_text': _('Fill out the first name.')
        }
        last_name = {
            'verbose_name': _('Last Name'),
            'help_text': _('Fill out the last name.')
        }
        date_of_birth = {
            'verbose_name': _('Date of Birth'),
            'help_text': _('Fill out the date of birth.')
        }


class USER_PROFILE:
    verbose_name = _('User')
    verbose_name_plural =  _('Users')
    
    class Field:
        user = {
            'verbose_name': _('user'),
            'help_text': _('Registered User')
        }
        photo = {
            'verbose_name': _('photo'),
            'help_text': _('Load up your personal photo.')
        }
        primary_tenant = {
            'verbose_name': _('Tenant'),
            'help_text': _('Tenant of your employer')
        }
        additional_tenants = {
            'verbose_name': _('Clients'),
            'help_text': _("Clients you're working for. ")
        }
