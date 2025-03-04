'''billing/actions.py
'''
from django.contrib import admin, messages
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from scerp.actions import action_check_nr_selected
from . import forms
from asset.models import Device
from .models import Subscription


@action_with_form(
    forms.PeriodExportActionForm, description=_('Export Counter Data'))
def export_counter_data(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        route = queryset.first()
        buildings = Subscription.objects.filter(
            tenant=route.tenant, end=None).all()
            
        # Counters    
        counters = Device.objects.all()
    
        data = {
            'billing_mde': {
                'route': {
                    'name': route.name,
                    'user': route.created_by.username
                },
                'meter': []
            }
        }
           
        meter = {
          "id": "00001111",
          "energytype": "W",
          "number": "Bemerkung 57",
          "hint": "Test Messanlage1",
          "address": {
            "street": "Teststrasse",
            "housenr": "12",
            "city": "Luzern",
            "zip": "6005",
            "hint": "Adresse Messanlage1"
          },
          "subscriber": {
            "name": "Kunde Test1",
            "hint": "Kunde Test1"
          },
          "value": {
            "obiscode": "8-0:1.0.0",
            "dateOld": "2023-12-31",
            "old": 50,
            "min": 40,
            "max": 88,
            "dateCur": "2024-03-01",
            "cur": 0
          }
        }
        
        data['billing_mde']['meter'].append(meter)
        
        print("d", data)
