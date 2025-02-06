'''
accounting/import_export.py
'''
import openpyxl

from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext as _

from scerp.mixins import make_multi_language
from .models import LedgerBalance


class LedgerBalanceImportExport:
    fields_import = [
        'hrm', 'name', 'opening_balance', 'closing_balance', 'increase',
        'decrease', 'notes']

    def __init__(self, ledger, request, language=None):
        self.ledger = ledger
        self.setup = ledger.setup
        self.request = request
        self.language = language if language else self.setup.language

    def update_or_get(self, excel_file):
        # Init
        nr_of_fields = len(self.fields_import)

        # Load the workbook from the uploaded file
        wb = openpyxl.load_workbook(excel_file)
        sheet = wb.active  # Get the first sheet

        # Init rows (skipping header)
        rows = [row for row in sheet.iter_rows(min_row=2, values_only=True)]
        data_list = []
        last_row = None
        request = self.request

        # Process rows (skipping header)
        for nr, row in enumerate(rows, start=2):
            data = dict(zip(self.fields_import, row))

            # Validate name
            if not data['name']:
                messages.info(
                    request, _(f"row {nr} skipping").format(nr=nr))
                continue

            # Validate hrm
            if data['hrm']:
                try:
                    int(data['hrm']) in range(0, 100000)
                except:
                    messages.info(
                        request, _(f"row {nr} no valid hrm").format(nr=nr))
                    continue
            elif last_row and last_row['hrm'] and last_row['name']:
                # merge line breaks in name
                last_row['name'] += ' ' + data['name']
                messages.info(
                    request, _(f"row {nr} merging name").format(nr=nr))
                continue

            last_row = data
            data_list.append(data)

        # Create_or_update
        updates, creates = 0, 0
        for data in data_list:
            # Make multilanguage
            name_json = make_multi_language(data.pop('name'), self.language)
            
            # Add name, logging
            # is_enabled_sync: False 
            #   as we don't want to fire signals at the beginning
            data.update({
                'is_enabled_sync': False,  
                'name': name_json,
                'tenant': self.setup.tenant,
                'setup': self.setup,
                'ledger': self.ledger,
                'created_by': self.request.user,
                'sync_to_accounting': True
            })
            
            # Create
            obj, created = LedgerBalance.objects.update_or_create(
                ledger=data.pop('ledger'),
                hrm=data.pop('hrm'),
                defaults=data)

            if created:
                creates = creates + 1
            else:
                updates = updates + 1
