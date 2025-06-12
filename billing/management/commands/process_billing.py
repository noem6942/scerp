# process_billing.py
'''usage:
    python manage.py process_billing gesoft --tenant_id=12 --route_id=1 --date=2024-09-30
    python manage.py process_billing gesoft_area --tenant_id=12
    python manage.py process_billing gesoft_archive --tenant_id=12
    python manage.py process_billing article_import --tenant_id=12
    python manage.py process_billing article_daily_rename --tenant_id=12
    python manage.py process_billing fix_zero_problem --tenant_id=12
    python manage.py process_billing adjust_articles --tenant_id=12
    python manage.py process_billing adjust_mfh --tenant_id=12
    python manage.py process_billing rearrange_counters --tenant_id=12
    python manage.py process_billing delete_negative_counter
    python manage.py process_billing update_invoiced
    python manage.py process_billing correct_article_counts --tenant_id=12
    python manage.py process_billing get_list_of_open_records --tenant_id=12
    python manage.py process_billing get_list_of_do_again_records --tenant_id=12
    
'''
import json
from django.core.management.base import BaseCommand
from django.core.management import CommandError


class Command(BaseCommand):
    help = 'Process accounting'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',  # Positional argument
            choices=[
                'gesoft', 'gesoft_area', 'gesoft_archive',
                'article_import', 'article_daily_rename',
                'fix_zero_problem', 'adjust_articles', 'adjust_mfh',
                'rearrange_counters', 'delete_negative_counter',
                'update_invoiced', 'correct_article_counts',
                'get_list_of_open_records', 'get_list_of_do_again_records'
            ],
            help='Specify the action: gesoft'
        )
        parser.add_argument(
            '--tenant_id',  # Optional argument (use '--')
            type=int,
            required=False,
            help='Setup ID for the operation'
        )
        parser.add_argument(
            '--route_id',
            type=int,
            required=False,
            help='Route ID for the operation'
        )
        parser.add_argument(
            '--date',
            type=str,
            required=False,
            help='Date default for counter data'
        )

    def handle(self, *args, **options):
        action = options['action']
        tenant_id = options.get('tenant_id')
        route_id = options.get('route_id')
        date = options.get('date')

        if action == 'gesoft':
            # Import library
            from billing.gesoft_import import ImportAddress, ImportData

            # Load addresses
            file_name = 'Abonnenten Gebühren einzeilig.xlsx'
            handler = ImportAddress(tenant_id)
            address_data = handler.load(file_name)

            # Load subscribers + counters
            file_name = 'Abonnenten mit Zähler und Gebühren.xlsx'
            handler = ImportData(tenant_id, route_id, date)
            handler.load(file_name, address_data)

        elif action == 'gesoft_area':
            # Import library
            from billing.gesoft_import import AreaAssignment

            # Load subscribers + counters
            handler = AreaAssignment(tenant_id)
            handler.assign()

        elif action == 'article_import':
            # Import library
            from billing.gesoft_import import ArticleCopy

            # Make daily articles
            handler = ArticleCopy(tenant_id)
            handler.make_daily()

        elif action == 'article_daily_rename':
            # Import library
            from billing.gesoft_import import ArticleCopy

            # Make daily articles
            handler = ArticleCopy(tenant_id)
            handler.rename_daily()

        elif action == 'gesoft_archive':
            # Import library
            from billing.gesoft_import import ImportArchive

            # Load subscribers + counters
            file_name = 'Abonnenten Archiv Gebühren einzeilig.xlsx'
            handler = ImportArchive(tenant_id)
            handler.load(file_name)

        elif action == 'fix_zero_problem':
            # Import library
            from billing.gesoft_import import fix_zero_problem

            # Load subscribers + counters
            json_filename = 'productive_route0120250325_2025-04-16_12-44-39 (leading 0, some entries empty).json'
            excel_file_name = 'Abonnenten mit Zähler und Gebühren.xlsx'
            fix_zero_problem(json_filename, excel_file_name, tenant_id)

        elif action == 'adjust_articles':
            # Import library
            from billing.gesoft_import import adjust_articles

            # Load subscribers + counters            
            adjust_articles(tenant_id)

        elif action == 'adjust_mfh':
            # Import library
            from billing.gesoft_import import adjust_mfh

            # Load subscribers + counters            
            adjust_mfh(tenant_id)

        elif action == 'rearrange_counters':
            # Import library
            from billing.gesoft_import import rearrange_counters

            # Load subscribers + counters            
            rearrange_counters(tenant_id)

        elif action == 'delete_negative_counter':
            # Import library
            from billing.gesoft_import import delete_negative_counter

            # Delete counters      
            delete_negative_counter()

        elif action == 'update_invoiced':
            # Import library
            from billing.gesoft_import import update_invoiced

            # Update
            update_invoiced()

        elif action == 'correct_article_counts':
            # Import library
            from billing.gesoft_import import correct_article_counts

            # Update
            correct_article_counts(tenant_id)

        elif action == 'get_list_of_open_records':
            # Import library
            from billing.gesoft_import import get_list_of_open_records

            # Update
            get_list_of_open_records(tenant_id)
            
        elif action == 'get_list_of_do_again_records':
            # Import library
            from billing.gesoft_import import get_list_of_do_again_records

            # Update
            get_list_of_do_again_records(tenant_id)

        else:
            raise ValueError("No valid action")
