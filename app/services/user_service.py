from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.users import User
from app.schemas.user import UserCreate, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    return pwd_context.verify(plain_password, hashed_password)


def create_user(db: Session, user: UserCreate, role: str = "user", is_verified: bool = False):
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role=role,
        is_verified=1 if is_verified else 0,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_super_admin(db: Session, username: str, email: str, password: str):
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        return None

    db_user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role="super_admin",
        is_verified=1,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).filter(
        User.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()


def delete_user_by_id(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        return False
    user.deleted_at = datetime.utcnow()
    db.commit()
    return True


def update_user_profile(db: Session, user: User, data: UserUpdate):
    """Обновление профиля пользователя"""
    if data.username is not None:
        existing = db.query(User).filter(
            User.username == data.username,
            User.id != user.id,
            User.deleted_at.is_(None),
        ).first()
        if existing:
            raise ValueError("Username already taken")
        user.username = data.username

    if data.email is not None:
        existing = db.query(User).filter(
            User.email == data.email,
            User.id != user.id,
            User.deleted_at.is_(None),
        ).first()
        if existing:
            raise ValueError("Email already taken")
        user.email = data.email

    db.commit()
    db.refresh(user)
    return user


def change_user_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
    """Смена пароля (требуется старый)"""
    if not verify_password(old_password, user.hashed_password):
        return False

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return True


def update_user_password_by_email(db: Session, email: str, new_password: str) -> bool:
    """Обновление пароля по email (для восстановления)"""
    user = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
    if not user:
        return False

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return True