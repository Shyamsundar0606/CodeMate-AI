import os
import secrets
from pathlib import Path

import pytest
from alembic.config import Config
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from alembic import command
from app.core.config import Settings
from app.db.session import build_engine, build_session_factory

# Guard before importing app.main or doing any database writes.
BACKEND = Path(__file__).resolve().parents[1]
TEST_URL = os.environ.get("TEST_DATABASE_URL") or dotenv_values(BACKEND / ".env.test").get(
    "TEST_DATABASE_URL"
)
if not TEST_URL:
    raise pytest.UsageError("TEST_DATABASE_URL missing; run scripts/setup_local.py")
url = make_url(TEST_URL)
if (
    url.drivername != "postgresql+psycopg"
    or url.database != "codemate_test_db"
    or url.username != "codemate_test_user"
    or url.host != "127.0.0.1"
    or url.port != 5433
):
    raise pytest.UsageError("Tests require the dedicated CodeMate test database/user on port 5433")
os.environ["DATABASE_URL"] = TEST_URL
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["APP_ENV"] = "test"
os.environ["COOKIE_SECURE"] = "false"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'


@pytest.fixture(scope="session")
def settings():
    return Settings(_env_file=None)


@pytest.fixture(scope="session")
def engine(settings):
    engine = build_engine(settings)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "codemate_test_db"
        assert connection.scalar(text("SELECT session_user")) == "codemate_test_user"
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(engine):
    # Only dedicated test role can own these tables. Never truncate development data.
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE refresh_sessions, users, login_throttles CASCADE"))


@pytest.fixture
def session_factory(engine):
    return build_session_factory(engine)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def client(settings):
    from app.main import create_app

    with TestClient(create_app(settings)) as client:
        client.headers["X-CodeMate-Request"] = "1"
        client.headers["Origin"] = "http://localhost:3000"
        yield client


@pytest.fixture
def registered(client):
    data = {"username": "alice", "email": "alice@example.com", "password": "StrongPassword123!"}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201
    return data


@pytest.fixture
def logged_in(client, registered):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": registered["password"]},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def auth_headers(logged_in):
    return {"Authorization": "Bearer " + logged_in["access_token"]}
