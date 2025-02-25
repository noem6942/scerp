'''
scerp/actions.py

General actions used by all apps
'''
from django.contrib import admin
from django.utils.translation import gettext as _

# Helpers
def action_check_nr_selected(request, queryset, count=None, min_count=None):
    """
    This checks that a user selects the appropriate number of items in admin.py
    """
    if count is not None:
        if queryset.count() != count:
            msg = _('Please select excatly {count} record(s).').format(
                    count=count)
            messages.warning(request, msg)
            return False
    elif min_count is not None:
        if queryset.count() < min_count:
            msg =  _('Please select more than {count - 1} record(s).').format(
                    count=min_count)
            messages.warning(request, msg)
            return False

    return True


# Default row actions, general
@admin.action(description=_('Set inactive'))
def set_inactive(modeladmin, request, queryset):
    queryset.update(is_inactive=True)
    msg = _("Set {count} records as inactive.").format(count=queryset.count())
    messages.success(request, msg)


@admin.action(description=_('Set protected'))
def set_protected(modeladmin, request, queryset):
    queryset.update(is_protected=True)
    msg = _("Set {count} records as protected.").format(count=queryset.count())
    messages.success(request, msg)


# Default row actions, accounting
@admin.action(description=_("S. Sync with Accounting"))
def sync_accounting(modeladmin, request, queryset):
    ''' set is_enabled_sync to True and save to trigger post_save '''
    if action_check_nr_selected(request, queryset, min_count=1):
        for instance in queryset.all():
            if not instance.is_enabled_sync:
                instance.is_enabled_sync = True
                instance.save()


@admin.action(description=_("D. De-sync from Accounting"))
def de_sync_accounting(modeladmin, request, queryset):
    ''' update is_enabled_sync to False '''
    if action_check_nr_selected(request, queryset, min_count=1):
        queryset = queryset.update(is_enabled_sync=False)
