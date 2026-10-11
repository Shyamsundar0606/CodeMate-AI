import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.github.authorization_cache import AuthorizationCache
from app.integrations.github.client import LOG_LIMIT, GitHubClient
from app.integrations.github.exceptions import GitHubError, malformed
from app.integrations.github.logs import WARNING, redact_logs
from app.integrations.github.schemas import Collection, normalize, valid_repository_path
from app.services.github_connection_service import GitHubConnectionService


class GitHubRepositoryService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        client: GitHubClient,
        cache: AuthorizationCache,
        user_id: uuid.UUID,
    ):
        self.db = db
        self.settings = settings
        self.client = client
        self.cache = cache
        self.user_id = user_id
        self.connections = GitHubConnectionService(db, settings, client)
        self.item, self.token = self.connections.credentials(user_id)

    def _json(self, path: str, params: dict | None = None):
        try:
            return self.client.json(path, self.token, params)
        except GitHubError as exc:
            if exc.detail["code"] == "GITHUB_REAUTHORIZATION_REQUIRED":
                self.connections.invalidate(self.item)
                self.cache.clear_user(str(self.user_id))
            raise

    def success(self) -> None:
        self.item.last_verified_at = datetime.now(UTC)
        self.db.commit()

    def key(self, installation_id: int, full_name: str) -> tuple:
        return (
            str(self.user_id),
            str(self.item.id),
            hashlib.sha256(self.token.encode()).hexdigest(),
            installation_id,
            full_name.casefold(),
        )

    def installations(self, page: int, per_page: int) -> Collection:
        path = "/user/installations"
        data, headers = self._json(path, {"page": page, "per_page": per_page})
        return self.collection(
            "installations",
            data,
            headers,
            path,
            page,
            per_page,
            "installations",
            scope="Installations accessible to this GitHub App user authorization",
        )

    def repositories(
        self, installation_id: int, page: int, per_page: int, q: str, sort: str
    ) -> Collection:
        path = f"/user/installations/{installation_id}/repositories"
        data, headers = self._json(path, {"page": page, "per_page": per_page})
        result = self.collection(
            "repositories",
            data,
            headers,
            path,
            page,
            per_page,
            "repositories",
            scope="Selected installation; search and sorting apply to this page only",
        )
        for item in result.items:
            self.cache.put(self.key(installation_id, item.full_name), item.id)
        result.items = [
            item
            for item in result.items
            if q.casefold() in f"{item.full_name} {item.description or ''}".casefold()
        ]
        result.items.sort(
            key=(lambda item: item.stars)
            if sort == "stars"
            else (lambda item: item.updated_at)
            if sort == "updated"
            else (lambda item: item.full_name.casefold()),
            reverse=sort in {"stars", "updated"},
        )
        return result

    def repository(self, owner: str, repo: str, installation_id: int):
        valid_repository_path(owner, repo)
        path = f"/repos/{owner}/{repo}"
        data, _ = self._json(path)
        metadata = normalize("repositories", data)
        full_name = f"{owner}/{repo}"
        authorized = self.cache.get(self.key(installation_id, full_name))
        if authorized != metadata.id:
            # Bounded membership verification; private/public endpoint access alone is
            # insufficient proof of this installation's selected repository access.
            for page in range(1, 6):
                listing = f"/user/installations/{installation_id}/repositories"
                value, headers = self._json(listing, {"page": page, "per_page": 100})
                if not isinstance(value, dict) or not isinstance(value.get("repositories"), list):
                    raise malformed()
                for raw in value["repositories"]:
                    item = normalize("repositories", raw)
                    self.cache.put(self.key(installation_id, item.full_name), item.id)
                authorized = self.cache.get(self.key(installation_id, full_name))
                if authorized == metadata.id:
                    break
                if not self.client.has_next(headers, listing):
                    raise GitHubError(
                        "GITHUB_REPOSITORY_NOT_AUTHORIZED",
                        (
                            "This repository is not available in the selected "
                            "installation. Check selected repositories and organization access."
                        ),
                        404,
                    )
            else:
                raise GitHubError(
                    "GITHUB_AUTHORIZATION_CHECK_LIMIT",
                    (
                        "Repository access could not be verified within the bounded lookup. "
                        "Open it from the repository explorer to verify its authorized page."
                    ),
                    409,
                )
        self.success()
        return metadata

    def collection(
        self,
        kind: str,
        data: object,
        headers,
        path: str,
        page: int,
        per_page: int,
        key: str | None = None,
        *,
        owner: str = "",
        repo: str = "",
        scope: str = "Selected repository",
    ) -> Collection:
        raw = data.get(key) if isinstance(data, dict) and key else data
        if not isinstance(raw, list) or len(raw) > 100:
            raise malformed()
        items = [
            normalize(kind, item, owner=owner, repo=repo)
            for item in raw
            if not (kind == "issues" and isinstance(item, dict) and "pull_request" in item)
        ]
        total = data.get("total_count") if isinstance(data, dict) else None
        if total is not None and (
            not isinstance(total, int) or isinstance(total, bool) or total < 0
        ):
            raise malformed()
        result = Collection(
            items=items,
            page=page,
            per_page=per_page,
            has_next=self.client.has_next(headers, path),
            total=total,
            scope=scope,
            fetched_at=datetime.now(UTC),
        )
        self.success()
        return result

    def resource(
        self,
        owner: str,
        repo: str,
        installation_id: int,
        kind: str,
        page: int,
        per_page: int,
        state: str = "open",
        status: str | None = None,
        workflow_id: int | None = None,
        run_id: int | None = None,
    ) -> Collection:
        metadata = self.repository(owner, repo, installation_id)
        self.item, self.token = self.connections.credentials(self.user_id)
        root = f"/repos/{owner}/{repo}"
        params = {"page": page, "per_page": per_page}
        key = None
        if kind in {"branches", "commits", "pulls", "issues"}:
            path = root + "/" + kind
            if kind in {"pulls", "issues"}:
                params["state"] = state
        elif kind == "workflows":
            path = root + "/actions/workflows"
            key = "workflows"
        elif kind == "runs":
            path = root + (
                f"/actions/workflows/{workflow_id}/runs" if workflow_id else "/actions/runs"
            )
            key = "workflow_runs"
            if status:
                params["status"] = status
        elif kind == "jobs" and run_id:
            self.run(owner, repo, installation_id, run_id)
            self.item, self.token = self.connections.credentials(self.user_id)
            path = root + f"/actions/runs/{run_id}/jobs"
            key = "jobs"
        else:
            raise malformed()
        data, headers = self._json(path, params)
        if kind == "runs":
            if not isinstance(data, dict) or not isinstance(data.get(key), list):
                raise malformed()
            for entry in data[key]:
                if (
                    not isinstance(entry, dict)
                    or not isinstance(entry.get("repository"), dict)
                    or entry["repository"].get("id") != metadata.id
                ):
                    raise malformed()
        if kind == "jobs":
            if not isinstance(data, dict) or not isinstance(data.get(key), list):
                raise malformed()
            if any(
                not isinstance(entry, dict) or entry.get("run_id") != run_id for entry in data[key]
            ):
                raise malformed()
        return self.collection(
            kind, data, headers, path, page, per_page, key, owner=owner, repo=repo
        )

    def run(self, owner: str, repo: str, installation_id: int, run_id: int):
        metadata = self.repository(owner, repo, installation_id)
        self.item, self.token = self.connections.credentials(self.user_id)
        data, _ = self._json(f"/repos/{owner}/{repo}/actions/runs/{run_id}")
        if (
            not isinstance(data, dict)
            or data.get("id") != run_id
            or not isinstance(data.get("repository"), dict)
            or data["repository"].get("id") != metadata.id
        ):
            raise malformed()
        result = normalize("runs", data, owner=owner, repo=repo)
        self.success()
        return result

    def logs(self, owner: str, repo: str, installation_id: int, job_id: int) -> dict:
        self.repository(owner, repo, installation_id)
        self.item, self.token = self.connections.credentials(self.user_id)
        job, _ = self._json(f"/repos/{owner}/{repo}/actions/jobs/{job_id}")
        if not isinstance(job, dict) or job.get("id") != job_id:
            raise malformed()
        normalize("jobs", job, owner=owner, repo=repo)
        try:
            raw, truncated = self.client.logs(
                f"/repos/{owner}/{repo}/actions/jobs/{job_id}/logs", self.token
            )
        except GitHubError as exc:
            if exc.detail["code"] == "GITHUB_REAUTHORIZATION_REQUIRED":
                self.connections.invalidate(self.item)
            if exc.detail["code"] == "GITHUB_RESOURCE_UNAVAILABLE":
                raise GitHubError(
                    "GITHUB_LOGS_UNAVAILABLE", "Job logs are unavailable, expired or deleted.", 404
                ) from exc
            raise
        content, truncated, redacted = redact_logs(
            raw, truncated, [self.token, self.settings.github_client_secret.get_secret_value()]
        )
        self.success()
        return {
            "job_id": job_id,
            "content": content,
            "byte_limit": LOG_LIMIT,
            "truncated": truncated,
            "redacted": redacted,
            "warning": WARNING,
            "fetched_at": datetime.now(UTC),
        }
