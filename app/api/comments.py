from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.dependencies import get_current_user, get_db
from app.models.tasks import Task
from app.models.users import User
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.services.comment_service import (
    create_comment,
    get_comments_by_task,
    get_comment_by_id,
    update_comment,
    delete_comment,
)
from app.services.permissions import require_project_role

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.post("/task/{task_id}", response_model=CommentOut)
def create_comment_endpoint(
    task_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    require_project_role(db, task.project_id, current_user.id, ["owner", "admin", "member"])

    logger.info(f"User {current_user.id} commenting on task {task_id}")

    comment = create_comment(db, data.text, task_id, current_user.id)
    return comment


@router.get("/task/{task_id}", response_model=list[CommentOut])
def get_comments_endpoint(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    require_project_role(db, task.project_id, current_user.id, ["owner", "admin", "member"])

    return get_comments_by_task(db, task_id, skip, limit)


@router.put("/{comment_id}", response_model=CommentOut)
def update_comment_endpoint(
    comment_id: int,
    data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your comment")

    logger.info(f"User {current_user.id} updating comment {comment_id}")
    return update_comment(db, comment, data.text)


@router.delete("/{comment_id}")
def delete_comment_endpoint(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    task = db.query(Task).filter(Task.id == comment.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if comment.author_id != current_user.id:
        require_project_role(db, task.project_id, current_user.id, ["owner", "admin"])

    logger.info(f"User {current_user.id} deleting comment {comment_id}")
    delete_comment(db, comment)
    return {"message": "Comment deleted"}