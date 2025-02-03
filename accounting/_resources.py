'''
accounting/resources.py
'''
from import_export.resources import ModelResource
from import_export import fields
from import_export.widgets import DecimalWidget, ForeignKeyWidget
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import Tenant
from core.safeguards import get_tenant
from .models import APISetup, LedgerBalance, FiscalPeriod
from .models import PeriodTest, LedgerTest



import logging
from import_export import resources, fields
from import_export.widgets import DecimalWidget, ForeignKeyWidget
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant
from .models import LedgerBalance, LedgerTest

logger = logging.getLogger(__name__)


# Helpers
def get_setup_id(**kwargs):
    request = kwargs.get("request")        
    return get_tenant(request)['setup_id']


class FiscalPeriodWidget(ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        setup = 
        return self.model.objects.filter(
            name=row["period"],
            setup=
        )


class LedgerBalanceResource(ModelResource):
    api_setup = None  # gets assigned before_import
    period = fields.Field(
        column_name='period',
        attribute='period',
        widget=FiscalPeriodWidget(FiscalPeriod, 'name')
    )
    hrm = fields.Field(widget=DecimalWidget())

    class Meta:
        model = LedgerBalance
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['period', 'hrm']
        fields = ('period', 'hrm', 'name')

    def before_import_row(self, row, **kwargs):
        # Validate period (must exist in FiscalPeriod)        
        period_name = str(row.get('period'))                
        if not FiscalPeriod.objects.filter(
                setup=self.api_setup, name=period_name).exists():
            msg = _('Invalid fiscal period: {name}').format(name=period_name)
            raise ValidationError(msg)        
        
        if not 0 <= row['hrm'] < 100000:        
            msg = _("{hrm} no valid HRM code")
            raise ValidationError(msg.format(hrm=row['hrm']))

    def before_import(self, dataset, **kwargs):
        # setup
        setup_id = get_setup_id(**kwargs)
        self.api_setup = APISetup.objects.get(id=setup_id)
        logger.info("*self.api_setup", self.api_setup)

        return super().before_import(dataset, **kwargs)

    def before_save_instance(self, instance, row, **kwargs):
        logger.info("***3")
        instance.setup = self.api_setup
        instance.tenant = self.api_setup.tenant
        instance.created_by = kwargs.get("user")
        return super().before_save_instance(instance, row, **kwargs)

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not row.get('period') or not row.get('hrm') or not row.get('name'):
            logger.warning(f"Skipping row due to missing fields: {row}")
            return True  # Skips this row
        return super().skip_row(instance, original, row, import_validation_errors)


class PeriodTestForeignKeyWidget(ForeignKeyWidget):
        
    def get_queryset(self, value, row, *args, **kwargs):
        print("*args", args, kwargs)
        return self.model.objects.filter(
            name=row["period"],
            sex='M'
        )


class LedgerTestResource(ModelResource):
    api_setup = None  # gets assigned before_import
    period = fields.Field(
        column_name='period',
        attribute='period',
        widget=PeriodTestForeignKeyWidget(PeriodTest, 'name')
    )  
    
    class Meta:
        model = LedgerTest
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['period', 'hrm']
        fields = ('period', 'hrm', 'name')

    def before_import_row(self, row, **kwargs):
        '''
        for field_name in self.fields:
            if not row.get(field_name):
        #if 'F' not in row['name']:
        #    raise ValidationError("has no F")
        '''
        return super().before_import_row(row, **kwargs)

    def before_import(self, dataset, **kwargs):
        request = kwargs.get("request")
        setup_id = get_tenant(request)['setup_id']
        self.api_setup = APISetup.objects.get(id=setup_id)

        return super().before_import(dataset, **kwargs)

    def before_save_instance(self, instance, row, **kwargs):
        instance.setup = self.api_setup
        return super().before_save_instance(instance, row, **kwargs)

    '''
    def import_instance(instance, row, **kwargs):
        pass
        return super().before_import(instance, row, **kwargs)
    '''
    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not row['period']:
            import_validation_errors['period'] = 'period Missing'
            return True
        return super().skip_row(
            instance, original, row, import_validation_errors)
