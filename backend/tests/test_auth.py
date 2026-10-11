import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.api.dependencies.auth import REFRESH_COOKIE
from app.core.security import password_hasher
from app.models import RefreshSession, User


def test_registration_profile_and_hash(client, registered, db):
    user = db.scalar(select(User))
    assert user.email == registered["email"]
    assert user.role.value == "USER"
    assert user.password_hash.startswith("$argon2id$")
    assert password_hasher.verify(user.password_hash, registered["password"])
    assert user.created_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize("field", ["email", "username"])
def test_duplicate_registration(client, registered, field):
    data = dict(registered)
    data["email" if field == "username" else "username"] = (
        "different@example.com" if field == "username" else "different"
    )
    assert client.post("/api/v1/auth/register", json=data).status_code == 409


@pytest.mark.parametrize(
    "update",
    [
        {"email": "invalid"},
        {"password": "short"},
        {"password": "aaaaaaaaaaaa"},
        {"username": "Bad Name"},
        {"username": "ab"},
        {"role": "ADMIN"},
        {"is_active": False},
        {"password": "x" * 129},
    ],
)
def test_registration_validation(client, update):
    data = {"username": "alice", "email": "alice@example.com", "password": "StrongPassword123!"}
    data.update(update)
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 422
    assert "password_hash" not in response.text
    assert data["password"] not in response.text


def test_normalized_email(client, registered):
    data = {**registered, "username": "other", "email": "ALICE@EXAMPLE.COM"}
    assert client.post("/api/v1/auth/register", json=data).status_code == 409
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ALICE@EXAMPLE.COM", "password": registered["password"]},
    )
    assert response.status_code == 200


def test_login_cookie_and_hash(client, logged_in, db):
    token = client.cookies.get(REFRESH_COOKIE)
    session = db.scalar(select(RefreshSession))
    assert session.token_hash != token
    assert len(session.token_hash) == 64
    assert "refresh_token" not in logged_in
    response = client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "StrongPassword123!"}
    )
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert "secure" not in cookie  # local HTTP development only
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "email,password",
    [
        ("alice@example.com", "IncorrectPassword123!"),
        ("unknown@example.com", "StrongPassword123!"),
    ],
)
def test_invalid_login(client, registered, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired credentials"


def test_inactive_login(client, registered, db):
    user = db.scalar(select(User))
    user.is_active = False
    db.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": registered["password"]},
    )
    assert response.status_code == 401


def test_me_sanitized(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "USER"
    assert not {"password", "password_hash", "token_hash", "refresh_token"} & response.json().keys()


@pytest.mark.parametrize(
    "change",
    [
        "expired",
        "type",
        "signature",
        "issuer",
        "audience",
        "subject",
        "missing_exp",
        "algorithm",
    ],
)
def test_jwt_rejections(client, registered, db, settings, change):
    user = db.scalar(select(User))
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
    }
    secret = settings.jwt_secret_key.get_secret_value()
    algorithm = "HS256"
    if change == "expired":
        payload["exp"] = now - timedelta(seconds=1)
    elif change == "type":
        payload["type"] = "refresh"
    elif change == "signature":
        secret = secrets.token_urlsafe(48)
    elif change == "issuer":
        payload["iss"] = "other"
    elif change == "audience":
        payload["aud"] = "other"
    elif change == "subject":
        payload["sub"] = "invalid-uuid"
    elif change == "missing_exp":
        del payload["exp"]
    elif change == "algorithm":
        algorithm = "HS384"
    token = jwt.encode(payload, secret, algorithm=algorithm)
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token}).status_code
        == 401
    )


@pytest.mark.parametrize("token", ["garbage", "", "a.b.c"])
def test_invalid_tokens(client, token):
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token}).status_code
        == 401
    )


def test_account_status_checked(client, auth_headers, db):
    user = db.scalar(select(User))
    user.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401


def test_login_account_throttling(client, registered):
    statuses = [
        client.post(
            "/api/v1/auth/login", json={"email": registered["email"], "password": "wrong"}
        ).status_code
        for _ in range(11)
    ]
    assert statuses == [401] * 10 + [429]


def test_login_ip_throttling(client):
    statuses = [
        client.post(
            "/api/v1/auth/login", json={"email": f"unknown{i}@example.com", "password": "wrong"}
        ).status_code
        for i in range(31)
    ]
    assert statuses == [401] * 30 + [429]


def test_auth_origin_and_custom_header(client):
    data = {"username": "alice", "email": "alice@example.com", "password": "StrongPassword123!"}
    response = client.post(
        "/api/v1/auth/register", json=data, headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403
    del client.headers["X-CodeMate-Request"]
    assert client.post("/api/v1/auth/register", json=data).status_code == 403
