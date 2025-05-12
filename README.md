# Django Project SCERP

## Description
This is a Django-based project to manage the Swiss City ERP

## Local tasks
Libraries:
    pipreqs . --ignore ignore --force
    INFO: Successfully saved requirements file in .\requirements.txt

Docu
    sphinx-build -b html docs/source docs/build/html

## Installation
Clone the repository:
   ```bash```
   git clone https://github.com/noem6942/scerp

Libraries:
    pip install -r requirements.txt

Docu:
    sphinx-build -b html docs/source docs/build/html


## Translation
django-admin makemessages -l de --ignore="fixtures/*" --ignore="asset/ignore/*"
django-admin compilemessages

## Bugs

### accounting
- FiscalPeriod: current not set correctly
- Re-do Ledger Account Setup: Aufwand (ER), Ausgaben (IV) have duplicates


## To-do's

### accounting
- Plan through: copy of ledger accounts to new or old fiscal year


