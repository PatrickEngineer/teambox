from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"