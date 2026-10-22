import uuid
from typing import Literal

from pydantic import Field, model_validator

from app.ai.schemas import StrictModel


class Prepare(StrictModel):
    request_id: uuid.UUID
    session_id: uuid.UUID
    proposal_id: uuid.UUID
    profiles: list[Literal["python_syntax"]] = Field(min_length=1, max_length=1)


class Confirm(StrictModel):
    binding_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    interaction: Literal["ui_click"]


class ReadinessCheck(StrictModel):
    id: Literal[
        "worker_identity",
        "launcher_boundary",
        "image_provenance",
        "hostile_isolation",
        "durable_recovery",
        "fixture_integration",
    ]
    status: Literal["not_implemented", "unverified"]
    label: str = Field(max_length=80)
    reason: str = Field(max_length=240)


class RunnerReadiness(StrictModel):
    policy_version: Literal["m10-readiness-v1"]
    state: Literal["blocked"]
    checks: list[ReadinessCheck] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def distinct_requirements(self):
        if len({check.id for check in self.checks}) != 6:
            raise ValueError("Every admission requirement must be represented exactly once.")
        return self


class Capabilities(StrictModel):
    execution_enabled: Literal[False]
    verification: Literal["unverified"]
    reasons: list[str]
    isolation: dict
    profiles: list[dict]
    readiness: RunnerReadiness


class ExecutionView(StrictModel):
    id: uuid.UUID
    state: Literal["awaiting_confirmation", "cancelled", "expired"]
    binding_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    preview: dict
    expires_at: str
    execution_enabled: Literal[False] = False
    applied: Literal[False] = False
    validation_status: Literal["not_executed"] = "not_executed"
    exit_code: None = None
    stdout: Literal[""] = ""
    stderr: Literal[""] = ""
    changed_manifest: list[dict] = Field(max_length=0)
    audit: list[dict] = Field(max_length=50)
