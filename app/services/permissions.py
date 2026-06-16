from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.projects import Project
from app.models.project_members import ProjectMember
from app.models.users import User


def get_user_role(db: Session, project_id: int, user_id: int) -> str | None:
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    if user and user.role == "super_admin":
        return "super_admin"

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.deleted_at.is_(None)
    ).first()
    if not project:
        return None
    if project.owner_id == user_id:
        return "owner"
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    return member.role if member else None


# Функция (IDOR)
def require_project_role(
    db: Session,
    project_id: int,
    user_id: int,
    allowed_roles: list[str],
):
    role = get_user_role(db, project_id, user_id)

    if role == "super_admin":
        return role

    if role is None:
        raise HTTPException(status_code=403, detail="Not a project member")
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return role


def is_super_admin(user: User) -> bool:
    return user.role == "super_admin"


def is_owner(db: Session, project_id: int, user_id: int) -> bool:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.deleted_at.is_(None)
    ).first()
    return project and project.owner_id == user_id