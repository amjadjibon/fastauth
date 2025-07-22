"""Role-Permission association table."""
from sqlmodel import Field, SQLModel


class RolePermissionLink(SQLModel, table=True):
    """Association table for Role and Permission many-to-many relationship."""
    __tablename__ = "role_permissions"
    
    role_id: int = Field(foreign_key="role.id", primary_key=True)
    permission_id: int = Field(foreign_key="permission.id", primary_key=True)