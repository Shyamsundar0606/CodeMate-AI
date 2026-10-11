import secrets
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import unauthorized
from app.core.security import csrf_token, decode_access_token
from app.db.session import get_db
from app.models import Role, User

bearer = HTTPBearer(auto_error=False)
REFRESH_COOKIE = "codemate_refresh"
COOKIE_PATH = "/api/v1/auth"
Database = Annotated[Session, Depends(get_db)]


def current_user(
    request: Request,
    db: Database,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials, request.app.state.settings)
    except jwt.InvalidTokenError as exc:
        raise unauthorized() from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized()
    return user


AuthenticatedUser = Annotated[User, Depends(current_user)]


def require_roles(*roles: Role) -> Callable[..., User]:
    def authorize(user: AuthenticatedUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return authorize


def require_auth_request(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = request.app.state.settings.cors_origins
    if origin is not None and origin not in allowed:
        raise HTTPException(403, "Untrusted request origin")
    # Custom header blocks browser form submissions even without an Origin header.
    if request.headers.get("x-codemate-request") != "1":
        raise HTTPException(403, "X-CodeMate-Request header required")


def refresh_cookie(request: Request) -> str:
    token = request.cookies.get(REFRESH_COOKIE)
    if token is None or len(token) != 64:
        raise unauthorized()
    return token


def refresh_credentials(request: Request) -> str:
    token = refresh_cookie(request)
    provided = request.headers.get("x-csrf-token", "")
    expected = csrf_token(token, request.app.state.settings)
    if (
        len(provided) != 64
        or any(c not in "0123456789abcdef" for c in provided)
        or not secrets.compare_digest(provided, expected)
    ):
        raise HTTPException(403, "Invalid CSRF token")
    return token
