# vault/locales.py
from django.utils.translation import gettext_lazy as _


class APP:
    name = 'vault'
    verbose_name = _('Vault')


class REGISTRATION_PLAN:
    verbose_name = _('Registration Plan (Canton)')
    verbose_name_plural = _('Registration Plans (Canton)')

    class Field:
        name = {
            'verbose_name': _('Name'),
            'help_text': _('Enter the name of the registration plan')
        }
        canton = {
            'verbose_name': _('Canton'),
            'help_text': _('Select the associated canton for this registration plan.')
        }
        category = {
            'verbose_name': _('Category'),
            'help_text': _('Choose the category from the available city options.')
        }
        plan_version = {
            'verbose_name': _('Plan Version'),
            'help_text': _('Specify the version of the registration plan.')
        }
        date = {
            'verbose_name': _('Date'),
            'help_text': _('Enter the date for this registration plan record.')
        }
        excel = {
            'verbose_name': _('Excel File'),
            'help_text': _('Upload the Excel file associated with this registration plan.')
        }
        exported_at = {
            'verbose_name': _('Exported At'),
            'help_text': _('Record the date and time this plan use to create positions.')
        }



# ACCOUNT_POSITION dictionary for documentation
class ACCOUNT_POSITION:

    class Field:
        chart_of_accounts = {
            'verbose_name': _('Chart of Accounts'),
            'help_text': _('Link to the relevant chart of accounts')
        }
        account_number = {
            'verbose_name': _('Account Number'),
            'help_text': _('Unique identifier for the account')
        }
        account_4_plus_2 = {
            'verbose_name': _('Account 4+2'),
            'help_text': _('Account identifier with 4 main digits and 2 sub-digits')
        }
        name = {
            'verbose_name': _('Description'),
            'help_text': _('Description of the account')
        }
        hrm_1 = {
            'verbose_name': _('HRM1'),
            'help_text': _('HRM1 account identifier if applicable')
        }
        description_hrm_1 = {
            'verbose_name': _('HRM1 Notes'),
            'help_text': _('Notes related to HRM1 account')
        }
        account = {
            'verbose_name': _('account'),
            'help_text': _('Calculated account for sorting')
        }
        ff = {
            'verbose_name': _('FF'),
            'help_text': _('Flag indicating functional feature status')
        }
        is_category = {
            'verbose_name': _('is category'),
            'help_text': _('Flag indicating position is category')
        }
        hrm_2 = {
            'verbose_name': _('HRM 2'),
            'help_text': _('HRM 2 identifier if available')
        }
        hrm_2_short = {
            'verbose_name': _('HRM 2 Short'),
            'help_text': _('Shortened HRM 2 identifier')
        }
        number = {
            'verbose_name': _('Number'),
            'help_text': _('Calculated account number for reference')
        }        


class ACCOUNT_POSITION_CANTON:
    verbose_name = _('Account Position (Canton)')
    verbose_name_plural = _('Account Positions (Canton)')


class ACCOUNT_CHART_MUNICIPALITY:
    verbose_name = _('Account Chart (Municipality)')
    verbose_name_plural = _('Account Charts (Municipality)')

    class Field:
        name = {
            'verbose_name': _('name'),
            'help_text': _('Unique name of accounting chart. Also used for '
                           'versioning.')
        }
        period = {
            'verbose_name': _('period'),
            'help_text': _('Fiscal period')
        }


class ACCOUNT_POSITION_MUNICIPALITY:
    verbose_name = ('Account Position (Municipality)')
    verbose_name_plural = _('Account Positions (Municipality)')

    class Field:
        display_type = {
            'verbose_name': _('Chart Type'),
            'help_text': _('Show position in one or more selection. Choices: see Type')
        }
        chart = {
            'verbose_name': _('Chart'),  # Change 'chart' to 'verbose_name'
            'help_text': _('Chart the position belongs to')
        }
        function = {
            'verbose_name': _('Function'),
            'help_text': _('Function code related to account type')
        }            

class ACTION:    
    # RegistrationPlanCanton
    canton_positions_check = _('Check Excel for validity')
    canton_positions_create = _('Create positions from Excel')
    position_insert = _('Insert copy of record below')
    

class FIELDSET:
    content = _('Content')
    others = _('Others')
