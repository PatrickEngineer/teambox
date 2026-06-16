from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.users import User
from app.services.auth_service import get_current_user_by_token

security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    user = get_current_user_by_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    if user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Account deleted")
    if not user.is_verified:
        raise HTTPException(status_code=401, detail="Email not verified")
    return user