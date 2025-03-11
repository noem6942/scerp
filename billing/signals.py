'''
billing/signals.py
'''
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Subscription


@receiver(m2m_changed, sender=Subscription.counters.through)
def update_number_of_counters(sender, instance, action, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.number_of_counters = instance.counters.count()
        instance.save(update_fields=['number_of_counters'])
