# meeting/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver


from .models import AgendaItem


@receiver(post_save, sender=AgendaItem)
def api_setup(sender, instance, created, **kwargs):
    """Perform follow-up actions when a new APISetup is created."""
    if created:        
        # create business id  ... TEST
        if instance.is_business and not instance.id_business:
            id = AgendaItem.objects.filter(
                meeting=instance.meeting).count() + 1
            instance.id_business = f'1900/{str(id).zfill(3)}'
    else:   
        pass