# accounting/run_init_first.py
from django.contrib.auth.models import Group, Permission
import logging

from core.mixins import get_admin

logger = logging.getLogger(__name__)  # Using the app name for logging


class Init(object):
    """
    Manage user groups with specific permissions.
    """

    def initialize(self):
        """
        Initialize
        """        
        admin = get_admin()
        pass
