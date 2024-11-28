# vault/models.py
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _


from core.models import (
    LogAbstract, NotesAbstract, TenantAbstract, CITY_CATEGORY)
from scerp.locales import CANTON_CHOICES


# Registration Plan ----------------------------------------------------------
class RegistrationPlanAbstract(models.Model):
    '''Model for Registration Plan (Canton).
    Only accessible by admin!
    '''    
    name = models.CharField(
        _('Name'),max_length=250, 
        help_text=_('Enter the name of the registration plan'))
    canton = models.CharField(
        _('Canton'), max_length=2, choices=CANTON_CHOICES, 
        help_text=_('Select the associated canton for this registration plan.'))
    category = models.CharField(
        _('Category'), max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True, 
        help_text=_('Choose the category from the available city options.'))     
    plan_version = models.CharField(
        _('Plan Version'), max_length=100,
        help_text=_('Specify the version of the registration plan.'))
    date = models.DateField(
        _('Date'), 
        help_text=_('Enter the date for this registration plan record.'))
    excel = models.FileField(
        _('Excel File'), upload_to='uploads/', 
        help_text=_('Upload the Excel file associated with this registration plan.'))
    exported_at = models.DateTimeField(
        _('Exported At'), null=True, blank=True, 
        help_text=_('Record the date and time this plan use to create positions.'))
    website_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f'{self.name}, V{self.plan_version}'

    class Meta:
        abstract = True
        ordering = ['canton', 'name']
        verbose_name = _('Registration Plan (Canton)')
        verbose_name_plural = _('Registration Plans (Canton)')


class RegistrationPlanCanton(
        RegistrationPlanAbstract, LogAbstract, NotesAbstract):
    pass


class LeadAgency(LogAbstract, NotesAbstract):  # Federführung
    name = models.CharField(
        max_length=255,
        verbose_name=_("Lead Agency"),
        help_text=_("Name of the responsible organization or agency (e.g., Zweckverband).")
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Description of the agency's role."),
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Lead Agency")
        verbose_name_plural = _("Lead Agencies")
        ordering = ['name']
        

class RetentionPeriod(LogAbstract, NotesAbstract):  # Aufbewahrungsfrist
    name = models.CharField(
        max_length=50,
        verbose_name=_("Retention Period"),
        help_text=_("Retention period, e.g., 10 years, 50 years, or 'as long as valid'.")
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Explanation of the retention period."),
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Retention Period")
        verbose_name_plural = _("Retention Periods")
        ordering = ['name']


class LegalBasis(LogAbstract, NotesAbstract):  # Rechtliche/interne Grundlage
    name = models.CharField(
        max_length=255,
        verbose_name=_("Legal/Organizational Basis"),
        help_text=_("Legal or internal organizational basis (e.g., Gemeindegesetz, intern/IDG).")
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Explanation of the legal or internal basis."),
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Legal Basis")
        verbose_name_plural = _("Legal Bases")
        ordering = ['name']


class ArchivalEvaluation(LogAbstract, NotesAbstract):  # Archivische Bewertung
    name = models.CharField(
        max_length=255,
        verbose_name=_("Archival Evaluation"),
        help_text=_("Evaluation for archiving, e.g., 'fully archive' or 'destroy'.")
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Details on the archival evaluation."),
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Archival Evaluation")
        verbose_name_plural = _("Archival Evaluations")
        ordering = ['name']


class RegistrationPosition(LogAbstract, NotesAbstract):  # Previously FilePlan
    registration_plan = models.ForeignKey(
        RegistrationPlanCanton,
        on_delete=models.CASCADE,
        verbose_name=_("Registration Plan"),
        help_text=_("The registration plan to which this position belongs."),
        related_name="positions"
    )
    is_category = models.BooleanField()
    number = models.CharField(
        max_length=50,
        verbose_name=_("Number"),
        help_text=_("The number assigned to this record, e.g., 1.1, 2.3.2.")
    )
    position = models.CharField(
        max_length=255,
        verbose_name=_("Registration Position"),
        help_text=_("The position name in the registration plan (e.g., Budgets, Delegiertenversammlung).")
    )
    lead_agency = models.ForeignKey(
        LeadAgency,
        on_delete=models.SET_NULL,
        verbose_name=_("Lead Agency"),
        help_text=_("Responsible lead agency."),
        null=True,
        blank=True
    )
    retention_period = models.ForeignKey(
        RetentionPeriod,
        on_delete=models.SET_NULL,
        verbose_name=_("Retention Period"),
        help_text=_("Retention period for the record."),
        null=True,
        blank=True
    )
    legal_basis = models.ForeignKey(
        LegalBasis,
        on_delete=models.SET_NULL,
        verbose_name=_("Legal Basis"),
        help_text=_("Legal or internal basis for this record."),
        null=True,
        blank=True
    )
    archival_evaluation = models.ForeignKey(
        ArchivalEvaluation,
        on_delete=models.SET_NULL,
        verbose_name=_("Archival Evaluation"),
        help_text=_("Evaluation regarding archiving the record."),
        null=True,
        blank=True
    )
    remarks = models.TextField(
        verbose_name=_("Remarks"),
        help_text=_("Additional comments or notes."),
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.number} - {self.position}"

    class Meta:
        verbose_name = _("Registration Position")
        verbose_name_plural = _("Registration Positions")
        ordering = ['number']  # Ensures positions are ordered numerically.




class RegistrationPlan(RegistrationPlanAbstract, TenantAbstract):
    pass
