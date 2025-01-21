from django.core.management import call_command
from django.test import TestCase

class CoreCommandTest(TestCase):

    '''
    python manage.py test core.tests
    '''    
    def test_init_first_command(self):
        # Call the command
        call_command('process_core', 'core__init_first')
        
        # Add assertions to verify the expected outcomes
        self.assertTrue(True)
