import uuid
from typing import Literal

from pydantic import Field

from app.ai.schemas import StrictModel


class Prepare(StrictModel):
    request_id: uuid.UUID
    session_id: uuid.UUID
    proposal_id: uuid.UUID
    profiles: list[Literal["python_syntax"]] = Field(min_length=1, max_length=1)


class Confirm(StrictModel):
    binding_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    interaction: Literal["ui_click"]


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
