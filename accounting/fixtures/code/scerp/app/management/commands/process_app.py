# process_app.py
'''
call e.g. python manage.py process_app
'''
from django.core.management.base import BaseCommand
from app.process import Test

class Command(BaseCommand):
    help = 'Descriptions for your batch job'

    def handle(self, *args, **options):
        t = Test('bdo')
        # data = t.api_get_test()
        # t.api_post_test()
        t.other_test()
        self.stdout.write('Batch process completed successfully.')
