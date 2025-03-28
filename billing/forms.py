'''
billing/forms.py
'''
import datetime

from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django_admin_action_forms import action_with_form, AdminActionForm

from core.models import UserProfile
from .models import Period

LABEL_BACK = _("Back")


class RouteCopyActionForm(AdminActionForm):
    period = forms.ModelChoiceField(
        label=_('Period'),
        required=True,
        queryset=Period.objects.none()
    )
    name = forms.CharField(
        label=_('Route Name'),
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter name')})
    )

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        tenant = route.tenant        
        self.fields['period'].queryset = Period.objects.filter(
            tenant=tenant).order_by('-end')        
        

class RouteMeterExportJSONActionForm(AdminActionForm):
    route_date = forms.DateField(
        label=_('Route Date'),
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    responsible_user = forms.ModelChoiceField(
        label=_('Employee responsible'),
        required=True,
        queryset=UserProfile.objects.none()
    )
    filename = forms.CharField(
        label=_('Filename'),
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )
    key_enabled = forms.BooleanField(
        label=_('Test data'),
        required=False,
        initial=False,
        help_text=_("Generate Test Data"),
    )
    
    class Meta:
        list_objects = True

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        tenant = route.tenant
        today = datetime.date.today()
        
        if not route.previous_period:
            messages.warning(request, _('Warning: no previous period given'))        
            self.Meta.confirm_button_text = LABEL_BACK
            self.fields['responsible_user'].required = False
            
        employees = UserProfile.objects.filter(
            person__tenant=tenant).order_by(
                'user__last_name', 'user__first_name')
        self.fields['responsible_user'].queryset = employees
        self.fields['route_date'].initial = datetime.date.today
        self.fields['filename'].initial = f"route_{route.name}_{today}.json"


class RouteMeterExportExcelActionForm(AdminActionForm):    
    filename = forms.CharField(
        label=_('Filename'),
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )
    key_enabled = forms.BooleanField(
        label=_('Test data'),
        required=False,
        initial=False,
        help_text=_("Generate Test Data"),
    )

    def __post_init__(self, modeladmin, request, queryset):
        route = queryset.first()
        today = datetime.date.today()
        self.fields['filename'].initial = f"route_{route.name}_{today}.xlsx"


class AnaylseMeasurentExcelActionForm(AdminActionForm):
    filename = forms.CharField(
        label=_('Filename'),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )
    ws_title = forms.CharField(
        label=_('Worksheet Name'),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': _('Enter filename')})
    )    

    def __post_init__(self, modeladmin, request, queryset):
        measurement = queryset.first()        
        today = datetime.date.today()

        self.fields['filename'].initial = (
            f"analysis_{measurement.route.name}_{today}.xlsx")
        self.fields['ws_title'].initial = (f"{measurement.route.name}")
