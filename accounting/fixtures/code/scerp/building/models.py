from django.db import models
from django.utils.translation import gettext_lazy as _

from app.models import Client


class BuildingForLater(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)     
    name = models.CharField(max_length=250)    

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Bauverwaltung")
        verbose_name_plural = _("Bauverwaltung")
        