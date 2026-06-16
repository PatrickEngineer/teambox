from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import RATE_LIMIT_PER_MINUTE
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.dependencies import get_current_user, get_db
from app.models.users import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.permissions import require_project_role, is_super_admin
from app.services.project_service import (
    create_project,
    get_user_projects,
    get_all_projects,
    get_project_by_id,
    update_project,
    delete_project,
    get_project_members,
    add_member_to_project,
    remove_project_member_service,
    update_member_role_service,
    search_projects_by_name,
)

router = APIRouter(prefix="/projects", tags=["Projects"])
limiter = Limiter(key_func=get_remote_address)

# Уязвимый фрагмент кода (Dos)
# @router.post("", response_model=ProjectOut)
# def create_project_endpoint(
#     data: ProjectCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     logger.info(f"User {current_user.id} creating project: {data.name}")
#     result = create_project(db, data, current_user.id)
#     logger.info(f"Project created: id={result.id}, name={result.name}, owner={current_user.id}")
#     return result


# Безопасный фрагмент кода (Dos)
@router.post("", response_model=ProjectOut)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def create_project_endpoint(
    request: Request,
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"User {current_user.id} creating project: {data.name}")
    result = create_project(db, data, current_user.id)
    logger.info(f"Project created: id={result.id}, name={result.name}, owner={current_user.id}")
    return result


@router.get("", response_model=list[ProjectOut])
def get_projects_endpoint(
    skip: int = 0,
    limit: int = 100,
    search: str | None = Query(None, description="Поиск по названию проекта"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.debug(f"User {current_user.id} fetching projects (skip={skip}, limit={limit}, search={search})")

    if is_super_admin(current_user):
        if search:
            return search_projects_by_name(db, search, skip, limit)
        return get_all_projects(db, skip, limit)

    if search:
        return search_projects_by_name(db, search, skip, limit, user_id=current_user.id)

    return get_user_projects(db, current_user.id, skip, limit)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner", "admin", "member"])

    project = get_project_by_id(db, project_id)
    if not project or project.deleted_at is not None:
        logger.warning(f"Project {project_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project_endpoint(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner", "admin"])

    project = get_project_by_id(db, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"User {current_user.id} updating project {project_id}")
    return update_project(db, project, data.name, data.description)


@router.delete("/{project_id}")
def delete_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner"])

    project = get_project_by_id(db, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"User {current_user.id} deleting project {project_id}")
    delete_project(db, project)
    return {"message": "Project deleted"}


@router.get("/{project_id}/members")
def get_members_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner", "admin", "member"])

    return get_project_members(db, project_id)


@router.post("/{project_id}/members")
def add_member_endpoint(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} adding user {user_id} to project {project_id}")
    return add_member_to_project(db, project_id, user_id)


@router.delete("/{project_id}/members/{user_id}")
def remove_member_endpoint(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} removing user {user_id} from project {project_id}")
    success = remove_project_member_service(db, project_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member removed"}


@router.put("/{project_id}/members/{user_id}/role")
def update_member_role_endpoint(
    project_id: int,
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        require_project_role(db, project_id, current_user.id, ["owner"])

    if role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Invalid role. Allowed: admin, member")

    logger.info(f"User {current_user.id} changing role of user {user_id} to {role} in project {project_id}")
    success = update_member_role_service(db, project_id, user_id, role)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")

    return {"message": f"User {user_id} role updated to {role}"}