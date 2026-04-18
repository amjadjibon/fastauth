from pydantic_settings import BaseSettings, SettingsConfigDict


def _asyncpg_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
        "postgres://", "postgresql+asyncpg://", 1
    )


def _psycopg2_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg2://", 1).replace(
        "postgres://", "postgresql+psycopg2://", 1
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_seconds: int = 60
    refresh_token_expire_seconds: int = 3600
    database_url: str

    @property
    def async_database_url(self) -> str:
        return _asyncpg_url(self.database_url)

    @property
    def sync_database_url(self) -> str:
        return _psycopg2_url(self.database_url)


settings = Settings()  # ty: ignore[missing-argument]
