from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import uuid

class TaskPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class TaskStatus(Enum):
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"

@dataclass
class Task:
    name: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    deadline: Optional[str] = None
    scheduled: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "deadline": self.deadline,
            "scheduled": self.scheduled,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict):
        # Handle priority conversion from string
        priority_val = data.get("priority", "Medium")
        try:
            priority = TaskPriority(priority_val)
        except ValueError:
            priority = TaskPriority.MEDIUM
            
        # Handle status conversion from string
        status_val = data.get("status", "TODO")
        try:
            status = TaskStatus(status_val)
        except ValueError:
            status = TaskStatus.TODO
            
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "New Task"),
            description=data.get("description", ""),
            priority=priority,
            status=status,
            deadline=data.get("deadline"),
            scheduled=data.get("scheduled"),
            tags=data.get("tags", [])
        )
