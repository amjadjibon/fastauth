"""SQLModel table definitions for OAuth2, MFA, sessions, RBAC, and audit logging."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Boolean, Integer
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# OAuth2 tables
# ---------------------------------------------------------------------------


class OAuthClient(SQLModel, table=True):
    __tablename__ = "oauth_clients"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    name: str = Field(sa_column=Column(String(255), nullable=False))
    client_secret_hash: str | None = Field(sa_column=Column(String(128), nullable=True))
    redirect_uris: str = Field(sa_column=Column(Text(), nullable=False))
    scopes: str = Field(default="openid profile email", sa_column=Column(Text(), nullable=False))
    grant_types: str = Field(default="authorization_code", sa_column=Column(Text(), nullable=False))
    is_confidential: bool = Field(default=True, sa_column=Column(Boolean(), nullable=False))
    is_active: bool = Field(default=True, sa_column=Column(Boolean(), nullable=False))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class OAuthAuthorizationCode(SQLModel, table=True):
    __tablename__ = "oauth_authorization_codes"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    code: str = Field(sa_column=Column(String(128), nullable=False, unique=True))
    client_id: str = Field(sa_column=Column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    redirect_uri: str = Field(sa_column=Column(String(2048), nullable=False))
    scopes: str = Field(sa_column=Column(Text(), nullable=False))
    code_challenge: str | None = Field(sa_column=Column(String(128), nullable=True))
    code_challenge_method: str | None = Field(sa_column=Column(String(10), nullable=True))
    nonce: str | None = Field(sa_column=Column(String(128), nullable=True))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class OAuthAccessToken(SQLModel, table=True):
    __tablename__ = "oauth_access_tokens"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    jti: str = Field(sa_column=Column(String(128), nullable=False, unique=True))
    client_id: str = Field(sa_column=Column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False))
    user_id: str | None = Field(default=None, sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=True))
    scopes: str = Field(sa_column=Column(Text(), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class OAuthRefreshToken(SQLModel, table=True):
    __tablename__ = "oauth_refresh_tokens"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    token_hash: str = Field(sa_column=Column(String(128), nullable=False, unique=True))
    client_id: str = Field(sa_column=Column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False))
    user_id: str | None = Field(default=None, sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=True))
    access_token_id: str | None = Field(default=None, sa_column=Column(String(36), ForeignKey("oauth_access_tokens.id", ondelete="CASCADE"), nullable=True))
    scopes: str = Field(sa_column=Column(Text(), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


# ---------------------------------------------------------------------------
# MFA tables
# ---------------------------------------------------------------------------


class UserMfaSecret(SQLModel, table=True):
    __tablename__ = "user_mfa_secrets"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True))
    secret_encrypted: str = Field(sa_column=Column(Text(), nullable=False))
    algorithm: str = Field(default="SHA1", sa_column=Column(String(10), nullable=False))
    digits: int = Field(default=6, sa_column=Column(Integer(), nullable=False))
    period: int = Field(default=30, sa_column=Column(Integer(), nullable=False))
    is_verified: bool = Field(default=False, sa_column=Column(Boolean(), nullable=False))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    verified_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


class UserMfaBackupCode(SQLModel, table=True):
    __tablename__ = "user_mfa_backup_codes"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    code_hash: str = Field(sa_column=Column(String(128), nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


# ---------------------------------------------------------------------------
# Session table
# ---------------------------------------------------------------------------


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    refresh_token_jti: str = Field(sa_column=Column(String(128), nullable=False, unique=True))
    device_type: str | None = Field(default=None, sa_column=Column(String(32), nullable=True))
    device_name: str | None = Field(default=None, sa_column=Column(String(128), nullable=True))
    browser: str | None = Field(default=None, sa_column=Column(String(128), nullable=True))
    os: str | None = Field(default=None, sa_column=Column(String(128), nullable=True))
    ip_address: str | None = Field(default=None, sa_column=Column(String(45), nullable=True))
    user_agent: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    last_active_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


# ---------------------------------------------------------------------------
# Social accounts table
# ---------------------------------------------------------------------------


class UserSocialAccount(SQLModel, table=True):
    __tablename__ = "user_social_accounts"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    provider: str = Field(sa_column=Column(String(32), nullable=False))
    provider_user_id: str = Field(sa_column=Column(String(255), nullable=False))
    provider_email: str | None = Field(default=None, sa_column=Column(String(254), nullable=True))
    provider_username: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    access_token_encrypted: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    refresh_token_encrypted: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    token_expires_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    raw_data: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


# ---------------------------------------------------------------------------
# RBAC tables
# ---------------------------------------------------------------------------


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    name: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    description: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    is_system: bool = Field(default=False, sa_column=Column(Boolean(), nullable=False))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    resource: str = Field(sa_column=Column(String(64), nullable=False))
    action: str = Field(sa_column=Column(String(64), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    role_id: str = Field(sa_column=Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False))
    assigned_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    assigned_by: str | None = Field(default=None, sa_column=Column(String(36), nullable=True))


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    role_id: str = Field(sa_column=Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False))
    permission_id: str = Field(sa_column=Column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False))
    assigned_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


# ---------------------------------------------------------------------------
# Password reset tokens table
# ---------------------------------------------------------------------------


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    token_hash: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


# ---------------------------------------------------------------------------
# Audit log table
# ---------------------------------------------------------------------------


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: str = Field(default_factory=_uuid, sa_column=Column(String(36), primary_key=True))
    event_type: str = Field(sa_column=Column(String(64), nullable=False))
    user_id: str | None = Field(default=None, sa_column=Column(String(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True))
    ip_address: str | None = Field(default=None, sa_column=Column(String(45), nullable=True))
    user_agent: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    metadata_json: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    outcome: str = Field(default="success", sa_column=Column(String(16), nullable=False))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
