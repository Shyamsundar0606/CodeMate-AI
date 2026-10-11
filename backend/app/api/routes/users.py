from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies.auth import Database, require_roles
from app.models import Role, User
from app.schemas.user import UserPage
from app.services.user_service import list_users

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=UserPage)
def users(
    db: Database,
    response: Response,
    admin: Annotated[User, Depends(require_roles(Role.ADMIN))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserPage:
    response.headers["Cache-Control"] = "no-store"
    return list_users(db, offset, limit)
