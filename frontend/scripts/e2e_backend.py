"""Isolated E2E helper: guarded test role/database; never reads development credentials."""

import os
import re
import secrets
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
mode, prefix = sys.argv[1:3]
if not re.fullmatch(r"e2e_[a-f0-9]{10}", prefix):
    raise SystemExit("Invalid disposable account prefix")
# Do not accept DATABASE_URL / TEST_DATABASE_URL from the caller. This helper uses only
# the explicit test config and validates the live DB identity before every write.
value = dotenv_values(BACKEND / ".env.test").get("TEST_DATABASE_URL")
if not value:
    raise SystemExit("Dedicated test database configuration is missing")
url = make_url(value)
if (url.drivername, url.database, url.username, url.host, url.port) != (
    "postgresql+psycopg",
    "codemate_test_db",
    "codemate_test_user",
    "127.0.0.1",
    5433,
):
    raise SystemExit(
        "E2E requires the dedicated CodeMate test database and role on 5433"
    )
os.environ.update(
    DATABASE_URL=value,
    JWT_SECRET_KEY=secrets.token_urlsafe(48),
    APP_ENV="test",
    COOKIE_SECURE="false",
    CORS_ORIGINS='["http://localhost:3000"]',
)
os.chdir(BACKEND)
engine = create_engine(value, hide_parameters=True)
with engine.connect() as connection:
    if (
        connection.scalar(text("SELECT current_database()")) != "codemate_test_db"
        or connection.scalar(text("SELECT session_user")) != "codemate_test_user"
    ):
        raise SystemExit("Live database identity check failed")
if mode == "prepare":
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
    # This dedicated test environment is exclusive during this suite.
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM login_throttles"))
elif mode == "cleanup":
    with engine.begin() as connection:
        # Exact known disposable names, no wildcard deletion or truncate.
        for suffix in ("user", "mobile", "admin", "outage", "github"):
            connection.execute(
                text("DELETE FROM users WHERE username=:name AND email=:email"),
                {
                    "name": f"{prefix}_{suffix}",
                    "email": f"{prefix}_{suffix}@example.com",
                },
            )
elif mode == "promote-test-admin":
    with engine.begin() as connection:
        result = connection.execute(
            text("UPDATE users SET role='ADMIN' WHERE username=:name AND email=:email"),
            {"name": f"{prefix}_admin", "email": f"{prefix}_admin@example.com"},
        )
        if result.rowcount != 1:
            raise SystemExit("Expected disposable test administrator account missing")
elif mode != "serve":
    raise SystemExit("Unsupported E2E helper operation")
engine.dispose()
if mode == "serve":
    import uvicorn
    from app.core.config import Settings
    from app.main import create_app
    from cryptography.fernet import Fernet

    sys.path.insert(0, str(BACKEND / "tests"))
    from contextlib import asynccontextmanager
    from threading import Event, Thread

    from ai_mock import MockOllama
    from app.ai.worker import InvestigationWorker
    from github_mock import MockGitHub

    # Explicit test-only credentials and transport; never read a live App configuration.
    config = Settings(
        _env_file=None,
        github_client_id="Iv1.codemate-test",
        github_client_secret=secrets.token_urlsafe(32),
        github_token_encryption_key=Fernet.generate_key().decode(),
        github_redirect_uri="http://localhost:8001/api/v1/github/callback",
    )
    ollama_mock = MockOllama()
    ollama_mock.delay = 1
    application = create_app(
        config,
        github_transport=MockGitHub().transport,
        ollama_transport=ollama_mock.transport,
    )
    worker = InvestigationWorker(
        config,
        application.state.session_factory,
        application.state.engine,
        application.state.github_client,
        application.state.ollama_client,
    )
    original_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def test_lifespan(app):
        async with original_lifespan(app):
            stop = Event()

            def work():
                while not stop.is_set():
                    worker.tick()
                    stop.wait(0.2)

            thread = Thread(target=work, daemon=False)
            thread.start()
            try:
                yield
            finally:
                stop.set()
                thread.join(timeout=10)
                if thread.is_alive():
                    raise RuntimeError("Test-only AI worker did not stop")

    application.router.lifespan_context = test_lifespan
    uvicorn.run(
        application,
        host="127.0.0.1",
        port=8001,
        proxy_headers=False,
        log_level="warning",
    )
