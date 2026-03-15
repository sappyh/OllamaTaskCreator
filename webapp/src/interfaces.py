from abc import ABC, abstractmethod
from typing import List, Optional
try:
    from common.src.models import Task
except ImportError:
    pass

class BaseVaultManager(ABC):
    """
    Abstract base class defining the contract for managing a vault and its notes.
    """
    
    @abstractmethod
    def create_vault(self, vault_path: str) -> dict:
        pass

    @abstractmethod
    def list_vaults(self) -> list:
        pass

    @abstractmethod
    def list_notes(self, vault_path: str) -> list:
        pass

    @abstractmethod
    def create_note(self, vault_path: str, filename: str, content: str) -> dict:
        pass

    @abstractmethod
    def retrieve_note(self, vault_path: str, filename: str) -> dict:
        pass

    @abstractmethod
    def update_note(self, vault_path: str, filename: str, content: str) -> dict:
        pass

    @abstractmethod
    def delete_note(self, vault_path: str, filename: str) -> dict:
        pass

    @abstractmethod
    def delete_vault(self, vault_path: str) -> dict:
        """Removes a vault (directory and tracking)."""
        pass

    @abstractmethod
    def get_tasks(self, vault_path: str) -> List[dict]:
        """Returns all tasks stored in the vault."""
        pass

    @abstractmethod
    def upsert_task(self, vault_path: str, task_data: dict) -> dict:
        """Creates or updates a task in the vault."""
        pass

    @abstractmethod
    def delete_task(self, vault_path: str, task_id: str) -> dict:
        """Removes a task from the vault."""
        pass
