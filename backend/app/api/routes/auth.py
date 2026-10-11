from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies.auth import (
    COOKIE_PATH,
    REFRESH_COOKIE,
    AuthenticatedUser,
    Database,
    refresh_cookie,
    refresh_credentials,
    require_auth_request,
)
from app.core.security import create_access_token, csrf_token
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def deliver_tokens(user: User, token: str, request: Request, response: Response) -> TokenResponse:
    settings = request.app.state.settings
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=create_access_token(user.id, settings),
        expires_in=settings.access_token_expire_minutes * 60,
        csrf_token=csrf_token(token, settings),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(require_auth_request)],
)
def register(data: RegisterRequest, request: Request, db: Database) -> User:
    return AuthService(db, request.app.state.settings).register(data)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(require_auth_request)])
def login(data: LoginRequest, request: Request, response: Response, db: Database) -> TokenResponse:
    user, token = AuthService(db, request.app.state.settings).login(
        str(data.email),
        data.password.get_secret_value(),
        request.client.host if request.client else "unknown",
    )
    return deliver_tokens(user, token, request, response)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(require_auth_request)])
def refresh(
    request: Request,
    response: Response,
    db: Database,
    token: Annotated[str, Depends(refresh_credentials)],
) -> TokenResponse:
    user, replacement = AuthService(db, request.app.state.settings).rotate(token)
    return deliver_tokens(user, replacement, request, response)


@router.post("/logout", status_code=204, dependencies=[Depends(require_auth_request)])
def logout(
    request: Request, db: Database, token: Annotated[str, Depends(refresh_credentials)]
) -> Response:
    AuthService(db, request.app.state.settings).logout(token)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        REFRESH_COOKIE,
        path=COOKIE_PATH,
        httponly=True,
        secure=request.app.state.settings.cookie_secure,
        samesite="strict",
    )
    return response


@router.get("/me", response_model=UserResponse)
def me(user: AuthenticatedUser, response: Response) -> User:
    response.headers["Cache-Control"] = "no-store"
    return user


@router.get("/csrf", dependencies=[Depends(require_auth_request)])
def csrf_bootstrap(
    request: Request,
    response: Response,
    db: Database,
    token: Annotated[str, Depends(refresh_cookie)],
) -> dict[str, str]:
    """Recover CSRF state after reload without exposing the HttpOnly refresh token."""
    AuthService(db, request.app.state.settings).active_session(token)
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": csrf_token(token, request.app.state.settings)}
