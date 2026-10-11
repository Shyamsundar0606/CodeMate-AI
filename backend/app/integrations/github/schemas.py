import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError

from app.integrations.github.exceptions import malformed

Positive = Annotated[int, Field(gt=0)]


class Installation(BaseModel):
    id: Positive
    account: str
    repository_selection: Literal["all", "selected"]
    permissions: dict[str, str]
    suspended: bool


class Repository(BaseModel):
    id: Positive
    name: str
    full_name: str
    owner: str
    description: str | None
    private: bool
    default_branch: str | None
    language: str | None
    stars: Annotated[int, Field(ge=0)]
    forks: Annotated[int, Field(ge=0)]
    fork: bool
    updated_at: datetime
    pushed_at: datetime | None
    html_url: str


class Branch(BaseModel):
    name: str
    sha: str
    protected: bool


class Commit(BaseModel):
    sha: str
    short_sha: str
    message: str
    author: str | None
    timestamp: datetime | None
    html_url: str


class PullRequest(BaseModel):
    number: Positive
    title: str
    state: str
    author: str | None
    created_at: datetime
    updated_at: datetime
    base: str
    head: str
    draft: bool
    html_url: str


class Issue(BaseModel):
    number: Positive
    title: str
    state: str
    labels: list[str]
    author: str | None
    created_at: datetime
    updated_at: datetime
    html_url: str


class Workflow(BaseModel):
    id: Positive
    name: str
    path: str
    state: str
    html_url: str


class Run(BaseModel):
    id: Positive
    name: str | None
    run_number: Positive
    branch: str | None
    sha: str
    event: str
    status: str
    conclusion: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    duration_seconds: int | None
    html_url: str


class Step(BaseModel):
    number: int
    name: str
    status: str
    conclusion: str | None


class Job(BaseModel):
    id: Positive
    run_id: Positive
    name: str
    status: str
    conclusion: str | None
    started_at: datetime | None
    completed_at: datetime | None
    steps: list[Step]
    html_url: str


class Collection[T](BaseModel):
    items: list[T]
    page: int
    per_page: int
    has_next: bool
    total: int | None = None
    scope: str
    fetched_at: datetime


class ConnectionResponse(BaseModel):
    configured: bool
    status: Literal["disconnected", "connected", "reauthorization_required"]
    id: str | None = None
    github_user_id: int | None = None
    github_login: str | None = None
    github_display_name: str | None = None
    github_avatar_url: str | None = None
    granted_permissions: dict[str, str] = {}
    connected_at: datetime | None = None
    last_verified_at: datetime | None = None
    install_url: str | None = None


class ConnectResponse(BaseModel):
    authorization_url: str


class DisconnectResponse(BaseModel):
    disconnected: bool
    remote_revoked: bool
    message: str


class LogResponse(BaseModel):
    job_id: Positive
    content: str
    byte_limit: int
    truncated: bool
    redacted: bool
    warning: str
    fetched_at: datetime


def valid_repository_path(owner: str, repo: str) -> None:
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", owner)
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", repo)
        or repo in {".", ".."}
    ):
        from app.integrations.github.exceptions import GitHubError

        raise GitHubError(
            "GITHUB_INVALID_REPOSITORY", "Invalid GitHub owner or repository name.", 422
        )


def normalize(kind: str, item: object, *, owner: str = "", repo: str = "") -> BaseModel:
    try:
        if not isinstance(item, dict):
            raise ValueError("Expected object")
        link = f"https://github.com/{owner}/{repo}"
        if kind == "installations":
            permissions = item["permissions"]
            if not isinstance(permissions, dict) or any(
                value != "read" for value in permissions.values()
            ):
                from app.integrations.github.exceptions import GitHubError

                raise GitHubError(
                    "GITHUB_UNSAFE_PERMISSIONS",
                    (
                        "This App installation has permissions beyond "
                        "read-only access. Correct its configuration before continuing."
                    ),
                )
            return Installation(
                id=item["id"],
                account=item["account"]["login"],
                repository_selection=item["repository_selection"],
                permissions=permissions,
                suspended=item.get("suspended_at") is not None,
            )
        if kind == "repositories":
            owner = item["owner"]["login"]
            repo = item["name"]
            valid_repository_path(owner, repo)
            return Repository(
                id=item["id"],
                name=repo,
                full_name=f"{owner}/{repo}",
                owner=owner,
                description=item.get("description"),
                private=item["private"],
                default_branch=item.get("default_branch"),
                language=item.get("language"),
                stars=item["stargazers_count"],
                forks=item["forks_count"],
                fork=item["fork"],
                updated_at=item["updated_at"],
                pushed_at=item.get("pushed_at"),
                html_url=f"https://github.com/{owner}/{repo}",
            )
        if kind == "branches":
            return Branch(name=item["name"], sha=item["commit"]["sha"], protected=item["protected"])
        if kind == "commits":
            sha = item["sha"]
            commit = item["commit"]
            author = commit.get("author") or {}
            if not re.fullmatch(r"[a-fA-F0-9]{40,64}", sha):
                raise ValueError("Invalid SHA")
            return Commit(
                sha=sha,
                short_sha=sha[:7],
                message=commit["message"][:4000],
                author=author.get("name"),
                timestamp=author.get("date"),
                html_url=f"{link}/commit/{sha}",
            )
        if kind == "pulls":
            return PullRequest(
                number=item["number"],
                title=item["title"][:1000],
                state=item["state"],
                author=(item.get("user") or {}).get("login"),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                base=item["base"]["ref"],
                head=item["head"]["ref"],
                draft=item["draft"],
                html_url=f"{link}/pull/{item['number']}",
            )
        if kind == "issues":
            labels = [
                label["name"] if isinstance(label, dict) else str(label) for label in item["labels"]
            ][:100]
            return Issue(
                number=item["number"],
                title=item["title"][:1000],
                state=item["state"],
                labels=labels,
                author=(item.get("user") or {}).get("login"),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                html_url=f"{link}/issues/{item['number']}",
            )
        if kind == "workflows":
            return Workflow(
                id=item["id"],
                name=item["name"],
                path=item["path"],
                state=item["state"],
                html_url=f"{link}/actions/workflows/{item['id']}",
            )
        if kind == "runs":
            start = item.get("run_started_at")
            finish = item["updated_at"]
            duration = (
                max(
                    0,
                    int(
                        (
                            datetime.fromisoformat(finish.replace("Z", "+00:00"))
                            - datetime.fromisoformat(start.replace("Z", "+00:00"))
                        ).total_seconds()
                    ),
                )
                if start and item["status"] == "completed"
                else None
            )
            return Run(
                id=item["id"],
                name=item.get("name"),
                run_number=item["run_number"],
                branch=item.get("head_branch"),
                sha=item["head_sha"],
                event=item["event"],
                status=item["status"],
                conclusion=item.get("conclusion"),
                created_at=item["created_at"],
                updated_at=finish,
                started_at=start,
                duration_seconds=duration,
                html_url=f"{link}/actions/runs/{item['id']}",
            )
        if kind == "jobs":
            steps = [
                Step(
                    number=step["number"],
                    name=step["name"],
                    status=step["status"],
                    conclusion=step.get("conclusion"),
                )
                for step in item["steps"][:200]
            ]
            return Job(
                id=item["id"],
                run_id=item["run_id"],
                name=item["name"],
                status=item["status"],
                conclusion=item.get("conclusion"),
                started_at=item.get("started_at"),
                completed_at=item.get("completed_at"),
                steps=steps,
                html_url=f"{link}/actions/runs/{item['run_id']}/job/{item['id']}",
            )
        raise ValueError("Unsupported resource")
    except (KeyError, TypeError, ValueError, AttributeError, ValidationError) as exc:
        raise malformed() from exc
