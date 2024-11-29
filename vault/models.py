# vault/models.py
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _


from core.models import LogAbstract, NotesAbstract, Tenant, CITY_CATEGORY
from scerp.locales import CANTON_CHOICES


# Abstract ----------------------------------------------------------
class RegistrationPlanAbstract(LogAbstract, NotesAbstract):
    name = models.CharField(
        _('Name'),max_length=250,
        help_text=_('Enter the name of the registration plan'))
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


class RegistrationPositionAbstract(LogAbstract, NotesAbstract):
    is_category = models.BooleanField(
        _('is category'),
        help_text=_("If true it's only a document category, "
                    "no documents must be stored here."))           
    number = models.CharField(
        _("Number"), max_length=50,
        help_text=_("The number assigned to this record, e.g., 1.1, 2.3.2."))
    name = models.CharField(
        _("Registration Position"), max_length=255,        
        help_text=_("The position name in the registration plan (e.g., "
                    "Budgets, Delegiertenversammlung)."))
    remarks = models.TextField(
        _("Remarks"),  blank=True, null=True,
        help_text=_("Additional comments or notes."))

    def __str__(self):
        return f"{self.number} - {self.name}"

    class Meta:
        abstract = True


class RetentionPeriodAbstract(LogAbstract, NotesAbstract):
    ''' Aufbewahrungsfrist '''
    name = models.CharField(
        _("Retention Period"), max_length=50,
        help_text=_("Retention period, e.g., 10 years, 50 years, or "
                    "'as long as valid'."))
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Explanation of the retention period."))

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        verbose_name = _("Retention Period")
        verbose_name_plural = _("Retention Periods")
        ordering = ['name']


class LegalBasisAbstract(LogAbstract, NotesAbstract):
    ''' Rechtliche/interne Grundlage '''
    name = models.CharField(
        _("Legal/Organizational Basis"), max_length=255,
        help_text=_("Legal or internal organizational basis (e.g., "
                    "Gemeindegesetz, intern/IDG)."))
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Explanation of the legal or internal basis."))

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        verbose_name = _("Legal Basis")
        verbose_name_plural = _("Legal Bases")
        ordering = ['name']


class ArchivalEvaluationAbstract(LogAbstract, NotesAbstract):
    ''' Archivische Bewertung '''
    name = models.CharField(
        _("Archival Evaluation"), max_length=255,
        help_text=_("Evaluation for archiving, e.g., "
                    "'fully archive' or 'destroy'."))
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Details on the archival evaluation."))

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        verbose_name = _("Archival Evaluation")
        verbose_name_plural = _("Archival Evaluations")
        ordering = ['name']


class TenantAbstract(models.Model):
    ''' used for all models that need a tenant
    '''
    tenant = models.ForeignKey(
        Tenant, verbose_name=_('tenant'), on_delete=models.CASCADE,
        related_name='%(class)s_tenant',
        help_text=_('assignment of tenant / client'))

    class Meta:
        abstract = True


# Canton --------------------------------------------------------------------
class RegistrationPlanCanton(RegistrationPlanAbstract):
    canton = models.CharField(
        _('Canton'), max_length=2, choices=CANTON_CHOICES,
        help_text=_('Select the associated canton for this registration plan.'))
    category = models.CharField(
        _('Category'), max_length=1, choices=CITY_CATEGORY.choices,
        null=True, blank=True,
        help_text=_('Choose the category from the available city options.'))

    class Meta:
        ordering = ['canton', 'name']
        verbose_name = _('Registration Plan (Canton)')
        verbose_name_plural = _('Registration Plans (Canton)')


class LeadAgency(LogAbstract, NotesAbstract):
    ''' Federführung '''
    name = models.CharField(
        _("Lead Agency"), max_length=255,
    help_text=_("Name of the responsible organization or agency "
                "(e.g., Zweckverband)."))
    description = models.TextField(
        _("Description"), blank=True, null=True,
        help_text=_("Description of the agency's role."))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Lead Agency")
        verbose_name_plural = _("Lead Agencies")
        ordering = ['name']


class RetentionPeriodCanton(RetentionPeriodAbstract):
    pass


class LegalBasisCanton(LegalBasisAbstract):
    pass


class ArchivalEvaluationCanton(ArchivalEvaluationAbstract):
    pass


class RegistrationPositionCanton(RegistrationPositionAbstract):
    registration_plan = models.ForeignKey(
        RegistrationPlanCanton,
        on_delete=models.CASCADE,
        verbose_name=_("Registration Plan"),
        help_text=_("The registration plan to which this position belongs."),
        related_name="positions")
    lead_agency = models.ForeignKey(
        LeadAgency, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Lead Agency"),
        help_text=_("Responsible lead agency."))
    retention_period = models.ForeignKey(
        RetentionPeriodCanton, on_delete=models.SET_NULL,
        blank=True, null=True,
        verbose_name=_("Retention Period"),
        help_text=_("Retention period for the record."))
    legal_basis = models.ForeignKey(
        LegalBasisCanton, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Legal Basis"),
        help_text=_("Legal or internal basis for this record."))
    archival_evaluation = models.ForeignKey(
        ArchivalEvaluationCanton, on_delete=models.SET_NULL,
        blank=True, null=True,
        verbose_name=_("Archival Evaluation"),
        help_text=_("Evaluation regarding archiving the record."))

    class Meta:
        verbose_name = _("Registration Position (Canton)")
        verbose_name_plural = _("Registration Positions (Canton)")
        ordering = ['registration_plan', 'name']


# Municipal------------------------------------------------------------------
class RegistrationPlan(TenantAbstract, RegistrationPlanAbstract):
    class Meta:
        ordering = ['name']
        verbose_name = _('Registration Plan')
        verbose_name_plural = _('Registration Plans')


class RetentionPeriod(TenantAbstract, RetentionPeriodAbstract):
    pass


class LegalBasis(TenantAbstract, LegalBasisAbstract):
    pass


class ArchivalEvaluation(TenantAbstract, ArchivalEvaluationAbstract):
    pass


class RegistrationPosition(TenantAbstract, RegistrationPositionAbstract):
    registration_plan = models.ForeignKey(
        RegistrationPlan,
        on_delete = RegistrationPositionCanton._meta.get_field(
            'registration_plan').remote_field.on_delete,
        verbose_name=RegistrationPositionCanton._meta.get_field(
            'registration_plan').verbose_name,
        help_text=RegistrationPositionCanton._meta.get_field(
            'registration_plan').help_text,
        related_name='registration_plan'
    )
    lead_agency = models.ForeignKey(
        Group, blank=True, null=True,
        on_delete = RegistrationPositionCanton._meta.get_field(
            'lead_agency').remote_field.on_delete,
        verbose_name=RegistrationPositionCanton._meta.get_field(
            'lead_agency').verbose_name,
        help_text=RegistrationPositionCanton._meta.get_field(
            'lead_agency').help_text,
        related_name='lead_agency'
    )
    retention_period = models.ForeignKey(
        RetentionPeriod, blank=True, null=True,
        on_delete = RegistrationPositionCanton._meta.get_field(
            'retention_period').remote_field.on_delete,
        verbose_name=RegistrationPositionCanton._meta.get_field(
            'retention_period').verbose_name,
        help_text=RegistrationPositionCanton._meta.get_field(
            'retention_period').help_text,
        related_name='retention_period'
    )
    legal_basis = models.ForeignKey(
        LegalBasis, blank=True, null=True,
        on_delete = RegistrationPositionCanton._meta.get_field(
            'legal_basis').remote_field.on_delete,
        verbose_name=RegistrationPositionCanton._meta.get_field(
            'legal_basis').verbose_name,
        help_text=RegistrationPositionCanton._meta.get_field(
            'legal_basis').help_text,
        related_name='legal_basis'
    )
    archival_evaluation = models.ForeignKey(
        ArchivalEvaluation, blank=True, null=True,
        on_delete = RegistrationPositionCanton._meta.get_field(
            'archival_evaluation').remote_field.on_delete,
        verbose_name=RegistrationPositionCanton._meta.get_field(
            'archival_evaluation').verbose_name,
        help_text=RegistrationPositionCanton._meta.get_field(
            'archival_evaluation').help_text,
        related_name='archival_evaluation'
    )

    class Meta:
        verbose_name = _("Registration Position")
        verbose_name_plural = _("Registration Positions")
        ordering = ['number']  # Ensures positions are ordered numerically.
