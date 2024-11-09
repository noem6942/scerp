# accounting/mixins.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from scerp.mixins import is_url_friendly


class TenantValidate:

    def clean_related_data(self):
        if not is_url_friendly(self.code):
            msg = _("Code cannot be displayed in an url.")
            raise ValidationError(msg)
        elif self.code != self.code.lower():
            msg = _("Code contains upper letters")
            raise ValidationError(msg)            
