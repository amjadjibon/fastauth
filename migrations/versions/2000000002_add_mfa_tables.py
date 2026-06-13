"""add_mfa_tables

Revision ID: 2000000002
Revises: 2000000001
Create Date: 2026-06-13 00:00:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000002"
down_revision: str | Sequence[str] | None = "2000000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_mfa_secrets",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.String(10), nullable=False, server_default="SHA1"),
        sa.Column("digits", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("period", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_mfa_secrets_user_id", "user_mfa_secrets", ["user_id"])

    op.create_table(
        "user_mfa_backup_codes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_mfa_backup_codes_user_id", "user_mfa_backup_codes", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_mfa_backup_codes")
    op.drop_table("user_mfa_secrets")
