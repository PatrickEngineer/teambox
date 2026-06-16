from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.dependencies import get_current_user, get_db
from app.models.users import User
from app.schemas.file import FileOut
from app.services.file_service import (
    save_file,
    get_files_by_project,
    get_file_by_id,
    delete_file,
    get_file_path,
)
from app.services.permissions import require_project_role

router = APIRouter(prefix="/files", tags=["Files"])

MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/project/{project_id}", response_model=FileOut)
async def upload_file_endpoint(
    project_id: int,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(db, project_id, current_user.id, ["owner", "admin"])

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        logger.warning(
            f"User {current_user.id} attempted to upload file larger than 10MB to project {project_id}"
        )
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    logger.info(f"User {current_user.id} uploading file {file.filename} to project {project_id}")
    result = save_file(db, file, project_id, current_user.id)
    logger.info(f"File uploaded: id={result.id}, filename={result.original_filename}, project={project_id}")
    return result


@router.get("/project/{project_id}", response_model=list[FileOut])
def get_files_endpoint(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(db, project_id, current_user.id, ["owner", "admin", "member"])
    return get_files_by_project(db, project_id, skip, limit)


@router.get("/download/{file_id}")
def download_file_endpoint(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_db = get_file_by_id(db, file_id)
    if not file_db:
        logger.warning(f"User {current_user.id} attempted to download non-existent file {file_id}")
        raise HTTPException(status_code=404, detail="File not found")

    require_project_role(db, file_db.project_id, current_user.id, ["owner", "admin", "member"])

    logger.info(f"User {current_user.id} downloading file {file_db.id} - {file_db.original_filename}")
    file_path = get_file_path(file_db)
    return FileResponse(
        path=file_path,
        filename=file_db.original_filename,
        media_type=file_db.mime_type,
    )


@router.delete("/{file_id}")
def delete_file_endpoint(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_db = get_file_by_id(db, file_id)
    if not file_db:
        logger.warning(f"User {current_user.id} attempted to delete non-existent file {file_id}")
        raise HTTPException(status_code=404, detail="File not found")

    require_project_role(db, file_db.project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} deleting file {file_db.id} - {file_db.original_filename}")
    delete_file(db, file_db)
    return {"message": "File deleted"}