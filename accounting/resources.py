'''
accounting/resources.py
'''
import logging

from import_export.resources import ModelResource
from import_export import fields
from import_export.widgets import DecimalWidget, ForeignKeyWidget
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import Tenant
from core.safeguards import get_tenant
from .models import APISetup, LedgerBalance, FiscalPeriod
from .models import LedgerTest

from .models import LedgerBalance, LedgerTest

logger = logging.getLogger(__name__)


# Helpers


class Setup:
    api_setup = None
        
    def get(**kwargs):
        ''' get APISetup from request '''
        request = kwargs.get("request")
        setup_id = get_tenant(request)['setup_id']
        self.api_setup = APISetup.objects.get(id=setup_id)


class FiscalPeriodWidget(ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):        
        return self.model.objects.filter(id=2)
        #filter(
        #    setup__id=2, name=row["period"]
        #)


class LedgerImportBaseResource(ModelResource):    
    setup = Setup  # gets assigned before_import
    period = fields.Field(
        column_name='period',
        attribute='period',
        widget=FiscalPeriodWidget(FiscalPeriod)
    )
    hrm = fields.Field(widget=DecimalWidget())

    class Meta:
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['period', 'hrm']
        fields = ('period', 'hrm', 'name', 'notes')

    def before_import(self, dataset, **kwargs):
        # setup
        return super().before_import(dataset, **kwargs)

    def before_import_row(self, row, **kwargs):
        # Validate hrm
        if not 0 <= row['hrm'] < 100000:
            msg = _("{hrm} no valid HRM code")
            raise ValidationError(msg.format(hrm=row['hrm']))
                
        # Validate function
        if self._meta.model == LedgerBalance:
            row['function'] = int(row['hrm'])
            
        if 'function' in row:
            if not 0 <= row['function'] < 100000:
                msg = _("{function} no valid function code")
                raise ValidationError(msg.format(function=row['function']))

    def before_save_instance(self, instance, row, **kwargs):
        # init
        instance.setup = APISetup.objects.last()
        instance.tenant = instance.setup.tenant
        instance.created_by = kwargs.get('user')
        
        # validate
        if instance.name.isupper():
            msg = _("Warning: name is in all upper letters.")
            instance.notes = f"{msg} ** {instance.notes}"
        
        return super().before_save_instance(instance, row, **kwargs)

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not row.get('period') or not row.get('hrm') or not row.get('name'):
            logger.warning(f"Skipping row due to missing fields: {row}")
            return True  # Skips this row
        return super().skip_row(instance, original, row, import_validation_errors)


class LedgerBalanceImportResource(LedgerImportBaseResource):   
    class Meta(LedgerImportBaseResource.Meta):
        model = LedgerBalance    

class PeriodTestForeignKeyWidget(ForeignKeyWidget):

    def get_queryset(self, value, row, *args, **kwargs):
        print("*args", args, kwargs)
        return self.model.objects.filter(
            name=row["period"],
            sex='M'
        )


class LedgerTestResource(ModelResource):
    api_setup = None  # gets assigned before_import
    period = None  # gets assigned before_import    

    class Meta:
        model = LedgerTest
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['hrm']
        fields = ('hrm', 'name')

    def before_import(self, dataset, **kwargs):
        request = kwargs.get("request")
        setup_id = get_tenant(request)['setup_id']
        self.api_setup = APISetup.objects.get(id=setup_id)   

        # Get current period
        self.period = FiscalPeriod.objects.filter(
            setup=self.api_setup, is_current=True).first()            

        return super().before_import(dataset, **kwargs)

    def before_import_row(self, row, **kwargs):
        '''
        for field_name in self.fields:
            if not row.get(field_name):
        #if 'F' not in row['name']:
        #    raise ValidationError("has no F")
        '''
        return super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, row, **kwargs):
        instance.setup = self.api_setup
        instance.tenant = instance.setup.tenant
        instance.period = self.period
        instance.created_by = kwargs.get('request').user        
        print("*instance", instance.__dict__)
        return super().before_save_instance(instance, row, **kwargs)

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not self.period:
            raise ValidationError(_("No fiscal period selected as current."))       
            return True
        return super().skip_row(
            instance, original, row, import_validation_errors)


