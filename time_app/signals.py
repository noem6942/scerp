# time_app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .connector_clockify import Clock
from .models import Person, Project



@receiver(post_save, sender=Project)
def create_project_signal(sender, instance, created, **kwargs):
    """
    Signal to create a project via API when a new Project instance is saved.
    """
    if created:
        # Initialize the ProjectManager
        person = Person.objects.get(id=instance.person.id)

        # Call the create_project API method
        clock = Clock(person.api_key, person.workspace_id)
        response = clock.create_project(
            instance.name, instance.client_id, instance.billable, 
            instance.color, instance.tags)
