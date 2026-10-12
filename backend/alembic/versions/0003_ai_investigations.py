"""Add durable, owner-scoped AI investigations."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_ai_investigations"
down_revision = "0002_github_integration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_investigations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "github_connection_id",
            sa.UUID(),
            sa.ForeignKey("github_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.String(39), nullable=False),
        sa.Column("repo", sa.String(100), nullable=False),
        sa.Column("workflow_run_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(100)),
        sa.Column("report", postgresql.JSONB()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('queued','running','completed','failed','cancelled')", name="ck_ai_status"
        ),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_ai_attempts"),
        sa.CheckConstraint("octet_length(report::text) <= 131072", name="ck_ai_report_size"),
        sa.UniqueConstraint(
            "user_id",
            "github_connection_id",
            "installation_id",
            "owner",
            "repo",
            "workflow_run_id",
            name="uq_ai_run_owner",
        ),
    )
    op.create_index("ix_ai_user_created", "ai_investigations", ["user_id", "created_at"])
    op.create_index("ix_ai_status_created", "ai_investigations", ["status", "created_at"])


def downgrade():
    op.drop_table("ai_investigations")
