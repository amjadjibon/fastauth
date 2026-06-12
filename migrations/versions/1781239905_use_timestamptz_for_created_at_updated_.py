"""use timestamptz for created_at updated_at

Revision ID: 1781239905
Revises: 1776492254
Create Date: 2026-06-12 12:51:45.961763

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1781239905"
down_revision: str | Sequence[str] | None = "1776492254"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("user", "created_at", type_=sa.DateTime(timezone=True), existing_nullable=False)
    op.alter_column("user", "updated_at", type_=sa.DateTime(timezone=True), existing_nullable=False)


def downgrade() -> None:
    op.alter_column(
        "user", "created_at", type_=sa.DateTime(timezone=False), existing_nullable=False
    )
    op.alter_column(
        "user", "updated_at", type_=sa.DateTime(timezone=False), existing_nullable=False
    )
