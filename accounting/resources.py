'''
accounting/resources.py
'''
import logging
from import_export.resources import ModelResource
from import_export import fields
from import_export.widgets import ForeignKeyWidget
from import_export.results import RowResult
from import_export.widgets import DecimalWidget
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import Tenant
from core.safeguards import get_tenant
from .models import APISetup, LedgerBalance, FiscalPeriod
from .models import LedgerTest


# Define a logger for warnings and other logs
logger = logging.getLogger(__name__)


import logging
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.results import RowResult
from django.utils.translation import gettext_lazy as _
from .models import APISetup

logger = logging.getLogger(__name__)


import logging
from import_export import resources, fields
from import_export.widgets import DecimalWidget, ForeignKeyWidget
from django.utils.translation import gettext_lazy as _

from core.safeguards import get_tenant
from .models import LedgerBalance, LedgerTest

logger = logging.getLogger(__name__)


class LedgerBalanceResource(resources.ModelResource):
    api_setup = None  # gets assigned before_import
    period = fields.Field(
        column_name='period',
        attribute='period',
        widget=ForeignKeyWidget(FiscalPeriod, 'name')
    )    

    hrm = fields.Field(widget=DecimalWidget())

    class Meta:
        model = LedgerBalance
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['period__name', 'hrm']
        fields = ('period__name', 'hrm', 'name')

    def before_import_row(self, row, **kwargs):
        # Validate period (must exist in FiscalPeriod)        
        logger.info("***1")
        period_name = str(row.get('period'))        
        logger.info(f"*period_name: {period_name}, api_setup: {self.api_setup}")
        if not FiscalPeriod.objects.filter(
                setup=self.api_setup, name=period_name).exists():
            msg = _('Invalid fiscal period: {name}').format(name=period_name)
            raise ValidationError(msg)        
        
        if not 0 <= row['hrm'] < 100000:        
            msg = _("{hrm} no valid HRM code")
            raise ValidationError(msg.format(hrm=row['hrm']))

    def before_import(self, dataset, **kwargs):
        # setup
        logger.info("***2")
        request = kwargs.get("request")        
        setup_id = get_tenant(request)['setup_id']
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


class LedgerTestResource(resources.ModelResource):
    api_setup = None  # gets assigned before_import

    class Meta:
        model = LedgerTest
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['period', 'hrm']
        fields = ('period', 'hrm', 'name')

    def before_import_row(self, row, **kwargs):
        if 'F' not in row['name']:
            raise ValidationError("has no F")

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
            return True
        return super().skip_row(
            instance, original, row, import_validation_errors)


class LedgerBalanceResource(ModelResource):
    period = fields.Field(
        column_name='period',
        attribute='period',
        widget=ForeignKeyWidget(FiscalPeriod, 'name')  # Ensures the period exists
    )
    name = fields.Field(column_name='name')
    hrm = fields.Field(column_name='hrm')

    class Meta:
        model = LedgerBalance
        fields = ('period', 'hrm', 'name')  # Add other fields if needed

    def import_data(self, dataset, **kwargs):
        """
        Override the import_data method to capture the request and pass it to
        the before_import_row method.
        """
        request = kwargs.get('request')  # Capture the request here
        setup_id = get_tenant(request)['setup_id']
        setup = APISetup.objects.get(id=setup_id)

        # Now pass the request to the import method
        for row in dataset.dict:
            # Add setup and tenant information for each row processing
            row['setup'] = setup
            row['tenant'] = setup.tenant

        return super().import_data(dataset, **kwargs)

    def before_import_row(self, row, **kwargs):
        """Validation before importing each row."""
        # Get variables (passed through the row)
        period_name = row.get('period')
        hrm = row.get('hrm')
        name = row.get('name')
        tenant = row.get('tenant')

        # Validate 'period' field
        if not period_name or not FiscalPeriod.objects.filter(name=period_name).exists():
            logger.warning(_('Skipping row due to invalid or missing period: {row}').format(row=row))
            return None  # Skip this row

        # Validate 'hrm' field (assuming hrm is numeric and should not be empty)
        if not hrm:
            logger.warning(_('Skipping row due to missing HRM: {row}').format(row=row))
            return None  # Skip this row

        # Validate 'name' field
        if not name:
            logger.warning(_('Skipping row due to missing Name: {row}').format(row=row))
            return None  # Skip this row

        # Validate period and tenant (if relevant)
        if not FiscalPeriod.objects.filter(tenant=tenant, name=period_name).exists():
            logger.warning(_('Skipping row due to invalid period for tenant: {row}').format(row=row))
            return None  # Skip this row

        # At this point, the row is valid and can be processed further
        return super().before_import_row(row, **kwargs)
