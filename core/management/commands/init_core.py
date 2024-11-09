# core/management/commands/init_core.py
'''usage:
    python manage.py init_core initialize
'''
from django.core.management.base import BaseCommand

from core.process_init import Core


class Command(BaseCommand):
    help = 'Init accounting'

    def add_arguments(self, parser):
        # Choices for the 'action' argument
        parser.add_argument(
            'action', 
            type=str, 
            choices=['first_time'], 
            help='Specify the action: "first_time"'
        )
        
        # Optional arguments
        pass

    def handle(self, *args, **options):
        # Retrieve options
        action = options['action']        

        # Perform different actions based on 'action' choice
        if action == 'first_time':
            pass
