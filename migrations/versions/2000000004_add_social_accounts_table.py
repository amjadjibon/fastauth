"""add_social_accounts_table

Revision ID: 2000000004
Revises: 2000000003
Create Date: 2026-06-13 00:00:03.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000004"
down_revision: str | Sequence[str] | None = "2000000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_social_accounts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(254), nullable=True),
        sa.Column("provider_username", sa.String(255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),
    )
    op.create_index("ix_user_social_accounts_user_id", "user_social_accounts", ["user_id"])
    op.create_index("ix_user_social_accounts_provider", "user_social_accounts", ["provider"])


def downgrade() -> None:
    op.drop_table("user_social_accounts")
