'''core/actions.py
'''
from django.contrib import admin, messages
from django.contrib.auth.models import User, Group
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from django_admin_action_forms import action_with_form

from scerp.actions import action_check_nr_selected
from scerp.mixins import generate_random_password
from . import forms
from .models import UserProfile
from .signals import tenant_post_save


@admin.action(description=('Admin: Run setup'))
def init_setup(modeladmin, request, queryset):    
    # Check
    if action_check_nr_selected(request, queryset, 1):        
        instance = queryset.first() 
        try:
            tenant_post_save(
                modeladmin.model, instance, created=False, init=True, 
                request=request)
            messages.success(request, _("Scerp initialized"))
        except Exception as e:
            messages.error(request, _('Unexpected error: ') + str(e))        


@action_with_form(
    forms.CreateUserForm, description=_("Create a User"))
def tenant_setup_create_user(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        if data['username'] in [x.username for x in User.objects.all()]:
            messages.warning(request, _("User already existing"))
            return 
        
        # Add user
        groups = [group for group in data.pop('groups')]
        data['password'] = generate_random_password()        
        user = User.objects.create_user(**data)
        
        # Register user
        setup = queryset.first()
        setup.users.add(user)
        
        # Add Profile
        UserProfile.objects.create(user=user, created_by=request.user)
        
        # Add Groups        
        user.groups.add(*groups)
        msg = _("Created {user} with password {password}").format(
            user=data['username'], password=data['password'])
        messages.info(request, msg)
