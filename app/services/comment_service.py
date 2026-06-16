from sqlalchemy.orm import Session
from app.models.comments import Comment
from app.models.tasks import Task
from app.models.users import User


def create_comment(
        db: Session,
        text: str,
        task_id: int,
        author_id: int,
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None

    comment = Comment(
        text=text,
        task_id=task_id,
        author_id=author_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments_by_task(db: Session, task_id: int, skip: int = 0, limit: int = 100):
    results = db.query(Comment, User.username).join(
        User, Comment.author_id == User.id
    ).filter(
        Comment.task_id == task_id
    ).order_by(Comment.created_at).offset(skip).limit(limit).all()

    comments = []
    for comment, username in results:
        comment_dict = {
            "id": comment.id,
            "text": comment.text,
            "task_id": comment.task_id,
            "author_id": comment.author_id,
            "author_username": username,
            "created_at": comment.created_at
        }
        comments.append(comment_dict)

    return comments


def get_comment_by_id(db: Session, comment_id: int):
    return db.query(Comment).filter(Comment.id == comment_id).first()


def update_comment(db: Session, comment: Comment, text: str):
    comment.text = text
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: Comment):
    db.delete(comment)
    db.commit()
    return True