# core/management/commands/process_core.py
'''usage:
    python manage.py process_core update_or_create_apps --update
    python manage.py process_core update_or_create_countries --update
    python manage.py process_core update_or_create_groups --update
    python manage.py process_core update_or_create_base_buildings --update
    python manage.py process_core sync_person_again --tenant_id=4
    python manage.py process_core clear_company_addresses
'''
import logging
from django.core.management.base import BaseCommand
from django.core.management import CommandError

from core.process import (
    update_or_create_apps, update_or_create_countries, update_or_create_groups,
    update_or_create_base_buildings, sync_person_again, clear_company_addresses
)

# Set up logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process core'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',  # Positional argument
            choices=[
                'update_or_create_apps',
                'update_or_create_countries',
                'update_or_create_groups',
                'update_or_create_base_buildings',
                'sync_person_again',
                'clear_company_addresses'
            ],
            help='Specify the action: gesoft'
        )

        # Optional argument 'update', defaulting to False
        parser.add_argument(
            '--update',  # Optional flag
            action='store_true',  # Store true if flag is provided
            help='Specify if update is true (default is false)'
        )

        # Optional argument 'tenant_id', which expects a string or integer
        parser.add_argument(
            '--tenant_id',  # Optional argument
            type=int,  # Make it an integer, or type=str if you need a string
            help='Specify the tenant ID'
        )

    def handle(self, *args, **options):
        action = options['action']
        update = options.get('update', False)

        if action == 'update_or_create_apps':
            # Import library
            created, updated, deleted = update_or_create_apps(update)
            logger.info(
                f"Apps: {created} created, {updated} updated, "
                f"{deleted} deleted.")

        elif action == 'update_or_create_countries':
            # Import library
            created, updated, deleted = update_or_create_countries(update)
            logger.info(
                f"Countries: {created} created, {updated} updated, "
                f"{deleted} deleted.")

        elif action == 'update_or_create_groups':
            # Import library
            created, updated, deleted = update_or_create_groups(update)
            logger.info(
                f"Groups: {created} created, {updated} updated, "
                f"{deleted} deleted.")

        elif action == 'update_or_create_base_buildings':
            # Import library
            tenant_id = options.get('tenant_id', None)
            created, updated, deleted = update_or_create_base_buildings(
                tenant_id, update)
            logger.info(
                f"Buildings: {created} created, {updated} updated, "
                f"{deleted} deleted.")

        elif action == 'clear_company_addresses':
            # necessary as company addresses often double
            count = clear_company_addresses()
            logger.info(f"{count} itmes updated.")

        elif action == 'sync_person_again':
            # sync person, necessary as for some reason addresses were missing
            tenant_id = options.get('tenant_id', None)
            count = sync_person_again(tenant_id)
            logger.info(f"Synced {count} records.")
