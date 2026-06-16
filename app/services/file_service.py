import os
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.files import File

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx'}


def save_file(db: Session, file: UploadFile, project_id: int, user_id: int):
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    unique_filename = f"{uuid.uuid4().hex}{file_extension}"

    project_dir = UPLOAD_DIR / f"project_{project_id}"
    project_dir.mkdir(exist_ok=True)

    file_path = project_dir / unique_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = file_path.stat().st_size

    db_file = File(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        project_id=project_id,
        uploaded_by=user_id,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file


def get_files_by_project(db: Session, project_id: int, skip: int = 0, limit: int = 100):
    return db.query(File).filter(
        File.project_id == project_id
    ).offset(skip).limit(limit).all()


def get_file_by_id(db: Session, file_id: int):
    return db.query(File).filter(File.id == file_id).first()


def delete_file(db: Session, file: File):
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    db.delete(file)
    db.commit()
    return True


def get_file_path(file: File) -> str:
    return file.file_path