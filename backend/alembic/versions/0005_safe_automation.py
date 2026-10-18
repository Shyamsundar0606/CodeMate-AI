"""Add expiring proposal-only developer automation metadata."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0005_safe_automation"
down_revision = "0004_voice_agent"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "automation_sessions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("workspace_id", sa.UUID(), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("github_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("repository", sa.String(140), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("base_sha", sa.String(40), nullable=False),
        sa.Column("context", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_automation_request"),
    )
    op.create_index("ix_automation_owner_expiry", "automation_sessions", ["user_id", "expires_at"])
    op.create_table(
        "automation_proposals",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("automation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.UniqueConstraint("session_id", "request_id", name="uq_automation_proposal_request"),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("patch_hash", sa.String(64), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("approval", JSONB()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('awaiting_approval','explained','approved','rejected','cancelled')",
            name="ck_automation_proposal_state",
        ),
    )
    op.create_index("ix_automation_proposals_session_id", "automation_proposals", ["session_id"])
    op.create_table(
        "automation_audit",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("automation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_automation_audit_session_id", "automation_audit", ["session_id"])
    op.create_table(
        "automation_budgets",
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("window", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )


def downgrade():
    for name in (
        "automation_budgets",
        "automation_audit",
        "automation_proposals",
        "automation_sessions",
    ):
        op.drop_table(name)
