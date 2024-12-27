'''
accounting/signals.py
'''
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import (
    APPLICATION, APISetup, AccountPosition, AccountPositionTemplate
    # not used: FiscalPeriod, Location
)
from .mixins import account_position_calc_number
from .process import ProcessCashCtrl


# helpers
def get_ctrl(instance=None, apiset=None):
    '''
    Get APISetup given an instance that has a tenant field
    '''
    if not apiset:
        try:
            apiset = APISetup.objects.get(tenant=instance.tenant)
        except APISetup.DoesNotExist as exc:  # Capture the original exception
            raise ValidationError(
                f"APISetup not found for tenant: {instance.tenant}"
            ) from exc  # Re-raise the original exception with the new one

    if apiset.application == APPLICATION.CASH_CTRL:
        return ProcessCashCtrl(apiset)
    
    raise ValidationError("No application found.")


@receiver(post_save, sender=APISetup)
def api_setup(sender, instance, created, **kwargs):
    """
    Perform follow-up actions when a new APISetup is created.
    """
    _ = sender  # disable pylint warning
    if created or kwargs.get('init', False):
        # Init -------------------------------------------------------------
        ctrl = get_ctrl(apiset=instance)
        
        # Create Custom Groups
        ctrl.init_custom_groups()

        # Create Custom Fields if not existing and update numbers in setup
        ctrl.init_custom_fields()
        
        # Create m³
        # ctrl.init_units()
        ""
        # Create Accounts, Persons
        ctrl.init_accounts()
        ctrl.init_persons()

        """
        # Settings
        # 'thousand_separator'
        ''' do this after first practice with invoices
            do this at the end
        '''
        settings = {
            'default_sequence_number_inventory_article': 2,
            'first_steps_account': True,
            'tax_accounting_method': 'AGREED',
            'first_steps_currency': True,
            'default_sequence_number_inventory_asset': 4,
            'default_opening_account_id': 37,
            'default_input_tax_adjustment_account_id': 173,
            'thousand_separator': '',
            'default_inventory_asset_revenue_account_id': 164,
            'order_mail_copy_to_me': True,
            'default_inventory_depreciation_account_id': 28,
            'default_sequence_number_person': 5,
            'first_steps_tax': True,
            'default_profit_allocation_account_id': 127,
            'journal_import_force_sequence_number': False,
            'default_sales_tax_adjustment_account_id': 174,
            'default_sequence_number_journal': 6,
            'first_steps_two_factor_auth': True,
            'default_inventory_article_revenue_account_id': 42,
            'default_inventory_article_expense_account_id': 45,
            'csv_delimiter': ';',
            'first_steps_opening_entries': False,
            'default_debtor_account_id': 4,
            'first_steps_tax_type': True,
            'default_inventory_disposal_account_id': 92,
            'first_steps_pro_demo': True,
            'first_steps_logo': True,
            'default_exchange_diff_account_id': 131,
            'default_creditor_account_id': 9
        }

        # Settings
        ctrl.get_settings()

        """
        # Location for VAT, Codes, Formats if not existing
        ctrl.get_locations()

        # FiscalPeriod: download first fiscal period if not existing
        ctrl.get_fiscal_periods()

        # Currencies
        ctrl.get_currencies()
        """

        # Units
        ctrl.get_units()

        """
        # Tax Rates
        # ctrl.get_tax()

        # Cost Center
        # ctrl.get_cost_centere()


@receiver(pre_save, sender=AccountPosition)
def account_position(sender, instance, *args, **kwargs):
    '''
    Update number before saving
    '''
    _ = sender  # disable pylint warning
    number = account_position_calc_number(
        instance.account_type,
        instance.function,
        instance.account_number,
        instance.is_category)
    instance.number = Decimal(number)


@receiver(pre_save, sender=AccountPositionTemplate)
def account_position_template(sender, instance, *args, **kwargs):
    '''
    Update number before saving
    '''
    _ = sender  # disable pylint warning
    function = None
    number = account_position_calc_number(
        instance.chart.account_type,
        function,
        instance.account_number,
        instance.is_category)
    instance.number = Decimal(number)
