'''
accounting/signals_cash_ctrl.py
'''
import logging
import time

from django.conf import settings
from django.db import IntegrityError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import LedgerBalance

# Set up logging
logger = logging.getLogger(__name__)
MIN_REFRESH_TIME = 5  # seconds


# Helpers
class Ledger:
    '''
        Gets called before Ledger is saved
        updates category, parent and function
    '''
    def __init__(self, model, instance, **kwargs):
        self.model = model
        self.instance = instance

    def update(self):
        # Init
        instance = self.instance

        # Calc
        if instance.hrm == int(instance.hrm):
            # category
            instance.type = self.model.TYPE.CATEGORY

            # parent
            hrm = int(instance.hrm / 10)
            instance.parent = self.model.objects.filter(
                setup=instance.setup,
                hrm__lte=hrm
            ).order_by('hrm').last()

            # function
            instance.function = instance.hrm
        else:
            # category
            instance.type = self.model.TYPE.ACCOUNT

            # parent
            hrm = int(instance.hrm)
            instance.parent = self.model.objects.filter(
                setup=instance.setup,
                type=self.model.TYPE.CATEGORY,
                hrm=hrm
            ).last()

            # function
            instance.function = instance.parent.hrm

        return instance


# LedgerBalance
@receiver(pre_save, sender=LedgerBalance)
def ledger_balance_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre_save signals on LedgerBalance '''
    # Assign    
    if instance.sync_to_accounting:
        ledger = Ledger(sender, instance, **kwargs)
        instance = ledger.update()


@receiver(pre_delete, sender=LedgerBalance)
def ledger_balance_pre_delete(sender, instance, **kwargs):
    '''Signal handler for pre_save signals on LedgerBalance '''
    # No action so far, we keep the account as it could be used by another
    # ledger
    pass
