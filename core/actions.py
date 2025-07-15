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
from . import forms
from .models import Person, PersonContact
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
    forms.TenantUserGroupForm, description=_("Assign Groups"))
def tenant_user_assign_groups(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        user = queryset.first().user     

        # Replace the user's groups with the selected groups
        user.groups.set(data['groups'])
        user.save()        


@action_with_form(
    forms.AssignTitleForm, description=_("Assign Title to Users"))
def assign_title(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, max_count=10):
        title = data['title']
        for person in queryset.all():
            person.title = title
            person.save()
