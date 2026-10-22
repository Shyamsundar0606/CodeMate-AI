"""Database-independent gate tests. No repository content is executed."""

import copy
import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.ai.errors import AIError
from app.automation.policy import digest, patch
from app.automation.schemas import Change
from app.sandbox.policy import ISOLATION, PROFILE, capabilities, fingerprint
from app.sandbox.schemas import Confirm, Prepare
from app.services.sandbox_service import SandboxService


@pytest.fixture
def service():
    owner = uuid.uuid4()
    source = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        base_sha="a" * 40,
        repository="owner/repo",
        context={"files": {"main.py": "x = 1\n"}},
    )
    change = Change(path="main.py", before_sha256=digest("x = 1\n"), replacement="x = 2\n")
    changes = patch(source.context["files"], [change])
    content = {
        "suggestion": {
            "explanation": "Change a constant",
            "expected_improvement": "Unverified",
            "risks": ["Review required"],
            "limitations": ["Not executed"],
            "confidence": "LOW",
            "evidence": [{"source": "main.py", "quote": "x = 1"}],
            "changes": [change.model_dump()],
            "validations": [],
        },
        "changes": changes,
        "diff": "".join(c["diff"] for c in changes),
    }
    proposal = SimpleNamespace(
        id=uuid.uuid4(),
        status="approved",
        content=content,
        patch_hash=fingerprint(content),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    proposal.approval = {
        "user_id": str(owner),
        "workspace_id": str(source.workspace_id),
        "repository": source.repository,
        "base_sha": source.base_sha,
        "patch_hash": proposal.patch_hash,
        "action": "review_patch_only",
        "decision": "approve",
    }
    automation = Mock(user_id=owner)
    automation.owned.return_value = source
    automation.db.scalar.return_value = proposal
    automation.content_hash.side_effect = lambda row, value: fingerprint(value)
    service = SandboxService(automation)
    return service, source, proposal


def test_revalidate_approved_patch(service):
    runner, source, proposal = service
    assert runner.proposal(source.id, proposal.id)[2] == proposal.content["changes"]
    runner.automation.authorize.assert_called_once_with(source)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "rejected"),
        ("status", "awaiting_approval"),
        ("expires_at", datetime(2000, 1, 1, tzinfo=UTC)),
        ("patch_hash", "0" * 64),
    ],
)
def test_invalid_approval_rejected(service, field, value):
    runner, source, proposal = service
    setattr(proposal, field, value)
    with pytest.raises(AIError):
        runner.proposal(source.id, proposal.id)


@pytest.mark.parametrize("field", ["user_id", "workspace_id", "repository", "base_sha", "action"])
def test_review_binding_rejected(service, field):
    runner, source, proposal = service
    proposal.approval[field] = "changed"
    with pytest.raises(AIError):
        runner.proposal(source.id, proposal.id)


@pytest.mark.parametrize("path", ["../main.py", "C:/main.py", ".git/config", "a\\main.py"])
def test_rehashed_malicious_paths_rejected(service, path):
    runner, source, proposal = service
    proposal.content["suggestion"]["changes"][0]["path"] = path
    proposal.patch_hash = fingerprint(proposal.content)
    proposal.approval["patch_hash"] = proposal.patch_hash
    with pytest.raises(AIError):
        runner.proposal(source.id, proposal.id)


def test_source_revision_change_rejected(service):
    runner, source, proposal = service
    source.base_sha = "b" * 40
    with pytest.raises(AIError):
        runner.proposal(source.id, proposal.id)


def test_source_content_change_rejected(service):
    runner, source, proposal = service
    source.context["files"]["main.py"] = "changed\n"
    with pytest.raises(AIError):
        runner.proposal(source.id, proposal.id)


@pytest.mark.parametrize("field", ["diff", "changes"])
def test_rehashed_artifact_mismatch_rejected(service, field):
    runner, source, proposal = service
    proposal.content[field] = "changed" if field == "diff" else []
    proposal.patch_hash = fingerprint(proposal.content)
    proposal.approval["patch_hash"] = proposal.patch_hash
    with pytest.raises(AIError):
        runner.proposal(source.id, proposal.id)


@pytest.mark.parametrize("interaction", ["voice", "model", "yes"])
def test_voice_cannot_confirm(interaction):
    with pytest.raises(ValidationError):
        Confirm(binding_hash="a" * 64, interaction=interaction)


@pytest.mark.parametrize(
    "extra", [{"command": "echo no"}, {"host_path": "C:/"}, {"profiles": ["python_tests"]}]
)
def test_no_arbitrary_command_or_host_path(extra):
    with pytest.raises(ValidationError):
        Prepare.model_validate(
            {
                "request_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "proposal_id": str(uuid.uuid4()),
                "profiles": ["python_syntax"],
                **extra,
            }
        )


def test_confirmation_hard_denial_even_when_valid(service, monkeypatch):
    runner, source, proposal = service
    preview = {
        "request": {"session_id": str(source.id), "proposal_id": str(proposal.id)},
        "base_sha": source.base_sha,
        "patch_hash": proposal.patch_hash,
        "diff": proposal.content["diff"],
        "isolation": copy.deepcopy(ISOLATION),
        "profiles": [copy.deepcopy(PROFILE)],
    }
    row = SimpleNamespace(
        id=uuid.uuid4(),
        state="awaiting_confirmation",
        preview=preview,
        binding_hash=fingerprint(preview),
    )
    monkeypatch.setattr("app.services.sandbox_service.serialized", lambda *args: nullcontext())
    runner.owned = Mock(return_value=row)
    runner.authorize_preview = Mock()
    runner.audit = Mock()
    with pytest.raises(AIError) as result:
        runner.confirm(row.id, Confirm(binding_hash=row.binding_hash, interaction="ui_click"))
    assert result.value.status_code == 503
    assert result.value.detail["code"] == "SANDBOX_UNVERIFIED"
    assert row.state == "awaiting_confirmation"
    runner.audit.assert_called_once_with(row, "confirmation_denied_sandbox_unverified")


def test_unverified_capability_has_no_image_or_enable_override(monkeypatch):
    monkeypatch.setenv("SANDBOX_EXECUTION_ENABLED", "true")
    assert capabilities()["execution_enabled"] is False
    assert capabilities()["isolation"]["image_digest"] is None


@pytest.mark.parametrize(
    "phrase",
    [
        "CodeMate, show my approved patch",
        "CodeMate, show the sandbox validation status",
        "CodeMate, open execution history",
        "CodeMate, explain why the tests failed",
        "CodeMate, show my last sandbox result",
        "CodeMate, explain my failed validation",
        "CodeMate, show the patch that was tested",
    ],
)
def test_voice_only_navigates_to_preparation(phrase):
    from app.voice.agent import known

    result = known(phrase)
    assert result.intent == "navigate"
    assert result.destination == "automation"
