from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_contract():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "codemate-api",
        "version": "0.1.0",
    }


def test_cors_permits_local_frontend():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unknown_origin():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"Origin": "https://unknown.example"})
    assert "access-control-allow-origin" not in response.headers
