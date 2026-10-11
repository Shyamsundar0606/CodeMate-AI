from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "codemate-api"
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Process liveness only; does not imply database or AI readiness."""
    return HealthResponse()
