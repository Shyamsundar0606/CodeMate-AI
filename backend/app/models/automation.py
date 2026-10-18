import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AutomationSession(Base):
    __tablename__ = "automation_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_automation_request"),
        Index("ix_automation_owner_expiry", "user_id", "expires_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("github_connections.id", ondelete="CASCADE")
    )
    request_id: Mapped[uuid.UUID] = mapped_column()
    repository: Mapped[str] = mapped_column(String(140))
    installation_id: Mapped[int] = mapped_column(BigInteger)
    base_sha: Mapped[str] = mapped_column(String(40))
    context: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AutomationProposal(Base):
    __tablename__ = "automation_proposals"
    __table_args__ = (
        UniqueConstraint("session_id", "request_id", name="uq_automation_proposal_request"),
        CheckConstraint(
            "status IN ('awaiting_approval','explained','approved','rejected','cancelled')",
            name="ck_automation_proposal_state",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("automation_sessions.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column()
    status: Mapped[str] = mapped_column(String(24))
    patch_hash: Mapped[str] = mapped_column(String(64))
    content: Mapped[dict] = mapped_column(JSONB)
    approval: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AutomationAudit(Base):
    __tablename__ = "automation_audit"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("automation_sessions.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutomationBudget(Base):
    __tablename__ = "automation_budgets"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    window: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(default=0)
