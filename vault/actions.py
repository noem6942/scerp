# vault/actions.py
from django.contrib import admin, messages
from django.db import transaction
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from .forms import OverrideConfirmationForm
from .locales import ACTION
from .models import (
    RegistrationPlanCanton, RegistrationPosition,
    LeadAgency, RetentionPeriod, LegalBasis, ArchivalEvaluation)
    
from core.safeguards import save_logging    
from scerp.actions import action_check_nr_selected
from scerp.mixins import read_excel_file



# mixins
@admin.action(description=ACTION.position_insert)
def position_insert(self, request, queryset):
    ''' Insert row of a model that has a field position '''
    pass
    '''
    # Check
    if action_check_nr_selected(request, queryset, 1):
        obj = queryset.first()
    else:
        return

    # Create a copy of the instance with a new position
    obj.pk = None  # Clear the primary key for duplication
    obj.name += ' <copy>'
    try:
        if obj.account_number:
            obj.account_number = str(int(obj.account_number) + 1)
        elif obj.account_4_plus_2:
            obj.account_4_plus_2 = str(float(obj.account_4_plus_2) + 0.01)
        obj.save()
        messages.success(request, _('Copied record.'))
    except:
        messages.warning(request, _('Not allowed to copy this record.'))
        return
    '''


def positions(request, queryset, action):
    # Check number selected
    if action_check_nr_selected(request, queryset, 1):
        plan = queryset.first()
    else:
        return

    # Load excel
    rows = read_excel_file(plan.excel.path)

    # Init
    add_tenant = False
    headers = [
        'number',
        'position',
        'lead_agency',
        'retention_period',
        'legal_basis',
        'archival_evaluation',
        'remarks'
    ]
    
    models = {
        'lead_agency': LeadAgency, 
        'retention_period': RetentionPeriod, 
        'legal_basis': LegalBasis, 
        'archival_evaluation': ArchivalEvaluation
    }

    # Parse
    started, positions = False, []
    for index, row in enumerate(rows, start=1):
        # Check header
        if not started:
            if row[:2] != ['Nr', 'Aktenplanposition']:
                continue
            else:
                started = True
                continue
            
        # Check empty    
        if all(element == '' for element in row): 
            continue
            
        # Check no nr    
        if row[0] == '':
            msg = _("Position {position} has no number").format(position=index)
            messages.error(request, msg)
            return
            
        # Check no name
        if row[0] != '' and row[1] == '':
            msg = _("Position {position} has no name").format(position=index)
            messages.error(request, msg)            
            return    
            
        position = dict(zip(headers, row))
        positions.append(position)
        
    # Check no positions
    if not positions:
        msg = _("No positions to create")
        messages.error(request, msg)                    
        return
        
    # Only check    
    if action == 'check':
        msg = _("Excel sheet checked {count} positions  with no errors."
            ).format(count=len(positions))            
        messages.success(request, msg)                    
        return        
            
    # Delete old
    if action == 'create':
        RegistrationPosition.objects.filter(registration_plan=plan).delete()
    
    # Create positions
    with transaction.atomic():
        for position in positions:
            # Create
            position_obj = RegistrationPosition(registration_plan=plan)
        
            # Get foreign keys
            for key in headers:         
                value = position.get(key, None)
                                
                if key in models.keys() and value is not None:
                    # get foreign key
                    if value == '':
                        foreign = None
                    else:
                        foreign = models[key].objects.filter(
                            name=value).first()
                        if not foreign:
                            foreign = models[key](name=value)
                            save_logging(request, foreign, add_tenant)
                            foreign.save()
                    value = foreign                    
                    
                # Assign value    
                setattr(position_obj, key, value)
        
            # Calc is_category, level
            position_obj.is_category = (
                True if position.get('lead_agency') else False)
            position_obj.level = position_obj.number.count('.') + 1
        
            # Save
            if action == 'create':            
                # Add Logging
                save_logging(request, position_obj, add_tenant)
                position_obj.save()
        
    # Message
    msg = _("successfully added {count} positions.").format(
        count=len(positions))
    messages.success(request, msg)          


@admin.action(description=ACTION.canton_positions_check)
def canton_positions_check(modeladmin, request, queryset):
    action_form = OverrideConfirmationForm
    positions(request, queryset, 'check')


@action_with_form(
    OverrideConfirmationForm,
    description=ACTION.canton_positions_create,
)
def canton_positions_create(modeladmin, request, queryset, data):
    action_form = OverrideConfirmationForm
    positions(request, queryset, 'create')
