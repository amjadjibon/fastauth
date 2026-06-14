"""SQLAlchemy ORM table definitions for all auth entities."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(60))
    email_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="0", default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    refresh_token_jti: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    browser: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    os: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, default=None)
    user_agent: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# MFA
# ---------------------------------------------------------------------------


class UserMfaSecret(Base):
    __tablename__ = "user_mfa_secrets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True)
    secret_encrypted: Mapped[str] = mapped_column(Text(), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(10), nullable=False, default="SHA1")
    digits: Mapped[int] = mapped_column(Integer(), nullable=False, default=6)
    period: Mapped[int] = mapped_column(Integer(), nullable=False, default=30)
    is_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


class UserMfaBackupCode(Base):
    __tablename__ = "user_mfa_backup_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Social accounts
# ---------------------------------------------------------------------------


class UserSocialAccount(Base):
    __tablename__ = "user_social_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(254), nullable=True, default=None)
    provider_username: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    raw_data: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    is_system: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    assigned_by: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# OAuth2
# ---------------------------------------------------------------------------


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    redirect_uris: Mapped[str] = mapped_column(Text(), nullable=False)
    scopes: Mapped[str] = mapped_column(Text(), nullable=False, default="openid profile email")
    grant_types: Mapped[str] = mapped_column(Text(), nullable=False, default="authorization_code")
    is_confidential: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    scopes: Mapped[str] = mapped_column(Text(), nullable=False)
    code_challenge: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_challenge_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nonce: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class OAuthAccessToken(Base):
    __tablename__ = "oauth_access_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    jti: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=True, default=None)
    scopes: Mapped[str] = mapped_column(Text(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class OAuthRefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=True, default=None)
    access_token_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("oauth_access_tokens.id", ondelete="CASCADE"), nullable=True, default=None)
    scopes: Mapped[str] = mapped_column(Text(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


class APIKey(Base):
    __tablename__ = "api_key"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scopes: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True, default=None)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, default=None)
    user_agent: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    metadata_json: Mapped[str | None] = mapped_column(Text(), nullable=True, default=None)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
