from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from app.models import Client, prepare__str__
    

class Inhabitant(models.Model):
    name = models.CharField(max_length=250)
    def __str__(self):
        return self.name
    class Meta:
        ordering = ['name']
        verbose_name = _("Einwohner")
        verbose_name_plural = _("Einwohner")