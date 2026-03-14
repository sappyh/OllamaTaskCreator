import requests
from orchestrator.src.interfaces import BaseNotesSource

class WebappNotesSource(BaseNotesSource):
    def __init__(self, base_url: str, vault_path: str):
        self.base_url = base_url.rstrip('/')
        self.vault_path = vault_path
        
        # Ensure vault exists
        response = requests.post(f"{self.base_url}/vault", json={"vault_path": self.vault_path})
        if response.status_code != 200:
            raise RuntimeError(f"Failed to initialize vault: {response.text}")
            
    def listAllFiles(self) -> list:
        response = requests.get(f"{self.base_url}/notes", params={"vault_path": self.vault_path})
        if response.status_code == 200:
            return response.json()
        return []

    def retrieveContentFromFile(self, file_identifier: str) -> str:
        response = requests.get(f"{self.base_url}/notes/{file_identifier}", params={"vault_path": self.vault_path})
        if response.status_code == 200:
            return response.json().get("content", "")
        else:
            return NameError
