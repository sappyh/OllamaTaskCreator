from abc import ABC, abstractmethod

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
