from pydantic import BaseModel
from datetime import datetime


class FileOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    project_id: int
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True