"""M8 fallback API regressions. Uses only the guarded PostgreSQL fixture."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_ai import ai as ai
from test_automation import automation as automation
from test_automation import decision, prepare, url

from app.models.automation import AutomationProposal, AutomationSession
from app.models.sandbox import SandboxAudit, SandboxPreview

READ = "/api/v1/sandbox"
WRITE = "/api/v1/auth/sandbox/executions"


def approved(automation):
    client, _ = automation
    row = prepare(automation)
    assert client.post(url(row), json=decision(row)).status_code == 200
    return row, {
        "request_id": str(uuid.uuid4()),
        "session_id": row["id"],
        "proposal_id": row["proposals"][0]["id"],
        "profiles": ["python_syntax"],
    }


def preview(automation):
    row, body = approved(automation)
    response = automation[0].post(WRITE, json=body)
    assert response.status_code == 201, response.text
    return row, body, response.json()


@pytest.mark.parametrize(
    "path", ["/capabilities", "/executions", "/executions/" + str(uuid.uuid4())]
)
def test_unauthenticated_reads(client, path):
    assert client.get(READ + path).status_code == 401


def test_preview_exact_and_persisted(automation):
    row, body, result = preview(automation)
    client, _ = automation
    assert result["preview"]["base_sha"] == row["base_sha"]
    assert result["preview"]["diff"] == row["proposals"][0]["diff"]
    assert result["preview"]["patch_hash"] == row["proposals"][0]["patch_hash"]
    assert result["execution_enabled"] is False
    assert result["exit_code"] is None
    assert result["stdout"] == ""
    assert result["changed_manifest"] == []
    assert client.post(WRITE, json=body).json()["id"] == result["id"]
    assert client.get(READ + "/executions/" + result["id"]).json() == result
    assert client.get(READ + "/executions").json()[0] == result


def test_review_does_not_authorize_execution(automation, db):
    _, _, result = preview(automation)
    client, _ = automation
    path = WRITE + "/" + result["id"] + "/confirm"
    body = {"binding_hash": result["binding_hash"], "interaction": "ui_click"}
    for _ in range(2):
        response = client.post(path, json=body)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "SANDBOX_UNVERIFIED"
    assert db.get(SandboxPreview, uuid.UUID(result["id"])).state == "awaiting_confirmation"
    assert (
        len(
            list(
                db.scalars(
                    select(SandboxAudit).where(
                        SandboxAudit.event == "confirmation_denied_sandbox_unverified"
                    )
                )
            )
        )
        == 1
    )


@pytest.mark.parametrize(
    "headers",
    [
        {"X-CSRF-Token": "invalid"},
        {"Origin": "https://evil.example"},
        {"X-CodeMate-Request": "0"},
    ],
)
def test_prepare_csrf(automation, headers):
    _, body = approved(automation)
    assert automation[0].post(WRITE, json=body, headers=headers).status_code == 403


@pytest.mark.parametrize("state", ["awaiting_approval", "rejected", "cancelled", "explained"])
def test_nonapproved_denied(automation, db, state):
    _, body = approved(automation)
    db.get(AutomationProposal, uuid.UUID(body["proposal_id"])).status = state
    db.commit()
    assert automation[0].post(WRITE, json=body).status_code == 409


@pytest.mark.parametrize("target", ["proposal", "session"])
def test_expired_source_denied(automation, db, target):
    _, body = approved(automation)
    model, key = (
        (AutomationProposal, "proposal_id")
        if target == "proposal"
        else (AutomationSession, "session_id")
    )
    db.get(model, uuid.UUID(body[key])).expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert automation[0].post(WRITE, json=body).status_code in (404, 409)


def test_hash_tamper_denied(automation, db):
    _, body = approved(automation)
    db.get(AutomationProposal, uuid.UUID(body["proposal_id"])).patch_hash = "0" * 64
    db.commit()
    assert automation[0].post(WRITE, json=body).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"profiles": ["python_tests"]},
        {"profiles": ["python_syntax", "python_syntax"]},
        {"command": "echo unsafe"},
        {"host_path": "C:/Users"},
    ],
)
def test_only_fixed_profiles(automation, changes):
    _, body = approved(automation)
    assert automation[0].post(WRITE, json={**body, **changes}).status_code == 422


def test_cancellation_is_idempotent_and_final(automation):
    _, _, result = preview(automation)
    client, _ = automation
    path = WRITE + "/" + result["id"]
    for _ in range(2):
        assert client.post(path + "/cancel").json()["state"] == "cancelled"
    assert (
        client.post(
            path + "/confirm",
            json={
                "binding_hash": result["binding_hash"],
                "interaction": "ui_click",
            },
        ).status_code
        == 409
    )


def test_changed_confirmation_and_voice_denied(automation):
    _, _, result = preview(automation)
    client, _ = automation
    path = WRITE + "/" + result["id"] + "/confirm"
    assert (
        client.post(path, json={"binding_hash": "0" * 64, "interaction": "ui_click"}).status_code
        == 409
    )
    assert (
        client.post(
            path, json={"binding_hash": result["binding_hash"], "interaction": "voice"}
        ).status_code
        == 422
    )


def test_expired_preview_denied(automation, db):
    _, _, result = preview(automation)
    db.get(SandboxPreview, uuid.UUID(result["id"])).expires_at = datetime.now(UTC) - timedelta(
        seconds=1
    )
    db.commit()
    assert (
        automation[0]
        .post(
            WRITE + "/" + result["id"] + "/confirm",
            json={
                "binding_hash": result["binding_hash"],
                "interaction": "ui_click",
            },
        )
        .status_code
        == 409
    )


def test_concurrent_prepare_has_one_record(automation, db):
    _, body = approved(automation)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: automation[0].post(WRITE, json=body), range(2)))
    assert all(r.status_code in (201, 409) for r in results)
    successful = [r for r in results if r.status_code == 201]
    assert successful
    for response in results:
        if response.status_code == 409:
            assert response.json()["detail"]["code"] == "VOICE_BUSY"
    retry = automation[0].post(WRITE, json=body)
    assert retry.status_code == 201
    assert all(r.json()["id"] == retry.json()["id"] for r in successful)
    assert len(list(db.scalars(select(SandboxPreview)))) == 1


def test_preview_cross_owner_denied(automation, client, logged_in):
    _, _, result = preview(automation)
    client.headers["Authorization"] = "Bearer " + logged_in["access_token"]
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert client.get(READ + "/executions/" + result["id"]).status_code == 404
    assert client.get(READ + "/executions").json() == []
    assert client.post(WRITE + "/" + result["id"] + "/cancel").status_code == 404
