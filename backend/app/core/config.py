import json
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    voice_enabled: bool = True
    whisper_model_size: Literal["base", "small"] = "base"
    whisper_model_path: str = "models/whisper-base"
    whisper_device: Literal["cpu", "auto", "cuda"] = "cpu"
    whisper_compute_type: Literal["int8", "float32", "float16"] = "int8"
    voice_max_recording_seconds: int = Field(default=30, ge=1, le=60)
    voice_max_upload_bytes: int = Field(default=8388608, ge=1024, le=16777216)
    voice_session_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    voice_action_ttl_seconds: int = Field(default=120, ge=10, le=300)
    voice_timeout_seconds: int = Field(default=60, ge=5, le=180)
    voice_max_concurrent_requests: int = Field(default=1, ge=1, le=2)
    voice_requests_per_minute: int = Field(default=12, ge=1, le=60)
    voice_retain_transcripts: bool = False
    voice_tts_enabled: bool = True
    piper_model_path: str = "models/en_US-ljspeech-medium.onnx"
    piper_config_path: str = "models/en_US-ljspeech-medium.onnx.json"
    piper_speaker_id: int = Field(default=0, ge=0, le=1000)

    app_name: str = "CodeMate AI"
    http_max_body_bytes: int = Field(default=1048576, ge=16384, le=2097152)
    http_body_timeout_seconds: int = Field(default=15, ge=1, le=60)
    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "codemate-ai"
    jwt_audience: str = "codemate-api"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=30)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    cookie_secure: bool = False
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    login_window_seconds: int = Field(default=300, ge=60)
    login_ip_limit: int = Field(default=30, ge=1)
    login_account_limit: int = Field(default=10, ge=1)

    # GitHub App user authorization; disabled until all private configuration is present.
    github_client_id: str = ""
    github_client_secret: SecretStr | None = None
    github_token_encryption_key: SecretStr | None = None
    github_redirect_uri: str = "http://localhost:8000/api/v1/github/callback"
    github_frontend_origin: str = "http://localhost:3000"
    github_app_slug: str = ""
    github_api_base_url: Literal["https://api.github.com"] = "https://api.github.com"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = Field(default="qwen2.5-coder:3b", pattern=r"^[A-Za-z0-9_.:/-]{1,100}$")
    ollama_timeout_seconds: int = Field(default=120, ge=5, le=180)
    ai_max_log_chars: int = Field(default=64000, ge=1000, le=262144)
    ai_max_context_chars: int = Field(default=24000, ge=4000, le=32000)
    ai_max_evidence_chars: int = Field(default=12000, ge=1000, le=16000)
    ai_per_job_chars: int = Field(default=3000, ge=500, le=4000)
    ai_max_jobs: int = Field(default=4, ge=1, le=4)
    ai_max_concurrent_investigations: int = Field(default=1, ge=1, le=4)
    ai_max_retries: int = Field(default=2, ge=0, le=2)
    ai_investigation_timeout_seconds: int = Field(default=240, ge=30, le=360)
    ai_investigation_retention_days: int = Field(default=30, ge=1, le=90)

    @model_validator(mode="after")
    def voice_model_directory(self) -> "Settings":
        if self.whisper_model_size == "small" and self.whisper_model_path == "models/whisper-base":
            self.whisper_model_path = "models/whisper-small"
        return self

    @field_validator("ollama_base_url")
    @classmethod
    def local_inference_only(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port != 11434
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Ollama must use http://127.0.0.1:11434")
        return value.rstrip("/")

    @model_validator(mode="after")
    def ai_budgets(self) -> "Settings":
        if "cloud" in self.ollama_model.lower():
            raise ValueError("Cloud-hosted Ollama models are prohibited")
        if self.ai_max_context_chars < self.ai_max_evidence_chars + 3000:
            raise ValueError("AI context must leave room for evidence metadata")
        return self

    @property
    def github_configured(self) -> bool:
        return bool(
            self.github_client_id and self.github_client_secret and self.github_token_encryption_key
        )

    @model_validator(mode="after")
    def valid_github_configuration(self) -> "Settings":
        import re
        from urllib.parse import urlsplit

        from cryptography.fernet import Fernet

        if self.github_token_encryption_key:
            try:
                Fernet(self.github_token_encryption_key.get_secret_value().encode())
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    "GITHUB_TOKEN_ENCRYPTION_KEY must be an independently generated Fernet key"
                ) from exc
            if (
                self.github_token_encryption_key.get_secret_value()
                == self.jwt_secret_key.get_secret_value()
            ):
                raise ValueError("GitHub encryption and JWT signing keys must be separate")
        if self.github_client_id or self.github_client_secret:
            if not self.github_configured or not re.fullmatch(
                r"[A-Za-z0-9._-]{1,100}", self.github_client_id
            ):
                raise ValueError(
                    "GitHub requires client ID, client secret and a separate encryption key"
                )
            if len(self.github_client_secret.get_secret_value()) < 20:
                raise ValueError("GitHub client secret is invalid")
        if self.github_app_slug and not re.fullmatch(r"[a-z0-9-]{1,100}", self.github_app_slug):
            raise ValueError("GitHub App slug must be its registered URL slug")
        callback = urlsplit(self.github_redirect_uri)
        if (
            callback.scheme not in {"http", "https"}
            or not callback.netloc
            or callback.username
            or callback.password
            or callback.query
            or callback.fragment
            or callback.path != "/api/v1/github/callback"
        ):
            raise ValueError(
                "GitHub callback must be an explicit "
                "HTTP(S) callback URL without credentials or query"
            )
        frontend = urlsplit(self.github_frontend_origin)
        if (
            frontend.scheme not in {"http", "https"}
            or not frontend.netloc
            or frontend.path
            or frontend.username
            or frontend.password
            or frontend.query
            or frontend.fragment
        ):
            raise ValueError("GitHub frontend return origin must be explicit without a path")
        if self.github_configured:
            if self.github_frontend_origin not in self.cors_origins:
                raise ValueError("GitHub frontend origin must be an allowed CORS origin")
            if self.app_env == "production" and (
                callback.scheme != "https" or frontend.scheme != "https"
            ):
                raise ValueError("Production GitHub authorization requires HTTPS")
            if (
                self.app_env != "production"
                and callback.scheme == "http"
                and callback.hostname not in {"localhost", "127.0.0.1"}
            ):
                raise ValueError("HTTP GitHub callbacks are permitted only on local loopback")
        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value) if value.startswith("[") else value.split(",")
        return value

    @field_validator("cors_origins")
    @classmethod
    def valid_origins(cls, origins: list[str]) -> list[str]:
        from urllib.parse import urlsplit

        if not origins:
            raise ValueError("At least one explicit CORS origin is required")
        for origin in origins:
            if "*" in origin or any(ord(c) <= 32 or ord(c) == 127 for c in origin):
                raise ValueError("CORS origins cannot contain wildcards or control characters")
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return origins

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and bool(url.database and url.username)
        except Exception:
            valid = False
        if not valid:
            raise ValueError("DATABASE_URL must specify PostgreSQL with the psycopg driver")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def strong_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret.encode()) < 48 or len(set(secret)) < 16:
            raise ValueError("JWT_SECRET_KEY requires a securely generated secret of >=48 bytes")
        return value

    @model_validator(mode="after")
    def secure_production(self) -> "Settings":
        if self.app_env == "production":
            secret = self.jwt_secret_key.get_secret_value().lower()
            url = make_url(self.database_url.get_secret_value())
            if secret.startswith(("test", "example", "changeme", "replace_me")):
                raise ValueError("Production signing keys must not be test or example values")
            if url.database == "codemate_test_db" or url.username == "codemate_test_user":
                raise ValueError("Production cannot use the dedicated test database identity")
            if (
                not url.password
                or len(url.password) < 16
                or url.password.lower().startswith(("test", "example", "changeme", "replace"))
            ):
                raise ValueError("Production requires a non-placeholder database password")
            if not self.cookie_secure or any(
                not x.startswith("https://") for x in self.cors_origins
            ):
                raise ValueError("Production requires Secure cookies and HTTPS CORS origins")
        return self
