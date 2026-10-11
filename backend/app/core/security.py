import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings

password_hasher = PasswordHasher()
# Equalize the expensive verification work for unknown accounts.
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        valid = password_hasher.verify(password_hash or _dummy_hash, password)
        return valid and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def csrf_token(refresh_token: str, settings: Settings) -> str:
    return hmac.new(
        settings.jwt_secret_key.get_secret_value().encode(),
        ("csrf:" + token_hash(refresh_token)).encode(),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "type": "access",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["sub", "jti", "type", "iss", "aud", "iat", "nbf", "exp"]},
    )
    if claims["type"] != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    try:
        return uuid.UUID(claims["sub"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise jwt.InvalidTokenError("Invalid subject") from exc
