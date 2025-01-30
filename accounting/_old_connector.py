# accounting/connector.py
'''Interface to cashCtrl (and other accounting applications later)
'''
import importlib
from scerp.mixins import get_admin, make_timeaware
from .models import APPLICATION, MappingId


DJANGO_KEYS = [
    '_state', 'id', 'created_at', 'created_by_id', 'modified_at', 
    'modified_by_id', 'notes', 'attachment', 'version_id', 'is_protected', 
    'tenant_id', 'setup_id'
]


# helpers
def get_connector_module(instance=None, api_setup=None):
    '''
    Import right connector
        instance has either a field setup or api_setup is given
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


def extract_fields_to_dict(instance, fields):
    """
    Extract specified fields from a Django model instance to a dictionary.

    Args:
        instance (Model): The model instance to extract data from.
        fields (list): List of field names to extract.

    Returns:
        dict: Dictionary containing field names and their corresponding values.
    """
    return {field: getattr(instance, field, None) for field in fields}


class ConnectorBase(object):

    def __init__(self, api_setup):
        '''messages is admin.py messanger; if not giving logger is used
        '''
        self.api_setup = api_setup
        self.admin = get_admin()
        self.model = getattr(self, 'MODEL', None)
        
    def add_logging(self, data):
        data['setup'] = self.api_setup
        if not data.get('tenant'):
            data['tenant'] = self.api_setup.tenant
        if not data.get('created_by'):
            data['created_by'] = self.admin            
        return data
      
    def add_modified(self, instance):        
        instance.modified_by = self.admin        
        instance.save()

    def get_mapping_id(self, mapping_type, key):
        mapping = MappingId.objects.filter(
            setup=self.api_setup, name=key, type=mapping_type)
        if mapping:
            return mapping.first().c_id
        return None

    def register(self, mapping_type, key, c_id, description=None):
        '''Register ids in MappingId
        '''
        # Prepare
        data = {
            'c_id': c_id,
            'description': description
        }
        self.add_logging(data)

        # store
        obj, created = MappingId.objects.update_or_create(
            setup=self.api_setup,
            name=key,
            type=mapping_type,
            defaults=data)  
            
        return obj, created


class ConnectorGeneric(ConnectorBase):
    pass
