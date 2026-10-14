"""Add owner-scoped bounded voice metadata without changing existing tables."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0004_voice_agent"
down_revision = "0003_ai_investigations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "voice_sessions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("context", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_voice_session_owner_expiry", "voice_sessions", ["user_id", "expires_at"])
    op.create_table(
        "voice_turns",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("voice_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("reply", JSONB(), nullable=False),
        sa.Column("transcript", sa.String(1000)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("session_id", "request_id", name="uq_voice_request"),
    )
    op.create_index("ix_voice_turn_session_created", "voice_turns", ["session_id", "created_at"])
    op.create_table(
        "voice_actions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("voice_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target", JSONB(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column(
            "investigation_id",
            sa.UUID(),
            sa.ForeignKey("ai_investigations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_voice_actions_session_id", "voice_actions", ["session_id"])
    op.create_table(
        "voice_budgets",
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("window", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )


def downgrade():
    for table in ("voice_budgets", "voice_actions", "voice_turns", "voice_sessions"):
        op.drop_table(table)
