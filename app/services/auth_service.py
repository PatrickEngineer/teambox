from authlib.jose import jwt
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY
from app.models.users import User


def get_current_user_by_token(token: str, db: Session) -> User | None:
    try:
        print(f"[AUTH_DEBUG] Получен токен: {token[:50]}...")

        # 🔥 ИСПРАВЛЕНО: decoded — это объект, который ведёт себя как словарь
        decoded = jwt.decode(token, SECRET_KEY.encode('utf-8'))

        # Превращаем в словарь, если нужно
        claims = dict(decoded)
        email = claims.get("sub")

        print(f"[AUTH_DEBUG] Email из токена: {email}")

        if not email:
            return None

        user = db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None)
        ).first()

        print(f"[AUTH_DEBUG] Найден пользователь: {user.id if user else None}")
        return user

    except Exception as e:
        print(f"[AUTH_DEBUG] Ошибка: {type(e).__name__}: {e}")
        return None