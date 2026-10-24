from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies.auth import require_roles
from app.models import Role, User

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/metrics")
def metrics(
    request: Request,
    response: Response,
    admin: Annotated[User, Depends(require_roles(Role.ADMIN))],
):
    """Protected process-local aggregates, never source or user labels."""
    response.headers["Cache-Control"] = "no-store"
    return request.app.state.metrics.snapshot()
