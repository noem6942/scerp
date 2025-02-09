'''
accounting/import_export.py
'''
import openpyxl
from decimal import Decimal

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
        # Load the workbook
        # We need data_only=False to find out e.g. 3100.00 without seeing it as
        # int or float
        wb = openpyxl.load_workbook(excel_file, data_only=False)
        sheet = wb.active  # Get the first sheet

        # Loop through it preserving .00
        rows = []
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            new_row = []
            for col_idx, cell in enumerate(row):
                value = cell.value
                number_format = cell.number_format  # Get Excel's formatting

                if col_idx == 0:  # Apply special treatment to the first cell
                    if isinstance(value, (int, float)):
                        # If the number format contains decimals, keep them
                        if ".00" in number_format or number_format == "0.00":
                            value = f"{Decimal(value):.2f}"  # Force two decimal places
                        else:
                            value = str(value)  # Otherwise, keep as is
                else:
                    # For other cells, check number conversion
                    try: 
                        value = float(value)
                    except:
                        pass

                # Append to new row, convert None to empty string
                new_row.append(value if value is not None else None)

            # Append the processed new row to rows
            rows.append(new_row)

        # Init
        data_list = []
        last_row = None
        request = self.request

        # Process rows (skipping header)
        for nr, row in enumerate(rows, start=2):
            data = dict(zip(self.fields_import, row))

            # Validate name
            if not data['name']:
                msg = _(f"row {nr} skipping, has no name").format(nr=nr)
                messages.info(request, msg)
                continue

            # Validate hrm
            if not data['hrm']:
                # Check merging
                if last_row and last_row['hrm'] and last_row['name']:
                    # Merge line breaks in name
                    last_row['name'] += ' ' + data['name']
                    msg = _(f"row {nr} merging name").format(nr=nr)
                    messages.info(request, msg)
                    continue

                # Check headings
                if '.' not in data['hrm']:  # is heading
                    level = len(data['hrm'])
                    level_last = len(last_row['hrm'])
                    if level > 1 and level != level_last + 1:
                        msg = _(f"row {nr}: level not consistant").format(
                            nr=nr)
                        messages.info(request, msg)
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
