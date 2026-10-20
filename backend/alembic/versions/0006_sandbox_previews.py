"""Add safe preparation records; execution remains unavailable."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0006_sandbox_previews"
down_revision = "0005_safe_automation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sandbox_previews",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column(
            "proposal_id", sa.UUID(), sa.ForeignKey("automation_proposals.id", ondelete="SET NULL")
        ),
        sa.Column("binding_hash", sa.String(64), nullable=False),
        sa.Column("preview", JSONB(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_sandbox_preview_request"),
        sa.CheckConstraint(
            "state IN ('awaiting_confirmation','cancelled','expired')",
            name="ck_sandbox_preview_state",
        ),
    )
    op.create_index(
        "ix_sandbox_preview_owner_created", "sandbox_previews", ["user_id", "created_at"]
    )
    op.create_table(
        "sandbox_audit",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "preview_id",
            sa.UUID(),
            sa.ForeignKey("sandbox_previews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_sandbox_audit_preview_id", "sandbox_audit", ["preview_id"])


def downgrade():
    op.drop_table("sandbox_audit")
    op.drop_table("sandbox_previews")
