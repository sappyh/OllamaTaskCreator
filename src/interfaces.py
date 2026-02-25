from abc import ABC, abstractmethod

class BaseNotesSource(ABC):
    """
    Abstract base class defining the contract for any source of notes (e.g., Obsidian, Notion, Local Files).
    """
    
    @abstractmethod
    def listAllFiles(self) -> list:
        """
        Returns a list of all relevant files/notes available in the source.
        """
        pass

    @abstractmethod
    def retrieveContentFromFile(self, file_identifier: str) -> str:
        """
        Retrieves the string content of a specific note given its identifier.
        """
        pass

class BaseTaskTarget(ABC):
    """
    Abstract base class defining the contract for any target task management system (e.g., Vikunja, Todoist, Jira).
    """
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Validates the connection to the underlying task management service.
        """
        pass

    @abstractmethod
    def create_task(self, project_id: int, title: str, description: str = "") -> dict:
        """
        Creates a core actionable task in the target location/project.
        """
        pass
