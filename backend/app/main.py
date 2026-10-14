import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import BoundedSemaphore

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.health import router as health_router
from app.api.routes.ai import mutations as ai_mutations
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.github import mutations as github_mutations
from app.api.routes.github import router as github_router
from app.api.routes.users import router as users_router
from app.api.routes.voice import mutations as voice_mutations
from app.api.routes.voice import router as voice_router
from app.core.config import Settings
from app.core.logging import RequestLogMiddleware, protect_external_access_logs
from app.db.session import build_engine, build_session_factory
from app.integrations.github.authorization_cache import AuthorizationCache
from app.integrations.github.client import GitHubClient
from app.integrations.ollama.client import OllamaClient
from app.voice.speech import SpeechRuntime

logger = logging.getLogger("codemate.errors")


def create_app(
    settings: Settings | None = None,
    *,
    github_transport: httpx.BaseTransport | None = None,
    ollama_transport: httpx.BaseTransport | None = None,
) -> FastAPI:
    protect_external_access_logs()
    config = settings or Settings()
    if (github_transport is not None or ollama_transport is not None) and config.app_env != "test":
        raise ValueError("Mock GitHub transport is permitted only in the isolated test environment")
    github_client = GitHubClient(config, github_transport)
    ollama_client = OllamaClient(config, ollama_transport)
    engine = build_engine(config)
    voice_speech = SpeechRuntime(config)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            voice_speech.close()
            github_client.close()
            ollama_client.close()
            engine.dispose()

    application = FastAPI(title=config.app_name, version="0.1.0", lifespan=lifespan)
    application.state.voice_gate = BoundedSemaphore(config.voice_max_concurrent_requests)
    application.state.voice_speech = voice_speech
    application.state.github_client = github_client
    application.state.ollama_client = ollama_client
    application.state.github_authorization_cache = AuthorizationCache()
    application.state.settings = config
    application.state.engine = engine
    application.state.session_factory = build_session_factory(engine)
    application.add_middleware(RequestLogMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-CodeMate-Request"],
        expose_headers=["X-Request-ID"],
    )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic errors may include submitted passwords; omit input and context.
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"detail": errors, "request_id": getattr(request.state, "request_id", None)},
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            json.dumps(
                {
                    "event": "unexpected_failure",
                    "request_id": request_id,
                    "category": type(exc).__name__,
                }
            )
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id or "unknown"},
        )

    @application.get("/health/ready", tags=["health"])
    def readiness() -> JSONResponse:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar()
            if revision != "0004_voice_agent":
                return JSONResponse(status_code=503, content={"status": "unavailable"})
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return JSONResponse(content={"status": "ok", "database": "ready"})

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(github_router)
    application.include_router(github_mutations)
    application.include_router(ai_router)
    application.include_router(ai_mutations)
    application.include_router(voice_router)
    application.include_router(voice_mutations)
    return application


app = create_app()
