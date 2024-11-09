# validations.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_person(first_name, last_name, company):
	if not first_name and not last_name and not company:
		raise ValidationError(_('Either First Name, Last Name or Company must be set.'))