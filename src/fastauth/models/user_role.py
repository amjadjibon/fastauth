from sqlmodel import Field, SQLModel


class UserRole(SQLModel, table=True):
    """Association table for User and Role many-to-many relationship."""
    __tablename__ = "user_roles"
    
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)
