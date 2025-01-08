'''
accounting/signals.py
'''
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import (
    APPLICATION, ACCOUNT_TYPE, APISetup, AccountPosition, 
    AccountPositionTemplate, Location, FiscalPeriod
)
from .connector import get_connector_module
from .mixins import account_position_calc_number


@receiver(post_save, sender=APISetup)
def api_setup_post_save(sender, instance, created, **kwargs):
    """
    Perform follow-up actions when a new APISetup is created.
    """
    __ = sender  # disable pylint warning
    if created or kwargs.get('init', False): 
        api_setup, module = get_connector_module(api_setup=instance)

        # Init
        CLASSES = [
            module.CustomFieldGroupConn,
            module.CustomFieldConn,
            module.PersonConn,
            module.UnitConn,
            module.Account
        ]
        for cls in CLASSES:
            ctrl = cls(api_setup)
            ctrl.init()

        # Get initial data
        module.get_all(api_setup)        


@receiver(post_save, sender=FiscalPeriod)
def fiscal_period_post_save(sender, instance, created, **kwargs):
    pass  # Check if new current period and do updates


@receiver(pre_save, sender=AccountPosition)
def account_position(sender, instance, *args, **kwargs):
    '''
    Update number before saving
    '''
    __ = sender  # disable pylint warning
    function = (
        None if instance.account_type == ACCOUNT_TYPE.BALANCE
        else instance.function)
    number = account_position_calc_number(
        instance.account_type,
        function,
        instance.account_number,
        instance.is_category)
    instance.number = Decimal(number)


@receiver(pre_save, sender=AccountPositionTemplate)
def account_position_template(sender, instance, *args, **kwargs):
    '''
    Update number before saving
    '''
    __ = sender  # disable pylint warning
    function = None
    number = account_position_calc_number(
        instance.chart.account_type,
        function,
        instance.account_number,
        instance.is_category)
    instance.number = Decimal(number)
