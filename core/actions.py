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
from .models import Person, PersonContact, UserProfile
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
    forms.CreateUserForm, description=_("Create a User"))
def tenant_setup_create_user(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, 1):
        tenant_data = get_tenant_data(request)
        tenant_id = tenant_data.get('id')
        person = data['person']

        user = User.objects.filter(username=data['username']).first()
        if user:
            messages.warning(request, _("User already existing"))
        else:
            # create user
            groups = [group for group in data.pop('groups')]
            password = generate_random_password()
            email = PersonContact.objects.filter(person=person).first()
            user = User.objects.create_user(
                username=data['username'],
                password=password,
                first_name=person.first_name,
                last_name=person.last_name,
                email=email,
                is_staff=data.get('is_staff', False)
            )

        # Add user to tenant_setup
        tenant_setup = queryset.first()
        tenant_setup.users.add(user)

        # Add Profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults=dict(
                person=data['person'],
                created_by=request.user
            )
        )

        # Add Groups
        user.groups.add(*groups)
        msg = _("Created {user} with password {password}").format(
            user=data['username'], password=password)
        messages.info(request, msg)


@action_with_form(
    forms.AssignTitleForm, description=_("Assign Title to Users"))
def assign_title(modeladmin, request, queryset, data):
    __ = modeladmin  # disable pylint warning
    if action_check_nr_selected(request, queryset, max_count=10):
        title = data['title']
        for person in queryset.all():
            person.title = title
            person.save()
