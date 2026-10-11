import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GitHubConnection(Base):
    __tablename__ = "github_connections"
    __table_args__ = (
        CheckConstraint(
            "connection_status IN ('connected', 'reauthorization_required')",
            name="ck_github_connection_status",
        ),
        CheckConstraint("github_user_id > 0", name="ck_github_user_id"),
        CheckConstraint(
            "connection_status <> 'connected' OR encrypted_access_token IS NOT NULL",
            name="ck_github_connected_credential",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    github_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    github_login: Mapped[str] = mapped_column(String(39))
    github_display_name: Mapped[str | None] = mapped_column(String(200))
    github_avatar_url: Mapped[str] = mapped_column(String(500))
    encrypted_access_token: Mapped[str | None] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_permissions: Mapped[dict] = mapped_column(JSONB, default=dict)
    connection_status: Mapped[str] = mapped_column(String(32), default="connected")
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GitHubOAuthState(Base):
    __tablename__ = "github_oauth_states"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("refresh_sessions.id", ondelete="CASCADE")
    )
    browser_hash: Mapped[str] = mapped_column(String(64))
    encrypted_verifier: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
