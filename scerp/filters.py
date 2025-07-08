'''
scerp/filters.py
'''
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class StepFilter(admin.SimpleListFilter):
    '''
    Abstract filter class for step-based numeric filters.
    Subclass must define: title, fieldname, parameter_name, unit, steps.
    '''
    def lookups(self, request, model_admin):
        steps = getattr(self, 'steps')
        unit = getattr(self, 'unit')
        step_max = max(steps)

        return [('null', _('Empty'))] + [
            (str(steps[i]), f'{steps[i]} - {steps[i + 1]} {unit}')
            for i in range(len(steps) - 1)
        ] + [
            (str(step_max), f'{step_max} {unit} +')
        ]

    def queryset(self, request, queryset):
        value = self.value()
        steps = getattr(self, 'steps')
        fieldname = getattr(self, 'fieldname')
        step_max = max(steps)

        if value is None:
            return queryset

        if value == 'null':
            return queryset.filter(**{f'{fieldname}__isnull': True})

        try:
            value = int(value)
        except ValueError:
            return queryset

        if value == step_max:
            return queryset.filter(**{f'{fieldname}__gt': step_max})

        for i in range(len(steps) - 1):
            min_val, max_val = steps[i], steps[i + 1]
            if value == min_val:
                return queryset.filter(**{
                    f'{fieldname}__gte': min_val,
                    f'{fieldname}__lt': max_val
                })

        return queryset
