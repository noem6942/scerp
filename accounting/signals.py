# accounting/signals.py
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import APPLICATION, APISetup, FiscalPeriod, Location
from .process import ProcessCashCtrl


# helpers
def get_ctrl(instance=None, apiset=None):
    if not apiset:
        try:
            apiset = APISetup.objects.get(tenant=instance.tenant)
        except APISetup.DoesNotExist:
            raise ValidationError(
                f"APISetup not found for tenant: {instance.tenant}")
    
    if apiset.application == APPLICATION.CASH_CTRL:
        return ProcessCashCtrl(apiset)
    else:
        raise ValidationError("No application found.")


@receiver(post_save, sender=APISetup)
def api_setup(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new APISetup is created."""
    if created:
        # This code only runs the first time the tenant is created (not on updates)
        pass
    else:        
        # Init -------------------------------------------------------------
        ctrl = get_ctrl(apiset=instance)

        # Create Custom Groups
        ctrl.init_custom_groups()

        # Create Custom Fields, currently only for simple types with no defaults
        ctrl.init_custom_fields()       
        
        # Create Location for VAT, Codes, Formats
        ctrl.init_locations()
            
        
        # FiscalPeriod
        ctrl.init_fiscal_periods()


@receiver(post_save, sender=FiscalPeriod)
def fiscal_period(sender, instance, created, **kwargs):    
    ctrl = get_ctrl(instance)
    if created:        
        print("*", created)
        # ctrl.create_fiscal_period(instance)
    else:
        print("**", created)
        # ctrl.update_fiscal_period(instance)
