# accounting/connector.py
'''Interface to cashCtrl (and other accounting applications later)
'''
import importlib
from scerp.mixins import get_admin, make_timeaware
from .models import APPLICATION


def get_connector_module(instance=None, api_setup=None):
    '''
    Import right connector
    '''
    if not api_setup:
        # get from instance
        api_setup = getattr(instance, 'setup', None)
        
    if not instance and not api_setup:
        raise ValidationError("Could not get application")

    # Import connector   
    application = None   
    if api_setup.application == APPLICATION.CASH_CTRL:
        application = 'connector_cash_ctrl'

    if application:
        module_name = f'accounting.{application}'
        module = importlib.import_module(module_name)
        return api_setup, module
        
    raise ValidationError("No application specified")


class ConnectorBase(object):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.api_setup = api_setup
        self.admin = get_admin()

    def add_logging(self, data):
        data['setup'] = self.api_setup

        if not data.get('tenant'):
            data['tenant'] = self.api_setup.tenant

        if not data.get('created_by'):
            data['created_by'] = self.admin

        if not data.get('modified_by'):
            data['modified_by'] = self.admin


class ConnectorGeneric(ConnectorBase):
    pass
