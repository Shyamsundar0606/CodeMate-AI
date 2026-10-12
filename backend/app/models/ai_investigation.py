import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIInvestigation(Base):
    __tablename__ = "ai_investigations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','completed','failed','cancelled')", name="ck_ai_status"
        ),
        CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_ai_attempts"),
        CheckConstraint("octet_length(report::text) <= 131072", name="ck_ai_report_size"),
        UniqueConstraint(
            "user_id",
            "github_connection_id",
            "installation_id",
            "owner",
            "repo",
            "workflow_run_id",
            name="uq_ai_run_owner",
        ),
        Index("ix_ai_user_created", "user_id", "created_at"),
        Index("ix_ai_status_created", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    github_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("github_connections.id", ondelete="CASCADE")
    )
    installation_id: Mapped[int] = mapped_column(BigInteger)
    owner: Mapped[str] = mapped_column(String(39))
    repo: Mapped[str] = mapped_column(String(100))
    workflow_run_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    stage: Mapped[str] = mapped_column(String(50), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    model_name: Mapped[str | None] = mapped_column(String(100))
    report: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
