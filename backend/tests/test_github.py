import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from github_mock import ACCESS, REFRESH, MockGitHub
from sqlalchemy import select

from app.integrations.github.client import JSON_LIMIT, LOG_LIMIT
from app.integrations.github.crypto import CredentialCipher
from app.integrations.github.exceptions import GitHubError
from app.models import GitHubConnection, GitHubOAuthState, RefreshSession

ROOT = "/api/v1/github"
REPO = ROOT + "/repositories/octocat/secure-demo"


@pytest.fixture
def github(settings):
    from app.main import create_app

    config = settings.model_copy(
        update={
            "github_client_id": "Iv1.codemate-test",
            "github_client_secret": __import__("pydantic").SecretStr(
                "test-client-secret-" + "z" * 32
            ),
            "github_token_encryption_key": __import__("pydantic").SecretStr(
                Fernet.generate_key().decode()
            ),
        }
    )
    mock = MockGitHub()
    with TestClient(create_app(config, github_transport=mock.transport)) as client:
        client.headers.update({"X-CodeMate-Request": "1", "Origin": "http://localhost:3000"})
        data = {
            "username": "githubalice",
            "email": "github@example.com",
            "password": "StrongPassword123!",
        }
        assert client.post("/api/v1/auth/register", json=data).status_code == 201
        tokens = client.post(
            "/api/v1/auth/login", json={"email": data["email"], "password": data["password"]}
        ).json()
        client.headers["Authorization"] = "Bearer " + tokens["access_token"]
        yield client, mock, config


def mutation(client, path):
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return client.post("/api/v1/auth/github/" + path, headers={"X-CSRF-Token": csrf})


def start(client):
    response = mutation(client, "connect")
    assert response.status_code == 200, response.text
    url = response.json()["authorization_url"]
    return parse_qs(urlsplit(url).query)["state"][0]


def finish(client, state=None, **params):
    return client.get(
        ROOT + "/callback",
        params={"state": state or start(client), "code": "fixture", **params},
        follow_redirects=False,
    )


@pytest.fixture
def connected(github):
    client, mock, config = github
    assert finish(client).headers["location"].endswith("github_result=connected")
    return github


def test_authorization_pkce_and_encrypted_storage(github, db):
    client, mock, config = github
    state = start(client)
    entry = db.get(GitHubOAuthState, hashlib.sha256(state.encode()).hexdigest())
    assert entry and entry.encrypted_verifier and state not in entry.encrypted_verifier
    assert len(state) == 43
    cookie = next(c for c in client.cookies.jar if c.name == "codemate_github_state")
    assert cookie.path == ROOT + "/callback" and cookie.has_nonstandard_attr("HttpOnly")
    assert finish(client, state).status_code == 303
    item = db.scalar(select(GitHubConnection))
    assert ACCESS not in item.encrypted_access_token and REFRESH not in item.encrypted_refresh_token
    cipher = CredentialCipher(config)
    assert cipher.decrypt(item.user_id, "access", item.encrypted_access_token) == ACCESS
    assert cipher.decrypt(item.user_id, "refresh", item.encrypted_refresh_token) == REFRESH
    response = client.get(ROOT + "/connection")
    assert response.json()["github_login"] == "octocat"
    assert ACCESS not in response.text and "encrypted" not in response.text
    exchange = next(r for r in mock.calls if r.method == "POST")
    verifier = json.loads(exchange.content)["code_verifier"]
    assert 43 <= len(verifier) <= 128
    assert "state=" not in finish(client, state).headers["location"]
    assert finish(client, state).headers["location"].endswith("github_invalid_state")


@pytest.mark.parametrize(
    "mode,result",
    [
        ("invalid", "github_invalid_state"),
        ("browser", "github_invalid_state"),
        ("expired", "github_invalid_state"),
        ("cancelled", "github_authorization_cancelled"),
        ("missing", "github_missing_code"),
        ("revoked_session", "github_session_changed"),
    ],
)
def test_callback_rejects_forgery_and_changed_session(github, db, mode, result):
    client, mock, config = github
    state = start(client)
    entry = db.get(GitHubOAuthState, hashlib.sha256(state.encode()).hexdigest())
    if mode == "invalid":
        state = "x" * 43
    if mode == "browser":
        client.cookies.clear()
    if mode == "expired":
        entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    if mode == "revoked_session":
        db.get(RefreshSession, entry.session_id).revoked_at = datetime.now(UTC)
        db.commit()
    params = {"state": state}
    if mode != "missing":
        params["code"] = "fixture"
    if mode == "cancelled":
        params["error"] = "access_denied"
    response = client.get(ROOT + "/callback", params=params, follow_redirects=False)
    assert response.headers["location"].endswith(result)
    assert db.scalar(select(GitHubConnection)) is None
    assert not mock.calls


def test_mutations_require_csrf(connected):
    client, _, _ = connected
    assert client.post("/api/v1/auth/github/disconnect").status_code == 403
    assert client.post("/api/v1/auth/github/connect").status_code == 403


@pytest.mark.parametrize("remote_ok", [True, False])
def test_disconnect_always_deletes_owned_credentials(connected, db, remote_ok):
    client, mock, config = connected
    if not remote_ok:
        mock.overrides["/applications/Iv1.codemate-test/grant"] = (500, {}, {})
    response = mutation(client, "disconnect")
    assert response.status_code == 200
    assert response.json()["remote_revoked"] is remote_ok
    assert db.scalar(select(GitHubConnection)) is None
    assert client.get(ROOT + "/connection").json()["status"] == "disconnected"
    assert client.get(ROOT + "/repositories?installation_id=10").status_code == 409


def test_cipher_rejects_owner_purpose_and_tampering(github):
    _, _, config = github
    cipher = CredentialCipher(config)
    owner = uuid.uuid4()
    encrypted = cipher.encrypt(owner, "access", ACCESS)
    for target, purpose, value in [
        (uuid.uuid4(), "access", encrypted),
        (owner, "refresh", encrypted),
        (owner, "access", encrypted[:-3] + "bad"),
    ]:
        with pytest.raises(GitHubError):
            cipher.decrypt(target, purpose, value)


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "/branches",
        "/commits",
        "/pulls",
        "/issues",
        "/workflows",
        "/actions/runs",
        "/actions/runs/701",
        "/actions/runs/701/jobs",
    ],
)
def test_repository_and_actions_reads(connected, suffix):
    client, _, _ = connected
    response = client.get(REPO + suffix, params={"installation_id": 10})
    assert response.status_code == 200, response.text
    value = response.json()
    if suffix == "/issues":
        assert [i["number"] for i in value["items"]] == [5]
    if suffix == "/commits":
        assert value["items"][0]["author"] == "Fixture author"
    if suffix == "/actions/runs/701/jobs":
        assert value["items"][0]["steps"][1]["conclusion"] == "failure"
    assert ACCESS not in response.text


def test_repository_pagination_search_and_public_access_boundary(connected):
    client, _, _ = connected
    response = client.get(ROOT + "/repositories", params={"installation_id": 10, "per_page": 1})
    assert response.json()["has_next"] and response.json()["total"] == 2
    next_page = client.get(
        ROOT + "/repositories", params={"installation_id": 10, "per_page": 1, "page": 2}
    )
    assert next_page.json()["items"][0]["name"] == "web-demo"
    assert not next_page.json()["has_next"]
    search = client.get(
        ROOT + "/repositories", params={"installation_id": 10, "q": "secure", "sort": "name"}
    )
    assert len(search.json()["items"]) == 1
    denied = client.get(ROOT + "/repositories/other/public?installation_id=10")
    assert (
        denied.status_code == 404
        and denied.json()["detail"]["code"] == "GITHUB_REPOSITORY_NOT_AUTHORIZED"
    )


def test_logs_are_bounded_redacted_and_token_free_on_redirect(connected):
    client, mock, _ = connected
    response = client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert response.status_code == 200, response.text
    assert "AssertionError" in response.json()["content"]
    assert ACCESS not in response.text and "example-value" not in response.text
    assert response.json()["redacted"]
    download = mock.calls[-1]
    assert download.url.host == "pipelines.actions.githubusercontent.com"
    assert "authorization" not in download.headers and "cookie" not in download.headers
    mock.logs = b"x" * (LOG_LIMIT + 100)
    assert client.get(REPO + "/actions/jobs/801/logs?installation_id=10").json()["truncated"]


@pytest.mark.parametrize(
    "location",
    [
        "http://localhost/private",
        "https://evil.example/log",
        "https://api.github.com/log",
        "https://pipelines.actions.githubusercontent.com@evil.example/log",
        "https://pipelines.actions.githubusercontent.com:8443/log",
        "https://productionresultssa12.blob.core.windows.net.evil.example/log",
    ],
)
def test_log_redirect_rejects_untrusted_destination(connected, location):
    client, mock, _ = connected
    mock.overrides["/repos/octocat/secure-demo/actions/jobs/801/logs"] = (
        302,
        None,
        {"Location": location},
    )
    response = client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "GITHUB_UNSAFE_REDIRECT"
    assert not any(r.url.host == "evil.example" for r in mock.calls)


@pytest.mark.parametrize(
    "status,expected", [(401, 424), (403, 424), (404, 404), (429, 429), (500, 502)]
)
def test_upstream_errors_are_safe_and_do_not_expire_codemate(connected, status, expected):
    client, mock, _ = connected
    mock.overrides["/repos/octocat/secure-demo"] = (
        status,
        {"message": "private upstream " + ACCESS},
        {},
    )
    response = client.get(REPO + "?installation_id=10")
    assert response.status_code == expected
    assert ACCESS not in response.text and "private upstream" not in response.text
    assert client.get("/api/v1/auth/me").status_code == 200
    if status == 401:
        assert client.get(ROOT + "/connection").json()["status"] == "reauthorization_required"


def test_refresh_rotation_persists_when_following_read_fails(connected, db):
    client, mock, config = connected
    item = db.scalar(select(GitHubConnection))
    item.token_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    mock.overrides["/repos/octocat/secure-demo"] = (500, {}, {})
    assert client.get(REPO + "?installation_id=10").status_code == 502
    db.expire_all()
    item = db.scalar(select(GitHubConnection))
    assert (
        CredentialCipher(config).decrypt(item.user_id, "refresh", item.encrypted_refresh_token)
        == "ghr_" + "S" * 40
    )
    assert len([r for r in mock.calls if r.method == "POST"]) == 2


def test_expired_without_refresh_requires_reauthorization(connected, db):
    client, _, _ = connected
    item = db.scalar(select(GitHubConnection))
    item.token_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    item.encrypted_refresh_token = None
    db.commit()
    assert client.get(REPO + "?installation_id=10").status_code == 424
    db.expire_all()
    assert db.scalar(select(GitHubConnection)).encrypted_access_token is None


@pytest.mark.parametrize(
    "mode,expected",
    [("timeout", 504), ("malformed", 502), ("partial", 502), ("large", 502), ("pagination", 502)],
)
def test_reliability_limits(connected, mode, expected):
    client, mock, _ = connected

    def response(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("fixture", request=request)
        if mode == "malformed":
            return httpx.Response(200, stream=httpx.ByteStream(b"invalid-json"))
        if mode == "large":
            return httpx.Response(200, stream=httpx.ByteStream(b"x" * (JSON_LIMIT + 1)))
        return mock.reply(
            200,
            {"total_count": 1, "repositories": [{}]},
            {"Link": '<https://evil.example/page>; rel="next"'} if mode == "pagination" else {},
        )

    if mode == "pagination":
        from github_mock import REPOSITORY

        mock.overrides["/user/installations/10/repositories"] = (
            200,
            {"total_count": 1, "repositories": [REPOSITORY]},
            {"Link": '<https://evil.example/page>; rel="next"'},
        )
    else:
        mock.overrides["/user/installations/10/repositories"] = response
    assert client.get(ROOT + "/repositories?installation_id=10").status_code == expected


def test_rate_limit_stops_duplicate_upstream_requests(connected):
    client, mock, _ = connected
    mock.overrides["/user/installations/10/repositories"] = (
        403,
        {"message": "secondary rate limit"},
        {"Retry-After": "30"},
    )
    first = client.get(ROOT + "/repositories?installation_id=10")
    count = len(mock.calls)
    second = client.get(ROOT + "/repositories?installation_id=10")
    assert first.status_code == second.status_code == 429
    assert len(mock.calls) == count
    assert first.json()["detail"]["retry_after"] == 30


@pytest.mark.parametrize(
    "path",
    [
        ROOT + "/connection",
        ROOT + "/repositories?installation_id=10",
        REPO + "?installation_id=10",
        REPO + "/actions/jobs/801/logs?installation_id=10",
    ],
)
def test_unauthenticated_reads_rejected(connected, path):
    client, _, _ = connected
    client.headers.pop("Authorization")
    assert client.get(path).status_code == 401


def test_other_codemate_user_cannot_see_private_connection(connected):
    client, _, _ = connected
    data = {
        "username": "othergithub",
        "email": "other@example.com",
        "password": "StrongPassword123!",
    }
    assert client.post("/api/v1/auth/register", json=data).status_code == 201
    token = client.post(
        "/api/v1/auth/login", json={"email": data["email"], "password": data["password"]}
    ).json()["access_token"]
    client.headers["Authorization"] = "Bearer " + token
    assert client.get(ROOT + "/connection").json()["github_login"] is None
    assert client.get(REPO + "?installation_id=10").status_code == 409


def test_callback_and_signed_urls_are_not_logged(connected, caplog):
    client, _, _ = connected
    with caplog.at_level(logging.INFO):
        client.get(ROOT + "/callback?state=secret-state&code=secret-code", follow_redirects=False)
        client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert "secret-state" not in caplog.text and "secret-code" not in caplog.text
    assert "temporary-signature" not in caplog.text and ACCESS not in caplog.text


def test_test_transport_cannot_be_used_in_development(settings):
    from app.main import create_app

    with pytest.raises(ValueError, match="isolated test"):
        create_app(
            settings.model_copy(update={"app_env": "development"}),
            github_transport=MockGitHub().transport,
        )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/github/installations?per_page=101",
        "/api/v1/github/repositories?installation_id=0",
        "/api/v1/github/repositories/bad!owner/demo?installation_id=10",
        REPO + "/actions/runs/-1?installation_id=10",
    ],
)
def test_request_validation_bounds(connected, path):
    client, _, _ = connected
    assert client.get(path).status_code == 422


def test_missing_logs_safe_error(connected):
    client, mock, _ = connected
    mock.overrides["/repos/octocat/secure-demo/actions/jobs/801/logs"] = (404, {}, {})
    response = client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "GITHUB_LOGS_UNAVAILABLE"


def test_private_responses_are_not_cacheable(connected):
    client, _, _ = connected
    response = client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_connection_deletion_cascades_with_owner(connected, db):
    from app.models import User

    client, _, _ = connected
    item = db.scalar(select(GitHubConnection))
    db.delete(db.get(User, item.user_id))
    db.commit()
    assert db.scalar(select(GitHubConnection)) is None
    assert db.scalar(select(GitHubOAuthState)) is None
    assert client.get(ROOT + "/connection").status_code == 401


def test_github_account_unique_across_codemate_users(connected, db):
    client, _, _ = connected
    credentials = {
        "username": "secondgithub",
        "email": "second@example.com",
        "password": "StrongPassword123!",
    }
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    ).json()
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    state = start(client)
    response = finish(client, state)
    assert response.headers["location"].endswith("github_account_already_linked")
    assert len(list(db.scalars(select(GitHubConnection)))) == 1
    db.expire_all()
    assert db.get(GitHubOAuthState, hashlib.sha256(state.encode()).hexdigest()).consumed_at


def test_additive_migration_preserves_existing_users_and_sessions(engine):
    from alembic.config import Config
    from conftest import BACKEND
    from sqlalchemy import text

    from alembic import command

    config = Config(str(BACKEND / "alembic.ini"))
    try:
        command.downgrade(config, "0001_backend_core")
        with engine.begin() as connection:
            identity = uuid.uuid4()
            connection.execute(
                text(
                    "INSERT INTO users(id, username, email, password_hash, role, is_active) "
                    "VALUES (:id, 'migrationuser', 'migration@example.com', "
                    "'test-only-hash', 'USER', true)"
                ),
                {"id": identity},
            )
            connection.execute(
                text(
                    "INSERT INTO refresh_sessions(id,user_id,token_hash,expires_at) "
                    "VALUES (:id,:user,:hash,:expires)"
                ),
                {
                    "id": uuid.uuid4(),
                    "user": identity,
                    "hash": "f" * 64,
                    "expires": datetime.now(UTC) + timedelta(days=1),
                },
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM users")) == 1
            assert connection.scalar(text("SELECT count(*) FROM refresh_sessions")) == 1
            assert connection.scalar(text("SELECT to_regclass('github_connections')"))
        command.check(config)
    finally:
        command.upgrade(config, "head")


def test_rate_limit_recovers_after_reset(monkeypatch):
    from app.integrations.github.rate_limit import RateLimitGuard

    clock = [100.0]
    monkeypatch.setattr("app.integrations.github.rate_limit.time.monotonic", lambda: clock[0])
    guard = RateLimitGuard()
    guard.record("hashed-owner", 30, None)
    with pytest.raises(GitHubError):
        guard.check("hashed-owner")
    clock[0] += 31
    guard.check("hashed-owner")


@pytest.mark.parametrize(
    "field,value",
    [
        ("github_api_base_url", "https://evil.example"),
        ("github_redirect_uri", "http://evil.example/api/v1/github/callback"),
        ("github_token_encryption_key", "invalid-key"),
        ("github_frontend_origin", "https://evil.example"),
    ],
)
def test_github_configuration_rejects_unsafe_destinations_and_keys(github, field, value):
    from pydantic import ValidationError

    from app.core.config import Settings

    _, _, config = github
    values = config.model_dump()
    values[field] = value
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_completed_job_logs_without_log_url(connected, conclusion):
    from github_mock import JOB

    client, mock, _ = connected
    metadata = {**JOB, "conclusion": conclusion}
    assert "logs_url" not in metadata
    mock.overrides["/repos/octocat/secure-demo/actions/jobs/801"] = (200, metadata, {})
    response = client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert response.status_code == 200
    assert response.json()["job_id"] == 801
    assert "AssertionError" in response.json()["content"]
    request = next(r for r in mock.calls if r.url.path.endswith("/jobs/801/logs"))
    assert request.url.host == "api.github.com"
    assert request.headers["authorization"] == "Bearer " + ACCESS
    assert "authorization" not in mock.calls[-1].headers


@pytest.mark.parametrize("status", [404, 410])
def test_unavailable_job_logs_can_be_retried(connected, status):
    client, mock, _ = connected
    path = "/repos/octocat/secure-demo/actions/jobs/801/logs"
    mock.overrides[path] = (status, {"message": "private " + ACCESS}, {})
    response = client.get(REPO + "/actions/jobs/801/logs?installation_id=10")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "GITHUB_LOGS_UNAVAILABLE"
    assert ACCESS not in response.text
    assert not any(r.url.host != "api.github.com" for r in mock.calls if r.method == "GET")
    del mock.overrides[path]
    assert client.get(REPO + "/actions/jobs/801/logs?installation_id=10").status_code == 200
