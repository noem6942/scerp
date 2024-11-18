# scerp/actions.py
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from .locales import ACTION

# Admin Actions --------------------------------------------------------------
def action_check_nr_selected(request, queryset, count=None, min_count=None):
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
