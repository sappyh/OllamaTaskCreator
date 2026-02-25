import requests
from src.interfaces import BaseTaskTarget

class VikunjaInterface(BaseTaskTarget):
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    def test_connection(self) -> bool:
        """
        Tests the connection to the Vikunja server by hitting /api/v1/info
        """
        try:
            response = requests.get(
                f'{self.base_url}/api/v1/info', 
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_projects(self) -> list:
        """
        Retrieves all projects the user has access to.
        Returns a list of project dictionaries or an empty list on failure.
        """
        try:
            response = requests.get(
                f'{self.base_url}/api/v1/projects',
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except requests.exceptions.RequestException:
            return []

    def create_task(self, project_id: int, title: str, description: str = "") -> dict:
        """
        Creates a new task in a specific project.
        Returns the created task dictionary or an empty dict on failure.
        """
        try:
            payload = {
                "title": title,
                "description": description
            }
            response = requests.put(
                f'{self.base_url}/api/v1/projects/{project_id}/tasks',
                headers=self.headers,
                json=payload,
                timeout=10
            )
            # Vikunja returns 201 Created on task creation
            if response.status_code in (200, 201):
                return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}
