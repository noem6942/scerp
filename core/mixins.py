# accounting/mixins.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from scerp.mixins import is_url_friendly


class TenantMixin:

    def clean_related_data(self):
        if not is_url_friendly(self.code):
            msg = _("Code cannot be displayed in an url.")
            raise ValidationError(msg)
        elif self.code != self.code.lower():
            msg = _("Code contains upper letters")
            raise ValidationError(msg)            

    def post_save(self, *args, **kwargs):
        # Perform the follow-up actions here
        TenantSetup.objects.get_or_create(
            tenant=self, 
            created_by=self.created_by, 
            modified_by=self.modified_by
        )
