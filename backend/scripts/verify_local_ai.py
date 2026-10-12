"""Controlled live Ollama verification: harmless fixture and guarded test DB only."""

import json
import logging
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dotenv import dotenv_values
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from ai_mock import FAILURES
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from github_mock import MockGitHub

from app.ai.schemas import Report
from app.ai.worker import InvestigationWorker
from app.core.config import Settings
from app.main import create_app
from app.models import AIInvestigation, User


def main():
    backend = Path(__file__).resolve().parents[1]
    value = dotenv_values(backend / ".env.test").get("TEST_DATABASE_URL")
    if not value:
        raise SystemExit("Dedicated test DB configuration missing")
    url = make_url(value)
    if (url.drivername, url.database, url.username, url.host, url.port) != (
        "postgresql+psycopg",
        "codemate_test_db",
        "codemate_test_user",
        "127.0.0.1",
        5433,
    ):
        raise SystemExit("Live fixture verification requires the guarded test DB")
    logging.disable(logging.CRITICAL)
    config = Settings(
        _env_file=None,
        database_url=value,
        jwt_secret_key=secrets.token_urlsafe(48),
        app_env="test",
        github_client_id="Iv1.codemate-test",
        github_client_secret=secrets.token_urlsafe(32),
        github_token_encryption_key=Fernet.generate_key().decode(),
        ollama_model=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b"),
    )
    github = MockGitHub()
    github.logs = FAILURES["pytest"].encode()
    username = "ai_live_" + secrets.token_hex(6)
    credentials = {
        "username": username,
        "email": username + "@example.com",
        "password": "Test!Aa9" + secrets.token_hex(18),
    }
    application = create_app(config, github_transport=github.transport)
    with TestClient(application) as client:
        client.headers.update({"X-CodeMate-Request": "1", "Origin": "http://localhost:3000"})
        try:
            assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
            tokens = client.post(
                "/api/v1/auth/login",
                json={"email": credentials["email"], "password": credentials["password"]},
            ).json()
            client.headers["Authorization"] = "Bearer " + tokens["access_token"]
            client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            authorization = client.post("/api/v1/auth/github/connect").json()["authorization_url"]
            state = parse_qs(urlsplit(authorization).query)["state"][0]
            client.get(
                "/api/v1/github/callback",
                params={"state": state, "code": "fixture"},
                follow_redirects=False,
            )
            response = client.post(
                "/api/v1/auth/ai/investigations",
                json={
                    "owner": "octocat",
                    "repo": "secure-demo",
                    "installation_id": 10,
                    "workflow_run_id": 701,
                },
            )
            assert response.status_code == 202
            worker = InvestigationWorker(
                config,
                application.state.session_factory,
                application.state.engine,
                application.state.github_client,
                application.state.ollama_client,
            )
            import time

            started = time.monotonic()
            assert worker.tick()
            elapsed = time.monotonic() - started
            result = client.get("/api/v1/ai/investigations/" + response.json()["id"]).json()
            if result["status"] != "completed":
                print(
                    json.dumps(
                        {
                            "fixture_based": True,
                            "status": result["status"],
                            "error_code": result["error_code"],
                            "elapsed_seconds": round(elapsed, 2),
                        }
                    )
                )
                return 1
            report = Report.model_validate(result["report"])
            with application.state.session_factory() as db:
                persisted = db.scalar(
                    select(AIInvestigation).where(
                        AIInvestigation.id == __import__("uuid").UUID(result["id"])
                    )
                )
                assert persisted.report
            print(
                json.dumps(
                    {
                        "fixture_based": True,
                        "status": result["status"],
                        "model": report.model_name,
                        "elapsed_seconds": round(elapsed, 2),
                        "findings": len(report.findings),
                        "evidence": len(report.evidence),
                        "completeness": report.evidence_completeness,
                        "schema_valid": True,
                        "persisted_and_reloaded": True,
                    }
                )
            )
            return 0
        finally:
            with application.state.session_factory() as db:
                db.execute(
                    delete(User).where(
                        User.username == username, User.email == credentials["email"]
                    )
                )
                db.commit()


if __name__ == "__main__":
    raise SystemExit(main())
