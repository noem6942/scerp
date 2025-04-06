'''core/actions.py
'''
from django.contrib import admin, messages
from django.contrib.auth.models import User, Group
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from accounting.signals_cash_ctrl import tenant_accounting_post_save
from scerp.actions import action_check_nr_selected
from scerp.mixins import generate_random_password
from . import forms
from .models import Person, UserProfile
from .safeguards import get_tenant_data
from .signals import tenant_post_save


@admin.action(description=('Admin: Run setup'))
def init_setup(modeladmin, request, queryset):    
    # Check
    if action_check_nr_selected(request, queryset, 1):        
        tenant = queryset.first() 
        try:
            tenant_post_save(
                modeladmin.model, tenant, created=False, init=True, 
                request=request)
            messages.success(request, _("Scerp initialized"))
        except Exception as e:
            messages.error(request, _('Unexpected error: ') + str(e))        


@admin.action(description=('Admin: Run accounting setup'))
def init_accounting_setup(modeladmin, request, queryset):    
    # Check
    if action_check_nr_selected(request, queryset, 1):        
        tenant = queryset.first() 
        tenant_accounting_post_save(
            modeladmin.model, tenant, created=False, init=True, 
            request=request)
        messages.success(request, _("cashCtrl initialized"))        
        return
        try:
            tenant_accounting_post_save(
                modeladmin.model, tenant, created=False, init=True, 
                request=request)
            messages.success(request, _("cashCtrl initialized"))
        except Exception as e:
            messages.error(request, _('Unexpected error: ') + str(e))


@action_with_form(
    forms.CreateUserForm, description=_("Create a User"))
def tenant_setup_create_user(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')
        person = data['person']
        if (data['username'] in [x.username for x in User.objects.all()]
                or UserProfile.objects.filter(person=person)):
            messages.warning(request, _("User already existing"))
            return 
        
        # Add user
        groups = [group for group in data.pop('groups')]
        password = generate_random_password()        
        user = User.objects.create_user(
            username=data['username'],
            password=password,
            first_name=person.first_name,
            last_name=person.last_name
        )
        
        # Register user
        setup = queryset.first()
        setup.users.add(user)
        
        # Add Profile
        UserProfile.objects.create(
            user=user, 
            person=data['person'],
            created_by=request.user
        )
        
        # Add Groups        
        user.groups.add(*groups)
        msg = _("Created {user} with password").format(
            user=data['username'], password=password)
        messages.info(request, msg)
