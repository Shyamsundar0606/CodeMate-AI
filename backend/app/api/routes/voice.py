import uuid
from typing import Annotated, Literal

import anyio
from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies.auth import (
    AuthenticatedUser,
    Database,
    refresh_credentials,
    require_auth_request,
)
from app.api.routes.github import repository_service
from app.services.auth_service import AuthService
from app.services.voice_service import VoiceService
from app.voice.errors import error
from app.voice.schemas import (
    Action,
    ActionResult,
    Capabilities,
    Command,
    Reply,
    Transcription,
    TTSRequest,
)
from app.voice.speech import MIMES

router = APIRouter(prefix="/api/v1/voice", tags=["local voice agent"])
mutations = APIRouter(
    prefix="/api/v1/auth/voice",
    tags=["local voice mutations"],
    dependencies=[Depends(require_auth_request)],
)


def service(request: Request, db: Database, user: AuthenticatedUser):
    return VoiceService(
        db,
        request.app.state.settings,
        user.id,
        request.app.state.engine,
        request.app.state.ollama_client,
        lambda: repository_service(request, db, user),
    )


Service = Annotated[VoiceService, Depends(service)]


def authorized(
    service: Service,
    request: Request,
    token: Annotated[str, Depends(refresh_credentials)],
    user: AuthenticatedUser,
):
    _, owner = AuthService(service.db, service.settings).active_session(token)
    if owner.id != user.id:
        raise error("SESSION_CHANGED", "Active session does not match the account.", 403)
    return service


Mutation = Annotated[VoiceService, Depends(authorized)]


@router.get("/status", response_model=Capabilities)
def status(request: Request, user: AuthenticatedUser):
    settings = request.app.state.settings
    speech = request.app.state.voice_speech
    return Capabilities(
        enabled=settings.voice_enabled,
        stt_installed=speech.installed("stt"),
        tts_installed=speech.installed("tts"),
        ollama_available=request.app.state.ollama_client.status().model_available,
        max_recording_seconds=settings.voice_max_recording_seconds,
        max_upload_bytes=settings.voice_max_upload_bytes,
        message=(
            "Speech processing is local. GitHub commands require GitHub "
            "connectivity. Model files must be installed separately."
        ),
    )


@mutations.post("/command", response_model=Reply)
def command(body: Command, request: Request, service: Mutation):
    gate = request.app.state.voice_gate
    if not gate.acquire(blocking=False):
        raise error("BUSY", "Voice agent is busy. Try again shortly.", 429)
    try:
        return service.command(body)
    finally:
        gate.release()


@router.get("/sessions/{identity}", response_model=list[Reply])
def history(identity: uuid.UUID, service: Service):
    return service.history(identity)


@mutations.post("/confirm", response_model=ActionResult)
def confirm(body: Action, service: Mutation):
    return service.action(body)


@mutations.post("/cancel", response_model=ActionResult)
def cancel(body: Action, service: Mutation):
    return service.action(body, cancel=True)


@mutations.post("/transcribe", response_model=Transcription)
async def transcribe(
    request: Request, service: Mutation, language: Literal["en", "fr", "auto"] = "en"
):
    service.budget()
    mime = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if mime not in MIMES:
        raise error("MEDIA_TYPE", "Record WebM, Ogg, WAV or MP4 audio.", 415)
    maximum = service.settings.voice_max_upload_bytes
    raw = bytearray()
    try:
        with anyio.fail_after(15):
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > maximum:
                    raise error("UPLOAD_LIMIT", "Recording exceeds its upload limit.", 413)
    except TimeoutError as exc:
        raise error("UPLOAD_TIMEOUT", "Audio upload timed out. Try again.", 408) from exc
    if not raw:
        raise error("EMPTY_AUDIO", "Recording is empty.")
    return await anyio.to_thread.run_sync(
        lambda: request.app.state.voice_speech.run(
            "stt", {"audio": bytes(raw), "mime": mime, "language": language}
        )
    )


@mutations.post("/speech")
def speech(body: TTSRequest, request: Request, service: Mutation):
    service.budget()
    history = service.history(body.session_id)
    turn = next((turn for turn in history if turn.turn_id == body.turn_id), None)
    if turn is None:
        raise error("TURN_UNAVAILABLE", "Response is unavailable.", 404)
    # Client cannot ask Piper to speak arbitrary logs, token strings, or another user's text.
    safe = service.safe(turn.message)[:800]
    audio = request.app.state.voice_speech.run("tts", {"text": safe})
    return Response(
        audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
