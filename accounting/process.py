'''
accounting/process.py

usage:
   python manage.py process_accounting sync --org_name=test167 --ledger_id=1 --category=ic --max_count=100

'''
import logging
from datetime import timedelta
from django.utils.timezone import now

from .models import OutgoingOrder


logger = logging.getLogger(__name__)


def sync_outgoing_order(days_back=5):
    '''
    Set is_enabled_sync to True and save to trigger post_save.
    '''
    start_date = now() - timedelta(days=days_back)
    
    queryset = OutgoingOrder.objects.filter(
        date__gte=start_date,
        is_enabled_sync=False
    ).order_by('tenant', 'date')

    count = queryset.count()
    logger.info(
        f"Found {count} unsynced OutgoingOrders from the past {days_back} "
        "days.")

    for instance in queryset:
        instance.is_enabled_sync = True
        instance.sync_accounting = True
        instance.save()
        logger.info(f"{instance} synched.")

    return count
