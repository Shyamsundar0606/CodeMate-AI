"""Add encrypted GitHub connections and single-use browser-bound authorization state."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_github_integration"
down_revision = "0001_backend_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_connections",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("github_user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("github_login", sa.String(39), nullable=False),
        sa.Column("github_display_name", sa.String(200)),
        sa.Column("github_avatar_url", sa.String(500), nullable=False),
        sa.Column("encrypted_access_token", sa.Text()),
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True)),
        sa.Column("granted_permissions", postgresql.JSONB(), nullable=False),
        sa.Column("connection_status", sa.String(32), nullable=False),
        sa.Column(
            "connected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "connection_status IN ('connected', 'reauthorization_required')",
            name="ck_github_connection_status",
        ),
        sa.CheckConstraint("github_user_id > 0", name="ck_github_user_id"),
        sa.CheckConstraint(
            "connection_status <> 'connected' OR encrypted_access_token IS NOT NULL",
            name="ck_github_connected_credential",
        ),
    )
    op.create_table(
        "github_oauth_states",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("refresh_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("encrypted_verifier", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_github_oauth_states_user_id", "github_oauth_states", ["user_id"])
    op.create_index("ix_github_oauth_states_expires_at", "github_oauth_states", ["expires_at"])


def downgrade() -> None:
    op.drop_table("github_oauth_states")
    op.drop_table("github_connections")
