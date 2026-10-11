import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_missing_secret_fails(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "values",
    [
        {"jwt_secret_key": "weak"},
        {"database_url": "sqlite:///test.db"},
        {"cors_origins": ["*"]},
        {"app_env": "production", "cookie_secure": False},
        {"app_env": "production", "cookie_secure": True, "cors_origins": ["http://localhost:3000"]},
        {"jwt_algorithm": "none"},
    ],
)
def test_unsafe_configuration_fails(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_secure_production_configuration():
    settings = Settings(
        _env_file=None,
        app_env="production",
        cookie_secure=True,
        cors_origins=["https://codemate.example"],
        jwt_secret_key=secrets.token_urlsafe(48),
    )
    assert settings.cookie_secure


def test_request_ids_and_readiness(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ready"}
    assert len(response.headers["x-request-id"]) == 36
    assert response.headers["x-content-type-options"] == "nosniff"
    second = client.get("/does-not-exist")
    assert second.status_code == 404
    assert second.json()["request_id"] == second.headers["x-request-id"]
    assert second.headers["x-request-id"] != response.headers["x-request-id"]


def test_production_refresh_cookie(settings, registered):
    from fastapi.testclient import TestClient

    from app.main import create_app

    production = Settings(
        _env_file=None,
        app_env="production",
        cookie_secure=True,
        cors_origins=["https://codemate.example"],
    )
    with TestClient(create_app(production), base_url="https://api.codemate.example") as client:
        response = client.post(
            "/api/v1/auth/login",
            headers={"X-CodeMate-Request": "1", "Origin": "https://codemate.example"},
            json={"email": registered["email"], "password": registered["password"]},
        )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie


def test_logs_exclude_credentials(client, registered, caplog):
    import logging

    caplog.set_level(logging.INFO, logger="codemate.requests")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": registered["password"]},
    )
    assert response.status_code == 200
    assert "request_id" in caplog.text
    assert registered["password"] not in caplog.text
    assert registered["email"] not in caplog.text
    assert response.json()["access_token"] not in caplog.text
    assert client.cookies.get("codemate_refresh") not in caplog.text
