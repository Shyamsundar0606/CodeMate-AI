import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.ai.errors import AIError
from app.ai.schemas import AIStatus, History, InvestigationRequest, InvestigationResponse, ModelInfo
from app.api.dependencies.auth import (
    AuthenticatedUser,
    Database,
    refresh_credentials,
    require_auth_request,
)
from app.api.routes.github import repository_service
from app.services.ai_investigation_service import InvestigationService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/ai", tags=["local AI diagnostics"])
mutations = APIRouter(
    prefix="/api/v1/auth/ai",
    tags=["local AI diagnostics mutations"],
    dependencies=[Depends(require_auth_request)],
)


def service(request: Request, db: Database, user: AuthenticatedUser):
    return InvestigationService(db, request.app.state.settings, user.id)


Service = Annotated[InvestigationService, Depends(service)]


def mutation_service(
    request: Request,
    db: Database,
    user: AuthenticatedUser,
    token: Annotated[str, Depends(refresh_credentials)],
):
    _, owner = AuthService(db, request.app.state.settings).active_session(token)
    if owner.id != user.id:
        raise AIError("AI_SESSION_CHANGED", "The active session does not match this account.", 403)
    return InvestigationService(db, request.app.state.settings, user.id)


Mutation = Annotated[InvestigationService, Depends(mutation_service)]


@router.get("/status", response_model=AIStatus)
def status(request: Request, user: AuthenticatedUser):
    return request.app.state.ollama_client.status()


@router.get("/models", response_model=list[ModelInfo])
def models(request: Request, user: AuthenticatedUser):
    return request.app.state.ollama_client.models()


@router.get("/investigations", response_model=History)
def history(
    service: Service,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 10,
):
    return service.history(page, per_page)


@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
def report(investigation_id: uuid.UUID, service: Service):
    return service.response(service.owned(investigation_id))


@router.post(
    "/investigations",
    response_model=InvestigationResponse,
    status_code=202,
    dependencies=[Depends(require_auth_request)],
)
@mutations.post("/investigations", response_model=InvestigationResponse, status_code=202)
def create(
    body: InvestigationRequest,
    request: Request,
    db: Database,
    user: AuthenticatedUser,
    service: Mutation,
):
    service.github = repository_service(request, db, user)
    return service.create(body)


@router.post(
    "/investigations/{investigation_id}/retry",
    response_model=InvestigationResponse,
    dependencies=[Depends(require_auth_request)],
)
@mutations.post("/investigations/{investigation_id}/retry", response_model=InvestigationResponse)
def retry(
    investigation_id: uuid.UUID,
    request: Request,
    db: Database,
    user: AuthenticatedUser,
    service: Mutation,
):
    service.github = repository_service(request, db, user)
    return service.retry(investigation_id)


@router.post(
    "/investigations/{investigation_id}/cancel",
    response_model=InvestigationResponse,
    dependencies=[Depends(require_auth_request)],
)
@mutations.post("/investigations/{investigation_id}/cancel", response_model=InvestigationResponse)
def cancel(investigation_id: uuid.UUID, service: Mutation):
    return service.cancel(investigation_id)


@router.post(
    "/investigations/{investigation_id}/delete", dependencies=[Depends(require_auth_request)]
)
@mutations.post("/investigations/{investigation_id}/delete")
def remove(investigation_id: uuid.UUID, service: Mutation):
    return service.remove(investigation_id)
