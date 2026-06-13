"""add_oauth_tables

Revision ID: 2000000001
Revises: 1781239905
Create Date: 2026-06-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2000000001"
down_revision: str | Sequence[str] | None = "1781239905"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_secret_hash", sa.String(128), nullable=True),
        sa.Column("redirect_uris", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default="openid profile email"),
        sa.Column("grant_types", sa.Text(), nullable=False, server_default="authorization_code"),
        sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "oauth_authorization_codes",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("code", sa.String(128), nullable=False, unique=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("redirect_uri", sa.String(2048), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=True),
        sa.Column("code_challenge_method", sa.String(10), nullable=True),
        sa.Column("nonce", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_authorization_codes_code", "oauth_authorization_codes", ["code"])
    op.create_index("ix_oauth_authorization_codes_client_id", "oauth_authorization_codes", ["client_id"])

    op.create_table(
        "oauth_access_tokens",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("jti", sa.String(128), nullable=False, unique=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_access_tokens_jti", "oauth_access_tokens", ["jti"])

    op.create_table(
        "oauth_refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=True),
        sa.Column("access_token_id", sa.String(36), sa.ForeignKey("oauth_access_tokens.id", ondelete="CASCADE"), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_refresh_tokens_token_hash", "oauth_refresh_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("oauth_refresh_tokens")
    op.drop_table("oauth_access_tokens")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("oauth_clients")
