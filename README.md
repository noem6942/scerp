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
open \locale\de\LC_MESSAGES\django.po

## Bugs

### accounting
- FiscalPeriod: current not set correctly
- Re-do Ledger Account Setup: Aufwand (ER), Ausgaben (IV) have duplicates


## To-do's

### accounting
- Plan through: copy of ledger accounts to new or old fiscal year


## Kontrollieren der Rechnungen
Ausgangslage:
* Es gibt einen langen Excelsheet, der aus dem alten GESoft kommt mit dem
Stand der letzten Periode. Dieser wurde importiert und mit verschiedenen Daten
angereichert. 
* Es gibt ca. 500 Abonnenten mit einer von GESoft vergebenen Abo-Nr.; sie ist
ein nicht sprechender Schlüssel und wurde abgelöst durch die offizielle eidg.
Bezeichnung im EGID. Das Objekt auf der Rechnung ist zu 100% (anders gar nicht 
möglich) die offizielle Bezeichnung und entspricht der Spalte L (wobei die voller
Fehler ist, einmal str. abgekürzt, dann nicht etc.)
* Jedes Abo hat genau einen Zähler, Sonderfälle 2 (Negativzähler zur Korrektur)
oder 0 (kein Zähler und trotzdem werden die Grundgebühren verrechnet)
* Für jeden Abonnenten werden Produkte verrechnet (ZM, ARA etc.). Bei Industrie
sind die Bezeichnungen nicht eindeutig. Auf der Rechnung wurden klare Produkte-
bezeichungen eingeführt. Tarif sollte weiterhin der gleiche sein. 
Wassergebühren als Produkt fehlen im Excelsheet. Grundregel ist: jeder der 
Abwasser bezieht (CHF 1.40), bezieht auch die gleiche Menge Wasser (CHF 1.1)
* Aus den Daten (Abonnenten, Kunden, Adressen) werden die Rechnungen generiert,
und nach cashCtrl im Hintergrund exportiert. Es wurden schon mehrfache komplette
Komplettexporte gemacht und ausnahmslos alle Datensätze werden bei mir und bei
 cashCtrl ohne Fehler akzeptiert.
* Der Abonnent ist neben WA-2402 aufgeführt, die Rechnung geht an den R-Empf, 
das kann Abonnent selbst ("Besitzer"), Abonnent + Partner, Rechnungsadresse des Abonnenten
oder der Mieter sein. Es wurde ein "Best Guess" gemacht und von David die 
per Skript "verdächtigen" Fälle im System aktualisiert. 
* Es gab einige Neubauten (also neue Abonnenten), die nicht im Excel aufgeführt 
sind. Ihnen wird die Grundbebühr nach Tagen anteilsmässig verrechnet.
