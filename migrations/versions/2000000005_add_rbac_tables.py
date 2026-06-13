"""add_rbac_tables

Revision ID: 2000000005
Revises: 2000000004
Create Date: 2026-06-13 00:00:04.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000005"
down_revision: str | Sequence[str] | None = "2000000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "permission_id",
            sa.String(36),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    # Seed default roles
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    cols = "id, name, description, is_system, created_at, updated_at"
    role_rows = ", ".join(
        [
            f"('00000000-0000-0000-0000-000000000001', 'admin', 'Full system access', true, '{now}', '{now}')",  # noqa: E501
            f"('00000000-0000-0000-0000-000000000002', 'user', 'Standard user access', true, '{now}', '{now}')",  # noqa: E501
            f"('00000000-0000-0000-0000-000000000003', 'moderator', 'Moderation access', true, '{now}', '{now}')",  # noqa: E501
        ]
    )
    op.execute(f"INSERT INTO roles ({cols}) VALUES {role_rows}")

    # Seed default permissions
    resources_actions = [
        ("users", "read:own"),
        ("users", "update:own"),
        ("users", "delete:own"),
        ("users", "read:all"),
        ("users", "update:all"),
        ("users", "delete:all"),
        ("sessions", "read:own"),
        ("sessions", "revoke:own"),
        ("sessions", "revoke:all"),
        ("audit_logs", "read:own"),
        ("audit_logs", "read:all"),
        ("roles", "read"),
        ("roles", "manage"),
    ]
    perm_values = []
    for i, (resource, action) in enumerate(resources_actions, start=1):
        pid = f"00000000-0000-0000-0001-{i:012d}"
        perm_values.append(f"('{pid}', '{resource}', '{action}', '{now}')")
    values_str = ", ".join(perm_values)
    op.execute(f"INSERT INTO permissions (id, resource, action, created_at) VALUES {values_str}")


def downgrade() -> None:
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
