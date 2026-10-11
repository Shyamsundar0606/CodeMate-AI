from sqlalchemy import select

from app.models import Role, User


def test_anonymous_denied(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/users").status_code == 401


def test_user_denied(client, auth_headers):
    assert client.get("/api/v1/users", headers=auth_headers).status_code == 403


def test_admin_pagination_sanitized(client, auth_headers, db):
    user = db.scalar(select(User))
    user.role = Role.ADMIN
    db.commit()
    response = client.get("/api/v1/users?limit=1&offset=0", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert "password_hash" not in response.text and "token_hash" not in response.text
    assert client.get("/api/v1/users?offset=1", headers=auth_headers).json()["items"] == []
    assert client.get("/api/v1/users?limit=101", headers=auth_headers).status_code == 422
    assert client.get("/api/v1/users?offset=-1", headers=auth_headers).status_code == 422
    # Permissions are fetched from the database, not a stale token role claim.
    user.role = Role.USER
    db.commit()
    assert client.get("/api/v1/users", headers=auth_headers).status_code == 403


def test_inactive_admin_denied(client, auth_headers, db):
    user = db.scalar(select(User))
    user.role = Role.ADMIN
    user.is_active = False
    db.commit()
    assert client.get("/api/v1/users", headers=auth_headers).status_code == 401
