from pydantic import BaseModel
from datetime import datetime


class CommentCreate(BaseModel):
    text: str


class CommentUpdate(BaseModel):
    text: str


class CommentOut(BaseModel):
    id: int
    text: str
    task_id: int
    author_id: int
    author_username: str
    created_at: datetime

    class Config:
        from_attributes = True