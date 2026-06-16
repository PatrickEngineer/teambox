from authlib.jose import jwt
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from passlib.context import CryptContext
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

serializer = URLSafeTimedSerializer(SECRET_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "access"})
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    header = {"alg": ALGORITHM}
    return jwt.encode(header, to_encode, SECRET_KEY.encode('utf-8')).decode('utf-8')


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "refresh"})
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": int(expire.timestamp())})
    header = {"alg": ALGORITHM}
    return jwt.encode(header, to_encode, SECRET_KEY.encode('utf-8')).decode('utf-8')


def decode_token(token: str) -> dict | None:
    try:
        decoded = jwt.decode(token, SECRET_KEY.encode('utf-8'))
        exp = decoded.claims.get("exp")
        now = int(datetime.utcnow().timestamp())
        if exp and exp < now:
            return None
        return decoded.claims
    except Exception:
        return None


def is_token_valid(token: str, token_type: str = None) -> bool:
    payload = decode_token(token)
    if not payload:
        return False
    if token_type and payload.get("type") != token_type:
        return False
    return True


def generate_email_verification_token(email: str) -> str:
    return serializer.dumps(email, salt="email-verification")


def verify_email_token(token: str, expiration: int = 3600) -> str | None:
    try:
        email = serializer.loads(token, salt="email-verification", max_age=expiration)
        return email
    except Exception:
        return None


def generate_password_reset_token(email: str) -> str:
    return serializer.dumps(email, salt="password-reset")


def verify_password_reset_token(token: str, expiration: int = 3600) -> str | None:
    try:
        email = serializer.loads(token, salt="password-reset", max_age=expiration)
        return email
    except Exception:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_email_token(token: str, expiration: int = 3600) -> str | None:
    try:
        email = serializer.loads(token, salt="email-verification", max_age=expiration)
        return email
    except Exception:
        return None


def generate_password_reset_token(email: str) -> str:
    """Генерирует токен для восстановления пароля (действует 1 час)"""
    return serializer.dumps(email, salt="password-reset")


def verify_password_reset_token(token: str, expiration: int = 3600) -> str | None:
    """Проверяет токен восстановления пароля"""
    try:
        email = serializer.loads(token, salt="password-reset", max_age=expiration)
        return email
    except Exception:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль (используется в user_service)"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хэширует пароль"""
    return pwd_context.hash(password)