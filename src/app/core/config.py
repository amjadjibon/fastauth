from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_seconds: int = 60
    refresh_token_expire_seconds: int = 3600
    database_url: str = "sqlite+aiosqlite:///fastauth.db"


settings = Settings()  # ty: ignore[missing-argument]
