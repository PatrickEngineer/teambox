from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.dependencies import get_current_user, get_db
from app.models.users import User
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate, TaskStatus, TaskPriority
from app.services.permissions import require_project_role
from app.services.task_service import (
    create_task,
    get_tasks_by_project,
    get_task_by_id,
    update_task,
    delete_task,
    search_tasks_by_title,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/project/{project_id}", response_model=TaskOut)
def create_task_endpoint(
    project_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(db, project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} creating task in project {project_id}: {data.title}")

    result = create_task(
        db,
        data.title,
        data.description,
        project_id,
        current_user.id,
        data.priority.value if data.priority else "medium",
    )

    logger.info(f"Task created: id={result.id}, title={result.title}, project={project_id}")
    return result


@router.get("/project/{project_id}", response_model=list[TaskOut])
def get_tasks_endpoint(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    search: str | None = Query(None, description="Поиск по названию задачи"),
    status: TaskStatus | None = Query(None, description="Фильтр по статусу"),
    priority: TaskPriority | None = Query(None, description="Фильтр по приоритету"),
    sort_by: str = Query("created_at", description="sort_by: created_at, title, status, priority"),
    order: str = Query("desc", description="asc или desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(db, project_id, current_user.id, ["owner", "admin", "member"])

    if search:
        return search_tasks_by_title(db, project_id, search, skip, limit)

    return get_tasks_by_project(
        db, project_id, skip, limit,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{task_id}", response_model=TaskOut)
def get_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_by_id(db, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found")
    require_project_role(db, task.project_id, current_user.id, ["owner", "admin", "member"])
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task_endpoint(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_by_id(db, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found")
    require_project_role(db, task.project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} updating task {task_id}")

    return update_task(
        db, task,
        data.title,
        data.description,
        data.status.value if data.status else None,
        data.priority.value if data.priority else None,
    )


@router.delete("/{task_id}")
def delete_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_by_id(db, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found")
    require_project_role(db, task.project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} deleting task {task_id}")
    delete_task(db, task)
    return {"message": "Task deleted"}