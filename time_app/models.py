'''
time_app/models.py
'''
from django.db import models

from core.models import NotesAbstract, LogAbstract


class Person(NotesAbstract, LogAbstract):  
    name = models.CharField(
        max_length=100, default="Michael")
    api_key = models.CharField(
        max_length=100, default="YzJkYTg3NTgtZWU5Zi00ZWM5LThhOTMtZjk0OTdlOTY4ZTBi"
    )
    workspace_id = models.CharField(
        max_length=32, default="67829f2d1c567d719f23da07"
    )
    
    def __str__(self):
        return self.name


class Project(NotesAbstract, LogAbstract):
    """Model to represent a project."""
    
    class ClockifyColors(models.TextChoices):
        AMBER = "#FFC107", "Amber"
        BLUE = "#2196F3", "Blue"
        BLUE_GREY = "#607D8B", "Blue Grey"
        BROWN = "#795548", "Brown"
        CYAN = "#00BCD4", "Cyan"
        DEEP_ORANGE = "#FF5722", "Deep Orange"
        DEEP_PURPLE = "#673AB7", "Deep Purple"
        GREEN = "#4CAF50", "Green"
        GREY = "#9E9E9E", "Grey"
        INDIGO = "#3F51B5", "Indigo"
        LIGHT_BLUE = "#03A9F4", "Light Blue"
        LIGHT_GREEN = "#8BC34A", "Light Green"
        LIME = "#CDDC39", "Lime"
        ORANGE = "#FF9800", "Orange"
        PINK = "#E91E63", "Pink"
        PURPLE = "#9C27B0", "Purple"
        RED = "#F44336", "Red"
        TEAL = "#009688", "Teal"
        YELLOW = "#FFEB3B", "Yellow"
    
    class TYPE(models.TextChoices):
        PRESENCE = 'Ab-/Anwesenheit'
        ENTRY = 'Freie Eingabe'
        CLIENT = 'Kundenauftrag'
    
    # Time
    name = models.CharField(max_length=255)
    client_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Leave empty for now")
    billable = models.BooleanField(default=True)
    color = models.CharField(
        max_length=7,
        choices=ClockifyColors.choices,
        default=ClockifyColors.BLUE
    )    
    tags = models.JSONField(null=True, blank=True)    
    person = models.ForeignKey(
        Person, verbose_name=('person'),
        on_delete=models.CASCADE, related_name='person',
        help_text=('Project Setup')) 
        
    # project_id in clockify    
    c_id = models.CharField(max_length=24, null=True, blank=True)
        
    # Accounting
    type = models.CharField(
        max_length=20,
        choices=TYPE.choices,
        default=TYPE.ENTRY
    )    
    project = models.CharField(
        max_length=100, default='PR',  # 'Ab-/Anwesenheit'
        help_text="e.g. 21902412"
    )    
    position = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="e.g. 10-outsourcing"
    )    

    def __str__(self):
        return self.name