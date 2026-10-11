from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.api.dependencies.auth import (
    AuthenticatedUser,
    Database,
    refresh_credentials,
    require_auth_request,
)
from app.integrations.github.exceptions import GitHubError
from app.integrations.github.schemas import (
    Branch,
    Collection,
    Commit,
    ConnectionResponse,
    ConnectResponse,
    DisconnectResponse,
    Installation,
    Issue,
    Job,
    LogResponse,
    PullRequest,
    Repository,
    Run,
    Workflow,
)
from app.services.auth_service import AuthService
from app.services.github_connection_service import (
    BROWSER_COOKIE,
    CALLBACK_PATH,
    GitHubConnectionService,
)
from app.services.github_repository_service import GitHubRepositoryService

router = APIRouter(prefix="/api/v1/github", tags=["github read-only integration"])
mutations = APIRouter(
    prefix="/api/v1/auth/github",
    tags=["github connection"],
    dependencies=[Depends(require_auth_request)],
)
Page = Annotated[int, Query(ge=1, le=1000)]
Size = Annotated[int, Query(ge=1, le=100)]
InstallationId = Annotated[int, Query(gt=0, le=9223372036854775807)]


def connection_service(request: Request, db: Database) -> GitHubConnectionService:
    return GitHubConnectionService(db, request.app.state.settings, request.app.state.github_client)


def repository_service(
    request: Request, db: Database, user: AuthenticatedUser
) -> GitHubRepositoryService:
    return GitHubRepositoryService(
        db,
        request.app.state.settings,
        request.app.state.github_client,
        request.app.state.github_authorization_cache,
        user.id,
    )


Service = Annotated[GitHubRepositoryService, Depends(repository_service)]
Connections = Annotated[GitHubConnectionService, Depends(connection_service)]


@router.get("/connection", response_model=ConnectionResponse)
def connection(user: AuthenticatedUser, service: Connections, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.status(user.id)


@mutations.post("/connect", response_model=ConnectResponse)
def connect(
    user: AuthenticatedUser,
    request: Request,
    response: Response,
    db: Database,
    service: Connections,
    token: Annotated[str, Depends(refresh_credentials)],
):
    session, owner = AuthService(db, request.app.state.settings).active_session(token)
    if owner.id != user.id:
        raise GitHubError(
            "GITHUB_SESSION_CHANGED",
            "The active session does not match this CodeMate account.",
            403,
        )
    url, browser = service.start(user, session)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        BROWSER_COOKIE,
        browser,
        max_age=600,
        httponly=True,
        secure=request.app.state.settings.cookie_secure,
        samesite="lax",
        path=CALLBACK_PATH,
    )
    return {"authorization_url": url}


@router.get("/callback", include_in_schema=False)
def callback(
    request: Request,
    service: Connections,
    state: str = "",
    code: str | None = None,
    error: str | None = None,
):
    result = "connected"
    try:
        service.finish(state, request.cookies.get(BROWSER_COOKIE, ""), code, error is not None)
    except GitHubError as exc:
        result = exc.detail["code"].lower()
    target = (
        request.app.state.settings.github_frontend_origin
        + "/dashboard/github?github_result="
        + result
    )
    response = RedirectResponse(
        target,
        status_code=303,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
    response.delete_cookie(
        BROWSER_COOKIE,
        path=CALLBACK_PATH,
        httponly=True,
        secure=request.app.state.settings.cookie_secure,
        samesite="lax",
    )
    return response


@mutations.post("/disconnect", response_model=DisconnectResponse)
def disconnect(
    user: AuthenticatedUser,
    request: Request,
    db: Database,
    service: Connections,
    token: Annotated[str, Depends(refresh_credentials)],
):
    _, owner = AuthService(db, request.app.state.settings).active_session(token)
    if owner.id != user.id:
        raise GitHubError(
            "GITHUB_SESSION_CHANGED",
            "The active session does not match this CodeMate account.",
            403,
        )
    result = service.disconnect(user.id)
    request.app.state.github_authorization_cache.clear_user(str(user.id))
    return result


@router.get("/installations", response_model=Collection[Installation])
def installations(service: Service, page: Page = 1, per_page: Size = 20):
    return service.installations(page, per_page)


@router.get("/repositories", response_model=Collection[Repository])
def repositories(
    service: Service,
    installation_id: InstallationId,
    page: Page = 1,
    per_page: Size = 20,
    q: Annotated[str, Query(max_length=100)] = "",
    sort: Literal["name", "updated", "stars"] = "updated",
):
    return service.repositories(installation_id, page, per_page, q, sort)


@router.get("/repositories/{owner}/{repo}", response_model=Repository)
def repository(owner: str, repo: str, installation_id: InstallationId, service: Service):
    return service.repository(owner, repo, installation_id)


@router.get("/repositories/{owner}/{repo}/branches", response_model=Collection[Branch])
def branches(
    owner: str,
    repo: str,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
):
    return service.resource(owner, repo, installation_id, "branches", page, per_page)


@router.get("/repositories/{owner}/{repo}/commits", response_model=Collection[Commit])
def commits(
    owner: str,
    repo: str,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
):
    return service.resource(owner, repo, installation_id, "commits", page, per_page)


@router.get("/repositories/{owner}/{repo}/pulls", response_model=Collection[PullRequest])
def pulls(
    owner: str,
    repo: str,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
    state: Literal["open", "closed", "all"] = "open",
):
    return service.resource(owner, repo, installation_id, "pulls", page, per_page, state)


@router.get("/repositories/{owner}/{repo}/issues", response_model=Collection[Issue])
def issues(
    owner: str,
    repo: str,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
    state: Literal["open", "closed", "all"] = "open",
):
    return service.resource(owner, repo, installation_id, "issues", page, per_page, state)


@router.get("/repositories/{owner}/{repo}/workflows", response_model=Collection[Workflow])
def workflows(
    owner: str,
    repo: str,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
):
    return service.resource(owner, repo, installation_id, "workflows", page, per_page)


RunStatus = Literal[
    "completed",
    "in_progress",
    "queued",
    "waiting",
    "requested",
    "pending",
    "success",
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "neutral",
    "skipped",
    "stale",
]


@router.get("/repositories/{owner}/{repo}/actions/runs", response_model=Collection[Run])
def runs(
    owner: str,
    repo: str,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
    status: RunStatus | None = None,
    workflow_id: Annotated[int | None, Query(gt=0)] = None,
):
    return service.resource(
        owner, repo, installation_id, "runs", page, per_page, status=status, workflow_id=workflow_id
    )


@router.get("/repositories/{owner}/{repo}/actions/runs/{run_id}", response_model=Run)
def run(owner: str, repo: str, run_id: int, installation_id: InstallationId, service: Service):
    if run_id <= 0 or run_id > 9223372036854775807:
        raise GitHubError("GITHUB_INVALID_RUN", "Invalid workflow run ID.", 422)
    return service.run(owner, repo, installation_id, run_id)


@router.get(
    "/repositories/{owner}/{repo}/actions/runs/{run_id}/jobs", response_model=Collection[Job]
)
def jobs(
    owner: str,
    repo: str,
    run_id: int,
    installation_id: InstallationId,
    service: Service,
    page: Page = 1,
    per_page: Size = 20,
):
    if run_id <= 0 or run_id > 9223372036854775807:
        raise GitHubError("GITHUB_INVALID_RUN", "Invalid workflow run ID.", 422)
    return service.resource(owner, repo, installation_id, "jobs", page, per_page, run_id=run_id)


@router.get("/repositories/{owner}/{repo}/actions/jobs/{job_id}/logs", response_model=LogResponse)
def logs(owner: str, repo: str, job_id: int, installation_id: InstallationId, service: Service):
    if job_id <= 0 or job_id > 9223372036854775807:
        raise GitHubError("GITHUB_INVALID_JOB", "Invalid job ID.", 422)
    return service.logs(owner, repo, installation_id, job_id)
