from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.medium


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    priority: str
    project_id: int
    creator_id: int
    created_at: datetime

    class Config:
        from_attributes = True