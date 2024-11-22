# vault/models.py
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _


from core.models import (
    LogAbstract, NotesAbstract, TenantAbstract, CITY_CATEGORY)
from scerp.locales import CANTON_CHOICES
from .locales import (REGISTRATION_PLAN)
# from .mixins import ()


# Registration Plan ----------------------------------------------------------
class RegistrationPlanCanton(LogAbstract, NotesAbstract):
    '''Model for Registration Plan (Canton).
    Only accessible by admin!
    '''    
    name = models.CharField(
        max_length=250, **REGISTRATION_PLAN.Field.name)
    canton = models.CharField(
        max_length=2, choices=CANTON_CHOICES, 
        **REGISTRATION_PLAN.Field.canton)
    category = models.CharField(
        max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True, **REGISTRATION_PLAN.Field.category)     
    plan_version = models.CharField(
        max_length=100, **REGISTRATION_PLAN.Field.plan_version)
    date = models.DateField(
        **REGISTRATION_PLAN.Field.date)
    excel = models.FileField(
        upload_to='uploads/', **REGISTRATION_PLAN.Field.excel)
    exported_at = models.DateTimeField(
        null=True, blank=True, **REGISTRATION_PLAN.Field.exported_at)

    def __str__(self):
        return f'{self.name}, V{self.plan_version}'

    class Meta:
        ordering = ['canton', 'name']
        verbose_name = REGISTRATION_PLAN.verbose_name
        verbose_name_plural = REGISTRATION_PLAN.verbose_name_plural
