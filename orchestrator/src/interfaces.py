from abc import ABC, abstractmethod
from typing import List, Optional
try:
    from common.src.models import Task
except ImportError:
    # Handle cases where common is not in path yet
    pass

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
    def create_task(self, name: str, description: str = "", priority: str = "Medium", 
                    status: str = "TODO",
                    deadline: Optional[str] = None, scheduled: Optional[str] = None, 
                    tags: List[str] = []) -> dict:
        """
        Creates a core actionable task in the target location/project.
        """
        pass

    @abstractmethod
    def fetch_tasks(self, **kwargs) -> List[dict]:
        """
        Fetches all currently existing tasks from the target system.
        """
        pass


