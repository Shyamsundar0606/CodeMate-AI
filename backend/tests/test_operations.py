import asyncio
import json
import logging
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.core.observability import HTTPProtectionMiddleware, Metrics, SafeJSONFormatter, correlation
from app.main import create_app
from app.models import Role, User


@pytest.mark.parametrize(
    "origin", ["https://*.example.com", "https://example.com\n", "https://example.com "]
)
def test_ambiguous_cors_rejected(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def production(**changes):
    return Settings(
        _env_file=None,
        app_env="production",
        cookie_secure=True,
        cors_origins=["https://codemate.example"],
        database_url="postgresql+psycopg://production_role:unused-fixture-password@localhost/production",
        **changes,
    )


def test_production_rejects_known_placeholder_signing_key():
    with pytest.raises(ValidationError):
        production(jwt_secret_key="test-placeholder-" + secrets.token_urlsafe(48))


def test_production_rejects_test_database_identity(settings):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            cookie_secure=True,
            cors_origins=["https://codemate.example"],
        )


@pytest.mark.parametrize("password", ["", "short", "REPLACE_WITH_DATABASE_SECRET"])
def test_production_rejects_missing_or_placeholder_database_password(password):
    values = production().model_dump()
    values["database_url"] = f"postgresql+psycopg://production_role:{password}@localhost/production"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_production_headers_and_documentation_disabled():
    with TestClient(create_app(production())) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404


def test_security_headers_on_errors_and_cors_preflight(client):
    for response in (
        client.get("/private-unmatched"),
        client.options("/health", headers={"Access-Control-Request-Method": "GET"}),
    ):
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "microphone=(self)" in response.headers["permissions-policy"]
        uuid.UUID(response.headers["x-request-id"])


def test_concurrent_context_isolation_and_forwarded_headers_ignored(client):
    @client.app.get("/testing/context")
    async def context(request: Request):
        initial = correlation.get().copy()
        await asyncio.sleep(0.01)
        assert correlation.get() == initial
        assert request.client.host == "testclient"
        return initial

    identifiers = [str(uuid.uuid4()) for _ in range(12)]

    def fetch(identity):
        return client.get(
            "/testing/context",
            headers={
                "X-Correlation-ID": identity,
                "X-Request-ID": "untrusted-client-id",
                "X-Forwarded-For": "203.0.113.7",
            },
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(fetch, identifiers))
    assert len({r.headers["x-request-id"] for r in responses}) == 12
    for identity, response in zip(identifiers, responses, strict=True):
        assert response.json()["correlation_id"] == identity
        assert response.headers["x-correlation-id"] == identity
        assert response.json()["request_id"] == response.headers["x-request-id"]
    assert correlation.get() is None


@pytest.mark.parametrize(
    "value", ["not-a-uuid", "a" * 1000, "../../private", "00000000-0000-0000-0000-000000000000"]
)
def test_invalid_correlation_replaced(client, value):
    response = client.get("/health", headers={"X-Correlation-ID": value})
    assert response.headers["x-correlation-id"] == response.headers["x-request-id"]


def test_body_limit_checks_declared_and_streamed_content(client):
    limit = client.app.state.settings.http_max_body_bytes
    assert client.post("/api/v1/auth/login", content=b"x" * (limit + 1)).status_code == 413

    def chunks():
        yield b"x" * limit
        yield b"y"

    response = client.post("/api/v1/auth/login", content=chunks())
    assert response.status_code == 413
    assert response.json()["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize("length", ["-1", "invalid"])
def test_invalid_content_length_is_rejected(client, length):
    assert (
        client.post(
            "/api/v1/auth/login", content=b"", headers={"Content-Length": length}
        ).status_code
        == 400
    )


def test_voice_upload_budget_is_preserved(client):
    response = client.post("/api/v1/auth/voice/transcribe", content=b"x" * (1048576 + 1))
    assert response.status_code == 401  # Within voice upload limit; still requires authentication.


def test_body_upload_timeout(settings):
    async def run():
        sent = []

        async def receive():
            await asyncio.sleep(2)
            return {"type": "http.request", "body": b"", "more_body": False}

        app = Mock()
        middleware = HTTPProtectionMiddleware(
            app, settings.model_copy(update={"http_body_timeout_seconds": 1}), Metrics()
        )

        async def send(message):
            sent.append(message)

        await middleware(
            {"type": "http", "path": "/", "method": "POST", "headers": []}, receive, send
        )
        assert sent[0]["status"] == 408
        app.assert_not_called()

    asyncio.run(run())


def test_total_upload_deadline_cannot_be_bypassed_by_ready_chunks(settings, monkeypatch):
    values = iter([0, 2, 3])
    monkeypatch.setattr("app.core.observability.time.perf_counter", lambda: next(values, 3))

    async def run():
        sent = []
        receive = Mock()

        async def send(message):
            sent.append(message)

        middleware = HTTPProtectionMiddleware(
            Mock(), settings.model_copy(update={"http_body_timeout_seconds": 1}), Metrics()
        )
        await middleware(
            {"type": "http", "path": "/", "method": "POST", "headers": []}, receive, send
        )
        assert sent[0]["status"] == 408
        receive.assert_not_called()

    asyncio.run(run())


def test_database_readiness_failure_and_recovery(client, monkeypatch):
    engine = client.app.state.engine
    original = engine.connect
    calls = 0

    def connect():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OperationalError("SELECT 1", {}, Exception("private-db-failure"))
        return original()

    monkeypatch.setattr(engine, "connect", connect)
    failed = client.get("/health/ready")
    assert failed.status_code == 503
    assert failed.json() == {"status": "unavailable"}
    assert "private" not in failed.text
    assert client.get("/health/ready").status_code == 200
    assert client.get("/health").status_code == 200


def test_metrics_access_control_and_privacy(client, registered, auth_headers, db):
    path = "/api/v1/operations/metrics"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=auth_headers).status_code == 403
    user = db.scalar(select(User).where(User.email == registered["email"]))
    user.role = Role.ADMIN
    db.commit()
    for index in range(10):
        client.get(f"/private-name-{index}?token=private-query")
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["scope"] == "process"
    assert response.json()["events"]["authorization_denied"] >= 2
    for secret in (registered["email"], registered["password"], "private-name", "private-query"):
        assert secret not in response.text
    assert len([r for r in response.json()["http"] if r["route"] == "unmatched"]) == 1


def test_json_logs_allowlist_data_and_never_format_tracebacks():
    formatter = SafeJSONFormatter("test")
    record = logging.LogRecord(
        "codemate",
        logging.ERROR,
        "",
        0,
        json.dumps(
            {
                "event": "safe_event",
                "password": "private-value",
                "transcript": "private-audio",
            }
        ),
        (),
        (ValueError, ValueError("private-exception"), None),
    )
    output = formatter.format(record)
    value = json.loads(output)
    assert value["event"] == "safe_event"
    assert value["timestamp"].endswith("+00:00")
    assert not any(s in output for s in ("private-value", "private-audio", "private-exception"))


def test_logs_use_templates_and_sanitized_unexpected_errors(client, caplog):
    @client.app.get("/testing/failure")
    def fail():
        raise RuntimeError("private-token-from-upstream")

    response = client.get("/testing/failure")
    assert response.status_code == 500
    assert response.json()["request_id"] == response.headers["x-request-id"]
    client.get("/private-path-value?token=private-query-value")
    records = [json.loads(r.message) for r in caplog.records if r.name == "codemate.requests"]
    assert records[-1]["route"] == "unmatched"
    assert "private-token-from-upstream" not in caplog.text
    assert "private-path-value" not in caplog.text
    assert "private-query-value" not in caplog.text
