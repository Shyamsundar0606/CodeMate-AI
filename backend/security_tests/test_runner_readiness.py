"""Admission metadata cannot become execution authority. No runtime is launched."""

import copy

import pytest
from pydantic import ValidationError

from app.sandbox.policy import capabilities
from app.sandbox.schemas import Capabilities
from app.voice.agent import known


def test_requirements_are_independent_of_environment_and_fixture_success(monkeypatch):
    monkeypatch.setenv("SANDBOX_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("SANDBOX_FIXTURE_CHECKS_PASSED", "true")
    value = Capabilities.model_validate(capabilities())
    assert value.execution_enabled is False
    assert value.readiness.state == "blocked"
    assert value.isolation["image_digest"] is None
    assert len({c.id for c in value.readiness.checks}) == 6


@pytest.mark.parametrize(
    "mutation", ["enable", "verified", "missing", "duplicate", "passed", "command"]
)
def test_invalid_admission_contract_fails_closed(mutation):
    value = copy.deepcopy(capabilities())
    if mutation == "enable":
        value["execution_enabled"] = True
    elif mutation == "verified":
        value["readiness"]["state"] = "verified"
    elif mutation == "missing":
        value["readiness"]["checks"].pop()
    elif mutation == "duplicate":
        value["readiness"]["checks"][1] = value["readiness"]["checks"][0]
    elif mutation == "passed":
        value["readiness"]["checks"][0]["status"] = "verified"
    else:
        value["readiness"]["command"] = "sh"
    with pytest.raises(ValidationError):
        Capabilities.model_validate(value)


def test_readiness_response_mutation_cannot_affect_future_requests():
    first = capabilities()
    first["readiness"]["checks"][0]["status"] = "verified"
    assert capabilities()["readiness"]["checks"][0]["status"] == "not_implemented"


@pytest.mark.parametrize(
    "phrase",
    [
        "CodeMate, show my latest validation result.",
        "CodeMate, explain why validation failed.",
        "CodeMate, open sandbox execution history.",
        "CodeMate, show the sandbox readiness status.",
    ],
)
def test_readiness_voice_commands_only_navigate(phrase):
    result = known(phrase)
    assert result.intent == "navigate"
    assert result.destination == "automation"
