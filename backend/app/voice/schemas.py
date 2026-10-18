import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROUTES = {
    "automation": "/dashboard/automation",
    "dashboard": "/dashboard",
    "repositories": "/dashboard/repositories",
    "cicd": "/dashboard/cicd",
    "ai": "/dashboard/ai",
    "profile": "/dashboard/profile",
    "settings": "/dashboard/settings",
    "github": "/dashboard/github",
}
IntentName = Literal[
    "navigate",
    "repositories",
    "repository",
    "latest_run",
    "failed_run",
    "jobs",
    "logs",
    "analyze",
    "history",
    "report",
    "explain_report",
    "help",
    "question",
    "confirm",
    "cancel",
    "unsupported",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Intent(Strict):
    selected: bool = Field(
        default=False,
        description="True only for a previous workflow reference. False for latest-run searches.",
    )
    intent: IntentName
    destination: (
        Literal[
            "dashboard", "repositories", "cicd", "ai", "profile", "settings", "github", "automation"
        ]
        | None
    ) = None
    repository: str | None = Field(default=None, max_length=140)


class Command(Strict):
    session_id: uuid.UUID | None = None
    request_id: uuid.UUID
    text: str = Field(min_length=1, max_length=1000)


class Action(Strict):
    session_id: uuid.UUID
    action_id: uuid.UUID


class TTSRequest(Strict):
    session_id: uuid.UUID
    turn_id: uuid.UUID


class Target(Strict):
    owner: str
    repo: str
    installation_id: int
    workflow_run_id: int
    status: str
    conclusion: str | None
    connection_id: uuid.UUID


class Reply(Strict):
    session_id: uuid.UUID
    turn_id: uuid.UUID
    intent: str
    message: str
    route: str | None = None
    confirmation_required: bool = False
    action_id: uuid.UUID | None = None
    target: Target | None = None
    choices: list[str] = Field(default_factory=list)


class Transcription(Strict):
    text: str
    language: str


class Capabilities(Strict):
    enabled: bool
    stt_installed: bool
    tts_installed: bool
    ollama_available: bool
    max_recording_seconds: int
    max_upload_bytes: int
    message: str


class ActionResult(Strict):
    message: str = Field(max_length=1000)
    route: str | None = None
