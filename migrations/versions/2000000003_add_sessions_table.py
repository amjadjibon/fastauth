"""add_sessions_table

Revision ID: 2000000003
Revises: 2000000002
Create Date: 2026-06-13 00:00:02.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000003"
down_revision: str | Sequence[str] | None = "2000000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("refresh_token_jti", sa.String(128), nullable=False, unique=True),
        sa.Column("device_type", sa.String(32), nullable=True),
        sa.Column("device_name", sa.String(128), nullable=True),
        sa.Column("browser", sa.String(128), nullable=True),
        sa.Column("os", sa.String(128), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_refresh_token_jti", "user_sessions", ["refresh_token_jti"])


def downgrade() -> None:
    op.drop_table("user_sessions")
