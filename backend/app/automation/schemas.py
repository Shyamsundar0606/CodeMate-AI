import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.ai.schemas import StrictModel
from app.automation.policy import safe_path


class Create(StrictModel):
    request_id: uuid.UUID
    owner: str = Field(min_length=1, max_length=39)
    repo: str = Field(min_length=1, max_length=100)
    installation_id: int = Field(gt=0, le=9007199254740991)
    workflow_run_id: int | None = Field(default=None, gt=0, le=9007199254740991)
    paths: list[str] = Field(min_length=1, max_length=4)

    @field_validator("paths")
    @classmethod
    def paths_valid(cls, value):
        if len(set(p.casefold() for p in value)) != len(value):
            raise ValueError("Duplicate paths")
        return [safe_path(p) for p in value]


class Generate(StrictModel):
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    request: str = Field(min_length=3, max_length=1000)
    mode: Literal["explain", "patch"] = "patch"


class Change(StrictModel):
    path: str = Field(max_length=180)
    before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    replacement: str = Field(max_length=12000)


class Citation(StrictModel):
    evidence_id: str | None = None
    line_start: int | None = Field(default=None, gt=0, strict=True)
    line_end: int | None = Field(default=None, gt=0, strict=True)
    source: str = Field(min_length=1, max_length=180)
    quote: str = Field(min_length=1, max_length=300)


class Suggestion(StrictModel):
    explanation: str = Field(min_length=1, max_length=2000)
    expected_improvement: str = Field(min_length=1, max_length=1000)
    risks: list[str] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(min_length=1, max_length=5)
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    evidence: list[Citation] = Field(min_length=1, max_length=8)
    changes: list[Change] = Field(max_length=4)
    validations: list[Literal["python_syntax", "python_tests", "typescript", "eslint"]] = Field(
        max_length=4
    )

    @field_validator("risks", "limitations")
    @classmethod
    def bounded_items(cls, value):
        if any(not item or len(item) > 1000 for item in value):
            raise ValueError("Bounded nonempty items required")
        return value


class CitationReference(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=32)
    line_start: int | None = Field(default=None, gt=0, strict=True)
    line_end: int | None = Field(default=None, gt=0, strict=True)


class GeneratedSuggestion(Suggestion):
    evidence: list[CitationReference] = Field(min_length=1, max_length=8)


class FileExplanation(StrictModel):
    evidence: list[CitationReference] = Field(min_length=1, max_length=2)


class Decision(StrictModel):
    workspace_id: uuid.UUID
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approve", "reject", "cancel"]
    validations: list[Literal["python_syntax", "python_tests", "typescript", "eslint"]] = Field(
        default_factory=list, max_length=4
    )


class Proposal(StrictModel):
    id: uuid.UUID
    status: Literal[
        "awaiting_approval", "explained", "approved", "rejected", "cancelled", "expired"
    ]
    request: str
    mode: str
    patch_hash: str
    diff: str
    files: list[str]
    suggestion: Suggestion
    expires_at: datetime
    selected_validations: list[str]
    applied: Literal[False] = False
    execution: Literal["disabled"] = "disabled"


class SessionView(StrictModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    repository: str
    base_sha: str
    expires_at: datetime
    files: list[str]
    evidence: dict[str, str]
    proposals: list[Proposal]
    audit: list[dict]
    execution_enabled: Literal[False] = False
    execution_message: str
