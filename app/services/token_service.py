from sqlalchemy.orm import Session
from datetime import datetime
from app.models.refresh_token import RefreshToken
from app.core.security import decode_token, create_access_token


def save_refresh_token(db: Session, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
        is_revoked=0
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_refresh_token(db: Session, token: str) -> RefreshToken | None:
    return db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.is_revoked == 0
    ).first()


def revoke_refresh_token(db: Session, token: str) -> bool:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if not db_token:
        return False
    db_token.is_revoked = 1
    db.commit()
    return True


def revoke_all_user_tokens(db: Session, user_id: int) -> int:
    """Отзывает все refresh токены пользователя (при смене пароля)"""
    result = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == 0
    ).update({"is_revoked": 1})
    db.commit()
    return result


def refresh_access_token(db: Session, refresh_token: str) -> str | None:
    payload = decode_token(refresh_token)
    if not payload:
        return None

    if payload.get("type") != "refresh":
        return None

    db_token = get_refresh_token(db, refresh_token)
    if not db_token:
        return None

    if db_token.expires_at < datetime.utcnow():
        return None

    user_email = payload.get("sub")
    if not user_email:
        return None

    return create_access_token({"sub": user_email})