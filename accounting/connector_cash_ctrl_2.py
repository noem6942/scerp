'''
accounting/connector_cash_ctrl_2.py
'''
from django.forms.models import model_to_dict

from . import api_cash_ctrl
from .models import APISetup, Title

EXCLUDE_FIELDS = [
    'id', 'tenant', 'sync_to_accounting',
    'modified_at', 'modified_by', 'created_at', 'created_by',
    'is_protected', 'attachment', 'version',
    'setup', 'c_id', 'c_created', 'c_created_by', 'c_last_updated',
    'c_last_updated_by', 'last_received', 'message', 'is_enabled_sync'
]


class CashCtrl:

    def __init__(self, language=None):
        self.language = language

    def _get_api(self, setup):
        return self.api_class(
            setup.org_name, setup.api_key, language=self.language)

    def get(self, model, setup, created_by, params={}, update=True):
        api = self._get_api(setup)
        data_list = api.list(params)

        for data in data_list:
            # Get or create instances
            instance = model.objects.filter(
                setup=setup, c_id=data['id']).first()
            if instance and not update:
                continue  # no further update
            else:
                # create instance
                instance = model(
                    c_id=data.get('id'),
                    tenant=setup.tenant,
                    setup=setup,
                    created_by=created_by
                )

            # add data
            for field in model_to_dict(instance, exclude=self.exclude):
                setattr(instance, field, data.get(field))

            if instance.is_inactive is None:
                instance.is_inactive = False

            # save instance
            self.save_instance(instance, data)

    def save(self, instance, created=None):
        # Get api
        api = self._get_api(instance.setup)

        # Prepare data
        data = self.instance_to_dict(instance)

        # Save
        if created:
            # Save object
            response = api.create(data)
            print("*data", data)
            instance.c_id = response.get('insert_id')
            print("*data", instance.c_id)
            instance.sync_to_accounting = False
            instance.save(update_fields=['c_id', 'sync_to_accounting'])
        else:
            data['id'] = instance.c_id
            print("*data", data)
            _response = api.update(data)

    def delete(self, instance):
        api = self._get_api(instance.setup)
        response = api.delete(instance.c_id)


class CashCtrlDual(CashCtrl):

    def save(self, instance, created=None):
        # Get setup
        if created:
            setup = APISetup.get_setup(tenant=instance.tenant)
        else:
            instance_acct = self.model_accounting.objects.get(
                tenant=instance.tenant, core=instance)
            setup = instance_acct.setup

        # Get api
        api = self._get_api(setup)

        # Prepare data
        data = self.instance_to_dict(instance)

        # Save
        if created:
            # Save object
            response = api.create(data)
            c_id = response.get('insert_id')
            instance_acct = self.model_accounting.objects.create(
                core=instance,
                c_id=c_id,
                tenant=instance.tenant,
                setup=setup,
                created_by=instance.tenant.created_by
            )
        else:
            data['id'] = instance_acct.c_id
            _response = api.update(data)

        # Only updates this field, avoids triggering full post_save
        instance.sync_to_accounting = False
        instance.save(update_fields=['sync_to_accounting'])

    def get(self, model, model_accounting, setup, created_by, update=True):
        api = self._get_api(setup)
        data_list = api.list()

        for data in data_list:
            # Get or create instances
            instance_acct = model_accounting.objects.filter(
                setup=setup, c_id=data['id']).first()
            if instance_acct:
                if update:
                    instance = instance_acct.core  # assign instance
                else:
                    continue  # no further update
            else:
                # create instance
                instance = model(
                    tenant=setup.tenant,
                    created_by=created_by
                )

            # add data
            for field in model_to_dict(instance, exclude=self.exclude):
                setattr(instance, field, data.get(field))

            if instance.is_inactive is None:
                instance.is_inactive = False

            # save instance
            self.save_instance(instance, data)
            if not instance_acct:
                # create accounting_instance
                instance_acct = model_accounting(
                    core=instance,
                    c_id=data['id'],
                    tenant=setup.tenant,
                    setup=setup,
                    created_by=created_by
                )


class CustomFieldGroup(CashCtrl):
    api_class = api_cash_ctrl.CustomFieldGroup
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def get(self, model, setup, created_by, params={}, update=True):
        for field in api_cash_ctrl.FIELD_TYPE:
            params = {'type': field.value}
            super().get(model, setup, created_by, params, update)
    
    def instance_to_dict(self, instance):
        return model_to_dict(instance, exclude=self.exclude)

    def save_instance(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"
        instance.save()


class Title(CashCtrlDual):
    api_class = api_cash_ctrl.PersonTitle
    exclude = EXCLUDE_FIELDS + ['code']
    model_accounting = Title

    def instance_to_dict(self, instance):
        return model_to_dict(instance, exclude=self.exclude)

    def save_instance(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"
        instance.save()
