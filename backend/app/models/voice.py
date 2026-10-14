import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    __table_args__ = (Index("ix_voice_session_owner_expiry", "user_id", "expires_at"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VoiceTurn(Base):
    __tablename__ = "voice_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "request_id", name="uq_voice_request"),
        Index("ix_voice_turn_session_created", "session_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE")
    )
    request_id: Mapped[uuid.UUID] = mapped_column()
    reply: Mapped[dict] = mapped_column(JSONB)
    transcript: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceAction(Base):
    __tablename__ = "voice_actions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE"), index=True
    )
    target: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_investigations.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VoiceBudget(Base):
    __tablename__ = "voice_budgets"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    window: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(default=0)
