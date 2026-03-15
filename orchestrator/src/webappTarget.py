import requests
from typing import List, Optional
from orchestrator.src.interfaces import BaseTaskTarget
from common.src.models import Task

class WebappTaskTarget(BaseTaskTarget):
    """
    Implementation of BaseTaskTarget that feeds tasks directly into the Webapp via its REST API.
    """
    
    def __init__(self, webapp_base_url: str = "http://127.0.0.1:8000"):
        self.base_url = webapp_base_url.rstrip("/")

    def test_connection(self) -> bool:
        try:
            # Check if webapp is alive by hitting the context root or a health check
            response = requests.get(f"{self.base_url}/vaults", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def create_task(self, name: str, description: str = "", priority: str = "Medium", 
                    status: str = "TODO",
                    deadline: Optional[str] = None, scheduled: Optional[str] = None, 
                    tags: List[str] = [], vault_path: str = None) -> dict:
        """
        Sends a POST request to the Webapp to upsert a task.
        """
        if not vault_path:
            raise ValueError("vault_path is required for WebappTaskTarget")

        task_data = {
            "name": name,
            "description": description,
            "priority": priority,
            "status": status,
            "deadline": deadline,
            "scheduled": scheduled,
            "tags": tags
        }

        try:
            url = f"{self.base_url}/vaults/tasks?vault_path={requests.utils.quote(vault_path)}"
            response = requests.post(url, json=task_data, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to push task to webapp: {str(e)}")

    def fetch_tasks(self, vault_path: str = None) -> List[dict]:
        if not vault_path:
            raise ValueError("vault_path is required for WebappTaskTarget")
        try:
            url = f"{self.base_url}/vaults/tasks?vault_path={requests.utils.quote(vault_path)}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch tasks from webapp: {str(e)}")
