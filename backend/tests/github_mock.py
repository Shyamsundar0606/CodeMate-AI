"""Controlled GitHub HTTP fixture. No live requests, credentials or production imports."""

import copy
import json
from urllib.parse import parse_qs

import httpx

DATE = "2026-10-01T10:00:00Z"
ACCESS = "ghu_" + "A" * 40
REFRESH = "ghr_" + "B" * 40
PERMISSIONS = {
    "metadata": "read",
    "contents": "read",
    "issues": "read",
    "pull_requests": "read",
    "actions": "read",
}
REPOSITORY = {
    "id": 42,
    "name": "secure-demo",
    "owner": {"login": "octocat"},
    "description": "Isolated GitHub HTTP test fixture",
    "private": True,
    "default_branch": "main",
    "language": "Python",
    "stargazers_count": 7,
    "forks_count": 2,
    "fork": False,
    "updated_at": DATE,
    "pushed_at": DATE,
}
SECOND = {**REPOSITORY, "id": 43, "name": "web-demo", "private": False, "language": "TypeScript"}
INSTALLATION = {
    "id": 10,
    "account": {"login": "octocat"},
    "repository_selection": "selected",
    "permissions": PERMISSIONS,
    "suspended_at": None,
}
WORKFLOW = {
    "id": 11,
    "name": "Backend Tests",
    "path": ".github/workflows/tests.yml",
    "state": "active",
}
RUN = {
    "id": 701,
    "name": "Backend Tests",
    "run_number": 128,
    "head_branch": "main",
    "head_sha": "a" * 40,
    "event": "push",
    "status": "completed",
    "conclusion": "failure",
    "created_at": DATE,
    "updated_at": "2026-10-01T10:02:00Z",
    "run_started_at": DATE,
    "repository": REPOSITORY,
}
SUCCESS = {**RUN, "id": 702, "run_number": 127, "conclusion": "success"}
QUEUED = {
    **RUN,
    "id": 703,
    "run_number": 129,
    "status": "queued",
    "conclusion": None,
    "run_started_at": None,
}
JOB = {
    "id": 801,
    "run_id": 701,
    "name": "pytest",
    "status": "completed",
    "conclusion": "failure",
    "started_at": DATE,
    "completed_at": "2026-10-01T10:02:00Z",
    "steps": [
        {"number": 1, "name": "Checkout", "status": "completed", "conclusion": "success"},
        {
            "number": 2,
            "name": "Run API integration tests",
            "status": "completed",
            "conclusion": "failure",
        },
    ],
}
PULL = {
    "number": 4,
    "title": "Improve session checks",
    "state": "open",
    "user": {"login": "octocat"},
    "created_at": DATE,
    "updated_at": DATE,
    "base": {"ref": "main"},
    "head": {"ref": "fix-session"},
    "draft": False,
}
ISSUE = {
    "number": 5,
    "title": "Refresh session edge case",
    "state": "open",
    "user": {"login": "octocat"},
    "created_at": DATE,
    "updated_at": DATE,
    "labels": [{"name": "bug"}],
}


class MockGitHub:
    def __init__(self):
        self.calls = []
        self.overrides = {}
        self.user_id = 101
        self.logs = (
            b"Run API integration tests\nAssertionError: expected 200, received 401\n"
            b"secret=example-value\n" + ACCESS.encode() + b"\n<script>alert('unsafe')</script>\n"
        )
        self.transport = httpx.MockTransport(self.handle)

    def reply(self, status: int, data=None, headers=None):
        raw = json.dumps(data).encode() if data is not None else b""
        return httpx.Response(
            status,
            headers={"Content-Type": "application/json", **(headers or {})},
            stream=httpx.ByteStream(raw),
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path in self.overrides:
            value = self.overrides[path]
            if callable(value):
                return value(request)
            status, data, headers = value
            return self.reply(status, data, headers)
        if request.url.host in {
            "pipelines.actions.githubusercontent.com",
            "productionresultssa12.blob.core.windows.net",
        }:
            return httpx.Response(
                200, stream=httpx.ByteStream(self.logs), headers={"Content-Type": "text/plain"}
            )
        if request.url.host == "github.com" and path == "/login/oauth/access_token":
            body = json.loads(request.content)
            if body.get("code") == "bad":
                return self.reply(200, {"error": "bad_verification_code"})
            refreshing = body.get("grant_type") == "refresh_token"
            return self.reply(
                200,
                {
                    "access_token": "ghu_" + "R" * 40 if refreshing else ACCESS,
                    "token_type": "bearer",
                    "refresh_token": "ghr_" + "S" * 40 if refreshing else REFRESH,
                    "expires_in": 28800,
                    "refresh_token_expires_in": 15897600,
                    "scope": "",
                },
            )
        if request.url.host != "api.github.com":
            return self.reply(500)
        if path.startswith("/applications/") and path.endswith("/grant"):
            return self.reply(204) if request.method == "DELETE" else self.reply(405)
        if request.method != "GET":
            return self.reply(405)
        if path == "/user":
            return self.reply(
                200, {"id": self.user_id, "login": "octocat", "name": "GitHub test account"}
            )
        params = parse_qs(request.url.query.decode())
        page = int(params.get("page", ["1"])[0])
        size = int(params.get("per_page", ["20"])[0])
        if path == "/user/installations":
            return self.reply(
                200, {"total_count": 1, "installations": [INSTALLATION] if page == 1 else []}
            )
        if path == "/user/installations/10/repositories":
            values = [REPOSITORY, SECOND]
            items = values[(page - 1) * size : page * size]
            headers = (
                {
                    "Link": (
                        f"<https://api.github.com{path}?page={page + 1}"
                        f'&per_page={size}>; rel="next"'
                    )
                }
                if page * size < len(values)
                else {}
            )
            return self.reply(200, {"total_count": len(values), "repositories": items}, headers)
        if path.startswith("/user/installations/"):
            return self.reply(404, {"message": "Not found"})
        root = "/repos/octocat/secure-demo"
        if path in {root, "/repos/octocat/web-demo"}:
            return self.reply(200, REPOSITORY if path == root else SECOND)
        if path == "/repos/other/public":
            return self.reply(
                200,
                {
                    **REPOSITORY,
                    "id": 999,
                    "owner": {"login": "other"},
                    "name": "public",
                    "private": False,
                },
            )
        if not path.startswith(root):
            return self.reply(404, {"message": "Not found"})
        suffix = path[len(root) :]
        if suffix == "/branches":
            return self.reply(
                200,
                [{"name": "main", "commit": {"sha": "a" * 40}, "protected": True}]
                if page == 1
                else [],
            )
        if suffix == "/commits":
            return self.reply(
                200,
                [
                    {
                        "sha": "a" * 40,
                        "author": None,
                        "commit": {
                            "message": "Fix session restoration",
                            "author": {"name": "Fixture author", "date": DATE},
                        },
                    }
                ]
                if page == 1
                else [],
            )
        if suffix == "/pulls":
            return self.reply(200, [PULL] if page == 1 else [])
        if suffix == "/issues":
            return self.reply(
                200,
                [
                    ISSUE,
                    {
                        **PULL,
                        "labels": [],
                        "pull_request": {
                            "url": "https://api.github.com/repos/octocat/secure-demo/pulls/4"
                        },
                    },
                ]
                if page == 1
                else [],
            )
        if suffix == "/actions/workflows":
            return self.reply(200, {"total_count": 1, "workflows": [WORKFLOW] if page == 1 else []})
        if suffix in {"/actions/runs", "/actions/workflows/11/runs"}:
            runs = [RUN, SUCCESS, QUEUED]
            status = params.get("status", [None])[0]
            if status:
                runs = [
                    run for run in runs if run["status"] == status or run["conclusion"] == status
                ]
            return self.reply(
                200, {"total_count": len(runs), "workflow_runs": runs if page == 1 else []}
            )
        if suffix == "/actions/runs/701":
            return self.reply(200, RUN)
        if suffix == "/actions/runs/701/jobs":
            return self.reply(200, {"total_count": 1, "jobs": [JOB] if page == 1 else []})
        if suffix == "/actions/jobs/801":
            return self.reply(200, JOB)
        if suffix == "/actions/jobs/801/logs":
            return self.reply(
                302,
                headers={
                    "Location": (
                        "https://pipelines.actions.githubusercontent.com/logs/fixture"
                        "?sig=temporary-signature"
                    )
                },
            )
        return self.reply(404, {"message": "Not found"})

    def data(self, value):
        return copy.deepcopy(value)
