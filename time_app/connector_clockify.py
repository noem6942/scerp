import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Define Swiss Holidays (example dates)
SWISS_HOLIDAYS = [
    "2025-01-01",  # New Year's Day
    "2025-04-18",  # Good Friday
    "2025-04-21",  # Easter Monday
    "2025-05-01",  # Labor Day
    "2025-08-01",  # Swiss National Day
    "2025-12-25",  # Christmas Day
]

# Mandatory working hours (e.g., 8 hours per day)
MANDATORY_HOURS = 8


class Clock:

    def __init__(self, api_key, workspace_id):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base_url = "https://api.clockify.me/api/v1"
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

    def get_projects(self):
        """Fetch all projects in the workspace."""
        response = requests.get(f"{self.base_url}/workspaces/{self.workspace_id}/projects", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def convert_to_utc(self, time):
        """Convert a given datetime to UTC."""
        if isinstance(time, str):
            time = datetime.fromisoformat(time)
        local_time = time.replace(tzinfo=ZoneInfo(self.timezone))
        return local_time.astimezone(ZoneInfo("UTC"))

    def create_time_entry(self, project_id, description, start_time, end_time):
        """Log a time entry."""
        # Convert to UTC
        start_time_utc = self.convert_to_utc(start_time)
        end_time_utc = self.convert_to_utc(end_time)

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

    def create_project(
            self, project_name, client_id=None, billable=True, color=None,
            tags=None):
        """Create a new project."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/projects"

        data = {
            "name": project_name,
            "clientId": client_id,  # Optional: client ID if you have clients in your workspace
            "billable": billable,
            "color": color,  # Optional: Project color in hex format, e.g., "#FF5733"
            "tags": tags  # Optional: List of tag IDs to associate with this project
        }

        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()  # Raise error for bad responses
        return response.json()

    def create_tag(self, tag_name):
        """Create a new tag only if it doesn't already exist."""
        # First, get all tags in the workspace to check if the tag already exists
        existing_tags = self.get_workspace_tags()
        existing_tag_names = [tag['name'] for tag in existing_tags]

        if tag_name in existing_tag_names:
            print(f"Tag '{tag_name}' already exists.")
            return None  # Return None or an appropriate response indicating no new tag created

        # If tag doesn't exist, create a new one
        url = f"{self.base_url}/workspaces/{self.workspace_id}/tags"
        data = {
            "name": tag_name
        }

        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()  # Raise error for bad responses
        return response.json()

    def get_time_entries(self):
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

# Main Execution
if __name__ == "__main__":
    # Init
    api_key = "YzJkYTg3NTgtZWU5Zi00ZWM5LThhOTMtZjk0OTdlOTY4ZTBi"
    workspace_id="67829f2d1c567d719f23da07"

    # Create a Clock instance
    clock = Clock(api_key, workspace_id)

    # Create ----
    # Example: Log a sample time entry (modify as needed)
    if False:  # Set to True to log a time entry
        example_project_id = clock.get_projects()[0]["id"]  # Use the first project's ID
        clock.create_time_entry(example_project_id)

    # Create Tag
    if True:
        new_tag = clock.create_tag("Testing")
        print("Created tag:", new_tag)

    # Create Project
    if False:
        new_project = clock.create_project("Default Project")
        print("Created project:", new_project)

    # View ----
    # Display projects and time entries
    clock.display_projects()

    clock.display_time_entries()
    print("*", clock.tags)
