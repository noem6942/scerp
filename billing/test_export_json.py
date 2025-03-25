'''
 test_export_json.py
 25.3.2025
'''
import json

data = {
  "billing_mde": {
    "route": {
      "name": "test167, Wasser 2025/1, 2024-10-01 - 2025-03-31, Route Testlauf, Wasser",
      "user": "brunnenmeister.gunzgen@outlook.com"
    },
    "meter": [
      {
        "id": "16519786",
        "energytype": "W",
        "number": "16519786",
        "hint": None,
        "address": {
          "street": "Markstrasse",
          "housenr": 12,
          "city": "Gunzgen",
          "zip": "4617",
          "hint": "non_residential"
        },
        "subscriber": {
          "name": "AmTech GmbH",
          "hint": "abo_nr: 585"
        },
        "value": {
          "obiscode": None,
          "dateOld": None,
          "old": 303,
          "min": 304.2,
          "max": 327,
          "dateCur": "2025-03-25"
        }
      },
      {
        "id": "14737334",
        "energytype": "W",
        "number": "14737334",
        "hint": None,
        "address": {
          "street": "Markstrasse",
          "housenr": "2",
          "city": "Gunzgen",
          "zip": "4617",
          "hint": "residential"
        },
        "subscriber": {
          "name": "Studer-Reinhard Hansruedi und Monika",
          "hint": "abo_nr: 239"
        },
        "value": {
          "obiscode": None,
          "dateOld": None,
          "old": 1797,
          "min": 1805.9,
          "max": 1975,
          "dateCur": "2025-03-25"
        }
      },
      {
        "id": "19683091",
        "energytype": "W",
        "number": "19683091",
        "hint": None,
        "address": {
          "street": "Kirchweg",
          "housenr": "19",
          "city": "Gunzgen",
          "zip": "4617",
          "hint": "residential"
        },
        "subscriber": {
          "name": "STOWE Eigentümergemeinschaft",
          "hint": "abo_nr: 361"
        },
        "value": {
          "obiscode": None,
          "dateOld": None,
          "old": 2606,
          "min": 2642.9,
          "max": 3344,
          "dateCur": "2025-03-25"
        }
      },
      {
        "id": "19871934",
        "energytype": "W",
        "number": "19871934",
        "hint": None,
        "address": {
          "street": "Kirchweg",
          "housenr": "19",
          "city": "Gunzgen",
          "zip": "4617",
          "hint": "residential"
        },
        "subscriber": {
          "name": "STOWE Eigentümergemeinschaft",
          "hint": "abo_nr: 361"
        },
        "value": {
          "obiscode": None,
          "dateOld": None,
          "old": None,
          "min": None,
          "max": None,
          "dateCur": "2025-03-25"
        }
      }
    ]
  }
}

# main
# Serialize the data to JSON
filename = "route_01_2025_03_25.json"
json_data = json.dumps(data, ensure_ascii=False, indent=4)

# Write the JSON data to the specified file
with open(filename, 'w', encoding='utf-8') as json_file:
    json_file.write(json_data)