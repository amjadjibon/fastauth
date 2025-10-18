from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    # Supports both PostgreSQL and SQLite:
    # - PostgreSQL: postgresql+asyncpg://user:password@host:port/dbname
    # - SQLite: sqlite+aiosqlite:///path/to/database.db
    # - SQLite (in-memory): sqlite+aiosqlite:///:memory:
    database_url: str = "sqlite+aiosqlite:///./fastauth.db"

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Application
    app_name: str = "FastAuth"
    app_description: str = (
        "A high-performance authentication system with FastAPI and async PostgreSQL"
    )
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
