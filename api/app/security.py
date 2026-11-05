import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt

from app.config import Settings

ACCESS_TOKEN_TYPE = "access"


def generate_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(
    user_id: uuid.UUID, roles: list[str], now: datetime, settings: Settings
) -> str:
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, now: datetime, settings: Settings) -> dict[str, Any]:
    """Проверяет подпись и срок по часам приложения. Бросает jwt.InvalidTokenError."""
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        # Срок проверяем сами по часам приложения, чтобы тесты управляли временем
        options={
            "verify_exp": False,
            "verify_iat": False,
            "verify_nbf": False,
            "require": ["sub", "exp", "type"],
        },
    )
    if payload["type"] != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Неверный тип токена")
    if now.timestamp() >= payload["exp"]:
        raise jwt.ExpiredSignatureError("Токен истёк")
    return payload
