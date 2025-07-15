from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/fastauth"
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Application
    app_name: str = "FastAuth"
    debug: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings()