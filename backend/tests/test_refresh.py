import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.dependencies.auth import REFRESH_COOKIE
from app.core.security import token_hash
from app.models import RefreshSession, User


def test_rotation_and_replay(client, logged_in, db):
    original = client.cookies.get(REFRESH_COOKIE)
    response = client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": logged_in["csrf_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"] != logged_in["access_token"]
    assert client.cookies.get(REFRESH_COOKIE) != original
    sessions = list(db.scalars(select(RefreshSession)))
    assert len(sessions) == 2
    assert sum(session.revoked_at is not None for session in sessions) == 1
    replay = client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"{REFRESH_COOKIE}={original}", "X-CSRF-Token": logged_in["csrf_token"]},
    )
    assert replay.status_code == 401


@pytest.mark.parametrize("condition", ["expired", "revoked", "inactive"])
def test_refresh_denied(client, logged_in, db, condition):
    session = db.scalar(select(RefreshSession))
    if condition == "expired":
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif condition == "revoked":
        session.revoked_at = datetime.now(UTC)
    else:
        db.scalar(select(User)).is_active = False
    db.commit()
    response = client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": logged_in["csrf_token"]}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("csrf", [None, "invalid", "a" * 64, "?" * 64])
def test_refresh_csrf_denied(client, logged_in, csrf):
    headers = {"X-CSRF-Token": csrf} if csrf is not None else {}
    if csrf and not csrf.isascii():
        # HTTP headers use Latin-1 at the transport boundary.
        headers = {b"X-CSRF-Token": csrf.encode("utf-8")}
    response = client.post("/api/v1/auth/refresh", headers=headers)
    assert response.status_code == 403


def test_no_cookie(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_and_clears_cookie(client, logged_in, db, auth_headers):
    token = client.cookies.get(REFRESH_COOKIE)
    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": logged_in["csrf_token"]})
    assert response.status_code == 204
    assert client.cookies.get(REFRESH_COOKIE) is None
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash(token))
    )
    assert session.revoked_at is not None
    assert (
        client.post(
            "/api/v1/auth/refresh",
            headers={
                "Cookie": f"{REFRESH_COOKIE}={token}",
                "X-CSRF-Token": logged_in["csrf_token"],
            },
        ).status_code
        == 401
    )
    # Logout revokes refresh only; already-issued stateless JWT remains valid until expiry.
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 200


def test_concurrent_refresh(client, logged_in, db, settings):
    token = client.cookies.get(REFRESH_COOKIE)
    barrier = threading.Barrier(2)

    def attempt():
        from app.main import create_app

        with TestClient(create_app(settings)) as other:
            barrier.wait(timeout=5)
            return other.post(
                "/api/v1/auth/refresh",
                headers={
                    "X-CodeMate-Request": "1",
                    "Origin": "http://localhost:3000",
                    "X-CSRF-Token": logged_in["csrf_token"],
                    "Cookie": f"{REFRESH_COOKIE}={token}",
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        statuses = [future.result(timeout=15) for future in futures]
    assert sorted(statuses) == [200, 401]
    sessions = list(db.scalars(select(RefreshSession)))
    assert len(sessions) == 2
    assert sum(session.revoked_at is not None for session in sessions) == 1


def test_rotation_failure_rolls_back(client, logged_in, db, monkeypatch):
    from app.services.auth_service import AuthService

    original = client.cookies.get(REFRESH_COOKIE)

    def fail_creation(self, user_id):
        raise RuntimeError("simulated failure")

    with monkeypatch.context() as patch:
        patch.setattr(AuthService, "_new_session", fail_creation)
        with TestClient(client.app, raise_server_exceptions=False) as other:
            response = other.post(
                "/api/v1/auth/refresh",
                headers={
                    "X-CodeMate-Request": "1",
                    "Origin": "http://localhost:3000",
                    "X-CSRF-Token": logged_in["csrf_token"],
                    "Cookie": f"{REFRESH_COOKIE}={original}",
                },
            )
        assert response.status_code == 500
        assert "simulated failure" not in response.text
        assert response.json()["request_id"] == response.headers["x-request-id"]
    db.expire_all()
    sessions = list(db.scalars(select(RefreshSession)))
    assert len(sessions) == 1 and sessions[0].revoked_at is None
    assert (
        client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": logged_in["csrf_token"]}
        ).status_code
        == 200
    )


def test_csrf_bootstrap_after_reload(client, logged_in):
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json() == {"csrf_token": logged_in["csrf_token"]}
    assert response.headers["cache-control"] == "no-store"
    assert client.cookies.get(REFRESH_COOKIE) not in response.text
    assert (
        client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": response.json()["csrf_token"]}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("condition", ["missing", "expired", "untrusted_origin"])
def test_csrf_bootstrap_denied(client, logged_in, db, condition):
    headers = {}
    if condition == "missing":
        client.cookies.clear()
    elif condition == "expired":
        db.scalar(select(RefreshSession)).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    else:
        headers["Origin"] = "https://evil.example"
    response = client.get("/api/v1/auth/csrf", headers=headers)
    assert response.status_code == (403 if condition == "untrusted_origin" else 401)
