from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import REFRESH_TOKEN_EXPIRE_DAYS, RATE_LIMIT_PER_MINUTE
from app.core.logging_config import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_email_verification_token,
    generate_password_reset_token,
    verify_email_token,
    verify_password_reset_token,
)
from app.dependencies import get_current_user, get_db
from app.models.users import User
from app.schemas.token import TokenResponse, RefreshTokenRequest, LogoutRequest
from app.schemas.user import (
    UserCreate,
    UserOut,
    UserLogin,
    UserUpdate,
    UserChangePassword,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.email_service import send_verification_email, send_password_reset_email
from app.services.permissions import is_super_admin
from app.services.token_service import (
    save_refresh_token,
    revoke_refresh_token,
    refresh_access_token,
)
from app.services.user_service import (
    create_user,
    verify_password,
    get_all_users,
    delete_user_by_id,
    update_user_profile,
    change_user_password,
    update_user_password_by_email,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserOut)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for email: {user.email}")

    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing_user:
        logger.warning(f"Registration failed - user already exists: {user.email}")
        raise HTTPException(status_code=400, detail="User already exists")

    db_user = create_user(db, user, is_verified=False)
    logger.info(f"User created successfully: {db_user.id} - {db_user.email}")

    token = generate_email_verification_token(user.email)
    send_verification_email(user.email, token)

    return db_user


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    email = verify_email_token(token)
    if not email:
        logger.warning("Email verification failed - invalid token")
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"Email verification failed - user not found: {email}")
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = 1
    db.commit()
    logger.info(f"Email verified successfully: {email}")

    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for email: {user.email}")

    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        logger.warning(f"Login failed - user not found: {user.email}")
        raise HTTPException(status_code=400, detail="User not found")

    if db_user.deleted_at is not None:
        logger.warning(f"Login failed - account deleted: {user.email}")
        raise HTTPException(status_code=400, detail="Account deleted")

    if not db_user.is_verified:
        logger.warning(f"Login failed - email not verified: {user.email}")
        raise HTTPException(status_code=400, detail="Email not verified")

    if not verify_password(user.password, db_user.hashed_password):
        logger.warning(f"Login failed - wrong password: {user.email}")
        raise HTTPException(status_code=400, detail="Wrong password")

    access_token = create_access_token({"sub": db_user.email})
    refresh_token = create_refresh_token({"sub": db_user.email})

    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, db_user.id, refresh_token, expires_at)

    logger.info(f"User logged in successfully: {db_user.id} - {db_user.email}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    logger.info("Refresh token attempt")

    new_access_token = refresh_access_token(db, request.refresh_token)
    if not new_access_token:
        logger.warning("Refresh token failed - invalid or expired")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(request.refresh_token)
    if not payload:
        logger.warning("Refresh token failed - invalid payload")
        raise HTTPException(status_code=401, detail="Invalid token")

    user_email = payload.get("sub")
    if not user_email:
        logger.warning("Refresh token failed - no email in payload")
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        logger.warning(f"Refresh token failed - user not found: {user_email}")
        raise HTTPException(status_code=401, detail="User not found")

    revoke_refresh_token(db, request.refresh_token)

    new_access_token = create_access_token({"sub": user_email})
    new_refresh_token = create_refresh_token({"sub": user_email})

    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, user.id, new_refresh_token, expires_at)

    logger.info(f"Refresh token successful for user: {user.id}")

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Logout attempt for user: {current_user.id}")

    payload = decode_token(request.refresh_token)
    if not payload:
        logger.warning(f"Logout failed - invalid token for user: {current_user.id}")
        raise HTTPException(status_code=401, detail="Invalid token")

    user_email = payload.get("sub")
    if user_email != current_user.email:
        logger.warning("Logout failed - token belongs to different user")
        raise HTTPException(status_code=403, detail="Token does not belong to you")

    success = revoke_refresh_token(db, request.refresh_token)
    if not success:
        logger.warning(f"Logout failed - refresh token not found for user: {current_user.id}")
        raise HTTPException(status_code=404, detail="Refresh token not found")

    logger.info(f"User logged out successfully: {current_user.id}")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    logger.debug(f"User profile accessed: {current_user.id}")
    return current_user


@router.put("/me", response_model=UserOut)
def update_profile(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Profile update attempt for user: {current_user.id}")
    result = update_user_profile(db, current_user, data)
    logger.info(f"Profile updated successfully for user: {current_user.id}")
    return result


@router.put("/me/password")
def change_password(
    data: UserChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Password change attempt for user: {current_user.id}")

    success = change_user_password(db, current_user, data.old_password, data.new_password)
    if not success:
        logger.warning(f"Password change failed - wrong old password for user: {current_user.id}")
        raise HTTPException(status_code=400, detail="Wrong old password")

    from app.services.token_service import revoke_all_user_tokens
    revoke_all_user_tokens(db, current_user.id)

    logger.info(f"Password changed successfully for user: {current_user.id}")
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    logger.info(f"Password reset request for email: {data.email}")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        logger.warning(f"Password reset request - email not found: {data.email}")
        return {"message": "If your email is registered, you will receive a reset link"}

    token = generate_password_reset_token(user.email)
    send_password_reset_email(user.email, token)

    logger.info(f"Password reset email sent to: {data.email}")
    return {"message": "If your email is registered, you will receive a reset link"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    logger.info("Password reset attempt")

    email = verify_password_reset_token(data.token)
    if not email:
        logger.warning("Password reset failed - invalid token")
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"Password reset failed - user not found: {email}")
        raise HTTPException(status_code=404, detail="User not found")

    update_user_password_by_email(db, email, data.new_password)

    logger.info(f"Password reset successful for user: {user.id} - {email}")
    return {"message": "Password reset successfully"}


@router.get("/users", response_model=list[UserOut])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        logger.warning(f"Unauthorized attempt to get users by user: {current_user.id}")
        raise HTTPException(status_code=403, detail="Super admin access required")

    logger.info(f"Users list accessed by super_admin: {current_user.id}")
    return get_all_users(db, skip, limit)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_super_admin(current_user):
        logger.warning(f"Unauthorized attempt to delete user by: {current_user.id}")
        raise HTTPException(status_code=403, detail="Super admin access required")

    if user_id == current_user.id:
        logger.warning(f"Super_admin attempted to delete themselves: {current_user.id}")
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    success = delete_user_by_id(db, user_id)
    if not success:
        logger.warning(f"Delete user failed - user not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User deleted by super_admin {current_user.id}: user_id={user_id}")
    return {"message": f"User {user_id} deleted"}