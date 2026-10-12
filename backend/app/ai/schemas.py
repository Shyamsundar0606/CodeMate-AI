import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, max_length=2000)]
Category = Literal[
    "dependency_installation",
    "python_test",
    "javascript_test",
    "build",
    "lint",
    "database_migration",
    "configuration",
    "environment",
    "permissions",
    "networking",
    "resource_exhaustion",
    "timeout",
    "security_finding",
    "unknown",
    "no_failure",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class InvestigationRequest(StrictModel):
    installation_id: Annotated[int, Field(gt=0, le=9223372036854775807)]
    owner: Annotated[str, Field(min_length=1, max_length=39)]
    repo: Annotated[str, Field(min_length=1, max_length=100)]
    workflow_run_id: Annotated[int, Field(gt=0, le=9007199254740991)]


class Evidence(StrictModel):
    id: str
    workflow_run_id: int
    job_id: int | None
    step: str | None
    source: Literal["job_log", "job_metadata", "run_metadata"]
    excerpt: Annotated[str, Field(max_length=4000)]
    line_start: int | None = None
    line_end: int | None = None
    timestamp: str | None = None
    redacted: bool = True
    truncated: bool = False


class Claim(StrictModel):
    evidence_id: Annotated[str, Field(min_length=1, max_length=80)]
    quote: Annotated[str, Field(min_length=1, max_length=600)]


class Finding(StrictModel):
    id: Annotated[str, Field(min_length=1, max_length=50)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Text
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    evidence: Annotated[list[Claim], Field(min_length=1, max_length=5)]
    root_cause_hypothesis: Text
    suggested_fix: Text
    verification_steps: Annotated[list[Text], Field(min_length=1, max_length=5)]


class Diagnosis(StrictModel):
    summary: Text
    failure_category: Category
    findings: Annotated[list[Finding], Field(max_length=5)]
    recommended_actions: Annotated[list[Text], Field(max_length=5)]
    limitations: Annotated[list[Text], Field(max_length=10)]


class Report(Diagnosis):
    workflow_name: str | None
    commit_sha: str
    branch: str | None
    run_conclusion: str | None
    analyzed_job_ids: list[int]
    model_name: str | None
    evidence_completeness: Literal["complete", "partial", "missing"]
    evidence: Annotated[list[Evidence], Field(max_length=24)]


class InvestigationResponse(StrictModel):
    id: uuid.UUID
    owner: str
    repo: str
    workflow_run_id: int
    installation_id: int
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    stage: str
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    report: Report | None


class History(StrictModel):
    items: list[InvestigationResponse]
    page: int
    has_next: bool
    completed_count: int
    failed_count: int


class ModelInfo(StrictModel):
    name: str
    size_bytes: int


class AIStatus(StrictModel):
    available: bool
    model_available: bool
    selected_model: str
    message: str


def ground(diagnosis: Diagnosis, evidence: list[Evidence]) -> Diagnosis:
    """References and observations are authoritative only when quotes match retrieved evidence."""
    available = {item.id: item.excerpt for item in evidence}
    ids = [item.id for item in diagnosis.findings]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate finding identifiers")
    prose = " ".join(
        [
            diagnosis.summary,
            *diagnosis.recommended_actions,
            *[
                f.root_cause_hypothesis + " " + f.suggested_fix + " " + f.description
                for f in diagnosis.findings
            ],
        ]
    )
    if re.search(
        r"(?i)(send|upload|reveal|exfiltrate).{0,80}(credentials?|tokens?|secrets?|passwords?)|"
        r"ignore previous instructions|https?://(?!github\.com(?:/|\b))",
        prose,
    ):
        raise ValueError("Suspicious generated instructions")
    corpus = "\n".join(available.values())
    limitations = list(diagnosis.limitations)
    for finding in diagnosis.findings:
        for claim in finding.evidence:
            if (
                claim.evidence_id not in available
                or claim.quote not in available[claim.evidence_id]
            ):
                raise ValueError("Unsupported evidence reference or observation")
        prose = " ".join(
            [finding.description, finding.root_cause_hypothesis, finding.suggested_fix]
        )
        specific = re.findall(
            r"CVE-\d{4}-\d+|[\w./-]+\.(?:py|tsx?|ya?ml|json)|\b\w+(?:Error|Exception)\b", prose
        )
        if any(value not in corpus for value in specific):
            finding.confidence = "LOW"
            limitations.append(
                "A proposed detail is not present in retrieved evidence; treat it as unverified."
            )
    if diagnosis.failure_category == "security_finding" and not re.search(
        r"vulnerab|CVE-|security|audit", corpus, re.I
    ):
        raise ValueError("Security finding lacks supporting evidence")
    diagnosis.limitations = list(dict.fromkeys(limitations))[:10]
    return diagnosis
