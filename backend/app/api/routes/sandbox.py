import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.dependencies.auth import AuthenticatedUser, require_auth_request
from app.api.routes.automation import Mutation, Service
from app.sandbox.policy import capabilities
from app.sandbox.schemas import Capabilities, Confirm, ExecutionView, Prepare
from app.services.sandbox_service import SandboxService

router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox preparation"])
mutations = APIRouter(
    prefix="/api/v1/auth/sandbox",
    tags=["sandbox preparation"],
    dependencies=[Depends(require_auth_request)],
)


def read_service(automation: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return SandboxService(automation)


def write_service(automation: Mutation):
    return SandboxService(automation)


Read = Annotated[SandboxService, Depends(read_service)]
Write = Annotated[SandboxService, Depends(write_service)]


@router.get("/capabilities", response_model=Capabilities)
def status(user: AuthenticatedUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return capabilities()


@router.get("/executions", response_model=list[ExecutionView])
def history(service: Read):
    return service.history()


@router.get("/executions/{identity}", response_model=ExecutionView)
def detail(identity: uuid.UUID, service: Read):
    return service.get(identity)


@mutations.post("/executions", status_code=201, response_model=ExecutionView)
def prepare(body: Prepare, service: Write):
    return service.prepare(body)


@mutations.post("/executions/{identity}/confirm")
def confirm(identity: uuid.UUID, body: Confirm, service: Write):
    return service.confirm(identity, body)


@mutations.post("/executions/{identity}/cancel", response_model=ExecutionView)
def cancel(identity: uuid.UUID, service: Write):
    return service.cancel(identity)
