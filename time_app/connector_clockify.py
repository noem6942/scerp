'''
app_time/connector_clockify.py
'''
import logging
import requests
import re

from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware

from .models import (
    Workspace, ClockifyUser, Tag, Client, Project, TimeEntry
)

# Define Swiss Holidays (example dates)
SWISS_HOLIDAYS = [
    "2025-01-01",  # New Year's Day
    "2025-04-18",  # Good Friday
    "2025-04-21",  # Easter Monday
    "2025-05-01",  # Labor Day
    "2025-08-01",  # Swiss National Day
    "2025-12-25",  # Christmas Day
]

logger = logging.getLogger(__name__)  # Using the app name for logging


# mixins, we change right at down and uploading of data
def camel_to_snake(name):
    ''' we don't use cashCtrl camel field names '''
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def snake_to_camel(snake_str):
    ''' we don't use cashCtrl camel field names '''
    components = snake_str.split('_')
    camel_case_str = ''.join(x.title() for x in components)

    # ensure the first letter is lowercase and return
    return camel_case_str[0].lower() + camel_case_str[1:]


def convert_to_utc(time):
    """Convert a given datetime to UTC."""
    if isinstance(time, str):
        time = datetime.fromisoformat(time)
    local_time = time.replace(tzinfo=ZoneInfo(self.timezone))
    return local_time.astimezone(ZoneInfo("UTC"))


def make_datetime(iso_datetime):
    '''Input datetime string:
        iso_datetime = '2025-01-11T09:00:00Z'
    '''
    # Convert string to a naive datetime object
    naive_datetime = datetime.strptime(iso_datetime, '%Y-%m-%dT%H:%M:%SZ')

    # Make it timezone-aware using UTC
    aware_datetime = naive_datetime.replace(tzinfo=ZoneInfo('UTC'))

    return aware_datetime


class Clock:
    
    def __init__(self, api_key, workspace_id):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base_url = "https://api.clockify.me/api/v1"
        self.workspace_url = f"{self.base_url}/workspaces/{self.workspace_id}"
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        self.timezone = self.get_workspace_timezone()
        self.tags = self.get_workspace_tags()

    def get_user(self):
        """Fetch current user details."""
        response = requests.get(f"{self.base_url}/user", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_workspace_timezone(self):
        """Fetch workspace details and return the timezone."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        workspace_data = response.json()
        return workspace_data.get("timezone", "UTC")  # Default to UTC if not found

    def get_workspace_tags(self):
        """Get all tags in a workspace."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/tags"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_projects(self, start_date=None, end_date=None):
        """Fetch all projects in the workspace."""
        response = requests.get(f"{self.base_url}/workspaces/{self.workspace_id}/projects", headers=self.headers)
        response.raise_for_status()
        data = response.json()
        obj, created = Project.objects.update_or_create(
            c_id=id, defaults = dict(
                hourly_rate=data['hourlyRate']['amount'],
                currency=data['hourlyRate']['currency'],
                client_name=data['clientName'],
                billable=data['billable']
            ))
        
        return 

    def create_time_entry(self, project_id, description, start_time, end_time):
        """Log a time entry."""
        # Convert to UTC
        start_time_utc = convert_to_utc(make_datetime(start_time))
        end_time_utc = convert_to_utc(make_datetime(end_time))

        # Format as ISO 8601 (Clockify expects this format)
        start_time_str = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_str = end_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Prepare the data for the request
        data = {
            "start": start_time_str,
            "end": end_time_str,
            "billable": True,
            "description": description,
            "projectId": project_id
        }

        # Make the API request to log the time entry
        url = f"{self.base_url}/workspaces/{self.workspace_id}/time-entries"
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    # project
    def create_project(self, data):
        """Create a new project."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/projects"        
        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code == 201:
            # Successfully created project
            logging.info(f"Project `{data['name']}` created successfully!")
            return response.json()  # This will return the created project data
        else:
            logging.error(f"Error creating project: {response.status_code}")
            return None

    def update_project(self, project_id, data):
        url = f"{self.base_url}/workspaces/{self.workspace_id}/projects/{project_id}"
        response = requests.patch(url, json=data, headers=self.headers)
        if response.status_code == 200:
            # Successfully updated project
            logging.info(f"Project '{project_id}' updated successfully!")
            return response.json()  # This will return the updated project data
        else:
            logging.error(f"Error updating project: {response.status_code}")
            return None

    def delete_project(self, project_id):
        url = f"{self.workspace_url}/projects/{project_id}"
        response = requests.delete(url, headers=self.headers)        
        if response.status_code == 200:
            # Successfully deleted the project
            print(f"Project '{project_id}' deleted successfully!")
            return response.json()  # This will return the response data if needed
        else:
            raise Exception(
                f"Failed to delete project '{project_id}'. "
                f"HTTP Status Code: {response.status_code}, "
                f"Response: {response.text}"
            )

    def create_client(self, data):
        """Create a new tag only if it doesn't already exist."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/clients"        
        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code == 201:
            # Successfully created client
            logging.info(f"Client `{data['name']}` created successfully!")
            return response.json()  # This will return the created client data
        else:
            logging.error(f"Error creating client: {response.status_code}")
            return None

    def create_tag(self, data):
        """Create a new tag only if it doesn't already exist."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/tags"        
        response = requests.post(url, json=data, headers=self.headers)        
        if response.status_code == 201:
            # Successfully created client
            logging.info(f"Tag `{data['name']}` created successfully!")
            return response.json()  # This will return the created client data
        else:
            logging.error(f"Error creating tag: {response.status_code}")
            return None

    def get_time_entries(self, start_date=None, end_date=None):
        """Fetch all time entries for the user."""
        user = self.get_user()
        user_id = user["id"]
        url = f"{self.base_url}/workspaces/{self.workspace_id}/user/{user_id}/time-entries"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def check_holiday(self, date):
        """Check if the given date is a holiday."""
        return date in SWISS_HOLIDAYS

    def create_time_entry(self, project_id):
        """Example: Log a sample time entry for a project."""
        # Get current time in the local timezone (e.g., Europe/Zurich)
        now = datetime.now(ZoneInfo("Europe/Zurich"))

        # Set the start and end time for a typical workday (9am to 5pm)
        start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=17, minute=0, second=0, microsecond=0)

        # Check if today is a holiday before logging the time entry
        if not self.check_holiday(now.strftime("%Y-%m-%d")):
            self.create_time_entry(project_id, "Sample Work", start_time, end_time)
            print("Sample time entry logged.")

    def display_projects(self):
        """Display all available projects in the workspace."""
        projects = self.get_projects()
        print("Available Projects:")
        for project in projects:
            print(f"- {project['name']} (ID: {project['id']})")

    def display_time_entries(self):
        """Display all time entries for the user."""
        time_entries = self.get_time_entries()
        print("Your time entries:")
        for entry in time_entries:
            print(f"- {entry['description']}: {entry['timeInterval']['start']} to {entry['timeInterval']['end']}")


class ClockConnector:
    
    def __init__(self, workspace, admin):
        if not workspace.tenant.is_app_time_trustee:
            raise ValidationError("Only Trustees can create workspaces")
        self.workspace = workspace        
        self.admin = admin

    def load_timesheets(self):
        # Init
        count, warnings = 0, []
        clock = Clock(self.workspace.api_key, self.workspace.c_id)
        
        data_list = clock.get_time_entries()
        for data in data_list:
            data = {camel_to_snake(key): value for key, value in data.items()}
            
            # Check User
            user_id = data.pop('user_id')
            clockify_user = ClockifyUser.objects.filter(c_id=user_id).first()
            if not clockify_user:
                msg = f"User '{user_id}' not existing."
                warnings.append(msg)                
                logger.warning(msg)
                continue            
            
            # Check Project            
            project_id = data.pop('project_id')
            project = Project.objects.filter(c_id=project_id).first()
            if not project:   
                msg = (
                    f"{data['time_interval']['start']}: Project '{project_id}'"
                    f"{data['description']} not existing.")
                warnings.append(msg)
                logger.warning(msg)
                continue            
                                
            # TimeEntry
            time, created = TimeEntry.objects.get_or_create(
                c_id=data.pop('id'),
                defaults={
                    'description': data['description'],
                    'start_time': make_datetime(
                        data['time_interval']['start']),
                    'end_time': make_datetime(
                        data['time_interval']['end']),
                    'project': project,
                    'clockify_user': clockify_user,
                    'tenant': project.tenant,
                    'created_by': self.admin
                })
            if created:
                count += 1
                
        logger.info(f"{count} time entries created.")
        return count, warnings


# Main Execution
if __name__ == "__main__":
    # Init
    api_key = "YzJkYTg3NTgtZWU5Zi00ZWM5LThhOTMtZjk0OTdlOTY4ZTBi"
    workspace_id="67829f2d1c567d719f23da07"

    # Create a Clock instance
    clock = Clock(api_key, workspace_id)

    # Get
    if False:  # Set to True to log a time entry
        data_list = clock.get_projects()
        for data in data_list:
            print("*data", data)

    # Create ----
    # Example: Log a sample time entry (modify as needed)
    if False:  # Set to True to log a time entry
        example_project_id = clock.get_projects()[0]["id"]  # Use the first project's ID
        clock.create_time_entry(example_project_id)

    # Create Tag
    if True:
        new_tag = clock.create_tag("Testing2")
        print("Created tag:", new_tag)

    # Create Project
    if False:
        new_project = clock.create_project("Default Project 2")
        print("Created project:", new_project)

    # View ----
    # Display projects and time entries
    if False:
        data = clock.get_time_entries()

        clock.display_time_entries()
        print("*", data)
