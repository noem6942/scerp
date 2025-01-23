'''
asset/create_tenant.py
'''
from .models import Category, CounterCategory, CounterUnit

def create(tenant, created_by):
    '''
    init values with new tenant
    '''
    for model, data in INIT_VALUES:
        data.update({
            'tenant: tenant,
            'created_by': created_by
        })
        try:
            model.create(**data)
        except:
            raise ValueError(f"could not create {data}")
