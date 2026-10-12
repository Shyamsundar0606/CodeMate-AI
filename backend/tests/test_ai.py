import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event

import httpx
import pytest
from ai_mock import FAILURES, MockOllama, diagnostic
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from github_mock import ACCESS, JOB, RUN, MockGitHub
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.ai.errors import AIError
from app.ai.evidence import extract
from app.ai.schemas import Diagnosis, Evidence, ground
from app.ai.worker import InvestigationWorker
from app.integrations.ollama.client import OllamaClient, local_url
from app.main import create_app
from app.models import AIInvestigation, GitHubConnection
from app.services.ai_investigation_service import purge_expired

REQUEST = {"installation_id": 10, "owner": "octocat", "repo": "secure-demo", "workflow_run_id": 701}
MUTATIONS = "/api/v1/auth/ai/investigations"
READS = "/api/v1/ai/investigations"


@pytest.fixture
def ai(settings):
    config = settings.model_copy(
        update={
            "github_client_id": "Iv1.codemate-test",
            "github_client_secret": __import__("pydantic").SecretStr("fixture-secret-" + "z" * 32),
            "github_token_encryption_key": __import__("pydantic").SecretStr(
                Fernet.generate_key().decode()
            ),
        }
    )
    github, ollama = MockGitHub(), MockOllama()
    with TestClient(
        create_app(config, github_transport=github.transport, ollama_transport=ollama.transport)
    ) as client:
        client.headers.update({"X-CodeMate-Request": "1", "Origin": "http://localhost:3000"})
        credentials = {
            "username": "aiengineer",
            "email": "ai@example.com",
            "password": "StrongPassword123!",
        }
        assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
        tokens = client.post(
            "/api/v1/auth/login",
            json={"email": credentials["email"], "password": credentials["password"]},
        ).json()
        client.headers["Authorization"] = "Bearer " + tokens["access_token"]
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        url = client.post("/api/v1/auth/github/connect", headers={"X-CSRF-Token": csrf}).json()[
            "authorization_url"
        ]
        from urllib.parse import parse_qs, urlsplit

        state = parse_qs(urlsplit(url).query)["state"][0]
        assert (
            client.get(
                "/api/v1/github/callback",
                params={"state": state, "code": "fixture"},
                follow_redirects=False,
            ).status_code
            == 303
        )
        client.headers["X-CSRF-Token"] = csrf
        worker = InvestigationWorker(
            config,
            client.app.state.session_factory,
            client.app.state.engine,
            client.app.state.github_client,
            client.app.state.ollama_client,
        )
        yield client, github, ollama, worker, config


def create(ai, body=None):
    response = ai[0].post(MUTATIONS, json=body or REQUEST)
    assert response.status_code == 202, response.text
    return response.json()


def fetch(ai, identity):
    return ai[0].get(READS + "/" + identity).json()


def test_ai_status_models_and_no_startup_dependency(ai):
    client, _, mock, _, _ = ai
    assert client.get("/api/v1/ai/status").json()["model_available"]
    assert client.get("/api/v1/ai/models").json()[0]["name"] == "qwen2.5-coder:3b"
    mock.mode = "offline"
    assert not client.get("/api/v1/ai/status").json()["available"]
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize(
    "mode,code",
    [
        ("offline", "AI_PROVIDER_UNAVAILABLE"),
        ("missing", "AI_MODEL_MISSING"),
        ("timeout", "AI_TIMEOUT"),
        ("malformed", "AI_INVALID_OUTPUT"),
        ("extra", "AI_INVALID_OUTPUT"),
        ("oversized", "AI_INVALID_OUTPUT"),
        ("truncated", "AI_INVALID_OUTPUT"),
        ("bad_reference", "AI_INVALID_OUTPUT"),
        ("injection", "AI_INVALID_OUTPUT"),
    ],
)
def test_provider_errors_persist_safe_failed_states(ai, mode, code):
    item = create(ai)
    ai[2].mode = mode
    assert ai[3].tick()
    result = fetch(ai, item["id"])
    assert result["status"] == "failed"
    assert result["error_code"] == code
    assert ACCESS not in json.dumps(result)
    assert "private" not in result["error_message"]
    assert ai[0].get("/health").status_code == 200


@pytest.mark.parametrize("name", [key for key in FAILURES if key != "success"])
def test_failure_dataset_graph_evidence_persistence(ai, name, caplog):
    ai[1].logs = FAILURES[name].encode()
    item = create(ai)
    with caplog.at_level("INFO", logger="codemate.ai"):
        assert ai[3].tick()
    result = fetch(ai, item["id"])
    assert result["status"] == "completed", result
    report = result["report"]
    assert report["run_conclusion"] == "failure"
    assert report["findings"] and report["evidence"]
    by_id = {e["id"]: e["excerpt"] for e in report["evidence"]}
    for finding in report["findings"]:
        for claim in finding["evidence"]:
            assert claim["quote"] in by_id[claim["evidence_id"]]
    assert ai[0].get(READS).json()["completed_count"] == 1
    assert "ignore previous" not in caplog.text
    assert ACCESS not in caplog.text
    assert all(
        request.method == "GET" for request in ai[1].calls if request.url.host == "api.github.com"
    )
    assert [
        json.loads(r.message)["stage"]
        for r in caplog.records
        if r.name == "codemate.ai" and json.loads(r.message)["event"] == "ai_stage"
    ] == [
        "authorize",
        "fetch_run",
        "fetch_jobs",
        "collect_evidence",
        "extract_signals",
        "local_diagnosis",
        "ground_findings",
        "build_report",
    ]


def test_success_skips_logs_and_inference(ai):
    ai[1].overrides["/repos/octocat/secure-demo/actions/runs/701"] = (
        200,
        {**RUN, "conclusion": "success"},
        {},
    )
    item = create(ai)
    assert ai[3].tick()
    report = fetch(ai, item["id"])["report"]
    assert report["failure_category"] == "no_failure"
    assert not report["findings"] and report["model_name"] is None
    assert not ai[2].calls
    assert not any(r.url.path.endswith("/logs") for r in ai[1].calls)


@pytest.mark.parametrize("missing", [True, False])
def test_missing_jobs_or_logs_does_not_invent_cause(ai, missing):
    if missing:
        ai[1].overrides["/repos/octocat/secure-demo/actions/runs/701/jobs"] = (
            200,
            {"total_count": 0, "jobs": []},
            {},
        )
    else:
        ai[1].overrides["/repos/octocat/secure-demo/actions/jobs/801/logs"] = (404, {}, {})
    item = create(ai)
    assert ai[3].tick()
    report = fetch(ai, item["id"])["report"]
    assert report["failure_category"] == "unknown" and not report["findings"]
    assert report["evidence_completeness"] in {"partial", "missing"}
    assert not ai[2].calls


def test_multiple_jobs_partial_pagination_and_budgets(ai):
    jobs = [{**JOB, "id": 801 + i} for i in range(4)]
    ai[1].overrides["/repos/octocat/secure-demo/actions/runs/701/jobs"] = (
        200,
        {"total_count": 5, "jobs": jobs},
        {
            "Link": (
                "<https://api.github.com/repos/octocat/secure-demo/"
                'actions/runs/701/jobs?page=2>; rel="next"'
            )
        },
    )
    item = create(ai)
    assert ai[3].tick()
    report = fetch(ai, item["id"])["report"]
    assert report["evidence_completeness"] == "partial"
    assert len(report["analyzed_job_ids"]) == 4


def test_idempotency_admission_and_history(ai):
    first = create(ai)
    second = create(ai)
    assert first["id"] == second["id"]
    ai[1].overrides["/repos/octocat/secure-demo/actions/runs/702"] = (200, {**RUN, "id": 702}, {})
    response = ai[0].post(MUTATIONS, json={**REQUEST, "workflow_run_id": 702})
    assert response.status_code == 409
    assert ai[3].tick()
    create(ai, {**REQUEST, "workflow_run_id": 702})
    response = ai[0].get(READS + "?per_page=1").json()
    assert len(response["items"]) == 1 and response["has_next"]
    assert len(ai[0].get(READS + "?per_page=1&page=2").json()["items"]) == 1


def test_retries_are_bounded_and_recover(ai):
    item = create(ai)
    ai[2].mode = "offline"
    for attempt in range(3):
        assert ai[3].tick()
        assert fetch(ai, item["id"])["attempts"] == attempt + 1
        response = ai[0].post(MUTATIONS + "/" + item["id"] + "/retry")
        assert response.status_code == (200 if attempt < 2 else 409)
    assert not ai[3].tick()


def test_interrupted_execution_recovers_and_limits(ai, db):
    item = create(ai)
    entry = db.get(AIInvestigation, uuid.UUID(item["id"]))
    entry.status = "running"
    entry.attempts = 1
    db.commit()
    assert ai[3].tick()
    assert fetch(ai, item["id"])["status"] == "completed"
    assert fetch(ai, item["id"])["attempts"] == 2
    db.expire_all()
    entry = db.get(AIInvestigation, entry.id)
    entry.status = "running"
    entry.attempts = 3
    db.commit()
    assert ai[3].tick()
    assert fetch(ai, item["id"])["error_code"] == "AI_RETRY_LIMIT"


def test_worker_global_and_job_locks(ai):
    item = create(ai)
    key = int.from_bytes(uuid.UUID(item["id"]).bytes[:8], "big", signed=True)
    with ai[3].engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(51805,0)"))
        connection.commit()
        try:
            assert not ai[3].tick()
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(51805,0)"))
            connection.commit()
        connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        connection.commit()
        try:
            assert not ai[3].tick()
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
            connection.commit()
    assert ai[3].tick()


def test_two_workers_cannot_run_same_item(ai, monkeypatch):
    create(ai)
    entered, release = Event(), Event()
    real = ai[3].execute

    def blocked(db, item):
        entered.set()
        assert release.wait(10)
        real(db, item)

    monkeypatch.setattr(ai[3], "execute", blocked)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(ai[3].tick)
        assert entered.wait(10)
        assert not ai[3].tick()
        release.set()
        assert first.result()


def test_cancellation_and_deletion(ai):
    item = create(ai)
    assert ai[0].post(MUTATIONS + "/" + item["id"] + "/cancel").json()["status"] == "cancelled"
    assert not ai[3].tick()
    assert ai[0].post(MUTATIONS + "/" + item["id"] + "/retry").status_code == 409
    assert ai[0].post(MUTATIONS + "/" + item["id"] + "/delete").status_code == 200
    assert ai[0].get(READS + "/" + item["id"]).status_code == 404


def test_owner_isolation_and_csrf(ai):
    item = create(ai)
    client = ai[0]
    assert client.post(MUTATIONS, json=REQUEST, headers={"X-CSRF-Token": "bad"}).status_code == 403
    assert (
        client.post(MUTATIONS, json=REQUEST, headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    client.headers.pop("Authorization")
    assert client.get(READS).status_code == 401
    credentials = {
        "username": "otherengineer",
        "email": "otherai@example.com",
        "password": "StrongPassword123!",
    }
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    ).json()
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert client.get(READS + "/" + item["id"]).status_code == 404
    assert not client.get(READS).json()["items"]
    assert client.post(MUTATIONS + "/" + item["id"] + "/cancel").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {**REQUEST, "installation_id": 11},
        {**REQUEST, "owner": "other", "repo": "public"},
        {**REQUEST, "owner": "bad!"},
        {**REQUEST, "workflow_run_id": 0},
    ],
)
def test_unauthorized_or_invalid_context(ai, body):
    response = ai[0].post(MUTATIONS, json=body)
    assert response.status_code in {404, 422}
    assert not ai[0].get(READS).json()["items"]


def test_database_constraints_cascades_retention(ai, db):
    item = create(ai)
    row = db.get(AIInvestigation, uuid.UUID(item["id"]))
    row.status = "invalid"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    row = db.get(AIInvestigation, row.id)
    row.status = "failed"
    row.completed_at = datetime.now(UTC) - timedelta(days=31)
    db.commit()
    purge_expired(db, ai[4])
    assert db.get(AIInvestigation, row.id) is None
    item = create(ai)
    connection = db.scalar(select(GitHubConnection))
    db.delete(connection)
    db.commit()
    assert db.get(AIInvestigation, uuid.UUID(item["id"])) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example",
        "http://localhost:11434",
        "http://127.0.0.1:1234",
        "http://127.0.0.1:11434/api",
        "http://user:pass@127.0.0.1:11434",
        "http://127.0.0.1:11434?x=1",
    ],
)
def test_external_inference_urls_rejected(url):
    with pytest.raises(ValueError):
        local_url(url)


def test_evidence_stability_context_redaction_and_truncation():
    raw = "before\nAssertionError: failure\nsecret=hello\n" + ACCESS + "\nafter\n" * 500
    first = extract(raw, 1, 2, None, 500, 1000)
    assert first == extract(raw, 1, 2, None, 500, 1000)
    assert first[0].line_start == 1 and "before" in first[0].excerpt
    assert ACCESS not in json.dumps([e.model_dump() for e in first])
    assert sum(len(e.excerpt) for e in first) <= 500 and first[0].truncated


def test_grounding_rejects_unknown_quotes_and_flags_unverified_details():
    evidence = Evidence(
        id="E1",
        workflow_run_id=1,
        job_id=2,
        step=None,
        source="job_log",
        excerpt="AssertionError: failed",
    )
    value = diagnostic({"evidence": [evidence.model_dump()]})
    value["findings"][0]["description"] = "Check nonexistent.py"
    result = ground(Diagnosis.model_validate(value), [evidence])
    assert result.findings[0].confidence == "LOW" and len(result.limitations) == 2
    value["findings"][0]["evidence"][0]["quote"] = "invented traceback"
    with pytest.raises(ValueError):
        ground(Diagnosis.model_validate(value), [evidence])


def test_cancellation_propagates_from_provider_check(settings):
    provider = OllamaClient(settings, httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    try:
        with pytest.raises(AIError):
            provider.request(
                "/api/tags",
                check=lambda: (_ for _ in ()).throw(AIError("AI_CANCELLED", "Cancelled", 409)),
            )
    finally:
        provider.close()


def test_additive_migration_preserves_existing_users_connections(ai, db):
    from alembic.config import Config
    from conftest import BACKEND

    from alembic import command

    before = db.scalar(select(GitHubConnection))
    identity, user_id, ciphertext = before.id, before.user_id, before.encrypted_access_token
    db.commit()
    config = Config(str(BACKEND / "alembic.ini"))
    try:
        command.downgrade(config, "0002_github_integration")
        assert db.scalar(text("SELECT to_regclass('ai_investigations')")) is None
    finally:
        db.commit()
        command.upgrade(config, "head")
    db.expire_all()
    after = db.get(GitHubConnection, identity)
    assert after.user_id == user_id and after.encrypted_access_token == ciphertext
    command.check(config)


def test_concurrent_create_is_idempotent(ai):
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: ai[0].post(MUTATIONS, json=REQUEST), range(2)))
    assert all(response.status_code == 202 for response in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]


def test_live_inference_remains_off_in_automated_tests(ai):
    item = create(ai)
    assert ai[3].tick()
    result = fetch(ai, item["id"])
    assert result["report"]["limitations"][0].startswith("Fixture response")
    assert all(r.url.host == "127.0.0.1" for r in ai[2].calls)


def test_cloud_model_setting_is_rejected(settings):
    from app.core.config import Settings

    values = settings.model_dump()
    values["ollama_model"] = "qwen:cloud"
    with pytest.raises(ValueError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("remove", [False, True])
def test_running_cancellation_and_deletion_are_safe(ai, monkeypatch, remove):
    item = create(ai)
    original = ai[3].ollama.diagnose

    def interrupt(context, check, timeout):
        assert ai[0].post(MUTATIONS + "/" + item["id"] + "/cancel").status_code == 200
        if remove:
            assert ai[0].post(MUTATIONS + "/" + item["id"] + "/delete").status_code == 200
        return original(context, check, timeout)

    monkeypatch.setattr(ai[3].ollama, "diagnose", interrupt)
    assert ai[3].tick()
    response = ai[0].get(READS + "/" + item["id"])
    if remove:
        assert response.status_code == 404
    else:
        assert response.json()["status"] == "cancelled"
        assert response.json()["report"] is None


def test_per_user_worker_lock_blocks_work_even_with_free_global_slot(ai, db):
    item = create(ai)
    row = db.get(AIInvestigation, uuid.UUID(item["id"]))
    key = int.from_bytes(row.user_id.bytes[:4], "big", signed=True)
    db.commit()
    with ai[3].engine.connect() as guard:
        guard.execute(text("SELECT pg_advisory_lock(51806,:key)"), {"key": key})
        guard.commit()
        try:
            assert not ai[3].tick()
        finally:
            guard.execute(text("SELECT pg_advisory_unlock(51806,:key)"), {"key": key})
            guard.commit()
    assert ai[3].tick()
