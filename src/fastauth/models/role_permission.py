from uuid import UUID

from sqlmodel import Field, SQLModel


class RolePermission(SQLModel, table=True):
    """Association table for Role and Permission many-to-many relationship."""

    __tablename__ = "role_permissions"

    role_id: UUID = Field(foreign_key="roles.id", primary_key=True)
    permission_id: UUID = Field(foreign_key="permissions.id", primary_key=True)
