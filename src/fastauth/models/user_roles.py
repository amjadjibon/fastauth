"""User-Role association table."""
from sqlmodel import Field, SQLModel


class UserRoleLink(SQLModel, table=True):
    """Association table for User and Role many-to-many relationship."""
    __tablename__ = "user_roles"
    
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role_id: int = Field(foreign_key="role.id", primary_key=True)