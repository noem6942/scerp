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
from django.utils.translation import gettext_lazy as _

from .models import LedgerBalance, LedgerPL

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
        
        # validate hrm
        try:
            __ = float(instance.hrm)
        except:
            msg = _("{hrm} not a valid hrm").format(hrm=instance.hrm)
            raise ValueError(msg)

    def update(self):
        # Init
        instance = self.instance

        # Calc
        if '.' in instance.hrm:
            # type = account
            instance.type = self.model.TYPE.ACCOUNT

            # parent
            hrm = instance.hrm
            instance.parent = self.model.objects.filter(
                setup=instance.setup,
                type=self.model.TYPE.CATEGORY,
                hrm__lte=hrm
            ).order_by('hrm').last()

            # function
            instance.function = instance.parent.hrm            
        else:
            # type = category
            instance.type = self.model.TYPE.CATEGORY

            # parent                        
            hrm = instance.hrm[:-1]  # skip last letter
            if hrm:
                instance.parent = self.model.objects.filter(
                    setup=instance.setup,
                    hrm__lte=hrm
                ).order_by('hrm').last()
            else:
                instance.parent = None

            # function
            instance.function = instance.hrm


        # Check name
        for label in instance.name.values():
            if label.isupper():
                instance.message =  _("Title in upper letters")
                break

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


# LedgerPL
@receiver(pre_save, sender=LedgerPL)
def ledger_pl_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre_save signals on LedgerBalance '''
    # Assign
    if instance.sync_to_accounting:
        ledger = Ledger(sender, instance, **kwargs)
        instance = ledger.update()
