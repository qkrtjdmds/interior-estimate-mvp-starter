from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()

COMMON_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "admin12345",
    "admin123456",
    "qwerty12345",
    "test123456",
    "interior123",
}


class TokenError(Exception):
    pass


class ExpiredTokenError(TokenError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password_policy(password: str) -> None:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    if not any(char.isalpha() for char in password):
        raise ValueError("Password must include a letter")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must include a number")
    if password.strip().lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_hasher.verify(plain_password, password_hash)


def create_access_token(subject: int | str) -> tuple[str, int]:
    secret = settings.get_jwt_secret_key()
    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": expires_at,
    }
    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.get_jwt_secret_key(), algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token expired") from exc
    except InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    if payload.get("type") != "access":
        raise TokenError("Invalid token type")
    if not payload.get("sub"):
        raise TokenError("Invalid token subject")
    return payload
