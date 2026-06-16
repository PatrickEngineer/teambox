from datetime import datetime
from sqlalchemy.orm import Session

from app.models.tasks import Task


def create_task(
    db: Session,
    title: str,
    description: str,
    project_id: int,
    user_id: int,
    priority: str = "medium",
):
    task = Task(
        title=title,
        description=description,
        project_id=project_id,
        creator_id=user_id,
        status="todo",
        priority=priority,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks_by_project(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    priority: str = None,
    sort_by: str = "created_at",
    order: str = "desc",
):
    query = db.query(Task).filter(
        Task.project_id == project_id,
        Task.deleted_at.is_(None),
    )

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    if order == "desc":
        query = query.order_by(getattr(Task, sort_by).desc())
    else:
        query = query.order_by(getattr(Task, sort_by).asc())

    return query.offset(skip).limit(limit).all()


def search_tasks_by_title(db: Session, project_id: int, search: str, skip: int = 0, limit: int = 100):
    return db.query(Task).filter(
        Task.project_id == project_id,
        Task.deleted_at.is_(None),
        Task.title.ilike(f"%{search}%"),
    ).offset(skip).limit(limit).all()


def get_task_by_id(db: Session, task_id: int):
    return db.query(Task).filter(
        Task.id == task_id,
        Task.deleted_at.is_(None),
    ).first()


def update_task(
    db: Session,
    task: Task,
    title: str,
    description: str,
    status: str,
    priority: str,
):
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if status is not None:
        task.status = status
    if priority is not None:
        task.priority = priority
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task):
    """Soft delete задачи"""
    task.deleted_at = datetime.utcnow()
    db.commit()