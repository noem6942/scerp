# time_app/signals.py
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

from .connector_clockify import Clock
from .models import Client, Tag, Project


@receiver(post_save, sender=Client)
def create_client_signal(sender, instance, created, **kwargs):
    data = {
        "name": instance.name,
        # "email" # contact_email,   # Optional
        # "phone": contact_phone,   # Optional
    }
    c = Clock(instance.workspace.api_key, instance.workspace.c_id)
    response = c.create_client(data)
    if response:
        instance.c_id = response['id']
        instance.save()    


@receiver(post_save, sender=Tag)
def create_tag_signal(sender, instance, created, **kwargs):
    data = {
        "name": instance.name,
    }
    c = Clock(instance.workspace.api_key, instance.workspace.c_id)
    response = c.create_tag(data)
    if response:
        instance.c_id = response['id']
        instance.save()    


@receiver(pre_save, sender=Project)
def project_pre_save(sender, instance, **kwargs):
    """
    Signal to create a project via API when a new Project instance is saved.
    """
    c = Clock(instance.workspace.api_key, instance.workspace.c_id)    
    data = {
        "name": instance.name,
        "client_id": instance.client.c_id if instance.client else None,
        "billable": instance.billable,
        "color": instance.color,
        # "tags": [x.c_id for x in instance.tags.all()],
    }    
    if instance.c_id:
        response = c.create_project(data)
        if response:
            instance.c_id = response['id']
            instance.save()   
    else:
        response = c.update_project(instance.c_id, data)  
   

@receiver(post_save, sender=Project)
def project_pre_save(sender, instance, **kwargs):
    """
    Signal to create a project via API when a new Project instance is saved.
    """
    c = Clock(instance.workspace.api_key, instance.workspace.c_id) 
    tags = [x.c_id for x in instance.tags.all()]
    print("*tags")
    
@receiver(pre_delete, sender=Project)
def project_pre_delete(sender, instance, **kwargs):
    """Triggered after a Project is deleted."""
    c = Clock(instance.workspace.api_key, instance.workspace.c_id)
    response = c.delete_project(instance.c_id)
    print("*response", response)
