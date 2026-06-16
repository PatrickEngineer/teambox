from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.projects import Project
from app.models.project_members import ProjectMember
from app.models.users import User


def create_project(db: Session, data, user_id: int):
    """Создаёт проект и добавляет создателя как owner (одна транзакция)"""
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=user_id,
    )
    db.add(project)

    member = ProjectMember(
        user_id=user_id,
        project_id=project.id,
        role="owner",
    )
    db.add(member)

    db.commit()
    db.refresh(project)
    return project


def get_user_projects(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    member_projects = db.query(ProjectMember.project_id).filter(
        ProjectMember.user_id == user_id
    )
    return db.query(Project).filter(
        or_(
            Project.owner_id == user_id,
            Project.id.in_(member_projects),
        ),
        Project.deleted_at.is_(None),
    ).offset(skip).limit(limit).all()


def get_all_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Project).filter(
        Project.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()


def search_projects_by_name(db: Session, search: str, skip: int = 0, limit: int = 100, user_id: int = None):
    query = db.query(Project).filter(
        Project.deleted_at.is_(None),
        Project.name.ilike(f"%{search}%"),
    )

    if user_id is not None:
        member_projects = db.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == user_id
        )
        query = query.filter(
            or_(
                Project.owner_id == user_id,
                Project.id.in_(member_projects),
            )
        )

    return query.offset(skip).limit(limit).all()


def get_project_by_id(db: Session, project_id: int):
    return db.query(Project).filter(
        Project.id == project_id,
        Project.deleted_at.is_(None),
    ).first()


def update_project(db: Session, project: Project, name: str, description: str):
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project):
    """Soft delete проекта"""
    project.deleted_at = datetime.utcnow()
    db.commit()


def get_project_members(db: Session, project_id: int):
    return db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id
    ).all()


def add_member_to_project(db: Session, project_id: int, user_id: int):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        return {"error": "User not found"}

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if existing:
        return {"message": "User already in project"}

    member = ProjectMember(
        user_id=user_id,
        project_id=project_id,
        role="member",
    )
    db.add(member)
    db.commit()
    return {"message": "User added"}


def remove_project_member_service(db: Session, project_id: int, user_id: int) -> bool:
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True


def update_member_role_service(db: Session, project_id: int, user_id: int, new_role: str) -> bool:
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not member:
        return False

    if member.role == "owner":
        return False

    member.role = new_role
    db.commit()
    return True