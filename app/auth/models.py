import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    username: str = Field(sa_column=Column(String(32), unique=True, index=True))
    email: str = Field(sa_column=Column(String(254), unique=True))
    hashed_password: str = Field(sa_column=Column(String(60)))
    email_verified: bool = Field(
        default=False, sa_column=Column(Boolean(), nullable=False, server_default="0")
    )
    created_at: datetime = Field(
        default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
