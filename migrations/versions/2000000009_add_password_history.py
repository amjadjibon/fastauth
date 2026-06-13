"""add_password_history

Revision ID: 2000000009
Revises: 2000000008
Create Date: 2026-06-13 00:00:08.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000009"
down_revision: str | Sequence[str] | None = "2000000008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_history",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("hashed_password", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_history_user_id", "password_history", ["user_id"])


def downgrade() -> None:
    op.drop_table("password_history")
