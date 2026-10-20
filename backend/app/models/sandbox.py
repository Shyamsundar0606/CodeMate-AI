import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SandboxPreview(Base):
    __tablename__ = "sandbox_previews"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_sandbox_preview_request"),
        CheckConstraint(
            "state IN ('awaiting_confirmation','cancelled','expired')",
            name="ck_sandbox_preview_state",
        ),
        Index("ix_sandbox_preview_owner_created", "user_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    request_id: Mapped[uuid.UUID] = mapped_column()
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("automation_proposals.id", ondelete="SET NULL")
    )
    binding_hash: Mapped[str] = mapped_column(String(64))
    preview: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(32), default="awaiting_confirmation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SandboxAudit(Base):
    __tablename__ = "sandbox_audit"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    preview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sandbox_previews.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
