# accounting/mixins.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image

from scerp.mixins import is_url_friendly


# Tenant
def validate_tenant(obj):
    if not is_url_friendly(obj.code):
        msg = _("Code cannot be displayed in an url.")
        raise ValidationError(msg)
    elif obj.code != obj.code.lower():
        msg = _("Code contains upper letters")
        raise ValidationError(msg)       


# TenantLocation
def validate_tenant_setup(obj):
    """Validate Tenant Setup"""
    MAX_SIZE_KB = 400  # unit: KB
    MAX_RESOLUTION = (2500, 2500)

    # Logo
    if obj.logo:  # Ensure a logo is uploaded before validation
        # Validate that the uploaded file is of an allowed type.
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if obj.logo.file.content_type not in allowed_types:
            msg = _("Unsupported file type. Only JPG, GIF, and PNG are allowed.")
            raise ValidationError(msg)

        # Validate that the file size does not exceed MAX_SIZE_KB.
        if obj.logo.size > max_size_kb * 1024:
            raise ValidationError(_(f"File size exceeds {MAX_SIZE_KB}KB."))

        # Validate that the image resolution does not exceed 2500x2500 pixels.        
        try:
            img = Image.open(obj.logo)
            if img.width > MAX_RESOLUTION[0] or img.height > MAX_RESOLUTION[1]:
                raise ValidationError(
                    _("Image resolution exceeds "
                      f"{MAX_RESOLUTION[0]} * {MAX_RESOLUTION[1]} pixels."))
        except Exception:
            raise ValidationError(_("Invalid image file."))
