'''
accounting/signals_cash_ctrl.py
'''
from django.conf import settings
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

from .ledger import Ledger
from .models import LedgerBalance, LedgerPL, LedgerIC


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
    '''Signal handler for pre_save signals on LedgerPL '''
    # Assign
    if instance.sync_to_accounting:
        ledger = Ledger(sender, instance, **kwargs)
        instance = ledger.update()
        
        
# LedgerIC
@receiver(pre_save, sender=LedgerIC)
def ledger_pl_pre_save(sender, instance, **kwargs):
    '''Signal handler for pre_save signals on LedgerIC '''
    # Assign
    if instance.sync_to_accounting:
        ledger = Ledger(sender, instance, **kwargs)
        instance = ledger.update()        
