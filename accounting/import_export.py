'''
accounting/import_export.py
'''
import openpyxl

from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext as _

from scerp.mixins import make_multi_language
from .models import LedgerBalance, LedgerPL, LedgerIC


class ImportExport:

    def __init__(self, ledger, request, language=None):
        self.ledger = ledger
        self.setup = ledger.setup
        self.request = request
        self.language = language if language else self.setup.language

    def update_or_get(self, excel_file):
        # Init
        nr_of_fields = len(self.fields_import)

        # Load the workbook from the uploaded file
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        sheet = wb.active  # Get the first sheet
        
        # Read rows while preserving leading zeros in the first column
        rows = []
        for row_idx, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=True), start=2):
            # Read raw value
            first_cell = sheet.cell(row=row_idx, column=1).value 
            
            # Ensure it's a string
            first_cell = str(first_cell) if first_cell is not None else "" 

            # Replace first cell with string version
            row = (first_cell,) + row[1:]
            rows.append(row)

        # Init
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
            if data['hrm'] is None:
                if last_row and last_row['hrm'] and last_row['name']:
                    # Merge line breaks in name
                    last_row['name'] += ' ' + data['name']
                    messages.info(
                        request, _(f"row {nr} merging name").format(nr=nr))
                    continue

            # Append data
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
            obj, created = self.model.objects.update_or_create(
                ledger=data.pop('ledger'),
                hrm=data.pop('hrm'),
                defaults=data)

            if created:
                creates = creates + 1
            else:
                updates = updates + 1


class LedgerBalanceImportExport(ImportExport):
    model = LedgerBalance
    fields_import = [
        'hrm', 'name', 'opening_balance', 'closing_balance', 'increase',
        'decrease', 'notes']


class LedgerPLImportExport(ImportExport):
    model = LedgerPL
    fields_import = [
        'hrm', 'name', 'expense', 'revenue',
        'expense_budget', 'revenue_budget',
        'expense_previous', 'revenue_previous', 'notes']
