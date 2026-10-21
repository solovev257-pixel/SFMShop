from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from src.core.config import settings


def hash_password(password: str) -> str:
    """bcrypt-хэш пароля; bcrypt учитывает только первые 72 байта"""
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode()[:72], password_hash.encode())


def create_access_token(user_id: int) -> str:
    """Подписанный токен: sub - id пользователя, exp - срок действия"""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Проверить подпись и срок; вернуть id пользователя или None"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None