"""add_oauth_client_active

Revision ID: 2000000008
Revises: 2000000007
Create Date: 2026-06-13 00:00:07.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000008"
down_revision: str | Sequence[str] | None = "2000000007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oauth_clients",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("oauth_clients", "is_active")
