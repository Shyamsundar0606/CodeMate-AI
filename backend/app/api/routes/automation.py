import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies.auth import (
    AuthenticatedUser,
    Database,
    refresh_credentials,
    require_auth_request,
)
from app.api.routes.github import repository_service
from app.automation.policy import EXECUTION_MESSAGE, VALIDATIONS
from app.automation.schemas import Create, Decision, Generate, SessionView
from app.services.auth_service import AuthService
from app.services.automation_service import AutomationService
from app.voice.errors import error

router = APIRouter(prefix="/api/v1/automation", tags=["developer automation previews"])
mutations = APIRouter(
    prefix="/api/v1/auth/automation",
    tags=["developer automation review"],
    dependencies=[Depends(require_auth_request)],
)


def service(request: Request, db: Database, user: AuthenticatedUser):
    return AutomationService(
        db,
        request.app.state.settings,
        user.id,
        request.app.state.engine,
        request.app.state.ollama_client,
        lambda: repository_service(request, db, user),
    )


Service = Annotated[AutomationService, Depends(service)]


def authorized(
    response: Response,
    service: Service,
    token: Annotated[str, Depends(refresh_credentials)],
    user: AuthenticatedUser,
):
    response.headers["Cache-Control"] = "no-store"
    _, owner = AuthService(service.db, service.settings).active_session(token)
    if owner.id != user.id:
        raise error("SESSION_CHANGED", "Active session does not match this account.", 403)
    return service


Mutation = Annotated[AutomationService, Depends(authorized)]


@router.get("/capabilities")
def capabilities(user: AuthenticatedUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"execution_enabled": False, "message": EXECUTION_MESSAGE, "validations": VALIDATIONS}


@router.get("/sessions")
def history(service: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.history()


@router.get("/sessions/{identity}", response_model=SessionView)
def detail(identity: uuid.UUID, service: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.get(identity)


@mutations.post("/sessions", response_model=SessionView, status_code=201)
def create(body: Create, service: Mutation):
    return service.create(body)


@mutations.post("/sessions/{identity}/proposals", response_model=SessionView)
def generate(identity: uuid.UUID, body: Generate, service: Mutation, request: Request):
    gate = request.app.state.automation_gate
    if not gate.acquire(blocking=False):
        raise error("BUSY", "A proposal is being generated. Try again shortly.", 429)
    try:
        return service.generate(identity, body)
    finally:
        gate.release()


@mutations.post("/sessions/{identity}/proposals/{proposal_id}/decision", response_model=SessionView)
def decision(identity: uuid.UUID, proposal_id: uuid.UUID, body: Decision, service: Mutation):
    return service.decide(identity, proposal_id, body)


@mutations.post("/sessions/{identity}/execute")
def execute(identity: uuid.UUID, service: Mutation):
    service.execution_disabled(identity)
