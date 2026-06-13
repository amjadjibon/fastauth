from pydantic_settings import BaseSettings, SettingsConfigDict


def _async_url(url: str) -> str:
    return (
        url.replace("postgresql://", "postgresql+asyncpg://", 1)
        .replace("postgres://", "postgresql+asyncpg://", 1)
        .replace("sqlite://", "sqlite+aiosqlite://", 1)
    )


def _sync_url(url: str) -> str:
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
    redis_url: str | None = None

    # CORS
    cors_origins: list[str] = []

    # MFA
    mfa_required_for_all_users: bool = False

    # Load testing
    load_test: bool = False

    # OpenTelemetry
    otel_enabled: bool = False
    otel_service_name: str = "fastauth"
    otel_exporter: str = "otlp"  # "otlp" | "console" | "none"
    otel_otlp_endpoint: str | None = None  # e.g. http://localhost:4318/v1/traces

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def async_database_url(self) -> str:
        return _async_url(self.database_url)

    @property
    def sync_database_url(self) -> str:
        return _sync_url(self.database_url)


settings = Settings()  # ty: ignore[missing-argument]
